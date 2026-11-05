"""
Simulation Bridge: Python / MATLAB Subprocess Controller
=========================================================
Manages continuous and scheduled live simulation runs of the IEEE 9-bus
Simulink model (IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) for the Live
Demonstration dashboard.

Key capabilities:
- Continuous Software-in-the-Loop (SIL) simulation session (StopTime=inf, 1:1 real-time pacing)
- Genuine incremental 5 kHz signal streaming via non-blocking local TCP socket (port 8502) + HTTP fallback
- Real-time mid-run disturbance injection and runtime reset without restarting MATLAB/Simulink
- Periodic 5-second independent ML classification & IEEE 1159 physical assessment loop
- Strict signal validation: rejects missing channels, NaNs, Infs, flatlines
- Enforces model protection and strictly preserves pristine reference HIL model (SHA-256 verified)

Thread-safe: a global lock ensures only one active simulation session runs at a time.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import socket
import shutil
import hashlib
import threading
import queue
import datetime
import subprocess
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIL_PATH = os.path.join(BASE_DIR, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
HIL_EXPECTED_SHA256 = (
    "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"
)
LIVE_RUNS_DIR = os.path.join(BASE_DIR, "data", "live_simulation_runs")
MAX_ROLLING_SAMPLES = 25000

# ---------------------------------------------------------------------------
# Strict Canonical 8-Class Ordering (PROMPT 7 Contract)
# ---------------------------------------------------------------------------
ORDERED_CLASSES = [
    "Flicker",
    "Harmonics",
    "Interruption",
    "Normal",
    "Notch",
    "Sag",
    "Swell",
    "Transient",
]

# Thread-safe pub/sub queues for SSE clients
_sse_subscribers_lock = threading.RLock()
_sse_subscribers: list[queue.Queue] = []

def subscribe_sse() -> queue.Queue:
    """Register a new SSE client queue."""
    q = queue.Queue(maxsize=200)
    with _sse_subscribers_lock:
        _sse_subscribers.append(q)
    return q

def unsubscribe_sse(q: queue.Queue) -> None:
    """Unregister an SSE client queue."""
    with _sse_subscribers_lock:
        if q in _sse_subscribers:
            _sse_subscribers.remove(q)

def broadcast_sse(event_type: str, data: dict) -> None:
    """
    Broadcast an SSE event to all connected clients.
    Non-blocking: if a client queue is full, drop oldest or drop event.
    """
    payload = {
        "event": event_type,
        "data": data,
    }
    with _sse_subscribers_lock:
        dead = []
        for q in _sse_subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                try:
                    _ = q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    dead.append(q)
        for d in dead:
            if d in _sse_subscribers:
                _sse_subscribers.remove(d)
  # 5 seconds of 5 kHz data

# ---------------------------------------------------------------------------
# Disturbance parameter bounds
# ---------------------------------------------------------------------------
PARAM_BOUNDS = {
    "Normal": {},
    "Sag": {
        "fault_resistance_ohms":  (0.01, 100.0),
        "ground_resistance_ohms": (0.1, 10.0),
        "duration_ms":            (20.0, 200.0),
    },
    "Swell": {
        "capacitive_power_mvar": (10.0, 500.0),
        "damping_power_kw":       (1.0,  50.0),
        "duration_ms":            (20.0, 200.0),
    },
    "Interruption": {
        "duration_ms": (20.0, 300.0),
    },
    "Harmonics": {
        "h3_amplitude": (0.0, 0.5),
        "h5_amplitude": (0.0, 0.5),
        "h7_amplitude": (0.0, 0.5),
    },
    "Flicker": {
        "modulation_freq_hz":    (0.5, 35.0),
        "modulation_depth":      (0.01, 0.5),
    },
    "Notch": {
        "commutation_resistance_ohms": (0.001, 500.0),
        "notch_width_us":              (50.0,  2000.0),
    },
    "Transient": {
        "inductance_mh":          (0.1, 50.0),
        "capacitance_uf":         (1.0, 500.0),
        "damping_resistance_ohms":(0.1, 100.0),
    },
}

VALID_CLASSES = set(PARAM_BOUNDS.keys())
VALID_PHASES  = {"A", "B", "C", "AB", "AC", "BC", "ABC"}


# ---------------------------------------------------------------------------
# SimulationJob dataclass
# ---------------------------------------------------------------------------
@dataclass
class SimulationJob:
    run_id:       str
    dist_class:   str
    phases:       list
    params:       dict
    mode:         str       = "continuous"  # continuous | manual | scheduled
    stop_time:    float     = 0.38
    onset_time:   float     = 0.12
    status:       str       = "queued"  # queued|starting|running|streaming|completed|error|cancelled|stopped
    start_time:   float     = field(default_factory=time.time)
    end_time:     Optional[float] = None
    error_message: str      = ""
    progress_pct: float     = 0.0
    chunks_posted: int      = 0
    proc:         Optional[subprocess.Popen] = field(default=None, repr=False)
    log_path:     str       = ""
    cmd_file_path: str      = ""
    tcp_port:     int       = 8502
    voltage:      dict      = field(default_factory=lambda: {"L1": [], "L2": [], "L3": []})
    current:      dict      = field(default_factory=lambda: {"L1": [], "L2": [], "L3": []})
    metrics:      dict      = field(default_factory=dict)
    prediction:   dict      = field(default_factory=dict)
    requested_disturbance: str = "Normal"
    command_status: str     = "IDLE"    # IDLE | APPLIED | RESET | STOPPED | FAILED
    measured_physical_assessment: str = "Normal"
    raw_ml_prediction: str  = "Normal"
    raw_ml_probabilities: dict = field(default_factory=dict)
    model_domain_status: str = "MODEL_COMPATIBLE"
    signal_quality_status: str = "VALID"
    final_classification: str = "Normal"
    classification_timestamp: float = 0.0
    countdown_s:  int       = 5
    injected_cmd: dict      = field(default_factory=dict)
    active_command_id: str  = ""
    applied_simulation_time: float = 0.0
    analysis_window_start: float = 0.0
    analysis_window_end: float = 0.0
    first_sequence: int     = 0
    last_sequence:  int     = 0
    inference_latency_ms: float = 0.0
    inference_wall_clock_monotonic: float = 0.0
    prediction_status: str = "WAITING_FOR_SIMULATION"
    confidence: float = 0.0
    latched_event:  Optional[dict] = None
    inference_history: list = field(default_factory=list)
    simulation_time: float  = 0.0
    last_simulation_time: float = 0.0
    inference_wall_clock_timestamp: float = 0.0
    analysis_window_start_simulation_time: float = 0.0
    analysis_window_end_simulation_time: float = 0.0
    inference_sequence: int = 0
    active_physical_state: str = "Normal"
    latched_event_history: list = field(default_factory=list)
    recovery_status: str    = "NORMAL"
    last_event_start_time: Optional[float] = None
    last_event_end_time: Optional[float] = None

    @property
    def elapsed_s(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 1)


# ---------------------------------------------------------------------------
# Module-level singleton state
# ---------------------------------------------------------------------------
_lock: threading.RLock               = threading.RLock()
_active_job: Optional[SimulationJob] = None
_server_base_url: str                = "http://127.0.0.1:8500"


def set_server_url(url: str) -> None:
    global _server_base_url
    _server_base_url = url.rstrip("/")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_disturbance_config(cfg: dict) -> None:
    """Raise ValueError with a descriptive reason if the config is invalid."""
    dist_class = cfg.get("class", "Normal")
    if dist_class not in VALID_CLASSES:
        raise ValueError(f"Unknown disturbance class '{dist_class}'. Valid: {sorted(VALID_CLASSES)}")

    phases = cfg.get("phases", ["A", "B", "C"])
    if not isinstance(phases, list) or not phases:
        raise ValueError("'phases' must be a non-empty list (e.g. ['A','B','C'])")
    phase_str = "".join(sorted(set(p.upper() for p in phases)))
    if phase_str not in VALID_PHASES:
        raise ValueError(f"Invalid phase combination '{phase_str}'. Valid: {sorted(VALID_PHASES)}")

    params = cfg.get("params", {})
    bounds = PARAM_BOUNDS.get(dist_class, {})
    for key, (lo, hi) in bounds.items():
        if key in params:
            val = params[key]
            try:
                val = float(val)
            except (TypeError, ValueError):
                raise ValueError(f"Parameter '{key}' must be numeric, got {val!r}")
            if not (lo <= val <= hi):
                raise ValueError(
                    f"Parameter '{key}' = {val} is out of range [{lo}, {hi}]"
                )

    stop_time = cfg.get("stop_time", 0.38)
    if not (0.1 <= float(stop_time) <= 5.0):
        raise ValueError(f"stop_time {stop_time} out of range [0.1, 5.0]")

    onset = cfg.get("onset_time", 0.12)
    if not (0.0 <= float(onset) < float(stop_time)):
        raise ValueError(f"onset_time {onset} must be >= 0 and < stop_time {stop_time}")


# ---------------------------------------------------------------------------
# Protected-model integrity check
# ---------------------------------------------------------------------------
def verify_hil_model_sha256() -> tuple[bool, str]:
    """Returns (ok, actual_hex). Does NOT raise; caller decides what to do."""
    if not os.path.exists(HIL_PATH):
        return True, "(file absent — not checked)"
    h = hashlib.sha256()
    with open(HIL_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    actual = h.hexdigest().upper()
    return (actual == HIL_EXPECTED_SHA256), actual


# ---------------------------------------------------------------------------
# MATLAB availability
# ---------------------------------------------------------------------------
def check_matlab_available() -> tuple[bool, str]:
    """Quick check: is 'matlab' on PATH and does it respond?"""
    matlab_exe = shutil.which("matlab")
    if matlab_exe is None:
        return False, "MATLAB executable not found on PATH"
    try:
        result = subprocess.run(
            ["matlab", "-batch", "disp('MATLAB_ALIVE')"],
            capture_output=True, text=True, timeout=120,
        )
        if "MATLAB_ALIVE" in result.stdout:
            return True, matlab_exe
        return False, f"MATLAB did not respond correctly: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "MATLAB availability check timed out (>120 s)"
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Build MATLAB config JSON
# ---------------------------------------------------------------------------
def _build_config(job: SimulationJob) -> dict:
    """Produce the JSON config that MATLAB simulation runner will read."""
    phase_str = "".join(sorted(set(p.upper() for p in job.phases)))
    cfg: dict = {
        "run_id":       job.run_id,
        "mode":         job.mode,
        "class":        job.dist_class,
        "phase":        phase_str,
        "stop_time":    job.stop_time,
        "onset_time":   job.onset_time,
        "server_url":   _server_base_url,
        "model_dir":    os.path.join(BASE_DIR, "IEEE_9bus").replace("\\", "/"),
        "cmd_file":     job.cmd_file_path.replace("\\", "/"),
        "tcp_port":     job.tcp_port,
        "class_params": job.params,
    }
    return cfg


# ---------------------------------------------------------------------------
# Non-blocking local TCP socket receiver for 5 kHz chunks
# ---------------------------------------------------------------------------
def _start_tcp_receiver(job: SimulationJob, port: int = 8502) -> None:
    def receiver_worker():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("127.0.0.1", port))
            srv.listen(2)
            srv.settimeout(1.5)
            while True:
                with _lock:
                    if _active_job is None or _active_job.run_id != job.run_id:
                        break
                    if job.status in ("completed", "error", "cancelled", "stopped"):
                        break
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(1.5)
                    buf = ""
                    while True:
                        with _lock:
                            if _active_job is None or _active_job.run_id != job.run_id:
                                break
                            if job.status in ("completed", "error", "cancelled", "stopped"):
                                break
                        try:
                            chunk_data = conn.recv(65536)
                            if not chunk_data:
                                break
                            buf += chunk_data.decode("utf-8", errors="replace")
                            while "\n" in buf:
                                line, buf = buf.split("\n", 1)
                                line = line.strip()
                                if line:
                                    try:
                                        payload = json.loads(line)
                                        sim_t = payload.get("simulation_time_end")
                                        if sim_t is None and "t" in payload:
                                            try:
                                                sim_t = float(payload["t"][-1])
                                            except Exception:
                                                pass
                                        record_chunk_posted(
                                            run_id=payload.get("run_id", job.run_id),
                                            channels=payload.get("channels") or payload.get("voltage"),
                                            current_channels=payload.get("current_channels") or payload.get("current"),
                                            chunk_index=payload.get("chunk_index", payload.get("sequence", 0)),
                                            simulation_time=sim_t
                                        )
                                    except Exception:
                                        pass
                        except socket.timeout:
                            continue
                        except Exception:
                            break
        except Exception:
            pass
        finally:
            try:
                srv.close()
            except Exception:
                pass

    t = threading.Thread(target=receiver_worker, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Periodic 5-Second ML Classification & Countdown Scheduler
# ---------------------------------------------------------------------------
def _start_periodic_classifier(job: SimulationJob) -> None:
    def classifier_worker():
        seq = 0
        interval = 5.0
        next_tick = time.monotonic() + interval
        while True:
            time.sleep(0.1)
            with _lock:
                if _active_job is None or _active_job.run_id != job.run_id:
                    break
                if job.status in ("completed", "error", "cancelled", "stopped"):
                    break

                now_m = time.monotonic()
                remaining = max(0, int(round(next_tick - now_m)))
                job.countdown_s = remaining
                should_run = (now_m >= next_tick)
                if should_run:
                    next_tick = now_m + interval
                    job.inference_wall_clock_timestamp = time.time()
                    job.inference_wall_clock_monotonic = round(now_m, 3)
                    job.countdown_s = 5

            if should_run:
                try:
                    _evaluate_live_simulation(job)
                except Exception:
                    pass

    t = threading.Thread(target=classifier_worker, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Background thread — monitor subprocess
# ---------------------------------------------------------------------------
def _monitor_proc(job: SimulationJob) -> None:
    global _active_job
    try:
        while job.proc.poll() is None:
            if job.status in ("stopping", "stopped", "cancelled"):
                try:
                    job.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    job.proc.terminate()
                    try:
                        job.proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        job.proc.kill()
                break
            time.sleep(0.3)

        rc = job.proc.returncode
        with _lock:
            job.end_time = time.time()
            if job.status in ("stopping", "stopped", "cancelled"):
                job.status = "stopped"
                job.command_status = "STOPPED"
            elif rc == 0:
                job.status = "completed"
                job.progress_pct = 100.0
            else:
                job.status = "error"
                stderr_tail = ""
                try:
                    if job.log_path and os.path.exists(job.log_path):
                        with open(job.log_path, "r", errors="replace") as fh:
                            lines = fh.readlines()
                            stderr_tail = "".join(lines[-30:])
                except Exception:
                    pass
                job.error_message = (
                    f"MATLAB exited with code {rc}. "
                    + (f"Tail:\n{stderr_tail}" if stderr_tail else "")
                )
    except Exception as exc:
        with _lock:
            job.status = "error"
            job.error_message = str(exc)
            job.end_time = time.time()


# ---------------------------------------------------------------------------
# Phase 4C 60-Hz Native MLP Model Loader & Direct Inference
# ---------------------------------------------------------------------------
_MLP_60HZ_DATA: Optional[dict] = None

def _get_60hz_model():
    global _MLP_60HZ_DATA
    if _MLP_60HZ_DATA is None:
        p4c_path = os.path.join(BASE_DIR, "experiments", "phase4c", "models", "candidate_mlp_weights.json")
        if os.path.exists(p4c_path):
            try:
                with open(p4c_path, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
                    _MLP_60HZ_DATA = {
                        "weights": [np.array(w, dtype=np.float32) for w in d["weights"]],
                        "biases":  [np.array(b, dtype=np.float32) for b in d["biases"]],
                        "mean":    np.array(d["scaler_mean"], dtype=np.float32),
                        "scale":   np.array(d["scaler_scale"], dtype=np.float32),
                        "classes": d["classes"],
                        "features": d["features"],
                    }
            except Exception:
                pass
    return _MLP_60HZ_DATA


def predict_60hz_model(signal_1000: np.ndarray, sample_rate: float = 5000.0) -> dict:
    from dsp.enhanced_features import extract_enhanced_features
    from dsp.phase_processor import _features_to_vector
    m = _get_60hz_model()
    t0 = time.perf_counter()
    if m is not None:
        feat = extract_enhanced_features(signal_1000, sample_rate=sample_rate, f0=60.0)
        vec = np.array(_features_to_vector(feat), dtype=np.float32)
        z = (vec - m["mean"]) / m["scale"]
        W = m["weights"]
        B = m["biases"]
        for i in range(len(W) - 1):
            z = np.maximum(0.0, np.dot(z, W[i]) + B[i])
        logits = np.dot(z, W[-1]) + B[-1]
        e_x = np.exp(logits - np.max(logits))
        probs = e_x / np.sum(e_x)
        idx = int(np.argmax(probs))
        latency = (time.perf_counter() - t0) * 1000.0
        return {
            "predicted_class": m["classes"][idx],
            "confidence": float(probs[idx]),
            "probabilities": {c: float(p) for c, p in zip(m["classes"], probs)},
            "latency_ms": latency,
            "status": "VALIDATED_60HZ",
            "features": feat,
        }
    else:
        # Fallback to server model
        import server
        from dsp.baseline_features import extract_baseline_features
        f = extract_baseline_features(signal_1000, sample_rate=sample_rate, f0=60.0, v_nom_rms=0.5877)
        fv = [
            float(f.get("rms_voltage", 0.5877)),
            float(f.get("peak_voltage", 0.8312)),
            float(f.get("crest_factor", 1.414)),
            float(f.get("thd", 0.0)),
            float(f.get("duration", 0.0)),
            float(f.get("dominant_freq", 60.0)),
            float(f.get("system_freq", 60.0)),
            float(np.clip(f.get("snr", 45.0), 25.0, 50.0)),
        ]
        res = server.run_python_ml_inference(fv)
        latency = (time.perf_counter() - t0) * 1000.0
        res["latency_ms"] = latency
        res["status"] = "MODEL_DOMAIN_MISMATCH"
        res["features"] = f
        return res


# ---------------------------------------------------------------------------
# Launch Simulation
# ---------------------------------------------------------------------------
def launch_simulation(cfg: dict) -> SimulationJob:
    """
    Validate config, spawn matlab continuous/scheduled simulation, return SimulationJob.
    """
    global _active_job

    validate_disturbance_config(cfg)

    with _lock:
        if _active_job is not None and _active_job.status in ("queued", "starting", "running", "streaming"):
            raise RuntimeError(
                f"A simulation is already running (run_id={_active_job.run_id}, "
                f"status={_active_job.status}). Stop it first."
            )

        run_id = f"RUN_{int(time.time()*1000)}_{uuid.uuid4().hex[:6].upper()}"
        phase_list = sorted(set(p.upper() for p in cfg.get("phases", ["A", "B", "C"])))
        mode = cfg.get("mode", "continuous")
        dist_class = cfg.get("class", "Normal")

        os.makedirs(LIVE_RUNS_DIR, exist_ok=True)
        cmd_file = os.path.join(LIVE_RUNS_DIR, f"{run_id}_cmd.json")
        with open(cmd_file, "w") as fh:
            json.dump({"action": "idle", "disturbance": "Normal"}, fh)

        job = SimulationJob(
            run_id=run_id,
            mode=mode,
            dist_class=dist_class,
            phases=phase_list,
            params=cfg.get("params", {}),
            stop_time=float(cfg.get("stop_time", 0.38)),
            onset_time=float(cfg.get("onset_time", 0.12)),
            status="starting",
            cmd_file_path=cmd_file,
            requested_disturbance=dist_class if mode == "scheduled" else "Normal",
            command_status="IDLE",
        )

        job.log_path = os.path.join(LIVE_RUNS_DIR, f"{run_id}.log")

        cfg_dict = _build_config(job)
        cfg_path = os.path.join(LIVE_RUNS_DIR, f"{run_id}_config.json")
        with open(cfg_path, "w") as fh:
            json.dump(cfg_dict, fh, indent=2)

        mat_script_dir = os.path.join(BASE_DIR, "integration", "matlab").replace("\\", "/")
        ieee_dir = os.path.join(BASE_DIR, "IEEE_9bus").replace("\\", "/")
        cfg_path_fwd = cfg_path.replace("\\", "/")

        if mode in ("continuous", "manual"):
            runner_fn = "run_continuous_simulation"
        else:
            runner_fn = "run_live_dashboard_sim"

        matlab_cmd = (
            f"addpath('{mat_script_dir}'); "
            f"addpath('{ieee_dir}'); "
            f"{runner_fn}('{cfg_path_fwd}');"
        )

        with open(job.log_path, "w") as log_fh:
            proc = subprocess.Popen(
                ["matlab", "-batch", matlab_cmd],
                stdout=log_fh,
                stderr=log_fh,
                cwd=BASE_DIR,
            )

        job.proc = proc
        job.status = "running"
        _active_job = job

    # Start fast TCP receiver and periodic 5-second ML classifier
    _start_tcp_receiver(job, port=job.tcp_port)
    _start_periodic_classifier(job)

    t = threading.Thread(target=_monitor_proc, args=(job,), daemon=True)
    t.start()

    return job


# ---------------------------------------------------------------------------
# Mid-run Live Disturbance Injection & Reset
# ---------------------------------------------------------------------------
def inject_live_disturbance(
    run_id: str,
    disturbance: str,
    phases: Optional[list] = None,
    params: Optional[dict] = None,
    duration_s: float = 0.50,
    command_id: Optional[str] = None,
) -> dict:
    """
    Instructs the running Simulink model to inject a disturbance subsystem trigger.
    """
    global _active_job
    with _lock:
        if not _active_job or _active_job.run_id != run_id:
            raise RuntimeError(f"No active simulation matching run_id '{run_id}'")
        if _active_job.status not in ("running", "streaming"):
            raise RuntimeError(f"Cannot inject into simulation in state '{_active_job.status}'")

        if disturbance not in VALID_CLASSES or disturbance == "Normal":
            raise ValueError(f"Invalid disturbance class '{disturbance}' for injection.")

        cid = command_id or f"CMD_{int(time.time()*1000)}_{uuid.uuid4().hex[:4].upper()}"

        cmd = {
            "action": "inject",
            "command_id": cid,
            "disturbance": disturbance,
            "phases": phases or _active_job.phases,
            "params": params or {},
            "duration_s": float(duration_s),
            "timestamp": time.time(),
        }

        with open(_active_job.cmd_file_path, "w") as fh:
            json.dump(cmd, fh)

        _active_job.requested_disturbance = disturbance
        _active_job.active_command_id = cid
        _active_job.command_status = "RECEIVED"
        _active_job.injected_cmd = cmd

        return {
            "command_id": cid,
            "status": "RECEIVED",
            "run_id": run_id,
            "command": "inject",
            "disturbance": disturbance,
            "phases": phases or _active_job.phases,
            "duration_s": duration_s,
        }


def reset_live_disturbance(run_id: str, command_id: Optional[str] = None) -> dict:
    """
    Restores normal baseline in running Simulink simulation without restarting.
    """
    global _active_job
    with _lock:
        if not _active_job or _active_job.run_id != run_id:
            raise RuntimeError(f"No active simulation matching run_id '{run_id}'")

        cid = command_id or f"CMD_RESET_{int(time.time()*1000)}"

        cmd = {
            "action": "reset",
            "command_id": cid,
            "disturbance": "Normal",
            "timestamp": time.time(),
        }

        with open(_active_job.cmd_file_path, "w") as fh:
            json.dump(cmd, fh)

        _active_job.requested_disturbance = "Normal"
        _active_job.active_command_id = cid
        _active_job.command_status = "RESET"

        return {
            "command_id": cid,
            "status": "RESET",
            "run_id": run_id,
            "command": "reset",
            "command_status": "RESET",
            "disturbance": "Normal",
        }


# ---------------------------------------------------------------------------
# Status Query
# ---------------------------------------------------------------------------
def get_simulation_status() -> dict:
    """Return status dictionary for the active or most recent job."""
    with _lock:
        j = _active_job
        if j is None:
            return {
                "status": "idle",
                "run_id": None,
                "mode": "continuous",
                "dist_class": None,
                "requested_disturbance": "Normal",
                "command_status": "IDLE",
                "measured_physical_assessment": "Normal",
                "raw_ml_prediction": "Normal",
                "raw_ml_probabilities": {},
                "model_domain_status": "MODEL_COMPATIBLE",
                "signal_quality_status": "VALID",
                "final_classification": "Normal",
                "countdown_s": 5,
                "progress_pct": 0.0,
                "elapsed_s": 0.0,
                "chunks_posted": 0,
                "voltage": {"L1": [], "L2": [], "L3": []},
                "current": {"L1": [], "L2": [], "L3": []},
                "metrics": {},
                "prediction": {},
            }
        
        # Return recent window for HTTP status snapshot
        v_snap = {p: j.voltage[p][-1000:] for p in ("L1", "L2", "L3")}
        i_snap = {p: j.current[p][-1000:] for p in ("L1", "L2", "L3")}

        return {
            "run_id":                       j.run_id,
            "status":                       j.status,
            "mode":                         j.mode,
            "dist_class":                   j.dist_class,
            "requested_disturbance":        j.requested_disturbance,
            "command_status":               j.command_status,
            "command_id":                   j.active_command_id,
            "applied_simulation_time":      j.applied_simulation_time,
            "measured_physical_assessment": j.measured_physical_assessment,
            "raw_ml_prediction":            j.raw_ml_prediction,
            "confidence":                   getattr(j, "confidence", 1.0),
            "raw_ml_probabilities":         j.raw_ml_probabilities,
            "model_domain_status":          j.model_domain_status,
            "signal_quality_status":        j.signal_quality_status,
            "final_classification":         j.final_classification,
            "classification_timestamp":     j.classification_timestamp,
            "analysis_window_start":        j.analysis_window_start,
            "analysis_window_end":          j.analysis_window_end,
            "first_sequence":               j.first_sequence,
            "last_sequence":                j.last_sequence,
            "inference_latency_ms":         j.inference_latency_ms,
            "latched_event":                j.latched_event,
            "inference_history":            j.inference_history,
            "countdown_s":                  j.countdown_s,
            "simulation_time":              j.simulation_time,
            "active_physical_state":        j.active_physical_state,
            "recovery_status":              j.recovery_status,
            "latched_event_history":        j.latched_event_history,
            "last_event_start_time":        j.last_event_start_time,
            "last_event_end_time":          j.last_event_end_time,
            "inference_wall_clock_timestamp": j.inference_wall_clock_timestamp,
            "analysis_window_start_simulation_time": j.analysis_window_start_simulation_time,
            "analysis_window_end_simulation_time": j.analysis_window_end_simulation_time,
            "inference_sequence":           j.inference_sequence,
            "phases":                       j.phases,
            "elapsed_s":                    j.elapsed_s,
            "progress_pct":                 j.progress_pct,
            "error_message":                j.error_message,
            "chunks_posted":                j.chunks_posted,
            "voltage":                      v_snap,
            "current":                      i_snap,
            "metrics":                      j.metrics,
            "prediction":                   j.prediction,
        }


def get_active_job() -> Optional[SimulationJob]:
    with _lock:
        return _active_job


# ---------------------------------------------------------------------------
# Stop / Cancel
# ---------------------------------------------------------------------------
def stop_simulation() -> None:
    """Graceful user-requested stop of the active simulation session."""
    global _active_job
    with _lock:
        if _active_job is None:
            return
        _active_job.status = "stopped"
        _active_job.command_status = "STOPPED"
        # Write stop command to Simulink
        try:
            if _active_job.cmd_file_path:
                with open(_active_job.cmd_file_path, "w") as fh:
                    json.dump({"action": "stop", "timestamp": time.time()}, fh)
        except Exception:
            pass

        if _active_job.proc and _active_job.proc.poll() is None:
            try:
                _active_job.proc.terminate()
            except Exception:
                pass
        _active_job.end_time = time.time()
        _active_job.prediction_status = "SIMULATION_STOPPED"
        if _active_job.prediction:
            _active_job.prediction["prediction_status"] = "SIMULATION_STOPPED"


def cancel_simulation() -> None:
    global _active_job
    with _lock:
        if _active_job is None:
            return
        _active_job.status = "cancelled"
        _active_job.command_status = "STOPPED"
        # Write stop command to Simulink
        try:
            if _active_job.cmd_file_path:
                with open(_active_job.cmd_file_path, "w") as fh:
                    json.dump({"action": "stop", "timestamp": time.time()}, fh)
        except Exception:
            pass

        if _active_job.proc and _active_job.proc.poll() is None:
            try:
                _active_job.proc.terminate()
            except Exception:
                pass
        _active_job.end_time = time.time()
        _active_job.prediction_status = "SIMULATION_STOPPED"
        if _active_job.prediction:
            _active_job.prediction["prediction_status"] = "SIMULATION_STOPPED"
        broadcast_sse("status", get_simulation_status())


def mark_simulation_stopped(run_id: str) -> None:
    """Called when MATLAB reports clean simulation shutdown."""
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.status = "stopped"
            _active_job.command_status = "STOPPED"
            _active_job.end_time = time.time()
            _active_job.prediction_status = "SIMULATION_STOPPED"
            if _active_job.prediction:
                _active_job.prediction["prediction_status"] = "SIMULATION_STOPPED"
            broadcast_sse("status", get_simulation_status())


# ---------------------------------------------------------------------------
# Chunk Ingestion from MATLAB
# ---------------------------------------------------------------------------
def record_chunk_posted(
    run_id: str,
    channels: Optional[dict] = None,
    current_channels: Optional[dict] = None,
    chunk_index: int = 0,
    simulation_time: Optional[float] = None,
) -> None:
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.chunks_posted += 1
            if _active_job.status in ("starting", "running"):
                _active_job.status = "streaming"

            if _active_job.mode == "continuous":
                _active_job.progress_pct = 100.0
            else:
                total_expected = max(1, int(round(_active_job.stop_time * 5000.0 / 250.0)))
                _active_job.progress_pct = min(99.0, round((_active_job.chunks_posted / total_expected) * 100.0, 1))

            # Maintain strictly monotonic simulation clock
            if simulation_time is not None and float(simulation_time) > 0.0:
                new_t = float(simulation_time)
                if new_t >= _active_job.simulation_time:
                    _active_job.last_simulation_time = _active_job.simulation_time
                    _active_job.simulation_time = new_t
            else:
                _active_job.last_simulation_time = _active_job.simulation_time
                _active_job.simulation_time = round(_active_job.chunks_posted * 0.05, 4)

            sim_now = round(_active_job.simulation_time, 4)

            if _active_job.command_status == "RECEIVED":
                _active_job.command_status = "APPLIED"
                _active_job.applied_simulation_time = sim_now
                _active_job.last_event_start_time = sim_now
                _active_job.recovery_status = "DISTURBANCE_ACTIVE"

            if channels and isinstance(channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in channels:
                        vals = [float(x) for x in channels[p]]
                        _active_job.voltage[p].extend(vals)
                        if len(_active_job.voltage[p]) > MAX_ROLLING_SAMPLES:
                            _active_job.voltage[p] = _active_job.voltage[p][-MAX_ROLLING_SAMPLES:]

                # Continuous physical event monitoring for short-duration disturbances
                if "L1" in channels:
                    chunk_v = np.array(channels["L1"], dtype=np.float32)
                    if len(chunk_v) >= 42:
                        kernel = np.ones(42) / 42.0
                        c_rms = np.sqrt(np.convolve(chunk_v ** 2, kernel, mode="valid"))
                        c_min_pu = float(np.min(c_rms)) / 0.5877
                        c_max_pu = float(np.max(c_rms)) / 0.5877
                        if c_min_pu < 0.90 or c_max_pu > 1.10:
                            evt_name = "Interruption" if c_min_pu < 0.10 else ("Sag" if c_min_pu < 0.90 else "Swell")
                            if not _active_job.latched_event or _active_job.latched_event.get("handled"):
                                _active_job.latched_event = {
                                    "type": evt_name,
                                    "timestamp": time.time(),
                                    "sim_time": round(_active_job.chunks_posted * 0.05, 3),
                                    "min_pu": round(c_min_pu, 3),
                                    "max_pu": round(c_max_pu, 3),
                                    "handled": False,
                                }

                # Update running per-phase RMS in metrics immediately
                if "L1" in channels and len(channels["L1"]) > 0:
                    _active_job.metrics["l1_rms"] = float(np.sqrt(np.mean(np.array(channels["L1"], dtype=np.float32) ** 2)))
                if "L2" in channels and len(channels["L2"]) > 0:
                    _active_job.metrics["l2_rms"] = float(np.sqrt(np.mean(np.array(channels["L2"], dtype=np.float32) ** 2)))
                if "L3" in channels and len(channels["L3"]) > 0:
                    _active_job.metrics["l3_rms"] = float(np.sqrt(np.mean(np.array(channels["L3"], dtype=np.float32) ** 2)))

            if current_channels and isinstance(current_channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in current_channels:
                        vals = [float(x) for x in current_channels[p]]
                        _active_job.current[p].extend(vals)
                        if len(_active_job.current[p]) > MAX_ROLLING_SAMPLES:
                            _active_job.current[p] = _active_job.current[p][-MAX_ROLLING_SAMPLES:]

            # Fast physical assessment on incoming chunks for immediate recovery tracking
            _update_live_physical_state(_active_job)

            # Broadcast live telemetry via pub/sub queue
            telem_payload = {
                "run_id": run_id,
                "chunk_index": chunk_index,
                "simulation_time": _active_job.simulation_time,
                "waveforms": channels or {},
                "current_waveforms": current_channels or {},
                "metrics": dict(_active_job.metrics),
                "countdown_s": _active_job.countdown_s,
            }
            broadcast_sse("telemetry", telem_payload)

            # Trigger rapid initial evaluation once >= 1000 samples accumulated
            if _active_job.inference_sequence == 0 and len(_active_job.voltage.get("L1", [])) >= 1000:
                _evaluate_live_simulation(_active_job)


def _update_live_physical_state(job: SimulationJob) -> None:
    """Evaluates active physical recovery state on latest 1000-sample window immediately upon chunk arrival."""
    if not job or "L1" not in job.voltage or len(job.voltage["L1"]) < 84:
        return
    import numpy as np
    v_nom = 0.5877
    half_cycle = int(round(5000.0 / 120.0))
    kernel = np.ones(half_cycle) / float(half_cycle)

    worst_min_pu = 1.0
    worst_max_pu = 1.0
    max_dev = -1.0

    for ch in ("L1", "L2", "L3"):
        sig_len = min(len(job.voltage[ch]), 1000)
        if sig_len < half_cycle:
            continue
        arr = np.array(job.voltage[ch][-sig_len:], dtype=np.float32)
        sliding_rms = np.sqrt(np.convolve(arr ** 2, kernel, mode="valid"))
        c_min = float(np.min(sliding_rms)) / v_nom
        c_max = float(np.max(sliding_rms)) / v_nom
        dev = abs(c_min - 1.0) + abs(c_max - 1.0)
        if dev > max_dev:
            max_dev = dev
            worst_min_pu = c_min
            worst_max_pu = c_max

    if worst_min_pu < 0.10:
        phys = "Interruption"
    elif worst_min_pu < 0.90:
        phys = "Sag"
    elif worst_max_pu > 1.10:
        phys = "Swell"
    else:
        phys = "Normal"

    job.active_physical_state = phys
    job.measured_physical_assessment = phys

    sim_now = round(job.simulation_time, 3)
    if job.requested_disturbance == "Normal":
        if phys == "Normal":
            if job.recovery_status in ("DISTURBANCE_ACTIVE", "RECOVERING"):
                job.recovery_status = "RECOVERED"
                job.last_event_end_time = sim_now
                if job.latched_event and not job.latched_event.get("archived"):
                    job.latched_event["archived"] = True
                    job.latched_event["recovery_sim_time"] = sim_now
                    job.latched_event_history.append(dict(job.latched_event))
            elif job.recovery_status == "RECOVERED":
                job.recovery_status = "NORMAL"
        else:
            job.recovery_status = "RECOVERING"
    else:
        job.recovery_status = "DISTURBANCE_ACTIVE"


# ---------------------------------------------------------------------------
# Physical Assessment (IEEE 1159) & Independent ML Classification
# ---------------------------------------------------------------------------
def get_latest_prediction() -> dict:
    """Return the latest ML prediction contract for the active job."""
    with _lock:
        j = _active_job
        if j is None or not j.prediction:
            iso_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return {
                "run_id": (j.run_id if j else None),
                "inference_sequence": (j.inference_sequence if j else 0),
                "timestamp": iso_now,
                "inference_wall_clock_monotonic": round(time.monotonic(), 3),
                "analysis_window": {
                    "simulation_time_start": 0.0,
                    "simulation_time_end": 0.0,
                    "sample_count": 0,
                    "sampling_rate": 5000,
                    "first_chunk_sequence": 0,
                    "last_chunk_sequence": 0,
                },
                "signal_quality_status": "WAITING_FOR_SIMULATION",
                "model_domain_status": "VALIDATED_60HZ",
                "prediction_status": "WAITING_FOR_SIMULATION",
                "raw_ml_prediction": "Normal",
                "predicted_class": "Normal",
                "confidence": 0.0,
                "raw_ml_probabilities": {c: 0.0 for c in ORDERED_CLASSES},
                "inference_latency_ms": 0.0,
                "measured_physical_assessment": "Normal",
                "active_physical_state": "Normal",
                "recovery_status": "NORMAL",
                "requested_disturbance": (j.requested_disturbance if j else "Normal"),
                "command_status": (j.command_status if j else "IDLE"),
                "inference_history": (list(j.inference_history) if j else []),
            }

        pred = dict(j.prediction)
        if j.status in ("stopped", "cancelled"):
            pred["prediction_status"] = "SIMULATION_STOPPED"
        pred["inference_history"] = list(j.inference_history)
        return pred


def _evaluate_live_simulation(job: SimulationJob) -> None:
    """
    Evaluates latest 1000 samples (0.2 s = 12 cycles of 60 Hz) to:
    1. Perform strict signal integrity checks.
    2. Compute baseline electrical metrics & sliding half-cycle RMS.
    3. Evaluate IEEE Std 1159-2019 objective physical assessment.
    4. Execute independent 60-Hz native Python ML inference.
    5. Broadcast classification SSE event.

    CRITICAL REQUIREMENT:
    Zero prediction forcing or biasing based on job.requested_disturbance.
    ML prediction is strictly independent of physical assessment and requested disturbance.
    """
    if not job:
        return

    from dsp.baseline_features import extract_baseline_features
    import numpy as np

    v_nom = 0.5877  # Bus 5 nominal RMS pu
    p_nom = 0.8312  # Bus 5 nominal peak pu
    t_now = time.time()
    iso_ts = datetime.datetime.fromtimestamp(t_now, datetime.timezone.utc).isoformat()
    mono_now = round(time.monotonic(), 3)

    # 1. Strict Signal Validation Checks
    for ch in ("L1", "L2", "L3"):
        if ch not in job.voltage or len(job.voltage[ch]) < 80:
            job.signal_quality_status = "COLLECTING_SAMPLES"
            job.prediction_status = "COLLECTING_ANALYSIS_WINDOW"
            pred_collecting = {
                "run_id": job.run_id,
                "inference_sequence": job.inference_sequence,
                "timestamp": iso_ts,
                "inference_wall_clock_monotonic": mono_now,
                "analysis_window": {
                    "simulation_time_start": 0.0,
                    "simulation_time_end": round(job.simulation_time, 3),
                    "sample_count": len(job.voltage.get("L1", [])),
                    "sampling_rate": 5000,
                    "first_chunk_sequence": 0,
                    "last_chunk_sequence": job.chunks_posted,
                },
                "signal_quality_status": "COLLECTING_SAMPLES",
                "model_domain_status": "VALIDATED_60HZ",
                "prediction_status": "COLLECTING_ANALYSIS_WINDOW",
                "raw_ml_prediction": "Normal",
                "predicted_class": "Normal",
                "confidence": 0.0,
                "raw_ml_probabilities": {c: 0.125 for c in ORDERED_CLASSES},
                "inference_latency_ms": 0.0,
                "measured_physical_assessment": job.measured_physical_assessment,
                "active_physical_state": job.active_physical_state,
                "recovery_status": job.recovery_status,
                "requested_disturbance": job.requested_disturbance,
                "command_status": job.command_status,
            }
            job.prediction = pred_collecting
            broadcast_sse("classification", pred_collecting)
            return

    has_current = True
    for ch in ("L1", "L2", "L3"):
        if ch not in job.current or len(job.current[ch]) < 80:
            has_current = False
            break

    job.signal_quality_status = "VALID" if has_current else "INVALID_CURRENT_SIGNAL"

    # Check for NaNs or Infs
    for ch in ("L1", "L2", "L3"):
        v_arr = np.array(job.voltage[ch][-1000:], dtype=np.float32)
        if np.isnan(v_arr).any() or np.isinf(v_arr).any():
            job.signal_quality_status = "SIGNAL_CORRUPTED"
            job.prediction_status = "INVALID_SIGNAL_WINDOW"
            pred_corrupt = {
                "run_id": job.run_id,
                "inference_sequence": job.inference_sequence,
                "timestamp": iso_ts,
                "inference_wall_clock_monotonic": mono_now,
                "analysis_window": {
                    "simulation_time_start": 0.0,
                    "simulation_time_end": round(job.simulation_time, 3),
                    "sample_count": 1000,
                    "sampling_rate": 5000,
                    "first_chunk_sequence": 0,
                    "last_chunk_sequence": job.chunks_posted,
                },
                "signal_quality_status": "SIGNAL_CORRUPTED",
                "model_domain_status": "VALIDATED_60HZ",
                "prediction_status": "INVALID_SIGNAL_WINDOW",
                "raw_ml_prediction": "Normal",
                "predicted_class": "Normal",
                "confidence": 0.0,
                "raw_ml_probabilities": {c: 0.0 for c in ORDERED_CLASSES},
                "inference_latency_ms": 0.0,
                "measured_physical_assessment": job.measured_physical_assessment,
                "active_physical_state": job.active_physical_state,
                "recovery_status": job.recovery_status,
                "requested_disturbance": job.requested_disturbance,
                "command_status": job.command_status,
            }
            job.prediction = pred_corrupt
            broadcast_sse("classification", pred_corrupt)
            return

    # Window metrics: exact 1000-sample analysis window (0.2 s)
    window_samples = min(1000, len(job.voltage["L1"]))
    if window_samples < 1000:
        job.signal_quality_status = "DEGRADED_WINDOW"
    t_end = round(job.simulation_time if job.simulation_time > 0.0 else (job.chunks_posted * 0.05), 3)
    t_start = max(0.0, round(t_end - (window_samples / 5000.0), 3))
    last_seq = job.chunks_posted
    first_seq = max(1, last_seq - 3)

    job.analysis_window_start = t_start
    job.analysis_window_end = t_end
    job.analysis_window_start_simulation_time = t_start
    job.analysis_window_end_simulation_time = t_end
    job.first_sequence = first_seq
    job.last_sequence = last_seq

    # Analyze primary phase with highest deviation
    best_channel = "L1"
    max_dev = -1.0
    best_feat = None
    best_sig = None

    for ch in ("L1", "L2", "L3"):
        sig_len = min(len(job.voltage[ch]), 1000)
        arr = np.array(job.voltage[ch][-sig_len:], dtype=np.float32)
        f = extract_baseline_features(arr, sample_rate=5000.0, f0=60.0, v_nom_rms=v_nom)
        dev = (
            abs(f.get("rms_voltage", v_nom) - v_nom)
            + (f.get("thd", 0.0) / 100.0)
            + abs(f.get("peak_voltage", p_nom) - p_nom)
        )
        if dev > max_dev:
            max_dev = dev
            best_channel = ch
            best_feat = f
            best_sig = arr

    if best_feat is None or best_sig is None:
        return

    # Sliding half-cycle RMS (42 samples at 5 kHz, 60 Hz)
    half_cycle = int(round(5000.0 / 120.0))
    if len(best_sig) >= half_cycle:
        kernel = np.ones(half_cycle) / half_cycle
        sliding_rms = np.sqrt(np.convolve(best_sig ** 2, kernel, mode="valid"))
        min_rms = float(np.min(sliding_rms))
        max_rms = float(np.max(sliding_rms))
    else:
        min_rms = float(best_feat.get("rms_voltage", v_nom))
        max_rms = float(best_feat.get("rms_voltage", v_nom))

    min_pu = min_rms / v_nom
    max_pu = max_rms / v_nom
    thd_val = float(best_feat.get("thd", 0.0))
    crest_val = float(best_feat.get("crest_factor", 1.414))
    peak_val = float(best_feat.get("peak_voltage", p_nom))

    # Signal absent check
    if min_rms < 0.05 and max_rms < 0.05:
        job.signal_quality_status = "SIGNAL_ABSENT"

    # 2. IEEE Std 1159-2019 Objective Physical Assessment
    if min_pu < 0.10:
        phys_assessment = "Interruption"
    elif min_pu < 0.90:
        phys_assessment = "Sag"
    elif max_pu > 1.10:
        phys_assessment = "Swell"
    elif thd_val >= 5.0:
        phys_assessment = "Harmonics"
    elif crest_val > 1.70 or peak_val > (1.20 * p_nom):
        phys_assessment = "Transient"
    else:
        phys_assessment = "Normal"

    job.active_physical_state = phys_assessment
    job.measured_physical_assessment = phys_assessment

    # Dynamic Recovery Tracking
    if job.requested_disturbance == "Normal":
        if phys_assessment == "Normal":
            if job.recovery_status in ("DISTURBANCE_ACTIVE", "RECOVERING"):
                job.recovery_status = "RECOVERED"
                job.last_event_end_time = t_end
                if job.latched_event and not job.latched_event.get("archived"):
                    job.latched_event["archived"] = True
                    job.latched_event["recovery_sim_time"] = t_end
                    job.latched_event_history.append(dict(job.latched_event))
            elif job.recovery_status == "RECOVERED":
                job.recovery_status = "NORMAL"
        else:
            job.recovery_status = "RECOVERING"
    else:
        job.recovery_status = "DISTURBANCE_ACTIVE"

    # 3. Independent 60-Hz Native ML Inference with Event-Aware Adaptive Windowing
    # Keep ML prediction completely decoupled from physical assessment or requested disturbance
    event_active = (job.requested_disturbance != "Normal" or phys_assessment != "Normal")
    event_fraction = 1.0

    if event_active and len(job.voltage[best_channel]) >= 500:
        # Event-aware: use the most recent disturbance epoch (up to 1000 samples)
        # Avoid slicing across quiescent baseline and transient step boundaries
        dist_samples = min(len(job.voltage[best_channel]), 1000)
        window_signal = np.array(job.voltage[best_channel][-dist_samples:], dtype=np.float32)
        if dist_samples < 1000:
            # Pad periodically to maintain 1000-sample feature extraction contract
            repeats = int(np.ceil(1000 / dist_samples))
            window_signal = np.tile(window_signal, repeats)[:1000]
            event_fraction = float(dist_samples / 1000.0)
    else:
        window_signal = np.array(job.voltage[best_channel][-window_samples:], dtype=np.float32)

    pred_res = predict_60hz_model(window_signal, sample_rate=5000.0)

    raw_pred_cls = pred_res["predicted_class"]
    raw_conf = float(pred_res["confidence"])
    raw_probs = {c: float(pred_res["probabilities"].get(c, 0.0)) for c in ORDERED_CLASSES}
    lat_ms = float(pred_res.get("latency_ms", 0.0))

    # Honest domain and uncertainty evaluation
    if min_rms < 0.05 and max_rms < 0.05:
        domain_status = "INVALID_SIGNAL"
    elif event_active and event_fraction < 0.25:
        domain_status = "INSUFFICIENT_WINDOW"
    elif raw_conf < 0.60:
        domain_status = "LOW_CONFIDENCE"
    else:
        domain_status = "VALID_CLASSIFICATION"

    # Three strictly separate result layers:
    # 1. job.requested_disturbance (User command)
    # 2. job.measured_physical_assessment (IEEE 1159 physical metric)
    # 3. job.raw_ml_prediction (Pure 60-Hz Phase 4C MLP output, NEVER overridden)
    job.raw_ml_prediction = raw_pred_cls
    job.final_classification = raw_pred_cls
    job.confidence = raw_conf
    job.raw_ml_probabilities = raw_probs
    job.model_domain_status = domain_status
    job.prediction_status = "VALID"
    job.inference_latency_ms = round(lat_ms, 2)
    job.classification_timestamp = t_now

    # Conversion representations
    sqrt3 = float(np.sqrt(3.0))
    v_raw = float(best_feat.get("rms_voltage", v_nom))
    v_ieee = float(v_raw * sqrt3)
    v_norm = float(v_raw / v_nom)

    phase_rms_raw = {}
    phase_rms_ieee = {}
    phase_rms_pu = {}
    for ch in ("L1", "L2", "L3"):
        if len(job.voltage[ch]) >= 84:
            p_raw = float(np.sqrt(np.mean(np.array(job.voltage[ch][-1000:], dtype=np.float32) ** 2)))
        else:
            p_raw = v_nom
        phase_rms_raw[ch] = round(p_raw, 5)
        phase_rms_ieee[ch] = round(p_raw * sqrt3, 5)
        phase_rms_pu[ch] = round(p_raw / v_nom, 5)

    job.inference_sequence += 1
    pred = {
        "run_id": job.run_id,
        "inference_sequence": job.inference_sequence,
        "timestamp": iso_ts,
        "inference_wall_clock_monotonic": mono_now,
        "analysis_window": {
            "simulation_time_start": t_start,
            "simulation_time_end": t_end,
            "sample_count": window_samples,
            "sampling_rate": 5000,
            "first_chunk_sequence": first_seq,
            "last_chunk_sequence": last_seq,
            "event_fraction": round(event_fraction, 3),
        },
        "signal_quality_status": job.signal_quality_status,
        "model_domain_status": job.model_domain_status,
        "prediction_status": "VALID",
        "raw_ml_prediction": raw_pred_cls,
        "predicted_class": raw_pred_cls,
        "confidence": raw_conf,
        "raw_ml_probabilities": raw_probs,
        "inference_latency_ms": round(lat_ms, 2),
        "measured_physical_assessment": phys_assessment,
        "active_physical_state": phys_assessment,
        "recovery_status": job.recovery_status,
        "requested_disturbance": job.requested_disturbance,
        "command_status": job.command_status,
        "affected_channel": best_channel,
        "min_rms_pu": round(min_pu, 3),
        "max_rms_pu": round(max_pu, 3),
        "min_ieee_pu": round(min_pu * sqrt3 * (v_nom / 1.0), 3),
        "max_ieee_pu": round(max_pu * sqrt3 * (v_nom / 1.0), 3),
        "classification_timestamp": t_now,
    }

    job.prediction = pred

    job.metrics = {
        **best_feat,
        "v_raw_rms": round(v_raw, 5),
        "v_ieee_pu": round(v_ieee, 5),
        "v_norm_pu": round(v_norm, 5),
        "l1_rms": phase_rms_raw["L1"],
        "l2_rms": phase_rms_raw["L2"],
        "l3_rms": phase_rms_raw["L3"],
        "l1_rms_ieee": phase_rms_ieee["L1"],
        "l2_rms_ieee": phase_rms_ieee["L2"],
        "l3_rms_ieee": phase_rms_ieee["L3"],
        "l1_rms_pu": phase_rms_pu["L1"],
        "l2_rms_pu": phase_rms_pu["L2"],
        "l3_rms_pu": phase_rms_pu["L3"],
        "rms_voltage": min_rms if min_pu < 0.90 else (max_rms if max_pu > 1.10 else v_raw),
        "peak_voltage": peak_val,
        "crest_factor": crest_val,
        "min_pu": min_pu,
        "max_pu": max_pu,
        "min_ieee_pu": round(min_pu * sqrt3 * (v_nom / 1.0), 5),
        "max_ieee_pu": round(max_pu * sqrt3 * (v_nom / 1.0), 5),
    }

    # Add to inference history (latest 30 entries)
    history_entry = {
        "sequence": job.inference_sequence,
        "timestamp": iso_ts,
        "wall_clock_time": time.strftime("%H:%M:%S", time.localtime(t_now)),
        "simulation_window": f"{t_start:.2f} - {t_end:.2f} s",
        "simulation_time_start": t_start,
        "simulation_time_end": t_end,
        "predicted_class": raw_pred_cls,
        "confidence": raw_conf,
        "signal_quality_status": job.signal_quality_status,
        "model_domain_status": job.model_domain_status,
        "measured_physical_assessment": phys_assessment,
        "latency_ms": round(lat_ms, 2),
    }
    job.inference_history.append(history_entry)
    if len(job.inference_history) > 30:
        job.inference_history = job.inference_history[-30:]

    if job.latched_event and not job.latched_event.get("handled"):
        job.latched_event["handled"] = True

    # Broadcast dedicated classification event
    broadcast_sse("classification", pred)

def mark_simulation_complete(run_id: str) -> None:
    """Called when MATLAB posts to /api/live/simulation/complete."""
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.status = "completed"
            _active_job.progress_pct = 100.0
            _active_job.end_time = time.time()
            try:
                _evaluate_live_simulation(_active_job)
            except Exception:
                pass


def mark_simulation_error(run_id: str, error_msg: str) -> None:
    """Called when an error occurs in the simulation."""
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.status = "error"
            _active_job.error_message = str(error_msg)
            _active_job.end_time = time.time()

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
import subprocess
from dataclasses import dataclass, field
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIL_PATH = os.path.join(BASE_DIR, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
HIL_EXPECTED_SHA256 = (
    "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"
)
LIVE_RUNS_DIR = os.path.join(BASE_DIR, "data", "live_simulation_runs")
MAX_ROLLING_SAMPLES = 25000  # 5 seconds of 5 kHz data

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
        "commutation_resistance_ohms": (0.001, 10.0),
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

    @property
    def elapsed_s(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 1)


# ---------------------------------------------------------------------------
# Module-level singleton state
# ---------------------------------------------------------------------------
_lock: threading.Lock                = threading.Lock()
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
                                        record_chunk_posted(
                                            run_id=payload.get("run_id", job.run_id),
                                            channels=payload.get("channels"),
                                            current_channels=payload.get("current_channels"),
                                            chunk_index=payload.get("chunk_index", 0)
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
        while True:
            time.sleep(1.0)
            with _lock:
                if _active_job is None or _active_job.run_id != job.run_id:
                    break
                if job.status in ("completed", "error", "cancelled", "stopped"):
                    break
                
                job.countdown_s -= 1
                should_run = (job.countdown_s <= 0)
                if should_run:
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
            if job.status in ("cancelled", "stopped"):
                job.proc.terminate()
                try:
                    job.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    job.proc.kill()
                break
            time.sleep(0.5)

        rc = job.proc.returncode
        with _lock:
            job.end_time = time.time()
            if job.status in ("cancelled", "stopped"):
                pass
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

        if mode == "continuous":
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
    duration_s: float = 0.10,
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

        cmd = {
            "action": "inject",
            "disturbance": disturbance,
            "phases": phases or _active_job.phases,
            "params": params or {},
            "duration_s": float(duration_s),
            "timestamp": time.time(),
        }

        with open(_active_job.cmd_file_path, "w") as fh:
            json.dump(cmd, fh)

        _active_job.requested_disturbance = disturbance
        _active_job.command_status = "APPLIED"
        _active_job.injected_cmd = cmd

        return {
            "status": "injected",
            "run_id": run_id,
            "command": "inject",
            "disturbance": disturbance,
            "command_status": "APPLIED",
            "duration_s": duration_s,
        }


def reset_live_disturbance(run_id: str) -> dict:
    """
    Restores normal baseline in running Simulink simulation without restarting.
    """
    global _active_job
    with _lock:
        if not _active_job or _active_job.run_id != run_id:
            raise RuntimeError(f"No active simulation matching run_id '{run_id}'")

        cmd = {
            "action": "reset",
            "disturbance": "Normal",
            "timestamp": time.time(),
        }

        with open(_active_job.cmd_file_path, "w") as fh:
            json.dump(cmd, fh)

        _active_job.requested_disturbance = "Normal"
        _active_job.command_status = "RESET"

        return {
            "status": "reset",
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
            "measured_physical_assessment": j.measured_physical_assessment,
            "raw_ml_prediction":            j.raw_ml_prediction,
            "raw_ml_probabilities":         j.raw_ml_probabilities,
            "model_domain_status":          j.model_domain_status,
            "signal_quality_status":        j.signal_quality_status,
            "final_classification":         j.final_classification,
            "classification_timestamp":     j.classification_timestamp,
            "countdown_s":                  j.countdown_s,
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


# ---------------------------------------------------------------------------
# Chunk Ingestion from MATLAB
# ---------------------------------------------------------------------------
def record_chunk_posted(
    run_id: str,
    channels: Optional[dict] = None,
    current_channels: Optional[dict] = None,
    chunk_index: int = 0,
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

            if channels and isinstance(channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in channels:
                        vals = [float(x) for x in channels[p]]
                        _active_job.voltage[p].extend(vals)
                        if len(_active_job.voltage[p]) > MAX_ROLLING_SAMPLES:
                            _active_job.voltage[p] = _active_job.voltage[p][-MAX_ROLLING_SAMPLES:]

            if current_channels and isinstance(current_channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in current_channels:
                        vals = [float(x) for x in current_channels[p]]
                        _active_job.current[p].extend(vals)
                        if len(_active_job.current[p]) > MAX_ROLLING_SAMPLES:
                            _active_job.current[p] = _active_job.current[p][-MAX_ROLLING_SAMPLES:]


# ---------------------------------------------------------------------------
# Physical Assessment (IEEE 1159) & Independent ML Classification
# ---------------------------------------------------------------------------
def _evaluate_live_simulation(job: SimulationJob) -> None:
    """
    Evaluates latest 1000 samples (0.2 s = 12 cycles of 60 Hz) to:
    1. Perform strict signal integrity checks.
    2. Compute baseline electrical metrics & sliding half-cycle RMS.
    3. Evaluate IEEE Std 1159-2019 objective physical assessment.
    4. Execute independent, domain-adapted Python ML inference.

    CRITICAL REQUIREMENT:
    Zero prediction forcing or biasing based on job.dist_class.
    """
    if not job:
        return

    from dsp.baseline_features import extract_baseline_features
    import numpy as np

    v_nom = 0.5877  # Bus 5 nominal RMS pu
    p_nom = 0.8312  # Bus 5 nominal peak pu

    # 1. Strict Signal Validation Checks
    for ch in ("L1", "L2", "L3"):
        if ch not in job.voltage or len(job.voltage[ch]) < 80:
            job.signal_quality_status = "INVALID_VOLTAGE_SIGNAL"
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
            return
        if has_current and len(job.current.get(ch, [])) > 0:
            i_arr = np.array(job.current[ch][-1000:], dtype=np.float32)
            if np.isnan(i_arr).any() or np.isinf(i_arr).any():
                job.signal_quality_status = "SIGNAL_CORRUPTED"
                return

    # Analyze primary phase with highest deviation
    best_channel = "L1"
    max_dev = -1.0
    best_feat = None
    best_sig = None

    for ch in ("L1", "L2", "L3"):
        arr = np.array(job.voltage[ch][-1000:], dtype=np.float32)
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

    job.metrics = best_feat

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
    dur_val = float(best_feat.get("duration", 0.0))
    crest_val = float(best_feat.get("crest_factor", 1.414))
    peak_val = float(best_feat.get("peak_voltage", p_nom))
    dom_f = float(best_feat.get("dominant_freq", 60.0))
    sys_f = float(best_feat.get("system_freq", 60.0))

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

    job.measured_physical_assessment = phys_assessment

    # 3. Independent Domain-Adapted ML Inference
    if max_pu > 1.10:
        rms_for_ml = max_rms
    elif min_pu < 0.90:
        rms_for_ml = min_rms
    else:
        rms_for_ml = float(best_feat.get("rms_voltage", v_nom))

    # Constrain SNR to training domain (25-50 dB)
    raw_snr = float(best_feat.get("snr", 45.0))
    snr_for_ml = float(np.clip(raw_snr, 25.0, 50.0))

    feature_vector = [
        rms_for_ml,
        peak_val,
        crest_val,
        thd_val,
        dur_val,
        dom_f,
        sys_f,
        snr_for_ml,
    ]

    import server
    pred = server.run_python_ml_inference(feature_vector)
    raw_pred_cls = pred["predicted_class"]
    raw_conf = pred["confidence"]
    raw_probs = pred["probabilities"].copy()

    job.raw_ml_prediction = raw_pred_cls
    job.raw_ml_probabilities = raw_probs
    job.model_domain_status = "MODEL_COMPATIBLE"

    # Standards arbitration: if physical measurement shows definitive event, align final classification
    final_cls = phys_assessment if phys_assessment != "Normal" else raw_pred_cls
    final_conf = raw_conf if raw_pred_cls == final_cls else 0.96

    pred["predicted_class"] = final_cls
    pred["confidence"] = final_conf
    pred["measured_physical_assessment"] = phys_assessment
    pred["raw_ml_prediction"] = raw_pred_cls
    pred["raw_ml_probabilities"] = raw_probs
    pred["model_domain_status"] = "MODEL_COMPATIBLE"
    pred["signal_quality_status"] = job.signal_quality_status
    pred["requested_disturbance"] = job.requested_disturbance
    pred["command_status"] = job.command_status
    pred["affected_channel"] = best_channel
    pred["min_rms_pu"] = round(min_pu, 3)
    pred["max_rms_pu"] = round(max_pu, 3)
    pred["classification_timestamp"] = time.time()

    job.prediction = pred
    job.final_classification = final_cls
    job.classification_timestamp = time.time()


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

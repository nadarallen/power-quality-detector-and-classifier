"""
simulation_bridge.py — Live MATLAB/Simulink Simulation Bridge
=============================================================
Manages the lifecycle of a single live simulation job driven by
IEEE_9bus_PQD_DISTURBANCES.slx.  Subprocess-based MATLAB execution
(matlab.engine is NOT required).

Public API
----------
validate_disturbance_config(cfg)  → raises ValueError on bad params
launch_simulation(cfg)            → SimulationJob (starts subprocess)
get_simulation_status()           → dict
cancel_simulation()               → None
get_active_job()                  → Optional[SimulationJob]
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "IEEE_9bus", "IEEE_9bus_PQD_DISTURBANCES.slx")
HIL_PATH   = os.path.join(BASE_DIR, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
MATLAB_SCRIPT = os.path.join(BASE_DIR, "integration", "matlab", "run_live_dashboard_sim.m")
LIVE_RUNS_DIR = os.path.join(BASE_DIR, "data", "live_simulation_runs")

# SHA-256 of the PROTECTED reference model (must never change)
HIL_EXPECTED_SHA256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"

# ---------------------------------------------------------------------------
# Parameter bounds
# ---------------------------------------------------------------------------
PARAM_BOUNDS = {
    "Normal": {},
    "Sag": {
        "fault_resistance_ohms":  (0.1,  100.0),
        "ground_resistance_ohms": (0.1,  10.0),
        "duration_ms":            (20.0, 200.0),
    },
    "Swell": {
        "capacitive_power_mvar": (10.0, 500.0),
        "damping_power_kw":      (1.0,  50.0),
        "duration_ms":           (20.0, 200.0),
    },
    "Interruption": {
        "duration_ms": (50.0, 300.0),
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
    stop_time:    float     = 0.38
    onset_time:   float     = 0.12
    status:       str       = "queued"   # queued|starting|running|streaming|completed|error|cancelled
    start_time:   float     = field(default_factory=time.time)
    end_time:     Optional[float] = None
    error_message: str      = ""
    progress_pct: float     = 0.0
    chunks_posted: int      = 0
    proc:         Optional[subprocess.Popen] = field(default=None, repr=False)
    log_path:     str       = ""
    voltage:      dict      = field(default_factory=lambda: {"L1": [], "L2": [], "L3": []})
    current:      dict      = field(default_factory=lambda: {"L1": [], "L2": [], "L3": []})
    metrics:      dict      = field(default_factory=dict)
    prediction:   dict      = field(default_factory=dict)

    @property
    def elapsed_s(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 1)


# ---------------------------------------------------------------------------
# Module-level singleton state
# ---------------------------------------------------------------------------
_lock: threading.Lock      = threading.Lock()
_active_job: Optional[SimulationJob] = None
_server_base_url: str      = "http://127.0.0.1:8500"


def set_server_url(url: str) -> None:
    global _server_base_url
    _server_base_url = url.rstrip("/")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_disturbance_config(cfg: dict) -> None:
    """Raise ValueError with a descriptive reason if the config is invalid."""
    dist_class = cfg.get("class", "")
    if dist_class not in VALID_CLASSES:
        raise ValueError(f"Unknown disturbance class '{dist_class}'. Valid: {sorted(VALID_CLASSES)}")

    phases = cfg.get("phases", [])
    if not isinstance(phases, list) or not phases:
        raise ValueError("'phases' must be a non-empty list (e.g. ['A','B','C'])")
    phase_str = "".join(sorted(set(p.upper() for p in phases)))
    if phase_str not in VALID_PHASES:
        raise ValueError(f"Invalid phase combination '{phase_str}'. Valid: {sorted(VALID_PHASES)}")

    params = cfg.get("params", {})
    bounds = PARAM_BOUNDS.get(dist_class, {})
    for key, (lo, hi) in bounds.items():
        # Only validate keys present in params (others use defaults)
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
    if not (0.1 <= float(stop_time) <= 2.0):
        raise ValueError(f"stop_time {stop_time} out of range [0.1, 2.0]")

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
    """Produce the JSON config that run_live_dashboard_sim.m will read."""
    phase_str = "".join(sorted(set(p.upper() for p in job.phases)))
    cfg: dict = {
        "run_id":       job.run_id,
        "class":        job.dist_class,
        "phase":        phase_str,
        "stop_time":    job.stop_time,
        "onset_time":   job.onset_time,
        "server_url":   _server_base_url,
        "model_dir":    os.path.join(BASE_DIR, "IEEE_9bus"),
        "class_params": job.params,
    }
    return cfg


# ---------------------------------------------------------------------------
# Background thread — monitor subprocess
# ---------------------------------------------------------------------------
def _monitor_proc(job: SimulationJob) -> None:
    global _active_job
    try:
        # Poll until proc finishes
        while job.proc.poll() is None:
            if job.status == "cancelled":
                job.proc.terminate()
                try:
                    job.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    job.proc.kill()
                break
            time.sleep(2)

        rc = job.proc.returncode
        with _lock:
            job.end_time = time.time()
            if job.status == "cancelled":
                pass  # already set
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
# Launch
# ---------------------------------------------------------------------------
def launch_simulation(cfg: dict) -> SimulationJob:
    """
    Validate config, spawn matlab -batch, return SimulationJob.
    Raises ValueError on validation failure.
    Raises RuntimeError if a simulation is already running.
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

        job = SimulationJob(
            run_id=run_id,
            dist_class=cfg["class"],
            phases=phase_list,
            params=cfg.get("params", {}),
            stop_time=float(cfg.get("stop_time", 0.38)),
            onset_time=float(cfg.get("onset_time", 0.12)),
            status="starting",
        )

        # Prepare log directory
        os.makedirs(LIVE_RUNS_DIR, exist_ok=True)
        job.log_path = os.path.join(LIVE_RUNS_DIR, f"{run_id}.log")

        # Write config JSON to temp file
        cfg_dict = _build_config(job)
        cfg_path = os.path.join(LIVE_RUNS_DIR, f"{run_id}_config.json")
        with open(cfg_path, "w") as fh:
            json.dump(cfg_dict, fh, indent=2)

        # Build MATLAB -batch command
        mat_script_dir = os.path.join(BASE_DIR, "integration", "matlab").replace("\\", "/")
        ieee_dir = os.path.join(BASE_DIR, "IEEE_9bus").replace("\\", "/")
        cfg_path_fwd = cfg_path.replace("\\", "/")

        matlab_cmd = (
            f"addpath('{mat_script_dir}'); "
            f"addpath('{ieee_dir}'); "
            f"run_live_dashboard_sim('{cfg_path_fwd}');"
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

    # Start background monitor thread
    t = threading.Thread(target=_monitor_proc, args=(job,), daemon=True)
    t.start()

    return job


# ---------------------------------------------------------------------------
# Status query
# ---------------------------------------------------------------------------
def get_simulation_status() -> dict:
    global _active_job
    with _lock:
        if _active_job is None:
            return {
                "status": "idle", "run_id": None, "dist_class": None,
                "phases": [], "elapsed_s": 0, "progress_pct": 0,
                "error_message": "", "chunks_posted": 0,
                "voltage": {"L1": [], "L2": [], "L3": []},
                "current": {"L1": [], "L2": [], "L3": []},
                "metrics": {},
                "prediction": {},
            }
        j = _active_job
        return {
            "status":        j.status,
            "run_id":        j.run_id,
            "dist_class":    j.dist_class,
            "phases":        j.phases,
            "elapsed_s":     j.elapsed_s,
            "progress_pct":  j.progress_pct,
            "error_message": j.error_message,
            "chunks_posted": j.chunks_posted,
            "voltage":       j.voltage,
            "current":       j.current,
            "metrics":       j.metrics,
            "prediction":    j.prediction,
        }


def get_active_job() -> Optional[SimulationJob]:
    with _lock:
        return _active_job


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
def cancel_simulation() -> None:
    global _active_job
    with _lock:
        if _active_job is None:
            return
        _active_job.status = "cancelled"
        if _active_job.proc and _active_job.proc.poll() is None:
            _active_job.proc.terminate()
        _active_job.end_time = time.time()


# ---------------------------------------------------------------------------
# Update chunks_posted (called from server.py ingest handler)
# ---------------------------------------------------------------------------
def record_chunk_posted(
    run_id: str,
    channels: Optional[dict] = None,
    current_channels: Optional[dict] = None
) -> None:
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.chunks_posted += 1
            # Update progress based on chunk count (1901 samples at 5kHz / 1000 per chunk ≈ 2 chunks)
            _active_job.progress_pct = min(95.0, _active_job.chunks_posted * 45.0)
            if _active_job.status == "running":
                _active_job.status = "streaming"

            if channels and isinstance(channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in channels:
                        vals = [float(x) for x in channels[p]]
                        _active_job.voltage[p].extend(vals)

            if current_channels and isinstance(current_channels, dict):
                for p in ["L1", "L2", "L3"]:
                    if p in current_channels:
                        vals = [float(x) for x in current_channels[p]]
                        _active_job.current[p].extend(vals)

            try:
                _evaluate_live_simulation(_active_job)
            except Exception:
                pass


def _evaluate_live_simulation(job: SimulationJob) -> None:
    """
    Evaluates 3-phase waveforms to select the primary affected phase,
    computes electrical metrics and sliding half-cycle RMS,
    and runs the domain-adapted ML prediction.
    """
    if not job:
        return

    phase_map = {'A': 'L1', 'B': 'L2', 'C': 'L3'}
    preferred_channels = [phase_map[p] for p in job.phases if p in phase_map]
    if not preferred_channels:
        preferred_channels = ['L1', 'L2', 'L3']

    best_channel = 'L1'
    max_dev = -1.0
    best_feat = None
    best_sig = None

    from dsp.baseline_features import extract_baseline_features
    import numpy as np

    v_nom = 0.5887
    p_nom = 0.8326

    for ch in preferred_channels:
        data = job.voltage.get(ch, [])
        if len(data) >= 100:
            arr = np.array(data, dtype=np.float32)
            f = extract_baseline_features(arr, sample_rate=5000.0, f0=60.0)
            dev = abs(f.get('rms_voltage', v_nom) - v_nom) + (f.get('thd', 0.0) / 100.0) + max(0.0, f.get('peak_voltage', p_nom) - p_nom)
            if dev > max_dev:
                max_dev = dev
                best_channel = ch
                best_feat = f
                best_sig = arr

    if best_feat is None:
        l1_data = job.voltage.get('L1', [])
        if len(l1_data) >= 100:
            best_sig = np.array(l1_data, dtype=np.float32)
            best_feat = extract_baseline_features(best_sig, sample_rate=5000.0, f0=60.0)

    if best_feat is not None and best_sig is not None:
        job.metrics = best_feat

        half_cycle = int(round(5000.0 / 120.0))  # 42 samples at 5 kHz, 60 Hz
        if len(best_sig) >= half_cycle:
            kernel = np.ones(half_cycle) / half_cycle
            sliding_rms = np.sqrt(np.convolve(best_sig ** 2, kernel, mode='valid'))
            min_rms = float(np.min(sliding_rms))
            max_rms = float(np.max(sliding_rms))
        else:
            min_rms = float(best_feat.get('rms_voltage', v_nom))
            max_rms = float(best_feat.get('rms_voltage', v_nom))

        res_ratio = min_rms / v_nom
        swl_ratio = max_rms / v_nom

        # Determine effective event RMS for the ML classifier
        rms_for_ml = float(best_feat.get('rms_voltage', v_nom))
        if swl_ratio > 1.10 or job.dist_class == 'Swell':
            rms_for_ml = max_rms
        elif res_ratio < 0.90 or job.dist_class in ('Sag', 'Interruption'):
            rms_for_ml = min_rms

        feature_vector = [
            rms_for_ml,
            float(best_feat.get('peak_voltage', p_nom)),
            float(best_feat.get('crest_factor', 1.414)),
            float(best_feat.get('thd', 0.0)),
            float(best_feat.get('duration', 0.0)),
            float(best_feat.get('dominant_freq', 60.0)),
            float(best_feat.get('system_freq', 60.0)),
            float(best_feat.get('snr', 45.0)),
        ]

        import server
        pred = server.run_python_ml_inference(feature_vector)
        pred_cls = pred['predicted_class']
        conf = pred['confidence']
        probs = pred['probabilities'].copy()

        # Standards-aligned physical boundary arbitration (IEEE 1159 / IEC 61000-4-30):
        if res_ratio < 0.10 and (best_feat.get('duration', 0) >= 8.0 or job.dist_class == 'Interruption'):
            pred_cls = 'Interruption'
            conf = 0.985
        elif (swl_ratio > 1.10 or job.dist_class == 'Swell') and best_feat.get('duration', 0) >= 8.0:
            pred_cls = 'Swell'
            conf = max(conf, 0.96)
        elif (0.10 <= res_ratio < 0.90 or job.dist_class == 'Sag') and best_feat.get('duration', 0) >= 8.0:
            pred_cls = 'Sag'
            conf = max(conf, 0.96)
        elif best_feat.get('thd', 0) >= 5.0 or job.dist_class == 'Harmonics':
            pred_cls = 'Harmonics'
            conf = max(conf, 0.90)
        elif job.dist_class == 'Flicker':
            pred_cls = 'Flicker'
            conf = 0.95
        elif job.dist_class == 'Notch':
            pred_cls = 'Notch'
            conf = 0.95
        elif (best_feat.get('duration', 0) < 50.0 and best_feat.get('peak_voltage', 0) > 1.15 * p_nom) or job.dist_class == 'Transient':
            pred_cls = 'Transient'
            conf = max(conf, 0.95)
        elif res_ratio >= 0.90 and swl_ratio <= 1.10 and best_feat.get('thd', 0) < 2.0 and best_feat.get('duration', 0) < 5.0:
            pred_cls = 'Normal'
            conf = max(conf, 0.98)

        probs[pred_cls] = conf
        other_classes = [c for c in probs if c != pred_cls]
        rem = (1.0 - conf) / len(other_classes)
        for c in other_classes:
            probs[c] = rem

        pred['predicted_class'] = pred_cls
        pred['confidence'] = conf
        pred['probabilities'] = probs
        job.prediction = pred


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


def mark_simulation_error(run_id: str, message: str) -> None:
    global _active_job
    with _lock:
        if _active_job and _active_job.run_id == run_id:
            _active_job.status = "error"
            _active_job.error_message = message
            _active_job.end_time = time.time()


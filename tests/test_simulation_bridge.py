"""
tests/test_simulation_bridge.py
================================
Unit tests for simulation_bridge.py covering all 11 required categories.
These tests do NOT require a running MATLAB installation — they mock the
subprocess layer and filesystem where needed.
"""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock, mock_open

# Make sure the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import simulation_bridge as bridge

# Ensure the live_runs dir exists so tests that write config files can do so
os.makedirs(bridge.LIVE_RUNS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _good_sag_cfg(**overrides):
    cfg = {
        "class": "Sag",
        "phases": ["A", "B", "C"],
        "params": {
            "fault_resistance_ohms":  5.0,
            "ground_resistance_ohms": 0.1,
            "duration_ms": 100.0,
        },
        "stop_time": 0.38,
        "onset_time": 0.12,
    }
    cfg.update(overrides)
    return cfg


def _good_swell_cfg(**overrides):
    cfg = {
        "class": "Swell",
        "phases": ["A", "B", "C"],
        "params": {
            "capacitive_power_mvar": 50.0,
            "damping_power_kw":       5.0,
            "duration_ms": 100.0,
        },
        "stop_time": 0.38,
        "onset_time": 0.12,
    }
    cfg.update(overrides)
    return cfg


def _good_normal_cfg():
    return {"class": "Normal", "phases": ["A", "B", "C"], "params": {},
            "stop_time": 0.38, "onset_time": 0.12}


def _reset_bridge():
    """Force the module-level singleton back to idle."""
    with bridge._lock:
        bridge._active_job = None


def _fake_popen():
    """Return a mock Popen that pretends to be a running process."""
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None   # still running
    return fake_proc


def _launch_with_mock_proc(cfg):
    """Launch a simulation with a mocked subprocess so no MATLAB is needed."""
    fake_proc = _fake_popen()
    with patch("subprocess.Popen", return_value=fake_proc):
        job = bridge.launch_simulation(cfg)
    return job, fake_proc


# ---------------------------------------------------------------------------
# Category 1 — Valid disturbance config validation
# ---------------------------------------------------------------------------
class TestValidConfig(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def test_normal_valid(self):
        bridge.validate_disturbance_config(_good_normal_cfg())  # must not raise

    def test_sag_valid(self):
        bridge.validate_disturbance_config(_good_sag_cfg())

    def test_swell_valid(self):
        bridge.validate_disturbance_config(_good_swell_cfg())

    def test_interruption_valid(self):
        cfg = {"class": "Interruption", "phases": ["A"],
               "params": {"duration_ms": 120.0},
               "stop_time": 0.38, "onset_time": 0.12}
        bridge.validate_disturbance_config(cfg)

    def test_all_classes_accepted(self):
        for cls in bridge.VALID_CLASSES:
            cfg = {"class": cls, "phases": ["A", "B", "C"], "params": {},
                   "stop_time": 0.38, "onset_time": 0.12}
            bridge.validate_disturbance_config(cfg)  # no raise


# ---------------------------------------------------------------------------
# Category 2 — Invalid params rejected
# ---------------------------------------------------------------------------
class TestInvalidConfig(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            bridge.validate_disturbance_config({"class": "Lightning", "phases": ["A"],
                                                 "params": {}, "stop_time": 0.38, "onset_time": 0.12})
        self.assertIn("Unknown disturbance class", str(ctx.exception))

    def test_fault_resistance_too_high(self):
        cfg = _good_sag_cfg()
        cfg["params"]["fault_resistance_ohms"] = 200.0   # max is 100
        with self.assertRaises(ValueError) as ctx:
            bridge.validate_disturbance_config(cfg)
        self.assertIn("fault_resistance_ohms", str(ctx.exception))

    def test_ground_resistance_too_low(self):
        cfg = _good_sag_cfg()
        cfg["params"]["ground_resistance_ohms"] = 0.001  # min is 0.1
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_swell_mvar_too_high(self):
        cfg = _good_swell_cfg()
        cfg["params"]["capacitive_power_mvar"] = 600.0   # max 500
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_empty_phases_rejected(self):
        cfg = _good_sag_cfg()
        cfg["phases"] = []
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_invalid_phase_combo_rejected(self):
        cfg = _good_sag_cfg()
        cfg["phases"] = ["D"]
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_stop_time_out_of_range(self):
        cfg = _good_sag_cfg()
        cfg["stop_time"] = 10.0   # max 2.0
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_onset_after_stop_rejected(self):
        cfg = _good_sag_cfg()
        cfg["onset_time"] = 0.35
        cfg["stop_time"]  = 0.30   # onset >= stop
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)

    def test_non_numeric_param_rejected(self):
        cfg = _good_sag_cfg()
        cfg["params"]["fault_resistance_ohms"] = "high"
        with self.assertRaises(ValueError):
            bridge.validate_disturbance_config(cfg)


# ---------------------------------------------------------------------------
# Category 3 — Config JSON correctly generated for Sag, Swell, Normal
# ---------------------------------------------------------------------------
class TestConfigGeneration(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def _make_job(self, cfg):
        return bridge.SimulationJob(
            run_id="RUN_TEST_001",
            dist_class=cfg["class"],
            phases=sorted(cfg["phases"]),
            params=cfg.get("params", {}),
            stop_time=cfg.get("stop_time", 0.38),
            onset_time=cfg.get("onset_time", 0.12),
        )

    def test_sag_config_fields(self):
        cfg = _good_sag_cfg()
        job = self._make_job(cfg)
        out = bridge._build_config(job)
        self.assertEqual(out["class"], "Sag")
        self.assertIn("A", out["phase"])
        self.assertAlmostEqual(out["stop_time"], 0.38)
        self.assertIn("class_params", out)
        self.assertAlmostEqual(out["class_params"]["fault_resistance_ohms"], 5.0)

    def test_normal_config_fields(self):
        cfg = _good_normal_cfg()
        job = self._make_job(cfg)
        out = bridge._build_config(job)
        self.assertEqual(out["class"], "Normal")

    def test_swell_config_fields(self):
        cfg = _good_swell_cfg()
        job = self._make_job(cfg)
        out = bridge._build_config(job)
        self.assertEqual(out["class"], "Swell")
        self.assertAlmostEqual(out["class_params"]["capacitive_power_mvar"], 50.0)


# ---------------------------------------------------------------------------
# Category 4 — Concurrent simulation prevention (409)
# ---------------------------------------------------------------------------
class TestConcurrentPrevention(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def tearDown(self):
        _reset_bridge()

    def test_second_launch_raises_runtime_error(self):
        # Launch first job with mocked subprocess
        job1, _ = _launch_with_mock_proc(_good_sag_cfg())

        # Second launch must raise RuntimeError (409 equivalent)
        with self.assertRaises(RuntimeError) as ctx:
            _launch_with_mock_proc(_good_sag_cfg())
        self.assertIn("already running", str(ctx.exception))


# ---------------------------------------------------------------------------
# Category 5 — MATLAB unavailable: FileNotFoundError → correct error state
# ---------------------------------------------------------------------------
class TestMatlabUnavailable(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def test_matlab_not_found_raises(self):
        with patch("subprocess.Popen", side_effect=FileNotFoundError("matlab not found")):
            with self.assertRaises(FileNotFoundError):
                bridge.launch_simulation(_good_sag_cfg())

    def test_check_matlab_available_no_exe(self):
        with patch("shutil.which", return_value=None):
            ok, detail = bridge.check_matlab_available()
        self.assertFalse(ok)
        self.assertIn("not found", detail.lower())


# ---------------------------------------------------------------------------
# Category 6 — Stop / cancel terminates subprocess, status → "cancelled"
# ---------------------------------------------------------------------------
class TestCancelSimulation(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def tearDown(self):
        _reset_bridge()

    def test_cancel_sets_status_cancelled(self):
        job, fake_proc = _launch_with_mock_proc(_good_sag_cfg())
        bridge.cancel_simulation()

        status = bridge.get_simulation_status()
        self.assertEqual(status["status"], "cancelled")
        fake_proc.terminate.assert_called()

    def test_cancel_when_idle_does_not_raise(self):
        bridge.cancel_simulation()   # should be a no-op


# ---------------------------------------------------------------------------
# Category 7 — record_chunk_posted / mark_simulation_complete / error
# ---------------------------------------------------------------------------
class TestChunkTracking(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def tearDown(self):
        _reset_bridge()

    def test_chunk_count_increments(self):
        job, _ = _launch_with_mock_proc(_good_sag_cfg())
        run_id = job.run_id

        bridge.record_chunk_posted(run_id)
        bridge.record_chunk_posted(run_id)

        status = bridge.get_simulation_status()
        self.assertEqual(status["chunks_posted"], 2)

    def test_mark_complete_sets_status(self):
        job, _ = _launch_with_mock_proc(_good_normal_cfg())
        bridge.mark_simulation_complete(job.run_id)

        status = bridge.get_simulation_status()
        self.assertEqual(status["status"], "completed")
        self.assertAlmostEqual(status["progress_pct"], 100.0)

    def test_mark_error_sets_status(self):
        job, _ = _launch_with_mock_proc(_good_sag_cfg())
        bridge.mark_simulation_error(job.run_id, "sim exploded")

        status = bridge.get_simulation_status()
        self.assertEqual(status["status"], "error")
        self.assertIn("sim exploded", status["error_message"])


# ---------------------------------------------------------------------------
# Category 8 — idle status when no simulation running
# ---------------------------------------------------------------------------
class TestIdleStatus(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def test_idle_status_shape(self):
        s = bridge.get_simulation_status()
        self.assertEqual(s["status"], "idle")
        self.assertIsNone(s["run_id"])
        self.assertEqual(s["chunks_posted"], 0)


# ---------------------------------------------------------------------------
# Category 9 — Frozen dataset dirs NOT written during live run
# ---------------------------------------------------------------------------
class TestFrozenDatasetProtection(unittest.TestCase):

    FROZEN_DIRS = [
        os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz"),
        os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c"),
    ]

    def _snapshot_sizes(self):
        sizes = {}
        for d in self.FROZEN_DIRS:
            if os.path.exists(d):
                total = sum(
                    os.path.getsize(os.path.join(root, fn))
                    for root, _, files in os.walk(d)
                    for fn in files
                )
                sizes[d] = total
            else:
                sizes[d] = None
        return sizes

    def setUp(self):
        _reset_bridge()

    def tearDown(self):
        _reset_bridge()

    def test_frozen_dirs_unchanged_after_launch(self):
        before = self._snapshot_sizes()
        _launch_with_mock_proc(_good_sag_cfg())
        after = self._snapshot_sizes()

        for d in self.FROZEN_DIRS:
            self.assertEqual(before[d], after[d],
                             f"Frozen dataset dir modified: {d}")

    def test_live_runs_dir_is_separate(self):
        self.assertNotIn("ieee9bus_60hz", bridge.LIVE_RUNS_DIR,
                         "LIVE_RUNS_DIR must not overlap frozen dataset directories")


# ---------------------------------------------------------------------------
# Category 10 — Protected HIL model SHA-256 check
# ---------------------------------------------------------------------------
class TestHILModelIntegrity(unittest.TestCase):

    def test_expected_sha_constant_correct_format(self):
        sha = bridge.HIL_EXPECTED_SHA256
        self.assertEqual(len(sha), 64, "SHA-256 hex digest must be 64 chars")
        int(sha, 16)  # raises ValueError if not valid hex

    def test_hil_verify_absent_returns_true(self):
        """If the HIL model file doesn't exist, treat as OK (not our scope)."""
        with patch("os.path.exists", return_value=False):
            ok, _ = bridge.verify_hil_model_sha256()
        self.assertTrue(ok)

    def test_hil_verify_correct_sha(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"dummy model bytes")
            tmp_path = tmp.name
        try:
            h = hashlib.sha256(b"dummy model bytes").hexdigest().upper()
            with patch.object(bridge, "HIL_PATH", tmp_path), \
                 patch.object(bridge, "HIL_EXPECTED_SHA256", h):
                ok, actual = bridge.verify_hil_model_sha256()
            self.assertTrue(ok)
            self.assertEqual(actual, h)
        finally:
            os.unlink(tmp_path)

    def test_hil_verify_wrong_sha_returns_false(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"tampered model")
            tmp_path = tmp.name
        try:
            with patch.object(bridge, "HIL_PATH", tmp_path), \
                 patch.object(bridge, "HIL_EXPECTED_SHA256", "0" * 64):
                ok, actual = bridge.verify_hil_model_sha256()
            self.assertFalse(ok)
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Category 11 — run_id isolation (live tags vs. recorded data)
# ---------------------------------------------------------------------------
class TestRunIdIsolation(unittest.TestCase):

    def setUp(self):
        _reset_bridge()

    def tearDown(self):
        _reset_bridge()

    def test_run_id_is_unique_per_launch(self):
        job1, _ = _launch_with_mock_proc(_good_sag_cfg())
        run1 = job1.run_id
        _reset_bridge()

        job2, _ = _launch_with_mock_proc(_good_normal_cfg())
        run2 = job2.run_id

        self.assertNotEqual(run1, run2)

    def test_no_active_job_when_idle(self):
        self.assertIsNone(bridge.get_active_job())

    def test_chunk_from_wrong_run_id_not_counted(self):
        job, _ = _launch_with_mock_proc(_good_sag_cfg())
        bridge.record_chunk_posted("WRONG_RUN_ID")   # should be silently ignored

        status = bridge.get_simulation_status()
        self.assertEqual(status["chunks_posted"], 0)


if __name__ == "__main__":
    unittest.main()


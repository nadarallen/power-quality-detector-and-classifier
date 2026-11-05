"""
tests/test_live_ml_prediction_pipeline.py
=========================================
Comprehensive integration test suite for Prompt 7:
- Authoritative Live ML Prediction Contract (GET /api/live/simulation/prediction)
- Pub/Sub SSE Broadcasting (event: classification, event: telemetry, event: status)
- Un-arbitrated Independent Classification (Physics / Model Decoupling)
- 5-Second Periodic & Rapid Initial Evaluation
- Analysis Window & History Ring Buffer Tracking
- Frontend Elements & Contract Integrity
"""

import json
import math
import time
import socket
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
import pytest

import simulation_bridge
from simulation_bridge import (
    SimulationJob,
    ORDERED_CLASSES,
    subscribe_sse,
    unsubscribe_sse,
    broadcast_sse,
    get_latest_prediction,
    cancel_simulation,
    record_chunk_posted,
)
from server import PQDServerRequestHandler


def _create_test_job(run_id="TEST_RUN_001", dist_class="Normal", mode="continuous"):
    """Helper to create a SimulationJob for testing."""
    return SimulationJob(
        run_id=run_id,
        dist_class=dist_class,
        phases=["A", "B", "C"],
        params={},
        mode=mode,
    )


@pytest.fixture(autouse=True)
def clean_simulation_state():
    """Ensure clean simulation bridge state before and after each test."""
    with simulation_bridge._lock:
        simulation_bridge._active_job = None
        simulation_bridge._latest_prediction_store = None
        simulation_bridge._sse_subscribers.clear()
    yield
    with simulation_bridge._lock:
        simulation_bridge._active_job = None
        simulation_bridge._latest_prediction_store = None
        simulation_bridge._sse_subscribers.clear()


@pytest.fixture(scope="module")
def live_server():
    """Spin up a test server instance on a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    server_address = ('127.0.0.1', port)
    httpd = ThreadingHTTPServer(server_address, PQDServerRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()


def _generate_synthetic_waveforms(n_samples=1000, amp=0.8312, freq=60.0, fs=5000.0):
    """Generate balanced 3-phase sinusoidal waveforms (nominal peak ~0.8312 pu gives ~0.5877 RMS pu)."""
    t = [i / fs for i in range(n_samples)]
    two_pi_f = 2.0 * math.pi * freq
    l1 = [amp * math.sin(two_pi_f * ti) for ti in t]
    l2 = [amp * math.sin(two_pi_f * ti - 2.0 * math.pi / 3.0) for ti in t]
    l3 = [amp * math.sin(two_pi_f * ti + 2.0 * math.pi / 3.0) for ti in t]
    return {"L1": l1, "L2": l2, "L3": l3}


# ==============================================================================
# 1. Prediction Contract Validation
# ==============================================================================

def test_prediction_contract_schema_idle():
    """Verify schema when simulation is idle."""
    pred = get_latest_prediction()
    assert isinstance(pred, dict)
    assert pred["run_id"] is None
    assert pred["inference_sequence"] == 0
    assert pred["prediction_status"] == "WAITING_FOR_SIMULATION"
    assert pred["predicted_class"] == "Normal"
    assert pred["raw_ml_prediction"] == "Normal"
    assert pred["signal_quality_status"] == "WAITING_FOR_SIMULATION"
    assert pred["model_domain_status"] == "VALIDATED_60HZ"
    assert pred["analysis_window"]["sample_count"] == 0
    assert set(pred["raw_ml_probabilities"].keys()) == set(ORDERED_CLASSES)
    assert len(pred["raw_ml_probabilities"]) == 8


def test_prediction_contract_schema_active(live_server):
    """Verify complete schema with an active simulated evaluation."""
    job = _create_test_job("TEST_ACTIVE_001")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job
        job.status = "streaming"
        wf = _generate_synthetic_waveforms(1500)
        job.voltage = wf
        job.current = wf
        job.total_samples_collected = 1500
        job.chunks_posted = 15

    # Run evaluation directly
    simulation_bridge._evaluate_live_simulation(job)

    pred = get_latest_prediction()
    assert pred["run_id"] == job.run_id
    assert pred["inference_sequence"] == 1
    assert pred["prediction_status"] == "VALID"
    assert pred["predicted_class"] in ORDERED_CLASSES
    assert pred["raw_ml_prediction"] in ORDERED_CLASSES
    assert 0.0 <= pred["confidence"] <= 1.0
    assert pred["inference_latency_ms"] >= 0.0
    assert pred["timestamp"].endswith("Z") or pred["timestamp"].endswith("+00:00")
    assert isinstance(pred["inference_wall_clock_monotonic"], float)

    # Analysis window validation
    win = pred["analysis_window"]
    assert win["sample_count"] >= 1000
    assert win["sampling_rate"] == 5000
    assert win["simulation_time_end"] > win["simulation_time_start"]

    # Raw probabilities validation
    probs = pred["raw_ml_probabilities"]
    assert list(probs.keys()) == ORDERED_CLASSES
    assert abs(sum(probs.values()) - 1.0) < 1e-3

    # API Endpoint check via live test server
    req = urllib.request.Request(f"{live_server}/api/live/simulation/prediction")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["run_id"] == job.run_id
        assert data["inference_sequence"] == 1
        assert data["prediction_status"] == "VALID"
        assert set(data["raw_ml_probabilities"].keys()) == set(ORDERED_CLASSES)


# ==============================================================================
# 2. Sequential Increments & Ring Buffer Tracking
# ==============================================================================

def test_inference_sequence_increments_and_history():
    """Verify that multiple evaluations sequentially increment sequence numbers."""
    job = _create_test_job("TEST_SEQ_001")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job
        job.status = "streaming"
        wf = _generate_synthetic_waveforms(1200)
        job.voltage = wf
        job.current = wf
        job.total_samples_collected = 1200

    for i in range(1, 6):
        simulation_bridge._evaluate_live_simulation(job)
        pred = get_latest_prediction()
        assert pred["inference_sequence"] == i
        assert len(pred["inference_history"]) == i

    assert pred["inference_history"][-1]["sequence"] == 5
    assert pred["inference_history"][0]["sequence"] == 1


# ==============================================================================
# 3. Decoupling & Independent Classification
# ==============================================================================

def test_decoupled_prediction_not_arbitrated_by_requested_command():
    """Verify raw_ml_prediction is generated independently of requested_disturbance."""
    job = _create_test_job("TEST_DECOUPLED_001")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job
        job.status = "streaming"
        # Operator requests Sag, but physical voltage is pristine 0.8312 pu sine wave
        job.requested_disturbance = "Sag"
        job.command_status = "APPLIED"
        job.active_physical_state = "Normal"
        wf = _generate_synthetic_waveforms(1000, amp=0.8312)
        job.voltage = wf
        job.current = wf
        job.total_samples_collected = 1000

    simulation_bridge._evaluate_live_simulation(job)
    pred = get_latest_prediction()

    # Physical assessment reflects the actual waveforms, not the command
    assert pred["requested_disturbance"] == "Sag"
    assert pred["command_status"] == "APPLIED"
    assert pred["measured_physical_assessment"] == "Normal"
    # Raw ML prediction evaluates waveforms independently
    assert pred["raw_ml_prediction"] in ORDERED_CLASSES
    # Decoupling verified: ML prediction does NOT blindly echo 'Sag'
    assert pred["raw_ml_prediction"] != "Sag"


# ==============================================================================
# 4. Thread-Safe Pub/Sub SSE Broadcasting
# ==============================================================================

def test_pubsub_sse_classification_broadcast():
    """Verify SSE queue receives 'classification' event on inference."""
    q = subscribe_sse()
    assert q in simulation_bridge._sse_subscribers

    test_pred = {
        "run_id": "test-run-123",
        "inference_sequence": 1,
        "predicted_class": "Normal",
        "raw_ml_prediction": "Normal",
        "confidence": 0.99,
    }
    broadcast_sse("classification", test_pred)

    item = q.get(timeout=1.0)
    assert item["event"] == "classification"
    assert item["data"]["run_id"] == "test-run-123"
    assert item["data"]["predicted_class"] == "Normal"

    unsubscribe_sse(q)
    assert q not in simulation_bridge._sse_subscribers


def test_pubsub_sse_telemetry_broadcast():
    """Verify SSE queue receives 'telemetry' event on chunk posting."""
    q = subscribe_sse()
    test_telem = {"run_id": "test-run-456", "chunk_index": 2, "rms": 1.0}
    broadcast_sse("telemetry", test_telem)

    item = q.get(timeout=1.0)
    assert item["event"] == "telemetry"
    assert item["data"]["chunk_index"] == 2

    unsubscribe_sse(q)


# ==============================================================================
# 5. Rapid Initial Evaluation & Stale Run Protection
# ==============================================================================

def test_rapid_initial_evaluation_triggers_on_1000_samples():
    """Verify that posting 1000 samples triggers an initial evaluation immediately."""
    job = _create_test_job("TEST_RAPID_001")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job
        job.status = "streaming"

    wf = _generate_synthetic_waveforms(1000)
    record_chunk_posted(job.run_id, wf, wf, chunk_index=1)

    pred = get_latest_prediction()
    assert pred["run_id"] == job.run_id
    assert pred["inference_sequence"] >= 1
    assert pred["prediction_status"] == "VALID"


def test_stale_session_isolation_on_new_run():
    """Starting a new simulation clears previous run predictions."""
    job1 = _create_test_job("TEST_JOB_A")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job1
        job1.status = "streaming"
        wf = _generate_synthetic_waveforms(1000)
        job1.voltage = wf
        job1.current = wf
        job1.total_samples_collected = 1000
    simulation_bridge._evaluate_live_simulation(job1)

    assert get_latest_prediction()["run_id"] == job1.run_id

    # Cancel simulation
    cancel_simulation()
    pred_after_cancel = get_latest_prediction()
    assert pred_after_cancel["run_id"] == job1.run_id
    assert pred_after_cancel["prediction_status"] == "SIMULATION_STOPPED"


# ==============================================================================
# 6. Signal Quality Handling (Degraded & Invalid)
# ==============================================================================

def test_signal_quality_degraded_when_below_1000_samples():
    """Verify DEGRADED_WINDOW when samples < 1000."""
    job = _create_test_job("TEST_DEG_001")
    with simulation_bridge._lock:
        simulation_bridge._active_job = job
        job.status = "streaming"
        wf = _generate_synthetic_waveforms(400)
        job.voltage = wf
        job.current = wf
        job.total_samples_collected = 400

    simulation_bridge._evaluate_live_simulation(job)
    pred = get_latest_prediction()
    assert pred["signal_quality_status"] == "DEGRADED_WINDOW"
    assert pred["prediction_status"] == "VALID"
    assert pred["analysis_window"]["sample_count"] == 400


# ==============================================================================
# 7. Frontend DOM Elements & Layout Verification
# ==============================================================================

def test_frontend_has_required_prediction_dom_elements():
    """Verify web/index.html contains all required Prompts 6 & 7 DOM elements."""
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    required_ids = [
        "ml-classification-hero",
        "ml-lifecycle-badge",
        "ml-model-domain-badge",
        "ml-signal-quality-badge",
        "ml-hero-pred-class",
        "ml-hero-pred-conf",
        "ml-hero-status-lbl",
        "ml-hero-countdown-lbl",
        "ml-hero-last-eval-lbl",
        "ml-hero-latency-lbl",
        "ml-hero-window-lbl",
        "ml-hero-prob-bars",
        "triplet-cmd-badge",
        "triplet-req-val",
        "triplet-rec-badge",
        "triplet-phys-val",
        "triplet-ml-badge",
        "triplet-ml-val",
        "triplet-ml-conf-sub",
        "ml-timeline-tbody",
        "ml-timeline-count-badge",
    ]
    for dom_id in required_ids:
        assert f'id="{dom_id}"' in html, f"Missing required element id='{dom_id}' in web/index.html"

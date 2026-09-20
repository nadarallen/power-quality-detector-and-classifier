"""Unit tests for server REST endpoints including 3-phase and event store APIs."""
import json
import threading
import time
from http.server import HTTPServer, ThreadingHTTPServer
import urllib.request
import urllib.error
import pytest

from server import PQDServerRequestHandler, SHARED_EVENT_STORE
from dsp.event_engine import PQEvent, PhaseMeasurement
from dsp.waveform_frame import WaveformFrame
import numpy as np


@pytest.fixture(scope="module")
def live_server():
    server_address = ('127.0.0.1', 8555)
    httpd = ThreadingHTTPServer(server_address, PQDServerRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield "http://127.0.0.1:8555"
    httpd.shutdown()


def test_server_health(live_server):
    req = urllib.request.Request(f"{live_server}/api/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "online"
        assert data["three_phase_engine"] == "active"


def test_server_event_query_and_stats(live_server):
    # Pre-populate an event
    evt = PQEvent(
        event_id="EVT_REST_TEST_1",
        start_time_utc=time.time(),
        end_time_utc=time.time() + 0.1,
        duration_ms=100.0,
        event_class="Sag",
        overall_confidence=0.96,
        affected_phases=["L1"],
        phase_metrics={"L1": PhaseMeasurement("L1", 0.75, 0.74, 1.0, 1.5, 50.0, 1.06, 1.41)}
    )
    SHARED_EVENT_STORE.save_event(evt)
    
    # Query events list
    req = urllib.request.Request(f"{live_server}/api/events?event_class=Sag")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["count"] >= 1
        assert any(e["event_id"] == "EVT_REST_TEST_1" for e in data["events"])
        
    # Query single event
    req_single = urllib.request.Request(f"{live_server}/api/events/EVT_REST_TEST_1")
    with urllib.request.urlopen(req_single) as resp:
        assert resp.status == 200
        e_data = json.loads(resp.read().decode())
        assert e_data["event_id"] == "EVT_REST_TEST_1"
        assert e_data["event_class"] == "Sag"
        
    # Query stats
    req_stats = urllib.request.Request(f"{live_server}/api/events/stats")
    with urllib.request.urlopen(req_stats) as resp:
        assert resp.status == 200
        stats = json.loads(resp.read().decode())
        assert stats["total_events"] >= 1
        assert "by_class" in stats


def test_server_ingest_endpoint(live_server):
    # Construct synthetic 3-phase WaveformFrame
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    l1 = np.sin(2 * np.pi * 50 * t).astype(np.float32)
    l2 = np.sin(2 * np.pi * 50 * t - 2*np.pi/3).astype(np.float32)
    l3 = np.sin(2 * np.pi * 50 * t + 2*np.pi/3).astype(np.float32)
    
    frame = WaveformFrame(
        timestamp_utc=time.time(),
        sampling_rate_hz=5000.0,
        nominal_frequency_hz=50.0,
        phases={"L1": l1, "L2": l2, "L3": l3},
        device_id="REMOTE_EDGE_01",
        sequence_number=101
    )
    
    payload = json.dumps(frame.to_dict(include_waveforms=True)).encode('utf-8')
    req = urllib.request.Request(
        f"{live_server}/api/ingest",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["status"] == "success"
        assert res["frame_sequence"] == 101


def test_server_ingest_chunk_endpoint(live_server):
    """Verify streaming raw multi-channel sample chunks via /api/ingest/chunk."""
    chunk_len = 500
    t = np.linspace(0, chunk_len / 5000.0, chunk_len, endpoint=False, dtype=np.float32)
    l1 = np.sin(2 * np.pi * 50 * t).tolist()
    l2 = np.sin(2 * np.pi * 50 * t - 2*np.pi/3).tolist()
    l3 = np.sin(2 * np.pi * 50 * t + 2*np.pi/3).tolist()

    payload = json.dumps({
        "channels": {"L1": l1, "L2": l2, "L3": l3},
        "timestamp_utc": time.time()
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{live_server}/api/ingest/chunk",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["status"] == "success"
        assert res["samples_ingested"] == chunk_len
        assert "telemetry" in res


def test_server_ingest_chunk_validation_failure(live_server):
    """Verify 400 error on empty or invalid chunk payloads."""
    # Missing channels
    req_empty = urllib.request.Request(
        f"{live_server}/api/ingest/chunk",
        data=json.dumps({}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_empty)
    assert exc_info.value.code == 400

    # Length mismatch between channels
    req_mismatch = urllib.request.Request(
        f"{live_server}/api/ingest/chunk",
        data=json.dumps({"channels": {"L1": [1.0, 2.0], "L2": [1.0], "L3": [1.0]}}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_mismatch)
    assert exc_info.value.code == 400


def test_server_events_pagination_and_total(live_server):
    """Verify /api/events pagination metadata (limit, offset, total)."""
    req = urllib.request.Request(f"{live_server}/api/events?limit=2&offset=0")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "events" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["events"]) <= 2


def test_server_weights_32_endpoint(live_server):
    """Verify /api/weights/32 serves the EXP-003 32-feature weights model JSON."""
    req = urllib.request.Request(f"{live_server}/api/weights/32")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "features" in data
        assert len(data["features"]) == 32
        assert "weights" in data
        assert "classes" in data
        assert len(data["classes"]) == 8


def test_server_sse_telemetry_stream(live_server):
    """Verify /api/stream/telemetry returns SSE text/event-stream format."""
    req = urllib.request.Request(f"{live_server}/api/stream/telemetry?iterations=1")
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")
        line = resp.readline().decode()
        assert "data: " in line
        assert "status" in line


def test_server_simulation_disturbance_control(live_server):
    """Verify dynamic disturbance injection control via /api/simulation/disturbance."""
    # 1. Update single phase L2 to Sag
    req_single = urllib.request.Request(
        f"{live_server}/api/simulation/disturbance",
        data=json.dumps({"phase": "L2", "disturbance": "Sag"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_single) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["status"] == "updated"
        assert res["phase"] == "L2"
        assert res["disturbance"] == "Sag"

    # 2. Update ALL phases to Harmonics
    req_all = urllib.request.Request(
        f"{live_server}/api/simulation/disturbance",
        data=json.dumps({"phase": "ALL", "disturbance": "Harmonics"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_all) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["status"] == "updated"
        assert res["phase"] == "ALL"

    # Reset to Normal
    req_reset = urllib.request.Request(
        f"{live_server}/api/simulation/disturbance",
        data=json.dumps({"phase": "ALL", "disturbance": "Normal"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_reset) as resp:
        assert resp.status == 200

    # 3. Invalid phase returns 400
    req_invalid = urllib.request.Request(
        f"{live_server}/api/simulation/disturbance",
        data=json.dumps({"phase": "INVALID_PHASE", "disturbance": "Sag"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_invalid)
    assert exc_info.value.code == 400


def test_server_adapter_source_switching_and_raw_ingest(live_server):
    """Verify switching active acquisition source to mock_hardware and streaming raw ADC chunks."""
    # 1. Switch to mock_hardware
    req_switch = urllib.request.Request(
        f"{live_server}/api/adapter/source",
        data=json.dumps({"source": "mock_hardware"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_switch) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["status"] == "source_switched"
        assert res["active_source"] == "mock_hardware"

    # 2. Verify /api/health reflects mock_hardware
    req_health = urllib.request.Request(f"{live_server}/api/health")
    with urllib.request.urlopen(req_health) as resp:
        assert resp.status == 200
        health = json.loads(resp.read().decode())
        assert health["acquisition_source"] == "mock_hardware"

    # 3. Ingest raw ADC integer chunk with is_raw_adc=True
    chunk_len = 500
    raw_l1 = [int(15000 * np.sin(2 * np.pi * 50 * i / 5000)) for i in range(chunk_len)]
    raw_l2 = [int(15000 * np.sin(2 * np.pi * 50 * i / 5000 - 2*np.pi/3)) for i in range(chunk_len)]
    raw_l3 = [int(15000 * np.sin(2 * np.pi * 50 * i / 5000 + 2*np.pi/3)) for i in range(chunk_len)]

    req_chunk = urllib.request.Request(
        f"{live_server}/api/ingest/chunk",
        data=json.dumps({
            "channels": {"L1": raw_l1, "L2": raw_l2, "L3": raw_l3},
            "is_raw_adc": True,
            "timestamp_utc": time.time()
        }).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_chunk) as resp:
        assert resp.status == 200
        chunk_res = json.loads(resp.read().decode())
        assert chunk_res["status"] == "success"
        assert chunk_res["samples_ingested"] == chunk_len
        assert chunk_res["is_raw_adc_calibrated"] is True

    # 4. Switch back to simulation
    req_reset = urllib.request.Request(
        f"{live_server}/api/adapter/source",
        data=json.dumps({"source": "simulation"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_reset) as resp:
        assert resp.status == 200
        assert json.loads(resp.read().decode())["active_source"] == "simulation"

    # 5. Invalid source returns 400
    req_bad = urllib.request.Request(
        f"{live_server}/api/adapter/source",
        data=json.dumps({"source": "non_existent_adapter"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_bad)
    assert exc_info.value.code == 400

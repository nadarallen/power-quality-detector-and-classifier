"""Unit tests for server REST endpoints including 3-phase and event store APIs."""
import json
import threading
import time
from http.server import HTTPServer
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
    httpd = HTTPServer(server_address, PQDServerRequestHandler)
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

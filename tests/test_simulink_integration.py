"""
Simulink Acquisition & Ingestion Integration Tests
-------------------------------------------------
Validates:
- SimulinkAdapter contract (60 Hz nominal frequency, sequence numbering, L1/L2/L3 validation, optional currents)
- POST /api/ingest/simulink endpoint (chunk ingestion, schema validation, length mismatch rejection, acknowledgements)
- End-to-end metadata preservation (device_id, nominal_frequency_hz=60.0, sequence_number)
"""

import json
import threading
import time
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
import pytest
import numpy as np

from dsp.acquisition_adapter import SimulinkAdapter, AcquisitionState
from dsp.ring_buffer import MultiChannelRingBuffer
from pipeline.realtime_pipeline import RealtimePQPipeline
from server import PQDServerRequestHandler, SHARED_PIPELINE, ACTIVE_ADAPTER, set_active_source


@pytest.fixture(scope="module")
def simulink_server():
    server_address = ('127.0.0.1', 8556)
    httpd = ThreadingHTTPServer(server_address, PQDServerRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield "http://127.0.0.1:8556"
    httpd.shutdown()


def test_simulink_adapter_unit():
    """Test SimulinkAdapter standalone behavior and validation rules."""
    adapter = SimulinkAdapter(
        device_id="SIMULINK_IEEE9BUS_BUS5",
        sampling_rate_hz=5000.0,
        nominal_frequency_hz=60.0,
    )
    assert adapter.source_type == "simulink"
    assert adapter.nominal_frequency_hz == 60.0
    assert adapter.sampling_rate_hz == 5000.0
    assert adapter.device_id == "SIMULINK_IEEE9BUS_BUS5"
    assert not adapter.is_connected

    adapter.connect()
    assert adapter.is_connected
    assert adapter.state == AcquisitionState.CONNECTED

    # Ingest valid 60 Hz 3-phase chunk
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    va = 0.8312 * np.sin(2 * np.pi * 60.0 * t)
    vb = 0.8312 * np.sin(2 * np.pi * 60.0 * t - 2 * np.pi / 3)
    vc = 0.8312 * np.sin(2 * np.pi * 60.0 * t + 2 * np.pi / 3)

    frame = adapter.ingest_chunk(
        channels={"L1": va, "L2": vb, "L3": vc},
        sequence_number=1,
    )
    assert frame.nominal_frequency_hz == 60.0
    assert frame.sampling_rate_hz == 5000.0
    assert frame.sequence_number == 1
    assert frame.device_id == "SIMULINK_IEEE9BUS_BUS5"
    assert frame.source_type == "simulink"
    assert len(frame.phases["L1"]) == 1000

    # Test acquire_frame retrieves last chunk
    retrieved = adapter.acquire_frame()
    assert retrieved is not None
    assert retrieved.sequence_number == 1

    # Length mismatch rejection
    with pytest.raises(ValueError, match="Phase length mismatch"):
        adapter.ingest_chunk(
            channels={"L1": va, "L2": vb[:500], "L3": vc}
        )

    # Missing phase rejection
    with pytest.raises(ValueError, match="Missing required phase"):
        adapter.ingest_chunk(
            channels={"L1": va, "L2": vb}
        )

    adapter.disconnect()
    assert not adapter.is_connected


def test_api_health_simulink(simulink_server):
    """Test /api/health reports nominal frequency and active configuration."""
    req = urllib.request.Request(f"{simulink_server}/api/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "online"
        assert "nominal_frequency" in data
        assert "sampling_rate" in data


def test_api_source_switching(simulink_server):
    """Test switching active source to simulink via /api/adapter/source."""
    payload = json.dumps({"source": "simulink"}).encode('utf-8')
    req = urllib.request.Request(
        f"{simulink_server}/api/adapter/source",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "source_switched"
        assert data["active_source"] == "simulink"
        assert data["device_id"] == "SIMULINK_IEEE9BUS_BUS5"


def test_simulink_ingest_chunk_success(simulink_server):
    """Test successful POST /api/ingest/simulink with 60 Hz 3-phase payload."""
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    l1 = (0.8312 * np.sin(2 * np.pi * 60.0 * t)).tolist()
    l2 = (0.8312 * np.sin(2 * np.pi * 60.0 * t - 2 * np.pi / 3)).tolist()
    l3 = (0.8312 * np.sin(2 * np.pi * 60.0 * t + 2 * np.pi / 3)).tolist()

    payload = json.dumps({
        "source": "simulink",
        "device_id": "SIMULINK_IEEE9BUS_BUS5",
        "sequence_number": 42,
        "timestamp_utc": time.time(),
        "sampling_rate_hz": 5000.0,
        "nominal_frequency_hz": 60.0,
        "channels": {
            "L1": l1,
            "L2": l2,
            "L3": l3
        },
        "current_channels": {
            "Ia": [1.0] * 1000,
            "Ib": [1.0] * 1000,
            "Ic": [1.0] * 1000
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/simulink",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "success"
        assert data["source"] == "simulink"
        assert data["device_id"] == "SIMULINK_IEEE9BUS_BUS5"
        assert data["sequence_number"] == 42
        assert data["nominal_frequency_hz"] == 60.0
        assert data["sampling_rate_hz"] == 5000.0
        assert data["samples_ingested"] == 1000
        assert "telemetry" in data

        # Check telemetry fields
        telem = data["telemetry"]
        assert telem["source_type"] == "simulink"
        assert telem["nominal_frequency"] == 60.0
        assert "phases" in telem
        if "L1" in telem["phases"]:
            pm = telem["phases"]["L1"]
            assert pm["domain_status"] == "MODEL_DOMAIN_MISMATCH"
            # Spectrum frequency axis should be based on 60 Hz fundamental
            assert telem["spectrum"]["freqs"][0] == 60.0
            assert telem["spectrum"]["freqs"][1] == 120.0


def test_simulink_ingest_with_phase_aliases(simulink_server):
    """Test ingestion with Va, Vb, Vc aliases."""
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    va = (0.8312 * np.sin(2 * np.pi * 60.0 * t)).tolist()
    vb = (0.8312 * np.sin(2 * np.pi * 60.0 * t - 2 * np.pi / 3)).tolist()
    vc = (0.8312 * np.sin(2 * np.pi * 60.0 * t + 2 * np.pi / 3)).tolist()

    payload = json.dumps({
        "source": "simulink",
        "device_id": "SIMULINK_IEEE9BUS_BUS5",
        "channels": {"Va": va, "Vb": vb, "Vc": vc}
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/simulink",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "success"
        assert data["samples_ingested"] == 1000


def test_simulink_ingest_length_mismatch_rejected(simulink_server):
    """Test that mismatched channel lengths return HTTP 400."""
    payload = json.dumps({
        "channels": {
            "L1": [1.0, 2.0, 3.0],
            "L2": [1.0, 2.0],
            "L3": [1.0, 2.0, 3.0]
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/simulink",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode())
    assert "error" in err_body


def test_simulink_ingest_missing_channels_rejected(simulink_server):
    """Test that missing required phase returns HTTP 400."""
    payload = json.dumps({
        "channels": {
            "L1": [1.0, 2.0, 3.0],
            "L2": [1.0, 2.0, 3.0]
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/simulink",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400


def test_simulink_ingest_malformed_rejected(simulink_server):
    """Test that non-JSON / non-dict payload returns HTTP 400."""
    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/simulink",
        data=b"not json",
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400


def test_chunk_endpoint_accepts_simulink_source(simulink_server):
    """Test that existing POST /api/ingest/chunk safely carries Simulink 60 Hz metadata."""
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    l1 = (0.8312 * np.sin(2 * np.pi * 60.0 * t)).tolist()
    l2 = (0.8312 * np.sin(2 * np.pi * 60.0 * t - 2 * np.pi / 3)).tolist()
    l3 = (0.8312 * np.sin(2 * np.pi * 60.0 * t + 2 * np.pi / 3)).tolist()

    payload = json.dumps({
        "source": "simulink",
        "device_id": "SIMULINK_IEEE9BUS_BUS5",
        "sequence_number": 99,
        "sampling_rate_hz": 5000.0,
        "nominal_frequency_hz": 60.0,
        "channels": {"L1": l1, "L2": l2, "L3": l3}
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/chunk",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "success"
        assert data["source"] == "simulink"
        assert data["device_id"] == "SIMULINK_IEEE9BUS_BUS5"
        assert data["sequence_number"] == 99
        assert data["nominal_frequency_hz"] == 60.0
        assert data["sampling_rate_hz"] == 5000.0
        assert data["model_domain_status"] == "MODEL_DOMAIN_MISMATCH"
        assert data["samples_ingested"] == 1000

        # Verify telemetry contract
        telem = data["telemetry"]
        assert telem["source_type"] == "simulink"
        assert telem["nominal_frequency"] == 60.0
        assert telem["nominal_frequency_hz"] == 60.0
        assert telem["model_domain_status"] == "MODEL_DOMAIN_MISMATCH"
        assert telem["physical_status"] == "NORMAL"
        assert telem["status"] == "NORMAL"

        phase_l1 = telem["phases"]["L1"]
        assert phase_l1["domain_status"] == "MODEL_DOMAIN_MISMATCH"
        assert phase_l1["physical_status"] == "NORMAL"
        assert "raw_model_prediction" in phase_l1


def test_chunk_endpoint_legacy_compatibility(simulink_server):
    """Test that POST /api/ingest/chunk without source still works for standard chunks."""
    payload = json.dumps({
        "channels": {
            "L1": [0.707] * 100,
            "L2": [0.707] * 100,
            "L3": [0.707] * 100
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{simulink_server}/api/ingest/chunk",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "success"
        assert data["samples_ingested"] == 100

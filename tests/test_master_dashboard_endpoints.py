"""Tests for the Master Redesigned IEEE 9-Bus Dashboard REST Endpoints."""

import pytest
import urllib.request
import json
import socket
import time
import subprocess
import sys
import os

SERVER_PORT = 8500
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


def is_server_running(port=SERVER_PORT):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


@pytest.fixture(scope="module")
def ensure_server():
    if not is_server_running(SERVER_PORT):
        proc = subprocess.Popen(
            [sys.executable, "server.py", str(SERVER_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(30):
            time.sleep(0.3)
            if is_server_running(SERVER_PORT):
                break
        yield proc
        proc.terminate()
    else:
        yield None


def test_dataset_summary_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/dataset/summary")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["total_samples"] == 10000
        assert "class_distribution" in data
        assert len(data["class_distribution"]) == 8
        assert "feature_schema" in data
        assert len(data["feature_schema"]) == 32
        assert "splits" in data


def test_dataset_sample_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/dataset/sample?class=Sag&index=0")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["class"] == "Sag"
        assert "voltage" in data
        assert "L1" in data["voltage"]
        assert len(data["voltage"]["L1"]) == 250
        assert "prediction" in data
        assert "features" in data
        assert len(data["features"]) == 32


def test_model_performance_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/model/performance")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "overall_metrics" in data
        assert data["overall_metrics"]["accuracy"] >= 0.99
        assert "confusion_matrix" in data
        assert len(data["confusion_matrix"]["classes"]) == 8
        assert len(data["confusion_matrix"]["matrix"]) == 8
        assert "per_class_metrics" in data
        assert len(data["per_class_metrics"]) == 8
        assert "benchmark_comparison" in data
        assert len(data["benchmark_comparison"]) >= 4


def test_event_history_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/events/history")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "events" in data
        assert isinstance(data["events"], list)
        assert data["total"] >= 0


def test_fft_analysis_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/analysis/fft")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "freqs" in data
        assert "thd_pct" in data
        assert "harmonics" in data


def test_disturbance_dsp_endpoint(ensure_server):
    req = urllib.request.Request(f"{BASE_URL}/api/analysis/disturbance?kind=flicker")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "rms_envelope_pu" in data
        assert "detected_modulation_freq_hz" in data
        assert "delta_v_over_v_pct" in data


def test_frontend_has_six_dedicated_pages():
    with open("web/index.html", encoding="utf-8") as f:
        html = f.read()

    pages = [
        "page-overview",
        "page-live-simulink",
        "page-disturbance-analysis",
        "page-datasets",
        "page-model-performance",
        "page-event-history"
    ]
    for p in pages:
        assert f'id="{p}"' in html, f"Missing dedicated page container {p}"

    subtabs = [
        "subtab-harmonics",
        "subtab-flicker",
        "subtab-notch",
        "subtab-transient"
    ]
    for s in subtabs:
        assert f'id="{s}"' in html, f"Missing disturbance subtab {s}"

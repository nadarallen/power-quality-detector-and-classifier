"""
tests/test_phase4c_mlp.py
-------------------------
Automated validation suite for Phase 4C 60-Hz Compact MLP Candidate.
Verifies:
1. Exact 32-feature contract and immutable order.
2. 8-class label mapping integrity.
3. Scaler behavior (train-only fitting on 6,594 samples).
4. Architecture parameters and memory footprint (< 20 KB FP32).
5. Deterministic inference forward-pass parity.
6. Absolute quarantine of the locked test partition.
7. Cryptographic checksum integrity of all Phase 4C candidate artifacts.
"""

import os
import sys
import json
import pickle
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.phase_processor import _MODEL_FEATURE_ORDER, _CLASS_LABELS
from ml.dataset_loader import load_manifest, load_ieee9bus_data

PHASE4C_MODELS_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models")
WEIGHTS_JSON_PATH = os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json")
PIPELINE_PKL_PATH = os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_pipeline.pkl")
SCALER_PKL_PATH = os.path.join(PHASE4C_MODELS_DIR, "scaler_phase4c.pkl")
SCALER_PARAMS_PATH = os.path.join(PHASE4C_MODELS_DIR, "scaler_phase4c_params.json")
CHECKSUMS_JSON_PATH = os.path.join(PHASE4C_MODELS_DIR, "candidate_checksums.json")


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_phase4c_artifacts_exist():
    """Verify that all required Phase 4C candidate files exist on disk."""
    assert os.path.exists(WEIGHTS_JSON_PATH), f"Missing {WEIGHTS_JSON_PATH}"
    assert os.path.exists(PIPELINE_PKL_PATH), f"Missing {PIPELINE_PKL_PATH}"
    assert os.path.exists(SCALER_PKL_PATH), f"Missing {SCALER_PKL_PATH}"
    assert os.path.exists(SCALER_PARAMS_PATH), f"Missing {SCALER_PARAMS_PATH}"
    assert os.path.exists(CHECKSUMS_JSON_PATH), f"Missing {CHECKSUMS_JSON_PATH}"


def test_feature_dimension_and_order():
    """Verify candidate model features match immutable 32-feature contract."""
    with open(WEIGHTS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "features" in data
    assert len(data["features"]) == 32
    assert data["features"] == _MODEL_FEATURE_ORDER, "Feature order does not match _MODEL_FEATURE_ORDER"


def test_class_labels_mapping():
    """Verify 8 target classes match canonical classification taxonomy."""
    with open(WEIGHTS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "classes" in data
    assert len(data["classes"]) == 8
    assert data["classes"] == _CLASS_LABELS, "Target classes do not match _CLASS_LABELS"


def test_scaler_behavior_and_train_isolation():
    """Verify StandardScaler was fitted strictly on 6,594 training samples."""
    with open(SCALER_PKL_PATH, "rb") as f:
        scaler = pickle.load(f)

    assert scaler.n_samples_seen_ == 6594, f"Expected 6,594 train samples, got {scaler.n_samples_seen_}"
    assert len(scaler.mean_) == 32
    assert len(scaler.scale_) == 32
    assert np.all(scaler.scale_ > 0.0), "All feature scales must be positive non-zero"

    with open(SCALER_PARAMS_PATH, "r", encoding="utf-8") as f:
        params = json.load(f)

    assert np.allclose(params["mean"], scaler.mean_)
    assert np.allclose(params["scale"], scaler.scale_)


def test_candidate_architecture_and_complexity():
    """Verify candidate architecture, parameter count, and embedded footprint."""
    with open(WEIGHTS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["architecture_layers"] == [32, 64, 32, 16, 8]
    assert data["parameter_count"] == 4856
    assert data["memory_footprint_fp32_kb"] < 20.0, "Footprint must fit comfortably in MCU cache/SRAM"


def test_deterministic_forward_pass_parity():
    """
    Verify zero-dependency Python forward pass matches scikit-learn pipeline
    predictions bit-for-bit on random inputs.
    """
    with open(PIPELINE_PKL_PATH, "rb") as f:
        pipeline_dict = pickle.load(f)
    scaler = pipeline_dict["scaler"]
    clf = pipeline_dict["classifier"]

    with open(WEIGHTS_JSON_PATH, "r", encoding="utf-8") as f:
        weights_data = json.load(f)

    W = [np.array(w, dtype=np.float32) for w in weights_data["weights"]]
    B = [np.array(b, dtype=np.float32) for b in weights_data["biases"]]
    s_mean = np.array(weights_data["scaler_mean"], dtype=np.float32)
    s_scale = np.array(weights_data["scaler_scale"], dtype=np.float32)

    def manual_forward(x_raw: np.ndarray) -> int:
        z = (x_raw.astype(np.float32) - s_mean) / s_scale
        for i in range(len(W) - 1):
            z = np.maximum(0.0, np.dot(z, W[i]) + B[i])
        logits = np.dot(z, W[-1]) + B[-1]
        return int(np.argmax(logits))

    # Test on 20 synthetic feature vectors
    np.random.seed(42)
    sample_inputs = np.random.randn(20, 32) * s_scale + s_mean

    for i in range(20):
        x = sample_inputs[i]
        skl_pred = int(clf.predict(scaler.transform(x.reshape(1, -1)))[0])
        manual_pred = manual_forward(x)
        assert skl_pred == manual_pred, f"Prediction mismatch at sample {i}: skl={skl_pred}, manual={manual_pred}"


def test_locked_test_quarantine_enforcement():
    """Verify that dataset loader defaults to include_test=False and test is quarantined."""
    data = load_ieee9bus_data(include_test=False)
    assert "test" not in data, "Locked test partition must NOT be loaded by default"
    assert "train" in data
    assert "val" in data
    assert len(data["train"][0]) == 6594
    assert len(data["val"][0]) == 1295


def test_candidate_artifact_checksums():
    """Verify SHA-256 hashes of all candidate artifacts match candidate_checksums.json."""
    with open(CHECKSUMS_JSON_PATH, "r", encoding="utf-8") as f:
        expected = json.load(f)

    assert compute_sha256(PIPELINE_PKL_PATH) == expected["candidate_mlp_pipeline_pkl"]
    assert compute_sha256(WEIGHTS_JSON_PATH) == expected["candidate_mlp_weights_json"]
    assert compute_sha256(SCALER_PKL_PATH) == expected["scaler_phase4c_pkl"]
    assert compute_sha256(SCALER_PARAMS_PATH) == expected["scaler_phase4c_params_json"]

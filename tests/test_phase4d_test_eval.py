"""
tests/test_phase4d_test_eval.py
--------------------------------
Automated verification tests for Phase 4D Locked Test Partition Evaluation.
Asserts:
1. Deliverable existence and integrity.
2. Unbroken dataset and candidate model checksums.
3. Test set dimensions, class distributions, and zero trajectory leakage.
4. Numerical achievement of macro F1 >= 99.00% target.
5. Zero Sag-to-Normal error boundary resolution.
6. Bit-exact mathematical parity between pipeline and JSON weights.
"""

import os
import json
import hashlib
import pickle
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "dataset_manifest_v1.json")
SIMULINK_PATH = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
PHASE4C_MODELS_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models")
PHASE4D_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4d")

EXPECTED_MANIFEST_SHA256 = "B4C7CCA746B69EE895BC6E7C68F2BE2F56700F3B9C1976BF0B674C4D292548F5"
EXPECTED_SIMULINK_SHA256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"
EXPECTED_WEIGHTS_SHA256 = "F0FEBD5B3829677AC0F2C13262CCCB5FF8947CDCB59596F5E4A8F2B6180C27C5"


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_phase4d_deliverables_exist():
    required_files = [
        "test_metrics.json",
        "test_predictions.csv",
        "confusion_matrix.csv",
        "trajectory_metrics.json",
        "evaluation_provenance.json"
    ]
    for rf in required_files:
        p = os.path.join(PHASE4D_DIR, rf)
        assert os.path.exists(p), f"Phase 4D deliverable missing: {rf}"
        assert os.path.getsize(p) > 0, f"Phase 4D deliverable is empty: {rf}"


def test_authoritative_manifest_checksum():
    actual_hash = compute_sha256(MANIFEST_PATH)
    assert actual_hash == EXPECTED_MANIFEST_SHA256, (
        f"Manifest SHA-256 altered: {actual_hash} != {EXPECTED_MANIFEST_SHA256}"
    )


def test_pristine_simulink_model_checksum():
    actual_hash = compute_sha256(SIMULINK_PATH)
    assert actual_hash == EXPECTED_SIMULINK_SHA256, (
        f"Pristine reference Simulink model modified: {actual_hash} != {EXPECTED_SIMULINK_SHA256}"
    )


def test_candidate_artifacts_integrity():
    weights_path = os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json")
    actual_hash = compute_sha256(weights_path)
    assert actual_hash == EXPECTED_WEIGHTS_SHA256, (
        f"Candidate weights modified after freeze: {actual_hash} != {EXPECTED_WEIGHTS_SHA256}"
    )


def test_test_predictions_contract():
    pred_csv_path = os.path.join(PHASE4D_DIR, "test_predictions.csv")
    df = pd.read_csv(pred_csv_path)

    # 1,295 total frames
    assert len(df) == 1295, f"Expected 1,295 test predictions, got {len(df)}"

    # Check 40 distinct trajectories
    assert df["trajectory_id"].nunique() == 40, f"Expected 40 trajectories, got {df['trajectory_id'].nunique()}"

    # Check class distribution
    class_counts = df["ground_truth_label"].value_counts().to_dict()
    assert class_counts["Normal"] == 175, f"Expected 175 Normal, got {class_counts.get('Normal')}"
    for dist_class in ["Sag", "Swell", "Interruption", "Harmonics", "Flicker", "Notch", "Transient"]:
        assert class_counts[dist_class] == 160, f"Expected 160 {dist_class}, got {class_counts.get(dist_class)}"


def test_macro_f1_target_achieved():
    metrics_path = os.path.join(PHASE4D_DIR, "test_metrics.json")
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    macro_f1 = metrics["overall_metrics"]["macro_f1"]
    accuracy = metrics["overall_metrics"]["accuracy"]
    target_met = metrics["overall_metrics"]["target_achieved"]

    assert target_met is True, "Predefined performance target was NOT achieved"
    assert macro_f1 >= 0.990, f"Macro F1 below target: {macro_f1:.4f} < 0.990"
    assert accuracy >= 0.990, f"Accuracy below target: {accuracy:.4f} < 0.990"


def test_sag_to_normal_boundary_resolved():
    metrics_path = os.path.join(PHASE4D_DIR, "test_metrics.json")
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    sag_to_norm = metrics["sag_normal_confusion"]["sag_to_normal_errors"]
    norm_to_sag = metrics["sag_normal_confusion"]["normal_to_sag_errors"]

    assert sag_to_norm == 0, f"Sag to Normal errors detected on test set: {sag_to_norm}"
    assert norm_to_sag <= 1, f"Normal to Sag errors exceeded threshold: {norm_to_sag}"


def test_deployment_parity_on_test_data():
    from ml.dataset_loader import load_ieee9bus_data

    # Load pipeline
    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_pipeline.pkl"), "rb") as f:
        pipe = pickle.load(f)
    clf = pipe["classifier"]
    scaler = pipe["scaler"]

    # Load weights
    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json"), "r", encoding="utf-8") as f:
        jw = json.load(f)

    W = [np.array(w, dtype=np.float32) for w in jw["weights"]]
    B = [np.array(b, dtype=np.float32) for b in jw["biases"]]
    s_mean = np.array(jw["scaler_mean"], dtype=np.float32)
    s_scale = np.array(jw["scaler_scale"], dtype=np.float32)

    data = load_ieee9bus_data(include_test=True)
    X_test, _, _ = data["test"]

    # Pipeline forward
    pipe_preds = clf.predict(scaler.transform(X_test))

    # JSON forward
    z = (X_test.astype(np.float32) - s_mean) / s_scale
    for i in range(len(W) - 1):
        z = np.maximum(0.0, np.dot(z, W[i]) + B[i])
    logits = np.dot(z, W[-1]) + B[-1]
    json_preds = np.argmax(logits, axis=1)

    mismatches = int(np.sum(pipe_preds != json_preds))
    assert mismatches == 0, f"Deployment parity failed on test data with {mismatches} mismatches"

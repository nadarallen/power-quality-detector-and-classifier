"""
Tests for dashboard backend utilities
"""

import pytest
import numpy as np
from dashboard_backend import (
    CLASSES,
    CANONICAL_32_FEATURES,
    get_available_npz_files,
    load_waveform_sample,
    extract_features_for_frame,
    load_candidate_model,
    predict_phase_features,
    load_benchmark_summary
)


def test_classes_and_features():
    assert len(CLASSES) == 8
    assert len(CANONICAL_32_FEATURES) == 32
    assert "rms_voltage" in CANONICAL_32_FEATURES
    assert "thd" in CANONICAL_32_FEATURES
    assert "true_dominant_freq" in CANONICAL_32_FEATURES


def test_get_available_npz_files():
    files = get_available_npz_files()
    assert len(files) == 8
    for c in CLASSES:
        assert c in files


def test_load_waveform_sample():
    wv, meta = load_waveform_sample("Sag", index=0)
    assert wv.shape == (1000, 3)
    assert meta["class"] == "Sag"
    assert meta["total_in_class"] > 0
    assert "frame_id" in meta


def test_extract_features_for_frame():
    wv, _ = load_waveform_sample("Normal", index=0)
    feats = extract_features_for_frame(wv, sample_rate=5000.0, f0=60.0)
    assert "Phase A" in feats
    assert "Phase B" in feats
    assert "Phase C" in feats
    assert len(feats["Phase A"]) == 32
    for k in CANONICAL_32_FEATURES:
        assert k in feats["Phase A"]
        assert isinstance(feats["Phase A"][k], float)


def test_load_candidate_model_and_predict():
    scaler, clf = load_candidate_model()
    assert scaler is not None
    assert clf is not None

    wv, _ = load_waveform_sample("Sag", index=0)
    feats = extract_features_for_frame(wv, sample_rate=5000.0, f0=60.0)
    pred_res = predict_phase_features(feats["Phase A"], scaler, clf)
    
    assert "predicted_class" in pred_res
    assert "confidence" in pred_res
    assert 0.0 <= pred_res["confidence"] <= 1.0
    assert len(pred_res["probabilities"]) == 8


def test_load_benchmark_summary():
    summary = load_benchmark_summary()
    assert "phase4b" in summary
    assert "phase4d" in summary
    assert "models_summary" in summary["phase4b"]
    assert "overall_metrics" in summary["phase4d"]
    assert summary["phase4d"]["overall_metrics"]["accuracy"] > 0.99

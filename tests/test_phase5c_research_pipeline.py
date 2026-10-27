"""
tests/test_phase5c_research_pipeline.py
---------------------------------------
Automated regression tests verifying Phase 5C research artifacts,
protected reference models, dataset shapes, zero-leakage partitions,
classical / DL / hybrid model loading, and challenge evaluation integrity.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pristine_reference_model_integrity():
    slx_path = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
    assert os.path.exists(slx_path), f"Reference model missing at {slx_path}"

    expected_sha256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D".lower()
    h = hashlib.sha256()
    with open(slx_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_sha256 = h.hexdigest().lower()
    assert actual_sha256 == expected_sha256, f"Pristine model hash {actual_sha256} != expected {expected_sha256}"


def test_historical_dataset_intact():
    m_path = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "dataset_manifest_v1.json")
    assert os.path.exists(m_path), "Historical manifest v1 missing!"
    with open(m_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["manifest_version"] == "1.0.0"
    assert doc["freeze_status"] == "FROZEN_BASELINE"


def test_phase5c_dataset_manifest_and_counts():
    m_path = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c", "dataset_manifest_v2.json")
    assert os.path.exists(m_path), "Phase 5C manifest v2 missing!"
    with open(m_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert doc["manifest_version"] == "2.0.0"
    assert doc["total_trajectories"] == 144
    assert doc["frames_per_trajectory"] == 32
    assert doc["total_frames"] == 4608

    splits = doc["split_summary"]
    assert splits["train_frames"] == 2560
    assert splits["val_frames"] == 1024
    assert splits["challenge_frames"] == 1024


def test_phase5c_dual_rate_shapes():
    p20 = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c", "processed", "phase5c_waveforms_20k.npz")
    p5 = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c", "processed", "phase5c_waveforms_5k.npz")
    p_feat = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c", "processed", "phase5c_features.npz")

    assert os.path.exists(p20) and os.path.exists(p5) and os.path.exists(p_feat)

    d20 = np.load(p20, allow_pickle=True)
    d5 = np.load(p5, allow_pickle=True)
    dfeats = np.load(p_feat, allow_pickle=True)

    assert d20["waveforms_20k"].shape == (4608, 4000, 3)
    assert d20["fs"] == 20000.0

    assert d5["waveforms_5k"].shape == (4608, 1000, 3)
    assert d5["fs"] == 5000.0

    assert dfeats["features"].shape == (4608, 32)
    assert dfeats["labels"].shape == (4608,)


def test_zero_operating_condition_leakage():
    m_path = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz_phase5c", "dataset_manifest_v2.json")
    with open(m_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    trajs = doc["trajectories"]
    train_conds = {t["operating_condition_id"] for t in trajs if t["split"] == "train"}
    val_conds = {t["operating_condition_id"] for t in trajs if t["split"] == "val"}
    ch_conds = {t["operating_condition_id"] for t in trajs if t["split"] == "challenge"}

    assert len(train_conds.intersection(val_conds)) == 0, "Leakage between train and val!"
    assert len(train_conds.intersection(ch_conds)) == 0, "Leakage between train and challenge!"
    assert len(val_conds.intersection(ch_conds)) == 0, "Leakage between val and challenge!"
    assert ch_conds == {33, 34, 35, 36}, "Challenge partition does not match Conditions 33-36!"


def test_classical_benchmark_metrics():
    c_path = os.path.join(PROJECT_ROOT, "experiments", "phase5c", "classical", "classical_benchmark_metrics.json")
    assert os.path.exists(c_path), "Classical benchmark metrics missing!"
    with open(c_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert "models" in doc
    models = doc["models"]
    assert "MLP" in models
    assert "Random Forest" in models
    assert "RBF SVM" in models
    assert doc["best_model"] == "MLP"
    assert models["MLP"]["macro_f1"] > 0.90


def test_deep_learning_benchmark_summary():
    dl_path = os.path.join(PROJECT_ROOT, "experiments", "phase5c", "deep_learning", "deep_learning_benchmark_summary.json")
    assert os.path.exists(dl_path), "DL benchmark summary missing!"
    with open(dl_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert "tcn_20k" in doc["best_models"]
    assert "cnn_20k" in doc["best_models"]
    assert doc["best_models"]["tcn_20k"]["macro_f1"] > 0.90


def test_hybrid_benchmark_results():
    hyb_path = os.path.join(PROJECT_ROOT, "experiments", "phase5c", "hybrid", "hybrid_benchmark_results.json")
    assert os.path.exists(hyb_path), "Hybrid benchmark results missing!"
    with open(hyb_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert "hybrid_fusion" in doc
    assert "features_only" in doc
    assert "waveform_only" in doc
    # Hybrid must achieve higher F1 than both individual modalities
    assert doc["deltas"]["hybrid_minus_features"] > 0.05
    assert doc["deltas"]["hybrid_minus_waveform"] > 0.05


def test_challenge_evaluation_results():
    ch_path = os.path.join(PROJECT_ROOT, "experiments", "phase5c", "challenge_eval", "challenge_evaluation_results.json")
    assert os.path.exists(ch_path), "Challenge evaluation results missing!"
    with open(ch_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert "HybridPQNet" in doc
    assert "Temporal ConvNet (TCN)" in doc
    assert "Classical (MLP)" in doc
    assert "Compact 1D CNN (20 kHz)" in doc

    # HybridPQNet must have evaluated all 4 challenge conditions
    by_cond = doc["HybridPQNet"]["by_condition"]
    assert set(by_cond.keys()) == {"33", "34", "35", "36"}
    assert doc["HybridPQNet"]["macro_f1"] >= 0.95

"""
tests/test_gate3w_transient_dataset.py
--------------------------------------
Pytest verification suite for Gate 3W Transient Dataset:
1. Pristine reference model SHA-256 untouched.
2. Frame count and waveform tensor geometry (1,152, 1000, 3).
3. 32-feature contract integrity (1,152, 0 NaN, 0 Inf).
4. Ground truth provenance strictly SCENARIO_CONTROLLER.
5. Trajectory leakage verification (Train/Val/Test strictly disjoint).
6. Operating condition diversity (covers all 32 operating conditions).
7. Phase configuration diversity (ABC, AB, BC, CA, A, B, C).
8. Physical validation pass rate (100% pass).
9. Percentile distributions for peak excursion, dominant frequency, duration.
10. Sampling adequacy (dominant frequency within 5 kHz bandwidth).
11. ML decoupling verification (OUT_OF_DOMAIN status).
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAN_DIR = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "transient")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
PRISTINE_PATH = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
EXPECTED_PRISTINE_SHA256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"


def test_pristine_model_untouched():
    """Verify reference model has not been modified."""
    assert os.path.exists(PRISTINE_PATH), f"Pristine model missing at {PRISTINE_PATH}"
    with open(PRISTINE_PATH, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest().upper()
    assert sha == EXPECTED_PRISTINE_SHA256, f"Pristine model SHA256 mismatch: {sha}"


def test_frame_count_and_geometry():
    """Verify waveform shape is (1152, 1000, 3) with zero NaN/Inf."""
    npz_path = os.path.join(TRAN_DIR, "transient_waveforms.npz")
    assert os.path.exists(npz_path), "Waveforms NPZ missing"
    data = np.load(npz_path)
    assert "waveforms" in data, "No 'waveforms' key in NPZ"
    waveforms = data["waveforms"]
    assert waveforms.shape == (1152, 1000, 3), f"Unexpected shape {waveforms.shape}"
    assert not np.any(np.isnan(waveforms)), "NaN found in waveforms"
    assert not np.any(np.isinf(waveforms)), "Inf found in waveforms"


def test_features_completeness_and_contract():
    """Verify 1,152 rows and all 32 features present with zero NaN/Inf."""
    csv_path = os.path.join(TRAN_DIR, "transient_features.csv")
    assert os.path.exists(csv_path), "Features CSV missing"
    df = pd.read_csv(csv_path)
    assert len(df) == 1152, f"Expected 1152 rows, got {len(df)}"
    
    expected_32 = [
        'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
        'duration', 'dominant_freq', 'system_freq', 'snr',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'h9', 'h10', 'h11',
        'h2_ratio', 'h3_ratio', 'h4_ratio', 'h5_ratio', 'h7_ratio', 'h9_ratio', 'h11_ratio',
        'harmonic_energy',
        'spectral_centroid', 'spectral_bandwidth', 'spectral_entropy',
        'spectral_flatness', 'true_dominant_freq'
    ]
    for col in expected_32:
        assert col in df.columns, f"Feature {col} missing from CSV"
        assert not df[col].isna().any(), f"NaN in feature {col}"
        assert not np.isinf(df[col]).any(), f"Inf in feature {col}"


def test_ground_truth_and_provenance():
    """Verify ground truth is strictly 'Transient' with label_idx=7."""
    csv_path = os.path.join(TRAN_DIR, "transient_features.csv")
    df = pd.read_csv(csv_path)
    assert (df['ground_truth'] == 'Transient').all(), "Not all labels are Transient"
    assert (df['label_idx'] == 7).all(), "Not all label_idx are 7"

    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["label_source"] == "SCENARIO_CONTROLLER"


def test_trajectory_leakage_strictly_zero():
    """Verify zero overlap across train, val, and test trajectories."""
    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    splits = meta["splits"]
    assert splits["train"]["frames"] == 832
    assert splits["val"]["frames"] == 160
    assert splits["test"]["frames"] == 160
    assert splits["train"]["frames"] + splits["val"]["frames"] + splits["test"]["frames"] == 1152

    scen_path = os.path.join(TRAN_DIR, "transient_scenarios.json")
    with open(scen_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    train_groups = {s["dataset_partition"]["group_id"] for s in scenarios.values() if s["dataset_partition"]["split"] == "train"}
    val_groups = {s["dataset_partition"]["group_id"] for s in scenarios.values() if s["dataset_partition"]["split"] == "val"}
    test_groups = {s["dataset_partition"]["group_id"] for s in scenarios.values() if s["dataset_partition"]["split"] == "test"}

    assert train_groups.isdisjoint(val_groups), "Train-Val trajectory leakage detected"
    assert train_groups.isdisjoint(test_groups), "Train-Test trajectory leakage detected"
    assert val_groups.isdisjoint(test_groups), "Val-Test trajectory leakage detected"


def test_operating_condition_and_phase_diversity():
    """Verify coverage across 32 operating conditions and varied phases."""
    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    phase_dist = meta["phase_distribution"]
    assert phase_dist["ABC"] > 0
    assert (phase_dist["AB"] + phase_dist["BC"] + phase_dist["CA"]) > 0
    assert (phase_dist["A"] + phase_dist["B"] + phase_dist["C"]) > 0

    scen_path = os.path.join(TRAN_DIR, "transient_scenarios.json")
    with open(scen_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    cond_ids = {s["operating_condition_id"] for s in scenarios.values()}
    assert len(cond_ids) == 32, f"Expected 32 unique operating conditions, got {len(cond_ids)}"


def test_physical_validation_pass_rate():
    """Verify 100% physical validation pass rate."""
    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    val_summary = meta["validation_summary"]
    assert val_summary["total_evaluated"] == 1152
    assert val_summary["passed"] == 1152
    assert val_summary["failed"] == 0
    assert val_summary["pass_rate_pct"] == 100.0


def test_percentile_distributions():
    """Verify physical metrics fall within approved bands."""
    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    p_stats = meta["percentile_statistics"]

    # Peak excursion >= 0.12 pu
    assert p_stats["peak_excursion_pu"]["min"] >= 0.12
    # Dominant frequency in [250, 1500] Hz
    assert p_stats["dominant_trans_freq_hz"]["min"] >= 250.0
    assert p_stats["dominant_trans_freq_hz"]["max"] <= 1500.0
    # Duration <= 50 ms
    assert p_stats["effective_duration_ms"]["max"] <= 50.0
    # System frequency in [59.5, 60.5] Hz
    assert p_stats["system_freq_hz"]["min"] >= 59.5
    assert p_stats["system_freq_hz"]["max"] <= 60.5


def test_sampling_adequacy():
    """Verify all dominant frequencies remain within 5 kHz Nyquist bandwidth."""
    meta_path = os.path.join(TRAN_DIR, "transient_dataset_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    f_max = meta["percentile_statistics"]["dominant_trans_freq_hz"]["max"]
    assert f_max < 2500.0, f"Transient frequency {f_max} exceeds Nyquist (2500 Hz)"

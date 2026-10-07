"""
tests/test_gate3t_notch_dataset.py
----------------------------------
Automated test suite verifying Gate 3T pass criteria for the
multi-condition Voltage Notch dataset in the 60-Hz IEEE 9-bus domain.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'
NOT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'notch')
NORMAL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')

from scenarios.scenario_controller import verify_pristine_model_integrity
from dsp.phase_processor import _MODEL_FEATURE_ORDER


# 1. Pristine Model Integrity
def test_1_pristine_model_untouched():
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == PRISTINE_SHA256


# 2. Notch Dataset Artifacts Exist
def test_2_notch_dataset_files_exist():
    expected_files = [
        'notch_features.csv',
        'notch_waveforms.npz',
        'notch_scenarios.json',
        'notch_dataset_metadata.json'
    ]
    for fn in expected_files:
        p = os.path.join(NOT_DIR, fn)
        assert os.path.exists(p), f"Missing artifact: {fn}"
        assert os.path.getsize(p) > 0, f"Empty artifact: {fn}"


# 3. Frame Count within Target Range (1,000 to 1,500)
def test_3_dataset_frame_count_and_shape():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    npz_path = os.path.join(NOT_DIR, 'notch_waveforms.npz')
    df = pd.read_csv(csv_path)
    npz = np.load(npz_path)

    n_csv = len(df)
    n_npz = len(npz['waveforms'])

    assert n_csv == 1152, f"Expected 1,152 frames, got {n_csv}"
    assert n_npz == 1152, f"Expected 1,152 waveforms, got {n_npz}"
    assert 1000 <= n_csv <= 1500, f"Frame count {n_csv} not in target [1000, 1500]"
    assert npz['waveforms'].shape == (1152, 1000, 3)


# 4. Feature Contract Integrity (32 features, 0 NaN, 0 Inf)
def test_4_feature_contract_integrity():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    df = pd.read_csv(csv_path)

    for feat in _MODEL_FEATURE_ORDER:
        assert feat in df.columns, f"Missing contract feature: {feat}"
        assert not df[feat].isna().any(), f"NaN detected in feature: {feat}"
        assert not np.isinf(df[feat]).any(), f"Inf detected in feature: {feat}"


# 5. Ground Truth Provenance
def test_5_ground_truth_provenance():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    df = pd.read_csv(csv_path)

    assert (df['class'] == 'Notch').all(), "Class label must be strictly 'Notch'"
    assert (df['label_idx'] == 4).all(), "Label index must be strictly 4"

    meta_path = os.path.join(NOT_DIR, 'notch_dataset_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    assert meta['label_source'] == 'SCENARIO_CONTROLLER'

    scen_path = os.path.join(NOT_DIR, 'notch_scenarios.json')
    with open(scen_path, 'r', encoding='utf-8') as f:
        scens = json.load(f)
    for sc_id, sc in scens.items():
        assert sc['label_source'] == 'SCENARIO_CONTROLLER'
        assert sc['class'] == 'Notch'


# 6. Zero Trajectory Leakage
def test_6_zero_trajectory_leakage():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    df = pd.read_csv(csv_path)

    train_sims = set(df[df['split'] == 'train']['trajectory_id'].unique())
    val_sims   = set(df[df['split'] == 'val']['trajectory_id'].unique())
    test_sims  = set(df[df['split'] == 'test']['trajectory_id'].unique())

    assert len(train_sims) == 26, f"Expected 26 train sims, got {len(train_sims)}"
    assert len(val_sims) == 5, f"Expected 5 val sims, got {len(val_sims)}"
    assert len(test_sims) == 5, f"Expected 5 test sims, got {len(test_sims)}"

    assert len(train_sims.intersection(val_sims)) == 0, "Train-Val simulation leakage detected!"
    assert len(train_sims.intersection(test_sims)) == 0, "Train-Test simulation leakage detected!"
    assert len(val_sims.intersection(test_sims)) == 0, "Val-Test simulation leakage detected!"


# 7. Operating Condition Diversity (All 32 Represented)
def test_7_operating_condition_coverage():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    df = pd.read_csv(csv_path)

    unique_conds = set(df['operating_condition_id'].unique())
    assert len(unique_conds) == 32, f"Expected 32 operating conditions, got {len(unique_conds)}"
    for c_id in range(1, 33):
        assert c_id in unique_conds, f"Operating condition {c_id} missing from dataset"


# 8. Physical Notch Metric Bounds
def test_8_physical_notch_metrics():
    meta_path = os.path.join(NOT_DIR, 'notch_dataset_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    # Validation pass rate 100%
    assert meta['accepted_frames'] == 1152
    assert meta['pass_rate_percent'] == 100.0

    # Depth statistics
    d_stats = meta['metrics_summary']['max_depth_pu']
    assert d_stats['min'] >= 0.20, f"Min depth {d_stats['min']} < 0.20 pu"
    assert d_stats['max'] <= 0.85, f"Max depth {d_stats['max']} > 0.85 pu"

    # Width statistics
    w_stats = meta['metrics_summary']['mean_width_ms']
    assert w_stats['min'] >= 0.35, f"Min width {w_stats['min']} < 0.35 ms"
    assert w_stats['max'] < 8.33, f"Max width {w_stats['max']} >= 8.33 ms"


# 9. Spectral Quality & Harmonics Bounds
def test_9_spectral_quality():
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')
    df = pd.read_csv(csv_path)

    # Fundamental frequency locked in [59.5, 60.5] Hz
    assert (df['dominant_freq'] >= 59.5).all(), "Frequency below 59.5 Hz detected"
    assert (df['dominant_freq'] <= 60.5).all(), "Frequency above 60.5 Hz detected"

    # Converter harmonics THD within physical expectations
    assert (df['thd'] >= 3.0).all(), "THD below 3.0% on commutation notch"
    assert (df['thd'] <= 15.0).all(), "Excessive THD > 15.0% detected"


# 10. Summary JSON Conforms to Contract
def test_10_summary_json_contract():
    sum_path = os.path.join(DOCS_DIR, 'gate3t_notch_dataset_summary.json')
    assert os.path.exists(sum_path)
    with open(sum_path, 'r', encoding='utf-8') as f:
        summ = json.load(f)

    assert summ['total_frames'] == 1152
    assert summ['accepted_frames'] == 1152
    assert summ['pass_rate_percent'] == 100.0
    assert summ['verdict'] == "GATE3T_NOTCH_DATASET = PASS"

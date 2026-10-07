"""
tests/test_gate3q_flicker_dataset.py
------------------------------------
Automated test suite verifying Gate 3Q and Gate 3R pass criteria for the
multi-condition Voltage Flicker dataset in the 60-Hz IEEE 9-bus domain.
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
FLK_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'flicker')
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


# 2. Flicker Dataset Artifacts Exist
def test_2_flicker_dataset_files_exist():
    expected_files = [
        'flicker_features.csv',
        'flicker_waveforms.npz',
        'flicker_scenarios.json',
        'flicker_dataset_metadata.json'
    ]
    for fn in expected_files:
        p = os.path.join(FLK_DIR, fn)
        assert os.path.exists(p), f"Missing artifact: {fn}"
        assert os.path.getsize(p) > 0, f"Empty artifact: {fn}"


# 3. Frame Count within Target Range (1,000 to 1,500)
def test_3_dataset_frame_count_and_shape():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    npz_path = os.path.join(FLK_DIR, 'flicker_waveforms.npz')
    df = pd.read_csv(csv_path)
    npz = np.load(npz_path)

    n_csv = len(df)
    n_npz = len(npz['waveforms'])

    assert n_csv == 1152, f"Expected 1,152 frames, got {n_csv}"
    assert n_npz == 1152, f"Expected 1,152 waveforms, got {n_npz}"
    assert 1000 <= n_csv <= 1500, f"Frame count {n_csv} not in target [1000, 1500]"
    assert npz['waveforms'].shape == (1152, 1000, 3)
    if 'currents' in npz:
        assert npz['currents'].shape == (1152, 1000, 3)


# 4. Feature Contract Integrity (32 features, 0 NaN, 0 Inf)
def test_4_feature_contract_integrity():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    for feat in _MODEL_FEATURE_ORDER:
        assert feat in df.columns, f"Missing contract feature: {feat}"
        assert not df[feat].isna().any(), f"NaN detected in feature: {feat}"
        assert not np.isinf(df[feat]).any(), f"Inf detected in feature: {feat}"


# 5. Ground Truth Provenance
def test_5_ground_truth_provenance():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    assert (df['class'] == 'Flicker').all(), "Class label must be strictly 'Flicker'"
    assert (df['label_idx'] == 0).all(), "Label index must be strictly 0"
    assert (df['label_source'] == 'SCENARIO_CONTROLLER').all(), "Label source must be SCENARIO_CONTROLLER"


# 6. Zero Trajectory Leakage
def test_6_zero_trajectory_leakage():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    train_sims = set(df[df['split'] == 'train']['simulation_id'].unique())
    val_sims   = set(df[df['split'] == 'val']['simulation_id'].unique())
    test_sims  = set(df[df['split'] == 'test']['simulation_id'].unique())

    assert len(train_sims) == 26, f"Expected 26 train sims, got {len(train_sims)}"
    assert len(val_sims) == 5, f"Expected 5 val sims, got {len(val_sims)}"
    assert len(test_sims) == 5, f"Expected 5 test sims, got {len(test_sims)}"

    assert len(train_sims.intersection(val_sims)) == 0, "Train-Val simulation leakage detected!"
    assert len(train_sims.intersection(test_sims)) == 0, "Train-Test simulation leakage detected!"
    assert len(val_sims.intersection(test_sims)) == 0, "Val-Test simulation leakage detected!"


# 7. Operating Conditions Coverage (All 32 conditions represented)
def test_7_operating_conditions_coverage():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    unique_conds = set(df['operating_condition_id'].unique())
    assert len(unique_conds) == 32, f"Expected all 32 operating conditions, got {len(unique_conds)}"
    assert unique_conds == set(range(1, 33))


# 8. Phase Diversity
def test_8_phase_diversity():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    phases = df['phase_configuration'].value_counts()
    assert 'ABC' in phases, "Missing three-phase flicker"
    assert phases['ABC'] == 768, f"Expected 768 three-phase frames, got {phases['ABC']}"
    assert sum(phases.get(p, 0) for p in ['A', 'B', 'C']) == 192, "Expected 192 single-phase frames"
    assert sum(phases.get(p, 0) for p in ['AB', 'BC', 'CA']) == 192, "Expected 192 two-phase frames"


# 9. Modulation Parameter Coverage (Depth and Frequency)
def test_9_modulation_parameter_distributions():
    csv_path = os.path.join(FLK_DIR, 'flicker_features.csv')
    df = pd.read_csv(csv_path)

    depths = df['envelope_depth_measured'].values
    freqs = df['modulation_freq_measured_hz'].values

    assert np.min(depths) >= 0.02, f"Min depth {np.min(depths)} below Gate 3C lower bound (0.02)"
    assert np.max(depths) <= 0.15, f"Max depth {np.max(depths)} above Gate 3C upper bound (0.15)"
    assert np.min(freqs) >= 3.0, f"Min frequency {np.min(freqs)} below Gate 3C lower bound (3.0)"
    assert np.max(freqs) <= 20.0, f"Max frequency {np.max(freqs)} above Gate 3C upper bound (20.0)"


# 10. Physical Acceptance Rate (100% accepted, 0 rejections)
def test_10_physical_acceptance_rate():
    meta_path = os.path.join(FLK_DIR, 'flicker_dataset_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    pv = meta['physical_validation']
    assert pv['total_evaluated'] == 1152
    assert pv['passed'] == 1152
    assert pv['rejected'] == 0
    assert pv['pass_rate_pct'] == 100.0


# 11. Legacy ML Decoupling
def test_11_ml_decoupling():
    meta_path = os.path.join(FLK_DIR, 'flicker_dataset_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    ml_diag = meta.get('ml_decoupling', {})
    assert ml_diag.get('decoupled') is True
    assert ml_diag.get('model_domain_status') == 'OUT_OF_DOMAIN'
    assert len(ml_diag.get('sample_evaluations', [])) > 0

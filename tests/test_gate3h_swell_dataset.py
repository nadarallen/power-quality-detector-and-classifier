"""
tests/test_gate3h_swell_dataset.py
----------------------------------
Test suite for Gate 3H — Voltage Swell Dataset Generation.
Verifies:
1. Target frame count (1,000–1,500 unique frames, exactly 1,152).
2. 100% physical validation pass rate.
3. Zero NaN, zero Inf across all features and waveforms.
4. Zero duplicate waveforms or feature rows.
5. Operating condition coverage (all 32 conditions represented).
6. Phase coverage (three-phase and phase-to-phase).
7. Zero cross-split trajectory leakage (Train, Val, Test).
8. Pristine Simulink model remains unchanged.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWELL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'swell')
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
EXPECTED_PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'


def test_1_pristine_model_untouched():
    """Verify the pristine electrical model has not been altered."""
    assert os.path.exists(PRISTINE_MODEL), "Pristine model does not exist"
    with open(PRISTINE_MODEL, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_PRISTINE_SHA256, f"Pristine model SHA256 mismatch: {sha256}"


def test_2_swell_dataset_files_exist():
    """Verify all 4 core dataset files exist."""
    feat_path = os.path.join(SWELL_DIR, 'swell_features.csv')
    wave_path = os.path.join(SWELL_DIR, 'swell_waveforms.npz')
    scen_path = os.path.join(SWELL_DIR, 'swell_scenarios.json')
    meta_path = os.path.join(SWELL_DIR, 'swell_dataset_metadata.json')

    assert os.path.exists(feat_path), f"Features CSV missing at {feat_path}"
    assert os.path.exists(wave_path), f"Waveforms NPZ missing at {wave_path}"
    assert os.path.exists(scen_path), f"Scenarios JSON missing at {scen_path}"
    assert os.path.exists(meta_path), f"Metadata JSON missing at {meta_path}"


def test_3_dataset_frame_count():
    """Verify frame count is within the approved 1,000–1,500 target (1,152)."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    waveforms = np.load(os.path.join(SWELL_DIR, 'swell_waveforms.npz'))['waveforms']

    assert len(df) == 1152, f"Expected 1,152 feature rows, got {len(df)}"
    assert waveforms.shape == (1152, 1000, 3), f"Expected shape (1152, 1000, 3), got {waveforms.shape}"


def test_4_zero_nan_zero_inf():
    """Verify zero NaN and zero Inf across all features and waveforms."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    waveforms = np.load(os.path.join(SWELL_DIR, 'swell_waveforms.npz'))['waveforms']

    assert not df.isna().any().any(), "Features CSV contains NaN"
    assert not np.isnan(waveforms).any(), "Waveforms contain NaN"
    assert not np.isinf(waveforms).any(), "Waveforms contain Inf"


def test_5_zero_duplicates():
    """Verify all 1,152 waveforms are genuinely distinct with zero duplicate rows."""
    waveforms = np.load(os.path.join(SWELL_DIR, 'swell_waveforms.npz'))['waveforms']
    hashes = set()
    for i in range(waveforms.shape[0]):
        h = hashlib.sha256(waveforms[i].tobytes()).hexdigest()
        assert h not in hashes, f"Duplicate waveform found at index {i}"
        hashes.add(h)
    assert len(hashes) == 1152, "Expected 1,152 unique waveform hashes"


def test_6_operating_condition_coverage():
    """Verify that all 32 operating conditions are represented in the dataset."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    conds = set(df['operating_condition_id'].unique())
    expected_conds = set(range(1, 33))
    assert expected_conds.issubset(conds), f"Missing operating conditions: {expected_conds - conds}"


def test_7_phase_coverage():
    """Verify that both three-phase and phase-to-phase swells are represented."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    phase_types = set(df['phase_config'].unique())
    assert 'three-phase' in phase_types, "Missing three-phase swells"
    assert 'phase-to-phase' in phase_types, "Missing phase-to-phase swells"


def test_8_leakage_prevention():
    """Verify zero cross-split simulation trajectory leakage."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    train_sims = set(df[df['split'] == 'train']['simulation_id'].unique())
    val_sims   = set(df[df['split'] == 'val']['simulation_id'].unique())
    test_sims  = set(df[df['split'] == 'test']['simulation_id'].unique())

    assert train_sims.isdisjoint(val_sims), "Leakage between train and val"
    assert train_sims.isdisjoint(test_sims), "Leakage between train and test"
    assert val_sims.isdisjoint(test_sims), "Leakage between val and test"


def test_9_ground_truth_purity():
    """Verify ground truth is strictly 'Swell' and originates from scenario controller."""
    df = pd.read_csv(os.path.join(SWELL_DIR, 'swell_features.csv'))
    assert (df['class'] == 'Swell').all(), "Ground truth is not uniformly 'Swell'"
    assert (df['label_idx'] == 6).all(), "Label index is not 6 for Swell"
    assert (df['label_source'] == 'SCENARIO_CONTROLLER').all(), "Label source not SCENARIO_CONTROLLER"


def test_10_physical_validation_100_percent():
    """Verify 100% of frames passed independent physical validation."""
    with open(os.path.join(SWELL_DIR, 'swell_dataset_metadata.json'), 'r') as f:
        meta = json.load(f)
    assert meta['num_frames'] == 1152, f"Expected 1,152 frames, got {meta['num_frames']}"
    assert meta['purity_verification']['physical_validation_pass_rate'] == 1.0
    assert meta['purity_verification']['rejected_frames_count'] == 0


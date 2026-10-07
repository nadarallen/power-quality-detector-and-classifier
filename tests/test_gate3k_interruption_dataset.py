"""
tests/test_gate3k_interruption_dataset.py
-----------------------------------------
Automated test suite verifying all Gate 3K pass criteria for the
multi-condition Voltage Interruption dataset in the 60-Hz IEEE 9-bus domain.
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
INT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'interruption')

from scenarios.scenario_controller import verify_pristine_model_integrity
from dsp.phase_processor import _MODEL_FEATURE_ORDER


# 1. Pristine Model Integrity
def test_1_pristine_model_untouched():
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == PRISTINE_SHA256


# 2. Interruption Dataset Artifacts Exist
def test_2_interruption_dataset_files_exist():
    expected_files = [
        'interruption_features.csv',
        'interruption_waveforms.npz',
        'interruption_scenarios.json',
        'interruption_dataset_metadata.json'
    ]
    for fn in expected_files:
        p = os.path.join(INT_DIR, fn)
        assert os.path.exists(p), f"Missing artifact: {fn}"
        assert os.path.getsize(p) > 0, f"Empty artifact: {fn}"


# 3. Frame Count within Target Range (1,000 to 1,500)
def test_3_dataset_frame_count():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    npz_path = os.path.join(INT_DIR, 'interruption_waveforms.npz')
    df = pd.read_csv(csv_path)
    npz = np.load(npz_path)
    
    n_csv = len(df)
    n_npz = len(npz['waveforms'])
    
    assert n_csv == 1152, f"Expected 1,152 frames, got {n_csv}"
    assert n_npz == 1152, f"Expected 1,152 waveforms, got {n_npz}"
    assert 1000 <= n_csv <= 1500, f"Frame count {n_csv} not in target [1000, 1500]"
    assert npz['waveforms'].shape == (1152, 1000, 3)


# 4. Numerical Integrity (Zero NaN, Zero Inf)
def test_4_zero_nan_zero_inf():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    npz_path = os.path.join(INT_DIR, 'interruption_waveforms.npz')
    npz = np.load(npz_path)
    waveforms = npz['waveforms']
    
    # Check waveforms
    assert not np.isnan(waveforms).any(), "NaN found in waveform arrays"
    assert not np.isinf(waveforms).any(), "Inf found in waveform arrays"
    
    # Check 32 model features
    for fn in _MODEL_FEATURE_ORDER:
        assert fn in df.columns, f"Feature {fn} missing from CSV"
        assert not df[fn].isna().any(), f"NaN found in feature {fn}"
        assert not np.isinf(df[fn]).any(), f"Inf found in feature {fn}"


# 5. Uniqueness (Zero Duplicate Rows, Zero Identical Waveforms)
def test_5_zero_duplicates():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    # Feature rows uniqueness
    feat_cols = list(_MODEL_FEATURE_ORDER)
    num_dups = df.duplicated(subset=feat_cols).sum()
    assert num_dups == 0, f"Found {num_dups} duplicate feature rows"
    
    # Frame ID uniqueness
    assert df['frame_id'].nunique() == len(df), "Duplicate frame_ids detected"


# 6. Operating Condition Coverage
def test_6_operating_condition_coverage():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    cond_counts = df['operating_condition_id'].value_counts()
    assert len(cond_counts) == 32, f"Expected all 32 operating conditions, got {len(cond_counts)}"
    # Verify no condition dominates (> 15% of dataset)
    max_pct = (cond_counts.max() / len(df)) * 100.0
    assert max_pct < 15.0, f"Condition dominates with {max_pct:.1f}%"


# 7. Phase Coverage (3-Phase, 2-Phase, 1-Phase)
def test_7_phase_coverage():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    phase_configs = set(df['phase_config'].unique())
    expected_configs = {'three-phase', 'phase-to-ground', 'phase-to-phase'}
    assert expected_configs.issubset(phase_configs), f"Missing phase configurations: {expected_configs - phase_configs}"
    
    counts = df['phase_config'].value_counts()
    assert counts['three-phase'] > 0
    assert counts['phase-to-ground'] > 0
    assert counts['phase-to-phase'] > 0


# 8. Physical Duration Range (IEEE 1159 Instantaneous Interruption)
def test_8_physical_duration_range():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    min_dur = df['duration_ms'].min()
    max_dur = df['duration_ms'].max()
    
    assert min_dur >= 8.33, f"Minimum duration {min_dur} ms violates 0.5 cycle threshold"
    assert max_dur <= 500.0, f"Maximum duration {max_dur} ms exceeds instantaneous interruption limit"
    assert 40.0 <= min_dur <= 50.0
    assert 100.0 <= max_dur <= 130.0


# 9. Residual Voltage Range (IEEE 1159 Table 2: < 0.10 pu)
def test_9_residual_voltage_range():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    min_v = df['residual_voltage_pu'].min()
    max_v = df['residual_voltage_pu'].max()
    
    assert min_v > 0.0, f"Residual voltage {min_v} must be non-zero (physical grid)"
    assert max_v < 0.10, f"Residual voltage {max_v} pu exceeds IEEE 1159 interruption limit (0.10 pu)"


# 10. Data Leakage Prevention (Grouped by Simulation ID)
def test_10_leakage_prevention():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    train_sims = set(df[df['split'] == 'train']['simulation_id'].unique())
    val_sims   = set(df[df['split'] == 'val']['simulation_id'].unique())
    test_sims  = set(df[df['split'] == 'test']['simulation_id'].unique())
    
    assert len(train_sims.intersection(val_sims)) == 0, "Train-Val simulation leakage detected"
    assert len(train_sims.intersection(test_sims)) == 0, "Train-Test simulation leakage detected"
    assert len(val_sims.intersection(test_sims)) == 0, "Val-Test simulation leakage detected"
    
    assert len(train_sims) == 26
    assert len(val_sims) == 5
    assert len(test_sims) == 5


# 11. Ground-Truth Purity
def test_11_ground_truth_purity():
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    df = pd.read_csv(csv_path)
    
    assert (df['class'] == 'Interruption').all(), "Impure class label found"
    assert (df['label_idx'] == 2).all(), "Impure label_idx found"
    assert (df['label_source'] == 'SCENARIO_CONTROLLER').all(), "Label not from SCENARIO_CONTROLLER"


# 12. Checksum Consistency
def test_12_checksum_consistency():
    meta_path = os.path.join(INT_DIR, 'interruption_dataset_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
        
    csv_path = os.path.join(INT_DIR, 'interruption_features.csv')
    npz_path = os.path.join(INT_DIR, 'interruption_waveforms.npz')
    
    actual_csv_sha = hashlib.sha256(open(csv_path, 'rb').read()).hexdigest()
    actual_npz_sha = hashlib.sha256(open(npz_path, 'rb').read()).hexdigest()
    
    assert actual_csv_sha == meta['checksums']['interruption_features_csv_sha256']
    assert actual_npz_sha == meta['checksums']['interruption_waveforms_npz_sha256']

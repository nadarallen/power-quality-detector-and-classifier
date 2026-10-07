"""
tests/test_gate3n_harmonics_dataset.py
--------------------------------------
Automated test suite verifying Gate 3N and Gate 3O pass criteria for the
multi-condition Harmonics dataset in the 60-Hz IEEE 9-bus domain.
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
HAR_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'harmonics')
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


# 2. Harmonics Dataset Artifacts Exist
def test_2_harmonics_dataset_files_exist():
    expected_files = [
        'harmonics_features.csv',
        'harmonics_waveforms.npz',
        'harmonics_scenarios.json',
        'harmonics_dataset_metadata.json'
    ]
    for fn in expected_files:
        p = os.path.join(HAR_DIR, fn)
        assert os.path.exists(p), f"Missing artifact: {fn}"
        assert os.path.getsize(p) > 0, f"Empty artifact: {fn}"


# 3. Frame Count within Target Range (1,000 to 1,500)
def test_3_dataset_frame_count_and_shape():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    npz_path = os.path.join(HAR_DIR, 'harmonics_waveforms.npz')
    df = pd.read_csv(csv_path)
    npz = np.load(npz_path)
    
    n_csv = len(df)
    n_npz = len(npz['waveforms'])
    
    assert n_csv == 1152, f"Expected 1,152 frames, got {n_csv}"
    assert n_npz == 1152, f"Expected 1,152 waveforms, got {n_npz}"
    assert 1000 <= n_csv <= 1500, f"Frame count {n_csv} not in target [1000, 1500]"
    assert npz['waveforms'].shape == (1152, 1000, 3)


# 4. Numerical Purity
def test_4_numerical_purity():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    npz_path = os.path.join(HAR_DIR, 'harmonics_waveforms.npz')
    df = pd.read_csv(csv_path)
    npz = np.load(npz_path)

    assert df[_MODEL_FEATURE_ORDER].isna().sum().sum() == 0, "NaN found in features CSV"
    assert np.isinf(df[_MODEL_FEATURE_ORDER].values).sum() == 0, "Inf found in features CSV"
    assert np.isnan(npz['waveforms']).sum() == 0, "NaN found in waveforms NPZ"
    assert np.isinf(npz['waveforms']).sum() == 0, "Inf found in waveforms NPZ"
    assert df.duplicated(subset=_MODEL_FEATURE_ORDER).sum() == 0, "Duplicate feature rows detected"
    assert df['frame_id'].duplicated().sum() == 0, "Duplicate frame_ids detected"


# 5. Production Feature Dimensions
def test_5_production_feature_contract():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    for fn in _MODEL_FEATURE_ORDER:
        assert fn in df.columns, f"Missing feature in production contract: {fn}"


# 6. Ground-Truth Provenance
def test_6_ground_truth_provenance():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    assert (df['label_source'] == 'SCENARIO_CONTROLLER').all(), "Label source not SCENARIO_CONTROLLER"
    assert (df['class'] == 'Harmonics').all(), "Class label not Harmonics"
    assert (df['label_idx'] == 1).all(), "Label index not 1"


# 7. Physical Representation of Approved Harmonic Orders
def test_7_harmonic_orders_represented():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    for order in [2, 3, 5, 7, 9, 11]:
        col = f'h{order}'
        assert col in df.columns, f"Missing harmonic column: {col}"
        max_val = df[col].max()
        assert max_val > 0.005, f"Harmonic order H{order} has zero/sub-noise magnitude: {max_val}"


# 8. THD Distribution & Demarcation
def test_8_thd_distribution():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    min_thd = df['thd'].min()
    max_thd = df['thd'].max()
    median_thd = df['thd'].median()
    
    assert min_thd >= 5.0, f"THD min {min_thd}% violates demarcation threshold (>= 5.0%)"
    assert max_thd <= 25.0, f"THD max {max_thd}% exceeds reasonable physical limit (<= 25.0%)"
    assert 6.0 <= median_thd <= 12.0, f"Median THD {median_thd}% outside expected target range"


# 9. Fundamental Voltage Stability & Frequency
def test_9_fundamental_voltage_and_frequency():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df_har = pd.read_csv(csv_path)
    df_norm = pd.read_csv(os.path.join(NORMAL_DIR, 'normal_features.csv'))
    
    norm_base_h1 = float(df_norm['h1'].mean())
    norm_base_rms = float(df_norm['rms_voltage'].mean())
    
    h1_pu = df_har['h1'].values / norm_base_h1
    rms_pu = df_har['rms_voltage'].values / norm_base_rms
    freq = df_har['dominant_freq'].values
    
    assert (h1_pu >= 0.90).all() and (h1_pu <= 1.10).all(), "Fundamental PU voltage outside [0.90, 1.10]"
    assert (rms_pu >= 0.90).all() and (rms_pu <= 1.15).all(), "Total RMS PU voltage outside [0.90, 1.15]"
    assert (freq >= 59.90).all() and (freq <= 60.10).all(), "Fundamental frequency outside [59.90, 60.10] Hz"


# 10. Phase Configuration Diversity
def test_10_phase_diversity():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    counts = df['phase_configuration'].value_counts().to_dict()
    assert 'ABC' in counts and counts['ABC'] == 768, f"Unexpected 3-phase frame count: {counts.get('ABC')}"
    
    single_phase_count = sum(counts.get(k, 0) for k in ['A', 'B', 'C'])
    two_phase_count = sum(counts.get(k, 0) for k in ['AB', 'BC', 'CA'])
    
    assert single_phase_count == 192, f"Expected 192 single-phase frames, got {single_phase_count}"
    assert two_phase_count == 192, f"Expected 192 two-phase frames, got {two_phase_count}"


# 11. Operating Condition Coverage & Dominance
def test_11_operating_conditions():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    cond_counts = df['operating_condition_id'].value_counts()
    assert len(cond_counts) == 32, f"Expected 32 unique operating conditions, got {len(cond_counts)}"
    
    max_share = (cond_counts.max() / len(df)) * 100.0
    assert max_share <= 10.0, f"Operating condition dominance {max_share:.2f}% exceeds 10% limit"


# 12. Trajectory-Grouped Leakage Prevention
def test_12_cross_split_leakage():
    csv_path = os.path.join(HAR_DIR, 'harmonics_features.csv')
    df = pd.read_csv(csv_path)
    
    train_sims = set(df[df['split'] == 'train']['simulation_id'].unique())
    val_sims = set(df[df['split'] == 'val']['simulation_id'].unique())
    test_sims = set(df[df['split'] == 'test']['simulation_id'].unique())
    
    assert len(train_sims) == 26
    assert len(val_sims) == 5
    assert len(test_sims) == 5
    assert len(train_sims.intersection(val_sims)) == 0, "Train-Val simulation trajectory overlap detected!"
    assert len(train_sims.intersection(test_sims)) == 0, "Train-Test simulation trajectory overlap detected!"
    assert len(val_sims.intersection(test_sims)) == 0, "Val-Test simulation trajectory overlap detected!"


# 13. Gate 3O Comprehensive Audit Result
def test_13_gate3o_audit_passed():
    summary_path = os.path.join(DOCS_DIR, 'gate3o_harmonics_quality_summary.json')
    assert os.path.exists(summary_path), "Missing gate3o_harmonics_quality_summary.json"
    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)
        
    overall = summary.get('overall_evaluation', {})
    assert overall.get('GATE3O_HARMONICS_AUDIT') == 'PASS', f"Gate 3O audit did not PASS: {overall}"
    assert overall.get('audits_passed') == 17, f"Expected 17 passed audits, got {overall.get('audits_passed')}"

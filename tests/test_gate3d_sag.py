"""
tests/test_gate3d_sag.py
------------------------
Automated test suite verifying the 10 Gate 3D pass criteria for
Voltage Sag implementation in the 60-Hz IEEE 9-bus domain.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'
SAG_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag')

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity
from pipeline.disturbance_validator import validate_sag_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER


# ---------------------------------------------------------------------------
# Test 1: ScenarioController selects Sag
# ---------------------------------------------------------------------------
def test_1_scenario_controller_selects_sag():
    sc = ScenarioController()
    scens = sc.list_scenarios(class_filter='Sag')
    assert 'SAG_0001_three_phase_symmetric' in scens
    sc.select_scenario('SAG_0001_three_phase_symmetric')
    active = sc.get_active_scenario()
    assert active is not None
    assert active['class'] == 'Sag'


# ---------------------------------------------------------------------------
# Test 2: Sag parameters are loaded correctly
# ---------------------------------------------------------------------------
def test_2_sag_parameters_loaded_correctly():
    sc = ScenarioController()
    active = sc.select_scenario('SAG_0001_three_phase_symmetric')
    p = active['parameters']
    assert p['fault_resistance_ohms'] == 180.0
    assert p['duration_cycles'] == 5.0
    assert p['duration_ms'] == 83.33
    assert p['onset_time_ms'] == 40.0
    assert active['injection_location']['bus'] == 'Bus4'
    assert active['injection_location']['mechanism'] == 'FAULT_IMPEDANCE'
    assert active['injection_location']['phase'] == 'ABC'


# ---------------------------------------------------------------------------
# Test 3: Ground-truth label is Sag
# ---------------------------------------------------------------------------
def test_3_ground_truth_label_is_sag():
    sc = ScenarioController()
    sc.select_scenario('SAG_0001_three_phase_symmetric')
    assert sc.ground_truth_label == 'Sag'
    assert sc.ground_truth_label_idx == 5
    assert sc.get_active_scenario()['label_source'] == 'SCENARIO_CONTROLLER'


# ---------------------------------------------------------------------------
# Test 4: Pristine model remains unchanged
# ---------------------------------------------------------------------------
def test_4_pristine_model_remains_unchanged():
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == PRISTINE_SHA256


# ---------------------------------------------------------------------------
# Test 5: Sag actually appears electrically
# ---------------------------------------------------------------------------
def test_5_sag_appears_electrically():
    npz_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_waveform.npz')
    assert os.path.exists(npz_path), "SAG waveform NPZ not found"
    data = np.load(npz_path)
    waveforms = data['waveforms'] # (1, 1000, 3)
    va = waveforms[0, :, 0]
    
    # Pre-event: t in [0.01, 0.035] s -> samples [50, 175]
    pre_rms = np.sqrt(np.mean(va[50:175]**2))
    # Event: t in [0.05, 0.12] s -> samples [250, 600]
    event_rms = np.sqrt(np.mean(va[250:600]**2))
    
    # Significant electrical voltage depression
    assert event_rms < pre_rms * 0.85
    assert pre_rms > 0.55


# ---------------------------------------------------------------------------
# Test 6: Sag start/end are detected
# ---------------------------------------------------------------------------
def test_6_sag_start_end_detected():
    val_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_validation.json')
    assert os.path.exists(val_path)
    with open(val_path, 'r') as f:
        val = json.load(f)
    assert val['start_time_s'] is not None
    assert val['end_time_s'] is not None
    assert 0.030 <= val['start_time_s'] <= 0.050
    assert 0.115 <= val['end_time_s'] <= 0.140
    assert val['duration_ms'] >= 8.33 # Minimum 0.5 cycle


# ---------------------------------------------------------------------------
# Test 7: Measured residual voltage matches scenario configuration
# ---------------------------------------------------------------------------
def test_7_residual_voltage_matches_configuration():
    val_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_validation.json')
    with open(val_path, 'r') as f:
        val = json.load(f)
    residual = val['residual_voltage_pu']
    # Residual should be within expected range for 180 ohm fault [0.60, 0.80]
    assert 0.60 <= residual <= 0.80
    assert val['gates']['SAG-01_residual_ge_0.10'] is True
    assert val['gates']['SAG-02_residual_lt_0.90'] is True


# ---------------------------------------------------------------------------
# Test 8: No unintended disturbance is silently accepted
# ---------------------------------------------------------------------------
def test_8_no_unintended_disturbance():
    val_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_validation.json')
    with open(val_path, 'r') as f:
        val = json.load(f)
    # Anti-contamination assertions
    assert val['gates']['SAG-ANTI-INTERRUPT'] is True
    assert val['gates']['SAG-ANTI-SWELL'] is True
    assert val['gates']['SAG-05_thd_lt_5pct'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True
    assert val['physical_validation_passed'] is True


# ---------------------------------------------------------------------------
# Test 9: Feature extraction completes
# ---------------------------------------------------------------------------
def test_9_feature_extraction_completes():
    feats_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_features.json')
    assert os.path.exists(feats_path)
    with open(feats_path, 'r') as f:
        feats_data = json.load(f)
    ph_a = feats_data['phase_A']
    # Check all 32 model features are present and non-null
    for feat_name in _MODEL_FEATURE_ORDER:
        assert feat_name in ph_a, f"Missing feature {feat_name}"
        assert ph_a[feat_name] is not None
        assert not np.isnan(ph_a[feat_name])
    assert ph_a['rms_voltage'] < 0.58 # depressed due to sag


# ---------------------------------------------------------------------------
# Test 10: Metadata contains complete provenance
# ---------------------------------------------------------------------------
def test_10_metadata_complete_provenance():
    meta_path = os.path.join(SAG_DATA_DIR, 'sag_scenario_0001_metadata.json')
    assert os.path.exists(meta_path)
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    assert meta['label_source'] == 'SCENARIO_CONTROLLER'
    assert meta['ground_truth'] == 'Sag'
    assert meta['ground_truth_label_idx'] == 5
    assert meta['model_domain_status'] == 'MODEL_DOMAIN_MISMATCH'
    assert meta['pristine_model_sha256'] == PRISTINE_SHA256
    prov = meta['scenario']['parameter_provenance']
    assert 'magnitude_pu' in prov
    assert 'fault_resistance_ohms' in prov
    assert 'standard_references' in meta['scenario']
    assert len(meta['scenario']['standard_references']) >= 2

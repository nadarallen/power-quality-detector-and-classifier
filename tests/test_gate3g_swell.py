"""
tests/test_gate3g_swell.py
--------------------------
Automated test suite verifying the Gate 3G pass criteria for
Voltage Swell implementation in the 60-Hz IEEE 9-bus domain.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'
SWELL_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'swell')

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity
from pipeline.disturbance_validator import validate_swell_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER


def test_1_scenario_controller_selects_swell():
    sc = ScenarioController()
    scens = sc.list_scenarios(class_filter='Swell')
    assert 'SWELL_0001_three_phase_symmetric' in scens
    sc.select_scenario('SWELL_0001_three_phase_symmetric')
    active = sc.get_active_scenario()
    assert active is not None
    assert active['class'] == 'Swell'


def test_2_swell_parameters_loaded_correctly():
    sc = ScenarioController()
    active = sc.select_scenario('SWELL_0001_three_phase_symmetric')
    p = active['parameters']
    assert p['capacitive_power_mvar'] == 150.0
    assert p['duration_cycles'] == 4.8
    assert p['duration_ms'] == 80.0
    assert p['onset_time_ms'] == 40.0
    assert active['injection_location']['bus'] == 'Bus4'
    assert active['injection_location']['mechanism'] == 'CAPACITOR_SWITCH'
    assert active['injection_location']['phase'] == 'ABC'


def test_3_ground_truth_label_is_swell():
    sc = ScenarioController()
    sc.select_scenario('SWELL_0001_three_phase_symmetric')
    assert sc.ground_truth_label == 'Swell'
    assert sc.ground_truth_label_idx == 6
    assert sc.get_active_scenario()['label_source'] == 'SCENARIO_CONTROLLER'


def test_4_pristine_model_remains_unchanged():
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == PRISTINE_SHA256


def test_5_swell_appears_electrically():
    npz_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_waveform.npz')
    assert os.path.exists(npz_path), "SWELL waveform NPZ not found"
    data = np.load(npz_path)
    waveforms = data['waveforms']  # (1, 1000, 3)
    va = waveforms[0, :, 0]
    
    # Pre-event: t in [0.01, 0.035] s -> samples [50, 175]
    pre_rms = np.sqrt(np.mean(va[50:175]**2))
    # Event: t in [0.05, 0.12] s -> samples [250, 600]
    event_rms = np.sqrt(np.mean(va[250:600]**2))
    
    # Significant electrical voltage rise (Swell)
    assert event_rms > pre_rms * 1.10
    assert pre_rms > 0.55


def test_6_swell_start_end_detected():
    val_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_validation.json')
    assert os.path.exists(val_path)
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['physical_validation_passed'] is True
    assert val['start_time_s'] is not None
    assert val['end_time_s'] is not None
    assert val['start_time_s'] < val['end_time_s']
    assert val['duration_ms'] >= 8.33


def test_7_swell_independent_physical_validation_gates():
    val_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['gates']['SWL-01_magnitude_gt_1.10'] is True
    assert val['gates']['SWL-02_magnitude_le_1.80'] is True
    assert val['gates']['SWL-03_duration_ge_8.33ms'] is True
    assert val['gates']['SWL-04_peak_elevated'] is True
    assert val['gates']['SWL-05_crest_factor_valid'] is True
    assert val['gates']['SWL-06_freq_59.5_60.5'] is True
    assert val['gates']['SWL-07_thd_lt_5pct'] is True
    assert val['gates']['SWL-ANTI-SAG'] is True
    assert val['gates']['SWL-ANTI-INTERRUPT'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True


def test_8_swell_multi_phase_behavior():
    val_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['phase_configuration'] == 'three-phase'
    assert set(val['affected_phases']) == {'A', 'B', 'C'}
    for ph in ['A', 'B', 'C']:
        m = val['per_phase_metrics'][ph]
        assert m['event_ratio'] > 1.10


def test_9_swell_feature_contract_and_metadata():
    feats_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_features.json')
    meta_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_metadata.json')
    assert os.path.exists(feats_path)
    assert os.path.exists(meta_path)
    
    with open(feats_path, 'r', encoding='utf-8') as f:
        feats = json.load(f)
    fa = feats['phase_A']
    for req_feat in _MODEL_FEATURE_ORDER:
        assert req_feat in fa
        assert not np.isnan(fa[req_feat])
        assert not np.isinf(fa[req_feat])


def test_10_swell_label_decoupling_and_domain_status():
    meta_path = os.path.join(SWELL_DATA_DIR, 'swell_scenario_0001_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    assert meta['scenario']['class'] == 'Swell'
    assert meta['scenario']['label_source'] == 'SCENARIO_CONTROLLER'
    assert meta['raw_ml_prediction']['model_domain_status'] == 'MODEL_DOMAIN_MISMATCH'

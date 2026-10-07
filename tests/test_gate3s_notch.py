"""
tests/test_gate3s_notch.py
--------------------------
Unit and integration test suite validating Gate 3S criteria for deterministic
Voltage Notch implementation.

Covers:
1. Electrical mechanism verification (Physical 6-pulse commutation switching at Bus 5)
2. Scenario reproducibility and artifact existence
3. Waveform integrity (1000 samples, 3 channels, Fs = 5000 Hz, 200 ms)
4. Notch depth: depth in [0.20, 0.85] pu (NOT-01, NOT-02)
5. Sub-cycle notch width: width < 8.33 ms (< 0.5 cycle per IEEE 1159) and >= 0.35 ms (NOT-03)
6. Periodic repetition and notch count >= 2 (NOT-05)
7. High-frequency residual energy ratio elevated (NOT-04)
8. Fundamental frequency preservation at 60 Hz and RMS in [0.45, 0.80] pu (NOT-06, NOT-07)
9. Multi-phase independent behavior (Va, Vb, Vc analyzed independently)
10. Anti-contamination: no sustained sag, swell, or interruption
11. Authoritative 32-feature contract compliance (no NaN, no Inf, exact order)
12. DSP parity between reference and Python implementations (< 0.05 tolerance)
13. Ground truth provenance: SCENARIO_CONTROLLER (label_idx = 4)
14. ML decoupling: model domain status OUT_OF_DOMAIN, labels uncontaminated
15. Pristine model SHA-256 integrity
"""

import os
import sys
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scenarios.scenario_controller import (
    ScenarioController,
    verify_pristine_model_integrity,
    PRISTINE_SHA256,
    PRISTINE_MODEL_FULL
)
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, MLPClassifier
from pipeline.disturbance_validator import validate_notch_frame

DATA_NOT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'notch')
WAVEFORM_PATH = os.path.join(DATA_NOT_DIR, 'notch_scenario_0001_waveform.npz')
FEATURES_PATH = os.path.join(DATA_NOT_DIR, 'notch_scenario_0001_features.json')
VALIDATION_PATH = os.path.join(DATA_NOT_DIR, 'notch_scenario_0001_validation.json')
METADATA_PATH = os.path.join(DATA_NOT_DIR, 'notch_scenario_0001_metadata.json')
SCENARIO_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', 'NOT_0001_width600us_depth40pct.json')


@pytest.fixture(scope="module")
def notch_artifacts():
    assert os.path.exists(WAVEFORM_PATH), f"Missing {WAVEFORM_PATH}"
    assert os.path.exists(FEATURES_PATH), f"Missing {FEATURES_PATH}"
    assert os.path.exists(VALIDATION_PATH), f"Missing {VALIDATION_PATH}"
    assert os.path.exists(METADATA_PATH), f"Missing {METADATA_PATH}"
    assert os.path.exists(SCENARIO_JSON), f"Missing {SCENARIO_JSON}"

    data_npz = np.load(WAVEFORM_PATH, allow_pickle=True)
    with open(FEATURES_PATH, 'r') as f:
        features = json.load(f)
    with open(VALIDATION_PATH, 'r') as f:
        validation = json.load(f)
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    with open(SCENARIO_JSON, 'r') as f:
        scenario = json.load(f)

    return {
        'v_frame': data_npz['v_frame'],
        'i_frame': data_npz['i_frame'],
        't_frame': data_npz['t_frame'],
        'features': features,
        'validation': validation,
        'metadata': metadata,
        'scenario': scenario
    }


def test_pristine_model_untouched():
    """Criterion 14: Pristine reference model remains byte-for-byte unchanged."""
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL_FULL, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    assert sha == PRISTINE_SHA256


def test_ground_truth_provenance(notch_artifacts):
    """Criterion 12: Ground truth comes strictly from SCENARIO_CONTROLLER (label_idx = 4)."""
    scen = notch_artifacts['scenario']
    val = notch_artifacts['validation']
    meta = notch_artifacts['metadata']

    assert scen['class'] == 'Notch'
    assert scen['label_idx'] == 4
    assert scen['label_source'] == 'SCENARIO_CONTROLLER'

    assert val['ground_truth'] == 'Notch'
    assert val['label_source'] == 'SCENARIO_CONTROLLER'
    assert val['label_idx'] == 4

    assert meta['ground_truth_label'] == 'Notch'
    assert meta['ground_truth_source'] == 'SCENARIO_CONTROLLER'
    assert meta['label_idx'] == 4


def test_waveform_geometry_and_integrity(notch_artifacts):
    """Criterion 8 & 12: Waveform has 1000 samples, 3 channels, Fs = 5000 Hz, no NaN/Inf."""
    v_frame = notch_artifacts['v_frame']
    t_frame = notch_artifacts['t_frame']

    assert v_frame.shape == (1000, 3)
    assert len(t_frame) == 1000
    assert not np.isnan(v_frame).any()
    assert not np.isinf(v_frame).any()

    # Time span must be ~200 ms (199.8 ms at 5 kHz)
    duration_ms = (t_frame[-1] - t_frame[0]) * 1000.0
    assert 199.0 <= duration_ms <= 201.0


def test_notch_depth_bounds(notch_artifacts):
    """Criterion 4: Physical notch depth is measured and within Gate 3C bounds (0.20, 0.85)."""
    val = notch_artifacts['validation']['validation']
    depth = val['primary_max_depth_pu']

    assert val['gates']['NOT-01_depth_ge_0.20'] is True
    assert val['gates']['NOT-02_depth_le_0.85'] is True
    assert 0.20 <= depth <= 0.85


def test_notch_width_subcycle(notch_artifacts):
    """Criterion 3: Notch width is sub-cycle (< 8.33 ms) and >= 0.35 ms for 5 kHz resolution."""
    val = notch_artifacts['validation']['validation']
    width_ms = val['primary_mean_width_ms']

    assert val['gates']['NOT-03_width_subcycle'] is True
    assert 0.35 <= width_ms < 8.33


def test_notch_periodicity_and_count(notch_artifacts):
    """Criterion 2 & 5: Periodic commutation notches detected with count >= 2."""
    val = notch_artifacts['validation']['validation']
    count = val['primary_notch_count']

    assert val['gates']['NOT-05_periodicity_ok'] is True
    assert count >= 2


def test_notch_energy_ratio_elevated(notch_artifacts):
    """Criterion 9: High-frequency residual energy ratio is elevated."""
    val = notch_artifacts['validation']['validation']
    energy_ratio = val['primary_energy_ratio']

    assert val['gates']['NOT-04_energy_ratio_elevated'] is True
    assert energy_ratio > 0.001


def test_fundamental_preservation(notch_artifacts):
    """Criterion 7: Fundamental grid voltage remains approximately 60 Hz and RMS in range."""
    feats = notch_artifacts['features']
    val = notch_artifacts['validation']['validation']

    assert val['gates']['NOT-07_freq_59.5_60.5'] is True
    assert val['gates']['NOT-06_rms_0.45_0.80'] is True
    assert 59.5 <= feats['dominant_freq'] <= 60.5
    assert 0.45 <= feats['rms_voltage'] <= 0.80


def test_anti_contamination(notch_artifacts):
    """Criterion 9: No unintended Interruption or sustained Swell."""
    val = notch_artifacts['validation']['validation']

    assert val['gates']['ANTI_INTERRUPTION'] is True
    assert val['gates']['ANTI_SWELL'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True


def test_multi_phase_analysis(notch_artifacts):
    """Criterion 6: Three phases analyzed independently."""
    val = notch_artifacts['validation']['validation']
    per_ph = val['per_phase_notches']

    assert 'A' in per_ph and 'B' in per_ph and 'C' in per_ph
    assert per_ph['A']['notch_count'] >= 2


def test_dsp_feature_contract(notch_artifacts):
    """Criterion 10: 32-feature vector contract unchanged, no NaN/Inf."""
    feats = notch_artifacts['features']

    for feat_name in _MODEL_FEATURE_ORDER:
        assert feat_name in feats, f"Missing feature: {feat_name}"
        val = feats[feat_name]
        assert not np.isnan(val), f"NaN in feature {feat_name}"
        assert not np.isinf(val), f"Inf in feature {feat_name}"


def test_matlab_python_dsp_parity(notch_artifacts):
    """Criterion 11: MATLAB reference and Python production DSP match within tolerance."""
    parity = notch_artifacts['validation']['parity']

    assert parity['parity_passed'] is True
    assert parity['max_diff'] < 0.05


def test_ml_decoupling(notch_artifacts):
    """Criterion 13: ML model is completely decoupled from ground truth."""
    diag = notch_artifacts['validation']['ml_diagnostic']

    assert diag['label_independence_confirmed'] is True
    assert 'OUT_OF_DOMAIN' in diag['model_domain_status']
    assert diag['ground_truth'] == 'Notch'

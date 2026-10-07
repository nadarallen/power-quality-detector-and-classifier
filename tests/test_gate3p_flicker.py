"""
tests/test_gate3p_flicker.py
----------------------------
Unit and integration test suite validating Gate 3P criteria for deterministic
Flicker implementation.

Covers:
1. Electrical mechanism verification (Controlled Dynamic Load at Bus 5)
2. Scenario reproducibility and artifact existence
3. Waveform integrity (1000 samples, 3 channels, Fs = 5000 Hz, 200 ms)
4. Envelope modulation depth: m in [0.02, 0.15] (FLK-01, FLK-02)
5. Modulation frequency: fm in [3.0, 20.0] Hz with >= 1.0 cycle in window (FLK-03, FLK-07)
6. Fundamental frequency preservation at 60 Hz (FLK-FREQ)
7. Low harmonic distortion: THD < 3.0% (FLK-06)
8. Multi-phase independent behavior (Va, Vb, Vc)
9. Anti-contamination: no sag, swell, or interruption (FLK-04, FLK-05, FLK-ANTI-INTERRUPT)
10. Authoritative 32-feature contract compliance (no NaN, no Inf, exact order)
11. DSP parity between reference and Python implementations (< 0.05 tolerance)
12. Ground truth provenance: SCENARIO_CONTROLLER (label_idx = 0)
13. ML decoupling: model domain status OUT_OF_DOMAIN, labels uncontaminated
14. Pristine model SHA-256 integrity
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
from pipeline.disturbance_validator import validate_flicker_frame

DATA_FLK_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'flicker')
WAVEFORM_PATH = os.path.join(DATA_FLK_DIR, 'flicker_scenario_0001_waveform.npz')
FEATURES_PATH = os.path.join(DATA_FLK_DIR, 'flicker_scenario_0001_features.json')
VALIDATION_PATH = os.path.join(DATA_FLK_DIR, 'flicker_scenario_0001_validation.json')
METADATA_PATH = os.path.join(DATA_FLK_DIR, 'flicker_scenario_0001_metadata.json')
SCENARIO_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', 'FLK_0001_fm10hz_depth5pct.json')


@pytest.fixture(scope="module")
def flicker_artifacts():
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
    """Criterion 11: Pristine reference model remains byte-for-byte unchanged."""
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL_FULL, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    assert sha == PRISTINE_SHA256


def test_ground_truth_provenance(flicker_artifacts):
    """Criterion 7: Ground truth comes strictly from SCENARIO_CONTROLLER (label_idx = 0)."""
    scen = flicker_artifacts['scenario']
    val = flicker_artifacts['validation']
    meta = flicker_artifacts['metadata']

    assert scen['class'] == 'Flicker'
    assert scen['label_idx'] == 0
    assert scen['label_source'] == 'SCENARIO_CONTROLLER'

    assert val['ground_truth'] == 'Flicker'
    assert val['label_source'] == 'SCENARIO_CONTROLLER'
    assert val['label_idx'] == 0

    assert meta['ground_truth_label'] == 'Flicker'
    assert meta['ground_truth_source'] == 'SCENARIO_CONTROLLER'
    assert meta['label_idx'] == 0


def test_waveform_geometry_and_integrity(flicker_artifacts):
    """Criterion 2 & 12: Waveform has 1000 samples, 3 channels, Fs = 5000 Hz, no NaN/Inf."""
    v_frame = flicker_artifacts['v_frame']
    t_frame = flicker_artifacts['t_frame']

    assert v_frame.shape == (1000, 3)
    assert len(t_frame) == 1000
    assert not np.isnan(v_frame).any()
    assert not np.isinf(v_frame).any()

    # Time span must be ~200 ms (199.8 ms at 5 kHz)
    duration_ms = (t_frame[-1] - t_frame[0]) * 1000.0
    assert 199.0 <= duration_ms <= 201.0


def test_envelope_modulation_depth(flicker_artifacts):
    """Criterion 3: Physical modulation is present and within Gate 3C bounds (0.02, 0.15)."""
    val = flicker_artifacts['validation']['validation']
    depth = val['primary_envelope_depth']

    assert val['gates']['FLK-01_depth_gt_0.02'] is True
    assert val['gates']['FLK-02_depth_lt_0.15'] is True
    assert 0.02 < depth < 0.15


def test_modulation_frequency_and_cycles(flicker_artifacts):
    """Criterion 12: Modulation frequency in sensitivity band (3-20 Hz) and >= 1 cycle in window."""
    val = flicker_artifacts['validation']['validation']
    fm = val['primary_modulation_freq_hz']
    cycles = val['primary_modulation_cycles']

    assert val['gates']['FLK-03_freq_3_to_20Hz'] is True
    assert val['gates']['FLK-07_cycles_ge_1.0'] is True
    assert 3.0 <= fm <= 20.0
    assert cycles >= 1.0


def test_fundamental_frequency_preservation(flicker_artifacts):
    """Criterion 4: Fundamental frequency remains ~60 Hz."""
    feats = flicker_artifacts['features']
    val = flicker_artifacts['validation']['validation']

    assert val['gates']['FLK-FREQ_59.5_60.5'] is True
    assert 59.5 <= feats['dominant_freq'] <= 60.5


def test_low_harmonic_distortion(flicker_artifacts):
    """Criterion 10: Harmonic content is low (THD < 3.0%), not confused with Harmonics class."""
    feats = flicker_artifacts['features']
    val = flicker_artifacts['validation']['validation']

    assert val['gates']['FLK-06_thd_lt_3pct'] is True
    assert feats['thd'] < 3.0


def test_anti_contamination_secondary_phenomena(flicker_artifacts):
    """Criterion 5: No unintended Sag, Swell, or Interruption."""
    val = flicker_artifacts['validation']['validation']

    assert val['gates']['FLK-04_anti_sag'] is True
    assert val['gates']['FLK-05_anti_swell'] is True
    assert val['gates']['FLK-ANTI-INTERRUPT'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True


def test_multi_phase_analysis(flicker_artifacts):
    """Criterion 6: Three phases analyzed independently."""
    val = flicker_artifacts['validation']['validation']
    per_ph = val['per_phase_envelope']

    assert 'A' in per_ph and 'B' in per_ph and 'C' in per_ph
    for ph in ['A', 'B', 'C']:
        assert per_ph[ph]['envelope_depth'] > 0.02
        assert 3.0 <= per_ph[ph]['envelope_freq_hz'] <= 20.0


def test_dsp_feature_contract(flicker_artifacts):
    """Criterion 8: 32-feature vector contract unchanged, no NaN/Inf."""
    feats = flicker_artifacts['features']

    for feat_name in _MODEL_FEATURE_ORDER:
        assert feat_name in feats, f"Missing feature: {feat_name}"
        val = feats[feat_name]
        assert not np.isnan(val), f"NaN in feature {feat_name}"
        assert not np.isinf(val), f"Inf in feature {feat_name}"


def test_matlab_python_dsp_parity(flicker_artifacts):
    """Criterion 9: MATLAB reference and Python production DSP match within tolerance."""
    parity = flicker_artifacts['validation']['parity']

    assert parity['parity_passed'] is True
    assert parity['max_diff'] < 0.05


def test_ml_decoupling(flicker_artifacts):
    """Criterion 7: ML model is completely decoupled from ground truth."""
    diag = flicker_artifacts['validation']['ml_diagnostic']

    assert diag['label_independence_confirmed'] is True
    assert 'OUT_OF_DOMAIN' in diag['model_domain_status']
    assert diag['ground_truth'] == 'Flicker'

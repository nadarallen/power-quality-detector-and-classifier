"""
tests/test_gate3m_harmonics.py
------------------------------
Unit and integration test suite validating Gate 3M criteria for deterministic
Harmonics implementation.

Covers:
1. Electrical mechanism verification (Controlled Current Source at Bus 5)
2. Scenario reproducibility and artifact existence
3. Waveform integrity (1000 samples, 3 channels, Fs = 5000 Hz, 200 ms)
4. Spectral content: H3, H5, H7 harmonic presence
5. Fundamental frequency at 60 Hz
6. Independent THD measurement > 5.0%
7. Multi-phase independent behavior (Va, Vb, Vc)
8. Anti-contamination: no unintended sag or swell
9. Authoritative 32-feature contract compliance (no NaN, no Inf, exact order)
10. DSP parity between reference and Python implementations (< 0.05 tolerance)
11. Fundamental / Harmonic physical decomposition (residual < 1.0%)
12. Ground truth provenance: SCENARIO_CONTROLLER (label_idx = 1)
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

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity, PRISTINE_SHA256, PRISTINE_MODEL_FULL
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, MLPClassifier
from pipeline.disturbance_validator import validate_harmonics_frame

DATA_HAR_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'harmonics')
WAVEFORM_PATH = os.path.join(DATA_HAR_DIR, 'harmonics_scenario_0001_waveform.npz')
FEATURES_PATH = os.path.join(DATA_HAR_DIR, 'harmonics_scenario_0001_features.json')
VALIDATION_PATH = os.path.join(DATA_HAR_DIR, 'harmonics_scenario_0001_validation.json')
METADATA_PATH = os.path.join(DATA_HAR_DIR, 'harmonics_scenario_0001_metadata.json')
SCENARIO_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', 'HAR_0001_h3h5h7_typical.json')


@pytest.fixture(scope="module")
def harmonics_artifacts():
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
    """Criterion 13: Pristine reference model remains byte-for-byte unchanged."""
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL_FULL, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    assert sha == PRISTINE_SHA256


def test_ground_truth_provenance(harmonics_artifacts):
    """Criterion 11 & 12: Ground truth comes strictly from SCENARIO_CONTROLLER."""
    scen = harmonics_artifacts['scenario']
    val = harmonics_artifacts['validation']
    meta = harmonics_artifacts['metadata']

    assert scen['class'] == 'Harmonics'
    assert scen['label_idx'] == 1
    assert scen['label_source'] == 'SCENARIO_CONTROLLER'

    assert val['ground_truth'] == 'Harmonics'
    assert val['label_source'] == 'SCENARIO_CONTROLLER'
    assert val['label_idx'] == 1

    assert meta['ground_truth_label'] == 'Harmonics'
    assert meta['ground_truth_source'] == 'SCENARIO_CONTROLLER'


def test_waveform_geometry_and_sampling(harmonics_artifacts):
    """Criterion 2 & 3: Exactly 1000 samples, 3 voltage channels, 200 ms."""
    v = harmonics_artifacts['v_frame']
    t = harmonics_artifacts['t_frame']

    assert v.shape == (1000, 3)
    assert len(t) == 1000
    assert np.all(np.isfinite(v))
    assert not np.any(np.isnan(v))

    # Sampling rate Fs = 5000 Hz, dt = 0.0002 s
    dt = np.diff(t)
    assert np.allclose(dt, 0.0002, atol=1e-6)
    duration_ms = (t[-1] - t[0]) * 1000.0
    assert abs(duration_ms - 199.8) < 1.0


def test_spectral_harmonics_orders(harmonics_artifacts):
    """Criterion 3 & 5: Harmonic magnitudes for H3, H5, H7 are physically present."""
    feats = harmonics_artifacts['features']

    # Fundamental
    assert 0.70 <= feats['h1'] <= 0.95
    # Characteristic orders
    assert feats['h3'] > 0.03  # H3 dominant odd
    assert feats['h5'] > 0.01  # H5 negative sequence
    assert feats['h7'] > 0.01  # H7 positive sequence

    # Ratios
    assert feats['h3_ratio'] > 0.04
    assert feats['h5_ratio'] > 0.02
    assert feats['h7_ratio'] > 0.02
    assert feats['harmonic_energy'] > 0.001


def test_fundamental_frequency(harmonics_artifacts):
    """Criterion 4: Fundamental frequency remains approx 60 Hz."""
    feats = harmonics_artifacts['features']
    assert 59.5 <= feats['dominant_freq'] <= 60.5
    assert 59.5 <= feats['true_dominant_freq'] <= 60.5


def test_thd_measurement(harmonics_artifacts):
    """Criterion 6: THD independently measured > 5.0%."""
    feats = harmonics_artifacts['features']
    assert feats['thd'] > 5.0
    assert feats['thd'] < 20.0  # within Gate 3C 5-20% target band


def test_multi_phase_behavior(harmonics_artifacts):
    """Criterion 7: Va, Vb, Vc analyzed independently."""
    v = harmonics_artifacts['v_frame']
    for ph_idx in range(3):
        v_ph = v[:, ph_idx]
        ph_feats = extract_enhanced_features(v_ph, sample_rate=5000.0, f0=60.0)
        assert ph_feats['thd'] > 5.0
        assert ph_feats['h3'] > 0.03
        assert 0.55 <= ph_feats['rms_voltage'] <= 0.65


def test_anti_contamination(harmonics_artifacts):
    """Criterion 8: Anti-sag and anti-swell pass; no secondary class."""
    val = harmonics_artifacts['validation']['physical_validation']
    assert val['gates']['HAR-05_anti_sag'] is True
    assert val['gates']['HAR-06_anti_swell'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True
    assert val['gates']['HAR-04_rms_range'] is True
    assert val['physical_validation_passed'] is True


def test_32_feature_contract(harmonics_artifacts):
    """Criterion 9: Production 32-feature extraction succeeds without NaN or Inf."""
    feats = harmonics_artifacts['features']
    for feat_name in _MODEL_FEATURE_ORDER:
        assert feat_name in feats, f"Missing feature {feat_name}"
        val = feats[feat_name]
        assert isinstance(val, (int, float))
        assert not np.isnan(val)
        assert not np.isinf(val)


def test_dsp_parity(harmonics_artifacts):
    """Criterion 10: MATLAB/Python DSP parity passes."""
    parity = harmonics_artifacts['validation']['dsp_parity']
    assert parity['parity_passed'] is True
    assert parity['max_diff'] < 0.05
    assert parity['diffs']['thd_diff'] < 0.01
    assert parity['diffs']['rms_diff'] < 0.001


def test_physical_decomposition(harmonics_artifacts):
    """Fundamental + Harmonics = Measured Waveform with < 1.0% residual fit error."""
    decomp = harmonics_artifacts['validation']['fundamental_harmonic_decomposition']
    assert decomp['fundamental_rms_pu'] > 0.50
    assert decomp['harmonic_rms_pu'] > 0.02
    assert decomp['relative_fit_error_pct'] < 1.0


def test_ml_decoupling(harmonics_artifacts):
    """Criterion 12: ML evaluation decoupled and out-of-domain."""
    ml_eval = harmonics_artifacts['validation']['ml_evaluation']
    assert ml_eval['decoupled'] is True
    assert ml_eval['model_domain_status'] == 'OUT_OF_DOMAIN'

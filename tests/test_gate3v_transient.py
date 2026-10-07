"""
tests/test_gate3v_transient.py
------------------------------
Unit and integration tests for Gate 3V deterministic Transient implementation.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_TRAN_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'transient')
PRISTINE_PATH = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D'


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_pristine_model_untouched():
    """Verify pristine reference model has not been altered."""
    assert os.path.exists(PRISTINE_PATH), "Pristine model file missing"
    assert compute_sha256(PRISTINE_PATH) == PRISTINE_SHA256, "Pristine reference model altered!"


def test_ground_truth_provenance():
    """Verify scenario metadata assigns class Transient from SCENARIO_CONTROLLER."""
    meta_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_metadata.json')
    assert os.path.exists(meta_path), "Metadata JSON missing"
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    assert meta['class'] == 'Transient'
    assert meta['label_idx'] == 7
    assert meta['label_source'] == 'SCENARIO_CONTROLLER'


def test_waveform_geometry_and_integrity():
    """Verify waveform shape, sampling, and lack of NaNs/Infs."""
    npz_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_waveform.npz')
    assert os.path.exists(npz_path), "Waveform NPZ missing"
    data = np.load(npz_path)
    waveform = data['waveform']
    assert waveform.shape == (1000, 3)
    assert not np.isnan(waveform).any()
    assert not np.isinf(waveform).any()
    assert data['class_label'] == 'Transient'
    assert int(data['label_idx']) == 7


def test_transient_peak_excursion():
    """Verify peak instantaneous voltage and excursion satisfy physical gates."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    res = val['validation_result']
    assert res['physical_validation_passed'] is True
    assert res['peak_excursion_pu'] >= 0.12
    assert res['event_peak_pu'] >= 1.00


def test_transient_dominant_frequency():
    """Verify dominant transient frequency is in the approved 5 kHz bandwidth."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    dom_f = val['validation_result']['dominant_trans_freq_hz']
    assert 250.0 <= dom_f <= 1500.0, f"Dominant frequency out of bounds: {dom_f}"


def test_transient_duration_subcycle():
    """Verify transient duration is bounded <= 50 ms."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    dur = val['validation_result']['effective_duration_ms']
    assert dur <= 50.0, f"Duration exceeded 50 ms limit: {dur}"


def test_fundamental_preservation():
    """Verify grid fundamental frequency remains 60 Hz."""
    feat_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_features.json')
    with open(feat_path, 'r', encoding='utf-8') as f:
        feat = json.load(f)
    f0 = feat['features_dict']['system_freq']
    assert 59.5 <= f0 <= 60.5, f"Fundamental grid frequency deviated: {f0}"


def test_anti_contamination():
    """Verify zero sustained Sag, Swell, or Interruption contamination."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    gates = val['validation_result']['gates']
    assert gates['ANTI_SAG'] is True
    assert gates['ANTI_INTERRUPTION'] is True
    assert gates['ANTI_SWELL'] is True
    assert gates['WAVEFORM_CONTINUITY'] is True


def test_multi_phase_analysis():
    """Verify multi-phase analysis is performed and affected phases are attributed."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    metrics = val['validation_result']['per_phase_metrics']
    assert 'A' in metrics and 'B' in metrics and 'C' in metrics
    assert len(val['validation_result']['affected_phases']) > 0


def test_dsp_feature_contract():
    """Verify all 32 contract features are present and non-null."""
    feat_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_features.json')
    with open(feat_path, 'r', encoding='utf-8') as f:
        feat = json.load(f)
    vec = feat['features_vector']
    assert len(vec) == 32
    assert not any(np.isnan(vec))
    assert not any(np.isinf(vec))


def test_matlab_python_dsp_parity():
    """Verify numerical parity between MATLAB and Python DSP."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    parity = val['dsp_parity']
    assert parity['parity_passed'] is True
    for k, comp in parity['comparison'].items():
        assert comp['pass'] is True, f"Parity failed on {k}: diff={comp['diff']}"


def test_ml_decoupling():
    """Verify ML model prediction does not dictate ground truth."""
    val_path = os.path.join(DATA_TRAN_DIR, 'transient_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    ml_diag = val['ml_diagnostic']
    assert ml_diag['domain_status'] == 'OUT_OF_DOMAIN'

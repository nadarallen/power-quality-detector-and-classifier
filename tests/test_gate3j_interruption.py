"""
tests/test_gate3j_interruption.py
---------------------------------
Automated test suite verifying all 16 Gate 3J pass criteria for
deterministic Voltage Interruption implementation in the 60-Hz IEEE 9-bus domain.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'
INT_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'interruption')

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity
from pipeline.disturbance_validator import validate_interruption_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER


# 1. Scenario Selection
def test_1_scenario_selection():
    sc = ScenarioController()
    scens = sc.list_scenarios(class_filter='Interruption')
    assert 'INT_0001_three_phase_symmetric' in scens
    active = sc.select_scenario('INT_0001_three_phase_symmetric')
    assert active is not None
    assert active['class'] == 'Interruption'
    assert active['scenario_id'] == 'INT_0001_three_phase_symmetric'


# 2. Ground-Truth Provenance
def test_2_ground_truth_provenance():
    sc = ScenarioController()
    sc.select_scenario('INT_0001_three_phase_symmetric')
    assert sc.ground_truth_label == 'Interruption'
    assert sc.ground_truth_label_idx == 2
    active = sc.get_active_scenario()
    assert active['label_source'] == 'SCENARIO_CONTROLLER'


# 3. Insertion Point
def test_3_insertion_point():
    sc = ScenarioController()
    active = sc.select_scenario('INT_0001_three_phase_symmetric')
    inj = active['injection_location']
    assert inj['bus'] == 'Bus5'
    assert inj['mechanism'] == 'CIRCUIT_BREAKER'
    assert inj['phase'] == 'ABC'


# 4. Electrical Event
def test_4_electrical_event():
    npz_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_waveform.npz')
    assert os.path.exists(npz_path), "Interruption waveform NPZ not found"
    data = np.load(npz_path)
    waveform = data['waveform']  # (1000, 3)
    va = waveform[:, 0]
    
    # Pre-event: t in [0.01, 0.035] s -> samples [50, 175]
    pre_rms = np.sqrt(np.mean(va[50:175]**2))
    # Event: t in [0.06, 0.10] s -> samples [300, 500] (steady interrupted state)
    event_rms = np.sqrt(np.mean(va[300:500]**2))
    
    assert pre_rms > 0.55, f"Pre-event RMS ({pre_rms}) should be near nominal 0.588 pu"
    assert event_rms < 0.05, f"Event RMS ({event_rms}) should be near zero during interruption"
    assert event_rms < pre_rms * 0.10, "Event RMS should be < 10% of pre-event RMS (IEEE 1159)"


# 5. Residual RMS
def test_5_residual_rms():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    assert os.path.exists(val_path)
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['residual_voltage_pu'] < 0.10, "Residual voltage ratio must be < 0.10 pu (IEEE 1159)"
    assert val['min_event_rms'] > 0.0, "Physical residual voltage must be non-zero (physical network)"
    assert val['gates']['INT-01_residual_lt_0.10'] is True
    assert val['gates']['INT-02_residual_gt_0.0'] is True


# 6. Event Timing
def test_6_event_timing():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['start_time_s'] is not None
    assert val['end_time_s'] is not None
    assert 0.035 <= val['start_time_s'] <= 0.045, "Onset time should be near configured 0.040 s"
    assert 0.105 <= val['end_time_s'] <= 0.120, "Recovery time should be near configured 0.114 s"
    assert val['start_time_s'] < val['end_time_s']


# 7. Duration
def test_7_duration():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['duration_ms'] >= 8.33, "Interruption duration must be >= 0.5 cycle (8.33 ms)"
    assert 60.0 <= val['duration_ms'] <= 85.0, f"Measured duration ({val['duration_ms']} ms) should match ~73.8 ms"
    assert val['gates']['INT-03_duration_ge_8.33ms'] is True


# 8. Recovery
def test_8_recovery():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['gates']['INT-04_recovery_confirmed'] is True
    
    # Check waveform post-event directly
    npz_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_waveform.npz')
    data = np.load(npz_path)
    waveform = data['waveform']
    # Post-event: t in [0.14, 0.19] s -> samples [700, 950]
    post_rms = np.sqrt(np.mean(waveform[700:950, 0]**2))
    assert post_rms > 0.50, f"Post-event RMS ({post_rms}) must recover to near nominal"


# 9. Phase Response
def test_9_phase_response():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['phase_configuration'] == 'three-phase'
    assert set(val['affected_phases']) == {'A', 'B', 'C'}
    for ph in ['A', 'B', 'C']:
        m = val['per_phase_metrics'][ph]
        assert m['residual_ratio'] < 0.10, f"Phase {ph} residual ratio ({m['residual_ratio']}) must be < 0.10 pu"
        assert m['duration_ms'] >= 8.33


# 10. Secondary Phenomena
def test_10_secondary_phenomena():
    val_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'r', encoding='utf-8') as f:
        val = json.load(f)
    assert val['gates']['INT-ANTI-SWELL'] is True
    assert val['gates']['WAVEFORM_CONTINUITY'] is True
    
    # Verify no uncontrolled overvoltage across all phases
    for ph in ['A', 'B', 'C']:
        assert val['per_phase_metrics'][ph]['max_rms'] < 0.65, f"Phase {ph} experienced unexpected overvoltage"


# 11. Duration Feature Physicality
def test_11_duration_feature():
    feat_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_features.json')
    with open(feat_path, 'r', encoding='utf-8') as f:
        feat = json.load(f)
    dur = feat['duration']
    assert dur > 50.0, f"DSP measured duration ({dur} ms) must physically capture the interruption interval"
    assert dur < 90.0


# 12. Feature Extraction (32 features, phase-aware SNR)
def test_12_feature_extraction():
    feat_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_features.json')
    with open(feat_path, 'r', encoding='utf-8') as f:
        feat = json.load(f)
    assert len(feat) == 32  # Authoritative 32 model features
    for k in _MODEL_FEATURE_ORDER:
        assert k in feat, f"Missing required model feature: {k}"
        v = feat[k]
        assert not np.isnan(v), f"Feature {k} is NaN"
        assert not np.isinf(v), f"Feature {k} is Inf"
    # Phase-aware SNR
    assert feat['snr'] is not None
    assert np.isfinite(feat['snr'])


# 13. Metadata Completeness & Checksums
def test_13_metadata_completeness():
    meta_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_metadata.json')
    assert os.path.exists(meta_path)
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    assert meta['class'] == 'Interruption'
    assert meta['label_idx'] == 2
    assert meta['label_source'] == 'SCENARIO_CONTROLLER'
    assert 'parameter_provenance' in meta
    assert 'standard_references' in meta
    assert 'checksums' in meta
    for fn, sha in meta['checksums'].items():
        assert len(sha) == 64


# 14. Pristine Model Integrity
def test_14_pristine_model_integrity():
    assert verify_pristine_model_integrity() is True
    with open(PRISTINE_MODEL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    assert actual_sha == PRISTINE_SHA256


# 15. Existing Integration Regression
def test_15_existing_integration():
    from dsp.waveform_frame import WaveformFrame
    from dsp.phase_processor import process_waveform_frame
    from dsp.event_engine import ThreePhaseEventEngine
    
    # Verify production pipeline components initialize and function
    engine = ThreePhaseEventEngine()
    assert engine is not None
    
    # Test synthetic normal frame through pipeline
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    frame = WaveformFrame(
        timestamp_utc=1000.0,
        sampling_rate_hz=5000.0,
        nominal_frequency_hz=60.0,
        phases={
            "L1": np.sin(2 * np.pi * 60.0 * t).astype(np.float32),
            "L2": np.sin(2 * np.pi * 60.0 * t - 2 * np.pi / 3).astype(np.float32),
            "L3": np.sin(2 * np.pi * 60.0 * t + 2 * np.pi / 3).astype(np.float32),
        }
    )
    result = process_waveform_frame(frame)
    assert result is not None
    assert len(result) == 3
    
    # Verify Normal reference dataset still intact
    normal_csv = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal', 'normal_features.csv')
    assert os.path.exists(normal_csv)
    # Verify Sag reference dataset still intact
    sag_csv = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag', 'sag_features.csv')
    assert os.path.exists(sag_csv)
    # Verify Swell reference dataset still intact
    swell_csv = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'swell', 'swell_features.csv')
    assert os.path.exists(swell_csv)


# 16. ML Decoupling Confirmation
def test_16_ml_decoupling():
    meta_path = os.path.join(INT_DATA_DIR, 'interruption_scenario_0001_metadata.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    ml_eval = meta['ml_evaluation']
    assert ml_eval['model_domain_status'] == 'OUT_OF_DOMAIN'
    assert ml_eval['decoupling_confirmed'] is True
    assert meta['label_source'] == 'SCENARIO_CONTROLLER'
    assert meta['class'] == 'Interruption'

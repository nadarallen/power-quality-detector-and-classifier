"""
tests/test_gate3e_sag_dataset.py
--------------------------------
Automated test suite verifying all Gate 3E Voltage Sag dataset requirements.
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

SAG_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag')
NPZ_PATH = os.path.join(SAG_DIR, 'sag_waveforms.npz')
CSV_PATH = os.path.join(SAG_DIR, 'sag_features.csv')
SCEN_PATH = os.path.join(SAG_DIR, 'sag_scenarios.json')
META_PATH = os.path.join(SAG_DIR, 'sag_dataset_metadata.json')


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_gate3e_pristine_model_integrity():
    """Verify pristine IEEE 9-bus reference model is 100% untouched."""
    assert os.path.exists(PRISTINE_MODEL), f"Pristine model missing: {PRISTINE_MODEL}"
    current_sha = compute_sha256(PRISTINE_MODEL)
    assert current_sha == PRISTINE_SHA256, (
        f"Pristine model modified! Expected {PRISTINE_SHA256}, got {current_sha}"
    )


def test_gate3e_dataset_artifacts_exist():
    """Verify all four dataset artifacts exist and are non-empty."""
    for p in [NPZ_PATH, CSV_PATH, SCEN_PATH, META_PATH]:
        assert os.path.exists(p), f"Artifact missing: {p}"
        assert os.path.getsize(p) > 0, f"Artifact empty: {p}"


def test_gate3e_dataset_size_and_dimensions():
    """Verify dataset contains 1,000–1,500 unique frames with correct dimensions."""
    data = np.load(NPZ_PATH)
    waveforms = data['waveforms']
    assert waveforms.ndim == 3, f"Expected 3D waveforms, got shape {waveforms.shape}"
    n_frames, n_samples, n_channels = waveforms.shape
    assert 1000 <= n_frames <= 1500, f"Expected 1,000-1,500 frames, got {n_frames}"
    assert n_samples == 1000, f"Expected 1,000 samples/frame, got {n_samples}"
    assert n_channels == 3, f"Expected 3 phases (L1, L2, L3), got {n_channels}"

    df = pd.read_csv(CSV_PATH)
    assert len(df) == n_frames, f"CSV rows ({len(df)}) != NPZ frames ({n_frames})"


def test_gate3e_zero_duplicates():
    """Verify zero duplicate waveforms exist using exact byte hashes."""
    data = np.load(NPZ_PATH)
    waveforms = data['waveforms']
    hashes = set()
    for i in range(len(waveforms)):
        h = hashlib.md5(waveforms[i].tobytes()).hexdigest()
        assert h not in hashes, f"Duplicate waveform frame detected at index {i}"
        hashes.add(h)
    assert len(hashes) == len(waveforms)


def test_gate3e_numerical_integrity():
    """Verify zero NaN and zero Inf across all waveforms and 32 features."""
    data = np.load(NPZ_PATH)
    waveforms = data['waveforms']
    assert not np.any(np.isnan(waveforms)), "NaN in waveforms"
    assert not np.any(np.isinf(waveforms)), "Inf in waveforms"

    df = pd.read_csv(CSV_PATH)
    from dsp.phase_processor import _MODEL_FEATURE_ORDER
    for col in _MODEL_FEATURE_ORDER:
        assert col in df.columns, f"Missing feature: {col}"
        assert not df[col].isnull().any(), f"NaN in feature {col}"
        assert not np.isinf(df[col]).any(), f"Inf in feature {col}"


def test_gate3e_ground_truth_labeling():
    """Verify ground truth originates strictly from scenario controller, not ML."""
    df = pd.read_csv(CSV_PATH)
    assert (df['class'] == 'Sag').all(), "Not all frames labeled as Sag"
    assert (df['label_idx'] == 5).all(), "Not all label_idx == 5"
    assert (df['label_source'] == 'SCENARIO_CONTROLLER').all(), "Label source not SCENARIO_CONTROLLER"


def test_gate3e_leakage_prevention():
    """Verify group-based partition prevents cross-split simulation trajectory leakage."""
    df = pd.read_csv(CSV_PATH)
    train_sims = set(df[df['split'] == 'train']['simulation_id'].unique())
    val_sims   = set(df[df['split'] == 'val']['simulation_id'].unique())
    test_sims  = set(df[df['split'] == 'test']['simulation_id'].unique())

    assert len(train_sims) > 0 and len(val_sims) > 0 and len(test_sims) > 0
    assert len(train_sims.intersection(val_sims)) == 0, "Leakage between train and val!"
    assert len(train_sims.intersection(test_sims)) == 0, "Leakage between train and test!"
    assert len(val_sims.intersection(test_sims)) == 0, "Leakage between val and test!"


def test_gate3e_operating_condition_and_phase_coverage():
    """Verify coverage across multiple operating conditions and phase configurations."""
    df = pd.read_csv(CSV_PATH)
    unique_conds = df['operating_condition_id'].nunique()
    assert unique_conds >= 30, f"Expected >= 30 operating conditions, got {unique_conds}"

    phase_configs = set(df['phase_config'].unique())
    assert 'three-phase' in phase_configs, "Missing three-phase sag events"
    assert 'phase-to-ground' in phase_configs, "Missing phase-to-ground sag events"
    assert 'phase-to-phase' in phase_configs, "Missing phase-to-phase sag events"


def test_gate3e_physical_parameter_distributions():
    """Verify Sag parameters conform to IEEE 1159 ranges."""
    df = pd.read_csv(CSV_PATH)
    # Residual voltage must be in (0.10, 0.90] pu
    min_res = df['residual_voltage_pu'].min()
    max_res = df['residual_voltage_pu'].max()
    assert min_res >= 0.10, f"Residual voltage below 0.10 pu: {min_res}"
    assert max_res <= 0.90, f"Residual voltage above 0.90 pu: {max_res}"

    # Duration must be >= 0.5 cycle (8.3 ms) and <= 150 ms (within 200 ms frame)
    min_dur = df['duration_ms'].min()
    max_dur = df['duration_ms'].max()
    assert min_dur >= 8.3, f"Sag duration below 0.5 cycle: {min_dur}"
    assert max_dur <= 150.0, f"Sag duration exceeds window limit: {max_dur}"


def test_gate3e_metadata_and_checksum_consistency():
    """Verify metadata JSON correctly records artifact checksums and statistics."""
    with open(META_PATH, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    assert meta['gate'] == 'GATE 3E'
    assert meta['pristine_reference_model']['status'] == 'UNTOUCHED'
    assert meta['counts']['total_accepted_frames'] == 1152
    assert meta['counts']['total_rejected_frames'] == 0

    assert meta['checksums']['sag_waveforms_npz'] == compute_sha256(NPZ_PATH)
    assert meta['checksums']['sag_features_csv'] == compute_sha256(CSV_PATH)
    assert meta['checksums']['sag_scenarios_json'] == compute_sha256(SCEN_PATH)

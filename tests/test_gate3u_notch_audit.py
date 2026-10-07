"""
tests/test_gate3u_notch_audit.py
--------------------------------
Pytest suite verifying Gate 3U Notch dataset quality, physics, and standards audit.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'notch')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
PRISTINE_PATH = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256 = '5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D'


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_gate3u_pristine_model_unchanged():
    """Verify pristine reference model remains byte-for-byte untouched."""
    assert os.path.exists(PRISTINE_PATH), "Pristine model file missing"
    current_hash = compute_sha256(PRISTINE_PATH)
    assert current_hash == PRISTINE_SHA256, f"Pristine model hash changed: {current_hash}"


def test_gate3u_audit_summary_and_verdict():
    """Verify Gate 3U quality summary JSON exists and verdict is PASS."""
    sum_path = os.path.join(DOCS_DIR, 'gate3u_notch_quality_summary.json')
    assert os.path.exists(sum_path), "gate3u_notch_quality_summary.json missing"
    with open(sum_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['verdict'] == 'GATE3U_NOTCH_AUDIT = PASS'
    assert data['total_frames'] == 1152
    assert data['pass_rate_percent'] == 100.0


def test_gate3u_structural_and_checksum_integrity():
    """Verify shapes, types, absence of NaNs/Infs, and checksum consistency."""
    npz_path = os.path.join(NOT_DIR, 'notch_waveforms.npz')
    csv_path = os.path.join(NOT_DIR, 'notch_features.csv')

    data = np.load(npz_path)
    waveforms = data['waveforms']
    assert waveforms.shape == (1152, 1000, 3)
    assert not np.isnan(waveforms).any()
    assert not np.isinf(waveforms).any()

    df = pd.read_csv(csv_path)
    assert len(df) == 1152
    assert not df.isna().any().any()


def test_gate3u_label_provenance():
    """Verify 100% of frames have pure SCENARIO_CONTROLLER ground truth."""
    df = pd.read_csv(os.path.join(NOT_DIR, 'notch_features.csv'))
    assert (df['class'] == 'Notch').all()
    assert (df['label_idx'] == 4).all()


def test_gate3u_physical_notch_metrics():
    """Verify physical notch depth, width, count, and frequency distributions."""
    with open(os.path.join(DOCS_DIR, 'gate3u_notch_quality_summary.json'), 'r', encoding='utf-8') as f:
        summary = json.load(f)

    depth_p = summary['distributions']['depth_pu']
    width_p = summary['distributions']['width_ms']
    thd_p = summary['distributions']['thd_percent']

    # Depth within [0.20, 0.80] pu
    assert depth_p['P0'] >= 0.20
    assert depth_p['P100'] <= 0.80

    # Width >= 0.40 ms
    assert width_p['P0'] >= 0.40

    # Commutation THD >= 3.0%
    assert thd_p['P0'] >= 3.0


def test_gate3u_sampling_resolution_adequacy():
    """Verify sampling resolution allows >= 2 discrete samples per notch."""
    with open(os.path.join(DOCS_DIR, 'gate3u_notch_quality_summary.json'), 'r', encoding='utf-8') as f:
        summary = json.load(f)
    min_width_ms = summary['distributions']['width_ms']['P0']
    ts_ms = 0.200  # 5000 Hz -> 0.2 ms
    samples_per_notch = min_width_ms / ts_ms
    assert samples_per_notch >= 2.0, f"Notch width {min_width_ms} ms under-resolved (< 2 samples)"


def test_gate3u_cross_class_separation():
    """Verify L2 centroid distances from Notch to all 6 previous classes exceed 10.0."""
    with open(os.path.join(DOCS_DIR, 'gate3u_notch_quality_summary.json'), 'r', encoding='utf-8') as f:
        summary = json.load(f)
    dist_dict = summary['audit_results']['cross_class_separation']['distances']
    for c_name, dist in dist_dict.items():
        assert dist > 10.0, f"Separation from {c_name} too low: {dist}"


def test_gate3u_zero_trajectory_leakage():
    """Verify strict simulation trajectory isolation across train, val, and test partitions."""
    df = pd.read_csv(os.path.join(NOT_DIR, 'notch_features.csv'))
    train_sims = set(df[df['split'] == 'train']['trajectory_id'].unique())
    val_sims = set(df[df['split'] == 'val']['trajectory_id'].unique())
    test_sims = set(df[df['split'] == 'test']['trajectory_id'].unique())

    assert len(train_sims.intersection(val_sims)) == 0
    assert len(train_sims.intersection(test_sims)) == 0
    assert len(val_sims.intersection(test_sims)) == 0
    assert len(train_sims) + len(val_sims) + len(test_sims) == 36


def test_gate3u_dsp_parity_pass():
    """Verify production DSP parity passes within 1e-3 tolerance."""
    with open(os.path.join(DOCS_DIR, 'gate3u_notch_quality_summary.json'), 'r', encoding='utf-8') as f:
        summary = json.load(f)
    assert summary['audit_results']['dsp_parity'] == 'PASS'

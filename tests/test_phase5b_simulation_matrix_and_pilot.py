"""
tests/test_phase5b_simulation_matrix_and_pilot.py
-------------------------------------------------
Automated test suite verifying the Phase 5B Simulation Matrix, Pilot Generation,
and Physical Validation deliverables for the IEEE 9-bus PQ comparative study.
"""

import os
import json
import hashlib
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRISTINE_MODEL = os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_SHA256_EXPECTED = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"

FROZEN_MANIFEST = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'dataset_manifest_v1.json')
MATRIX_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b_simulation_matrix.json')
MATRIX_CSV = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b_simulation_matrix.csv')

PILOT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot')
PILOT_MANIFEST = os.path.join(PILOT_DIR, 'pilot_manifest_v1.json')
PILOT_CHECKSUMS = os.path.join(PILOT_DIR, 'checksums_sha256.txt')
PILOT_RAW_DIR = os.path.join(PILOT_DIR, 'raw')
PILOT_PROCESSED_DIR = os.path.join(PILOT_DIR, 'processed')


def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_pristine_simulink_model_integrity():
    """Gate requirement: IEEE_9bus_PQD_HIL_R2025a.slx must remain byte-for-byte untouched."""
    assert os.path.exists(PRISTINE_MODEL), f"Pristine model missing: {PRISTINE_MODEL}"
    actual_sha = compute_file_sha256(PRISTINE_MODEL)
    assert actual_sha == PRISTINE_SHA256_EXPECTED, (
        f"Pristine model checksum mismatch! Expected: {PRISTINE_SHA256_EXPECTED}, got: {actual_sha}"
    )


def test_frozen_baseline_dataset_preserved():
    """Phase 4 frozen baseline of 9,184 frames must remain completely untouched."""
    assert os.path.exists(FROZEN_MANIFEST), f"Frozen manifest missing: {FROZEN_MANIFEST}"
    with open(FROZEN_MANIFEST, 'r', encoding='utf-8') as f:
        m = json.load(f)
    assert m.get('freeze_status') == 'FROZEN_BASELINE'
    totals = m.get('dataset_totals', {})
    assert totals.get('total_frames') == 9184
    assert totals.get('class_count') == 8
    assert totals.get('train_frames') == 6594
    assert totals.get('val_frames') == 1295
    assert totals.get('test_frames') == 1295


def test_simulation_matrix_schema_and_coverage():
    """Verify Phase 5B simulation matrix design, operating condition families, and classes."""
    assert os.path.exists(MATRIX_JSON), f"Matrix JSON missing: {MATRIX_JSON}"
    assert os.path.exists(MATRIX_CSV), f"Matrix CSV missing: {MATRIX_CSV}"

    with open(MATRIX_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    assert catalog.get('base_frequency_hz') == 60.0
    assert catalog.get('sampling_rate_hz') == 5000.0
    assert catalog.get('window_samples') == 1000
    assert catalog.get('window_ms') == 200.0
    assert catalog.get('classes_count') == 8
    assert catalog.get('pilot_trajectories_count') == 24

    # Verify Challenge Families exist in catalog
    op_cat = catalog.get('operating_condition_catalog', {})
    challenge_families = [c['family'] for c in op_cat.values() if 'CHALLENGE' in c.get('family', '')]
    assert len(challenge_families) >= 4, "Challenge operating families missing from matrix catalog"


def test_pilot_manifest_integrity_and_validation():
    """Verify the 24 pilot trajectories in pilot_manifest_v1.json pass physical validation."""
    assert os.path.exists(PILOT_MANIFEST), f"Pilot manifest missing: {PILOT_MANIFEST}"
    with open(PILOT_MANIFEST, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    assert manifest.get('total_pilot_trajectories') == 24
    assert manifest.get('classes_represented') == 8
    assert manifest.get('all_passed') is True, "Not all pilot trajectories passed physical validation!"

    counts = manifest.get('class_counts', {})
    for cls in ['Flicker', 'Harmonics', 'Interruption', 'Normal', 'Notch', 'Sag', 'Swell', 'Transient']:
        assert counts.get(cls) == 3, f"Class {cls} count {counts.get(cls)} != 3"

    split_counts = manifest.get('split_counts', {})
    assert split_counts.get('train') == 9
    assert split_counts.get('val') == 7
    assert split_counts.get('challenge') == 8


def test_pilot_checksums_match_all_artifacts():
    """Verify that all raw and processed artifacts match their recorded SHA-256 checksums."""
    assert os.path.exists(PILOT_CHECKSUMS), f"Checksums file missing: {PILOT_CHECKSUMS}"
    with open(PILOT_CHECKSUMS, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 48, f"Expected 48 checksum lines (24 raw + 24 processed), found {len(lines)}"

    for line in lines:
        parts = line.split(maxsplit=1)
        expected_sha = parts[0].lower()
        rel_path = parts[1].replace('\\', '/')
        full_path = os.path.join(PILOT_DIR, rel_path)
        assert os.path.exists(full_path), f"Artifact missing on disk: {full_path}"
        actual_sha = hashlib.sha256(open(full_path, 'rb').read()).hexdigest().lower()
        assert actual_sha == expected_sha, f"Checksum mismatch for {rel_path}!"


def test_pilot_processed_waveforms_structure():
    """Verify processed NPZ waveforms conform to the 3-phase 5 kHz 200 ms standard contract."""
    npz_files = [os.path.join(PILOT_PROCESSED_DIR, f) for f in os.listdir(PILOT_PROCESSED_DIR) if f.endswith('.npz')]
    assert len(npz_files) == 24

    for fpath in npz_files:
        data = np.load(fpath)
        assert 'vabc' in data
        assert 'iabc' in data
        vabc = data['vabc']
        iabc = data['iabc']

        assert vabc.shape == (1000, 3), f"Invalid vabc shape in {fpath}"
        assert iabc.shape == (1000, 3), f"Invalid iabc shape in {fpath}"
        assert not np.isnan(vabc).any(), f"NaN in vabc {fpath}"
        assert not np.isinf(vabc).any(), f"Inf in vabc {fpath}"
        assert float(data['fs']) == 5000.0
        assert float(data['f0']) == 60.0
        assert bool(data['validation_passed']) is True


def test_quarantined_challenge_split_leakage_safety():
    """Verify that challenge operating conditions are strictly quarantined from train and val."""
    with open(PILOT_MANIFEST, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    train_conds = {r['operating_condition_id'] for r in manifest['records'] if r['split'] == 'train'}
    val_conds = {r['operating_condition_id'] for r in manifest['records'] if r['split'] == 'val'}
    challenge_conds = {r['operating_condition_id'] for r in manifest['records'] if r['split'] == 'challenge'}

    # Condition IDs 33-36 are strictly challenge
    for cid in challenge_conds:
        assert cid not in train_conds, f"Leakage: Challenge condition {cid} present in train set!"
        assert cid not in val_conds, f"Leakage: Challenge condition {cid} present in val set!"

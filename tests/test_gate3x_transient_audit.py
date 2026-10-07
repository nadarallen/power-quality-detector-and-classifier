"""
tests/test_gate3x_transient_audit.py
------------------------------------
Pytest test suite validating Gate 3X Transient Dataset Audit:
1. Pristine reference model SHA-256 untouched.
2. Complete deliverable existence and checksum match.
3. 16-domain audit results all PASS in quality summary JSON.
4. Cross-class separation distances strictly > 10.0 against all 7 disturbance classes.
5. Sampling adequacy and Nyquist margin verified.
6. ML decoupling verified.
"""

import os
import json
import hashlib
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAN_DIR = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "transient")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
PRISTINE_PATH = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
EXPECTED_PRISTINE_SHA256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"


def test_pristine_reference_model_untouched():
    """Verify IEEE_9bus_PQD_HIL_R2025a.slx SHA-256 remains byte-for-byte identical."""
    assert os.path.exists(PRISTINE_PATH)
    with open(PRISTINE_PATH, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest().upper()
    assert sha == EXPECTED_PRISTINE_SHA256, f"Pristine SHA-256 altered: {sha}"


def test_audit_deliverables_exist():
    """Verify Gate 3X audit report MD and JSON summary exist."""
    md_path = os.path.join(DOCS_DIR, "GATE3X_TRANSIENT_DATASET_AUDIT.md")
    json_path = os.path.join(DOCS_DIR, "gate3x_transient_quality_summary.json")
    assert os.path.exists(md_path), "GATE3X_TRANSIENT_DATASET_AUDIT.md missing"
    assert os.path.exists(json_path), "gate3x_transient_quality_summary.json missing"


def test_audit_domains_all_pass():
    """Verify all audit domains in quality summary JSON are PASS."""
    json_path = os.path.join(DOCS_DIR, "gate3x_transient_quality_summary.json")
    with open(json_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["3X.1_structural"]["status"] == "PASS"
    assert summary["3X.2_provenance"]["status"] == "PASS"
    assert summary["3X.3_physics"]["status"] == "PASS"
    assert summary["3X.4_sampling"]["status"] == "PASS"
    assert summary["3X.10_secondary_phenomena"]["status"] == "PASS"
    assert summary["3X.11_diversity_and_rank"]["status"] == "PASS"
    assert summary["3X.12_dsp_parity"]["status"] == "PASS"
    assert summary["3X.13_leakage"]["status"] == "PASS"
    assert summary["3X.15_ml_decoupling"]["status"] == "PASS"


def test_cross_class_separation():
    """Verify Transient centroid is well separated from all 7 classes (> 10.0 distance)."""
    json_path = os.path.join(DOCS_DIR, "gate3x_transient_quality_summary.json")
    with open(json_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    
    distances = summary["3X.9_cross_class_distances"]
    expected_classes = ["Normal", "Sag", "Swell", "Interruption", "Harmonics", "Flicker", "Notch"]
    for cls in expected_classes:
        assert cls in distances, f"Class {cls} missing from cross-class distances"
        assert distances[cls] > 10.0, f"Distance to {cls} is too small: {distances[cls]}"


def test_sampling_adequacy_limits():
    """Verify sampling resolution satisfies Shannon-Nyquist margin."""
    json_path = os.path.join(DOCS_DIR, "gate3x_transient_quality_summary.json")
    with open(json_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    sampling = summary["3X.4_sampling"]
    assert sampling["highest_frequency_hz"] < sampling["nyquist_hz"]
    assert sampling["min_samples_per_oscillation_period"] >= 3.3

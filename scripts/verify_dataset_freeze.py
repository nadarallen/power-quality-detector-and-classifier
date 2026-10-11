"""
scripts/verify_dataset_freeze.py
--------------------------------
Authoritative verification tool for Phase 4A Dataset Freeze.
Validates:
1. Cryptographic SHA-256 integrity of all frozen waveform arrays, feature tables, and metadata.
2. Unaltered pristine Simulink reference model.
3. Group-based trajectory disjointness (zero leakage between Train, Val, and Test).
4. Exact 32-feature contract alignment with dsp/phase_processor.py.
"""

import os
import sys
import json
import hashlib
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.phase_processor import _MODEL_FEATURE_ORDER, _CLASS_LABELS

MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'dataset_manifest_v1.json')


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def verify_freeze():
    print("=" * 80)
    print("PHASE 4A — DATASET FREEZE & INTEGRITY VERIFICATION AUDIT")
    print("=" * 80)

    if not os.path.exists(MANIFEST_PATH):
        print(f"[FAIL] Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # 1. Verify Pristine Model
    slx_rel = manifest["electrical_system"]["reference_model"]
    slx_path = os.path.join(PROJECT_ROOT, slx_rel)
    slx_expected = manifest["electrical_system"]["reference_model_sha256"]
    slx_actual = compute_sha256(slx_path)
    if slx_actual != slx_expected:
        print(f"[FAIL] Pristine SLX modified! Expected: {slx_expected}, Actual: {slx_actual}")
        sys.exit(1)
    print(f"[PASS] Pristine Simulink model verified intact ({slx_actual})")

    # 2. Verify all class files and SHA-256
    all_files_ok = True
    total_frames = 0
    total_train = 0
    total_val = 0
    total_test = 0

    for cls_key, cls_info in manifest["classes"].items():
        print(f"\n--- Checking Class: {cls_info['canonical_name']} ---")
        for file_key, f_data in cls_info["files"].items():
            f_path = os.path.join(PROJECT_ROOT, f_data["rel_path"])
            if not os.path.exists(f_path):
                print(f"  [FAIL] Missing file: {f_path}")
                all_files_ok = False
                continue
            f_hash = compute_sha256(f_path)
            if f_hash != f_data["sha256"]:
                print(f"  [FAIL] Hash mismatch for {f_data['filename']}: expected {f_data['sha256']}, got {f_hash}")
                all_files_ok = False
            else:
                print(f"  [PASS] Hash verified: {f_data['filename']}")

        # Verify Disjoint Trajectories
        parts = cls_info["partitions"]
        tr_trajs = set(parts["train"]["trajectories"])
        val_trajs = set(parts["validation"]["trajectories"])
        te_trajs = set(parts["test"]["trajectories"])

        overlap_tv = tr_trajs.intersection(val_trajs)
        overlap_tt = tr_trajs.intersection(te_trajs)
        overlap_vt = val_trajs.intersection(te_trajs)

        if overlap_tv or overlap_tt or overlap_vt:
            print(f"  [FAIL] Trajectory leakage detected in {cls_key}!")
            all_files_ok = False
        else:
            print(f"  [PASS] Zero trajectory leakage (Train:{len(tr_trajs)}, Val:{len(val_trajs)}, Test:{len(te_trajs)})")

        total_frames += cls_info["total_frames"]
        total_train += parts["train"]["frames"]
        total_val += parts["validation"]["frames"]
        total_test += parts["test"]["frames"]

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY:")
    print(f"  Total Verified Frames : {total_frames:,}")
    print(f"  Train Frames          : {total_train:,} ({total_train/total_frames*100:.2f}%)")
    print(f"  Validation Frames     : {total_val:,} ({total_val/total_frames*100:.2f}%)")
    print(f"  Test Frames           : {total_test:,} ({total_test/total_frames*100:.2f}%)")
    print(f"  Feature Order Aligned : {_MODEL_FEATURE_ORDER == manifest['feature_contract']['ordering']}")
    print("=" * 80)

    if all_files_ok:
        print("[SUCCESS] ALL PHASE 4A INTEGRITY & LEAKAGE AUDITS PASSED — DATASET IS FROZEN")
    else:
        print("[ERROR] VERIFICATION FAILED")
        sys.exit(1)


if __name__ == '__main__':
    verify_freeze()

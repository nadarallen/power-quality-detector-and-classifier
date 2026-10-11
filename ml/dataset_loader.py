"""
ml/dataset_loader.py
--------------------
Canonical Dataset Loader for 60-Hz IEEE 9-bus PQD Baseline.
Reads directly from data/ieee9bus_60hz/dataset_manifest_v1.json.
Enforces:
1. Exact 32 production features in immutable manifest order.
2. Fixed, trajectory-safe partition assignments (Train: 6,594, Val: 1,295, Test: 1,295).
3. Zero metadata leakage into feature matrices.
4. Locked test set safety protection.
"""

import os
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_MANIFEST_PATH = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "dataset_manifest_v1.json")


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def load_manifest(manifest_path: Optional[str] = None) -> Tuple[dict, str]:
    path = manifest_path or DEFAULT_MANIFEST_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Manifest not found: {path}")
    manifest_hash = compute_sha256(path)
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest, manifest_hash


def load_ieee9bus_data(
    manifest_path: Optional[str] = None,
    verify_checksums: bool = True,
    include_test: bool = False
) -> Dict[str, Tuple[np.ndarray, np.ndarray, pd.DataFrame]]:
    """
    Loads features and labels for requested partitions.

    Args:
        manifest_path: Path to dataset_manifest_v1.json (default: authoritative path)
        verify_checksums: Whether to verify SHA-256 for all feature CSVs
        include_test: Explicit safety gate. If False, locked test set is NOT loaded.

    Returns:
        Dictionary mapping partition name ('train', 'val', and optionally 'test') to:
        (X, y, metadata_df)
        - X: np.ndarray of shape (N, 32), float64, containing strictly the 32 features in contract order
        - y: np.ndarray of shape (N,), int64, class index matching manifest class_to_index
        - metadata_df: pd.DataFrame of shape (N, M), containing frame_id, trajectory_id, canonical_class, split
    """
    manifest, manifest_hash = load_manifest(manifest_path)
    feature_order = manifest["feature_contract"]["ordering"]
    class_mapping = manifest["preprocessing_contract"]["class_to_index"]
    target_classes = manifest["preprocessing_contract"]["target_classes"]

    partitions_to_load = ["train", "val"]
    if include_test:
        partitions_to_load.append("test")

    partition_data = {p: {"X": [], "y": [], "meta": []} for p in partitions_to_load}

    for cls_key, cls_info in manifest["classes"].items():
        csv_rel = cls_info["files"]["features_csv"]["rel_path"]
        csv_path = os.path.join(PROJECT_ROOT, csv_rel)

        if verify_checksums:
            expected_hash = cls_info["files"]["features_csv"]["sha256"]
            actual_hash = compute_sha256(csv_path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Integrity check failed for {csv_rel}! "
                    f"Expected {expected_hash}, got {actual_hash}"
                )

        df = pd.read_csv(csv_path)

        # Identify trajectory and frame ID columns
        traj_col = None
        for candidate in ["simulation_id", "trajectory_id", "scenario_id"]:
            if candidate in df.columns:
                traj_col = candidate
                break

        id_col = "frame_id" if "frame_id" in df.columns else ("frame_idx" if "frame_idx" in df.columns else None)
        canonical_label = cls_info["canonical_name"]
        label_idx = class_mapping[canonical_label]

        # Extract features and split
        for p in partitions_to_load:
            sub_df = df[df["split"] == p]
            if len(sub_df) == 0:
                continue

            # Strict 32 features extraction
            X_sub = sub_df[feature_order].values.astype(np.float64)
            y_sub = np.full(len(sub_df), label_idx, dtype=np.int64)

            meta_records = []
            for idx_row, row in sub_df.iterrows():
                f_id = row[id_col] if id_col else f"{cls_key}_{idx_row}"
                if traj_col:
                    t_id = row[traj_col]
                else:
                    # For transient: TRAN_F0000_tran_sim_01_W00
                    import re
                    m = re.search(r'(tran_sim_\d+)', str(f_id))
                    t_id = m.group(1) if m else f"{cls_key}_{idx_row}"
                # Namespace trajectory by class to prevent cross-class accidental name collision
                namespaced_t_id = f"{cls_key}::{t_id}"
                meta_records.append({
                    "frame_id": f_id,
                    "trajectory_id": namespaced_t_id,
                    "raw_trajectory_id": t_id,
                    "class_name": canonical_label,
                    "class_index": label_idx,
                    "split": p
                })

            partition_data[p]["X"].append(X_sub)
            partition_data[p]["y"].append(y_sub)
            partition_data[p]["meta"].append(pd.DataFrame(meta_records))

    result = {}
    for p in partitions_to_load:
        X_cat = np.vstack(partition_data[p]["X"])
        y_cat = np.concatenate(partition_data[p]["y"])
        meta_cat = pd.concat(partition_data[p]["meta"], ignore_index=True)
        result[p] = (X_cat, y_cat, meta_cat)

    # Validate Partition Counts
    expected_counts = {
        "train": manifest["dataset_totals"]["train_frames"],
        "val": manifest["dataset_totals"]["val_frames"]
    }
    if include_test:
        expected_counts["test"] = manifest["dataset_totals"]["test_frames"]

    for p, expected_n in expected_counts.items():
        actual_n = len(result[p][0])
        if actual_n != expected_n:
            raise ValueError(f"Partition {p} count mismatch: expected {expected_n}, got {actual_n}")

    # Validate Trajectory Disjointness between train and val
    train_trajs = set(result["train"][2]["trajectory_id"].unique())
    val_trajs = set(result["val"][2]["trajectory_id"].unique())
    leakage = train_trajs.intersection(val_trajs)
    if leakage:
        raise ValueError(f"Trajectory leakage detected between train and val: {leakage}")

    return result


if __name__ == "__main__":
    print("Testing Canonical Dataset Loader...")
    data = load_ieee9bus_data(verify_checksums=True, include_test=False)
    print(f"Train: X shape = {data['train'][0].shape}, y shape = {data['train'][1].shape}")
    print(f"Val:   X shape = {data['val'][0].shape}, y shape = {data['val'][1].shape}")
    print("Zero leakage verified between Train and Validation sets.")

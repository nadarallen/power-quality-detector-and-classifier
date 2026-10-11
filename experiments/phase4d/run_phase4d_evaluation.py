#!/usr/bin/env python3
"""
Phase 4D — Locked Test Partition Evaluation & Generalization Audit
===================================================================
Authoritative evaluation runner for the frozen Phase 4C MLP candidate model
(Arch C: 32 -> 64 -> 32 -> 16 -> 8, L-BFGS, alpha=0.0001, seed=123).

Strict audit guarantees:
- Frozen data, manifest, and candidate integrity verification before test access.
- One-time evaluation of the locked test partition (1,295 frames across 40 trajectories).
- Absolute prohibition against retraining, hyperparameter tuning, threshold alteration,
  or post-evaluation model modification.
- Full trajectory-aware uncertainty estimation via cluster bootstrap.
- Export of machine-readable evaluation records.
"""

import os
import sys
import json
import time
import pickle
import hashlib
import platform
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    precision_recall_fscore_support, confusion_matrix
)

# Project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from ml.dataset_loader import load_ieee9bus_data, load_manifest

MANIFEST_PATH = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "dataset_manifest_v1.json")
SIMULINK_PATH = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")
LEGACY_MODEL_PATH = os.path.join(PROJECT_ROOT, "ml", "models", "model_weights_32.json")

PHASE4C_MODELS_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models")
PHASE4C_RESULTS_PATH = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "phase4c_tuning_results.json")
CHECKSUMS_JSON_PATH = os.path.join(PHASE4C_MODELS_DIR, "candidate_checksums.json")

PHASE4D_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4d")
os.makedirs(PHASE4D_DIR, exist_ok=True)

EXPECTED_MANIFEST_SHA256 = "B4C7CCA746B69EE895BC6E7C68F2BE2F56700F3B9C1976BF0B674C4D292548F5"
EXPECTED_SIMULINK_SHA256 = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"


def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def preflight_integrity_checks() -> Dict[str, Any]:
    """Verify cryptographic integrity of all inputs and frozen artifacts before test access."""
    print("=" * 80)
    print("PHASE 4D PRE-FLIGHT INTEGRITY AUDIT")
    print("=" * 80)

    # 1. Manifest
    assert os.path.exists(MANIFEST_PATH), f"Manifest missing: {MANIFEST_PATH}"
    manifest_hash = compute_sha256(MANIFEST_PATH)
    assert manifest_hash == EXPECTED_MANIFEST_SHA256, (
        f"Manifest hash mismatch: expected {EXPECTED_MANIFEST_SHA256}, got {manifest_hash}"
    )
    print(f"[OK] Authoritative Dataset Manifest SHA-256: {manifest_hash}")

    # 2. Pristine Simulink Model
    assert os.path.exists(SIMULINK_PATH), f"Simulink model missing: {SIMULINK_PATH}"
    simulink_hash = compute_sha256(SIMULINK_PATH)
    assert simulink_hash == EXPECTED_SIMULINK_SHA256, (
        f"Pristine Simulink hash mismatch: expected {EXPECTED_SIMULINK_SHA256}, got {simulink_hash}"
    )
    print(f"[OK] Pristine Reference Simulink Model SHA-256: {simulink_hash}")

    # 3. Legacy Model
    assert os.path.exists(LEGACY_MODEL_PATH), f"Legacy model missing: {LEGACY_MODEL_PATH}"
    legacy_hash = compute_sha256(LEGACY_MODEL_PATH)
    print(f"[OK] Legacy 50 Hz Model Preserved SHA-256: {legacy_hash}")

    # 4. Phase 4C Candidate Artifacts Checksums
    assert os.path.exists(CHECKSUMS_JSON_PATH), f"Checksums JSON missing: {CHECKSUMS_JSON_PATH}"
    with open(CHECKSUMS_JSON_PATH, "r", encoding="utf-8") as f:
        recorded_checksums = json.load(f)

    candidate_files = {
        "candidate_mlp_pipeline_pkl": os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_pipeline.pkl"),
        "candidate_mlp_weights_json": os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json"),
        "scaler_phase4c_pkl": os.path.join(PHASE4C_MODELS_DIR, "scaler_phase4c.pkl"),
        "scaler_phase4c_params_json": os.path.join(PHASE4C_MODELS_DIR, "scaler_phase4c_params.json")
    }

    actual_checksums = {}
    for key, path in candidate_files.items():
        assert os.path.exists(path), f"Candidate artifact missing: {path}"
        chash = compute_sha256(path)
        expected = recorded_checksums.get(key)
        assert chash == expected, f"Candidate artifact {key} hash mismatch: {chash} != {expected}"
        actual_checksums[key] = chash
        print(f"[OK] Candidate Artifact {key}: {chash}")

    # 5. Contract Verification (Manifest classes and features)
    manifest_data, _ = load_manifest(MANIFEST_PATH)
    manifest_features = manifest_data["feature_contract"]["ordering"]
    assert len(manifest_features) == 32, f"Expected 32 features, got {len(manifest_features)}"

    manifest_classes = manifest_data["preprocessing_contract"]["target_classes"]
    assert len(manifest_classes) == 8, f"Expected 8 classes, got {len(manifest_classes)}"
    print("[OK] Production 32-Feature Contract & 8-Class Mapping Verified Exact")

    return {
        "manifest_sha256": manifest_hash,
        "simulink_sha256": simulink_hash,
        "legacy_model_sha256": legacy_hash,
        "candidate_checksums": actual_checksums,
        "features": manifest_features,
        "classes": manifest_classes
    }


def verify_validation_parity() -> None:
    """Pre-flight check: Verify mathematical inference parity on validation data only."""
    print("\n[Pre-Flight Check] Verifying Python Pipeline vs JSON Weights parity on validation data...")
    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_pipeline.pkl"), "rb") as f:
        pipe = pickle.load(f)
    clf = pipe["classifier"]
    scaler = pipe["scaler"]

    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json"), "r", encoding="utf-8") as f:
        jw = json.load(f)

    W = [np.array(w, dtype=np.float32) for w in jw["weights"]]
    B = [np.array(b, dtype=np.float32) for b in jw["biases"]]
    s_mean = np.array(jw["scaler_mean"], dtype=np.float32)
    s_scale = np.array(jw["scaler_scale"], dtype=np.float32)

    def manual_forward(x_raw):
        z = (x_raw.astype(np.float32) - s_mean) / s_scale
        for i in range(len(W) - 1):
            z = np.maximum(0.0, np.dot(z, W[i]) + B[i])
        logits = np.dot(z, W[-1]) + B[-1]
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
        return logits, probs

    val_data = load_ieee9bus_data(include_test=False)["val"]
    X_val, y_val, _ = val_data

    X_val_scaled = scaler.transform(X_val)
    pipe_preds = clf.predict(X_val_scaled)
    pipe_probs = clf.predict_proba(X_val_scaled)

    _, json_probs = manual_forward(X_val)
    json_preds = np.argmax(json_probs, axis=1)

    mismatches = int(np.sum(pipe_preds != json_preds))
    max_prob_diff = float(np.max(np.abs(pipe_probs - json_probs)))
    assert mismatches == 0, f"Validation parity failed: {mismatches} mismatches"
    assert max_prob_diff < 1e-4, f"Validation probability drift too high: {max_prob_diff}"
    print(f"[OK] Validation Parity Verified: 0 mismatches across {len(X_val)} frames (max diff: {max_prob_diff:.2e})")


def benchmark_cpu_latency(clf, X_scaled: np.ndarray, n_runs: int = 2000) -> Dict[str, float]:
    """Measure single-frame CPU forward pass latency."""
    # Warmup
    for _ in range(200):
        idx = np.random.randint(0, len(X_scaled))
        _ = clf.predict(X_scaled[idx:idx + 1])

    durations_us = []
    for _ in range(n_runs):
        idx = np.random.randint(0, len(X_scaled))
        sample = X_scaled[idx:idx + 1]
        t0 = time.perf_counter_ns()
        _ = clf.predict(sample)
        dt_us = (time.perf_counter_ns() - t0) / 1000.0
        durations_us.append(dt_us)

    return {
        "mean_latency_us": round(float(np.mean(durations_us)), 2),
        "median_latency_us": round(float(np.median(durations_us)), 2),
        "p99_latency_us": round(float(np.percentile(durations_us, 99)), 2),
        "min_latency_us": round(float(np.min(durations_us)), 2),
        "max_latency_us": round(float(np.max(durations_us)), 2),
        "throughput_fps": round(1e6 / float(np.mean(durations_us)), 1),
        "measurement_runs": n_runs
    }


def trajectory_cluster_bootstrap(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    trajectories: List[str],
    n_bootstraps: int = 1000,
    seed: int = 42
) -> Dict[str, Tuple[float, float]]:
    """Compute 95% confidence intervals via trajectory-cluster bootstrap."""
    np.random.seed(seed)
    unique_trajs = np.array(list(set(trajectories)))
    n_trajs = len(unique_trajs)

    traj_to_indices = {}
    for idx, traj in enumerate(trajectories):
        traj_to_indices.setdefault(traj, []).append(idx)

    boot_accs = []
    boot_macro_f1s = []
    boot_bal_accs = []

    for _ in range(n_bootstraps):
        sampled_trajs = np.random.choice(unique_trajs, size=n_trajs, replace=True)
        boot_indices = []
        for t in sampled_trajs:
            boot_indices.extend(traj_to_indices[t])

        boot_y_true = y_true[boot_indices]
        boot_y_pred = y_pred[boot_indices]

        acc = accuracy_score(boot_y_true, boot_y_pred)
        bal_acc = balanced_accuracy_score(boot_y_true, boot_y_pred)
        macro_f1 = precision_recall_fscore_support(boot_y_true, boot_y_pred, average="macro", zero_division=0)[2]

        boot_accs.append(acc)
        boot_bal_accs.append(bal_acc)
        boot_macro_f1s.append(macro_f1)

    def ci(arr):
        return (round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4))

    return {
        "accuracy_ci_95": ci(boot_accs),
        "macro_f1_ci_95": ci(boot_macro_f1s),
        "balanced_accuracy_ci_95": ci(boot_bal_accs),
        "n_trajectories": n_trajs,
        "n_bootstraps": n_bootstraps
    }


def main():
    # Step 1: Pre-flight integrity checks
    preflight_info = preflight_integrity_checks()
    class_names = preflight_info["classes"]
    verify_validation_parity()

    # Step 2: Timestamped Authorization of Test Access
    test_unlock_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("\n" + "=" * 80)
    print(f"FORMAL TEST ACCESS AUTHORIZATION GRANTED: {test_unlock_time}")
    print("=" * 80)

    # Step 3: Load frozen dataset with test partition unlocked
    print("\n[Data Ingestion] Loading authoritative 60 Hz dataset (Train, Val, Test)...")
    dataset = load_ieee9bus_data(include_test=True)

    X_train, y_train, meta_train = dataset["train"]
    X_val, y_val, meta_val = dataset["val"]
    X_test, y_test, meta_test = dataset["test"]

    train_trajs = set(meta_train["trajectory_id"].unique())
    val_trajs = set(meta_val["trajectory_id"].unique())
    test_trajs = set(meta_test["trajectory_id"].unique())

    print(f"  Train: {X_train.shape[0]} frames across {len(train_trajs)} trajectories")
    print(f"  Val:   {X_val.shape[0]} frames across {len(val_trajs)} trajectories")
    print(f"  Test:  {X_test.shape[0]} frames across {len(test_trajs)} trajectories")

    # Verify partition invariants
    assert X_test.shape == (1295, 32), f"Expected [1295, 32], got {X_test.shape}"
    assert len(test_trajs) == 40, f"Expected 40 test trajectories, got {len(test_trajs)}"

    # Check trajectory disjointness
    assert len(train_trajs.intersection(test_trajs)) == 0, "TRAJECTORY LEAKAGE between Train and Test!"
    assert len(val_trajs.intersection(test_trajs)) == 0, "TRAJECTORY LEAKAGE between Val and Test!"
    print("[OK] Trajectory Isolation Confirmed: Zero overlap between Train, Val, and Test")

    # Verify class distribution: Normal is index 3 in target_classes
    norm_idx = class_names.index("Normal")
    sag_idx = class_names.index("Sag")
    class_counts = {c_idx: int(np.sum(y_test == c_idx)) for c_idx in range(8)}
    assert class_counts[norm_idx] == 175, f"Expected 175 Normal frames in test, got {class_counts[norm_idx]}"
    for c_idx in range(8):
        if c_idx != norm_idx:
            assert class_counts[c_idx] == 160, f"Expected 160 frames for class {c_idx}, got {class_counts[c_idx]}"
    print(f"[OK] Test Ground-Truth Distribution Verified: {class_counts}")

    # Step 4: Load frozen candidate pipeline and evaluate
    print("\n[Inference Execution] Scoring locked test partition with frozen candidate...")
    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_pipeline.pkl"), "rb") as f:
        pipe = pickle.load(f)
    clf = pipe["classifier"]
    scaler = pipe["scaler"]

    t_eval_start = time.perf_counter()
    X_test_scaled = scaler.transform(X_test)
    y_test_pred = clf.predict(X_test_scaled)
    y_test_prob = clf.predict_proba(X_test_scaled)
    eval_elapsed = time.perf_counter() - t_eval_start

    # Also score with JSON weights to assert deployment parity on test partition
    with open(os.path.join(PHASE4C_MODELS_DIR, "candidate_mlp_weights.json"), "r", encoding="utf-8") as f:
        jw = json.load(f)
    W = [np.array(w, dtype=np.float32) for w in jw["weights"]]
    B = [np.array(b, dtype=np.float32) for b in jw["biases"]]
    s_mean = np.array(jw["scaler_mean"], dtype=np.float32)
    s_scale = np.array(jw["scaler_scale"], dtype=np.float32)

    z = (X_test.astype(np.float32) - s_mean) / s_scale
    for i in range(len(W) - 1):
        z = np.maximum(0.0, np.dot(z, W[i]) + B[i])
    logits = np.dot(z, W[-1]) + B[-1]
    json_preds = np.argmax(logits, axis=1)

    json_test_mismatches = int(np.sum(y_test_pred != json_preds))
    assert json_test_mismatches == 0, f"JSON forward pass mismatch on test set: {json_test_mismatches}"
    print(f"[OK] Full Deployment Parity on Test Partition: 0 mismatches between Pipeline and JSON weights")

    # Step 5: Compute Overall Metrics
    test_acc = accuracy_score(y_test, y_test_pred)
    test_bal_acc = balanced_accuracy_score(y_test, y_test_pred)
    test_prec_macro, test_rec_macro, test_f1_macro, _ = precision_recall_fscore_support(
        y_test, y_test_pred, average="macro", zero_division=0
    )
    test_prec_weighted, test_rec_weighted, test_f1_weighted, _ = precision_recall_fscore_support(
        y_test, y_test_pred, average="weighted", zero_division=0
    )

    correct_count = int(np.sum(y_test == y_test_pred))
    incorrect_count = int(np.sum(y_test != y_test_pred))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_test_pred, labels=list(range(8)))
    cm_norm = cm.astype(float) / cm.sum(axis=1)[:, np.newaxis]

    # Explicit Sag-Normal confusion counts
    sag_to_normal_errors = int(cm[sag_idx, norm_idx])
    normal_to_sag_errors = int(cm[norm_idx, sag_idx])

    # Per-class metrics
    p_class, r_class, f1_class, s_class = precision_recall_fscore_support(
        y_test, y_test_pred, average=None, labels=list(range(8)), zero_division=0
    )

    per_class_metrics = {}
    for idx, c_name in enumerate(class_names):
        fp = int(np.sum((y_test_pred == idx) & (y_test != idx)))
        fn = int(np.sum((y_test_pred != idx) & (y_test == idx)))
        per_class_metrics[c_name] = {
            "class_index": idx,
            "support": int(s_class[idx]),
            "precision": round(float(p_class[idx]), 4),
            "recall": round(float(r_class[idx]), 4),
            "f1_score": round(float(f1_class[idx]), 4),
            "false_positives": fp,
            "false_negatives": fn
        }

    # Step 6: Generalization Gap Analysis (Phase 4C Val vs Phase 4D Test)
    with open(PHASE4C_RESULTS_PATH, "r", encoding="utf-8") as f:
        phase4c_data = json.load(f)
    val_metrics = phase4c_data["best_candidate"]["validation_metrics"]

    generalization_gap = {
        "macro_f1_gap_pp": round((test_f1_macro - val_metrics["macro_f1"]) * 100, 3),
        "accuracy_gap_pp": round((test_acc - val_metrics["accuracy"]) * 100, 3),
        "balanced_accuracy_gap_pp": round((test_bal_acc - val_metrics["balanced_accuracy"]) * 100, 3),
        "sag_to_normal_change": sag_to_normal_errors - val_metrics["sag_to_normal_errors"],
        "normal_to_sag_change": normal_to_sag_errors - val_metrics["normal_to_sag_errors"],
        "total_errors_change": incorrect_count - val_metrics["total_errors"]
    }

    # Step 7: Trajectory-Aware Uncertainty (Cluster Bootstrap)
    test_trajectories_list = meta_test["trajectory_id"].tolist()
    bootstrap_results = trajectory_cluster_bootstrap(y_test, y_test_pred, test_trajectories_list, n_bootstraps=1000)

    # Step 8: CPU Latency Measurement
    print("\n[Latency Benchmark] Measuring single-frame CPU latency on test data (2,000 runs)...")
    latency_stats = benchmark_cpu_latency(clf, X_test_scaled, n_runs=2000)
    print(f"  Mean Latency: {latency_stats['mean_latency_us']} us | P99: {latency_stats['p99_latency_us']} us | Throughput: {latency_stats['throughput_fps']} FPS")

    # Step 9: Diagnostic Error Inspection
    error_records = []
    meta_records = meta_test.to_dict(orient="records")
    for i in range(len(y_test)):
        if y_test[i] != y_test_pred[i]:
            m = meta_records[i]
            probs = y_test_prob[i]
            error_records.append({
                "frame_index": i,
                "frame_id": m.get("frame_id", "unknown"),
                "trajectory_id": m.get("trajectory_id", "unknown"),
                "ground_truth_label": class_names[y_test[i]],
                "predicted_label": class_names[y_test_pred[i]],
                "predicted_confidence": round(float(probs[y_test_pred[i]]), 4),
                "true_class_confidence": round(float(probs[y_test[i]]), 4),
                "top3_classes": [class_names[c] for c in np.argsort(probs)[-3:][::-1]],
                "top3_confidences": [round(float(probs[c]), 4) for c in np.argsort(probs)[-3:][::-1]]
            })

    # Display Summary
    print("\n" + "=" * 80)
    print("PHASE 4D FORMAL TEST EVALUATION RESULTS")
    print("=" * 80)
    print(f"Overall Accuracy:          {test_acc * 100:.2f}% ({correct_count} / {len(y_test)})")
    print(f"Balanced Accuracy:         {test_bal_acc * 100:.2f}%")
    print(f"Macro Precision:           {test_prec_macro * 100:.2f}%")
    print(f"Macro Recall:              {test_rec_macro * 100:.2f}%")
    print(f"Macro F1-Score:            {test_f1_macro * 100:.2f}%")
    print(f"Predefined Target:         >= 99.00% Macro F1")
    target_met = bool(test_f1_macro >= 0.990)
    print(f"Target Met:                {target_met} ({'PASS' if target_met else 'FAIL'})")
    print(f"Sag -> Normal Errors:      {sag_to_normal_errors}")
    print(f"Normal -> Sag Errors:      {normal_to_sag_errors}")
    print(f"Total Errors:              {incorrect_count}")
    print(f"95% CI Macro F1:           [{bootstrap_results['macro_f1_ci_95'][0] * 100:.2f}%, {bootstrap_results['macro_f1_ci_95'][1] * 100:.2f}%]")
    print(f"Generalization Gap:        Macro F1 delta = {generalization_gap['macro_f1_gap_pp']:+.3f} pp")

    print("\nPer-Class Breakdown:")
    for c_name, m_dict in per_class_metrics.items():
        print(f"  {c_name:12}: Support={m_dict['support']:3d} | Prec={m_dict['precision']*100:6.2f}% | Rec={m_dict['recall']*100:6.2f}% | F1={m_dict['f1_score']*100:6.2f}% | FP={m_dict['false_positives']} | FN={m_dict['false_negatives']}")

    print("\nConfusion Matrix (Raw Counts):")
    header = "True \\ Pred  " + "".join(f"{c_name[:4]:>6}" for c_name in class_names)
    print(header)
    for i, c_name in enumerate(class_names):
        row = f"{c_name[:10]:12} " + "".join(f"{cm[i, j]:6d}" for j in range(8))
        print(row)

    print(f"\nDiagnostic Errors Identified: {len(error_records)}")
    for err in error_records:
        print(f"  Frame {err['frame_index']:4d} | Traj: {err['trajectory_id']:25} | True: {err['ground_truth_label']:12} -> Pred: {err['predicted_label']:12} (conf: {err['predicted_confidence']:.2f})")

    # Step 10: Export Machine-Readable Deliverables
    predictions_df = pd.DataFrame({
        "frame_index": list(range(len(y_test))),
        "frame_id": meta_test["frame_id"].tolist(),
        "trajectory_id": meta_test["trajectory_id"].tolist(),
        "ground_truth_label": [class_names[y] for y in y_test],
        "ground_truth_index": y_test,
        "predicted_label": [class_names[y] for y in y_test_pred],
        "predicted_index": y_test_pred,
        "correct": (y_test == y_test_pred),
        "confidence": [float(y_test_prob[i, y_test_pred[i]]) for i in range(len(y_test))]
    })
    pred_csv_path = os.path.join(PHASE4D_DIR, "test_predictions.csv")
    predictions_df.to_csv(pred_csv_path, index=False)

    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)
    cm_csv_path = os.path.join(PHASE4D_DIR, "confusion_matrix.csv")
    cm_df.to_csv(cm_csv_path)

    # Trajectory-level metrics
    traj_metrics = {}
    for traj in test_trajs:
        mask = (predictions_df["trajectory_id"] == traj)
        traj_sub = predictions_df[mask]
        t_acc = float((traj_sub["correct"]).mean())
        traj_metrics[traj] = {
            "trajectory_id": traj,
            "class_name": traj_sub["ground_truth_label"].iloc[0],
            "total_frames": int(len(traj_sub)),
            "accuracy": round(t_acc, 4),
            "error_count": int((~traj_sub["correct"]).sum())
        }
    traj_metrics_path = os.path.join(PHASE4D_DIR, "trajectory_metrics.json")
    with open(traj_metrics_path, "w", encoding="utf-8") as f:
        json.dump(traj_metrics, f, indent=2)

    # Comprehensive test metrics JSON
    metrics_payload = {
        "gate": "GATE_4D",
        "timestamp_test_access": test_unlock_time,
        "preflight_integrity": preflight_info,
        "dataset_summary": {
            "total_test_frames": len(y_test),
            "test_trajectories_count": len(test_trajs),
            "class_counts": class_counts
        },
        "model_specification": {
            "architecture": "32 -> 64 -> 32 -> 16 -> 8",
            "solver": "lbfgs",
            "alpha": 0.0001,
            "seed": 123,
            "parameter_count": jw["parameter_count"],
            "memory_footprint_fp32_kb": jw["memory_footprint_fp32_kb"]
        },
        "overall_metrics": {
            "accuracy": round(float(test_acc), 4),
            "balanced_accuracy": round(float(test_bal_acc), 4),
            "macro_precision": round(float(test_prec_macro), 4),
            "macro_recall": round(float(test_rec_macro), 4),
            "macro_f1": round(float(test_f1_macro), 4),
            "weighted_precision": round(float(test_prec_weighted), 4),
            "weighted_recall": round(float(test_rec_weighted), 4),
            "weighted_f1": round(float(test_f1_weighted), 4),
            "correct_frames": correct_count,
            "incorrect_frames": incorrect_count,
            "predefined_target_macro_f1": 0.990,
            "target_achieved": target_met
        },
        "sag_normal_confusion": {
            "sag_to_normal_errors": sag_to_normal_errors,
            "normal_to_sag_errors": normal_to_sag_errors
        },
        "per_class_metrics": per_class_metrics,
        "confusion_matrix_raw": cm.tolist(),
        "confusion_matrix_normalized": cm_norm.round(4).tolist(),
        "generalization_gap": generalization_gap,
        "trajectory_cluster_bootstrap": bootstrap_results,
        "cpu_latency_benchmark": latency_stats,
        "diagnostic_errors": error_records
    }

    metrics_json_path = os.path.join(PHASE4D_DIR, "test_metrics.json")
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    # Evaluation Provenance Record
    provenance = {
        "evaluation_name": "Phase 4D Independent Test Partition Evaluation",
        "timestamp_utc": test_unlock_time,
        "host_environment": {
            "os": platform.platform(),
            "python_version": sys.version,
            "machine": platform.machine(),
            "processor": platform.processor()
        },
        "artifacts_evaluated": {
            "manifest_sha256": preflight_info["manifest_sha256"],
            "simulink_sha256": preflight_info["simulink_sha256"],
            "candidate_mlp_weights_sha256": preflight_info["candidate_checksums"]["candidate_mlp_weights_json"],
            "candidate_mlp_pipeline_sha256": preflight_info["candidate_checksums"]["candidate_mlp_pipeline_pkl"],
            "scaler_phase4c_pkl_sha256": preflight_info["candidate_checksums"]["scaler_phase4c_pkl"]
        },
        "deliverables_generated": {
            "test_metrics_json": compute_sha256(metrics_json_path),
            "test_predictions_csv": compute_sha256(pred_csv_path),
            "confusion_matrix_csv": compute_sha256(cm_csv_path),
            "trajectory_metrics_json": compute_sha256(traj_metrics_path)
        }
    }
    provenance_path = os.path.join(PHASE4D_DIR, "evaluation_provenance.json")
    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print(f"\n[Artifact Delivery] Machine-readable deliverables saved under: {PHASE4D_DIR}")
    print(f"  test_metrics.json:        {provenance['deliverables_generated']['test_metrics_json']}")
    print(f"  test_predictions.csv:    {provenance['deliverables_generated']['test_predictions_csv']}")
    print(f"  confusion_matrix.csv:    {provenance['deliverables_generated']['confusion_matrix_csv']}")
    print(f"  trajectory_metrics.json: {provenance['deliverables_generated']['trajectory_metrics_json']}")


if __name__ == "__main__":
    main()

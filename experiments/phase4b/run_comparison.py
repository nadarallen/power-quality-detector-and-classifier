"""
experiments/phase4b/run_comparison.py
-------------------------------------
Phase 4B: Leakage-Safe Baseline Model Comparison on Frozen 60-Hz IEEE 9-bus PQD Dataset.

Compares 5 baseline classifiers:
1. Logistic Regression (L2, L-BFGS, scaled)
2. Random Forest (100 trees, unscaled)
3. Support Vector Machine (RBF kernel, C=10.0, scaled)
4. Gradient Boosting (100 estimators, depth=4, unscaled)
5. Multilayer Perceptron (32 -> 64 -> 32 -> 8, ReLU, Adam, scaled)

Preconditions:
- Phase 4A dataset freeze verified via scripts/verify_dataset_freeze.py.
- Training partition: exactly 6,594 frames across 204 continuous trajectories.
- Validation partition: exactly 1,295 frames across 40 continuous trajectories.
- Scaler fitted STRICTLY on training partition.
- Locked test set (1,295 frames) STRICTLY PRESERVED & UNUSED.
"""

import os
import sys
import time
import json
import pickle
import hashlib
import numpy as np
import pandas as pd
from typing import Dict, Any

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.dataset_loader import load_ieee9bus_data, load_manifest

EXPERIMENT_DIR = os.path.join(PROJECT_ROOT, "experiments", "phase4b")
MODELS_DIR = os.path.join(EXPERIMENT_DIR, "models")
METRICS_DIR = os.path.join(EXPERIMENT_DIR, "metrics")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def benchmark_cpu_latency(pipeline: Pipeline, X_sample: np.ndarray, n_runs: int = 1000) -> Dict[str, float]:
    """
    Measures CPU single-frame inference latency using high-resolution performance counters.
    Warm-up: 100 runs.
    Benchmark: n_runs single-frame predictions.
    """
    n_samples = len(X_sample)
    
    # Warm-up phase
    for i in range(100):
        idx = i % n_samples
        _ = pipeline.predict(X_sample[idx:idx+1])
        
    latencies_us = []
    for i in range(n_runs):
        idx = (i + 100) % n_samples
        frame = X_sample[idx:idx+1]
        t0 = time.perf_counter_ns()
        _ = pipeline.predict(frame)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0) # convert ns to us
        
    latencies = np.array(latencies_us)
    return {
        "mean_latency_us": round(float(np.mean(latencies)), 2),
        "median_latency_us": round(float(np.median(latencies)), 2),
        "p95_latency_us": round(float(np.percentile(latencies, 95)), 2),
        "p99_latency_us": round(float(np.percentile(latencies, 99)), 2),
        "std_latency_us": round(float(np.std(latencies)), 2),
        "throughput_fps": round(float(1e6 / np.mean(latencies)), 1)
    }


def get_model_complexity(model: Any, model_name: str) -> Dict[str, Any]:
    """
    Analyzes model parameter count and architectural complexity.
    """
    estimator = model.named_steps.get("classifier", model)
    complexity = {"type": type(estimator).__name__}
    
    if isinstance(estimator, LogisticRegression):
        # weights: (n_classes, n_features), biases: (n_classes,)
        n_params = estimator.coef_.size + estimator.intercept_.size
        complexity["parameter_count"] = int(n_params)
        complexity["notes"] = f"Linear weights ({estimator.coef_.shape}) + biases ({estimator.intercept_.shape})"
    elif isinstance(estimator, RandomForestClassifier):
        total_nodes = sum(tree.tree_.node_count for tree in estimator.estimators_)
        complexity["n_trees"] = len(estimator.estimators_)
        complexity["total_tree_nodes"] = int(total_nodes)
        complexity["parameter_count"] = int(total_nodes * 3) # threshold, feature, children
        complexity["notes"] = f"{len(estimator.estimators_)} decision trees, total {total_nodes} nodes"
    elif isinstance(estimator, GradientBoostingClassifier):
        total_nodes = 0
        for stage in estimator.estimators_:
            for tree in (stage if hasattr(stage, '__iter__') else [stage]):
                total_nodes += tree.tree_.node_count
        complexity["n_estimators"] = len(estimator.estimators_)
        complexity["total_tree_nodes"] = int(total_nodes)
        complexity["parameter_count"] = int(total_nodes * 3)
        complexity["notes"] = f"{len(estimator.estimators_)} stages x {estimator.n_classes_} classes trees"
    elif isinstance(estimator, SVC):
        n_sv = estimator.support_vectors_.shape[0]
        n_features = estimator.support_vectors_.shape[1]
        complexity["support_vectors_count"] = int(n_sv)
        complexity["parameter_count"] = int(n_sv * n_features + estimator.dual_coef_.size)
        complexity["notes"] = f"{n_sv} support vectors x {n_features} features"
    elif isinstance(estimator, MLPClassifier):
        total_weights = sum(w.size for w in estimator.coefs_)
        total_biases = sum(b.size for b in estimator.intercepts_)
        complexity["parameter_count"] = int(total_weights + total_biases)
        complexity["architecture"] = [w.shape[0] for w in estimator.coefs_] + [estimator.coefs_[-1].shape[1]]
        complexity["layer_shapes"] = [f"{w.shape}" for w in estimator.coefs_]
        complexity["notes"] = f"MLP: 32 -> 64 -> 32 -> 8 ({total_weights + total_biases} parameters)"
    else:
        complexity["parameter_count"] = None
        complexity["notes"] = "Unknown estimator"
        
    return complexity


def run_experiment():
    print("=" * 80)
    print("PHASE 4B — LEAKAGE-SAFE BASELINE MODEL COMPARISON")
    print("=" * 80)
    
    # 1. Verify Dataset Freeze Precondition
    manifest_path = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", "dataset_manifest_v1.json")
    manifest, manifest_sha256 = load_manifest(manifest_path)
    print(f"[Precondition] Authoritative manifest loaded: {manifest_path}")
    print(f"[Precondition] Manifest SHA-256: {manifest_sha256}")
    
    # 2. Load Partitions (Strictly Train & Val; Test is Locked)
    print("\n[Data Loader] Loading Train (6,594) and Validation (1,295) partitions...")
    data = load_ieee9bus_data(manifest_path=manifest_path, verify_checksums=True, include_test=False)
    
    X_train, y_train, meta_train = data["train"]
    X_val, y_val, meta_val = data["val"]
    
    target_classes = manifest["preprocessing_contract"]["target_classes"]
    class_to_index = manifest["preprocessing_contract"]["class_to_index"]
    index_to_class = {v: k for k, v in class_to_index.items()}
    class_names = [index_to_class[i] for i in range(len(target_classes))]
    
    print(f"  Training set   : X shape = {X_train.shape}, y shape = {y_train.shape}")
    print(f"  Validation set : X shape = {X_val.shape}, y shape = {y_val.shape}")
    print(f"  Target classes : {class_names}")
    
    # Verify zero leakage
    tr_trajs = set(meta_train["trajectory_id"].unique())
    val_trajs = set(meta_val["trajectory_id"].unique())
    leakage = tr_trajs.intersection(val_trajs)
    if leakage:
        raise ValueError(f"FATAL: Trajectory leakage detected between Train and Val: {leakage}")
    print(f"  Trajectory Disjointness: PASS (Train: {len(tr_trajs)} trajectories, Val: {len(val_trajs)} trajectories, Overlap: 0)")

    # 3. Fit and Export Standalone StandardScaler (fitted strictly on training set)
    scaler = StandardScaler()
    scaler.fit(X_train)
    scaler_path = os.path.join(MODELS_DIR, "scaler_phase4b.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
        
    scaler_params = {
        "feature_order": manifest["feature_contract"]["ordering"],
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "var": scaler.var_.tolist(),
        "n_samples_seen": int(scaler.n_samples_seen_)
    }
    with open(os.path.join(MODELS_DIR, "scaler_phase4b_params.json"), "w", encoding="utf-8") as f:
        json.dump(scaler_params, f, indent=2)
    print(f"\n[Preprocessing] Fitted StandardScaler saved to {scaler_path} (n_samples={scaler.n_samples_seen_})")

    # 4. Define Candidate Models
    models_config = {
        "logistic_regression": {
            "display_name": "Logistic Regression",
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(
                    C=1.0,
                    max_iter=1000,
                    solver="lbfgs",
                    random_state=SEED
                ))
            ]),
            "hyperparameters": {
                "C": 1.0,
                "max_iter": 1000,
                "solver": "lbfgs",
                "penalty": "l2",
                "random_state": SEED
            }
        },
        "random_forest": {
            "display_name": "Random Forest",
            "pipeline": Pipeline([
                ("classifier", RandomForestClassifier(
                    n_estimators=100,
                    max_depth=16,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    max_features="sqrt",
                    random_state=SEED,
                    n_jobs=-1
                ))
            ]),
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 16,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "max_features": "sqrt",
                "random_state": SEED
            }
        },
        "svm_rbf": {
            "display_name": "Support Vector Machine (RBF)",
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", SVC(
                    C=10.0,
                    kernel="rbf",
                    gamma="scale",
                    random_state=SEED
                ))
            ]),
            "hyperparameters": {
                "C": 10.0,
                "kernel": "rbf",
                "gamma": "scale",
                "random_state": SEED
            }
        },
        "gradient_boosting": {
            "display_name": "Gradient Boosting",
            "pipeline": Pipeline([
                ("classifier", GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=4,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    random_state=SEED
                ))
            ]),
            "hyperparameters": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 4,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "random_state": SEED
            }
        },
        "mlp_compact": {
            "display_name": "Compact MLP (32->64->32->8)",
            "pipeline": Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", MLPClassifier(
                    hidden_layer_sizes=(64, 32),
                    activation="relu",
                    solver="adam",
                    alpha=1e-4,
                    batch_size=32,
                    learning_rate_init=1e-3,
                    max_iter=500,
                    early_stopping=True,
                    n_iter_no_change=25,
                    validation_fraction=0.1,
                    random_state=SEED
                ))
            ]),
            "hyperparameters": {
                "architecture": "32 -> 64 -> 32 -> 8",
                "hidden_layer_sizes": [64, 32],
                "activation": "relu",
                "solver": "adam",
                "alpha": 1e-4,
                "batch_size": 32,
                "learning_rate_init": 1e-3,
                "max_iter": 500,
                "early_stopping": True,
                "random_state": SEED
            }
        }
    }

    # 5. Execute Training and Evaluation Loop
    results = {}
    summary_rows = []

    print("\n" + "=" * 80)
    print("TRAINING & BENCHMARKING BASELINE MODELS")
    print("=" * 80)

    for model_key, cfg in models_config.items():
        name = cfg["display_name"]
        pipeline = cfg["pipeline"]
        print(f"\n--- Model: {name} ({model_key}) ---")

        # Training
        t_start = time.perf_counter()
        pipeline.fit(X_train, y_train)
        t_train_sec = time.perf_counter() - t_start
        print(f"  Training finished in {t_train_sec:.2f} s")

        # Predictions
        y_train_pred = pipeline.predict(X_train)
        y_val_pred = pipeline.predict(X_val)

        # Metrics on Train
        tr_acc = accuracy_score(y_train, y_train_pred)
        tr_macro_f1 = f1_score(y_train, y_train_pred, average="macro")
        tr_weighted_f1 = f1_score(y_train, y_train_pred, average="weighted")

        # Metrics on Val
        val_acc = accuracy_score(y_val, y_val_pred)
        val_macro_f1 = f1_score(y_val, y_val_pred, average="macro")
        val_weighted_f1 = f1_score(y_val, y_val_pred, average="weighted")
        val_precision = precision_score(y_val, y_val_pred, average="macro")
        val_recall = recall_score(y_val, y_val_pred, average="macro")

        print(f"  Train  : Acc={tr_acc*100:.2f}%, Macro F1={tr_macro_f1*100:.2f}%")
        print(f"  Val    : Acc={val_acc*100:.2f}%, Macro F1={val_macro_f1*100:.2f}%, Weighted F1={val_weighted_f1*100:.2f}%")

        # Per-Class Metrics on Val
        report_dict = classification_report(
            y_val, y_val_pred,
            target_names=class_names,
            output_dict=True,
            digits=4
        )
        cm = confusion_matrix(y_val, y_val_pred)

        # Per-class weaknesses identification (recall or precision < 95%)
        weaknesses = []
        for c_idx, c_name in enumerate(class_names):
            c_rec = report_dict[c_name]["recall"]
            c_prec = report_dict[c_name]["precision"]
            if c_rec < 0.95 or c_prec < 0.95:
                weaknesses.append({
                    "class": c_name,
                    "recall": round(float(c_rec), 4),
                    "precision": round(float(c_prec), 4),
                    "f1": round(float(report_dict[c_name]["f1-score"]), 4)
                })

        # Latency Benchmark
        print("  Running CPU inference latency benchmark (1,000 runs)...")
        latency_stats = benchmark_cpu_latency(pipeline, X_val, n_runs=1000)
        print(f"  Latency: Mean={latency_stats['mean_latency_us']} us, Median={latency_stats['median_latency_us']} us, Throughput={latency_stats['throughput_fps']} FPS")

        # Complexity & Model Size
        complexity = get_model_complexity(pipeline, model_key)
        model_file = os.path.join(MODELS_DIR, f"{model_key}.pkl")
        with open(model_file, "wb") as f:
            pickle.dump(pipeline, f)
        model_size_kb = round(os.path.getsize(model_file) / 1024.0, 2)
        complexity["model_file_size_kb"] = model_size_kb
        complexity["model_file"] = f"experiments/phase4b/models/{model_key}.pkl"
        print(f"  Model Size: {model_size_kb} KB, Parameters: {complexity.get('parameter_count')}")

        # Save Per-Model Artifacts
        model_results = {
            "model_key": model_key,
            "display_name": name,
            "experiment": "PHASE_4B",
            "seed": SEED,
            "manifest_sha256": manifest_sha256,
            "training_time_seconds": round(t_train_sec, 3),
            "hyperparameters": cfg["hyperparameters"],
            "complexity": complexity,
            "latency": latency_stats,
            "train_metrics": {
                "accuracy": round(float(tr_acc), 4),
                "macro_f1": round(float(tr_macro_f1), 4),
                "weighted_f1": round(float(tr_weighted_f1), 4)
            },
            "validation_metrics": {
                "accuracy": round(float(val_acc), 4),
                "macro_f1": round(float(val_macro_f1), 4),
                "weighted_f1": round(float(val_weighted_f1), 4),
                "macro_precision": round(float(val_precision), 4),
                "macro_recall": round(float(val_recall), 4)
            },
            "per_class_report": report_dict,
            "confusion_matrix": cm.tolist(),
            "confusion_matrix_classes": class_names,
            "weaknesses": weaknesses
        }

        # Save to JSON
        metrics_file = os.path.join(METRICS_DIR, f"{model_key}_metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(model_results, f, indent=2)

        results[model_key] = model_results

        # Summary Row
        summary_rows.append({
            "Model": name,
            "Train Acc (%)": round(tr_acc * 100, 2),
            "Val Acc (%)": round(val_acc * 100, 2),
            "Val Macro F1 (%)": round(val_macro_f1 * 100, 2),
            "Val Weighted F1 (%)": round(val_weighted_f1 * 100, 2),
            "Train Time (s)": round(t_train_sec, 2),
            "Latency Mean (us)": latency_stats["mean_latency_us"],
            "Latency Median (us)": latency_stats["median_latency_us"],
            "Model Size (KB)": model_size_kb,
            "Parameters": complexity.get("parameter_count"),
            "Weak Classes (<95% F1)": len(weaknesses)
        })

    # 6. Save Overall Experiment Summary
    summary_df = pd.DataFrame(summary_rows)
    summary_csv_path = os.path.join(EXPERIMENT_DIR, "baseline_comparison_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)

    summary_json_path = os.path.join(EXPERIMENT_DIR, "baseline_comparison_summary.json")
    summary_payload = {
        "experiment_name": "PHASE_4B_BASELINE_MODEL_COMPARISON",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_sha256": manifest_sha256,
        "seed": SEED,
        "partitions": {
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "locked_test_samples_preserved": manifest["dataset_totals"]["test_frames"]
        },
        "models_summary": summary_rows,
        "detailed_results": results
    }
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    # Save Experiment Config
    config_path = os.path.join(EXPERIMENT_DIR, "experiment_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": "PHASE_4B",
            "seed": SEED,
            "dataset_manifest": "data/ieee9bus_60hz/dataset_manifest_v1.json",
            "dataset_manifest_sha256": manifest_sha256,
            "feature_count": 32,
            "classes": class_names,
            "models_evaluated": list(models_config.keys())
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 4B BASELINE COMPARISON SUMMARY:")
    print("=" * 80)
    print(summary_df.to_string(index=False))
    print("\nArtifacts saved to experiments/phase4b/")
    return summary_payload


if __name__ == "__main__":
    run_experiment()

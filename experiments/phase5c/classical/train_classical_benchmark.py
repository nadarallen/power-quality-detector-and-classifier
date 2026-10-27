"""
experiments/phase5c/classical/train_classical_benchmark.py
----------------------------------------------------------
Rigorous Classical ML benchmark, constant feature verification, feature group ablation,
and SHAP / permutation interpretability for Phase 5C on the IEEE 9-bus WSCC benchmark.

Contract:
- Canonical 32-feature vector
- Fitted strictly on Train split (80 trajectories, 2,560 frames)
- Evaluated strictly on Validation split (32 trajectories, 1,024 frames)
- Challenge split is 100% quarantined (NOT accessed in this script)
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report
)
from sklearn.inspection import permutation_importance
import shap

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_NPZ = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'processed', 'phase5c_features.npz')
OUT_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'classical')
os.makedirs(OUT_DIR, exist_ok=True)

CLASS_NAMES = ["Flicker", "Harmonics", "Interruption", "Normal", "Notch", "Sag", "Swell", "Transient"]

FEATURE_GROUPS = {
    "Amplitude & Shape": ["rms_voltage", "peak_voltage", "crest_factor", "duration"],
    "Harmonics & Ratios": [
        "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10", "h11",
        "h2_ratio", "h3_ratio", "h4_ratio", "h5_ratio", "h7_ratio", "h9_ratio", "h11_ratio",
        "harmonic_energy"
    ],
    "Spectral Characteristics": [
        "spectral_centroid", "spectral_bandwidth", "spectral_entropy", "spectral_flatness"
    ],
    "Frequency Characteristics": [
        "dominant_freq", "system_freq", "true_dominant_freq"
    ],
    "Signal Quality": [
        "thd", "snr"
    ]
}


def run_classical_benchmark():
    print("=" * 80)
    print("PHASE 5C TRACK A: CLASSICAL MACHINE LEARNING BENCHMARK")
    print("=" * 80)

    if not os.path.exists(DATA_NPZ):
        raise FileNotFoundError(f"Feature dataset not found at {DATA_NPZ}. Run dataset processor first!")

    data = np.load(DATA_NPZ, allow_pickle=True)
    features = data['features']          # [4608, 32]
    labels = data['labels']              # [4608]
    splits = data['splits']              # [4608]
    feature_names = list(data['feature_names'])
    traj_ids = data['trajectory_ids']

    # Strict partition isolation
    train_mask = (splits == 'train')
    val_mask = (splits == 'val')
    challenge_mask = (splits == 'challenge')

    print(f"Loaded dataset: {len(labels)} total frames across {len(np.unique(traj_ids))} trajectories.")
    print(f"  - Train partition:     {np.sum(train_mask)} frames ({len(np.unique(traj_ids[train_mask]))} trajectories)")
    print(f"  - Val partition:       {np.sum(val_mask)} frames ({len(np.unique(traj_ids[val_mask]))} trajectories)")
    print(f"  - Challenge partition: {np.sum(challenge_mask)} frames (QUARANTINED - NOT TOUCHED)")

    X_train = features[train_mask]
    y_train = labels[train_mask]
    X_val = features[val_mask]
    y_val = labels[val_mask]

    # Verify constant features
    print("\n--- Auditing Constant Features ---")
    stds = np.std(X_train, axis=0)
    constant_features = []
    for i, name in enumerate(feature_names):
        u_vals = np.unique(X_train[:, i])
        is_const = (len(u_vals) <= 1 or stds[i] < 1e-9)
        if is_const:
            constant_features.append(name)
            print(f"  [CONSTANT] {name}: std={stds[i]:.2e}, unique values={u_vals[:3]}")
        else:
            print(f"  [VARYING]  {name:22s}: std={stds[i]:.4f}, min={np.min(X_train[:, i]):.4f}, max={np.max(X_train[:, i]):.4f}")

    print(f"Total features: {len(feature_names)} | Constant: {len(constant_features)} | Effective Varying: {len(feature_names) - len(constant_features)}")

    # Standard Scaler fitted ONLY on Train split
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    joblib.dump(scaler, os.path.join(OUT_DIR, 'phase5c_classical_scaler.joblib'))

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "RBF SVM": SVC(C=10.0, kernel='rbf', probability=True, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Extra Trees": ExtraTreesClassifier(n_estimators=100, random_state=42),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=100, random_state=42),
        "MLP": MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42)
    }

    benchmark_results = {}
    trained_models = {}

    print("\n--- Training and Evaluating Classical ML Models ---")
    for name, clf in models.items():
        print(f"\nTraining {name}...")
        # Tree models can use unscaled or scaled; using scaled for uniform pipeline
        clf.fit(X_train_scaled, y_train)
        y_pred = clf.predict(X_val_scaled)

        acc = accuracy_score(y_val, y_pred)
        bal_acc = balanced_accuracy_score(y_val, y_pred)
        macro_f1 = f1_score(y_val, y_pred, average='macro')
        macro_prec = precision_score(y_val, y_pred, average='macro', zero_division=0)
        macro_rec = recall_score(y_val, y_pred, average='macro', zero_division=0)
        cm = confusion_matrix(y_val, y_pred).tolist()

        # Per-class metrics
        per_class_f1 = f1_score(y_val, y_pred, average=None, zero_division=0).tolist()
        per_class_prec = precision_score(y_val, y_pred, average=None, zero_division=0).tolist()
        per_class_rec = recall_score(y_val, y_pred, average=None, zero_division=0).tolist()

        per_class_stats = {}
        for c_idx, c_name in enumerate(CLASS_NAMES):
            per_class_stats[c_name] = {
                'f1': per_class_f1[c_idx],
                'precision': per_class_prec[c_idx],
                'recall': per_class_rec[c_idx]
            }

        print(f"  -> Accuracy: {acc*100:.2f}% | Balanced Acc: {bal_acc*100:.2f}% | Macro F1: {macro_f1*100:.2f}%")

        benchmark_results[name] = {
            'accuracy': float(acc),
            'balanced_accuracy': float(bal_acc),
            'macro_f1': float(macro_f1),
            'macro_precision': float(macro_prec),
            'macro_recall': float(macro_rec),
            'confusion_matrix': cm,
            'per_class': per_class_stats
        }

        trained_models[name] = clf
        joblib.dump(clf, os.path.join(OUT_DIR, f"model_{name.lower().replace(' ', '_')}.joblib"))

    # Identify Best Model on Validation Macro F1
    best_model_name = max(benchmark_results.keys(), key=lambda k: benchmark_results[k]['macro_f1'])
    best_clf = trained_models[best_model_name]
    print(f"\n[Selection] Best Classical Model on Validation: {best_model_name} (Macro F1: {benchmark_results[best_model_name]['macro_f1']*100:.2f}%)")

    # Save benchmark metrics
    metrics_path = os.path.join(OUT_DIR, 'classical_benchmark_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump({
            'best_model': best_model_name,
            'models': benchmark_results,
            'constant_features': constant_features
        }, f, indent=2)

    # --- Feature Group Ablation ---
    print("\n--- Performing Controlled Feature Group Ablation ---")
    ablation_results = {}
    baseline_val_f1 = benchmark_results[best_model_name]['macro_f1']

    for grp_name, grp_features in FEATURE_GROUPS.items():
        remain_indices = [i for i, f in enumerate(feature_names) if f not in grp_features]
        print(f"\nAblating '{grp_name}' ({len(grp_features)} features removed, {len(remain_indices)} remaining)...")

        X_tr_abl = X_train[:, remain_indices]
        X_va_abl = X_val[:, remain_indices]

        sc_abl = StandardScaler()
        X_tr_abl_sc = sc_abl.fit_transform(X_tr_abl)
        X_va_abl_sc = sc_abl.transform(X_va_abl)

        # Retrain identical architecture of best model
        if best_model_name == "Extra Trees":
            clf_abl = ExtraTreesClassifier(n_estimators=100, random_state=42)
        elif best_model_name == "Random Forest":
            clf_abl = RandomForestClassifier(n_estimators=100, random_state=42)
        elif best_model_name == "HistGradientBoosting":
            clf_abl = HistGradientBoostingClassifier(max_iter=100, random_state=42)
        else:
            clf_abl = SVC(C=10.0, kernel='rbf', probability=True, random_state=42)

        clf_abl.fit(X_tr_abl_sc, y_train)
        y_abl_pred = clf_abl.predict(X_va_abl_sc)

        abl_acc = accuracy_score(y_val, y_abl_pred)
        abl_f1 = f1_score(y_val, y_abl_pred, average='macro')
        delta_f1 = abl_f1 - baseline_val_f1

        print(f"  -> Ablated Val Acc: {abl_acc*100:.2f}% | Val Macro F1: {abl_f1*100:.2f}% | Delta F1: {delta_f1*100:+.2f}%")

        ablation_results[grp_name] = {
            'ablated_features': grp_features,
            'remaining_features_count': len(remain_indices),
            'val_accuracy': float(abl_acc),
            'val_macro_f1': float(abl_f1),
            'delta_macro_f1': float(delta_f1)
        }

    with open(os.path.join(OUT_DIR, 'feature_ablation_results.json'), 'w', encoding='utf-8') as f:
        json.dump(ablation_results, f, indent=2)

    # --- Permutation Feature Importance ---
    print("\n--- Computing Permutation Feature Importance ---")
    perm_res = permutation_importance(
        best_clf, X_val_scaled, y_val, n_repeats=10, random_state=42, scoring='f1_macro', n_jobs=-1
    )
    perm_importances = {}
    for i, name in enumerate(feature_names):
        perm_importances[name] = {
            'mean_importance': float(perm_res.importances_mean[i]),
            'std_importance': float(perm_res.importances_std[i])
        }

    sorted_perm = sorted(perm_importances.items(), key=lambda kv: kv[1]['mean_importance'], reverse=True)
    print("Top 10 Features by Permutation Importance:")
    for rank, (name, val) in enumerate(sorted_perm[:10], 1):
        print(f"  {rank:2d}. {name:22s}: {val['mean_importance']:+.4f} (+/- {val['std_importance']:.4f})")

    with open(os.path.join(OUT_DIR, 'permutation_importance.json'), 'w', encoding='utf-8') as f:
        json.dump(perm_importances, f, indent=2)

    # --- SHAP Explainer (Tree or Kernel) ---
    print("\n--- Computing SHAP Values on Validation Set ---")
    shap_summary = {}
    try:
        if isinstance(best_clf, (RandomForestClassifier, ExtraTreesClassifier)):
            # TreeExplainer is exact and fast
            explainer = shap.TreeExplainer(best_clf)
            # Use 200 validation samples for tractable explanation summary
            sub_val = X_val_scaled[:200]
            shap_values = explainer.shap_values(sub_val)

            # For multi-class, shap_values is a list of [n_samples, n_features] per class
            # or an array [n_samples, n_features, n_classes]
            if isinstance(shap_values, list):
                shap_by_class = {}
                for c_idx, c_name in enumerate(CLASS_NAMES):
                    mean_abs = np.mean(np.abs(shap_values[c_idx]), axis=0)
                    top_feats = {feature_names[i]: float(mean_abs[i]) for i in np.argsort(-mean_abs)[:5]}
                    shap_by_class[c_name] = top_feats
            elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
                shap_by_class = {}
                for c_idx, c_name in enumerate(CLASS_NAMES):
                    mean_abs = np.mean(np.abs(shap_values[:, :, c_idx]), axis=0)
                    top_feats = {feature_names[i]: float(mean_abs[i]) for i in np.argsort(-mean_abs)[:5]}
                    shap_by_class[c_name] = top_feats
            else:
                shap_by_class = {}

            shap_summary = {
                'explainer_type': 'TreeExplainer',
                'samples_evaluated': 200,
                'per_class_top_features': shap_by_class
            }
            print("Successfully computed TreeExplainer SHAP summaries for all 8 classes.")
    except Exception as e:
        print(f"[Warning] SHAP calculation encountered exception: {e}")
        shap_summary = {'explainer_type': 'Failed', 'error': str(e)}

    with open(os.path.join(OUT_DIR, 'shap_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(shap_summary, f, indent=2)

    print("\n" + "=" * 80)
    print("TRACK A CLASSICAL ML & FEATURE ANALYSIS COMPLETE")
    print(f"Artifacts saved to: {OUT_DIR}")
    print("=" * 80)


if __name__ == '__main__':
    run_classical_benchmark()

"""
Research Dashboard Backend Utilities
------------------------------------
Provides robust helpers for:
- Loading recorded IEEE 9-bus 60 Hz waveforms from committed NPZ archives.
- Extracting the canonical 32-feature vector for Phase A/B/C.
- Running inference using the frozen Phase 4C candidate MLP model.
- Providing feature explainability metrics and comparison benchmarks.
"""

import os
import json
import pickle
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

from dsp.enhanced_features import extract_enhanced_features

CLASSES = [
    "Flicker",
    "Harmonics",
    "Interruption",
    "Normal",
    "Notch",
    "Sag",
    "Swell",
    "Transient"
]

CANONICAL_32_FEATURES = [
    "rms_voltage", "peak_voltage", "crest_factor", "thd",
    "duration", "dominant_freq", "system_freq", "snr",
    "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10", "h11",
    "h2_ratio", "h3_ratio", "h4_ratio", "h5_ratio", "h7_ratio", "h9_ratio", "h11_ratio",
    "harmonic_energy", "spectral_centroid", "spectral_bandwidth",
    "spectral_entropy", "spectral_flatness", "true_dominant_freq"
]

DATA_DIR = os.path.join("data", "ieee9bus_60hz")
MODELS_DIR = os.path.join("experiments", "phase4c", "models")


def get_available_npz_files() -> Dict[str, str]:
    """Returns mapping of class names to their canonical npz archive paths."""
    mapping = {}
    for c in CLASSES:
        c_lower = c.lower()
        path = os.path.join(DATA_DIR, c_lower, f"{c_lower}_waveforms.npz")
        if os.path.exists(path):
            mapping[c] = path
    return mapping


def load_waveform_sample(class_name: str, index: int = 0) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Loads a 3-phase waveform (1000, 3) from the class's NPZ archive.
    Returns (waveform, metadata_dict).
    """
    c_lower = class_name.lower()
    npz_path = os.path.join(DATA_DIR, c_lower, f"{c_lower}_waveforms.npz")
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Archive not found: {npz_path}")

    with np.load(npz_path, allow_pickle=True) as data:
        waveforms = data["waveforms"]
        total = waveforms.shape[0]
        idx = max(0, min(index, total - 1))
        wv = waveforms[idx].copy()
        
        meta = {
            "class": class_name,
            "index": idx,
            "total_in_class": total,
            "frame_id": str(data["frame_ids"][idx]) if "frame_ids" in data else f"frame_{idx}",
            "split": str(data["splits"][idx]) if "splits" in data else "unknown",
            "scenario_id": str(data["scenario_ids"][idx]) if "scenario_ids" in data else "N/A"
        }
    return wv, meta


def extract_features_for_frame(wv_3phase: np.ndarray, sample_rate: float = 5000.0, f0: float = 60.0) -> Dict[str, Dict[str, float]]:
    """
    Extracts the canonical 32 features for Phase A, B, and C.
    """
    result = {}
    phase_names = ["Phase A", "Phase B", "Phase C"]
    for ph_idx, ph_name in enumerate(phase_names):
        sig = wv_3phase[:, ph_idx]
        raw_feats = extract_enhanced_features(sig, sample_rate=sample_rate, f0=f0)
        ordered_32 = {k: float(raw_feats.get(k, 0.0)) for k in CANONICAL_32_FEATURES}
        result[ph_name] = ordered_32
    return result


def load_candidate_model():
    """Loads the frozen Phase 4C candidate MLP pipeline (StandardScaler + MLPClassifier)."""
    pipe_path = os.path.join(MODELS_DIR, "candidate_mlp_pipeline.pkl")
    if not os.path.exists(pipe_path):
        raise FileNotFoundError(f"Model pipeline not found: {pipe_path}")
    with open(pipe_path, "rb") as f:
        pipe = pickle.load(f)
    return pipe["scaler"], pipe["classifier"]


def predict_phase_features(features_dict: Dict[str, float], scaler=None, classifier=None) -> Dict[str, Any]:
    """
    Evaluates 32-feature vector with the MLP model.
    Returns predicted class, confidence, and class probabilities.
    """
    if scaler is None or classifier is None:
        scaler, classifier = load_candidate_model()
    
    vec = np.array([features_dict[k] for k in CANONICAL_32_FEATURES], dtype=np.float64).reshape(1, -1)
    vec_scaled = scaler.transform(vec)
    pred_idx = classifier.predict(vec_scaled)[0]
    probs = classifier.predict_proba(vec_scaled)[0]

    # Map class index to class name
    pred_class = CLASSES[pred_idx] if 0 <= pred_idx < len(CLASSES) else str(pred_idx)
    prob_dict = {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))}

    return {
        "predicted_class": pred_class,
        "predicted_index": int(pred_idx),
        "confidence": float(np.max(probs)),
        "probabilities": prob_dict
    }


def load_benchmark_summary() -> Dict[str, Any]:
    """Loads Phase 4B comparison summary and Phase 4D independent test evaluation results."""
    summary = {}
    p4b_path = os.path.join("experiments", "phase4b", "baseline_comparison_summary.json")
    if os.path.exists(p4b_path):
        with open(p4b_path, "r") as f:
            summary["phase4b"] = json.load(f)
    
    p4d_path = os.path.join("experiments", "phase4d", "test_metrics.json")
    if os.path.exists(p4d_path):
        with open(p4d_path, "r") as f:
            summary["phase4d"] = json.load(f)
            
    return summary


# ==============================================================================
# Phase 5C Comparative Research Helpers
# ==============================================================================

PHASE5C_DIR = os.path.join("data", "ieee9bus_60hz_phase5c")
PHASE5C_EXP_DIR = os.path.join("experiments", "phase5c")


def load_phase5c_manifest() -> Dict[str, Any]:
    """Loads Phase 5C dataset manifest v2 if available."""
    m_path = os.path.join(PHASE5C_DIR, "dataset_manifest_v2.json")
    if os.path.exists(m_path):
        with open(m_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_phase5c_dual_rate_sample(traj_id: str, window_idx: int = 16) -> Dict[str, Any]:
    """
    Loads both 20 kHz (4,000 pts) and 5 kHz (1,000 pts) waveforms for a given trajectory and window.
    """
    raw_path = os.path.join(PHASE5C_DIR, "raw", f"{traj_id}.mat")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw trajectory MAT file not found: {raw_path}")

    import scipy.io
    mat = scipy.io.loadmat(raw_path)
    v_cont_20k = mat["V_cont_20k"]
    v_cont_5k = mat["V_cont_5k"]

    # Window slicing
    w = max(0, min(window_idx, 31))
    t0 = 0.12
    onset_ms = 20.0 + (w * 1.0)
    t_start = max(0.0, t0 - (onset_ms / 1000.0))

    idx_20k = int(round(t_start * 20000.0))
    idx_5k = int(round(t_start * 5000.0))

    v_20k = v_cont_20k[idx_20k : idx_20k + 4000, :]
    v_5k = v_cont_5k[idx_5k : idx_5k + 1000, :]

    return {
        "trajectory_id": traj_id,
        "window_idx": w,
        "v_20k": v_20k,
        "v_5k": v_5k,
        "t_20k_ms": np.linspace(0, 200, 4000, endpoint=False),
        "t_5k_ms": np.linspace(0, 200, 1000, endpoint=False)
    }


def load_phase5c_research_results() -> Dict[str, Any]:
    """Loads all Phase 5C comparative benchmarks, ablations, SHAP, and challenge evaluations."""
    res = {}
    
    # Classical
    c_path = os.path.join(PHASE5C_EXP_DIR, "classical", "classical_benchmark_metrics.json")
    if os.path.exists(c_path):
        with open(c_path, "r", encoding="utf-8") as f:
            res["classical"] = json.load(f)

    # Feature ablation
    abl_path = os.path.join(PHASE5C_EXP_DIR, "classical", "feature_ablation_results.json")
    if os.path.exists(abl_path):
        with open(abl_path, "r", encoding="utf-8") as f:
            res["feature_ablation"] = json.load(f)

    # Permutation importance
    perm_path = os.path.join(PHASE5C_EXP_DIR, "classical", "permutation_importance.json")
    if os.path.exists(perm_path):
        with open(perm_path, "r", encoding="utf-8") as f:
            res["permutation_importance"] = json.load(f)

    # SHAP
    shap_path = os.path.join(PHASE5C_EXP_DIR, "classical", "shap_summary.json")
    if os.path.exists(shap_path):
        with open(shap_path, "r", encoding="utf-8") as f:
            res["shap"] = json.load(f)

    # Deep learning
    dl_path = os.path.join(PHASE5C_EXP_DIR, "deep_learning", "deep_learning_benchmark_summary.json")
    if os.path.exists(dl_path):
        with open(dl_path, "r", encoding="utf-8") as f:
            res["deep_learning"] = json.load(f)

    # Hybrid
    hyb_path = os.path.join(PHASE5C_EXP_DIR, "hybrid", "hybrid_benchmark_results.json")
    if os.path.exists(hyb_path):
        with open(hyb_path, "r", encoding="utf-8") as f:
            res["hybrid"] = json.load(f)

    # Challenge evaluation
    ch_path = os.path.join(PHASE5C_EXP_DIR, "challenge_eval", "challenge_evaluation_results.json")
    if os.path.exists(ch_path):
        with open(ch_path, "r", encoding="utf-8") as f:
            res["challenge_evaluation"] = json.load(f)

    return res


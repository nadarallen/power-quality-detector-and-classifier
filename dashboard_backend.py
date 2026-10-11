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

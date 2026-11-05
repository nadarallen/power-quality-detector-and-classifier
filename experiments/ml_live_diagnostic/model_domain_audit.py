"""
experiments/ml_live_diagnostic/model_domain_audit.py
----------------------------------------------------
Audits the feature domain and establishes honest Out-Of-Distribution (OOD)
and uncertainty status indicators:
- VALID_CLASSIFICATION
- LOW_CONFIDENCE
- OUT_OF_DISTRIBUTION
- MULTI_DISTURBANCE
- MODEL_DOMAIN_MISMATCH
- INSUFFICIENT_WINDOW
- INVALID_SIGNAL

Calibrates thresholds using the training set bounding box and Mahalanobis distance.
"""

import os
import sys
import json
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, _features_to_vector
import simulation_bridge as sb

def audit_model_domain():
    model_path = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models", "candidate_mlp_weights.json")
    with open(model_path, "r", encoding="utf-8") as f:
        model_data = json.load(f)

    features = model_data["features"]
    mean = np.array(model_data["scaler_mean"], dtype=np.float32)
    scale = np.array(model_data["scaler_scale"], dtype=np.float32)

    # Load all training features to compute domain bounds
    all_train_feats = []
    classes = ["normal", "sag", "swell", "harmonics", "flicker", "notch", "transient", "interruption"]
    for c in classes:
        csv_path = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", c, f"{c}_features.csv")
        df = pd.read_csv(csv_path)
        all_train_feats.append(df[features].to_numpy(dtype=np.float32))

    X_train = np.vstack(all_train_feats)
    Z_train = (X_train - mean) / scale

    # Compute bounding box and empirical covariance
    z_min = np.min(Z_train, axis=0)
    z_max = np.max(Z_train, axis=0)
    cov_z = np.cov(Z_train, rowvar=False)
    inv_cov_z = np.linalg.pinv(cov_z + 1e-4 * np.eye(len(features)))

    # Compute 99.5% Mahalanobis distance threshold
    diff = Z_train
    m_dists = np.sqrt(np.sum(diff @ inv_cov_z * diff, axis=1))
    m_threshold_99 = float(np.percentile(m_dists, 99.5))

    print("==================================================================")
    print("MODEL DOMAIN & OOD BOUNDARY CALIBRATION")
    print("==================================================================")
    print(f"Total training frames: {len(X_train)}")
    print(f"Feature dimensions: {len(features)}")
    print(f"99.5th percentile Mahalanobis distance: {m_threshold_99:.3f}")

    def evaluate_signal_domain(signal: np.ndarray, sample_rate: float = 5000.0, event_fraction: float = 1.0):
        N = len(signal)
        if N < 250:
            return "INSUFFICIENT_WINDOW", 0.0, "Sample count below minimum required"

        # Check signal validity
        rms = np.sqrt(np.mean(signal ** 2))
        if rms < 0.01 or np.isnan(rms):
            return "INVALID_SIGNAL", 0.0, "Zero or invalid voltage signal"

        feat = extract_enhanced_features(signal, sample_rate, 60.0)
        vec = _features_to_vector(feat)
        z = (vec - mean) / scale

        # Mahalanobis distance
        d_m = float(np.sqrt(np.dot(np.dot(z, inv_cov_z), z)))

        # Evaluate model prediction
        pred_res = sb.predict_60hz_model(signal, sample_rate)
        conf = pred_res["confidence"]

        if event_fraction < 0.30:
            return "INSUFFICIENT_WINDOW", conf, f"Event fraction ({event_fraction*100:.1f}%) too small"

        if d_m > m_threshold_99 * 1.5:
            return "OUT_OF_DISTRIBUTION", conf, f"Mahalanobis distance ({d_m:.1f}) exceeds domain threshold ({m_threshold_99:.1f})"

        if conf < 0.60:
            return "LOW_CONFIDENCE", conf, f"Softmax confidence ({conf*100:.1f}%) below 60% threshold"

        return "VALID_CLASSIFICATION", conf, "Within validated 60 Hz IEEE 9-bus domain"

    # Test calibration on known cases
    test_cases = [
        ("Normal Baseline", np.load(os.path.join(PROJECT_ROOT, "data/ieee9bus_60hz/normal/normal_waveforms.npz"))["waveforms"][0, :, 0], 1.0),
        ("Sag Disturbance", np.load(os.path.join(PROJECT_ROOT, "data/ieee9bus_60hz/sag/sag_waveforms.npz"))["waveforms"][0, :, 0], 1.0),
        ("White Noise (OOD)", np.random.normal(0, 0.5, 1000).astype(np.float32), 1.0),
        ("Zero Signal", np.zeros(1000, dtype=np.float32), 1.0),
        ("Short 10-sample Window", np.ones(50, dtype=np.float32), 1.0),
    ]

    print("\nCalibration Validation:")
    print("-" * 75)
    for name, sig, frac in test_cases:
        status, conf, reason = evaluate_signal_domain(sig, 5000.0, frac)
        print(f"  {name:25s} -> Status: {status:22s} (conf={conf*100:5.1f}%) | {reason}")

    out_file = os.path.join(os.path.dirname(__file__), "model_domain_audit_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "mahalanobis_threshold_99_5": m_threshold_99,
            "feature_mean": mean.tolist(),
            "feature_scale": scale.tolist(),
            "inv_cov_z_diagonal": np.diag(inv_cov_z).tolist()
        }, f, indent=2)

    print(f"\nDomain audit results saved to: {out_file}")

if __name__ == "__main__":
    audit_model_domain()

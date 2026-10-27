"""
experiments/phase5c/challenge_eval/run_challenge_evaluation.py
--------------------------------------------------------------
One-time independent Challenge Evaluation on the quarantined challenge partition
(Conditions 33-36: Renewable Inverter Penetration, Severe Reactive Imbalance,
Asymmetric Substation Loading, Stressed Transmission Import).

Models evaluated:
1. Best Classical ML Model
2. Compact 1D CNN (20 kHz)
3. Temporal Convolutional Network (TCN, 20 kHz)
4. HybridPQNet (Waveform + 32 Features)

Strict protocol:
- No hyperparameter tuning or retraining on challenge data
- Comprehensive breakdown by condition, noise SNR, ADC resolution, and class
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.deep_learning.waveform_models import Compact1DCNN, TemporalConvNet, HybridPQNet

DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'processed')
CLASSICAL_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'classical')
DL_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'deep_learning')
HYBRID_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'hybrid')
OUT_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'challenge_eval')
os.makedirs(OUT_DIR, exist_ok=True)

CLASS_NAMES = ["Flicker", "Harmonics", "Interruption", "Normal", "Notch", "Sag", "Swell", "Transient"]


def run_one_time_challenge_evaluation():
    print("=" * 80)
    print("PHASE 5C PART VII: ONE-TIME QUARANTINED CHALLENGE EVALUATION")
    print("=" * 80)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Evaluation compute device: {device}")

    # 1. Load Challenge Dataset
    path_20k = os.path.join(DATA_DIR, 'phase5c_waveforms_20k.npz')
    path_feats_npz = os.path.join(DATA_DIR, 'phase5c_features.npz')
    path_feats_csv = os.path.join(DATA_DIR, 'phase5c_features.csv')

    data_20k = np.load(path_20k, allow_pickle=True)
    data_feats = np.load(path_feats_npz, allow_pickle=True)
    df_meta = pd.read_csv(path_feats_csv)

    splits = data_feats['splits']
    ch_mask = (splits == 'challenge')
    num_ch = np.sum(ch_mask)

    print(f"Loaded Challenge Partition: {num_ch} frames across {len(np.unique(data_feats['trajectory_ids'][ch_mask]))} trajectories.")
    assert num_ch == 1024, f"Expected 1,024 challenge frames, found {num_ch}"

    y_ch = data_feats['labels'][ch_mask]
    X_ch_raw_feats = data_feats['features'][ch_mask]
    w_ch_raw = np.transpose(data_20k['waveforms_20k'][ch_mask], (0, 2, 1)).astype(np.float32)

    df_ch = df_meta[ch_mask].reset_index(drop=True)

    # 2. Normalize using FROZEN training-only parameters
    # Classical scaler
    scaler_path = os.path.join(CLASSICAL_DIR, 'phase5c_classical_scaler.joblib')
    scaler = joblib.load(scaler_path)
    X_ch_scaled_feats = scaler.transform(X_ch_raw_feats)

    # Deep learning waveform normalization
    with open(os.path.join(DL_DIR, 'deep_learning_norm_params.json'), 'r') as f:
        norm_params = json.load(f)
    ch_mean = np.array(norm_params['ch_mean_20k']).reshape(1, 3, 1)
    ch_std = np.array(norm_params['ch_std_20k']).reshape(1, 3, 1)
    w_ch_norm = (w_ch_raw - ch_mean) / ch_std

    # PyTorch tensors
    w_tensor = torch.from_numpy(w_ch_norm).float()
    f_tensor = torch.from_numpy(X_ch_scaled_feats).float()

    # 3. Load Candidate Models
    # Candidate 1: Classical Best
    with open(os.path.join(CLASSICAL_DIR, 'classical_benchmark_metrics.json'), 'r') as f:
        classical_meta = json.load(f)
    best_classical_name = classical_meta['best_model']
    classical_model_file = os.path.join(CLASSICAL_DIR, f"model_{best_classical_name.lower().replace(' ', '_')}.joblib")
    best_classical_model = joblib.load(classical_model_file)
    print(f"Loaded Candidate 1 (Classical Best): {best_classical_name}")

    # Candidate 2: 1D CNN
    cnn_model = Compact1DCNN(in_channels=3, num_classes=8).to(device)
    cnn_model.load_state_dict(torch.load(os.path.join(DL_DIR, 'best_cnn_20k.pt'), map_location=device, weights_only=True))
    cnn_model.eval()
    print("Loaded Candidate 2: Compact 1D CNN (20 kHz)")

    # Candidate 3: TCN
    tcn_model = TemporalConvNet(in_channels=3, num_classes=8).to(device)
    tcn_model.load_state_dict(torch.load(os.path.join(DL_DIR, 'best_tcn_20k.pt'), map_location=device, weights_only=True))
    tcn_model.eval()
    print("Loaded Candidate 3: Temporal Convolutional Network (TCN, 20 kHz)")

    # Candidate 4: HybridPQNet
    hybrid_model = HybridPQNet(in_waveform_channels=3, in_features_dim=32, num_classes=8).to(device)
    hybrid_model.load_state_dict(torch.load(os.path.join(HYBRID_DIR, 'best_hybrid_model.pt'), map_location=device, weights_only=True))
    hybrid_model.eval()
    print("Loaded Candidate 4: HybridPQNet (Waveform + Features Fusion)")

    # 4. Generate Predictions
    print("\nExecuting forward evaluation on Challenge partition...")
    # Classical predictions
    preds_classical = best_classical_model.predict(X_ch_scaled_feats)

    # CNN predictions
    with torch.no_grad():
        out_cnn = cnn_model(w_tensor.to(device))
        preds_cnn = torch.argmax(out_cnn, dim=1).cpu().numpy()

    # TCN predictions
    with torch.no_grad():
        out_tcn = tcn_model(w_tensor.to(device))
        preds_tcn = torch.argmax(out_tcn, dim=1).cpu().numpy()

    # Hybrid predictions
    with torch.no_grad():
        out_hybrid = hybrid_model(w_tensor.to(device), f_tensor.to(device))
        preds_hybrid = torch.argmax(out_hybrid, dim=1).cpu().numpy()

    all_preds_dict = {
        f"Classical ({best_classical_name})": preds_classical,
        "Compact 1D CNN (20 kHz)": preds_cnn,
        "Temporal ConvNet (TCN)": preds_tcn,
        "HybridPQNet": preds_hybrid
    }

    # 5. Compute Comprehensive Metrics
    challenge_summary = {}
    print("\n" + "=" * 80)
    print("CHALLENGE EVALUATION RESULTS:")
    print("=" * 80)

    for m_name, preds in all_preds_dict.items():
        acc = accuracy_score(y_ch, preds)
        bal_acc = balanced_accuracy_score(y_ch, preds)
        macro_f1 = f1_score(y_ch, preds, average='macro', zero_division=0)
        macro_prec = precision_score(y_ch, preds, average='macro', zero_division=0)
        macro_rec = recall_score(y_ch, preds, average='macro', zero_division=0)
        cm = confusion_matrix(y_ch, preds).tolist()

        per_class_f1 = f1_score(y_ch, preds, average=None, zero_division=0).tolist()
        per_class_prec = precision_score(y_ch, preds, average=None, zero_division=0).tolist()
        per_class_rec = recall_score(y_ch, preds, average=None, zero_division=0).tolist()

        per_class_stats = {}
        for c_idx, c_name in enumerate(CLASS_NAMES):
            per_class_stats[c_name] = {
                'f1': per_class_f1[c_idx],
                'precision': per_class_prec[c_idx],
                'recall': per_class_rec[c_idx]
            }

        # Breakdown by condition (33, 34, 35, 36)
        by_condition = {}
        for c_id in sorted(df_ch['operating_condition_id'].unique()):
            c_mask = (df_ch['operating_condition_id'] == c_id).values
            c_acc = accuracy_score(y_ch[c_mask], preds[c_mask])
            c_f1 = f1_score(y_ch[c_mask], preds[c_mask], average='macro', zero_division=0)
            by_condition[str(c_id)] = {'accuracy': float(c_acc), 'macro_f1': float(c_f1)}

        # Breakdown by SNR (52, 46, 40 dB)
        by_snr = {}
        for snr_val in sorted(df_ch['snr_db'].unique()):
            snr_mask = (df_ch['snr_db'] == snr_val).values
            s_acc = accuracy_score(y_ch[snr_mask], preds[snr_mask])
            s_f1 = f1_score(y_ch[snr_mask], preds[snr_mask], average='macro', zero_division=0)
            by_snr[f"{snr_val}dB"] = {'accuracy': float(s_acc), 'macro_f1': float(s_f1)}

        # Breakdown by ADC bits (12, 14 bits)
        by_adc = {}
        for adc_val in sorted(df_ch['adc_bits'].unique()):
            adc_mask = (df_ch['adc_bits'] == adc_val).values
            a_acc = accuracy_score(y_ch[adc_mask], preds[adc_mask])
            a_f1 = f1_score(y_ch[adc_mask], preds[adc_mask], average='macro', zero_division=0)
            by_adc[f"{adc_val}bit"] = {'accuracy': float(a_acc), 'macro_f1': float(a_f1)}

        print(f"\nModel: {m_name}")
        print(f"  Overall: Accuracy = {acc*100:.2f}% | Balanced Acc = {bal_acc*100:.2f}% | Macro F1 = {macro_f1*100:.2f}%")
        print("  Condition Breakdown:")
        for cid, c_stats in by_condition.items():
            print(f"    Cond {cid}: Macro F1 = {c_stats['macro_f1']*100:.2f}% (Acc: {c_stats['accuracy']*100:.2f}%)")
        print("  SNR Breakdown:")
        for snr_k, s_stats in by_snr.items():
            print(f"    {snr_k}: Macro F1 = {s_stats['macro_f1']*100:.2f}% (Acc: {s_stats['accuracy']*100:.2f}%)")

        challenge_summary[m_name] = {
            'accuracy': float(acc),
            'balanced_accuracy': float(bal_acc),
            'macro_f1': float(macro_f1),
            'macro_precision': float(macro_prec),
            'macro_recall': float(macro_rec),
            'confusion_matrix': cm,
            'per_class': per_class_stats,
            'by_condition': by_condition,
            'by_snr': by_snr,
            'by_adc': by_adc
        }

    # Save to JSON
    out_file = os.path.join(OUT_DIR, 'challenge_evaluation_results.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(challenge_summary, f, indent=2)

    print("\n" + "=" * 80)
    print("CHALLENGE EVALUATION COMPLETED")
    print(f"Authoritative challenge evaluation results saved to: {out_file}")
    print("=" * 80)


if __name__ == '__main__':
    run_one_time_challenge_evaluation()

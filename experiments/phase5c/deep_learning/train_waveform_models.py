"""
experiments/phase5c/deep_learning/train_waveform_models.py
----------------------------------------------------------
Rigorous deep learning comparison for raw voltage waveforms:
- Models: Compact 1D CNN and Temporal Convolutional Network (TCN)
- Sampling rate hypothesis: 20 kHz (4,000 pts) vs 5 kHz (1,000 pts)
- Explainability: Temporal-window occlusion and single-phase vs three-phase ablation
- Partition isolation: Fitted strictly on Train split (80 trajs, 2,560 frames);
  Evaluated on Validation split (32 trajs, 1,024 frames);
  Challenge split (32 trajs, 1,024 frames) quarantined.
"""

import os
import sys
import json
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
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

from models.deep_learning.waveform_models import Compact1DCNN, TemporalConvNet

DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'processed')
OUT_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'deep_learning')
os.makedirs(OUT_DIR, exist_ok=True)

CLASS_NAMES = ["Flicker", "Harmonics", "Interruption", "Normal", "Notch", "Sag", "Swell", "Transient"]


def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(y)
    return total_loss / len(loader.dataset)


def evaluate(model, loader, device):
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            out = model(x)
            preds = torch.argmax(out, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(y.numpy())
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    acc = accuracy_score(all_targets, all_preds)
    bal_acc = balanced_accuracy_score(all_targets, all_preds)
    macro_f1 = f1_score(all_targets, all_preds, average='macro', zero_division=0)
    macro_prec = precision_score(all_targets, all_preds, average='macro', zero_division=0)
    macro_rec = recall_score(all_targets, all_preds, average='macro', zero_division=0)
    cm = confusion_matrix(all_targets, all_preds).tolist()

    per_class_f1 = f1_score(all_targets, all_preds, average=None, zero_division=0).tolist()
    per_class_rec = recall_score(all_targets, all_preds, average=None, zero_division=0).tolist()
    per_class_prec = precision_score(all_targets, all_preds, average=None, zero_division=0).tolist()

    per_class_stats = {}
    for c_idx, c_name in enumerate(CLASS_NAMES):
        per_class_stats[c_name] = {
            'f1': per_class_f1[c_idx],
            'precision': per_class_prec[c_idx],
            'recall': per_class_rec[c_idx]
        }

    return {
        'accuracy': float(acc),
        'balanced_accuracy': float(bal_acc),
        'macro_f1': float(macro_f1),
        'macro_precision': float(macro_prec),
        'macro_recall': float(macro_rec),
        'confusion_matrix': cm,
        'per_class': per_class_stats,
        'predictions': all_preds
    }


def run_deep_learning_benchmark():
    print("=" * 80)
    print("PHASE 5C TRACK B: RAW-WAVEFORM DEEP LEARNING (CNN & TCN)")
    print("=" * 80)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Executing on compute device: {device}")

    # Set seeds
    torch.manual_seed(42)
    np.random.seed(42)

    # 1. Load 20 kHz dataset
    path_20k = os.path.join(DATA_DIR, 'phase5c_waveforms_20k.npz')
    if not os.path.exists(path_20k):
        raise FileNotFoundError(f"20 kHz dataset not found at {path_20k}")

    data_20k = np.load(path_20k, allow_pickle=True)
    w_20k = data_20k['waveforms_20k']  # [4608, 4000, 3]
    labels_20k = data_20k['labels']
    splits_20k = data_20k['splits']

    # Transpose to PyTorch shape [N, Channels=3, Length=4000]
    w_20k = np.transpose(w_20k, (0, 2, 1)).astype(np.float32)

    train_mask = (splits_20k == 'train')
    val_mask = (splits_20k == 'val')

    X_train_20k = w_20k[train_mask]
    y_train = labels_20k[train_mask]
    X_val_20k = w_20k[val_mask]
    y_val = labels_20k[val_mask]

    # Compute training-only channel normalization stats
    ch_mean_20k = np.mean(X_train_20k, axis=(0, 2), keepdims=True)
    ch_std_20k = np.std(X_train_20k, axis=(0, 2), keepdims=True) + 1e-8

    X_train_20k_norm = (X_train_20k - ch_mean_20k) / ch_std_20k
    X_val_20k_norm = (X_val_20k - ch_mean_20k) / ch_std_20k

    train_ds_20k = TensorDataset(torch.from_numpy(X_train_20k_norm), torch.from_numpy(y_train).long())
    val_ds_20k = TensorDataset(torch.from_numpy(X_val_20k_norm), torch.from_numpy(y_val).long())

    train_loader_20k = DataLoader(train_ds_20k, batch_size=64, shuffle=True)
    val_loader_20k = DataLoader(val_ds_20k, batch_size=64, shuffle=False)

    print(f"20 kHz Datasets: Train={len(train_ds_20k)} frames, Val={len(val_ds_20k)} frames")

    # 2. Train Compact1DCNN on 20 kHz
    print("\n--- Training Compact 1D CNN (20 kHz) ---")
    cnn_20k = Compact1DCNN(in_channels=3, num_classes=8).to(device)
    optimizer = torch.optim.Adam(cnn_20k.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    best_cnn_f1 = -1.0
    best_cnn_metrics = None
    best_cnn_path = os.path.join(OUT_DIR, 'best_cnn_20k.pt')

    for epoch in range(1, 26):
        loss = train_epoch(cnn_20k, train_loader_20k, criterion, optimizer, device)
        val_metrics = evaluate(cnn_20k, val_loader_20k, device)
        if val_metrics['macro_f1'] > best_cnn_f1:
            best_cnn_f1 = val_metrics['macro_f1']
            best_cnn_metrics = val_metrics
            torch.save(cnn_20k.state_dict(), best_cnn_path)
        if epoch % 5 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Train Loss: {loss:.4f} | Val Acc: {val_metrics['accuracy']*100:.2f}% | Val Macro F1: {val_metrics['macro_f1']*100:.2f}% (Best: {best_cnn_f1*100:.2f}%)")

    # 3. Train TemporalConvNet (TCN) on 20 kHz
    print("\n--- Training Temporal Convolutional Network (TCN) (20 kHz) ---")
    tcn_20k = TemporalConvNet(in_channels=3, num_classes=8).to(device)
    optimizer_tcn = torch.optim.Adam(tcn_20k.parameters(), lr=1e-3, weight_decay=1e-4)

    best_tcn_f1 = -1.0
    best_tcn_metrics = None
    best_tcn_path = os.path.join(OUT_DIR, 'best_tcn_20k.pt')

    for epoch in range(1, 26):
        loss = train_epoch(tcn_20k, train_loader_20k, criterion, optimizer_tcn, device)
        val_metrics = evaluate(tcn_20k, val_loader_20k, device)
        if val_metrics['macro_f1'] > best_tcn_f1:
            best_tcn_f1 = val_metrics['macro_f1']
            best_tcn_metrics = val_metrics
            torch.save(tcn_20k.state_dict(), best_tcn_path)
        if epoch % 5 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Train Loss: {loss:.4f} | Val Acc: {val_metrics['accuracy']*100:.2f}% | Val Macro F1: {val_metrics['macro_f1']*100:.2f}% (Best: {best_tcn_f1*100:.2f}%)")

    # 4. Train Compact1DCNN on 5 kHz for Sampling-Rate Hypothesis Testing
    print("\n--- Training Compact 1D CNN on 5 kHz (Hypothesis Test: 20 kHz vs 5 kHz) ---")
    path_5k = os.path.join(DATA_DIR, 'phase5c_waveforms_5k.npz')
    data_5k = np.load(path_5k, allow_pickle=True)
    w_5k = np.transpose(data_5k['waveforms_5k'], (0, 2, 1)).astype(np.float32)

    X_train_5k = w_5k[train_mask]
    X_val_5k = w_5k[val_mask]

    ch_mean_5k = np.mean(X_train_5k, axis=(0, 2), keepdims=True)
    ch_std_5k = np.std(X_train_5k, axis=(0, 2), keepdims=True) + 1e-8

    X_train_5k_norm = (X_train_5k - ch_mean_5k) / ch_std_5k
    X_val_5k_norm = (X_val_5k - ch_mean_5k) / ch_std_5k

    train_ds_5k = TensorDataset(torch.from_numpy(X_train_5k_norm), torch.from_numpy(y_train).long())
    val_ds_5k = TensorDataset(torch.from_numpy(X_val_5k_norm), torch.from_numpy(y_val).long())

    train_loader_5k = DataLoader(train_ds_5k, batch_size=64, shuffle=True)
    val_loader_5k = DataLoader(val_ds_5k, batch_size=64, shuffle=False)

    cnn_5k = Compact1DCNN(in_channels=3, num_classes=8).to(device)
    optimizer_5k = torch.optim.Adam(cnn_5k.parameters(), lr=1e-3, weight_decay=1e-4)

    best_5k_f1 = -1.0
    best_5k_metrics = None
    best_5k_path = os.path.join(OUT_DIR, 'best_cnn_5k.pt')

    for epoch in range(1, 26):
        loss = train_epoch(cnn_5k, train_loader_5k, criterion, optimizer_5k, device)
        val_metrics = evaluate(cnn_5k, val_loader_5k, device)
        if val_metrics['macro_f1'] > best_5k_f1:
            best_5k_f1 = val_metrics['macro_f1']
            best_5k_metrics = val_metrics
            torch.save(cnn_5k.state_dict(), best_5k_path)
        if epoch % 5 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Train Loss: {loss:.4f} | Val Acc: {val_metrics['accuracy']*100:.2f}% | Val Macro F1: {val_metrics['macro_f1']*100:.2f}%")

    # 5. Explainability & Ablation Experiments
    print("\n--- Performing Explainability & Ablation Analysis ---")
    # Load best 20k CNN
    cnn_20k.load_state_dict(torch.load(best_cnn_path, map_location=device, weights_only=True))
    cnn_20k.eval()

    # A. Phase Ablation: Compare 3-phase vs Phase A only
    X_val_single_phase = X_val_20k_norm.copy()
    X_val_single_phase[:, 1, :] = 0.0  # Zero out Phase B
    X_val_single_phase[:, 2, :] = 0.0  # Zero out Phase C

    single_phase_ds = TensorDataset(torch.from_numpy(X_val_single_phase), torch.from_numpy(y_val).long())
    single_phase_loader = DataLoader(single_phase_ds, batch_size=64, shuffle=False)
    single_phase_metrics = evaluate(cnn_20k, single_phase_loader, device)

    print(f"Phase Ablation: 3-Phase Val F1: {best_cnn_f1*100:.2f}% vs Phase-A Only Val F1: {single_phase_metrics['macro_f1']*100:.2f}% (Delta: {(single_phase_metrics['macro_f1'] - best_cnn_f1)*100:+.2f}%)")

    # B. Temporal Occlusion Window Analysis
    # Divide 4000 samples into 10 temporal bins (400 samples = 20 ms each)
    occlusion_steps = 10
    step_size = 4000 // occlusion_steps
    occlusion_f1_drops = []

    for step in range(occlusion_steps):
        occ_val = X_val_20k_norm.copy()
        start_idx = step * step_size
        end_idx = start_idx + step_size
        occ_val[:, :, start_idx:end_idx] = 0.0  # Occlude temporal window

        occ_ds = TensorDataset(torch.from_numpy(occ_val), torch.from_numpy(y_val).long())
        occ_loader = DataLoader(occ_ds, batch_size=64, shuffle=False)
        occ_metrics = evaluate(cnn_20k, occ_loader, device)
        f1_drop = best_cnn_f1 - occ_metrics['macro_f1']
        occlusion_f1_drops.append({
            'bin_idx': step,
            'time_ms_start': step * 20.0,
            'time_ms_end': (step + 1) * 20.0,
            'occluded_macro_f1': occ_metrics['macro_f1'],
            'macro_f1_drop': f1_drop
        })
        print(f"  Occlusion [{step*20:3.0f}-{(step+1)*20:3.0f} ms]: Macro F1 = {occ_metrics['macro_f1']*100:.2f}% (F1 Drop: {f1_drop*100:+.2f}%)")

    # 6. Save all results
    summary = {
        'best_models': {
            'cnn_20k': {
                'macro_f1': best_cnn_f1,
                'accuracy': best_cnn_metrics['accuracy'],
                'balanced_accuracy': best_cnn_metrics['balanced_accuracy'],
                'confusion_matrix': best_cnn_metrics['confusion_matrix'],
                'per_class': best_cnn_metrics['per_class']
            },
            'tcn_20k': {
                'macro_f1': best_tcn_f1,
                'accuracy': best_tcn_metrics['accuracy'],
                'balanced_accuracy': best_tcn_metrics['balanced_accuracy'],
                'confusion_matrix': best_tcn_metrics['confusion_matrix'],
                'per_class': best_tcn_metrics['per_class']
            },
            'cnn_5k': {
                'macro_f1': best_5k_f1,
                'accuracy': best_5k_metrics['accuracy'],
                'balanced_accuracy': best_5k_metrics['balanced_accuracy'],
                'confusion_matrix': best_5k_metrics['confusion_matrix'],
                'per_class': best_5k_metrics['per_class']
            }
        },
        'sampling_rate_comparison': {
            'hypothesis': '20 kHz improves sub-cycle Notch and Transient classification over 5 kHz',
            'notch_f1_20k': best_cnn_metrics['per_class']['Notch']['f1'],
            'notch_f1_5k': best_5k_metrics['per_class']['Notch']['f1'],
            'transient_f1_20k': best_cnn_metrics['per_class']['Transient']['f1'],
            'transient_f1_5k': best_5k_metrics['per_class']['Transient']['f1'],
            'overall_f1_20k': best_cnn_f1,
            'overall_f1_5k': best_5k_f1
        },
        'phase_ablation': {
            'three_phase_macro_f1': best_cnn_f1,
            'single_phase_macro_f1': single_phase_metrics['macro_f1'],
            'delta_macro_f1': single_phase_metrics['macro_f1'] - best_cnn_f1
        },
        'temporal_occlusion': occlusion_f1_drops
    }

    with open(os.path.join(OUT_DIR, 'deep_learning_benchmark_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Save normalization parameters
    norm_meta = {
        'ch_mean_20k': ch_mean_20k.squeeze().tolist(),
        'ch_std_20k': ch_std_20k.squeeze().tolist(),
        'ch_mean_5k': ch_mean_5k.squeeze().tolist(),
        'ch_std_5k': ch_std_5k.squeeze().tolist()
    }
    with open(os.path.join(OUT_DIR, 'deep_learning_norm_params.json'), 'w', encoding='utf-8') as f:
        json.dump(norm_meta, f, indent=2)

    print("\n" + "=" * 80)
    print("TRACK B DEEP LEARNING BENCHMARK COMPLETE")
    print(f"Artifacts saved to: {OUT_DIR}")
    print("=" * 80)


if __name__ == '__main__':
    run_deep_learning_benchmark()

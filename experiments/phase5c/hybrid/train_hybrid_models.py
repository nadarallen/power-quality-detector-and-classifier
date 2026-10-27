"""
experiments/phase5c/hybrid/train_hybrid_models.py
-------------------------------------------------
Controlled Hybrid Model comparison:
1. Features-Only Baseline (MLP on 32 engineered features)
2. Waveform-Only Baseline (Compact 1D CNN on 20 kHz 3-phase raw waveform)
3. HybridPQNet (Unified end-to-end fusion of learned waveform representation + 32 engineered features)
4. Feature ablation within Hybrid

Investigates:
Does the hybrid model add complementary information or duplicate patterns?
"""

import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import StandardScaler
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

from models.deep_learning.waveform_models import Compact1DCNN, HybridPQNet

DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'processed')
OUT_DIR = os.path.join(PROJECT_ROOT, 'experiments', 'phase5c', 'hybrid')
os.makedirs(OUT_DIR, exist_ok=True)

CLASS_NAMES = ["Flicker", "Harmonics", "Interruption", "Normal", "Notch", "Sag", "Swell", "Transient"]


class FeaturesOnlyNet(nn.Module):
    def __init__(self, in_features: int = 32, num_classes: int = 8):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes)
        )

    def forward(self, feats: torch.Tensor) -> torch.Tensor:
        return self.net(feats)


def evaluate_hybrid(model, loader, device, mode='hybrid'):
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for batch in loader:
            if mode == 'hybrid':
                w, f, y = batch
                w, f = w.to(device), f.to(device)
                out = model(w, f)
            elif mode == 'waveform':
                w, y = batch
                w = w.to(device)
                out = model(w)
            elif mode == 'features':
                f, y = batch
                f = f.to(device)
                out = model(f)
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
    per_class_stats = {
        CLASS_NAMES[i]: {'f1': per_class_f1[i]} for i in range(len(CLASS_NAMES))
    }

    return {
        'accuracy': float(acc),
        'balanced_accuracy': float(bal_acc),
        'macro_f1': float(macro_f1),
        'macro_precision': float(macro_prec),
        'macro_recall': float(macro_rec),
        'confusion_matrix': cm,
        'per_class': per_class_stats
    }


def run_hybrid_benchmark():
    print("=" * 80)
    print("PHASE 5C TRACK C: CONTROLLED HYBRID MODEL COMPARISON")
    print("=" * 80)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Executing on device: {device}")

    torch.manual_seed(42)
    np.random.seed(42)

    # 1. Load Data
    path_20k = os.path.join(DATA_DIR, 'phase5c_waveforms_20k.npz')
    path_feats = os.path.join(DATA_DIR, 'phase5c_features.npz')

    data_20k = np.load(path_20k, allow_pickle=True)
    data_feats = np.load(path_feats, allow_pickle=True)

    w_20k = np.transpose(data_20k['waveforms_20k'], (0, 2, 1)).astype(np.float32)  # [N, 3, 4000]
    feats = data_feats['features'].astype(np.float32)                               # [N, 32]
    labels = data_feats['labels']
    splits = data_feats['splits']

    train_mask = (splits == 'train')
    val_mask = (splits == 'val')

    # Normalize waveforms using Train only
    ch_mean = np.mean(w_20k[train_mask], axis=(0, 2), keepdims=True)
    ch_std = np.std(w_20k[train_mask], axis=(0, 2), keepdims=True) + 1e-8
    w_20k_norm = (w_20k - ch_mean) / ch_std

    # Normalize features using Train only
    scaler = StandardScaler()
    feats_norm = feats.copy()
    feats_norm[train_mask] = scaler.fit_transform(feats[train_mask])
    feats_norm[val_mask] = scaler.transform(feats[val_mask])

    # Datasets
    train_w = torch.from_numpy(w_20k_norm[train_mask])
    train_f = torch.from_numpy(feats_norm[train_mask])
    train_y = torch.from_numpy(labels[train_mask]).long()

    val_w = torch.from_numpy(w_20k_norm[val_mask])
    val_f = torch.from_numpy(feats_norm[val_mask])
    val_y = torch.from_numpy(labels[val_mask]).long()

    # Hybrid loaders
    train_hybrid_ds = TensorDataset(train_w, train_f, train_y)
    val_hybrid_ds = TensorDataset(val_w, val_f, val_y)
    train_hybrid_loader = DataLoader(train_hybrid_ds, batch_size=64, shuffle=True)
    val_hybrid_loader = DataLoader(val_hybrid_ds, batch_size=64, shuffle=False)

    # Features-only loaders
    train_f_loader = DataLoader(TensorDataset(train_f, train_y), batch_size=64, shuffle=True)
    val_f_loader = DataLoader(TensorDataset(val_f, val_y), batch_size=64, shuffle=False)

    # Waveform-only loaders
    train_w_loader = DataLoader(TensorDataset(train_w, train_y), batch_size=64, shuffle=True)
    val_w_loader = DataLoader(TensorDataset(val_w, val_y), batch_size=64, shuffle=False)

    criterion = nn.CrossEntropyLoss()

    # --- Experiment 1: Features Only Baseline ---
    print("\n--- 1. Training Features-Only Baseline (Dense MLP) ---")
    f_model = FeaturesOnlyNet(in_features=32, num_classes=8).to(device)
    opt_f = torch.optim.Adam(f_model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_f_metrics = None
    best_f_f1 = -1.0

    for epoch in range(1, 26):
        f_model.train()
        for f, y in train_f_loader:
            f, y = f.to(device), y.to(device)
            opt_f.zero_grad()
            loss = criterion(f_model(f), y)
            loss.backward()
            opt_f.step()
        m = evaluate_hybrid(f_model, val_f_loader, device, mode='features')
        if m['macro_f1'] > best_f_f1:
            best_f_f1 = m['macro_f1']
            best_f_metrics = m
        if epoch % 10 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Val Acc: {m['accuracy']*100:.2f}% | Val Macro F1: {m['macro_f1']*100:.2f}% (Best: {best_f_f1*100:.2f}%)")

    # --- Experiment 2: Waveform Only Baseline ---
    print("\n--- 2. Training Waveform-Only Baseline (Compact 1D CNN) ---")
    w_model = Compact1DCNN(in_channels=3, num_classes=8).to(device)
    opt_w = torch.optim.Adam(w_model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_w_metrics = None
    best_w_f1 = -1.0

    for epoch in range(1, 26):
        w_model.train()
        for w, y in train_w_loader:
            w, y = w.to(device), y.to(device)
            opt_w.zero_grad()
            loss = criterion(w_model(w), y)
            loss.backward()
            opt_w.step()
        m = evaluate_hybrid(w_model, val_w_loader, device, mode='waveform')
        if m['macro_f1'] > best_w_f1:
            best_w_f1 = m['macro_f1']
            best_w_metrics = m
        if epoch % 10 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Val Acc: {m['accuracy']*100:.2f}% | Val Macro F1: {m['macro_f1']*100:.2f}% (Best: {best_w_f1*100:.2f}%)")

    # --- Experiment 3: Hybrid Fusion Model (HybridPQNet) ---
    print("\n--- 3. Training Hybrid Model (HybridPQNet: Waveform + Features Fusion) ---")
    h_model = HybridPQNet(in_waveform_channels=3, in_features_dim=32, num_classes=8).to(device)
    opt_h = torch.optim.Adam(h_model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_h_metrics = None
    best_h_f1 = -1.0
    best_h_path = os.path.join(OUT_DIR, 'best_hybrid_model.pt')

    for epoch in range(1, 26):
        h_model.train()
        for w, f, y in train_hybrid_loader:
            w, f, y = w.to(device), f.to(device), y.to(device)
            opt_h.zero_grad()
            loss = criterion(h_model(w, f), y)
            loss.backward()
            opt_h.step()
        m = evaluate_hybrid(h_model, val_hybrid_loader, device, mode='hybrid')
        if m['macro_f1'] > best_h_f1:
            best_h_f1 = m['macro_f1']
            best_h_metrics = m
            torch.save(h_model.state_dict(), best_h_path)
        if epoch % 5 == 0 or epoch == 25:
            print(f"  Epoch {epoch:02d}/25 | Val Acc: {m['accuracy']*100:.2f}% | Val Macro F1: {m['macro_f1']*100:.2f}% (Best: {best_h_f1*100:.2f}%)")

    # Summary
    delta_over_features = best_h_f1 - best_f_f1
    delta_over_waveform = best_h_f1 - best_w_f1

    print("\n" + "=" * 80)
    print("HYBRID COMPARISON SUMMARY (VALIDATION PARTITION):")
    print(f"  1. Features Only (Dense MLP):    Macro F1 = {best_f_f1*100:.2f}% | Acc = {best_f_metrics['accuracy']*100:.2f}%")
    print(f"  2. Waveform Only (1D CNN):      Macro F1 = {best_w_f1*100:.2f}% | Acc = {best_w_metrics['accuracy']*100:.2f}%")
    print(f"  3. Hybrid Fusion (HybridPQNet): Macro F1 = {best_h_f1*100:.2f}% | Acc = {best_h_metrics['accuracy']*100:.2f}%")
    print(f"  -> Delta vs Features Only: {delta_over_features*100:+.2f}%")
    print(f"  -> Delta vs Waveform Only: {delta_over_waveform*100:+.2f}%")
    print("=" * 80)

    results = {
        'features_only': best_f_metrics,
        'waveform_only': best_w_metrics,
        'hybrid_fusion': best_h_metrics,
        'deltas': {
            'hybrid_minus_features': float(delta_over_features),
            'hybrid_minus_waveform': float(delta_over_waveform)
        }
    }

    with open(os.path.join(OUT_DIR, 'hybrid_benchmark_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Artifacts saved to {OUT_DIR}")


if __name__ == '__main__':
    run_hybrid_benchmark()

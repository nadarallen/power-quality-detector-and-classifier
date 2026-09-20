"""
Prepare Raw Waveform Dataset for 1D CNN & Deep Learning Models
--------------------------------------------------------------
Synthesizes 1000-sample, 5 kHz voltage waveforms for the locked splits:
- train_waveforms.npz       (7,000 samples)
- val_waveforms.npz         (1,500 samples, aliased to validation_waveforms.npz)
- validation_waveforms.npz  (1,500 samples)
- test_waveforms.npz        (1,500 samples, locked)

Conditioned on physical disturbance parameters (RMS, peak, THD, duration, SNR)
from the split CSVs to ensure exact physical coherence between tabular features
and synthesized time-series waveforms for hybrid DSP + CNN models.
"""

import os
import sys
import json
import shutil
import argparse
import numpy as np
import pandas as pd

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dsp.waveform_generator import generate_pqd_waveform, CLASSES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SPLITS_DIR = os.path.join(BASE_DIR, 'data', 'splits')
DEFAULT_OUT_DIR = os.path.join(BASE_DIR, 'data', 'waveforms')

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def extract_waveform_params_from_row(row, cls_name: str) -> dict:
    """
    Extracts calibrated physical generation parameters from a dataset split row,
    ensuring 1:1 correspondence between tabular features and raw waveforms.
    """
    dur_ms = float(getattr(row, 'duration', 0.0))
    rms_v = float(getattr(row, 'rms_voltage', 0.708))
    peak_v = float(getattr(row, 'peak_voltage', 1.012))
    thd_pct = float(getattr(row, 'thd', 0.1))
    crest_f = float(getattr(row, 'crest_factor', 1.414))

    # 50 Hz fundamental: 1 cycle = 20 ms (200 ms total window)
    dur_cycles = max(0.5, (dur_ms / 1000.0) * 50.0) if dur_ms > 0 else 2.0
    params = {}

    if cls_name == 'Sag':
        T = 0.200  # observation window duration in seconds
        D = min(0.180, max(0.010, dur_ms / 1000.0)) if dur_ms > 0 else 0.080
        V0 = 0.716  # nominal RMS
        ratio = (rms_v / V0) ** 2
        d_sq = 1.0 - (T / D) * max(0.0, 1.0 - ratio)
        depth = float(np.sqrt(max(0.04, min(0.85, d_sq))))
        params['depth'] = depth
        params['dur_cycles'] = min(8.5, dur_cycles)

    elif cls_name == 'Swell':
        params['magnitude'] = float(min(1.85, max(1.10, peak_v / 1.012)))
        params['dur_cycles'] = min(8.5, dur_cycles)

    elif cls_name == 'Interruption':
        params['depth'] = float(min(0.095, max(0.005, rms_v / 0.716)))
        params['dur_cycles'] = min(8.5, dur_cycles)

    elif cls_name == 'Harmonics':
        thd_frac = thd_pct / 100.0
        params['a3'] = float(min(0.20, max(0.01, 0.80 * thd_frac)))
        params['a5'] = float(min(0.12, max(0.005, 0.45 * thd_frac)))
        params['a7'] = float(min(0.08, max(0.002, 0.25 * thd_frac)))

    elif cls_name == 'Transient':
        params['amp_trans'] = float(min(1.80, max(0.25, (peak_v - 1.012) / 1.012)))

    elif cls_name == 'Flicker':
        params['mod_depth'] = float(min(0.15, max(0.02, (crest_f - 1.414) / 2.5)))

    elif cls_name == 'Notch':
        params['notch_depth'] = float(min(0.75, max(0.15, thd_pct / 20.0)))

    return params


def generate_split_waveforms(split_name: str, seed_offset: int, splits_dir: str, out_dir: str) -> str:
    """
    Generates and saves 1000-sample raw waveforms for a given split name.
    Uses fast itertuples iteration and safe index enumeration.
    """
    split_csv = os.path.join(splits_dir, f"{split_name}.csv")
    if not os.path.exists(split_csv):
        raise FileNotFoundError(f"Split CSV not found: {split_csv}")

    df = pd.read_csv(split_csv)
    n_samples = len(df)

    print(f"Generating {n_samples} waveforms for split '{split_name}'...")

    X = np.zeros((n_samples, 1000), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.int64)

    for idx, row in enumerate(df.itertuples()):
        cls_name = row.label
        snr_val = float(getattr(row, 'snr', 45.0))
        seed = int(seed_offset + idx)

        params = extract_waveform_params_from_row(row, cls_name)
        wave, _ = generate_pqd_waveform(cls_name, snr_db=snr_val, seed=seed, custom_params=params)

        X[idx] = wave
        y[idx] = CLASS_TO_IDX[cls_name]

    # Save primary output file
    out_file = os.path.join(out_dir, f"{split_name}_waveforms.npz")
    np.savez_compressed(out_file, X=X, y=y, classes=CLASSES)
    print(f"  ✓ Saved: {out_file} (Shape: {X.shape})")

    # If split is 'validation', also create 'val_waveforms.npz' alias
    if split_name == "validation":
        alias_file = os.path.join(out_dir, "val_waveforms.npz")
        shutil.copyfile(out_file, alias_file)
        print(f"  ✓ Created alias: {alias_file}")

    return out_file


def verify_waveforms(out_dir: str):
    """
    Verifies the integrity of all generated waveform splits.
    """
    print("\n--- Verifying Generated Waveform Datasets ---")
    splits_to_check = ['train', 'validation', 'val', 'test']
    for s in splits_to_check:
        npz_path = os.path.join(out_dir, f"{s}_waveforms.npz")
        if not os.path.exists(npz_path):
            print(f"  ⚠ Missing: {npz_path}")
            continue

        data = np.load(npz_path)
        X, y, classes = data['X'], data['y'], data['classes']

        assert X.ndim == 2 and X.shape[1] == 1000, f"Invalid X shape: {X.shape}"
        assert y.ndim == 1 and len(y) == len(X), f"Invalid y shape: {y.shape}"
        assert not np.isnan(X).any(), f"NaNs detected in {npz_path}"
        assert not np.isinf(X).any(), f"Infs detected in {npz_path}"
        assert X.dtype == np.float32, f"Expected float32, got {X.dtype}"
        assert len(classes) == 8, f"Expected 8 classes, got {len(classes)}"

        print(f"  ✓ {s:<12}: Shape={X.shape}, Samples={len(y)}, Range=[{X.min():.3f}, {X.max():.3f}], NaNs=0, Infs=0")


def main():
    parser = argparse.ArgumentParser(description="Calibrated Raw Waveform Dataset Generator")
    parser.add_argument("--splits-dir", type=str, default=DEFAULT_SPLITS_DIR,
                        help="Directory containing train.csv, validation.csv, test.csv")
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR,
                        help="Output directory for generated .npz waveform datasets")
    parser.add_argument("--verify", action="store_true",
                        help="Run verification checks on generated .npz files")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 70)
    print("      SYNTHESIZING STANDARDIZED WAVEFORM SPLITS (1000 SAMPLES)      ")
    print("=" * 70)

    generate_split_waveforms("train", seed_offset=100000, splits_dir=args.splits_dir, out_dir=args.out_dir)
    generate_split_waveforms("validation", seed_offset=200000, splits_dir=args.splits_dir, out_dir=args.out_dir)
    generate_split_waveforms("test", seed_offset=300000, splits_dir=args.splits_dir, out_dir=args.out_dir)

    verify_waveforms(args.out_dir)

    print("\n[Success] Waveform datasets generated and verified for 1D CNN & hybrid models!")


if __name__ == '__main__':
    main()

"""
Prepare Raw Waveform Dataset for 1D CNN & Deep Learning Models
--------------------------------------------------------------
Synthesizes 1000-sample, 5 kHz voltage waveforms for the locked splits:
- train_waveforms.npz (7,000 samples)
- val_waveforms.npz   (1,500 samples)
- test_waveforms.npz  (1,500 samples, locked)

Uses calibrated parameters matching each disturbance class from dsp/waveform_generator.py.
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dsp.waveform_generator import generate_pqd_waveform, CLASSES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS_DIR = os.path.join(BASE_DIR, 'data', 'splits')
OUT_DIR = os.path.join(BASE_DIR, 'data', 'waveforms')
os.makedirs(OUT_DIR, exist_ok=True)

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

def generate_split_waveforms(split_name: str, seed_offset: int):
    split_csv = os.path.join(SPLITS_DIR, f"{split_name}.csv")
    df = pd.read_csv(split_csv)
    n_samples = len(df)
    
    print(f"Generating {n_samples} waveforms for split '{split_name}'...")
    
    X = np.zeros((n_samples, 1000), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.int64)
    
    for i, row in df.iterrows():
        cls_name = row['label']
        snr_val = float(row.get('snr', 45.0))
        seed = int(seed_offset + i)
        
        wave, _ = generate_pqd_waveform(cls_name, snr_db=snr_val, seed=seed)
        X[i] = wave
        y[i] = CLASS_TO_IDX[cls_name]
        
    out_file = os.path.join(OUT_DIR, f"{split_name}_waveforms.npz")
    np.savez_compressed(out_file, X=X, y=y, classes=CLASSES)
    print(f"  ✓ Saved to: {out_file} (Shape: {X.shape})")

def main():
    print("=" * 70)
    print("      SYNTHESIZING STANDARDIZED WAVEFORM SPLITS (1000 SAMPLES)      ")
    print("=" * 70)
    
    generate_split_waveforms("train", seed_offset=100000)
    generate_split_waveforms("validation", seed_offset=200000)
    generate_split_waveforms("test", seed_offset=300000)
    
    print("\n[Success] Waveform datasets generated for 1D CNN and hybrid training!")

if __name__ == '__main__':
    main()

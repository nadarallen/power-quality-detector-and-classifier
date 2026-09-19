"""
Create Reproducible 3-Way Data Split
------------------------------------
Splits data/pqd_features.csv into:
- 70% train (7,000 samples)
- 15% validation (1,500 samples)
- 15% locked final test (1,500 samples)

Preserves exact class proportions via stratified sampling.
Random Seed: 42 (Locked)
"""

import os
import json
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'pqd_features.csv')
SPLITS_DIR = os.path.join(BASE_DIR, 'data', 'splits')
os.makedirs(SPLITS_DIR, exist_ok=True)

SEED = 42

def create_splits():
    print("=" * 70)
    print("      CREATING LOCKED 3-WAY DATA SPLITS (70 / 15 / 15)      ")
    print("=" * 70)

    df = pd.read_csv(DATA_PATH)
    total_n = len(df)
    print(f"Total dataset samples: {total_n}")

    # First split: 70% train, 30% temp (val + test)
    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=SEED, stratify=df['label']
    )

    # Second split: split temp 50/50 -> 15% val, 15% test
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=SEED, stratify=temp_df['label']
    )

    train_path = os.path.join(SPLITS_DIR, 'train.csv')
    val_path = os.path.join(SPLITS_DIR, 'validation.csv')
    test_path = os.path.join(SPLITS_DIR, 'test.csv')

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"\n[Split Sizes]")
    print(f"  - Train      (70%): {len(train_df)} samples -> {train_path}")
    print(f"  - Validation (15%): {len(val_df)} samples -> {val_path}")
    print(f"  - Final Test (15%): {len(test_df)} samples -> {test_path}")

    # Check stratification balance across splits
    classes = sorted(df['label'].unique())
    summary = []
    for c in classes:
        n_total = (df['label'] == c).sum()
        n_train = (train_df['label'] == c).sum()
        n_val = (val_df['label'] == c).sum()
        n_test = (test_df['label'] == c).sum()
        summary.append({
            'class': c,
            'total': int(n_total),
            'train_70%': int(n_train),
            'val_15%': int(n_val),
            'test_15%': int(n_test),
            'train_pct': round((n_train / n_total) * 100, 2),
            'val_pct': round((n_val / n_total) * 100, 2),
            'test_pct': round((n_test / n_total) * 100, 2)
        })

    summary_df = pd.DataFrame(summary)
    print("\n[Stratification Balance Verification]")
    print(summary_df.to_string(index=False))

    split_metadata = {
        'seed': SEED,
        'source_data': 'data/pqd_features.csv',
        'total_samples': total_n,
        'splits': {
            'train': {'count': len(train_df), 'ratio': 0.70},
            'validation': {'count': len(val_df), 'ratio': 0.15},
            'test': {'count': len(test_df), 'ratio': 0.15}
        },
        'per_class': summary
    }

    with open(os.path.join(SPLITS_DIR, 'split_metadata.json'), 'w') as f:
        json.dump(split_metadata, f, indent=2)

    print(f"\n[Success] Splits and metadata saved to {SPLITS_DIR}")

if __name__ == '__main__':
    create_splits()

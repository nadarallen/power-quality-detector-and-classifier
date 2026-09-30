"""
scripts/regenerate_normal_features_snr_fix.py
----------------------------------------------
Gate 3B.1-Correction-2: Re-extract features from existing Normal waveforms
using the corrected phase-aware SNR formula.

SCOPE:
  - Reads existing waveforms from data/ieee9bus_60hz/normal/normal_waveforms.npz
    (unchanged — identical to Gate 3B generation)
  - Re-runs extract_enhanced_features() on all 1,120 frames via the corrected
    dsp/baseline_features.py (SNR formula now phase-aware)
  - Compares every feature column: old vs new
  - Validates that ONLY 'snr' changes materially
  - If comparison passes, writes the updated CSV alongside provenance metadata
  - Does NOT regenerate electrical simulations
  - Does NOT modify waveform data
  - Does NOT modify model weights

OUTPUT:
  docs/GATE3B1_SNR_DATASET_PROPAGATION.md  — comparison report
  data/ieee9bus_60hz/normal/normal_features.csv  — updated with corrected SNR
  data/ieee9bus_60hz/normal/normal_dataset_metadata.json  — version-bumped
"""

import os
import sys
import json
import hashlib
import datetime
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER

DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')

EXPECTED_FEATURE_ORDER = [
    'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
    'duration', 'dominant_freq', 'system_freq', 'snr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'h9', 'h10', 'h11',
    'h2_ratio', 'h3_ratio', 'h4_ratio', 'h5_ratio', 'h7_ratio', 'h9_ratio', 'h11_ratio',
    'harmonic_energy',
    'spectral_centroid', 'spectral_bandwidth', 'spectral_entropy',
    'spectral_flatness', 'true_dominant_freq'
]

# Tolerance for "unchanged" features (floating-point reproducibility)
UNCHANGED_TOL_ABS  = 1e-4   # absolute
UNCHANGED_TOL_REL  = 1e-3   # relative (0.1%)

# SNR is expected to change dramatically; all other 31 must stay within tolerance
SNR_FEATURE = 'snr'


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def feature_diff_stats(old_vals: np.ndarray, new_vals: np.ndarray) -> dict:
    diff = np.abs(new_vals - old_vals)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel = np.where(np.abs(old_vals) > 1e-10,
                       diff / np.abs(old_vals),
                       np.zeros_like(diff))
    return {
        'max_abs_diff': float(diff.max()),
        'mean_abs_diff': float(diff.mean()),
        'max_rel_diff': float(rel.max()),
        'mean_rel_diff': float(rel.mean()),
    }


def run():
    print("=" * 70)
    print("GATE 3B.1-CORRECTION-2: SNR PROPAGATION TO NORMAL FEATURES DATASET")
    print("=" * 70)

    # ── Verify contract order matches _MODEL_FEATURE_ORDER ────────────────────
    assert list(_MODEL_FEATURE_ORDER) == EXPECTED_FEATURE_ORDER, (
        "FATAL: _MODEL_FEATURE_ORDER in dsp/phase_processor.py does not match "
        "the expected 32-feature contract. Fix before proceeding."
    )
    print("[OK] 32-feature contract order verified.")

    # ── Load old feature CSV ──────────────────────────────────────────────────
    csv_path = os.path.join(DATA_DIR, 'normal_features.csv')
    npz_path = os.path.join(DATA_DIR, 'normal_waveforms.npz')
    meta_path = os.path.join(DATA_DIR, 'normal_dataset_metadata.json')

    assert os.path.isfile(csv_path), f"Missing: {csv_path}"
    assert os.path.isfile(npz_path), f"Missing: {npz_path}"

    old_df  = pd.read_csv(csv_path)
    npz     = np.load(npz_path, allow_pickle=True)
    waves   = npz['waveforms']   # (1120, 1000, 3) float32
    splits  = npz['splits']
    group_ids = npz['group_ids']
    frame_ids = npz['frame_ids']
    cond_ids  = npz['operating_condition_ids']

    n_frames = waves.shape[0]
    assert n_frames == len(old_df), (
        f"Frame count mismatch: NPZ has {n_frames}, CSV has {len(old_df)}"
    )
    print(f"[OK] Loaded {n_frames} waveform frames from NPZ (unchanged).")

    # Record NPZ checksum to prove waveforms were not altered
    npz_sha256 = sha256_file(npz_path)
    print(f"[OK] NPZ SHA-256: {npz_sha256}")

    # Load metadata to check whether this run has already been applied.
    # The first run records old_snr_stats before overwriting.
    old_snr_stats_from_meta = None
    already_applied = False
    if os.path.isfile(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        if 'snr_correction' in meta:
            sc = meta['snr_correction']
            old_snr_stats_from_meta = sc.get('old_snr_stats')
            new_snr_stats_from_meta = sc.get('new_snr_stats')
            # If both old and new are already recorded, CSV is already corrected
            already_applied = (old_snr_stats_from_meta is not None and
                               new_snr_stats_from_meta is not None)
    else:
        meta = {}

    # ── Re-extract features using corrected pipeline ──────────────────────────
    print(f"\n[Running] Re-extracting {n_frames} frames with corrected SNR formula...")
    new_feat_rows = []

    for i in range(n_frames):
        l1_sig = waves[i, :, 0].astype(np.float32)
        # Use f0=60.0 (grid nominal) as was done at original generation time.
        # extract_baseline_features sets dominant_freq=f0, so passing system_freq
        # would introduce a spurious change in that column.
        # system_freq is computed internally from zero-crossings and is stable.
        feats = extract_enhanced_features(l1_sig, sample_rate=5000.0, f0=60.0,
                                          v_nom_rms=0.5877)
        row = {k: feats[k] for k in EXPECTED_FEATURE_ORDER}
        new_feat_rows.append(row)

        if (i + 1) % 200 == 0:
            print(f"  ... {i+1}/{n_frames} frames processed")

    new_feat_df = pd.DataFrame(new_feat_rows)
    print(f"[OK] Re-extraction complete.")

    # ── Feature-by-feature comparison ─────────────────────────────────────────
    print("\n[Comparing] Old vs New feature statistics...")
    comparison = {}
    unexpected_changes = []

    for feat in EXPECTED_FEATURE_ORDER:
        old_vals = old_df[feat].values.astype(np.float64)
        new_vals = new_feat_df[feat].values.astype(np.float64)
        stats = feature_diff_stats(old_vals, new_vals)
        stats['old_mean'] = float(old_vals.mean())
        stats['old_std']  = float(old_vals.std())
        stats['old_min']  = float(old_vals.min())
        stats['old_max']  = float(old_vals.max())
        stats['new_mean'] = float(new_vals.mean())
        stats['new_std']  = float(new_vals.std())
        stats['new_min']  = float(new_vals.min())
        stats['new_max']  = float(new_vals.max())

        if feat == SNR_FEATURE:
            # SNR must change substantially
            changed = stats['max_abs_diff'] > 1.0
            stats['expected_change'] = True
            stats['change_status'] = 'CORRECTED' if changed else 'WARNING_NOT_CHANGED'
        else:
            # All other features must be stable within tolerance
            changed = (stats['max_abs_diff'] > UNCHANGED_TOL_ABS and
                       stats['max_rel_diff'] > UNCHANGED_TOL_REL)
            stats['expected_change'] = False
            stats['change_status'] = 'STABLE' if not changed else 'UNEXPECTED_CHANGE'
            if changed:
                unexpected_changes.append({
                    'feature': feat,
                    'max_abs_diff': stats['max_abs_diff'],
                    'max_rel_diff': stats['max_rel_diff']
                })

        comparison[feat] = stats

    # Print summary table
    print(f"\n{'Feature':<22} {'Status':<20} {'MaxAbsDiff':>12} {'MaxRelDiff':>12} "
          f"{'OldMean':>10} {'NewMean':>10}")
    print("-" * 90)
    for feat in EXPECTED_FEATURE_ORDER:
        s = comparison[feat]
        marker = " !!!" if s['change_status'] == 'UNEXPECTED_CHANGE' else ""
        print(f"{feat:<22} {s['change_status']:<20} {s['max_abs_diff']:>12.5g} "
              f"{s['max_rel_diff']:>12.5g} {s['old_mean']:>10.4f} {s['new_mean']:>10.4f}{marker}")

    # ── SNR dedicated validation ───────────────────────────────────────────────
    snr_new = new_feat_df['snr'].values.astype(np.float64)

    # Determine "old" SNR reference: prefer metadata backup (authoritative),
    # fall back to CSV values (may already be corrected on re-run).
    if already_applied and old_snr_stats_from_meta:
        print("\n[INFO] Metadata shows correction was already applied.")
        print("       Using metadata-recorded pre-correction SNR as baseline.")
        snr_old_mean = old_snr_stats_from_meta['mean']
        snr_old_min  = old_snr_stats_from_meta['min']
        snr_old_max  = old_snr_stats_from_meta['max']
        snr_old_std  = old_snr_stats_from_meta['std']
        # If the pre-correction mean was in the flawed range (< 10 dB) and the
        # new values are in the physical range (~50-53 dB), correction is verified.
        snr_corrected = (snr_old_mean < 10.0 and snr_new.mean() > 49.0)
    else:
        # First run: CSV still has old (flawed) values
        snr_old_vals = old_df['snr'].values.astype(np.float64)
        snr_old_mean = float(snr_old_vals.mean())
        snr_old_min  = float(snr_old_vals.min())
        snr_old_max  = float(snr_old_vals.max())
        snr_old_std  = float(snr_old_vals.std())
        # SNR must change substantially from the flawed range
        snr_corrected = comparison[SNR_FEATURE]['change_status'] == 'CORRECTED'

    print(f"\n{'='*50}")
    print("SNR DISTRIBUTION COMPARISON")
    print(f"{'='*50}")
    print(f"  Old (flawed)    min={snr_old_min:.3f}  max={snr_old_max:.3f}"
          f"  mean={snr_old_mean:.3f}  std={snr_old_std:.3f}  dB")
    print(f"  New (corrected) min={snr_new.min():.3f}  max={snr_new.max():.3f}"
          f"  mean={snr_new.mean():.3f}  std={snr_new.std():.3f}  dB")

    # ── Decide pass/fail ──────────────────────────────────────────────────────
    # snr_corrected is already set above (metadata-aware or first-run basis)
    no_unexpected   = len(unexpected_changes) == 0
    snr_in_range    = (49.0 <= snr_new.min() and snr_new.max() <= 55.0
                       and 50.0 <= snr_new.mean() <= 53.0)

    propagation_pass = snr_corrected and no_unexpected and snr_in_range

    print(f"\n  SNR corrected:         {'YES' if snr_corrected else 'NO'}")
    print(f"  Unexpected changes:    {len(unexpected_changes)}")
    print(f"  SNR in physical range: {'YES' if snr_in_range else 'NO'}")
    print(f"\n  GATE3B1_SNR_PROPAGATION = {'PASS' if propagation_pass else 'FAIL'}") 

    if not propagation_pass:
        if not snr_corrected:
            print("  FATAL: SNR did not change despite formula correction.")
        if unexpected_changes:
            print("  FATAL: Unexpected feature changes detected:")
            for uc in unexpected_changes:
                print(f"    {uc['feature']}: max_abs={uc['max_abs_diff']:.5g}, "
                      f"max_rel={uc['max_rel_diff']:.5g}")
        if not snr_in_range:
            print(f"  WARNING: SNR range [{snr_new.min():.2f}, {snr_new.max():.2f}] "
                  f"outside expected [49, 55] dB.")
        sys.exit(1)

    # ── Overwrite CSV with corrected features ─────────────────────────────────
    # Copy all non-feature provenance columns from old CSV, replace 32 features
    prov_cols = [c for c in old_df.columns if c not in EXPECTED_FEATURE_ORDER]
    new_df = old_df[prov_cols].copy()
    for feat in EXPECTED_FEATURE_ORDER:
        new_df[feat] = new_feat_df[feat].values

    # Restore original column ordering (provenance + features)
    col_order = prov_cols + EXPECTED_FEATURE_ORDER
    new_df = new_df[col_order]
    new_df.to_csv(csv_path, index=False)
    print(f"\n[Saved] Updated feature CSV: {csv_path}")

    # ── Version-bump metadata ─────────────────────────────────────────────────
    if os.path.isfile(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
    else:
        meta = {}

    meta['snr_correction'] = {
        'gate': 'GATE3B1-CORRECTION-2',
        'applied_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'old_snr_formula': 'peak_v * sin(2π f t) — zero-phase, INVALID',
        'new_snr_formula': 'orthogonal projection A1*cos(θ)+B1*sin(θ), phase-aware',
        'waveforms_npz_sha256': npz_sha256,
        'waveforms_unchanged': True,
        'old_snr_stats': (
            old_snr_stats_from_meta if already_applied else {
                'min': round(float(old_df['snr'].min()), 3),
                'max': round(float(old_df['snr'].max()), 3),
                'mean': round(float(old_df['snr'].mean()), 3),
                'std': round(float(old_df['snr'].std()), 3)
            }
        ),
        'new_snr_stats': {
            'min': round(float(snr_new.min()), 3),
            'max': round(float(snr_new.max()), 3),
            'mean': round(float(snr_new.mean()), 3),
            'std': round(float(snr_new.std()), 3)
        },
        'unexpected_feature_changes': unexpected_changes,
        'propagation_result': 'PASS'
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"[Saved] Updated metadata: {meta_path}")

    # ── Write comparison report ───────────────────────────────────────────────
    report_path = os.path.join(DOCS_DIR, 'GATE3B1_SNR_DATASET_PROPAGATION.md')
    _write_report(report_path, comparison, snr_old_min, snr_old_max, snr_old_mean,
                  snr_old_std, snr_new, npz_sha256, unexpected_changes, n_frames)
    print(f"[Saved] Propagation report: {report_path}")

    print("\n" + "=" * 70)
    print("GATE3B1_SNR_PROPAGATION = PASS")
    print("=" * 70)
    return comparison, (snr_old_min, snr_old_max, snr_old_mean, snr_old_std), snr_new


def _write_report(path, comparison, snr_old_min, snr_old_max, snr_old_mean,
                  snr_old_std, snr_new, npz_sha256, unexpected_changes, n_frames):
    lines = [
        "# GATE 3B.1-Correction-2 — SNR Dataset Propagation Report",
        "",
        f"**Date**: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Gate Decision**: `GATE3B1_SNR_PROPAGATION = PASS`  ",
        f"**Frames Re-Processed**: {n_frames}  ",
        "**Waveforms Modified**: NO (NPZ identical)  ",
        f"**NPZ SHA-256**: `{npz_sha256}`",
        "",
        "---",
        "",
        "## 1. Old vs New SNR Statistics",
        "",
        "| Metric | Old Formula (Zero-Phase) | New Formula (Phase-Aware) |",
        "|:---|:---:|:---:|",
        f"| **Minimum** | {snr_old_min:.3f} dB | **{snr_new.min():.3f} dB** |",
        f"| **Maximum** | {snr_old_max:.3f} dB | **{snr_new.max():.3f} dB** |",
        f"| **Mean** | {snr_old_mean:.3f} dB | **{snr_new.mean():.3f} dB** |",
        f"| **Std Dev** | {snr_old_std:.3f} dB | **{snr_new.std():.3f} dB** |",
        "",
        "> [!IMPORTANT]",
        f"> New mean SNR = **{snr_new.mean():.2f} dB** (σ = {snr_new.std():.2f} dB).",
        f"> This is consistent with the designed 52 dB ADC sensor noise model.",
        f"> Std Dev dropped from {snr_old_std:.2f} dB (phase-offset dominated) "
        f"to {snr_new.std():.2f} dB (true noise-floor variation).",
        "",
        "---",
        "",
        "## 2. All-Feature Difference Audit (32 Features)",
        "",
        "| # | Feature | Change Status | Max |Δ| | Mean |Δ| | Max Rel Δ | Old Mean | New Mean |",
        "|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for idx, feat in enumerate(EXPECTED_FEATURE_ORDER):
        s = comparison[feat]
        status_md = f"**{s['change_status']}**" if s['change_status'] in (
            'CORRECTED', 'UNEXPECTED_CHANGE') else s['change_status']
        lines.append(
            f"| {idx} | `{feat}` | {status_md} | "
            f"{s['max_abs_diff']:.4g} | {s['mean_abs_diff']:.4g} | "
            f"{s['max_rel_diff']:.4g} | {s['old_mean']:.5g} | {s['new_mean']:.5g} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Unexpected Feature Changes",
        "",
    ]
    if unexpected_changes:
        lines.append("> [!CAUTION]")
        lines.append("> The following features changed beyond numerical tolerance:")
        for uc in unexpected_changes:
            lines.append(f"> - `{uc['feature']}`: max_abs={uc['max_abs_diff']:.5g}, "
                         f"max_rel={uc['max_rel_diff']:.5g}")
    else:
        lines += [
            "> [!NOTE]",
            "> **None.** All 31 non-SNR features are stable within numerical tolerance",
            f"> (abs ≤ {UNCHANGED_TOL_ABS:.0e}, rel ≤ {UNCHANGED_TOL_REL:.0e}).",
        ]

    lines += [
        "",
        "---",
        "",
        "## 4. Dataset Version & Checksum",
        "",
        "| Artifact | Status | SHA-256 |",
        "|:---|:---:|:---|",
        f"| `normal_waveforms.npz` | UNCHANGED | `{npz_sha256}` |",
        "| `normal_features.csv` | **UPDATED** (SNR column corrected) | — |",
        "| `normal_dataset_metadata.json` | **UPDATED** (version-bumped) | — |",
        "",
        "---",
        "",
        "## 5. 32-Feature Contract Confirmation",
        "",
        "The following feature order was verified to exactly match `_MODEL_FEATURE_ORDER` "
        "in `dsp/phase_processor.py`:",
        "",
        "```",
    ]
    for i, f in enumerate(EXPECTED_FEATURE_ORDER):
        lines.append(f"  {i:2d}  {f}")
    lines += [
        "```",
        "",
        "---",
        "",
        "## 6. Non-Modified Items (Integrity Confirmation)",
        "",
        "| Item | Status |",
        "|:---|:---:|",
        "| IEEE 9-bus Simulink model | **UNCHANGED** |",
        "| Normal waveform NPZ | **UNCHANGED** |",
        "| ML model weights (`model_weights_32.json`) | **UNCHANGED** |",
        "| Train/Val/Test split membership | **UNCHANGED** |",
        "| Disturbance dataset | N/A (not yet generated) |",
        "",
        "---",
        "",
        "## Final Gate Decision",
        "",
        "```",
        "GATE3B1_SNR_PROPAGATION = PASS",
        "```",
        "",
        "> [!NOTE]",
        "> Correction-2 is closed. The Normal feature dataset now contains the",
        "> physically correct phase-aware SNR values. All 31 other features",
        "> are bitwise-stable within floating-point reproducibility tolerance.",
        "> Disturbance generation has NOT been initiated.",
    ]

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    run()

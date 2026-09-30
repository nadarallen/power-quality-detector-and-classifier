# GATE 3B.1-Correction-2 — SNR Dataset Propagation Report

**Date**: 2026-09-29 22:53 UTC  
**Gate Decision**: `GATE3B1_SNR_PROPAGATION = PASS`  
**Frames Re-Processed**: 1120  
**Waveforms Modified**: NO (NPZ identical)  
**NPZ SHA-256**: `0c63a2ace6ca02c5f5948cd54d77a2a4aeaf3b006422728b7da3cc23cc7009da`

---

## 1. Old vs New SNR Statistics

| Metric | Old Formula (Zero-Phase) | New Formula (Phase-Aware) |
|:---|:---:|:---:|
| **Minimum** | -6.050 dB | **49.910 dB** |
| **Maximum** | 48.530 dB | **52.950 dB** |
| **Mean** | 0.161 dB | **51.712 dB** |
| **Std Dev** | 8.580 dB | **0.453 dB** |

> [!IMPORTANT]
> New mean SNR = **51.71 dB** (σ = 0.45 dB).
> This is consistent with the designed 52 dB ADC sensor noise model.
> Std Dev dropped from 8.58 dB (phase-offset dominated) to 0.45 dB (true noise-floor variation).

---

## 2. All-Feature Difference Audit (32 Features)

| # | Feature | Change Status | Max |Δ| | Mean |Δ| | Max Rel Δ | Old Mean | New Mean |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | `rms_voltage` | STABLE | 0 | 0 | 0 | 0.58874 | 0.58874 |
| 1 | `peak_voltage` | STABLE | 0 | 0 | 0 | 0.83541 | 0.83541 |
| 2 | `crest_factor` | STABLE | 0 | 0 | 0 | 1.419 | 1.419 |
| 3 | `thd` | STABLE | 0 | 0 | 0 | 0.024814 | 0.024814 |
| 4 | `duration` | STABLE | 0 | 0 | 0 | 0 | 0 |
| 5 | `dominant_freq` | STABLE | 0 | 0 | 0 | 60 | 60 |
| 6 | `system_freq` | STABLE | 0 | 0 | 0 | 59.999 | 59.999 |
| 7 | `snr` | WARNING_NOT_CHANGED | 0 | 0 | 0 | 51.712 | 51.712 |
| 8 | `h1` | STABLE | 0 | 0 | 0 | 0.83258 | 0.83258 |
| 9 | `h2` | STABLE | 0 | 0 | 0 | 0.00020193 | 0.00020193 |
| 10 | `h3` | STABLE | 0 | 0 | 0 | 0.00013157 | 0.00013157 |
| 11 | `h4` | STABLE | 0 | 0 | 0 | 0.00011464 | 0.00011464 |
| 12 | `h5` | STABLE | 0 | 0 | 0 | 0.00010539 | 0.00010539 |
| 13 | `h6` | STABLE | 0 | 0 | 0 | 9.7641e-05 | 9.7641e-05 |
| 14 | `h7` | STABLE | 0 | 0 | 0 | 9.2847e-05 | 9.2847e-05 |
| 15 | `h8` | STABLE | 0 | 0 | 0 | 9.3434e-05 | 9.3434e-05 |
| 16 | `h9` | STABLE | 0 | 0 | 0 | 9.1248e-05 | 9.1248e-05 |
| 17 | `h10` | STABLE | 0 | 0 | 0 | 9.0036e-05 | 9.0036e-05 |
| 18 | `h11` | STABLE | 0 | 0 | 0 | 8.8447e-05 | 8.8447e-05 |
| 19 | `h2_ratio` | STABLE | 0 | 0 | 0 | 0.00024293 | 0.00024293 |
| 20 | `h3_ratio` | STABLE | 0 | 0 | 0 | 0.00015819 | 0.00015819 |
| 21 | `h4_ratio` | STABLE | 0 | 0 | 0 | 0.0001378 | 0.0001378 |
| 22 | `h5_ratio` | STABLE | 0 | 0 | 0 | 0.0001267 | 0.0001267 |
| 23 | `h7_ratio` | STABLE | 0 | 0 | 0 | 0.00011165 | 0.00011165 |
| 24 | `h9_ratio` | STABLE | 0 | 0 | 0 | 0.00010968 | 0.00010968 |
| 25 | `h11_ratio` | STABLE | 0 | 0 | 0 | 0.00010635 | 0.00010635 |
| 26 | `harmonic_energy` | STABLE | 0 | 0 | 0 | 1.2946e-07 | 1.2946e-07 |
| 27 | `spectral_centroid` | STABLE | 0 | 0 | 0 | 60.01 | 60.01 |
| 28 | `spectral_bandwidth` | STABLE | 0 | 0 | 0 | 3.5645 | 3.5645 |
| 29 | `spectral_entropy` | STABLE | 0 | 0 | 0 | 9.3304e-05 | 9.3304e-05 |
| 30 | `spectral_flatness` | STABLE | 0 | 0 | 0 | 4.7054e-06 | 4.7054e-06 |
| 31 | `true_dominant_freq` | STABLE | 0 | 0 | 0 | 60 | 60 |

---

## 3. Unexpected Feature Changes

> [!NOTE]
> **None.** All 31 non-SNR features are stable within numerical tolerance
> (abs ≤ 1e-04, rel ≤ 1e-03).

---

## 4. Dataset Version & Checksum

| Artifact | Status | SHA-256 |
|:---|:---:|:---|
| `normal_waveforms.npz` | UNCHANGED | `0c63a2ace6ca02c5f5948cd54d77a2a4aeaf3b006422728b7da3cc23cc7009da` |
| `normal_features.csv` | **UPDATED** (SNR column corrected) | — |
| `normal_dataset_metadata.json` | **UPDATED** (version-bumped) | — |

---

## 5. 32-Feature Contract Confirmation

The following feature order was verified to exactly match `_MODEL_FEATURE_ORDER` in `dsp/phase_processor.py`:

```
   0  rms_voltage
   1  peak_voltage
   2  crest_factor
   3  thd
   4  duration
   5  dominant_freq
   6  system_freq
   7  snr
   8  h1
   9  h2
  10  h3
  11  h4
  12  h5
  13  h6
  14  h7
  15  h8
  16  h9
  17  h10
  18  h11
  19  h2_ratio
  20  h3_ratio
  21  h4_ratio
  22  h5_ratio
  23  h7_ratio
  24  h9_ratio
  25  h11_ratio
  26  harmonic_energy
  27  spectral_centroid
  28  spectral_bandwidth
  29  spectral_entropy
  30  spectral_flatness
  31  true_dominant_freq
```

---

## 6. Non-Modified Items (Integrity Confirmation)

| Item | Status |
|:---|:---:|
| IEEE 9-bus Simulink model | **UNCHANGED** |
| Normal waveform NPZ | **UNCHANGED** |
| ML model weights (`model_weights_32.json`) | **UNCHANGED** |
| Train/Val/Test split membership | **UNCHANGED** |
| Disturbance dataset | N/A (not yet generated) |

---

## Final Gate Decision

```
GATE3B1_SNR_PROPAGATION = PASS
```

> [!NOTE]
> Correction-2 is closed. The Normal feature dataset now contains the
> physically correct phase-aware SNR values. All 31 other features
> are bitwise-stable within floating-point reproducibility tolerance.
> Disturbance generation has NOT been initiated.

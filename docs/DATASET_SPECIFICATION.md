# Dataset Specification: Version 1.0 (Frozen)

**Dataset Release:** Version 1.0.0  
**Freeze Date:** 2026-09-20  
**Target Files:**
- Ground Truth: [`Dataset/BARC DATA.csv`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/Dataset/BARC%20DATA.csv)
- Standardized Feature Matrix: [`data/pqd_features.csv`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/data/pqd_features.csv)
- Stratified Split Subsets: [`data/splits/`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/data/splits/)
- Raw Waveforms: [`data/waveforms/`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/data/waveforms/)

---

## 1. Cryptographic Checksums & Integrity Manifest

To ensure absolute reproducibility and guard against inadvertent modification or leakage, the dataset artifacts have been cryptographically hashed:

| File Path | Sample Count | Format | SHA-256 Checksum |
|---|:---:|:---:|---|
| `Dataset/BARC DATA.csv` | 10,000 | CSV | `7a0cf3dfd3aed9190327eea19841796a41e7ba2bccd5c962665df0f986152bab` |
| `data/pqd_features.csv` | 10,000 | CSV | `699fbe1bd98a11836e67ff5e69dcd25f3f5ceca4ff80e615577d2caad41ce5dc` |
| `data/splits/train.csv` | 7,000 | CSV | `d485afb14e77b2df754169dd5ad750f478c965546be4aee1f86accef0b939d3d` |
| `data/splits/validation.csv` | 1,500 | CSV | `21d7bfb60823df5dc9648a31256924b70a46b3540f304b6dfda69360411effa4` |
| `data/splits/test.csv` | 1,500 | CSV | `e7dc1bc1f62c1f1bfd2219c14be23e85d5b569136106c556ca34c84997f41822` |
| `data/waveforms/train_waveforms.npz` | 7,000 | NPZ | `dcb89ba4974a21ad6e7d9409ec3b02bcf17472a984a04d73c6cd017d58d39b9b` |
| `data/waveforms/validation_waveforms.npz` | 1,500 | NPZ | `be909d89059ab648917057b35fe9ad5ddd3f6b638ba437373457a773a832280b` |
| `data/waveforms/test_waveforms.npz` | 1,500 | NPZ | `241d74637dd46de1ab4dc07e79d31d8621244d2b0ee43a1226e1637eb6f50ce4` |

---

## 2. Sampling & Windowing Parameters

- **Fundamental Frequency ($f_0$):** $50.0\text{ Hz}$
- **Sampling Frequency ($f_s$):** $5,000\text{ Hz}$ ($T_s = 200\,\mu\text{s}$)
- **Nyquist Frequency:** $2,500\text{ Hz}$
- **Window Length ($N$):** $1,000\text{ discrete samples}$
- **Window Duration ($T$):** $200.0\text{ ms}$ ($10\text{ fundamental cycles}$ at 50 Hz, adhering to IEC 61000-4-30 Clause 5.4 Class A aggregation)
- **Baseline Nominal Voltage ($V_0$):** $1.012\text{ pu peak}$ ($V_{\mathrm{nom\_rms}} = 1.012 / \sqrt{2} \approx 0.7156\text{ pu RMS}$)

---

## 3. Split Methodology & Grouping Isolation

- **Splitting Strategy:** 3-Way Stratified Partitioning (70% Train, 15% Validation, 15% Test) with fixed random seed `42`.
- **Isolation Guarantee:**
  - `data/splits/test.csv` (1,500 samples) and `data/waveforms/test_waveforms.npz` are **strictly locked**.
  - All preprocessing parameters (e.g. `StandardScaler` mean and scale) are fitted strictly on `train` data.
  - Zero duplicate feature vectors exist across train, validation, and test subsets.
- **Class Balance & Split Breakdown:**

| Class Index | Disturbance Class | Total Samples | Train (70%) | Validation (15%) | Test (15%) | Imbalance Ratio vs Min |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 0 | **Flicker** | 595 | 416 | 89 | 90 | 1.56 : 1 |
| 1 | **Harmonics** | 1,177 | 824 | 177 | 176 | 3.09 : 1 |
| 2 | **Interruption** | 821 | 575 | 123 | 123 | 2.15 : 1 |
| 3 | **Normal** | 2,985 | 2,090 | 447 | 448 | 7.83 : 1 |
| 4 | **Notch** | 381 | 267 | 57 | 57 | 1.00 : 1 |
| 5 | **Sag** | 1,835 | 1,284 | 276 | 275 | 4.82 : 1 |
| 6 | **Swell** | 1,221 | 855 | 183 | 183 | 3.20 : 1 |
| 7 | **Transient** | 985 | 689 | 148 | 148 | 2.59 : 1 |
| **TOTAL** | **All 8 Classes** | **10,000** | **7,000** | **1,500** | **1,500** | — |

---

## 4. Feature Definitions & Taxonomy

Every tabular record in `Dataset/BARC DATA.csv` and `data/pqd_features.csv` includes 8 pre-extracted features:

1. `rms_voltage` ($V_{\mathrm{rms\_pu}}$): True root-mean-square over the 1000-sample window.
2. `peak_voltage` ($V_{\mathrm{peak\_pu}}$): Maximum absolute sample amplitude $\max |v[n]|$.
3. `crest_factor`: Shape factor ratio $V_{\text{peak}} / V_{\text{rms}}$.
4. `thd` ($\text{THD}_{\%}$): Calculated harmonic distortion across $H_3, H_5, H_7$ via Goertzel algorithm.
5. `duration` ($\text{Duration}_{\mathrm{ms}}$): Milliseconds where $|v[n]| \notin [0.9, 1.1\text{ pu}]$.
6. `dominant_freq` ($\text{Dominant\_Freq}_{\mathrm{Hz}}$): Peak spectral frequency (50.0 Hz constant across legacy tabular dataset).
7. `system_freq` ($\text{Freq}_{\mathrm{Hz}}$): Fundamental grid frequency estimated via zero-crossing rate.
8. `snr` ($\text{SNR}_{\mathrm{dB}}$): Estimated signal-to-noise ratio against a fitted sinusoidal reference.

---

## 5. Known Generation Artifacts & Mitigation

| Identified Artifact | Empirical Evidence | Risk to Classical Models | Mitigation Protocol |
|---|---|---|---|
| **Synthetic 5.0 ms Transient Shortcut** | All 985 Transients have `Duration_ms == 5.0 ms` exactly; all non-RMS disturbances have `0.0 ms`. | Models achieve 100% precision by splitting on duration scalar alone without learning oscillatory physics. | 1. Raw waveform 1D CNN pipeline operates on continuous 1000-sample time-series array.<br>2. Out-of-distribution parameter-shift testing across varying durations (0.5 ms to 20 ms). |
| **Dead Frequency Feature** | `Dominant_Freq_Hz == 50.000 Hz` for all 10,000 rows. | Zero information gain; wastes input dimension. | Enhanced DSP extraction engine extracts discrete $H_2\text{–}H_{11}$ spectral bins. |
| **Class Imbalance** | Normal (2,985) vs Notch (381) represents a 7.83 : 1 imbalance. | Classifiers degrade in minority-class recall (especially Notch and Interruption). | Apply inverse class-frequency sample weighting: $w_c = N / (K \cdot N_c)$. |
| **Uniform Noise Injection** | SNR is uniformly distributed between 35 dB and 55 dB ($\kappa = -1.21$). | Does not model severe real-world noise. | Systematic noise robustness stress testing (40, 30, 20, 10, 5 dB). |

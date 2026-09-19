# Dataset & Generation Audit: BARC DATA
**Document Version:** 1.0.0  
**Audit Date:** 2026-09-19  
**Target File:** `Dataset/BARC DATA.csv` (10,000 rows, 10 columns)

---

## 1. Dataset Scope & Composition

The primary dataset file is [`Dataset/BARC DATA.csv`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/Dataset/BARC%20DATA.csv).
- **Total Samples:** 10,000
- **Total Columns:** 10 (`Event_ID`, `V_rms_pu`, `V_peak_pu`, `Crest_Factor`, `THD_percent`, `Duration_ms`, `Dominant_Freq_Hz`, `Freq_Hz`, `SNR_dB`, `Label`)
- **Missing / NaN / Inf values:** Exactly 0 (100% complete)
- **Exact Full Row Duplicates:** 0
- **Exact Feature Vector Duplicates:** 0
- **Underlying Storage:** Tabular pre-extracted features. **Raw time-series waveform arrays (e.g. 1000 samples @ 5 kHz) are not stored in the repository.**

---

## 2. Class Distribution & Imbalance

The dataset spans 8 electrical disturbance classes with a severe class imbalance ratio of **7.83 : 1**:

| Class | Sample Count | Percentage | Electrical Disturbance Type |
|---|---|---|---|
| **Normal** | 2,985 | 29.85% | Steady-state 50 Hz grid baseline |
| **Sag** | 1,835 | 18.35% | Temporary RMS voltage reduction (0.1–0.9 pu) |
| **Swell** | 1,221 | 12.21% | Temporary RMS voltage increase (1.1–1.8 pu) |
| **Harmonics** | 1,177 | 11.77% | Waveform distortion from non-linear loads |
| **Transient** | 985 | 9.85% | High-frequency sub-cycle impulse |
| **Interruption** | 821 | 8.21% | Complete or severe loss of grid voltage (<0.1 pu) |
| **Flicker** | 595 | 5.95% | Low-frequency periodic envelope modulation |
| **Notch** | 381 | 3.81% | Periodic sub-cycle commutation voltage drop |

### Observations:
- `Normal` represents nearly 30% of the entire dataset.
- `Notch` is under-represented with only 381 samples (3.81%), making it vulnerable to poor recall in unweighted models.
- `Interruption` (safety-critical) represents only 8.21% (821 samples).

---

## 3. Empirical Feature Parameter Analysis & Dead Features

| Feature Column | Min | Mean | Max | Std Dev | Skewness | Key Audit Finding |
|---|---|---|---|---|---|---|
| `V_rms_pu` | 0.224 | 0.685 | 1.166 | 0.116 | -0.51 | Strong discriminator for Sag, Swell, and Interruption. |
| `V_peak_pu` | 0.927 | 1.127 | 2.837 | 0.262 | +2.79 | Strong discriminator for Transient (max: 2.837) and Swell (max: 1.837). |
| `Crest_Factor` | 1.304 | 1.682 | 4.483 | 0.435 | +2.71 | High for Interruption (mean 2.27) and Transient (mean 2.22). |
| `THD_percent` | 0.018 | 2.474 | 66.828 | 3.750 | +3.02 | Heavy right tail; strong discriminator for Harmonics and Interruption. |
| `Duration_ms` | 0.000 | 36.153 | 179.400 | 51.662 | +1.14 | **Discrete cluster artifact** (see below). |
| `Dominant_Freq_Hz` | **50.000** | **50.000** | **50.000** | **0.000** | **NaN** | **DEAD FEATURE**: Completely invariant across all 10,000 samples. Zero variance. |
| `Freq_Hz` | 49.927 | 50.000 | 50.083 | 0.020 | +0.03 | Very narrow Gaussian noise around 50 Hz ($\pm 0.08$ Hz). Carries near-zero predictive power. |
| `SNR_dB` | 35.000 | 45.035 | 55.000 | 5.810 | -0.01 | Uniformly distributed random noise across all classes. |

---

## 4. Critical Generation Artifacts Identified

### A. Discrete Artifact in `Duration_ms`
Looking at the per-class distributions of `Duration_ms`:
- **Normal, Flicker, Harmonics, Notch:** Strictly **`0.0 ms`** across all samples.
- **Transient:** Strictly **`5.0 ms`** across all 985 samples.
- **Sag, Swell, Interruption:** Range between **`20.0 ms` and `179.4 ms`**.

This means any decision tree or MLP easily splits `Transient` with a single rule: `if Duration == 5.0 ms -> Transient`. In real electrical distribution grids, transients have continuous durations varying between microseconds and multiple milliseconds.

### B. Constant `Dominant_Freq_Hz`
`Dominant_Freq_Hz` is 50.0 Hz for all classes, including `Harmonics` and `Transient`. This indicates that whoever generated or extracted the features in `BARC DATA.csv` either:
1. Used a dominant frequency extractor with a bug that always picked the 50 Hz fundamental, OR
2. Kept the fundamental amplitude higher than harmonic components so the 50 Hz bin always had the highest peak.

### C. Near-Duplicate Distance Analysis
Evaluating 2,000 randomly selected samples ($1,999,000$ pairwise Euclidean distance calculations in normalized 8D feature space):
- Minimum distance between any two samples: `0.00784`
- Pairs with distance $< 0.05$: only 18 pairs ($0.0009\%$)
- Conclusion: The samples are genuinely continuous with low instance redundancy, but their feature ranges are bounded by rigid parameter regimes.

---

## 5. Audit Conclusions & Answers to Questions

1. **Are the samples actually diverse?**
   Moderate. For continuous voltage features (`V_rms_pu`, `V_peak_pu`, `THD_percent`), samples vary realistically. However, `Duration_ms` and `Dominant_Freq_Hz` suffer from synthetic discretization.
2. **Are many samples generated from identical parameters?**
   No exact duplicates exist. However, `Duration_ms = 5.0 ms` is identical for all 985 Transient events.
3. **Are classes balanced?**
   No. Severe imbalance exists: 29.85% Normal vs 3.81% Notch (7.83:1 ratio).
4. **Are parameter ranges realistic?**
   Generally yes according to IEEE Std 1159 (Sags down to 0.22 pu, Swells up to 1.17 pu, THD up to 12% in harmonics), but transient peak voltages are constrained to 2.8 pu.
5. **Should the dataset be regenerated?**
   **No.** The existing 10,000 samples should be preserved as the official benchmark dataset for comparability with baseline publications. However, future phases must test models against **out-of-distribution parameter shifts** and **controlled noise levels** to prevent memorization of these discrete generation boundaries.

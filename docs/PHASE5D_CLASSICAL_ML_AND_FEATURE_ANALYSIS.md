# PHASE 5D CLASSICAL ML BENCHMARK & FEATURE ANALYSIS REPORT

**Study:** IEEE 9-Bus WSCC Multi-Model Power Quality Comparative Research  
**Branch:** `research/pq-comparative-lab`  
**Experiment Directory:** [`experiments/phase5c/classical/`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/experiments/phase5c/classical/)  
**Metrics Artifact:** [`experiments/phase5c/classical/classical_benchmark_metrics.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/experiments/phase5c/classical/classical_benchmark_metrics.json)  
**Ablation Artifact:** [`experiments/phase5c/classical/feature_ablation_results.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/experiments/phase5c/classical/feature_ablation_results.json)  
**Permutation Importance:** [`experiments/phase5c/classical/permutation_importance.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/experiments/phase5c/classical/permutation_importance.json)  
**Date:** 2026-10-27  

---

## 1. Executive Summary

Track A benchmarks six classical machine learning algorithms on the newly generated, zero-leakage Phase 5C dataset (2,560 training frames across 80 trajectories, 1,024 validation frames across 32 trajectories). Models are trained strictly on the 32-feature contract using `StandardScaler` fitted exclusively on training data. The 1,024-frame challenge partition remains strictly quarantined.

### Multi-Model Benchmark Summary (Validation Partition)

| Model Architecture | Validation Accuracy | Balanced Accuracy | Macro F1 (%) | Macro Precision (%) | Macro Recall (%) | Selection Status |
|---|---|---|---|---|---|---|
| **Multilayer Perceptron (MLP)** | **93.26%** | **93.26%** | **92.60%** | **93.30%** | **93.26%** | **SELECTED BEST** |
| **RBF Support Vector Machine (SVM)** | 91.80% | 91.80% | 91.45% | 92.12% | 91.80% | Benchmark Runner-up |
| **Random Forest (RF)** | 90.62% | 90.62% | 90.13% | 90.68% | 90.62% | Tree Baseline |
| **Extra Trees (ET)** | 90.62% | 90.62% | 90.13% | 90.68% | 90.62% | Ensemble Baseline |
| **HistGradientBoosting** | 90.53% | 90.53% | 90.05% | 90.84% | 90.53% | Boosting Baseline |
| **Logistic Regression (L2)** | 90.53% | 90.53% | 90.04% | 90.96% | 90.53% | Linear Baseline |

---

## 2. Constant Feature Audit

Auditing feature variances on the 2,560 training frames confirmed:
- `dominant_freq`: Standard deviation = $0.00\text{ Hz}$ (constant at 60.0 Hz).
- `true_dominant_freq`: Standard deviation = $0.00\text{ Hz}$ (constant at 60.0 Hz).
- **Effective Varying Features:** 30 out of 32 canonical features.

*Finding:* Under a synchronous 60 Hz simulation grid, nominal fundamental Goertzel tracking resolves to 60.0 Hz. Sub-sample zero-crossing interpolated frequency (`system_freq`), however, varies continuously ($\text{std} = 1.675\text{ Hz}$, range: 49.31 to 68.38 Hz), capturing disturbance-induced phase and frequency deviations.

---

## 3. Controlled Feature Group Ablation

Ablation experiments were performed by retraining the baseline classifier on the training partition with each functional feature group removed, and measuring the resulting impact on validation Macro F1 score (Baseline: 92.60%):

| Feature Group Ablated | Features Removed | Remaining Features | Val Accuracy | Val Macro F1 | $\Delta$ Macro F1 | Criticality Ranking |
|---|---|---|---|---|---|---|
| **Amplitude & Shape** | 4 | 28 | 87.50% | 86.95% | **-5.65%** | **Rank 1 (Most Critical)** |
| **Signal Quality** | 2 | 30 | 87.89% | 87.20% | **-5.40%** | **Rank 2 (Critical)** |
| **Spectral Characteristics** | 4 | 28 | 91.50% | 91.06% | **-1.54%** | **Rank 3 (Moderate)** |
| **Frequency Characteristics** | 3 | 29 | 91.89% | 91.52% | **-1.08%** | **Rank 4 (Moderate)** |
| **Harmonics & Ratios** | 19 | 13 | 93.75% | 93.06% | **+0.45%** | **Rank 5 (Redundant)** |

### Key Physical Insights
1. **Amplitude & Shape (`rms_voltage`, `peak_voltage`, `crest_factor`, `duration`):** Removal drops performance by 5.65%, causing severe confusion between Sag, Swell, Interruption, and Normal.
2. **Signal Quality (`snr`, `thd`):** Removal drops performance by 5.40%. `snr` serves as the primary discriminator separating low-distortion transients from continuous noise.
3. **Harmonic Redundancy:** Pruning 19 harmonic Goertzel features actually improved validation F1 by +0.45%, demonstrating collinearity between individual harmonic bins (H2..H11) and global THD.

---

## 4. Permutation Feature Importance

Permutation feature importance computed across 10 random shuffles on the 1,024 validation frames identified the top 10 discriminative features:

1. **`snr`**: $+0.3904 \pm 0.0052$ (Primary signal quality metric)
2. **`duration`**: $+0.2036 \pm 0.0052$ (Separates transient/notch sub-cycle events from steady-state)
3. **`crest_factor`**: $+0.1236 \pm 0.0063$ (Isolates sharp oscillatory impulses)
4. **`rms_voltage`**: $+0.0747 \pm 0.0075$ (Governs Sag, Swell, and Interruption boundaries)
5. **`spectral_centroid`**: $+0.0656 \pm 0.0041$ (Detects high-frequency spectral shifts)
6. **`spectral_flatness`**: $+0.0627 \pm 0.0034$ (Distinguishes tonal harmonics from white noise)
7. **`spectral_bandwidth`**: $+0.0493 \pm 0.0058$ (Quantifies spectral dispersion)
8. **`peak_voltage`**: $+0.0473 \pm 0.0034$ (Captures transient overshoots)
9. **`h8`**: $+0.0435 \pm 0.0052$ (Identifies high-order harmonic distortion)
10. **`spectral_entropy`**: $+0.0364 \pm 0.0043$ (Measures energy disorder in complex events)

---

## 5. Candidate Model Selection

The **Multilayer Perceptron (MLP)** achieved the highest validation performance (93.26% Accuracy, 92.60% Macro F1) with balanced confusion across all eight classes. It is selected as Candidate 1 for the final one-time challenge evaluation.

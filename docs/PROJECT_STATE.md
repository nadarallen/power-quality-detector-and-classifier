# Project State & Architectural Baseline

**Current Git Commit:** `ff3d883`  
**Branch:** `main`  
**Working Tree:** Clean  
**Date of State Inspection:** 2026-09-20  

---

## 1. System Architecture Overview

The system is an edge-to-cloud Power Quality Disturbance (PQD) classification pipeline targeting both embedded microcontrollers (ESP32 / TinyML) and full-scale data analysis:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DATA & BENCHMARK CORE                                  │
│                                                                                        │
│   Dataset/BARC DATA.csv (Ground truth: 10,000 tabular instances, 8 physical classes)   │
│            │                                                                           │
│            ├──► data/splits/ (Locked 70/15/15 stratified train/val/test splits, v1.0)  │
│            │                                                                           │
│            └──► scripts/prepare_waveform_dataset.py                                    │
│                 └──► data/waveforms/ (*.npz 1000-sample raw time-series arrays)        │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│     DSP & FEATURE ENGINE        │             │        STANDARDS DETECTOR       │
│                                 │             │                                 │
│ dsp/baseline_features.py (8)    │             │ dsp/standards_detector.py       │
│ dsp/enhanced_features.py (47)   │             │ - Windowed sliding RMS (10 ms)  │
│ dsp/waveform_generator.py       │             │ - IEEE 1159 Interruption (<0.1) │
│ - 5 kHz sampling, 1000 samples  │             │ - FFT orders H2-H11 & THD_2_11  │
│ - IEEE 1159.3 metadata schema   │             │ - Sub-cycle transient bounds    │
└────────────────┬────────────────┘             └─────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MODEL PIPELINE                                       │
│                                                                                        │
│   ml/compare_models.py (Benchmarking RF, ExtraTrees, SVM, kNN, Compact MLP)            │
│   ml/convert_tflite.py ──► firmware/src/model_data.h (8.4 KB quantized byte array)     │
│                        └──► ml/models/model_weights.json (Zero-dependency weights)     │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│       EMBEDDED FIRMWARE         │             │      SIMULATION & FRONTENDS     │
│                                 │             │                                 │
│ firmware/src/                   │             │ server.py (REST API :8500)      │
│  ├── main.cpp                   │             │  └── web/ (HTML5 CRT scope,     │
│  ├── feature_extraction.cpp     │             │            client forward pass) │
│  ├── inference.cpp              │             │ app_frontend.py (Streamlit)     │
│  ├── display.cpp & relay_ctrl   │             │ mobile_app/ (React Native Expo) │
│  └── model_data.h               │             │ firebase/ (Cloud telemetry)     │
└─────────────────────────────────┘             └─────────────────────────────────┘
```

---

## 2. Key Modules & Subsystems

| Directory / Module | Key Files | Purpose / Implementation Detail |
|---|---|---|
| **Standards & Specs** | `config/pqd_parameter_spec.yaml` | Machine-readable single source of truth for all parameters categorized into IEEE-Standard, IEEE-Derived, Engineering-Derived, and ML-Only. |
| **Waveform Generation** | `dsp/waveform_generator.py` | Synthesizes 1000-sample voltage waveforms at 5 kHz across 8 classes with IEEE 1159.3-2025 nested metadata tracking. |
| **Standards Measurement** | `dsp/standards_detector.py` | Half-cycle sliding RMS ($U_{\mathrm{rms}(1/2)}$, 10 ms window), residual RMS $< 0.10\text{ pu}$ interruption detector, and FFT harmonic engine ($H_2$ through $H_{11}$). |
| **Preserved DSP** | `dsp/baseline_features.py` | 8 baseline features matching legacy firmware and dataset (RMS, peak, crest factor, Goertzel THD, duration, dominant freq, system freq, SNR). |
| **Enhanced DSP** | `dsp/enhanced_features.py` | 47 statistical, higher-order spectral ($H_1\text{–}H_{11}$), entropy, and shape features for Track B expansion. |
| **Firmware Engine** | `firmware/src/feature_extraction.cpp`<br>`firmware/src/inference.cpp` | On-device C++ feature extraction engine and TFLite Micro inference fallback handler. |
| **Raw Datasets** | `Dataset/BARC DATA.csv`<br>`data/splits/` | Ground truth dataset (10,000 samples) and frozen 70/15/15 stratified train, validation, and test splits. |
| **Automated Tests** | `tests/` (41 test cases) | Rigorous physical, standards, firmware parity, and classification test suite (100% passing). |

---

## 3. Current Classes & Definitions

The system addresses **8 physical states** strictly adhering to the immutable reference specification:
1. **Normal**: Steady-state fundamental sinusoid ($V_{\mathrm{rms}} \in [0.95, 1.05]\text{ pu}$, $\text{THD} < 1.5\%$) within nominal bounds.
2. **Voltage Sag**: RMS reduction to between $0.10\text{ pu}$ and $0.90\text{ pu}$ for $\ge 0.5\text{ cycles}$ (IEEE 1159 Clause 3.1.53).
3. **Voltage Swell**: RMS increase to between $1.10\text{ pu}$ and $1.80\text{ pu}$ for $\ge 0.5\text{ cycles}$ (IEEE 1159 Clause 3.1.58).
4. **Interruption**: Complete loss of voltage with residual RMS strictly $< 0.10\text{ pu}$ for $\ge 0.5\text{ cycles}$ (IEEE 1159 Clause 3.1.34). Instantaneous sample-based detection is prohibited.
5. **Harmonics**: Sinusoidal distortion containing integer multiples ($H_2, H_3, H_5, H_7, H_9, H_{11}$) evaluated via discrete Fourier analysis.
6. **Oscillatory Transient**: Sudden sub-cycle damped oscillation ($350\text{–}750\text{ Hz}$ in generator; strictly constrained $< 2500\text{ Hz}$ Nyquist).
7. **Flicker (Voltage Fluctuation)**: Low-frequency envelope modulation ($\Delta V/V \in [1\%, 10\%]$ at $f_m \in [0.1, 30\text{ Hz}]$, centered at 8.8 Hz eye sensitivity peak).
8. **Voltage Notching**: Localized periodic commutation notches characterized by depth, width, and crest factor depression.

---

## 4. Current Test Suite Status

Executed via `.venv/bin/pytest tests/ -v`:
- **Total Tests Collected:** 42
- **Passed:** 42
- **Failed:** 0
- **Skipped:** 0
- **Execution Time:** ~1.22s

Breakdown:
- `tests/test_classification_rules.py`: 11 tests (interruption boundary, duration thresholds, residual RMS $< 0.10\text{ pu}$, FFT harmonic components, analytical $\text{THD}_{2\_11}$).
- `tests/test_waveform_acceptance.py`: 26 tests (sampling rate, buffer lengths, Nyquist checks, IEEE 1159.3-2025 metadata conformance across all 8 classes).
- `tests/test_firmware_parity.py`: 4 tests (Python $\leftrightarrow$ C++ Goertzel single-precision magnitude, THD parity, and 32-feature Compact MLP forward pass parity).
- `tests/test_dsp_features.py`: 1 test (baseline feature preservation).

---

## 5. Model Baseline & Feature Ablation Results (Frozen 70/15/15 Split)

### 5.1 Baseline 8-Feature Benchmarks
Evaluated on locked 70/15/15 stratified train/validation/test splits (`data/splits/`):

| Model | Val Acc | Val Macro F1 | Test Acc | Test Macro F1 | Interruption Recall (Test) | Safety Status ($\ge 90\%$) | Latency |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compact MLP (Sklearn)** | 95.93% | 0.9482 | 96.87% | 0.9624 | **90.24%** | **PASS** | 310.2 $\mu\text{s}$ |
| **ExtraTrees** | 95.53% | 0.9462 | 98.40% | 0.9813 | **95.12%** | **PASS** | 6,603.4 $\mu\text{s}$ |
| **GradientBoosting** | 96.13% | 0.9546 | 97.73% | 0.9728 | 88.62% | WARNING (<90% Recall) | 16,948.2 $\mu\text{s}$ |
| **Random Forest** | 94.93% | 0.9389 | 97.20% | 0.9645 | 83.74% | WARNING (<90% Recall) | 7,696.6 $\mu\text{s}$ |
| **SVM (Linear)** | 91.80% | 0.8817 | 93.67% | 0.9020 | 81.30% | WARNING (<90% Recall) | — |
| **Logistic Regression** | 90.00% | 0.8487 | 91.47% | 0.8623 | 81.30% | WARNING (<90% Recall) | — |
| **SVM (RBF)** | 88.60% | 0.8251 | 89.73% | 0.8291 | 76.42% | WARNING (<90% Recall) | 314.7 $\mu\text{s}$ |
| **kNN (k=5)** | 86.13% | 0.7811 | 88.27% | 0.8059 | 78.86% | WARNING (<90% Recall) | 681.8 $\mu\text{s}$ |

### 5.2 Controlled Feature Ablation (Compact MLP, Track B)
Evaluated across dimensionally expanded DSP feature groups on locked test set:

| Experiment | Feature Pipeline | Dimensions | Val Acc | Val Macro F1 | Test Acc | Test Macro F1 | Interruption Recall (Test) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **EXP-001** | Baseline 8 | 8 | 97.07% | 0.9644 | 96.87% | 0.9624 | 90.24% |
| **EXP-002** | Baseline + Goertzel Harmonics ($H_1\text{–}H_{11}$) | 27 | 99.47% | 0.9937 | 98.80% | 0.9861 | 99.19% |
| **EXP-003** | EXP-002 + Spectral Moments (Centroid, Bandwidth, Entropy, Flatness, Peak) | **32** | **99.53%** | **0.9939** | **99.40%** | **0.9927** | **100.00%** |
| **EXP-004** | Full Enhanced DSP Matrix | 47 | 99.87% | 0.9985 | 99.67% | 0.9960 | 100.00% |

### 5.3 Generalization & Out-of-Grid Parameter Testing
Tested on 13 randomized parameter configurations outside training grid points:
- **Generalization Score:** 12/13 passed (**92.3%** accuracy).
- Fully generalizable on unseen sag depths ($0.35, 0.72, 0.88\text{ pu}$), swells ($1.22, 1.65\text{ pu}$), sub-cycle durations ($1.5\text{ to }7.2\text{ cycles}$), and transients ($420\text{ Hz and }680\text{ Hz}$).
- Only boundary confusion observed was between complex multi-order even/odd harmonic mixtures ($H_2+H_3+H_{11}$) and commutation notching.

### 5.4 Raw Waveform 1D CNN vs DSP Feature Compression (EXP-007)
Directly evaluated whether end-to-end deep learning on raw 1,000-sample voltage waveforms eliminates the need for DSP feature extraction:

| Architecture | Input Representation | Parameters | Memory (FP32) | Inference Latency | Test Accuracy | Macro F1 | Interruption Recall | Safety Gate ($\ge 90\%$) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compact 1D CNN** | Raw Waveform ($1 \times 1000$) | 4,232 | 16.53 KB | 376.6 $\mu\text{s}$ | 87.87% | 0.8082 | 75.61% | WARNING (<90%) |
| **Compact MLP (Baseline)** | Preserved 8 DSP Features | 2,888 | 11.28 KB | 310.2 $\mu\text{s}$ | 96.87% | 0.9624 | 90.24% | **PASS** |
| **Compact MLP (Enhanced)** | **32 DSP Features (EXP-003)** | **4,424** | **17.28 KB** | **325.7 $\mu\text{s}$** | **99.40%** | **0.9927** | **100.00%** | **PASS** |

*Core Scientific Insight:*
The 1D CNN operating on raw continuous time-series arrays achieved only **87.87% accuracy** and **75.61% Interruption recall**, underperforming both the 8-feature and 32-feature DSP classifiers. Structured domain-specific DSP transformations (Goertzel harmonic filtering, sliding RMS, and spectral moments) encode translation-invariant physical quantities that a compact neural network cannot infer purely from raw sample points at modest training sample counts (7,000 instances). Structured DSP feature compression is therefore scientifically superior and computationally more robust for edge microcontroller deployment.

### 5.5 Out-of-Distribution (OOD) Mixed Compound Disturbances (EXP-008)
Evaluated behavior on non-standardized multi-event waveforms without altering the fixed 8-class ground-truth taxonomy:

| Compound Scenario | Synthesized Disturbance Mixture | Top Model Prediction | Mean Confidence | 2nd Prediction | 2nd Probability |
|---|---|:---:|:---:|:---:|:---:|
| **Sag + Harmonics** | $V_{\mathrm{rms}} = 0.50\text{ pu}$ with $10\%\,H_3 + 6\%\,H_5$ | **Harmonics** | 100.00% | Sag | 0.00% |
| **Swell + Harmonics** | $V_{\mathrm{rms}} = 1.40\text{ pu}$ with $8\%\,H_3 + 5\%\,H_5$ | **Swell** | 99.65% | Harmonics | 0.35% |
| **Transient during Sag** | Sag $0.60\text{ pu}$ with superimposed $500\text{ Hz}$ impulse | **Transient** | 100.00% | Sag | 0.00% |
| **Notch + Harmonics** | Commutation notching with $8\%\,H_5$ distortion | **Notch** | 100.00% | Interruption | 0.00% |

*Diagnostic Finding:* The single-label softmax classifier overconfidently picks the disturbance component with the highest spectral/energy signature rather than exhibiting prediction entropy. For safety-critical field deployments, a secondary energy thresholding gate or `UNKNOWN / ANOMALY` rejection mechanism is recommended.

### 5.6 Model Confidence Calibration & Reliability (EXP-009)
Evaluated probability calibration and Expected Calibration Error (ECE) across 10 confidence bins on the locked test set:
- **Optimal Temperature ($T$):** $1.0824$ (fitted via negative log-likelihood on validation split).
- **Test Set ECE (Uncalibrated):** **$0.119\%$** ($0.00119$).
- **Test Set ECE (Temperature Calibrated):** **$0.188\%$**.
- **Calibration Status:** Exceptionally well calibrated in-distribution. High predicted probabilities ($\ge 95\%$) accurately reflect true ground-truth empirical correctness.

---

## 6. Known Limitations & Technical Debt

1. **Synthetic Dataset Artifacts (`BARC DATA.csv`):**
   - All 985 Transients have an exact duration of `5.0 ms` (synthetic tabular shortcut).
   - `Dominant_Freq_Hz` is constant at `50.0 Hz` across all 10,000 samples (zero variance).
   - Severe class imbalance (7.83 : 1 between Normal 2,985 and Notch 381).
2. **Sampling Rate Constraint on Notches:**
   - At $f_s = 5000\text{ Hz}$ ($T_s = 200\,\mu\text{s}$), notches narrower than $200\,\mu\text{s}$ cannot be resolved. The generator simulates $600\,\mu\text{s}$ notches ($10.8^\circ$), which span 3 discrete samples.
3. **Firmware TFLite Micro Runtime Linking:**
   - `firmware/src/inference.cpp` contains an explicit heuristic fallback covering all 8 classes; full static linking with `tflite::MicroInterpreter::Invoke()` remains to be wired when deploying to physical hardware.

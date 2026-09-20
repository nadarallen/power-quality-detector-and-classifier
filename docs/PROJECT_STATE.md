# Project State & Architectural Baseline

**Current Git Commit:** `f7299ff`  
**Branch:** `main` (Synchronized with `origin/main`)  
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
- **Total Tests Collected:** 41
- **Passed:** 41
- **Failed:** 0
- **Skipped:** 0
- **Execution Time:** ~1.32s

Breakdown:
- `tests/test_classification_rules.py`: 11 tests (interruption boundary, duration thresholds, residual RMS $< 0.10\text{ pu}$, FFT harmonic components, analytical $\text{THD}_{2\_11}$).
- `tests/test_waveform_acceptance.py`: 26 tests (sampling rate, buffer lengths, Nyquist checks, IEEE 1159.3-2025 metadata conformance across all 8 classes).
- `tests/test_firmware_parity.py`: 3 tests (Python $\leftrightarrow$ C++ Goertzel single-precision magnitude and THD parity).
- `tests/test_dsp_features.py`: 1 test (baseline feature preservation).

---

## 5. Historical Model Baseline Results

Evaluated on legacy 80/20 train/test split:

| Model | Accuracy | Macro F1 | Interruption Recall | Size (KB) | Latency ($\mu\text{s}$) | Safety Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compact Keras MLP (Deployed Candidate)** | 95.90% | 0.9468 | 96.34% | 64.8 (8.4 INT8) | 103,638 | **PASS** ($\ge 90\%$) |
| **ExtraTrees** | 96.65% | 0.9595 | 82.32% | 34,124 | 10,587 | WARNING (<90% Recall) |
| **Random Forest** | 96.50% | 0.9575 | 82.32% | 9,731 | 8,185 | WARNING (<90% Recall) |
| **Compact Sklearn MLP** | 96.85% | 0.9592 | 86.59% | 103.9 | 207 | WARNING (<90% Recall) |
| **SVM (RBF)** | 89.10% | 0.8296 | 71.95% | 335.4 | 703 | WARNING (<90% Recall) |
| **kNN (k=5)** | 87.10% | 0.7942 | 70.73% | 706.0 | 1,819 | WARNING (<90% Recall) |

*Note: These historical baselines must be re-benchmarked against the frozen 70/15/15 dataset splits.*

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

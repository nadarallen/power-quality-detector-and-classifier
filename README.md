# Power Quality Disturbance (PQD) Detection and Classification System

> **Research-Grade Edge-to-Cloud Disturbance Classifier (ESP32 TinyML & Cloud Telemetry)**  
> Compliant with **IEEE Std 1159-2019**, **IEEE Std 519-2022**, and **IEC 61000-4-30 Class A**.

---

## 📌 Executive Summary

This repository implements an end-to-end, scientifically validated system for detecting, categorizing, and monitoring **Power Quality Disturbances (PQD)** on electrical power grids. The pipeline ingests continuous voltage waveforms sampled at $f_s = 5000\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$, $N = 1000$ discrete samples per 10-cycle observation window at $f_0 = 50\,\text{Hz}$), extracts physics-informed digital signal processing (DSP) features, and executes low-latency neural network inference on resource-constrained embedded microcontrollers (ESP32) and cloud backends.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              DISCRETE SAMPLING & SENSING                               │
│                                                                                        │
│   12V AC Test Rig / Line Sensor ──► Hardware Timer ISR (5 kHz ADC, 200 µs interval)    │
│                                     1000 Samples (10 fundamental cycles = 200 ms)      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             DSP & FEATURE EXTRACTION                                   │
│                                                                                        │
│   • Track A (Baseline 8 Features): RMS, Peak, Crest Factor, Goertzel THD, Freq, SNR    │
│   • Track B (Validated 32 Features): Goertzel Bank H1–H11, Spectral Moments & Energy   │
│   • Half-Cycle Sliding RMS (10 ms window) for IEEE 1159 Interruption vs Sag detection  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ON-DEVICE EMBEDDED INFERENCE ENGINE                             │
│                                                                                        │
│   • Zero-Dependency C++ Forward Pass (firmware/src/model_weights_32.h)                 │
│   • 32-Feature Compact MLP (32 -> 64 -> 32 -> 8, FP32 footprint: 17.28 KB)             │
│   • Inference Latency: 325.7 µs | Safety Gate: Flag UNCERTAIN if confidence < 60%      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
│         LOCAL FIRMWARE OUTPUT         │       │          REMOTE TELEMETRY & UI        │
│                                       │       │                                       │
│ • OLED Display (SSD1306)              │       │ • Python Streamlit Dashboard (:8501)  │
│ • 115200 Baud Serial Telemetry CSV    │       │ • Interactive Web CRT Oscilloscope    │
│ • Hardware Relay Test Rig Control     │       │ • Firebase Firestore Event Logging    │
└───────────────────────────────────────┘       └───────────────────────────────────────┘
```

---

## 📚 Technical Documentation & Research Audits

For in-depth architectural proofs, mathematical derivations, empirical validation logs, and standards mapping, refer to the documentation suite:

| Document | Primary Focus & Coverage |
|---|---|
| 📖 [**`docs/PROJECT_STATE.md`**](docs/PROJECT_STATE.md) | Verified commit status, full 43-test suite breakdown, architectural diagrams, model benchmarks, and hardware constraints. |
| 🔬 [**`docs/DATASET_AUDIT.md`**](docs/DATASET_AUDIT.md) | Empirical audit of the 10,000-sample dataset: class imbalance ($7.83:1$), near-duplicate analysis, and synthetic artifact disclosures. |
| 🔒 [**`docs/DATASET_SPECIFICATION.md`**](docs/DATASET_SPECIFICATION.md) | Frozen v1.0 dataset specification with SHA-256 integrity checksums, partition criteria, and frozen 70/15/15 train/val/test splits. |
| ⚖️ [**`docs/IEEE_ALIGNMENT_AUDIT.md`**](docs/IEEE_ALIGNMENT_AUDIT.md) | Standards compliance audit mapping repository parameters against IEEE 1159-2019, IEEE 519-2022, and IEC 61000-4-30. |
| 🌊 [**`docs/WAVEFORM_STANDARD_AUDIT.md`**](docs/WAVEFORM_STANDARD_AUDIT.md) | Deep mathematical audit of discrete waveform generation, IEEE 1159.3 COMTRADE metadata, and sub-cycle transient bounds. |
| 🛡️ [**`docs/DATA_LEAKAGE_AUDIT.md`**](docs/DATA_LEAKAGE_AUDIT.md) | Quantitative verification of zero train/test contamination across continuous feature spaces ($k$-NN distance $\ge 0.0084$). |
| 📊 [**`reports/experiment_results.csv`**](reports/experiment_results.csv) | Full machine-readable experiment tracking ledger covering ablation runs EXP-001 through EXP-009. |
| 📜 [**`docs/paper_draft.md`**](docs/paper_draft.md) | IEEE PES transactions-style technical conference paper draft. |

---

## ⚡ Physical Disturbance Classes & Standards Mapping

The system classifies **8 distinct physical states** without modifying standard regulatory boundaries:

| ID | Disturbance Class | Governing Standard | Defining Characteristics | Documentation Citation |
|:---:|---|---|---|---|
| `0` | **Flicker (Fluctuation)** | IEEE 1453 / IEC 61000-4-15 | Envelope modulation $\Delta V/V \in [1\%, 10\%]$ at $f_m \in [0.1, 30\,\text{Hz}]$. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#flicker-voltage-fluctuations) |
| `1` | **Harmonics** | IEEE 519-2022 | Discrete Fourier integer harmonics ($H_2$ through $H_{11}$); $\text{THD}_{2\_11} > 5.0\%$. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#harmonics-and-waveform-distortion) |
| `2` | **Interruption** | IEEE 1159 Clause 3.1.34 | Severe power loss where residual half-cycle RMS is strictly $< 0.10\,\text{pu}$. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#voltage-sag-swell-and-interruption) |
| `3` | **Normal** | Grid nominal baseline | Clean fundamental sinusoid: $V_{\text{rms}} \in [0.95, 1.05]\,\text{pu}$, $\text{THD} < 1.5\%$. | [Read baseline details](docs/DATASET_SPECIFICATION.md#sampling--windowing-parameters) |
| `4` | **Notch** | IEEE 1159 Clause 3.1.50 | Commutation notch caused by thyristor switching; localized crest factor depression. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#voltage-notching) |
| `5` | **Voltage Sag** | IEEE 1159 Clause 3.1.53 | RMS voltage reduction to between $0.10\,\text{pu}$ and $0.90\,\text{pu}$ for $\ge 0.5$ cycles. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#voltage-sag-swell-and-interruption) |
| `6` | **Voltage Swell** | IEEE 1159 Clause 3.1.58 | RMS voltage increase to between $1.10\,\text{pu}$ and $1.80\,\text{pu}$ for $\ge 0.5$ cycles. | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#voltage-sag-swell-and-interruption) |
| `7` | **Transient** | IEEE 1159 Clause 3.1.66 | Sub-cycle damped oscillatory transient ($350\text{–}750\,\text{Hz} < 2500\,\text{Hz}$ Nyquist). | [Read standard details](docs/IEEE_ALIGNMENT_AUDIT.md#oscillatory-transient) |

---

## 📊 Empirical Benchmarks & Controlled Ablation

### 1. Controlled Feature Ablation (Track A vs. Track B)

All models were evaluated on the **frozen 70/15/15 stratified test set** (1,500 unseen samples, SHA-256: `e7dc1bc1...`):

| Experiment | Feature Pipeline | Dims | Test Accuracy | Macro F1 | Interruption Recall | Safety Gate ($\ge 90\%$) | Inference Latency |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **EXP-001** | Baseline 8 Features (Track A) | 8 | 96.87% | 0.9624 | 90.24% | **PASS** | 310.2 $\mu\text{s}$ |
| **EXP-002** | Baseline + Goertzel Harmonics ($H_1\text{–}H_{11}$) | 27 | 98.80% | 0.9861 | 99.19% | **PASS** | 319.4 $\mu\text{s}$ |
| **EXP-003 (Deployed)** | **EXP-002 + Spectral Moments (Centroid, Bandwidth, Entropy, Flatness, Peak)** | **32** | **99.40%** | **0.9927** | **100.00%** | **PASS** | **325.7 $\mu\text{s}$** |
| **EXP-004** | Full 47 Enhanced DSP Features | 47 | 99.67% | 0.9960 | 100.00% | **PASS** | 344.1 $\mu\text{s}$ |

> **Audit Insight:** EXP-003 achieved **100% Interruption recall** and **99.40% overall test accuracy** at an embedded inference latency of only $325.7\,\mu\text{s}$, resolving the 19 cross-confusions between Sag and Interruption present in the 8-feature baseline.  
> 🔗 *Full ablation analysis:* [docs/PROJECT_STATE.md (Section 5.2)](docs/PROJECT_STATE.md#52-controlled-feature-ablation-compact-mlp-track-b)

### 2. Deep Learning vs. Physics-Informed DSP (EXP-007)

We benchmarked a compact **1D Convolutional Neural Network (1D CNN)** operating directly on raw 1,000-sample time-series waveforms against our DSP-based MLPs:

| Architecture | Representation | Parameters | Memory Footprint | Test Acc | Macro F1 | Interruption Recall | Safety Gate Status |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compact 1D CNN** | Raw Waveform ($1 \times 1000$) | 4,232 | 16.53 KB | 87.87% | 0.8082 | 75.61% | ⚠️ **FAIL (<90%)** |
| **Compact MLP (Baseline)** | 8 Preserved DSP Features | 2,888 | 11.28 KB | 96.87% | 0.9624 | 90.24% | **PASS** |
| **Compact MLP (Enhanced)** | **32 DSP Features (EXP-003)** | **4,424** | **17.28 KB** | **99.40%** | **0.9927** | **100.00%** | **PASS** |

> **Scientific Finding:** Pure raw time-series 1D CNNs cannot achieve reliable generalization from moderate dataset scales without phase invariants. Structured DSP transformations (Goertzel harmonic banks, sliding RMS, spectral entropy) provide essential translation and phase invariance.  
> 🔗 *Complete study:* [docs/PROJECT_STATE.md (Section 5.4)](docs/PROJECT_STATE.md#54-raw-waveform-1d-cnn-vs-dsp-feature-compression-exp-007)

### 3. Out-of-Grid Stress Testing & Compound Waveforms

- **Out-of-Grid Parameter Sweep (EXP-005):** Tested on 13 randomized parameter configurations completely outside training grid points. Achieved **92.3% generalization** (12/13 passed).  
  🔗 *Sweep details:* [docs/PROJECT_STATE.md (Section 5.3)](docs/PROJECT_STATE.md#53-generalization--out-of-grid-parameter-testing)
- **Mixed Compound Disturbances (EXP-008):** Evaluated behavior on non-standard dual-event waveforms (e.g. Sag + Harmonics, Swell + Harmonics). Demonstrates that single-label softmax classifiers pick the dominant energy disturbance with ~100% confidence, proving the need for our confidence thresholding gate (`UNCERTAIN` for $< 60\%$).  
  🔗 *Compound findings:* [docs/PROJECT_STATE.md (Section 5.5)](docs/PROJECT_STATE.md#55-out-of-distribution-ood-mixed-compound-disturbances-exp-008)
- **Model Calibration (EXP-009):** Expected Calibration Error (ECE) is **$0.119\%$**, confirming predicted softmax probabilities match empirical accuracy.  
  🔗 *Calibration curves:* [docs/PROJECT_STATE.md (Section 5.6)](docs/PROJECT_STATE.md#56-model-confidence-calibration--reliability-exp-009)

---

## 📁 Repository Structure

```
power-quality-detector-and-classifier/
├── config/
│   └── pqd_parameter_spec.yaml         # Single source of truth for all electrical parameters
├── data/
│   ├── pqd_features.csv                # Standardized 8-feature matrix (10,000 samples)
│   ├── splits/                         # Frozen 70/15/15 train/val/test CSV splits (v1.0)
│   └── waveforms/                      # 1000-sample raw time-series arrays (*.npz)
├── Dataset/
│   └── BARC DATA.csv                   # Ground-truth raw tabular recording (10,000 instances)
├── dsp/
│   ├── baseline_features.py            # Preserved 8-feature Goertzel extraction engine
│   ├── enhanced_features.py            # 47-feature extended spectral, moment & entropy engine
│   ├── standards_detector.py           # IEEE 1159 half-cycle sliding RMS & FFT detector
│   └── waveform_generator.py           # IEEE 1159.3 compliant 5 kHz synthetic waveform generator
├── docs/                               # Comprehensive research audits & technical specifications
│   ├── PROJECT_STATE.md                # System baseline, commit status & test logs
│   ├── DATASET_AUDIT.md                # 10,000-sample dataset audit & artifact analysis
│   ├── DATASET_SPECIFICATION.md        # Cryptographic checksums & split methodology
│   ├── IEEE_ALIGNMENT_AUDIT.md         # IEEE 1159/519 & IEC 61000 standards alignment
│   ├── WAVEFORM_STANDARD_AUDIT.md      # Waveform acceptance & sampling math audit
│   ├── DATA_LEAKAGE_AUDIT.md           # Nearest-neighbor leakage audit
│   └── paper_draft.md                  # IEEE conference paper draft
├── firmware/
│   ├── platformio.ini                  # ESP32 PlatformIO configuration
│   └── src/
│       ├── main.cpp                    # Real-time 5 kHz ADC sampling and inference loop
│       ├── feature_extraction.cpp / .h # C++ single-precision 8 & 32-feature extraction
│       ├── inference.cpp / .h          # C++ inference runner with uncertainty gating
│       ├── model_weights_32.h          # Zero-dependency C++ forward pass (EXP-003 model)
│       ├── model_data.h                # Quantized TFLite Micro model byte array (8.4 KB)
│       ├── relay_control.cpp / .h      # Hardware relay switching & timer ISR ADC sampler
│       └── display.cpp / .h            # 115200 baud serial telemetry & OLED driver
├── ml/
│   ├── compare_models.py              # Cross-classifier benchmark suite
│   ├── convert_tflite.py              # TFLite post-training quantization pipeline
│   └── models/
│       ├── model_weights_32.json       # Scaler and neural network weights for C++ exporter
│       └── mlp_deployed.tflite         # Quantized 8.4 KB baseline model
├── reports/
│   └── experiment_results.csv          # Machine-readable ledger for experiments EXP-001–009
├── tests/
│   ├── test_classification_rules.py    # 11 tests: IEEE interruption, THD & boundaries
│   ├── test_waveform_acceptance.py     # 26 tests: IEEE 1159.3 metadata, Nyquist & buffers
│   ├── test_firmware_parity.py         # 5 tests: Python <-> C++ exact floating-point parity
│   └── test_dsp_features.py            # 1 test: Baseline feature preservation
├── app_frontend.py                     # Streamlit + Plotly interactive monitoring dashboard
└── server.py                           # REST API & HTML5 CRT Oscilloscope frontend
```

---

## 🚀 Quickstart & Verification

### 1. Environment Setup

Clone repository and install dependencies in a Python 3.10+ virtual environment:
```bash
git clone https://github.com/nadarallen/power-quality-detector-and-classifier.git
cd power-quality-detector-and-classifier
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or install numpy scipy pandas scikit-learn torch pytest
```

### 2. Run Comprehensive Automated Test Suite

Verify that all **43 physical, standards, firmware parity, and waveform acceptance tests** pass:
```bash
pytest tests/ -v
```
Expected output: `43 passed in ~2.5s`

### 3. Launch Interactive Streamlit Dashboard

Inspect real-time waveforms, DSP spectral decomposition, and model decisions:
```bash
streamlit run app_frontend.py --server.port 8501
```
Navigate to `http://localhost:8501` to view both the **Desktop Analytics View** and the **Mobile Simulator View**.

### 4. Native C++ Parity Test Compilation

Verify that the firmware C++ feature extraction and forward pass compile cleanly on native host machines without external dependencies:
```bash
g++ -std=c++17 -O2 tests/test_harness_manual.cpp firmware/src/feature_extraction.cpp firmware/src/inference.cpp -Ifirmware/src -o /tmp/pqd_test && /tmp/pqd_test
```
(Automated inside `tests/test_firmware_parity.py::test_cpp_native_feature_extraction_and_inference_parity`).

---

## 🔒 Electrical Safety & Hardware Interfacing

For physical hardware testing on test rigs or microcontrollers, consult [hardware/safety_checklist.md](hardware/safety_checklist.md):
- **Isolation:** Galvanic isolation using optocouplers (PC817) and 1:1 isolation transformers.
- **Voltage Clamping:** 3.3V Zener diodes across ESP32 ADC input pins (`GPIO 34`, `GPIO 35`) to protect silicon from inductive kickback.
- **Snubbers:** $RC$ snubber networks ($100\,\Omega, 0.1\,\mu\text{F}$) across all inductive switching relay contacts.
- **Watchdog:** Firmware watchdog timer (`esp_task_wdt`) enabled with automatic timeout reset on loop lockup.


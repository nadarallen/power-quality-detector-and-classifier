# AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation

> **Current Lifecycle Phase:** Phase 4 — Proper 60-Hz ML Implementation & Evaluation (**COMPLETE**)  
> **Next Engineering Phase:** Phase 5 — Live Simulink Demonstration MVP (**PENDING**)  
> **Optional Extension:** Phase 6 — Embedded ESP32 Hardware-in-the-Loop Deployment (**FUTURE / OPTIONAL**)  
>
> [![Tests](https://img.shields.io/badge/tests-322%20passed-brightgreen.svg)](tests/)
> [![Sampling](https://img.shields.io/badge/sampling-5%20kHz%20%7C%20200%20ms-blue.svg)](dsp/)
> [![Grid](https://img.shields.io/badge/grid-WSCC%2060%20Hz%20IEEE%209--bus-orange.svg)](IEEE_9bus/)
> [![Classes](https://img.shields.io/badge/classes-8%20disturbances%20audited-success.svg)](data/ieee9bus_60hz/)
> [![Phase](https://img.shields.io/badge/phase%204-COMPLETE%20(Gates%204A--4D)-brightgreen.svg)](docs/REPRODUCING_PHASE4.md)

---

## 1. Project Overview

This repository implements an end-to-end, scientifically validated, and standards-aligned system for simulating, detecting, extracting, and categorizing **Power Quality Disturbances (PQD)** in high-voltage electrical transmission grids.

The primary architecture bridges an electromagnetic simulation of the **WSCC 3-Machine 9-Bus Network** (operating at $60.0\text{ Hz}$ in MATLAB/Simulink Simscape Electrical) to a high-performance Python Digital Signal Processing (DSP) and event detection pipeline. The pipeline ingests continuous three-phase voltages ($V_a, V_b, V_c$) sampled at $F_s = 5,000\text{ Hz}$ ($T_s = 200\ \mu\text{s}$, $N = 1,000$ discrete samples per 12-cycle analysis window), extracts a formal **32-feature mathematical contract**, tracks multi-phase disturbance lifecycles independently of machine learning, and dispatches real-time telemetry to an interactive laboratory dashboard.

```
+-----------------------------------------------------------------------------+
|                      CURRENT PRODUCTION ARCHITECTURE                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   |         IEEE 9-Bus WSCC Transmission Model (Simscape 60 Hz)         |   |
|   |  - 3 Generators, 3 Transformers, 9 Transmission Buses, 3 Loads      |   |
|   |  - Authoritative Observation Point: Bus 5 (230 kV Load Bus)         |   |
|   |  - Working Disturbance Model: IEEE_9bus_PQD_DISTURBANCES.slx        |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Bus 5 Vabc, Iabc                    |
|   +---------------------------------------------------------------------+   |
|   |         MATLAB Acquisition & Resampling Bridge (5,000 Hz)           |   |
|   |  - Continuous discrete representation (Ts = 200 us, N = 1000)       |   |
|   |  - HTTP Streaming Ingestion Adapter (/api/simulink/ingest_chunk)     |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  JSON / Binary POST                  |
|   +---------------------------------------------------------------------+   |
|   |         Production 32-Feature Python DSP Engine                     |   |
|   |  - Goertzel Harmonic Filter Bank H1–H11 (60 Hz to 660 Hz)           |   |
|   |  - Phase-Aware Orthogonal Projection SNR (Angle-Invariant)          |   |
|   |  - Half-Cycle Sliding RMS & Statistical Moments (Skew/Kurt/Entropy) |   |
|   |  - Mathematical Parity with MATLAB Verified (< 0.000050 tolerance)  |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  32-Dimensional Feature Vector       |
|   +---------------------------------------------------------------------+   |
|   |         Three-Phase Event Engine & ML Classifier                    |   |
|   |  - Ground Truth derived strictly from Physical Scenario Controllers |   |
|   |  - Independent Physical Rule Engine (IEEE 1159 / IEEE 519)          |   |
|   |  - Legacy 50-Hz Weights Frozen (flags MODEL_DOMAIN_MISMATCH)        |   |
|   |  - SQLite Event Persistence (data/pq_events.db)                     |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Server-Sent Events (SSE)            |
|   +---------------------------------------------------------------------+   |
|   |         Live Telemetry & Laboratory Oscilloscope UI                 |   |
|   |  - CRT Oscilloscope (3-Phase Real-Time Waveforms)                   |   |
|   |  - FFT Spectrum Analyzer & Harmonic THD Bargraph                    |   |
|   |  - 32-Feature Parameter Matrix & Classification Telemetry           |   |
|   +---------------------------------------------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 2. Completed Disturbance Datasets (Phase 3)

The project has completed physical electromagnetic modeling, dataset generation, feature extraction, and independent scientific audits across all **8 disturbance classes** under `data/ieee9bus_60hz/`, authoritatively codified in [`data/ieee9bus_60hz/dataset_manifest_v1.json`](data/ieee9bus_60hz/dataset_manifest_v1.json):

| Class | Label | Frames | Trajectories | Physical Switching Mechanism | Key Physical Metric | Gate Status |
|---|:---:|:---:|:---:|---|---|:---:|
| **Normal** | 0 | 1,120 | 32 | Steady-state load flow (32 operating conditions) | $\text{RMS} = 0.589\text{ pu}, \text{THD} = 0.35\%$ | **PASS** (Gate 3B.1) |
| **Sag** | 1 | 1,152 | 36 | Transmission shunt fault switching (`PQD_Fault_Sag`) | Residual $0.10\text{--}0.90\text{ pu}$, $16.7\text{--}120\text{ ms}$ | **PASS** (Gate 3F) |
| **Swell** | 2 | 1,152 | 36 | Shunt capacitor bank energization (`PQD_Breaker_Swell`) | Magnitude $1.10\text{--}1.80\text{ pu}$, $16.7\text{--}120\text{ ms}$ | **PASS** (Gate 3I) |
| **Interruption** | 3 | 1,152 | 36 | Series line breaker opening (`PQD_Breaker_Interruption`) | Residual $< 0.10\text{ pu}$ (mean $0.008\text{ pu}$) | **PASS** (Gate 3L) |
| **Harmonics** | 4 | 1,152 | 36 | Non-linear load current injection (`PQD_Harm_Inj`) | Orders $H_2\text{--}H_{11}$, $\text{THD} = 5.1\%\text{--}19.8\%$ | **PASS** (Gate 3O) |
| **Flicker** | 5 | 1,152 | 36 | Sub-synchronous dynamic load modulation (`PQD_Flicker_Mod`) | $f_m \in [1, 25]\text{ Hz}$, depth $1.0\%\text{--}10.0\%$ | **PASS** (Gate 3R) |
| **Notch** | 6 | 1,152 | 36 | Commutation short-circuit switching (`PQD_Notch_Bus5`) | Width $100\text{--}900\ \mu\text{s}$, depth $20\%\text{--}70\%$ | **PASS** (Gate 3U) |
| **Transient** | 7 | 1,152 | 36 | High-frequency RLC energization (`PQD_Breaker_Transient`) | Oscillation $300\text{--}2,200\text{ Hz}$, peak $1.2\text{--}1.9\text{ pu}$ | **PASS** (Gate 3X) |

**Total Dataset Size:** Exactly **9,184 multi-phase frames across 284 independent simulation trajectories** (Train: 6,594 frames / 71.80%, Validation: 1,295 frames / 14.10%, Locked Test: 1,295 frames / 14.10%) with **zero inter-trajectory leakage**.

---

## 3. Strict Engineering Freeze Rules & Architectural Invariants

1. **Pristine Reference Model Freeze:**  
   `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` is frozen as the uncorrupted reference benchmark (SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`). All disturbance injection subsystems reside exclusively in `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`.
2. **Ground-Truth Decoupling Rule:**  
   Ground-truth class labels originate strictly from **physical scenario controllers and simulation metadata**—never from machine learning predictions.
3. **Legacy ML Weights Preservation:**  
   The legacy 50-Hz runtime weights (`ml/models/model_weights_32.json`, SHA-256: `BE9BDBC3641F...`) remain frozen for historical backwards compatibility. Phase 4 produced the verified 60-Hz production candidate MLP (`experiments/phase4c/models/candidate_mlp_pipeline.pkl`, 99.92% locked test accuracy, 99.93% macro F1).
4. **Authoritative 60-Hz / 5-kHz Sampling Contract:**  
   All feature definitions, FFT harmonic bins, and sliding RMS algorithms are strictly locked to $f_0 = 60.0\text{ Hz}$, $F_s = 5,000\text{ Hz}$, and $N = 1,000$ samples (200 ms).

---

## 4. Multi-Phase Engineering Roadmap

```
  [PHASE 1: ELECTRICAL FOUNDATION] ----------------------> COMPLETE (Gate 3A)
  [PHASE 2: 60-HZ DSP & INTEGRATION BRIDGE] --------------> COMPLETE (Gates 3B, 3C)
  [PHASE 3: PHYSICAL 8-CLASS DATASET & QUALITY AUDITS] --> COMPLETE (Gates 3D - 3X)
  [PHASE 4: PROPER 60-HZ MACHINE LEARNING TRAINING] -----> COMPLETE (Gates 4A - 4D)
  [PHASE 5: LIVE SIMULINK DEMONSTRATION MVP] ------------> FUTURE
  [PHASE 6: EMBEDDED ESP32 HIL EXTENSION] ---------------> FUTURE / OPTIONAL
```

- **Phase 4 (Proper 60-Hz ML):** COMPLETE. Trajectory-grouped dataset splitting (zero leakage), train-only scaler fitting, multi-model benchmarking (5 classifiers), hyperparameter tuning, and independent evaluation on locked test partition (99.92% accuracy, 99.93% macro F1).
- **Phase 5 (Live Demo MVP):** Derivative live Simulink model (`IEEE_9bus_PQD_LIVE_DEMO.slx`), programmatic MATLAB trigger API (`pqd.sag(...)`, etc.), Simulink interactive controls, and streaming CRT dashboard.
- **Phase 6 (Embedded HIL Extension):** Microcontroller ADC sampling and firmware inference on ESP32 hardware.

---

## 5. Repository Directory Structure

```
power-quality-detector-and-classifier/
├── README.md                      # Primary project overview and architectural status
├── RUNTHISPROJECT.md              # Developer quickstart and execution instructions
├── CHANGELOG.md                   # Formal chronological engineering record
├── .gitignore                     # Git hygiene and artifact exclusion rules
├── app.py                         # Interactive Streamlit research dashboard
├── dashboard_backend.py           # Backend helpers for waveform loading & inference
├── requirements.txt               # Complete Python dependencies
├── server.py                      # REST & SSE Telemetry server (port 8500)
├── app_frontend.py                # Alternative dashboard UI launcher
│
├── IEEE_9bus/                     # Power system simulation models (MATLAB/Simulink R2025a)
│   ├── IEEE_9bus_PQD_HIL_R2025a.slx  # Pristine frozen reference baseline (SHA-256 verified)
│   ├── IEEE_9bus_PQD_DISTURBANCES.slx # Working disturbance model (7 active injection blocks)
│   ├── Original9bus.slx           # Preserved baseline variant
│   └── jailib.slx                 # Preserved library model
│
├── docs/                          # Comprehensive technical documentation & audits
│   ├── README.md                  # Documentation navigation index
│   ├── PROJECT_STATUS.md          # Master single human-readable project status
│   ├── ARTIFACT_INTEGRITY_RECONCILIATION.md # Checksum reconciliation & parity audit
│   ├── REPRODUCING_PHASE4.md      # Clean-clone reproduction protocol
│   ├── SOURCE_OF_TRUTH.md         # Authoritative file and contract registry
│   ├── ARCHITECTURE.md            # 7-subsystem engineering specification
│   ├── ROADMAP.md                 # Multi-phase roadmap (Phases 1 through 6)
│   ├── DATASET.md                 # 8-class physical dataset specification
│   ├── STANDARDS_TRACEABILITY_INDEX.md # Standards mapping (IEEE 1159, 519, 1453)
│   ├── ML_READINESS.md            # 10-step protocol for Phase 4 ML training
│   ├── REPRODUCIBILITY.md         # Environment setup and reproduction recipes
│   ├── LIVE_MVP_PLAN.md           # Phase 5 live demonstration specification
│   ├── GATE_INDEX.md              # Gate verification matrix (Gates 1 to 4D)
│   ├── REPOSITORY_LEGACY_AUDIT.md # Component classification and legacy audit
│   └── GATE3A to GATE4D reports   # Immutable gate reports and quality summaries
│
├── data/
│   ├── ieee9bus_60hz/             # Authoritative 8-class 60-Hz physical datasets
│   │   ├── dataset_manifest_v1.json # Cryptographically frozen manifest (SHA-256 verified)
│   │   ├── normal/                # 1,152 frames, 32 operating conditions (.npz, .csv)
│   │   ├── sag/                   # 1,152 frames, shunt fault switching (.npz, .csv)
│   │   ├── swell/                 # 1,152 frames, capacitor energization (.npz, .csv)
│   │   ├── interruption/          # 1,152 frames, line breaker opening (.npz, .csv)
│   │   ├── harmonics/             # 1,152 frames, non-linear load injection (.npz, .csv)
│   │   ├── flicker/               # 1,152 frames, sub-synchronous modulation (.npz, .csv)
│   │   ├── notch/                 # 1,152 frames, commutation short-circuits (.npz, .csv)
│   │   └── transient/             # 1,152 frames, high-frequency RLC switching (.npz, .csv)
│   └── pq_events.db               # SQLite database for event persistence
│
├── dsp/                           # Digital Signal Processing subsystem
│   ├── enhanced_features.py       # Authoritative 32-feature extraction engine
│   ├── waveform_generator.py      # IEEE 1159 / 519 synthetic disturbance generator
│   ├── waveform_frame.py          # Multi-channel waveform container & NaN guards
│   ├── standards_detector.py      # Independent IEEE physical rule engine
│   ├── phase_processor.py         # Multi-phase sliding window processor
│   ├── ring_buffer.py             # Circular streaming acquisition buffer (5 kHz)
│   └── acquisition_adapter.py     # Streaming adapters (Simulink, Simulation, Mock)
│
├── experiments/                   # Controlled ML experiment tracking & frozen models
│   ├── phase4b/                   # 5-baseline classifier comparison metrics & models
│   ├── phase4c/models/            # Frozen candidate MLP pipeline (StandardScaler + MLP)
│   └── phase4d/                   # Independent locked test partition evaluation metrics
│
├── pipeline/                      # Ingestion and validation pipelines
│   ├── realtime_pipeline.py       # Core streaming ingestion & telemetry engine
│   └── disturbance_validator.py   # Ground-truth physical rule validator (8 classes)
│
├── scenarios/                     # Ground-truth scenario controller definitions
│   └── definitions/               # JSON scenario specs (SAG, SWELL, INT, HAR, etc.)
│
├── integration/                   # Simulation-to-Python integration bridge
│   └── matlab/                    # Streaming & auto-ingestion MATLAB scripts
│
├── ml/                            # Machine learning models and training scripts
│   └── models/
│       └── model_weights_32.json  # Preserved legacy 50-Hz baseline weights
│
├── scripts/                       # Dataset generators, validators, and audit scripts
│   ├── generate_ieee_waveform_graphs.py # Publication-quality standards-annotated waveform generator
│   └── verify_dataset_freeze.py   # Cryptographic dataset manifest auditor
├── tests/                         # Complete automated test suite (322 passed)
├── web/                           # Live laboratory oscilloscope dashboard UI
│
├── firmware/                      # Optional Phase 6 ESP32 C++ firmware (PlatformIO)
├── hardware/                      # Optional Phase 6 analog front-end schematics
├── firebase/                      # Optional cloud telemetry bridge
└── mobile_app/                    # Optional mobile telemetry viewer
```

---

## 6. Interactive Power Quality Research Dashboard

The repository includes a modern, interactive Streamlit research platform ([`app.py`](app.py)) demonstrating power-quality disturbance detection and classification across two operational modes:

```bash
# Launch the interactive research dashboard
streamlit run app.py
```

### Operational Modes:
- **Mode A: Recorded Experiment Explorer (Zero MATLAB Requirement — FULLY VERIFIED):**  
  Browse and visualize 3-phase waveforms ($V_A, V_B, V_C$) across all 8 classes from the frozen 60 Hz IEEE 9-bus dataset. Computes instantaneous 32-feature vectors in real time, runs inference with the frozen Phase 4C candidate MLP model, and displays prediction confidence distributions and softmax probability charts. Operates 100% standalone without requiring MATLAB or Simscape.
- **Mode B: Simulink Live Experiment Runner (SCRIPT HOOKS IMPLEMENTED — RUNTIME EXECUTION UNVERIFIED / NOT TESTED):**  
  Provides parameter validation and execution hooks for researchers with MATLAB R2024b/R2025a and Simscape Electrical to parameterize live disturbance injections (duration, fault resistance, affected phases) and invoke [`scripts/run_disturbance_simulation.m`](scripts/run_disturbance_simulation.m). *Note: While the model topology, injection blocks, and runner scripts have passed static dependency audits, full end-to-end live MATLAB execution is marked as UNVERIFIED / NOT TESTED in automated CI environments due to external MATLAB license and headless execution constraints.*
- **Model Comparison & Audit Evidence:**  
  Displays quantitative benchmark tables from Phase 4B (Logistic Regression, Random Forest, SVM-RBF, Gradient Boosting, Compact MLP), latency-vs-accuracy trade-offs, and independent confusion matrices on the locked Phase 4D test partition (1,295 frames, 99.92% accuracy, 99.93% macro F1).
- **Feature Engineering & Explainability:**  
  Provides full mathematical descriptions and IEEE standard mappings for all 32 time-domain, Goertzel harmonic, harmonic ratio, and FFT spectral moments.

---

## 7. Standards-Annotated Waveform Visualizations (IEEE Std 1159 & IEEE Std 519)

Publication-ready, physical standards-annotated waveform plots can be generated via [`scripts/generate_ieee_waveform_graphs.py`](scripts/generate_ieee_waveform_graphs.py):

```bash
# Generate high-resolution waveform graphs and 8-panel comparison overview
python scripts/generate_ieee_waveform_graphs.py
```

Each generated figure features a three-panel comparative layout:
1. **Top Panel:** Pure nominal reference sinusoid $v(t) = V_m \sin(2\pi f_0 t)$ ($f_0 = 60.0\text{ Hz}$).
2. **Middle Panel:** Disturbed waveform synthesized according to physical equations.
3. **Bottom Panel:** Comparative overlay with shaded disturbance regions and exact engineering parameter callouts.

> **Note on Parameter Specifications**: The numerical values listed below (e.g., sag depth $0.45\text{ pu}$, swell magnitude $1.45\text{ pu}$, transient oscillation $550\text{ Hz}$, flicker modulation $8.0\text{ Hz}$) represent **curated, standards-aligned simulation and demonstration parameters** selected for clean visual contrast and benchmark reproducibility. They fall within the allowable classification envelopes defined by IEEE Std 1159, IEEE Std 519, and IEEE Std 1453, but are illustrative design settings rather than singular numerical mandates of those standards.

### Curated Disturbance Parameter Specifications:
- **Voltage Sag (IEEE 1159):** Remaining magnitude $0.45\text{ pu}$, duration $4.0\text{ cycles}$ ($66.7\text{ ms}$), onset $t = 30.0\text{ ms}$.
- **Voltage Swell (IEEE 1159):** Elevated magnitude $1.45\text{ pu}$, duration $4.0\text{ cycles}$ ($66.7\text{ ms}$), onset $t = 30.0\text{ ms}$.
- **Voltage Interruption (IEEE 1159):** Residual magnitude $0.03\text{ pu}$, duration $5.0\text{ cycles}$ ($83.3\text{ ms}$), onset $t = 30.0\text{ ms}$.
- **Harmonics (IEEE 519):** Odd integer orders ($H_3 = 0.12\text{ pu}$, $H_5 = 0.07\text{ pu}$, $H_7 = 0.04\text{ pu}$), $\text{THD} = 14.46\%$.
- **Oscillatory Transient (IEEE 1159):** Oscillation frequency $f_{\text{trans}} = 550.0\text{ Hz}$, peak addition $0.85\text{ pu}$, decay $\tau = 5.0\text{ ms}$, onset $t = 65.0\text{ ms}$.
- **Voltage Flicker (IEEE 1453):** Sub-synchronous modulation frequency $f_m = 8.0\text{ Hz}$, modulation depth $8.0\%$.
- **Voltage Notch (IEEE 519):** Commutation notch depth $0.45\text{ pu}$, notch width $0.035\times 2\pi\text{ rad}$ ($583\ \mu\text{s}$).

---

## 8. Verification & Performance Boundaries

The complete test suite verifies mathematical parity, signal processing invariants, physical disturbance generation, model inference, and dashboard backend services:

```bash
# Run the full project test suite
pytest -v
```

**Test Execution Results:**
- **Total Tests:** 324
- **Passed:** 322
- **Skipped:** 2 (CUDA acceleration conditionally skipped on CPU environments)
- **Failed:** 0
- **Execution Time:** ~13.5 seconds

> **Scope of Validation & Performance Claims**:
> - **Evaluation Domain**: Model generalization metrics (99.92% accuracy, 99.93% macro F1) are measured on the trajectory-disjoint held-out test partition (1,295 frames across 40 unseen trajectories) of the simulated WSCC 9-bus grid model. While robust to unseen network operating points within the physical simulation envelope, these results reflect electromagnetic simulations and have not yet been evaluated on real-world utility physical grid substation PMU recordings.
> - **Inference Latency**: Benchmarked single-sample CPU latency (~190 µs) measures pure Python/x86 forward-pass evaluation of the 32-feature vector on host hardware. It does not include network round-trip time, hardware-in-the-loop streaming delays, or microcontroller clock constraints (addressed separately in Phase 6).

---

## 9. Documentation Quick Links

- [Documentation Landing Page](docs/README.md)
- [Reproducing Phase 4 on a Clean Clone](docs/REPRODUCING_PHASE4.md)
- [Artifact Integrity Reconciliation Audit](docs/ARTIFACT_INTEGRITY_RECONCILIATION.md)
- [Master Project Status](docs/PROJECT_STATUS.md)
- [Authoritative Source of Truth](docs/SOURCE_OF_TRUTH.md)
- [Gate Verification Matrix (Gates 1–4D)](docs/GATE_INDEX.md)
- [Developer Quickstart & Execution Guide](RUNTHISPROJECT.md)

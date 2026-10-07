# AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation

> **Current Lifecycle Phase:** Phase 3 — Physical PQD Dataset Generation (**COMPLETE**)  
> **Next Engineering Phase:** Phase 4 — Proper 60-Hz ML Implementation (**PENDING**)  
> **Future Demonstration Target:** Phase 5 — Live Simulink Demonstration MVP (**PENDING**)  
> **Optional Extension:** Phase 6 — Embedded ESP32 Hardware-in-the-Loop Deployment (**FUTURE / OPTIONAL**)  
>
> [![Tests](https://img.shields.io/badge/tests-300%20passed-brightgreen.svg)](tests/)
> [![Sampling](https://img.shields.io/badge/sampling-5%20kHz%20%7C%20200%20ms-blue.svg)](dsp/)
> [![Grid](https://img.shields.io/badge/grid-WSCC%2060%20Hz%20IEEE%209--bus-orange.svg)](IEEE_9bus/)
> [![Classes](https://img.shields.io/badge/classes-8%20disturbances%20audited-success.svg)](data/ieee9bus_60hz/)
> [![Phase](https://img.shields.io/badge/phase%203-COMPLETE%20(Gates%201--3X)-brightgreen.svg)](docs/GATE_INDEX.md)

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

The project has completed physical electromagnetic modeling, dataset generation, feature extraction, and independent scientific audits across all **8 disturbance classes** under `data/ieee9bus_60hz/`:

| Class | Label | Frames | Physical Switching Mechanism | Key Physical Metric | Gate Status |
|---|:---:|:---:|---|---|:---:|
| **Normal** | 0 | 1,152 | Steady-state load flow (32 operating conditions) | $\text{RMS} = 0.589\text{ pu}, \text{THD} = 0.35\%$ | **PASS** (Gate 3B.1) |
| **Sag** | 1 | 1,152 | Transmission shunt fault switching (`PQD_Fault_Sag`) | Residual $0.10\text{--}0.90\text{ pu}$, $16.7\text{--}120\text{ ms}$ | **PASS** (Gate 3F) |
| **Swell** | 2 | 1,152 | Shunt capacitor bank energization (`PQD_Breaker_Swell`) | Magnitude $1.10\text{--}1.80\text{ pu}$, $16.7\text{--}120\text{ ms}$ | **PASS** (Gate 3I) |
| **Interruption** | 3 | 1,152 | Series line breaker opening (`PQD_Breaker_Interruption`) | Residual $< 0.10\text{ pu}$ (mean $0.008\text{ pu}$) | **PASS** (Gate 3L) |
| **Harmonics** | 4 | 1,152 | Non-linear load current injection (`PQD_Harm_Inj`) | Orders $H_2\text{--}H_{11}$, $\text{THD} = 5.1\%\text{--}19.8\%$ | **PASS** (Gate 3O) |
| **Flicker** | 5 | 1,152 | Sub-synchronous dynamic load modulation (`PQD_Flicker_Mod`) | $f_m \in [1, 25]\text{ Hz}$, depth $1.0\%\text{--}10.0\%$ | **PASS** (Gate 3R) |
| **Notch** | 6 | 1,152 | Commutation short-circuit switching (`PQD_Notch_Bus5`) | Width $100\text{--}900\ \mu\text{s}$, depth $20\%\text{--}70\%$ | **PASS** (Gate 3U) |
| **Transient** | 7 | 1,152 | High-frequency RLC energization (`PQD_Breaker_Transient`) | Oscillation $300\text{--}2,200\text{ Hz}$, peak $1.2\text{--}1.9\text{ pu}$ | **PASS** (Gate 3X) |

**Total Dataset Size:** 9,216 multi-phase frames across 256 independent simulation trajectories with **zero inter-trajectory leakage**.

---

## 3. Strict Engineering Freeze Rules & Architectural Invariants

1. **Pristine Reference Model Freeze:**  
   `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` is frozen as the uncorrupted reference benchmark (SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`). All disturbance injection subsystems reside exclusively in `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`.
2. **Ground-Truth Decoupling Rule:**  
   Ground-truth class labels originate strictly from **physical scenario controllers and simulation metadata**—never from machine learning predictions.
3. **Legacy ML Weights Freeze:**  
   The current runtime weights (`ml/models/model_weights_32.json`) were trained on a legacy 50-Hz synthetic dataset and remain frozen. When presented with 60-Hz IEEE 9-bus grid data, the inference engine correctly reports `model_domain_status: 'MODEL_DOMAIN_MISMATCH'`, allowing the physical rule engine to maintain 100% classification integrity. Retraining is deferred to Phase 4.
4. **Authoritative 60-Hz / 5-kHz Sampling Contract:**  
   All feature definitions, FFT harmonic bins, and sliding RMS algorithms are strictly locked to $f_0 = 60.0\text{ Hz}$, $F_s = 5,000\text{ Hz}$, and $N = 1,000$ samples (200 ms).

---

## 4. Multi-Phase Engineering Roadmap

```
  [PHASE 1: ELECTRICAL FOUNDATION] ----------------------> COMPLETE (Gate 3A)
  [PHASE 2: 60-HZ DSP & INTEGRATION BRIDGE] --------------> COMPLETE (Gates 3B, 3C)
  [PHASE 3: PHYSICAL 8-CLASS DATASET & QUALITY AUDITS] --> COMPLETE (Gates 3D - 3X)
  [PHASE 4: PROPER 60-HZ MACHINE LEARNING TRAINING] -----> NEXT
  [PHASE 5: LIVE SIMULINK DEMONSTRATION MVP] ------------> FUTURE
  [PHASE 6: EMBEDDED ESP32 HIL EXTENSION] ---------------> FUTURE / OPTIONAL
```

- **Phase 4 (Proper 60-Hz ML):** Trajectory-grouped dataset splitting, train-only scaler fitting, multi-model benchmarking (MLP, Random Forest, XGBoost), calibration, and ONNX/JSON export.
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
├── server.py                      # REST & SSE Telemetry server (port 8500)
├── app_frontend.py                # Alternative dashboard UI launcher
│
├── IEEE_9bus/                     # Power system simulation models (MATLAB/Simulink R2025a)
│   ├── IEEE_9bus_PQD_HIL_R2025a.slx  # Pristine frozen reference baseline (SHA-256 verified)
│   └── IEEE_9bus_PQD_DISTURBANCES.slx # Working disturbance model (8 injection blocks)
│
├── docs/                          # Comprehensive technical documentation & audits
│   ├── README.md                  # Documentation navigation index
│   ├── PROJECT_STATUS.md          # Master single human-readable project status
│   ├── SOURCE_OF_TRUTH.md         # Authoritative file and contract registry
│   ├── ARCHITECTURE.md            # 7-subsystem engineering specification
│   ├── ROADMAP.md                 # Multi-phase roadmap (Phases 1 through 6)
│   ├── DATASET.md                 # 8-class physical dataset specification
│   ├── STANDARDS_TRACEABILITY_INDEX.md # Standards mapping (IEEE 1159, 519, 1453)
│   ├── ML_READINESS.md            # 10-step protocol for Phase 4 ML training
│   ├── REPRODUCIBILITY.md         # Environment setup and reproduction recipes
│   ├── LIVE_MVP_PLAN.md           # Phase 5 live demonstration specification
│   ├── GATE_INDEX.md              # Gate verification matrix (Gates 1 to 3X)
│   ├── REPOSITORY_LEGACY_AUDIT.md # Component classification and legacy audit
│   └── GATE3A to GATE3X reports   # 24 immutable gate reports and quality summaries
│
├── data/
│   ├── ieee9bus_60hz/             # Authoritative 8-class 60-Hz physical datasets
│   │   ├── normal/                # 1,152 frames, 32 operating conditions
│   │   ├── sag/                   # 1,152 frames, shunt fault switching
│   │   ├── swell/                 # 1,152 frames, capacitor energization
│   │   ├── interruption/          # 1,152 frames, line breaker opening
│   │   ├── harmonics/             # 1,152 frames, non-linear load injection
│   │   ├── flicker/               # 1,152 frames, sub-synchronous modulation
│   │   ├── notch/                 # 1,152 frames, commutation short-circuits
│   │   └── transient/             # 1,152 frames, high-frequency RLC switching
│   └── pq_events.db               # SQLite database for event persistence
│
├── dsp/                           # Digital Signal Processing subsystem
│   ├── enhanced_features.py       # Authoritative 32-feature extraction engine
│   ├── waveform_frame.py          # Multi-channel waveform container & NaN guards
│   ├── standards_detector.py      # Independent IEEE physical rule engine
│   ├── phase_processor.py         # Multi-phase sliding window processor
│   ├── ring_buffer.py             # Circular streaming acquisition buffer (5 kHz)
│   └── acquisition_adapter.py     # Streaming adapters (Simulink, Simulation, Mock)
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
│       └── model_weights_32.json  # Current 32-feature weights (FROZEN pending Phase 4)
│
├── scripts/                       # Dataset generators, validators, and audit scripts
├── tests/                         # Complete automated test suite (300 passed)
├── web/                           # Live laboratory oscilloscope dashboard UI
│
├── firmware/                      # Optional Phase 6 ESP32 C++ firmware (PlatformIO)
├── hardware/                      # Optional Phase 6 analog front-end schematics
├── firebase/                      # Optional cloud telemetry bridge
└── mobile_app/                    # Optional mobile telemetry viewer
```

---

## 6. Verification & Automated Testing

The complete test suite verifies mathematical parity, signal processing invariants, physical disturbance generation, and streaming integration:

```bash
# Run the full project test suite
pytest -v
```

**Test Execution Results:**
- **Total Tests:** 302
- **Passed:** 300
- **Skipped:** 2 (CUDA acceleration conditionally skipped on CPU environments)
- **Failed:** 0
- **Execution Time:** ~7.8 seconds

---

## 7. Documentation Quick Links

- [Documentation Landing Page](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/README.md)
- [Master Project Status](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/PROJECT_STATUS.md)
- [Authoritative Source of Truth](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/SOURCE_OF_TRUTH.md)
- [Reproducibility & Execution Guide](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REPRODUCIBILITY.md)
- [Gate Verification Matrix (Gates 1–3X)](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE_INDEX.md)
- [Phase 4 ML Readiness Protocol](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ML_READINESS.md)
- [Phase 5 Live MVP Plan](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/LIVE_MVP_PLAN.md)

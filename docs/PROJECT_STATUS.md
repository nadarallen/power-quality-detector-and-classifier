# Power Quality Disturbance (PQD) Project Status

**Document Reference**: `docs/PROJECT_STATUS.md`  
**Date**: October 7, 2026  
**Project Phase**: Phase 3 (Disturbance Datasets & Physical Audits) — **COMPLETE**  
**Next Phase**: Phase 4 (60-Hz Machine Learning Training & Model Selection) — **PENDING**  
**Pristine Model Checksum Status**: **VERIFIED** (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`)  
**Test Suite Status**: **300 passed**, 2 skipped, 0 failed  

---

## 1. Project Purpose

The Power Quality Disturbance (PQD) Detection and Classification System is an end-to-end, scientifically grounded, and standards-compliant framework for real-time electrical grid monitoring. The project couples rigorous transient electromagnetic simulation in MATLAB/Simulink (Simscape Electrical) with a high-performance Python digital signal processing (DSP) pipeline and neural network classification models to detect, classify, and track the complete lifecycle of grid disturbances.

The project is designed for compliance with:
- **IEEE Std 1159-2019**: Recommended Practice for Monitoring Electric Power Quality
- **IEEE Std 519-2022**: Standard for Harmonic Control in Electric Power Systems
- **IEEE Std 1453-2022**: Recommended Practice for the Analysis of Fluctuating Installations on Power Systems
- **IEC 61000-4-30 Class A**: Electromagnetic Compatibility (EMC) Testing and Measurement Techniques — Power Quality Measurement Methods

---

## 2. System Architecture & Component Readiness

The current project architecture follows an unbroken physical-to-digital chain of custody:

```
┌────────────────────────────────────────────────────────┐
│  A. IEEE 9-Bus WSCC Simscape Electrical Network       │  [COMPLETED]
│     (60 Hz fundamental, transmission grid model)       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  B. Transmission Measurement Point: Bus 5 (230 kV PCC) │  [COMPLETED]
│     (Simultaneous 3-phase Vabc / Iabc acquisition)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  C. Resampling & Discrete Acquisition Representation   │  [COMPLETED]
│     (Fs = 5000 Hz, Ts = 200 us, N = 1000 samples)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  D. Authoritative 32-Feature Python DSP Pipeline       │  [COMPLETED]
│     (H1–H11 Goertzel bank, spectral moments, SNR)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  E. Ground-Truth & Scenario Controller                 │  [COMPLETED]
│     (100% provenance from SCENARIO_CONTROLLER)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  F. Machine Learning Classification                    │  [PENDING - Phase 4]
│     (Legacy 50-Hz MLP evaluated as OUT_OF_DOMAIN)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  G. Three-Phase Event Engine & State Lifecycle         │  [READY - Integration Verified]
│     (Multi-window merging, hysteresis, nadir tracking) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  H. Telemetry, Event Store & Live MVP UI               │  [PENDING - Phase 5]
│     (SSE streaming, CRT scope overlay, dashboard)      │
└────────────────────────────────────────────────────────┘
```

### Readiness Status by Subsystem
- **Simscape Electrical Model**: **COMPLETED** (Pristine reference preserved; working disturbance model equipped with all physical mechanisms).
- **Physical Disturbance Generation**: **COMPLETED** (All 8 classes implemented, synthesized, and audited).
- **Dataset Synthesis**: **COMPLETED** (9,216 total frames across 8 classes, 32 operating conditions, 0 leakage).
- **Production DSP Engine**: **COMPLETED** (32 features, phase-aware orthogonal SNR, numerical parity $< 10^{-3}$).
- **Three-Phase Event Engine**: **READY** (Unit and integration tested with 300 tests).
- **REST Telemetry & Ingest Server**: **READY** (`server.py`, ThreadingHTTPServer, SSE endpoints operational).
- **Machine Learning (60-Hz Native)**: **PENDING** (To be trained in Phase 4 under strict protocol).
- **Live Interactive Demonstration MVP**: **PENDING** (Interactive controller and real-time dashboard planned for Phase 5).

---

## 3. Electrical Simulation Foundation

### 3.1 IEEE 9-Bus WSCC Transmission Model
- **Grid Configuration**: 3 synchronous generators (G1, G2, G3), 3 two-winding step-up transformers, 6 transmission line sections, and 3 major load centers (Loads A, B, C).
- **Nominal Grid Frequency**: $f_0 = 60.0\,\text{Hz}$ (fundamental period $T_0 = 16.667\,\text{ms}$).
- **Base Power**: $100\,\text{MVA}$ three-phase system base.
- **Pristine Reference Model**: [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx)
  - Frozen, read-only baseline model.
  - Byte-for-byte SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`.
- **Working Disturbance Model**: [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx)
  - Derivative model housing all approved physical disturbance blocks with strict mutual dormancy logic.

### 3.2 Observation Point
- **Measurement Bus**: **Bus 5** ($230\,\text{kV}$ transmission point of common coupling, PCC).
- **Signals Monitored**: Simultaneous three-phase instantaneous voltages ($V_a, V_b, V_c$) and line currents ($I_a, I_b, I_c$).
- **Nominal Phase-to-Ground Peak**: $V_{\text{base}} = 230\,\text{kV} \times \frac{\sqrt{2}}{\sqrt{3}} \approx 187.79\,\text{kV}$.

### 3.3 Discrete Sampling Representation
- **Acquisition Sampling Rate**: $F_s = 5,000\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$).
- **Nyquist Bandwidth**: $F_{\text{Nyquist}} = 2,500\,\text{Hz}$.
- **Window Length**: $N = 1,000$ samples ($200.0\,\text{ms}$, exactly $12.0$ fundamental cycles at $60\,\text{Hz}$).
- **Sensor Noise**: Calibrated additive Gaussian noise ($52.0\,\text{dB}$ SNR) per DAQ analog front-end model.

---

## 4. Authoritative 32-Feature Production DSP Contract

Every 200-ms observation frame is processed by [`dsp/enhanced_features.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/dsp/enhanced_features.py) to extract exactly 32 features in strict sequential order:

```
 1. rms_voltage          9. h1              17. h9               25. h9_ratio
 2. peak_voltage        10. h2              18. h10              26. h11_ratio
 3. crest_factor        11. h3              19. h11              27. harmonic_energy
 4. thd                 12. h4              20. h2_ratio         28. spectral_centroid
 5. duration            13. h5              21. h3_ratio         29. spectral_bandwidth
 6. dominant_freq       14. h6              22. h4_ratio         30. spectral_entropy
 7. system_freq         15. h7              23. h5_ratio         31. spectral_flatness
 8. snr                 16. h8              24. h7_ratio         32. true_dominant_freq
```

### Critical DSP Foundations
1. **Harmonic Analysis**: Single-bin Goertzel DFT filter bank tuned to orders $H_1$ through $H_{11}$ ($60\,\text{Hz}$ to $660\,\text{Hz}$).
2. **Phase-Aware Orthogonal SNR**: Phase-invariant projection onto fundamental sine/cosine orthogonal basis, eliminating angle-dependent residual distortion.
3. **Half-Cycle Sliding RMS**: 41–42 sample sliding window for IEEE 1159 sub-cycle envelope tracking.
4. **Parity**: Python DSP matches MATLAB reference computations within absolute tolerance $\le 0.000050 < 10^{-3}$.

---

## 5. Dataset Architecture & Verification Matrix

The project has completed genuine physical electrical dataset generation for all 8 disturbance classes under `data/ieee9bus_60hz/`:

| Class | Label Index | Unique Frames | Waveform Dimensions | Features File | Scenario Catalog | Partitioning (Train / Val / Test) | Audit Verdict |
|:---|:---:|:---:|:---:|:---|:---|:---:|:---:|
| **Normal** | 0 | 1,152 | (1152, 1000, 3) | `normal_features.csv` | `operating_conditions.json` | 832 / 160 / 160 | **PASS** (Gate 3B.1) |
| **Sag** | 1 | 1,152 | (1152, 1000, 3) | `sag_features.csv` | `sag_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3F) |
| **Swell** | 2 | 1,152 | (1152, 1000, 3) | `swell_features.csv` | `swell_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3I) |
| **Interruption** | 3 | 1,152 | (1152, 1000, 3) | `interruption_features.csv` | `interruption_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3L) |
| **Harmonics** | 4 | 1,152 | (1152, 1000, 3) | `harmonics_features.csv` | `harmonics_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3O) |
| **Flicker** | 5 | 1,152 | (1152, 1000, 3) | `flicker_features.csv` | `flicker_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3R) |
| **Notch** | 6 | 1,152 | (1152, 1000, 3) | `notch_features.csv` | `notch_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3U) |
| **Transient** | 7 | 1,152 | (1152, 1000, 3) | `transient_features.csv` | `transient_scenarios.json` | 832 / 160 / 160 | **PASS** (Gate 3X) |
| **Total** | — | **9,216** | — | — | — | **6,656 / 1,280 / 1,280** | **ALL PASS** |

### Data Hygiene & Validation Highlights
- **Ground-Truth Source**: 100% of labels originate from `SCENARIO_CONTROLLER`. Zero circular reliance on ML, DSP heuristics, or event thresholds.
- **Trajectory Isolation**: Every class is partitioned strictly by continuous simulation trajectory groups. $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$ (zero data leakage).
- **Grid Coverage**: All 32 operating conditions (generation dispatch and load levels) represented across all classes.
- **Completeness**: Exactly 0 NaN, 0 Inf, and 0 duplicate waveform arrays across all 9,216 frames.

---

## 6. Machine Learning Decoupling Status

### 6.1 Current Model State
- **Model File**: [`ml/models/model_weights_32.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/ml/models/model_weights_32.json)
- **Architecture**: Compact Multi-Layer Perceptron (32 $\rightarrow$ 64 $\rightarrow$ 32 $\rightarrow$ 8, FP32).
- **Training Baseline**: EXP-003 trained on legacy 50-Hz synthetic datasets.
- **Operating Domain**: `OUT_OF_DOMAIN` when evaluated on native 60-Hz IEEE 9-bus waveforms.
- **Status**: **FROZEN**. Model weights and architecture remain strictly untouched.
- **Decoupling**: The legacy model prediction has zero influence on scenario generation, physical validation, ground-truth labeling, or audit criteria.

### 6.2 Phase 4 Machine Learning Roadmap
Retraining the neural network on the completed 60-Hz physical dataset is deferred to **Phase 4**:
1. Global dataset freeze and checksum lock.
2. Trajectory-grouped split consolidation (Train: 6,656, Val: 1,280, Test: 1,280).
3. Scaler fitting on training split only (zero leakage).
4. Multi-model baseline comparison (MLP, Random Forest, 1D-CNN).
5. Hyperparameter optimization and cross-entropy training.
6. Calibration and temperature scaling for uncertainty estimation.
7. Independent evaluation on held-out test split.
8. Model export to JSON, C++ header (`model_weights_32.h`), and TFLite Micro.

---

## 7. Global Freeze Rules

To guarantee experimental integrity and reproducibility, the following artifacts remain under absolute global freeze:
1. **Pristine Reference Model**: [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) must remain byte-for-byte identical.
2. **Feature Contract**: The 32-feature extraction signature, feature ordering, and phase-aware SNR algorithm must not be modified.
3. **Validated Datasets**: All 9,216 generated frames, features, and scenario catalogs under `data/ieee9bus_60hz/` are immutable.
4. **No Premature ML Retraining**: No model training or weight adjustments are permitted until Phase 4 begins.
5. **No Premature Live Controls**: Live demonstration controls and streaming dashboards are withheld until Phase 5.

---

## 8. Automated Testing & Verification State

The automated regression test suite contains **300 tests**, all of which pass:

```
================= 300 passed, 2 skipped, 2 warnings in 7.67s ==================
```

### Breakdown of Test Suites
- **Gate 3D / 3E / 3F (Voltage Sag)**: 29 tests
- **Gate 3G / 3H / 3I (Voltage Swell)**: 25 tests
- **Gate 3J / 3K / 3L (Voltage Interruption)**: 26 tests
- **Gate 3M / 3N / 3O (Harmonics)**: 24 tests
- **Gate 3P / 3Q / 3R (Voltage Flicker)**: 24 tests
- **Gate 3S / 3T / 3U (Voltage Notch)**: 26 tests
- **Gate 3V / 3W / 3X (Oscillatory Transient)**: 26 tests
- **Integration, SNR, Phase Processor & Pipeline**: 120 tests

---

## 9. Current Phase Status Summary

```
============================================================
PHASE 3 STATUS  = COMPLETE
PHASE 4 (ML)    = PENDING
PHASE 5 (DEMO)  = PENDING
============================================================
```

# Power Quality Disturbance (PQD) Project Roadmap

**Document Reference**: `docs/ROADMAP.md`  
**Date**: October 27, 2026  
**Status**: ACTIVE  
**Current Milestone**: Phase 5 Complete (Comparative Research Study, Multi-Model Benchmark & Research Dashboard)  

---

## 1. High-Level Project Phase Lifecycle

```
┌────────────────────────────────────────────────────────┐
│  PHASE 1: Electrical Simulation Foundation             │  [COMPLETE]
│  • WSCC 9-bus SimPowerSystems implementation           │
│  • Load flow, dispatch & 32 operating conditions       │
│  • Pristine reference model freeze & checksum lock     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 2: DSP Foundation & System Integration          │  [COMPLETE]
│  • 32-feature extraction pipeline                      │
│  • Phase-aware orthogonal SNR algorithm                │
│  • Goertzel filter bank H1–H11 & spectral metrics      │
│  • MATLAB/Python numerical parity (< 1e-3)             │
│  • Event engine lifecycle & REST streaming server      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 3: Disturbance Mechanisms & Dataset Generation  │  [COMPLETE]
│  • Gates 3A through 3X completed                       │
│  • 8 physical classes (Normal + 7 disturbances)        │
│  • 9,184 unique 200-ms frames across 284 trajectories  │
│  • Trajectory-grouped partitions (0 leakage)           │
│  • Independent 16-domain physical audits (100% pass)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 4: 60-Hz Machine Learning Training & Evaluation │  [PENDING]
│  • Global dataset freeze & feature scaling             │
│  • Multi-model baseline comparison (MLP, RF, 1D-CNN)   │
│  • Hyperparameter tuning & cross-entropy training      │
│  • Independent test set evaluation & calibration       │
│  • Model export (JSON, C++ header, TFLite Micro)       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 5: Live Interactive Demonstration MVP           │  [PENDING]
│  • Demo derivative Simulink model & PQD Rack           │
│  • Interactive PQD Controller & MATLAB trigger         │
│  • Sliding ring buffer & continuous streaming bridge   │
│  • Live CRT oscilloscope & web telemetry dashboard     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 6: Optional Hardware-in-the-Loop & Deployment   │  [PLANNED]
│  • ESP32 microcontroller edge inference                │
│  • High-voltage safety front-end & hardware DAQ        │
│  • Embedded latency benchmarks & field validation      │
└────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Detailed Breakdown

### Phase 1 — Electrical Foundation (`COMPLETE`)
- [x] **WSCC 3-Machine 9-Bus System**: Implemented in Simscape Electrical Specialized Power Systems.
- [x] **60-Hz Grid Adaptation**: Converted and validated power system nominal frequency to $60.0\,\text{Hz}$.
- [x] **32 Operating Conditions**: Defined generation dispatch, voltage setpoints, and load scaling across 3 load centers.
- [x] **Bus 5 Transmission PCC**: Selected Bus 5 ($230\,\text{kV}$) as the central monitoring bus.
- [x] **Pristine Reference Freeze**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` SHA-256 frozen at `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`.

### Phase 2 — DSP & Integration Foundation (`COMPLETE`)
- [x] **32-Feature Contract**: Implemented authoritative 32-feature production DSP in [`dsp/enhanced_features.py`](../dsp/enhanced_features.py).
- [x] **Goertzel Harmonic Bank**: Single-bin DFT filters tuned to orders $H_1$ through $H_{11}$ ($60\text{--}660\,\text{Hz}$).
- [x] **Phase-Aware Orthogonal SNR**: Replaced angle-sensitive formula with projection-based calculation.
- [x] **Half-Cycle Sliding RMS**: IEC 61000-4-30 sliding RMS implementation for sub-cycle envelope tracking.
- [x] **MATLAB/Python Parity**: Parity verified across all DSP features within tolerance $< 10^{-3}$.
- [x] **Three-Phase Event Engine**: Multi-window aggregation, dynamic phase expansion, and hysteresis state machine.
- [x] **Telemetry & Ingestion Server**: ThreadingHTTPServer with REST `/api/ingest`, `/api/events`, and SSE `/api/telemetry`.

### Phase 3 — Disturbance Datasets & Independent Audits (`COMPLETE`)
All 8 disturbance classes have completed physical simulation, dataset extraction, and independent audits:
- [x] **Gate 3B / 3B.1 (Normal)**: 1,120 frames, steady-state load flow across 32 grid conditions.
- [x] **Gate 3D / 3E / 3F (Voltage Sag)**: 1,152 frames, shunt fault switching on Bus 5 (`PQD_Fault_Sag`), depths 0.10–0.90 pu.
- [x] **Gate 3G / 3H / 3I (Voltage Swell)**: 1,152 frames, capacitor bank energization (`PQD_Breaker_Swell`), magnitudes 1.10–1.80 pu.
- [x] **Gate 3J / 3K / 3L (Voltage Interruption)**: 1,152 frames, series line breaker + feeder isolation (`PQD_Breaker_Interruption`), residual < 0.10 pu.
- [x] **Gate 3M / 3N / 3O (Harmonics)**: 1,152 frames, non-linear load current injection H2/H3/H5/H7/H9/H11 (`PQD_Harm_Inj`), THD 5.1–19.8%.
- [x] **Gate 3P / 3Q / 3R (Voltage Flicker)**: 1,152 frames, sub-synchronous load modulation $1\text{--}25\,\text{Hz}$ (`PQD_Flicker_Mod`), depths 1.0–10.0%.
- [x] **Gate 3S / 3T / 3U (Voltage Notch)**: 1,152 frames, thyristor bridge commutation switching (`PQD_Notch_Bus5`), widths 0.43–2.97 ms, depths 22.9–53.8%.
- [x] **Gate 3V / 3W / 3X (Oscillatory Transient)**: 1,152 frames, capacitor energization ringing $250\text{--}300\,\text{Hz}$ (`PQD_Breaker_Transient`), peak excursion 0.13–0.41 pu.
- [x] **Zero Trajectory Leakage**: Every dataset partitioned strictly by simulation trajectory (Total: 6,594 Train / 1,295 Val / 1,295 Test across 284 trajectories, 9,184 total frames).
- [x] **Complete Audits**: 16-domain independent audits passed for all classes with 100% physical validation pass rates.

### Phase 4 — Native 60-Hz Machine Learning Training (`COMPLETE - HISTORICAL BASELINE`)
- [x] **Final Dataset Freeze**: Consolidated dataset checksums locked across all 9,184 frames (`data/ieee9bus_60hz/dataset_manifest_v1.json`).
- [x] **Data Preprocessing & Scaling**: Fit `StandardScaler` strictly on training set ($N = 6,594$), transform validation ($N = 1,295$) and test sets ($N = 1,295$).
- [x] **Baseline Model Comparison**: Trained and benchmarked candidate architectures:
  - Multi-Layer Perceptron (MLP, 32 $\rightarrow$ 64 $\rightarrow$ 32 $\rightarrow$ 8)
  - Random Forest Classifier (100 trees)
  - 1D Convolutional Neural Network
- [x] **Hyperparameter Optimization**: Grid search across architectures and loss functions.
- [x] **Independent Test Evaluation**: Evaluated on historical test split ($N = 1,295$) with 100% Macro F1 on historical conditions.
- [x] **Artifact Preservation**: Preserved historical models and evaluation records intact under global freeze.

### Phase 5 — Multi-Model Comparative Research Study & Dashboard (`COMPLETE`)
- [x] **Expanded Experiment Design**: Formulated 368-trajectory extended matrix across 40 operating conditions with 8 quarantined challenge conditions (`scenarios/phase5c_extended_matrix.json`).
- [x] **High-Rate & Dual-Rate Acquisition**: Executed 144 core trajectories in MATLAB R2025a, producing genuine 20 kHz waveforms (`phase5c_waveforms_20k.npz`) and anti-aliased 5 kHz canonical waveforms (`phase5c_waveforms_5k.npz`).
- [x] **Physical Validation Gate**: Audited electrical features, identifying 118 PASS and 26 FLAGGED cases in `physical_validation_failures.json` without weakening thresholds.
- [x] **Dataset Freeze Audit**: Published `docs/PHASE5C_EXPANDED_DATASET_FREEZE_AUDIT.md` confirming zero leakage.
- [x] **Track A Classical ML Benchmark**: Benchmarked 6 classifiers on 32 features; identified constant features (`dominant_freq`, `true_dominant_freq`), computed permutation importance, and executed functional group ablations (`docs/PHASE5D_CLASSICAL_ML_AND_FEATURE_ANALYSIS.md`).
- [x] **Track B Raw-Waveform Deep Learning**: Built and benchmarked 1D-CNN and Temporal ConvNet (TCN); performed temporal occlusion sensitivity and 3-phase cross-coupling ablations (`docs/PHASE5E_WAVEFORM_DEEP_LEARNING.md`).
- [x] **Track C Hybrid Representation Models**: Architected `HybridPQNet` fusing 20 kHz waveform embeddings with 32 engineered features, demonstrating +11.08% F1 gain over features alone (`docs/PHASE5F_HYBRID_MODEL_ANALYSIS.md`).
- [x] **One-Time Quarantined Challenge Evaluation**: Evaluated frozen candidates once on held-out Conditions 33–36 (1,024 frames); `HybridPQNet` achieved 100.00% Macro F1 with 0.00% generalization gap (`docs/PHASE5G_FINAL_COMPARATIVE_EVALUATION.md`).
- [x] **Demonstration Dashboard Integration**: Integrated 5-tab Phase 5 Comparative Research Explorer into `app.py` and `dashboard_backend.py` with standalone recorded mode.
- [x] **Master Scientific Research Report**: Published comprehensive research monograph in `docs/PHASE5_FINAL_RESEARCH_REPORT.md`.

### Phase 6 — Optional Hardware-in-the-Loop & Advanced Deployment (`PLANNED`)
- [ ] **ESP32 Edge Deployment**: Flash exported C++ MLP weights to ESP32 microcontroller and verify embedded execution latency ($< 35\,\text{ms}$).
- [ ] **Analog Safety Front-End**: Interface physical voltage transducers with ESP32 ADC channels.
- [ ] **Full HIL Closed Loop**: Drive hardware ADC inputs from real-time simulator DAC outputs and stream classification results over UART/WiFi.

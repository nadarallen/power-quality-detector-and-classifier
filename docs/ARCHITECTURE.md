# System Architecture: Power Quality Disturbance Detection and Classification

**Document Reference**: `docs/ARCHITECTURE.md`  
**Date**: October 7, 2026  
**Status**: ACTIVE / UPDATED  
**Architecture Domain**: End-to-End Simulation-to-Telemetry PQD Pipeline  

---

## 1. Architectural Philosophy & Design Principles

The Power Quality Disturbance (PQD) Detection and Classification System couples transient electromagnetic simulation in MATLAB/Simulink with an authoritative Python digital signal processing (DSP) engine, a state-machine event tracking engine, and a neural network inference architecture.

### Core Architectural Decisions & Rationales
1. **Pristine Reference Model Remains Frozen**:
   - [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) is the untouched scientific baseline. Its SHA-256 hash (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`) serves as the permanent anchor guaranteeing that all baseline power flows, impedance matrices, and generator dynamics are standard and untainted.
2. **Working Disturbance Model Exists as a Controlled Derivative**:
   - [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) houses the physical disturbance switching blocks (`PQD_Fault_Sag`, `PQD_Breaker_Swell`, `PQD_Breaker_Interruption`, `PQD_Harm_Inj`, `PQD_Flicker_Mod`, `PQD_Notch_Bus5`, and `PQD_Breaker_Transient`). Each block possesses explicit mutual dormancy logic such that when disabled, it acts as an open circuit ($R_{off} = 1\,\text{M}\Omega$, $0.0\,\text{A}$ injection), preserving pristine network behavior.
3. **Bus 5 is the Central Transmission Observation Point**:
   - Bus 5 is a $230\,\text{kV}$ transmission point of common coupling (PCC) connected to generator Bus 4 (via step-up transformer) and load Bus 7. Observing Bus 5 captures both local disturbance dynamics and grid-propagated network reflections without placing instrumentation inside generator internal sub-circuits.
4. **60 Hz Fundamental Grid Frequency is Authoritative**:
   - The WSCC 9-bus system is inherently a North American 60-Hz grid model ($f_0 = 60.0\,\text{Hz}$, $T_0 = 16.667\,\text{ms}$). All filters, Goertzel harmonic bins ($60\text{--}660\,\text{Hz}$), and half-cycle RMS sliding windows ($8.33\,\text{ms}$) are precisely synchronized to $60\,\text{Hz}$.
5. **Discrete Representation at 5 kHz ($200\,\mu\text{s}$)**:
   - $F_s = 5000\,\text{Hz}$ represents standard commercial power quality digital fault recorder (DFR) and micro-PMU acquisition rates. It yields an exact 1,000 samples over a 12-cycle ($200\,\text{ms}$) window and a Nyquist bandwidth of $2500\,\text{Hz}$, comfortably resolving harmonic orders up to $H_{11}$ ($660\,\text{Hz}$), commutation notches down to $0.4\,\text{ms}$, and low-frequency oscillatory transients ($250\text{--}1200\,\text{Hz}$).
6. **Ground Truth Originates 100% from Scenario Controller**:
   - Ground truth labels are derived exclusively from the physical simulation driver (`SCENARIO_CONTROLLER`). They are never derived from ML predictions, DSP thresholds, harmonic percentages, or event engine state transitions.
7. **Raw ML Predictions Kept Strictly Decoupled from Physical Truth**:
   - The legacy MLP model weights remain frozen in their legacy state and evaluate 60-Hz physical waveforms as `OUT_OF_DOMAIN`. Decoupling ML inference from physical validation prevents circular validation and ensures that dataset quality is judged purely on electromagnetic physics.
8. **Retraining Deferred Until Full Dataset Completion**:
   - Retraining before all 8 disturbance classes are simulated, validated, and audited would introduce catastrophic class bias, invalid preprocessing leakage, and wasted computational effort. Full dataset completion (Phase 3) is a mandatory precondition for Phase 4 ML training.

---

## 2. Subsystem Breakdown

```
┌────────────────────────────────────────────────────────────────────────┐
│  A. ELECTRICAL SIMULATION (MATLAB / Simulink Simscape Electrical)      │
│  • WSCC 9-bus 60-Hz transmission network (3 gens, 3 transformers, 3 loads)│
│  • Bus 5 PCC voltage (Vabc) and current (Iabc) acquisition            │
│  • Physical disturbance injection blocks with mutual dormancy          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  B. ACQUISITION & INTEGRATION BRIDGE (MATLAB -> Python)               │
│  • Continuous variable-step ode23tb solver resampled to 5000 Hz        │
│  • 1000-sample (200 ms) window extraction with 52 dB SNR sensor noise  │
│  • WaveformFrame data structure: (1000, 3) float32 arrays              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  C. DIGITAL SIGNAL PROCESSING (dsp/enhanced_features.py)               │
│  • Authoritative 32-feature contract                                   │
│  • Single-bin Goertzel DFT bank H1–H11 (60 Hz to 660 Hz)               │
│  • Phase-aware orthogonal projection SNR algorithm                     │
│  • Half-cycle sliding RMS envelope (IEC 61000-4-30)                    │
│  • Full numerical parity with MATLAB reference (< 1e-3)                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  D. THREE-PHASE EVENT ENGINE (dsp/event_engine.py)                     │
│  • Per-phase state machines (Normal <-> Disturbance)                   │
│  • Multi-window sliding aggregation and disturbance deduplication      │
│  • Dynamic multi-phase expansion (e.g., A -> AB -> ABC)                │
│  • Monotonic nadir and crest envelope aggregation                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  E. MACHINE LEARNING LAYER (ml/models/ & dsp/phase_processor.py)       │
│  • Current: Compact MLP (32->64->32->8) evaluated as OUT_OF_DOMAIN    │
│  • Uncertainty gate: confidence < 60% marked UNCERTAIN                 │
│  • Future Phase 4: Native 60-Hz multi-model training & calibration     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  F. STORAGE, REST API & TELEMETRY (storage/ & server.py)               │
│  • Embedded SQLite persistence (storage/event_store.py)                │
│  • REST API endpoints: GET /api/health, /api/events, POST /api/ingest │
│  • Server-Sent Events (SSE) stream: GET /api/telemetry                 │
│  • Web dashboard UI: CRT oscilloscope overlay (web/index.html)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  G. FUTURE LIVE CONTROLLER & SIMULATION RACK (Planned Phase 5)         │
│  • Dedicated demo derivative model: IEEE_9bus_PQD_DEMO.slx             │
│  • Interactive PQD Controller & MATLAB disturbance trigger GUI         │
│  • Rolling continuous acquisition and real-time inference bridge       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Detailed Specifications

### 3.1 Subsystem A: Electrical Simulation
- **Platform**: MATLAB R2024b / R2025a, Simulink, Simscape Electrical Specialized Power Systems.
- **Topology**: IEEE 9-bus WSCC transmission grid.
- **Components**:
  - Generator 1 (Swing, $247.5\,\text{MVA}$, $16.5\,\text{kV}$)
  - Generator 2 ($192\,\text{MVA}$, $18\,\text{kV}$)
  - Generator 3 ($128\,\text{MVA}$, $13.8\,\text{kV}$)
  - Step-up transformers ($16.5/230\,\text{kV}$, $18/230\,\text{kV}$, $13.8/230\,\text{kV}$)
  - 6 transmission lines with $\Pi$-section distributed parameter modeling.
  - Three nominal loads: Load A ($125\,\text{MW}, 50\,\text{MVAR}$), Load B ($90\,\text{MW}, 30\,\text{MVAR}$), Load C ($100\,\text{MW}, 35\,\text{MVAR}$).
- **Working Disturbance Subsystems**:
  - `PQD_Fault_Sag`: Shunt fault breaker to ground/phase on Bus 5.
  - `PQD_Breaker_Swell`: Three-phase capacitor bank energization ($50\text{--}150\,\text{MVAR}$).
  - `PQD_Breaker_Interruption`: Series line-opening breaker on Line 4-5 + feeder isolation breaker.
  - `PQD_Harm_Inj`: Controlled harmonic current source injecting odd and even orders $H_2\text{--}H_{11}$.
  - `PQD_Flicker_Mod`: Dynamically modulated dynamic load impedance ($1\text{--}25\,\text{Hz}$).
  - `PQD_Notch_Bus5`: Three-phase commutation fault block with sub-cycle pulse timing ($0.4\text{--}3.0\,\text{ms}$).
  - `PQD_Breaker_Transient`: Three-phase breaker switched into grounded series RLC branch ($250\text{--}300\,\text{Hz}$).

### 3.2 Subsystem B: Acquisition & Integration Bridge
- **Solver**: `ode23tb` (stiff trapezoidal / backward differentiation formula).
- **RelTol**: $10^{-4}$, **MaxStep**: $10^{-4}\,\text{s}$ ($100\,\mu\text{s}$) for transient and notch resolution.
- **Resampling**: Linear interpolation resampling to exact uniform grid at $F_s = 5000.0\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$).
- **Windowing**: Slices sliding 1,000-sample ($200.0\,\text{ms}$) windows with calibrated Gaussian sensor noise at $52.0\,\text{dB}$ SNR.

### 3.3 Subsystem C: Digital Signal Processing (DSP)
- **Feature Space**: Authoritative 32-feature contract:
  - 4 statistical / envelope metrics: `rms_voltage`, `peak_voltage`, `crest_factor`, `thd`.
  - 4 temporal / fundamental metrics: `duration`, `dominant_freq`, `system_freq`, `snr`.
  - 11 harmonic magnitudes: `h1` through `h11` ($60\,\text{Hz}$ to $660\,\text{Hz}$).
  - 7 harmonic ratios: `h2_ratio`, `h3_ratio`, `h4_ratio`, `h5_ratio`, `h7_ratio`, `h9_ratio`, `h11_ratio`.
  - 1 energy metric: `harmonic_energy`.
  - 5 spectral distribution metrics: `spectral_centroid`, `spectral_bandwidth`, `spectral_entropy`, `spectral_flatness`, `true_dominant_freq`.
- **Orthogonal Projection SNR**: Projects signal vector onto fundamental basis $[\cos(\omega_0 t), \sin(\omega_0 t)]$ and calculates noise power from the orthogonal residual, guaranteeing phase angle invariance.

### 3.4 Subsystem D: Three-Phase Event Engine
- **Per-Phase Lifecycle**: Tracks each phase independently through states: `NORMAL`, `PRE_DISTURBANCE`, `ACTIVE_DISTURBANCE`, `RECOVERY`.
- **Aggregation**: Merges overlapping 200-ms sliding windows into single continuous physical events.
- **Multi-Phase Association**: Associates concurrent phase events into unified multi-phase disturbances (`phase_configuration`: `three-phase`, `phase-to-phase`, `single-phase`).

### 3.5 Subsystem E: Machine Learning
- **Frozen Legacy Architecture**: 32 $\rightarrow$ 64 $\rightarrow$ 32 $\rightarrow$ 8 Multi-Layer Perceptron.
- **Weights Location**: `ml/models/model_weights_32.json`.
- **Decoupled Evaluation**: Operates as a diagnostic observer during Phase 3, marking 60-Hz physical inputs as `OUT_OF_DOMAIN`. Retraining is strictly quarantined to Phase 4.

### 3.6 Subsystem F: Telemetry, Persistence & Live MVP Dashboard
- **Storage**: SQLite embedded relational database (`storage/event_store.py`) recording event metadata, start/end timestamps, affected phases, nadir/crest values, and feature vectors.
- **HTTP Server**: Python `ThreadingHTTPServer` (`server.py`) serving:
  - REST endpoints: `GET /api/health`, `GET /api/events`, `POST /api/ingest`, `POST /api/simulation/disturbance`.
  - Server-Sent Events (SSE): `GET /api/telemetry` pushing 50 Hz frame updates to connected clients.
- **Frontend**: Lightweight vanilla HTML5/CSS/JavaScript interface (`web/index.html`) featuring real-time CRT oscilloscope canvas overlay, 3-phase grid status bar, and harmonic spectrum charts.

---

## 4. Current Operational Mode: Deterministic Replay vs Live Streaming

> [!IMPORTANT]
> The current verified state of the repository operates in **deterministic offline batch simulation and validated replay mode**. Full concurrent, real-time closed-loop Simulink streaming is an objective of **Phase 5 (Live Demonstration MVP)** and is **NOT** claimed to be fully active today.

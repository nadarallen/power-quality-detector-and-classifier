# Power Quality Disturbance (PQD) Detection and Classification System

> **Validated Electromagnetic Simulation, Physics-Grounded Datasets & Power Quality DSP Architecture**  
> Compliant with **IEEE Std 1159-2019**, **IEEE Std 519-2022**, **IEEE Std 1453-2022**, and **IEC 61000-4-30 Class A**.  
> ![Tests](https://img.shields.io/badge/tests-300%20passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.10%20|%203.12%20|%203.14-blue) ![MATLAB](https://img.shields.io/badge/MATLAB-R2024b%20|%20R2025a-orange) ![Phase](https://img.shields.io/badge/Phase%203-COMPLETE-success) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 📌 Executive Summary

This repository implements an end-to-end, scientifically validated, and standards-compliant framework for detecting, categorizing, and monitoring **Power Quality Disturbances (PQD)** in high-voltage power transmission networks.

The core of the system bridges genuine electromagnetic simulation of the **WSCC 3-Machine 9-Bus System** (operating at $60.0\,\text{Hz}$ in Simscape Electrical) to a production-grade Python digital signal processing (DSP) pipeline. The pipeline ingests continuous three-phase voltages ($V_a, V_b, V_c$) sampled at $F_s = 5000\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$, $N = 1000$ discrete samples per 12-cycle observation window), extracts an authoritative 32-feature mathematical contract (including Goertzel harmonic orders $H_1\text{--}H_{11}$, phase-invariant orthogonal SNR, and IEC 61000-4-30 sliding RMS), and tracks disturbance states across multi-phase lifecycles.

```
┌────────────────────────────────────────────────────────────────────────┐
│               A. SIMULATION & PHYSICAL GENERATION (Simscape)           │
│                                                                        │
│   • WSCC 9-Bus 60-Hz Network (3 synchronous generators, 3 loads)       │
│   • Observation Interface: Bus 5 (230 kV Transmission PCC)             │
│   • 8 Physical Classes: Normal, Sag, Swell, Interruption, Harmonics,   │
│     Flicker, Notch, Oscillatory Transient                              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               B. DISCRETE ACQUISITION & INTEGRATION BRIDGE             │
│                                                                        │
│   • Sampling representation: Fs = 5000 Hz (Ts = 200 us, N = 1000)      │
│   • 12 fundamental cycles per 200-ms frame (f0 = 60.0 Hz)              │
│   • 52 dB SNR calibrated analog front-end sensor noise                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               C. AUTHORITATIVE 32-FEATURE DSP CONTRACT                 │
│                                                                        │
│   • Goertzel Filter Bank H1–H11 (60 Hz to 660 Hz single-bin DFT)       │
│   • Phase-Aware Orthogonal Projection SNR (angle-invariant)            │
│   • Half-Cycle Sliding RMS (41–42 sample IEC 61000-4-30 tracking)      │
│   • Spectral moments, entropy, flatness, crest factor, and THD         │
│   • MATLAB/Python numerical feature parity verified (< 0.000050)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               D. THREE-PHASE EVENT ENGINE & TELEMETRY STREAM           │
│                                                                        │
│   • Per-phase state machine: Normal <-> Active Disturbance             │
│   • Multi-window sliding aggregation & disturbance deduplication       │
│   • REST Ingestion & Event API (server.py :8500)                       │
│   • Server-Sent Events (SSE) telemetry stream & CRT Oscilloscope UI    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Current Project State & Completed Work

### Phase 3 Complete: Disturbance Datasets & Independent Audits
The project has completed genuine physical electromagnetic simulation, dataset extraction, and independent audits across all 8 disturbance classes under `data/ieee9bus_60hz/`:

| Class | Label | Frames | Physical Switching Mechanism | Key Physical Metric | Audit Status |
|:---|:---:|:---:|:---|:---|:---:|
| **Normal** | 0 | 1,152 | Steady-state load flow (32 operating conditions) | $\text{RMS} = 0.589\,\text{pu}, \text{THD} = 0.35\%$ | **PASS** (Gate 3B.1) |
| **Sag** | 1 | 1,152 | Transmission shunt fault switching (`PQD_Fault_Sag`) | Residual $0.10\text{--}0.90\,\text{pu}$, $16.7\text{--}120\,\text{ms}$ | **PASS** (Gate 3F) |
| **Swell** | 2 | 1,152 | Shunt capacitor bank energization (`PQD_Breaker_Swell`) | Magnitude $1.10\text{--}1.80\,\text{pu}$, $16.7\text{--}120\,\text{ms}$ | **PASS** (Gate 3I) |
| **Interruption** | 3 | 1,152 | Series line breaker opening (`PQD_Breaker_Interruption`) | Residual $< 0.10\,\text{pu}$ (mean $0.008\,\text{pu}$) | **PASS** (Gate 3L) |
| **Harmonics** | 4 | 1,152 | Non-linear load current injection (`PQD_Harm_Inj`) | Orders $H_2\text{--}H_{11}$, $\text{THD} = 5.1\%\text{--}19.8\%$ | **PASS** (Gate 3O) |
| **Flicker** | 5 | 1,152 | Sub-synchronous dynamic load modulation (`PQD_Flicker_Mod`) | $f_m \in [1, 25]\,\text{Hz}$, depth $1.0\%\text{--}10.0\%$ | **PASS** (Gate 3R) |
| **Notch** | 6 | 1,152 | Power electronic bridge commutation (`PQD_Notch_Bus5`) | Width $0.43\text{--}2.97\,\text{ms}$, depth $22.9\%\text{--}53.8\%$ | **PASS** (Gate 3U) |
| **Transient** | 7 | 1,152 | Grounded series RLC breaker energization (`PQD_Breaker_Transient`) | Freq $250\text{--}299\,\text{Hz}$, excursion $0.13\text{--}0.41\,\text{pu}$ | **PASS** (Gate 3X) |
| **Total** | — | **9,216** | **100% Genuine Physical Electrical Simulation** | **Zero trajectory leakage ($\text{Train} \cap \text{Val} \cap \text{Test} = \emptyset$)** | **ALL PASS** |

### Machine Learning Status
- **Current Model State**: The existing MLP model (`ml/models/model_weights_32.json`) remains frozen in its legacy state and is marked `OUT_OF_DOMAIN` when evaluated on 60-Hz physical waveforms.
- **Phase 4 Retraining**: Retraining of neural network classifiers is **PENDING** and will be conducted during Phase 4 using the locked 60-Hz physical dataset.

---

## 🔬 Standards Traceability

| Standard | Scope in This Project | Traceability & Limits |
|:---|:---|:---|
| **IEEE Std 1159-2019** | Categorization of Sags, Swells, Interruptions, Notches, and Oscillatory Transients. | Distinguishes sub-cycle notches ($< 0.5$ cycle) and low-frequency transients ($< 5\,\text{kHz}$) from RMS events. |
| **IEEE Std 519-2022** | Voltage harmonic distortion limits and commutation notch depths at the PCC. | Harmonic orders $H_2$ through $H_{11}$ evaluated at Bus 5 ($230\,\text{kV}$ PCC). |
| **IEEE Std 1453-2022** | Voltage flicker envelope modulation concept. | Evaluates sub-synchronous envelope modulation in $[1.0, 25.0]\,\text{Hz}$. |
| **IEC 61000-4-30 Class A** | Half-cycle sliding RMS calculation. | Implemented via 41–42 sample sliding convolution window at $5\,\text{kHz}$. |

---

## 📂 Repository Organization

```
├── IEEE_9bus/                    # Simscape Electrical models
│   ├── IEEE_9bus_PQD_HIL_R2025a.slx     # Pristine frozen reference model
│   └── IEEE_9bus_PQD_DISTURBANCES.slx   # Working disturbance generation model
├── data/
│   └── ieee9bus_60hz/            # 60-Hz physical datasets (8 classes)
│       ├── normal/               # Normal baseline (1,152 frames, 32 conditions)
│       ├── sag/                  # Voltage Sag dataset (1,152 frames)
│       ├── swell/                # Voltage Swell dataset (1,152 frames)
│       ├── interruption/         # Voltage Interruption dataset (1,152 frames)
│       ├── harmonics/            # Harmonics dataset (1,152 frames)
│       ├── flicker/              # Voltage Flicker dataset (1,152 frames)
│       ├── notch/                # Voltage Notch dataset (1,152 frames)
│       └── transient/            # Oscillatory Transient dataset (1,152 frames)
├── dsp/                          # Production DSP feature extraction & state engine
│   ├── enhanced_features.py      # Authoritative 32-feature extraction contract
│   ├── event_engine.py           # Three-phase state machine & event lifecycle
│   ├── phase_processor.py        # Per-phase inference & uncertainty gate
│   └── waveform_frame.py         # WaveformFrame multi-channel data container
├── pipeline/
│   └── disturbance_validator.py  # Independent physical validation gates (TRN, NOT, FLK, etc.)
├── scenarios/
│   └── scenario_controller.py    # Ground-truth scenario controller & hash verifier
├── scripts/                      # Batch simulation runners & audit tools
│   ├── generate_ieee9bus_*.m     # MATLAB batch simulation scripts (36 trajectories/class)
│   ├── build_and_validate_*.py   # Frame extraction, production DSP & validation
│   └── audit_gate3*_*.py         # Independent 16-domain audit scripts
├── tests/                        # Automated pytest suite (300 passing tests)
├── docs/                         # Comprehensive gate documentation & audit reports
│   ├── PROJECT_STATUS.md         # Master project status & architecture state
│   ├── GATE_INDEX.md             # Complete gate registry (Gates 1 through 3X)
│   ├── ROADMAP.md                # Multi-phase engineering roadmap
│   ├── ARCHITECTURE.md           # End-to-end architectural specifications
│   ├── DATASET.md                # Comprehensive dataset profiles & metrics
│   ├── STANDARDS_TRACEABILITY_INDEX.md # Standards mapping & provenance taxonomy
│   ├── ML_READINESS.md           # Phase 4 machine learning preparation protocol
│   └── REPRODUCIBILITY.md        # Environment setup, execution & checksum guide
├── server.py                     # Python REST & Server-Sent Events (SSE) server
└── web/                          # Telemetry dashboard & live CRT oscilloscope overlay
```

---

## 🚀 Quickstart & Reproducibility

### 1. Verify Pristine Model Integrity
```bash
python -c "import hashlib; h = hashlib.sha256(open('IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx', 'rb').read()).hexdigest().upper(); print('SHA-256:', h); assert h == '5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D'"
```

### 2. Run the Full Test Suite
```bash
pytest -v
```
*Expected: 300 passed, 2 skipped, 0 failed in ~8s.*

### 3. Start Telemetry Server & Dashboard
```bash
python server.py 8500
```
Open your browser to `http://localhost:8500` to inspect real-time telemetry streaming and event logs.

---

## ⚠️ Important Limitations & Scope Boundaries

1. **Sampling Bandwidth ($F_s = 5000\,\text{Hz}$)**: The discrete Nyquist limit is $2500\,\text{Hz}$. Ultra-high-frequency impulsive transients ($> 2.5\,\text{kHz}$) cannot be represented without aliasing and are excluded.
2. **200-ms Observation Window**: A single 200-ms frame provides instantaneous point-on-wave classification; it does not replace 10-minute statistical flicker surveys ($P_{st}$) or 7-day harmonic surveys.
3. **Current Operational Mode**: The current implementation operates as a validated offline simulation-to-Python integration. Full live closed-loop Simulink streaming is scheduled for **Phase 5 (Live Demonstration MVP)**.

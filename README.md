# AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation

> **Target Research Branch:** `research/pq-comparative-lab`
> **Stable Baseline Branch:** `main` (Preserved intact at `8a4e567`)
>
> [![Tests](https://img.shields.io/badge/tests-426%20passed-brightgreen.svg)](tests/)
> [![Sampling](https://img.shields.io/badge/sampling-5%20kHz%20Bus%205%20VI-blue.svg)](data/ieee9bus_60hz/)
> [![Grid](https://img.shields.io/badge/grid-IEEE%209--bus%2060%20Hz-orange.svg)](IEEE_9bus/)
> [![Classes](https://img.shields.io/badge/classes-8%20disturbances%20audited-success.svg)](experiments/phase4c/models/)
> [![ML Architecture](https://img.shields.io/badge/ML%20Model-Phase%204C%20MLP%20(32%20features)-brightgreen.svg)](experiments/phase4c/models/)
> [![One-Command Launch](https://img.shields.io/badge/presentation-Start--Presentation.cmd-blue.svg)](Start-Presentation.cmd)

---

## Table of Contents

1. [Project Overview & Engineering Problem](#1-project-overview--engineering-problem)
2. [IEEE 9-Bus System & Simscape Electrical Architecture](#2-ieee-9-bus-system--simscape-electrical-architecture)
3. [Bus 5 Voltage & Current Acquisition Path](#3-bus-5-voltage--current-acquisition-path)
4. [Continuous Telemetry & Level-2 S-Function Streamer](#4-continuous-telemetry--level-2-s-function-streamer)
5. [Disturbance Injection Subsystems](#5-disturbance-injection-subsystems)
6. [Digital Signal Processing (32 Enhanced Features)](#6-digital-signal-processing-32-enhanced-features)
7. [FFT Spectrum Analysis & Harmonic Characterization](#7-fft-spectrum-analysis--harmonic-characterization)
8. [Machine Learning Classification Pipeline](#8-machine-learning-classification-pipeline)
9. [Web Dashboard & Engineering Interface](#9-web-dashboard--engineering-interface)
10. [One-Command Presentation Setup](#10-one-command-presentation-setup)
11. [Installation & Prerequisites](#11-installation--prerequisites)
12. [Troubleshooting & Diagnostics](#12-troubleshooting--diagnostics)
13. [Project Limitations & Future Scope](#13-project-limitations--future-scope)

---

## 1. Project Overview & Engineering Problem

Modern high-voltage transmission networks face increasing power quality degradation resulting from renewable energy integration, nonlinear power-electronic converters, capacitor bank switching, and network faults. Rapid and autonomous detection of Power Quality Disturbances (PQD) is essential to protect critical grid infrastructure and prevent cascading trips.

This project delivers an end-to-end Hardware-in-the-Loop compatible Software-in-the-Loop (SIL) simulation and machine learning classification platform. The framework models the **WSCC 3-Machine 9-Bus System** (operating at $60.0\text{ Hz}$ in MATLAB/Simulink R2025a) and continuously streams high-speed measurement chunks to an independent Python inference engine, providing real-time disturbance recognition across 8 standardized IEEE Std 1159 classes:

- **Normal:** Balanced 60 Hz sinusoidal conduction ($V_{\text{nom}} \approx 0.588\text{ pu}$ raw, $1.02\text{ pu}$ IEEE line-to-neutral).
- **Voltage Sag:** RMS drop ($0.10\text{--}0.90\text{ pu}$) caused by network shunt faults.
- **Voltage Swell:** RMS rise ($1.10\text{--}1.80\text{ pu}$) caused by capacitor energization.
- **Interruption:** Total voltage collapse ($< 0.10\text{ pu}$) resulting from breaker tripping.
- **Harmonics:** Steady-state waveform distortion ($\text{THD} > 5.0\%$, H3, H5, H7).
- **Flicker:** Low-frequency subharmonic modulation ($0.5\text{--}35\text{ Hz}$).
- **Notch:** Periodic commutation notches per half-cycle from converter firing.
- **Transient:** High-frequency sub-cycle oscillatory spikes ($> 1\text{ kHz}$).

---

## 2. IEEE 9-Bus System & Simscape Electrical Architecture

The electrical grid model comprises:
- **3 Synchronous Generators:** G1 (Slack, 16.5 kV), G2 (PV, 18.0 kV), G3 (PV, 13.8 kV).
- **3 Step-Up Transformers:** T1, T2, T3 (connecting generation to the 230 kV backbone).
- **9 Transmission Buses:** Buses 1--9 interconnected via three-phase distributed $\pi$-section lines.
- **3 Major Load Centers:** Bus 5 ($125\text{ MW} + 50\text{ MVAr}$), Bus 6 ($90\text{ MW} + 30\text{ MVAr}$), Bus 8 ($100\text{ MW} + 35\text{ MVAr}$).

### Model Protection & Provenance
- **Protected Reference Model:** `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`
  *SHA-256 Checksum:* `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` (Strictly Read-Only).
- **Working Disturbance Model:** `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`
  Contains physical injection blocks and the Level-2 S-Function streamer.

---

## 3. Bus 5 Voltage & Current Acquisition Path

Bus 5 is the primary observation node:
- **Voltage Channels:** Measured phase-to-ground ($V_a, V_b, V_c$) with nominal line-to-line base $230\text{ kV}_{\text{RMS}}$ ($187.79\text{ kV}_{\text{peak}}$ phase-to-ground). Raw sensor per-unit fundamental RMS is $0.5877\text{ pu}$ ($V_{\text{IEEE}} = V_{\text{raw}} \times \sqrt{3} \approx 1.02\text{ pu}$).
- **Current Channels:** Measured line current ($I_a, I_b, I_c$) with nominal load current base $251.02\text{ A}_{\text{RMS}}$ ($355.0\text{ A}_{\text{peak}}$).
- **Decoupled Processing:** Voltage and current signals are acquired via independent sensor ports, routed through separate Goto tags (`Vabc_5`, `Iabc_5`), and processed with physical units (kV and A) and per-unit normalization.

---

## 4. Continuous Telemetry & Level-2 S-Function Streamer

To achieve unpaused 1:1 real-time SIL execution without solver stutter:
1. **Decoupled Producer:** A discrete MATLAB Level-2 S-Function (`integration/matlab/pqd_live_streamer.m`) samples Bus 5 VI signals at $5000\text{ Hz}$ ($T_s = 200\,\mu\text{s}$).
2. **In-Memory FIFO Buffer:** Samples are accumulated into bounded 250-sample chunks ($50\text{ ms}$). **Zero network calls occur inside the solver callback.**
3. **Consumer Drain:** The driver script (`run_continuous_simulation.m`) drains the FIFO queue and pushes JSON chunks over TCP to port `8502`.
4. **Backend Ingestion:** `simulation_bridge.py` receives the stream, updates rolling ring buffers, and executes independent ML inference every $200\text{ ms}$.

---

## 5. Disturbance Injection Subsystems

Disturbances are triggered via Level-2 S-Function output ports connected to physical Simscape blocks:
- **Sag:** Triggered via S-Function Output Port 1 to `PQD_Fault_Sag` (configurable fault resistance $0.5\text{--}10.0\,\Omega$).
- **Swell:** Triggered via S-Function Output Port 2 to `PQD_Breaker_Swell` closing onto `PQD_Cap_Swell` ($50\text{--}200\text{ MVAr}$).
- **Interruption:** Triggered via S-Function Output Port 3 opening series breaker `PQD_Breaker_Interruption`.
- **Harmonics, Flicker, Notch, Transient:** Controlled via tunable injection sources (`PQD_Harm_Enable`, `PQD_Flicker_Enable`, `PQD_Notch_Enable`, `PQD_Breaker_Transient`).

All injections support custom durations, phase selection (A, B, C, AB, BC, CA, ABC), and automatic duration expiry.

---

## 6. Digital Signal Processing (32 Enhanced Features)

Every 1000-sample analysis window ($0.20\text{ s}$ at $5\text{ kHz}$) is processed by [`extract_enhanced_features`](dsp/enhanced_features.py):
1. **8 Baseline Metrics:** `rms_voltage`, `peak_voltage`, `crest_factor`, `thd`, `duration`, `dominant_freq`, `system_freq`, `snr`.
2. **11 Goertzel Harmonic Magnitudes:** Fundamental through 11th harmonic (`h1` through `h11`).
3. **7 Harmonic Ratios:** Harmonic magnitudes normalized to fundamental (`h2_ratio` through `h9_ratio`).
4. **Spectral Descriptors:** `harmonic_energy`, `spectral_centroid`, `spectral_bandwidth`, `spectral_entropy`, `spectral_flatness`, `true_dominant_freq`.

**Numerical Parity:** Parity audit against ground-truth datasets confirmed $0.00\text{e}+00$ maximum error across all 32 features.

---

## 7. FFT Spectrum Analysis & Harmonic Characterization

The live dashboard includes a dedicated 1024-point FFT spectrum analyzer:
- Identifies the $60.0\text{ Hz}$ fundamental peak and calculates true Total Harmonic Distortion ($\text{THD}$).
- Highlights integer harmonic markers (2nd through 15th harmonic).
- Provides toggles between Linear Magnitude and Logarithmic ($\text{dB}$) scales.
- Computes spectral centroid, spectral bandwidth, and total harmonic energy.

---

## 8. Machine Learning Classification Pipeline

- **Architecture:** Phase 4C Multi-Layer Perceptron ($32 \to 64 \to 32 \to 16 \to 8$).
- **Parameters:** 4,848 weights and biases.
- **Inference Latency:** $4.0\text{--}4.5\text{ ms}$ on standard CPU ($200\times$ faster than the $200\text{ ms}$ evaluation window).
- **Cryptographic Hashes (Frozen):**
  - Weights SHA-256: `f0febd5b3829677ac0f2c13262cccb5ff8947cdcb59596f5e4a8f2b6180c27c5`
  - Scaler SHA-256: `76d0ad26e730d19776d20e70055cc6d490f2aad4680bfd47df0d95689888fc6d`
- **Event-Aware Adaptive Windowing:** Aligns feature extraction strictly to active disturbance epochs, preventing edge step distortion from triggering spurious Notch classifications.
- **Honest Out-of-Distribution (OOD) Protection:** Enforces a $99.5\%$ Mahalanobis distance boundary ($D_M \le 12.01$) with 7 distinct validation states: `VALID_CLASSIFICATION`, `LOW_CONFIDENCE`, `OUT_OF_DISTRIBUTION`, `MULTI_DISTURBANCE`, `MODEL_DOMAIN_MISMATCH`, `INSUFFICIENT_WINDOW`, and `INVALID_SIGNAL`.

---

## 9. Web Dashboard & Engineering Interface

The web interface (`web/index.html`) provides a responsive, dark-mode/light-mode academic console:
1. **Overview:** System topology, parameters, disturbance taxonomy.
2. **Live Simulink:** Voltage oscilloscope, current oscilloscope, live FFT spectrum, decoupled 3-way assessment panel.
3. **Disturbance Lab:** Preset and custom injection controls, phase selection, parameter sliders, deep ML diagnostic mode.
4. **Disturbance Analysis:** Dedicated tabs for Harmonics, Flicker, Notch, and Transient characterization.
5. **Simulation History:** Chronological disturbance log, event database, waveform inspection.
6. **Datasets:** Exploration of the IEEE 9-bus training datasets.
7. **Model Diagnostics:** 32-feature extraction table, standardized $z$-scores, confusion matrices, and benchmark metrics.
8. **Presentation Mode:** Clean fullscreen mode with presentation steppers and executive summaries.

---

## 10. One-Command Presentation Setup

To run the complete presentation setup on Windows 11:

```cmd
Start-Presentation.cmd
```

To stop all services:
```cmd
Stop-Presentation.cmd
```

Refer to [`PRESENTATION_SETUP.md`](PRESENTATION_SETUP.md) and [`presentation/PRESENTATION_GUIDE.md`](presentation/PRESENTATION_GUIDE.md) for full walkthroughs.

---

## 11. Installation & Prerequisites

### Prerequisites
- Windows 11 / Windows 10 (64-bit)
- Python 3.10+ (Verified on Python 3.14.2)
- MATLAB/Simulink R2025a (with Simscape and Simscape Electrical)

### Installation
```powershell
git clone -b research/pq-comparative-lab https://github.com/nadarallen/power-quality-detector-and-classifier.git
cd power-quality-detector-and-classifier
powershell -ExecutionPolicy Bypass -File scripts/setup_presentation.ps1
```

---

## 12. Troubleshooting & Diagnostics

- **Run Preflight Diagnostic:**
  ```powershell
  python presentation/presentation_preflight.py
  ```
- **Run Active Demo Diagnostic:**
  ```powershell
  python presentation/presentation_demo_check.py
  ```
- **Run Test Suite:**
  ```powershell
  pytest tests/
  ```

---

## 13. Project Limitations & Future Scope

### Limitations
1. **Simulation Domain:** All models were trained and validated on electromagnetic Simscape simulations of the IEEE 9-bus benchmark; performance on real-world utility PMU feeds may vary with network topology.
2. **Single-Disturbance Contract:** The current model classifies isolated disturbances; simultaneous composite disturbances (e.g., Sag + Harmonics) require multi-label architectures.
3. **Bandwidth Limits:** The 5 kHz acquisition rate imposes a 2.5 kHz Nyquist ceiling. Ultra-high-frequency transients (> 2.5 kHz) require 20 kHz+ dual-rate sampling.

### Future Scope
- Hardware-in-the-Loop (HIL) physical microcontroller deployment (ESP32 / STM32 / FPGA).
- Multi-head multi-label classification for concurrent complex disturbances.
- Dynamic network topology adaptation across IEEE 14-bus and IEEE 39-bus networks.

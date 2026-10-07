# Live Demonstration MVP Architectural Plan (Phase 5)

**Document Version:** 1.0.0  
**Phase Target:** Phase 5 — Live Demonstration MVP  
**Current Status:** PENDING (Scheduled following Phase 4 60-Hz ML Training)  
**Authoritative Context:** Interactive 60-Hz WSCC IEEE 9-Bus Simulation & Streaming Telemetry  

> [!IMPORTANT]
> **Planning Document Notice:** This document specifies the planned architecture and control interfaces for Phase 5. The live interactive demonstration system is **NOT currently operational** during Phase 3/4 maintenance and will be implemented after final 60-Hz ML model validation.

---

## 1. Executive Objective

The objective of Phase 5 is to deliver an end-to-end **Live Demonstration Minimum Viable Product (MVP)** where an operator can interactively trigger physical power quality disturbances within a running Simulink simulation of the WSCC 9-bus grid, observe the resulting 3-phase waveforms at Bus 5 in real time, and verify instantaneous ML classification on a live laboratory dashboard.

```
+-----------------------------------------------------------------------------+
|                      PHASE 5 LIVE DEMONSTRATION ARCHITECTURE                |
+-----------------------------------------------------------------------------+
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   |         IEEE 9-Bus Live Demo Model (Simulink R2025a)                |   |
|   |  - Continuous running simulation (ode23t)                           |   |
|   |  - PQD Disturbance Injection Rack at Bus 5                          |   |
|   |  - Dual-Control Interface (MATLAB Command API & Simulink UI)        |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Bus 5 Vabc, Iabc (5 kHz)            |
|   +---------------------------------------------------------------------+   |
|   |       Rolling Acquisition Bridge (integration/matlab/live_stream.m) |   |
|   |  - Circular buffer (1,000 samples / 200 ms window)                  |   |
|   |  - HTTP Chunked Streaming to Python REST Server                     |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  JSON / Binary POST                  |
|   +---------------------------------------------------------------------+   |
|   |       Python Realtime Engine (server.py & realtime_pipeline.py)     |   |
|   |  - RingBuffer ingest (5 kHz stream)                                 |   |
|   |  - Production 32-Feature DSP (dsp/enhanced_features.py)             |   |
|   |  - Phase-Aware SNR & Orthogonal Projection                          |   |
|   |  - Physical Rule Validation (dsp/standards_detector.py)             |   |
|   |  - 60-Hz Retrained ML Model Forward Pass (Phase 4 Model)            |   |
|   |  - SQLite Event Persistence (data/pq_events.db)                     |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Server-Sent Events (SSE) Telemetry  |
|   +---------------------------------------------------------------------+   |
|   |       Live Laboratory Dashboard (web/index.html & web/app.js)       |   |
|   |  - CRT Oscilloscope (Real-time 3-phase waveforms)                   |   |
|   |  - FFT Spectrum Analyzer (Harmonics H1–H11)                         |   |
|   |  - 32-Feature Parameter Matrix                                      |   |
|   |  - Live Classification Badge & Softmax Confidence Breakdown         |   |
|   +---------------------------------------------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 2. Interactive Control Interfaces

Phase 5 will support two independent control modalities for initiating disturbances during a live demonstration:

### 2.1 Control Method 1: Programmatic MATLAB Trigger API

A high-level MATLAB object-oriented API (`pqd_controller.m`) allowing automated test scripting or interactive command-line injection:

```matlab
% Conceptual MATLAB Interactive Session
pqd = PQDLiveController('IEEE_9bus_PQD_LIVE_DEMO');
pqd.start(); % Start running simulation

% 1. Inject a 40% Voltage Sag on Phase A for 100 ms
pqd.sag('Phase', 'A', 'RemainingVoltage_pu', 0.60, 'Duration_ms', 100);

% 2. Inject 3-phase 5th & 7th Harmonics (12% THD)
pqd.harmonics('Phases', 'ABC', 'H5_pct', 8.0, 'H7_pct', 6.0, 'Duration_ms', 200);

% 3. Inject Commutation Notches (400 us, 50% depth)
pqd.notch('Phases', 'ABC', 'Width_us', 400, 'Depth_pct', 50);

% 4. Inject 1.2 kHz Oscillatory Transient
pqd.transient('Phase', 'A', 'Frequency_hz', 1200, 'Decay_ms', 15);

% 5. Return to Normal Steady-State
pqd.reset();
pqd.stop();
```

### 2.2 Control Method 2: Simulink Dashboard & Manual Operator Controls

A dedicated interactive dashboard subsystem integrated into `IEEE_9bus_PQD_LIVE_DEMO.slx` featuring:
1. **Rotary Selector Switch:** Selects disturbance class (`Normal`, `Sag`, `Swell`, `Interruption`, `Harmonics`, `Flicker`, `Notch`, `Transient`).
2. **Phase Checkbox Array:** Toggle active phases ($L_1$, $L_2$, $L_3$).
3. **Severity & Duration Sliders:** Real-time parameter tuning ($R_{\text{fault}}$, $C_{\text{bank}}$, modulation frequency).
4. **Trigger Pushbutton:** Manual single-shot or continuous pulse injection.

---

## 3. Subsystem Implementation Requirements

### 3.1 Live Derivative Simulink Model (`IEEE_9bus_PQD_LIVE_DEMO.slx`)
- **Pristine Isolation:** Derived from `IEEE_9bus_PQD_DISTURBANCES.slx`; pristine model `IEEE_9bus_PQD_HIL_R2025a.slx` remains strictly untouched.
- **Pacing Mechanism:** Uses MATLAB `set_param(mdl, 'SimulationPacing', 'on', 'SimulationPacingRate', 1.0)` for 1:1 wall-clock real-time simulation.
- **Continuous Buffer Output:** To Workspace / Streaming block writing Bus 5 $V_{abc}, I_{abc}$ to a shared memory circular buffer.

### 3.2 Streaming Bridge (`integration/matlab/stream_simulink_live.m`)
- Resamples variable-step simulation output to exact 5 kHz grid frames.
- Streams 50 ms chunks (250 samples) with zero-copy HTTP POST requests to `/api/simulink/ingest_chunk`.

### 3.3 Backend Processing Pipeline (`pipeline/realtime_pipeline.py`)
- Continuously maintains a 200 ms rolling ring buffer (1,000 samples).
- Executes 32-feature DSP extraction every 20 ms (100-sample sliding hop, 90% overlap).
- Queries retrained 60-Hz ML model forward pass.
- Dispatches Server-Sent Events (SSE) to connected frontend clients within $< 5\text{ ms}$ latency.

### 3.4 Frontend Laboratory UI (`web/`)
- Canvas-based 60 FPS oscilloscope rendering 3-phase waveforms.
- Dynamic harmonic bar chart updating at 20 Hz.
- Instant classification indicator with confidence meter and uncertainty gating ($< 60\%$ confidence flags `UNCERTAIN`).

---

## 4. Acceptance & Validation Criteria for Phase 5

| Criterion | Target Metric | Verification Method |
|---|---|---|
| **End-to-End Latency** | $< 50\text{ ms}$ (Disturbance onset to UI update) | High-precision timestamp logging across MATLAB, Python, and JS |
| **Stream Continuity** | Zero dropped frames over 10 minutes continuous run | Sequence ID counter verification in `MultiChannelRingBuffer` |
| **Classification Accuracy** | $\ge 95\%$ across all 8 classes in live simulation | 100 randomized interactive injections against ground-truth labels |
| **Decoupling Integrity** | Physical rule engine operates independently of ML | Verify that ML predictions do not overwrite physical status flags |

---

## 5. Prerequisite Checklist

Before Phase 5 implementation begins:
- [x] Phase 3: Eight disturbance classes generated, validated, and audited (**COMPLETE**).
- [ ] Phase 4: 60-Hz ML models trained on audited datasets and exported (**PENDING**).
- [ ] Phase 4: Model contract and scaler parameters deployed to `ml/models/` (**PENDING**).

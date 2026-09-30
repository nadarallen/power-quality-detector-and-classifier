# Simulink IEEE 9-Bus Integration Plan

**Document Version:** 1.0.0  
**Date:** 2026-09-30  
**Status:** Approved Architectural Baseline (GATE 0 Completed)  
**Author:** Antigravity Autonomous Systems Engineering  

---

## 1. Executive Summary & Objective

This document defines the production-style local integration between:
1. **System A — Electrical Simulation:** MATLAB/Simulink R2025a execution of the standard IEEE 9-bus 3-machine power system (`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`).
2. **System B — Python Power Quality Platform:** Real-time multi-channel DSP, physics-informed feature extraction, neural network inference, event engine, SQLite persistence, REST/SSE server (`server.py`), and CRT Oscilloscope frontend (`web/`).

The integration provides an automated, non-invasive waveform pipeline:
```
MATLAB/Simulink R2025a (IEEE 9-Bus)
       │ Bus 5 Vabc_5 (3-phase) & Iabc_5 (3-phase)
       ▼
Simulink Acquisition Bridge (integration/matlab/)
       │ Anti-aliasing downsampling (1.1 MHz → 5 kHz / 6 kHz) & chunk batching
       ▼ Localhost HTTP POST (/api/ingest/simulink or /api/ingest/chunk)
Python Ingestion Layer (server.py)
       │ MultiChannelRingBuffer (preserves 60 Hz metadata & channel sync)
       ▼
RealtimePQPipeline (pipeline/realtime_pipeline.py)
       │ dsp/phase_processor.py & dsp/enhanced_features.py (60 Hz aware)
       ▼
ThreePhaseEventEngine (dsp/event_engine.py)
       │ SQLite Persistence (storage/event_store.py)
       ▼
Telemetry & Frontend Dashboard (web/index.html & SSE /api/stream/telemetry)
```

No manual CSV upload or polling file transport is used at runtime.

---

## 2. System A Audit — MATLAB/Simulink Electrical Simulation

### 2.1 Model Topology & Parameters
- **Model File:** `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`
- **Electrical Base:** Western System Coordinating Council (WSCC) 3-machine, 9-bus system.
- **Electrical Nominal Frequency:** **$f_0 = 60.0\,\text{Hz}$** (Non-negotiable; electrical parameters, line inductances, and synchronous machine reactances are parameterized for 60 Hz).
- **Target Measurement Point:** **Bus 5** (Load Bus).
  - Three-phase voltage: `Vabc_5` (Phase A, B, C).
  - Three-phase current: `Iabc_5` (Phase A, B, C).

### 2.2 Simulink Logging Architecture
Audit of `IEEE_9bus_PQD_HIL_R2025a.slx` reveals two configured `To Workspace` blocks inside `/Subsystem`:
1. `IEEE_9bus_PQD_HIL_R2025a/Subsystem/To Workspace` $\rightarrow$ Variable: `PQD_Vabc`
   - `SaveFormat`: `Timeseries`
   - `SampleTime`: `-1` (inherited from variable-step continuous solver `ode45`)
   - `MaxDataPoints`: `inf`
2. `IEEE_9bus_PQD_HIL_R2025a/Subsystem/To Workspace1` $\rightarrow$ Variable: `PQD_Iabc`
   - `SaveFormat`: `Timeseries`
   - `SampleTime`: `-1`

### 2.3 Solver & Sampling Rate
- **Solver:** `ode45` (Dormand-Prince variable-step continuous solver).
- **Stop Time:** `1.0 s` (execution time $\approx 26.3\,\text{s}$ wall-clock in batch mode).
- **Raw Step Size:** Step size varies down to sub-microsecond intervals during switching/initialization, yielding approximately $N \approx 225,340$ time points per 0.2s window ($F_s \approx 1.126\,\text{MHz}$).
- **Signal Units:** In the existing baseline, Bus 5 voltage is scaled such that nominal peak phase-to-ground is $V_{\text{peak}} \approx 0.8312\,\text{pu}$, and nominal unnormalized RMS is $V_{\text{rms,raw}} \approx 0.5877\,\text{pu}$, corresponding to conventional RMS $V_{\text{rms,pu}} = V_{\text{rms,raw}} \times \sqrt{2} \approx 0.8312\,\text{pu}$.

### 2.4 Existing MATLAB Scripts
- `IEEE_9bus/extract_PQD_features.m`: Reference standards feature extractor computing 8 features:
  `V_rms_pu`, `V_peak_pu`, `Crest_Factor`, `THD_percent`, `Duration_ms`, `Dominant_Frequency_Hz`, `System_Frequency_Hz`, `SNR_dB`.
- `IEEE_9bus/PQD_Normal_Baseline.mat`: Frozen reference normal feature structure with $V_{\text{rms}} = 0.8312\,\text{pu}$, $THD = 0.0007\%$, $f_{\text{sys}} = 60.00\,\text{Hz}$.
- `IEEE_9bus/PQD_ML_Features_Normal.csv`: CSV export used for offline comparison.

---

## 3. System B Audit — Python PQD Software Platform

### 3.1 Data Structures
- **`WaveformFrame`** (`dsp/waveform_frame.py`):
  - Fields: `timestamp_utc`, `sampling_rate_hz`, `nominal_frequency_hz` (default 50.0), `source_type`, `device_id`, `sequence_number`, `phases` (`Dict[str, np.ndarray]`), `channels` (`Dict[str, ChannelMetadata]`).
  - Validation: NaN/Inf checks, channel synchronization check, clipping checks.
- **`MultiChannelRingBuffer`** (`dsp/ring_buffer.py`):
  - Manages continuous streaming sample accumulation.
  - Supports arbitrary chunk sizes.
  - Slices frames of `window_size` with configurable `hop_size`.
  - Carries `sampling_rate_hz` and `nominal_frequency_hz`.

### 3.2 Feature Extraction & DSP Engines
- **`dsp/baseline_features.py`**:
  - Computes 8 standard features.
  - Goertzel harmonic calculation hardcoded at 50, 150, 250, 350 Hz.
- **`dsp/enhanced_features.py`**:
  - Computes 47 extended features (Track B).
  - Goertzel harmonic profile `compute_harmonic_profile` takes `f0: float = 50.0`.
  - `extract_enhanced_features` defaulted `f0=50.0`.
- **`dsp/standards_detector.py`**:
  - 10 ms half-cycle sliding RMS detector ($U_{\mathrm{rms}(1/2)}$).
  - FFT harmonic analysis orders $H_2\text{--}H_{11}$.

### 3.3 Deployed Machine Learning Model
- **Model:** `ml/models/model_weights_32.json` (Compact MLP: 32 $\rightarrow$ 64 $\rightarrow$ 32 $\rightarrow$ 8).
- **Training Baseline:** Trained on 50 Hz synthetic BARC dataset (`Dataset/BARC DATA.csv`).
- **Input Dimension:** Exactly 32 features.
- **Scaler:** Pre-fitted `StandardScaler` with mean and scale vectors for 32 features.
- See detailed mathematical breakdown in `docs/SIMULINK_ML_MODEL_CONTRACT.md`.

### 3.4 Ingestion Endpoints (`server.py`)
- `POST /api/ingest`: Full `WaveformFrame` JSON payload.
- `POST /api/ingest/chunk`: Multi-channel streaming chunk `{"channels": {"L1": [...], "L2": [...], "L3": [...]}, "timestamp_utc": ...}`.
- `GET /api/health`: Node status, active acquisition source, hardware state, event count.
- `GET /api/stream/telemetry`: SSE stream broadcasting live phase metrics, harmonic spectrum, and active event flags to the web UI.

---

## 4. The Sampling Rate & Frequency Decoupling Solution

### 4.1 Resampling & Anti-Aliasing (MATLAB Bridge Side)
The raw continuous simulation produces variable-step points with average step $\sim 8.87 \times 10^{-7}\,\text{s}$ ($\sim 1.126\,\text{MHz}$). Transmitting 1.1 million points/sec over HTTP is both infeasible and unnecessary for power quality classification up to the 50th harmonic ($3000\,\text{Hz}$).

**Solution:**
1. **Target Sampling Rate:** $f_{s,\text{target}} = 5000.0\,\text{Hz}$ (default, yielding exactly 1000 samples per 200 ms window) or $6000.0\,\text{Hz}$ (100 samples/cycle @ 60 Hz). Both rates are fully supported.
2. **Anti-Aliasing Filter:** Prior to decimation, a digital low-pass Chebyshev Type I or Butterworth filter (cutoff $f_c = 2200\,\text{Hz} < f_{\text{Nyquist}} = 2500\,\text{Hz}$) is applied to prevent high-frequency solver chatter from aliasing into the power frequency spectrum.
3. **Resampling:** Uniform interpolation (`resample` or `interp1` with linear/spline) generates strictly monotonic, uniformly spaced time points $t_k = t_0 + k / f_{s,\text{target}}$.
4. **Channel Synchronization:** Phase A, B, and C voltages (and currents) are resampled on the identical uniform time grid, guaranteeing exact 3-phase synchronization with zero phase shift jitter.

### 4.2 60 Hz Nominal Frequency Handling
1. **Observation Window Math:**
   - 50 Hz grid: 10 cycles = 200.0 ms.
   - 60 Hz grid: 12 cycles = 200.0 ms.
   - At $f_s = 5000\,\text{Hz}$, a 200 ms window is **exactly 1000 discrete samples** for BOTH frequencies!
   - This physical property guarantees that the 1000-sample buffer length is preserved without altering buffer geometries.
2. **DSP Feature Extraction 60 Hz Parameterization:**
   - `extract_enhanced_features(signal, sample_rate=5000.0, f0=50.0)` is parameterized with `f0`.
   - When processing a 60 Hz frame, harmonic frequencies are evaluated at integer multiples of 60 Hz:
     $H_1 = 60\,\text{Hz}, H_2 = 120\,\text{Hz}, H_3 = 180\,\text{Hz}, \dots, H_{11} = 660\,\text{Hz}$.
   - System frequency calculation measures actual zero-crossing rate ($T = 16.67\,\text{ms} \rightarrow f \approx 60\,\text{Hz}$).
3. **ML Domain Separation:**
   - Because the deployed model was trained on 50 Hz BARC data, passing 60 Hz features into the model triggers the domain safety check.
   - The system distinguishes:
     - `MODEL_COMPATIBLE` (when nominal frequency is 50 Hz $\pm 1\,\text{Hz}$).
     - `MODEL_DOMAIN_MISMATCH` (when nominal frequency is 60 Hz, such as IEEE 9-bus).
   - In `MODEL_DOMAIN_MISMATCH` mode:
     - The true DSP features (60 Hz fundamental, THD, RMS, etc.) are computed and displayed accurately.
     - The model forward pass is executed for diagnostic inspection, but the result is flagged with `domain_status: "MODEL_DOMAIN_MISMATCH"` and uncertainty is enforced to prevent erroneous automated protection trips.
     - No fake "50 Hz" conversion or hardcoded "Normal" is permitted.

---

## 5. Architectural Implementation Plan

### Phase 1: Backend Simulink Ingestion Contract
- Implement `SimulinkAdapter` in `dsp/acquisition_adapter.py`:
  - `source_type = "simulink"`
  - `device_id = "SIMULINK_IEEE9BUS_BUS5"`
  - `nominal_frequency_hz = 60.0`
  - `sampling_rate_hz = 5000.0`
- Extend `server.py` with `POST /api/ingest/simulink`:
  - Accepts payload with `channels` (`L1`, `L2`, `L3`), optional current channels (`I1`, `I2`, `I3`), `sampling_rate_hz`, `nominal_frequency_hz = 60.0`, `sequence_number`, and `timestamp_utc`.
  - Validates array lengths and numerical integrity.
  - Automatically initializes or switches pipeline adapter to `SimulinkAdapter`.

### Phase 2: Parameterize DSP Pipeline for 60 Hz
- Refactor `dsp/enhanced_features.py`:
  - Accept `f0: float = 50.0` in `extract_enhanced_features` and pass down to `compute_harmonic_profile`.
- Update `dsp/phase_processor.py`:
  - Pass `nominal_frequency_hz` from `WaveformFrame` into `extract_enhanced_features`.
  - Add domain compatibility status determination (`MODEL_COMPATIBLE` vs `MODEL_DOMAIN_MISMATCH`).
- Update `pipeline/realtime_pipeline.py`:
  - Calculate telemetry harmonic spectrum frequencies based on `frame.nominal_frequency_hz` ($[h \times f_0]$).

### Phase 3: MATLAB Bridge Client (`integration/matlab/`)
- `integration/matlab/pqd_stream_client.m`:
  - Robust MATLAB class providing HTTP POST with JSON body.
  - Timeout, retry, sequence counting, and response parsing.
- `integration/matlab/run_simulink_pqd.m`:
  - Loads `IEEE_9bus_PQD_HIL_R2025a.slx`.
  - Executes simulation (`sim`).
  - Extracts `PQD_Vabc` (and `PQD_Iabc`).
  - Resamples to uniform $f_s = 5000\,\text{Hz}$ with anti-aliasing.
  - Slices into batches (e.g. 500 or 1000 samples per batch = 100 ms to 200 ms).
  - Streams batches to Python `/api/ingest/simulink`.
  - Prints transmission latency, acknowledged events, and DSP consistency report.

### Phase 4: Frontend & Telemetry Integration
- Ensure `server.py` `/api/health` and `/api/telemetry` report:
  - `acquisition_source`: `"simulink"`
  - `nominal_frequency`: `60.0`
  - `device_id`: `"SIMULINK_IEEE9BUS_BUS5"`
- Verify CRT oscilloscope displays L1, L2, L3 multi-trace waveforms at 60 Hz with correct period ($\approx 16.7\,\text{ms}$).

### Phase 5: Verification & Consistency Audit
- Run automated end-to-end tests:
  - Server start & health check.
  - Simulink chunk ingestion with 60 Hz metadata.
  - Malformed payload rejection & length mismatch rejection.
  - Comparison of MATLAB `extract_PQD_features.m` output against Python `PhaseMeasurement` on the exact same waveform window.
  - Generate `docs/SIMULINK_PYTHON_FEATURE_VALIDATION.md`.

---

## 6. Execution Gates & Milestones

| Gate | Focus | Deliverables | Verification Criterion |
|---|---|---|---|
| **GATE 0** | Repository & Model Audit | `SIMULINK_INTEGRATION_PLAN.md`, `SIMULINK_ML_MODEL_CONTRACT.md` | Model inspected, solver verified, variables verified |
| **GATE 1** | Backend Ingestion Contract | `SimulinkAdapter`, `/api/ingest/simulink`, 60 Hz DSP refactoring | Unit tests pass, 106 existing tests green |
| **GATE 2** | MATLAB Bridge Implementation | `integration/matlab/pqd_stream_client.m`, `run_simulink_pqd.m` | MATLAB syntax valid, headless runnable |
| **GATE 3** | Deterministic Replay Simulation | End-to-end simulation of IEEE 9-bus to Python API | MATLAB batches accepted, HTTP 200 OK |
| **GATE 4** | Python Pipeline Processing | Event engine & telemetry state verification | Waveforms ingested, zero spurious disturbance events |
| **GATE 5** | Frontend Telemetry Verification | Web dashboard reflecting Simulink source | CRT scope renders 60 Hz traces, SSE active |
| **GATE 6** | Feature Consistency Audit | `SIMULINK_PYTHON_FEATURE_VALIDATION.md` | MATLAB vs Python metrics compared within tolerance |
| **GATE 7** | Streaming & Extensibility Review | Documentation & final integration report | All 15 prompt validation tests verified |

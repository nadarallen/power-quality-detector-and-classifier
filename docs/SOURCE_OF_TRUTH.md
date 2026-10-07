# Master Source of Truth Registry

**Project Title:** AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation  
**Document Version:** 1.0.0  
**Phase Status:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Frequency Domain:** 60 Hz (WSCC Transmission Grid Standard)  
**Authoritative Sampling Rate:** 5,000 Hz ($T_s = 200\ \mu\text{s}$, 1,000 samples per 200 ms frame)  

---

## 1. Purpose & Authority

This document defines the **single authoritative registry** for all active subsystems, contracts, datasets, models, and documentation across the repository. 

Whenever two files, docstrings, or discussions conflict:
1. The file identified in this registry is the **authoritative source of truth**.
2. Derived documents or legacy artifacts must be updated to conform to this registry.
3. No metrics, parameters, or gate results may be claimed without verification against these authoritative files.

---

## 2. Authoritative Component Registry

### 2.1 Electrical Power System Simulation

| Domain / Purpose | Authoritative Path | Verification / Hash / Evidence | Status |
|---|---|---|---|
| **Pristine Reference Model** | `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` | SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` | **FROZEN** (Strict Reference Baseline) |
| **Disturbance Generation Model** | `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx` | Contains 8 physical disturbance injection blocks at Bus 5 | **ACTIVE PRODUCTION** |
| **Observation Point** | Bus 5 ($V_{abc}$, $I_{abc}$) | Load bus (125 MW, 50 MVAR nominal) | **ACTIVE CONTRACT** |
| **Simulation Engine** | MATLAB R2025a / Simulink Simscape Electrical | Variable-step `ode23t` (max step $\le 100\ \mu\text{s}$) | **ACTIVE PRODUCTION** |

---

### 2.2 Disturbance Scenario Definitions & Ground Truth

| Domain / Purpose | Authoritative Path | Verification / Hash / Evidence | Status |
|---|---|---|---|
| **Scenario Controller Schema** | `docs/GATE3C_SCENARIO_SCHEMA.json` | JSON Schema for programmatic scenario validation | **ACTIVE PRODUCTION** |
| **Authoritative Scenario Specs** | `scenarios/definitions/` (JSON) | 8 verified baseline files: `SAG_0001`, `SWELL_0001`, `INT_0001`, `HAR_0001`, `FLK_0001`, `NOT_0001`, `TRAN_0001`, `NORM_0001` | **ACTIVE PRODUCTION** |
| **Ground-Truth Source** | Simulation Scenario Metadata | Physical breaker/fault parameters dictate class truth (NOT ML prediction) | **ACTIVE CONTRACT** |

---

### 2.3 Physical Disturbance Datasets (60 Hz, 5 kHz)

| Disturbance Class | Directory Path | Waveform npz / MAT | Feature CSV / Metadata | Audit Report |
|---|---|---|---|---|
| **Normal** | `data/ieee9bus_60hz/normal/` | `normal_waveforms.npz` | `normal_features.csv` | `docs/GATE3B1_NORMAL_DATASET_AUDIT.md` |
| **Voltage Sag** | `data/ieee9bus_60hz/sag/` | `sag_waveforms.npz` | `sag_features.csv` | `docs/GATE3F_SAG_DATASET_AUDIT.md` |
| **Voltage Swell** | `data/ieee9bus_60hz/swell/` | `swell_waveforms.npz` | `swell_features.csv` | `docs/GATE3I_SWELL_DATASET_AUDIT.md` |
| **Voltage Interruption** | `data/ieee9bus_60hz/interruption/` | `interruption_waveforms.npz` | `interruption_features.csv` | `docs/GATE3L_INTERRUPTION_DATASET_AUDIT.md` |
| **Harmonics** | `data/ieee9bus_60hz/harmonics/` | `raw_harmonics_simulations.mat` | `harmonics_features.csv` | `docs/GATE3O_HARMONICS_DATASET_AUDIT.md` |
| **Voltage Flicker** | `data/ieee9bus_60hz/flicker/` | `raw_flicker_simulations.mat` | `flicker_features.csv` | `docs/GATE3R_FLICKER_DATASET_AUDIT.md` |
| **Voltage Notch** | `data/ieee9bus_60hz/notch/` | `raw_notch_simulations.mat` | `notch_features.csv` | `docs/GATE3U_NOTCH_DATASET_AUDIT.md` |
| **Oscillatory Transient** | `data/ieee9bus_60hz/transient/` | `raw_transient_simulations.mat` | `transient_features.csv` | `docs/GATE3X_TRANSIENT_DATASET_AUDIT.md` |

*Note: All 8 datasets are physically verified, trajectory-isolated, and audited across Gates 1 to 3X.*

---

### 2.4 Digital Signal Processing (DSP) & Feature Extraction

| Subsystem | Authoritative File | Key Responsibilities & Invariants |
|---|---|---|
| **Production 32-Feature Extraction** | `dsp/enhanced_features.py` | Computes exact 32-feature vector: $V_{\text{rms}}$, $V_{\text{peak}}$, Crest Factor, Form Factor, THD (H2–H11), Phase-Aware Orthogonal Projection SNR, Mean, Variance, Skewness, Kurtosis, Energy, Shannon Entropy, Zero Crossings, Frequency, DC Component. |
| **Waveform Frame Container** | `dsp/waveform_frame.py` | Validates 3-phase channel synchrony ($L_1, L_2, L_3$), strict 5 kHz rate, 200 ms duration, and NaN/Inf integrity guards. |
| **Physical Rule Detection** | `dsp/standards_detector.py` | Implements IEEE 1159 / IEEE 519 physical detection boundaries ($V_{\text{rms}} < 0.90\text{ pu}$ for Sag, $V_{\text{rms}} > 1.10\text{ pu}$ for Swell, $V_{\text{rms}} < 0.10\text{ pu}$ for Interruption, $\text{THD} > 5.0\%$ for Harmonics). |
| **Multi-Phase Sliding Processor** | `dsp/phase_processor.py` | Orchestrates 3-phase feature extraction, sliding window evaluation, and model prediction mapping. |
| **Ring Buffer Acquisition** | `dsp/ring_buffer.py` | Thread-safe circular buffer for seamless 5 kHz streaming ingestion with zero boundary drop. |
| **Acquisition Adapters** | `dsp/acquisition_adapter.py` | Concrete streaming adapters: `SimulinkAdapter`, `SimulationAdapter`, `MockHardwareAdapter`. |

---

### 2.5 Ingestion Pipeline, Validation & Storage

| Subsystem | Authoritative File | Functionality |
|---|---|---|
| **Realtime Pipeline Orchestrator** | `pipeline/realtime_pipeline.py` | Ingests chunks, updates circular buffer, extracts 32 features, applies physical rules, queries ML, and records telemetry. |
| **Physical Disturbance Validator** | `pipeline/disturbance_validator.py` | Rule-based mathematical validator verifying disturbance physics for all 8 classes independently of ML. |
| **SQLite Event Persistence** | `storage/event_store.py` | Persists detected power quality events, raw waveform snapshots, feature vectors, and classifications to `data/pq_events.db`. |

---

### 2.6 Simulink-to-Python Integration Bridge

| Component | Authoritative File | Operational Description |
|---|---|---|
| **Automated Ingestion Script** | `integration/matlab/send_simulink_pqd_auto.m` | Executes Simulink simulation, resamples Bus 5 measurements to 5 kHz, and POSTs chunks to `/api/simulink/ingest_chunk`. |
| **Live Streaming Script** | `integration/matlab/stream_simulink_live.m` | Streams active simulation buffer in real time via HTTP chunks. |
| **MATLAB Client Engine** | `integration/matlab/pqd_stream_client.m` | High-level MATLAB client wrapper for interacting with Python server API. |

---

### 2.7 Machine Learning Inference & Retraining Status

| Artifact / Contract | Authoritative Path | Status & Notes |
|---|---|---|
| **32-Feature Production Contract** | `docs/SIMULINK_ML_MODEL_CONTRACT.md` | Formal 32-feature definition, ordering, and normalization specification. |
| **Current Legacy Weights** | `ml/models/model_weights_32.json` | SHA-256: `BE9BDBC3641F6C2F667F65D32BA2DA90B244F0912F78A253221503E70BBAAB72` (**FROZEN**; flags `MODEL_DOMAIN_MISMATCH` pending Phase 4). |
| **Phase 4 Retraining Protocol** | `docs/ML_READINESS.md` | Authoritative 10-step protocol for 60-Hz model retraining on audited datasets. |

---

### 2.8 Telemetry Server & User Interfaces

| Component | Authoritative File | Operational Description |
|---|---|---|
| **FastAPI / HTTP Server** | `server.py` | Serves REST API (`/api/health`, `/api/simulink/ingest_chunk`, `/api/telemetry/stream` SSE, `/api/events`) and static frontend. |
| **Laboratory Oscilloscope UI** | `web/index.html`, `web/styles.css`, `web/app.js` | CRT oscilloscope display, real-time 3-phase Bus 5 waveform plotting, FFT spectrum analyzer, and classification telemetry. |
| **Streamlit / Dashboard Launcher** | `app_frontend.py` | Alternative UI launcher and frontend entry point. |

---

### 2.9 Master Project Documentation

| Role | Authoritative File | Purpose |
|---|---|---|
| **Root README** | `README.md` | Comprehensive GitHub project presentation, architecture, and current state. |
| **Project Status** | `docs/PROJECT_STATUS.md` | Master single human-readable project status document. |
| **Gate Registry** | `docs/GATE_INDEX.md` | Comprehensive status of Gates 1 through 3X. |
| **Project Roadmap** | `docs/ROADMAP.md` | Multi-phase development roadmap (Phases 1 through 6). |
| **System Architecture** | `docs/ARCHITECTURE.md` | 7-subsystem engineering specification. |
| **Dataset Specification** | `docs/DATASET.md` | Complete documentation of all 8 disturbance classes. |
| **Standards Index** | `docs/STANDARDS_TRACEABILITY_INDEX.md` | Standards mapping across IEEE 1159, 519, 1453, and IEC. |
| **Reproducibility Guide** | `docs/REPRODUCIBILITY.md` | Step-by-step instructions for reproducing all results. |
| **Live MVP Plan** | `docs/LIVE_MVP_PLAN.md` | Architectural plan for Phase 5 live Simulink demonstration. |
| **Changelog** | `CHANGELOG.md` | Chronological record of major engineering milestones. |

---

## 3. Legacy / Future Extension Boundaries

To avoid confusion, the following subsystems are explicitly designated as **non-primary / optional extensions**:

1. **ESP32 Firmware (`firmware/`) & Hardware Schematics (`hardware/`):**
   - **Status:** Phase 6 Optional Extension (Embedded HIL).
   - **Policy:** Maintained for future embedded research; not part of the primary 60-Hz simulation MVP.
2. **Firebase Realtime Database (`firebase/`) & Mobile App (`mobile_app/`):**
   - **Status:** Optional Cloud/Mobile Telemetry Client.
   - **Policy:** Decoupled from core local simulation and telemetry pipeline.
3. **Synthetic 50-Hz Datasets (`data/pqd_features.csv`, `Dataset/BARC DATA.csv`):**
   - **Status:** Historical Baseline Benchmarks.
   - **Policy:** Preserved for benchmark comparison; strictly prohibited from being mixed into 60-Hz IEEE 9-bus training datasets.

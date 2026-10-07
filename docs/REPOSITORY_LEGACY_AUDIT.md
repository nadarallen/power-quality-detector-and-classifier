# Repository Legacy & Component Audit

**Document Version:** 1.0.0  
**Phase Status:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Context:** 60-Hz WSCC IEEE 9-Bus Simulation & Python DSP Architecture  

---

## 1. Executive Summary

Over multiple iterations, this repository accumulated components from initial conceptual proposals, synthetic 50-Hz benchmarks, 8-feature compact prototypes, and early embedded ESP32 hardware investigations. 

Following the successful completion of **Phase 3 (Gates 1 through 3X)**, the project direction is rigorously established around:
1. **Electrical Physics:** 60-Hz WSCC IEEE 9-bus transmission simulation in MATLAB/Simulink R2025a.
2. **Measurement Point:** Bus 5 ($V_{abc}, I_{abc}$) sampled at 5 kHz with 200 ms (1,000-sample) analysis frames.
3. **Feature Contract:** Production 32-feature DSP vector with orthogonal projection SNR, per-phase harmonic extraction (H2–H11), and IEC/IEEE-aligned statistical moments.
4. **Physical Dataset:** 8 fully validated disturbance classes (Normal, Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient).
5. **Next Phase:** Phase 4 Proper 60-Hz ML Training & Validation (MLP/Random Forest/XGBoost).
6. **Future Phase:** Phase 5 Live Demonstration MVP (Simulink disturbance rack + MATLAB trigger API + Live Dashboard).
7. **Future Extension:** Phase 6 Embedded ESP32 Hardware-in-the-Loop (HIL) Deployment.

This audit systematically classifies every repository subsystem to prevent conceptual confusion, eliminate dead files, preserve historical scientific evidence, and establish clear architectural boundaries.

---

## 2. Component Taxonomy & Classification Matrix

| Category | Definition | Repository Action Policy |
|---|---|---|
| **A. ACTIVE CURRENT** | Core production components actively used in 60-Hz simulation, DSP, validation, streaming, and testing. | **KEEP** — Active maintenance under strict freeze rules. |
| **B. REQUIRED SUPPORTING** | Metadata, schemas, fixtures, and configuration essential for executing current pipelines. | **KEEP** — Maintain consistency with current schemas. |
| **C. HISTORICAL EVIDENCE** | Past gate audits, benchmark results, and baseline logs representing immutable scientific history. | **ARCHIVE / PRESERVE** — Keep intact as scientific record; do not rewrite. |
| **D. FUTURE / OPTIONAL** | ESP32 firmware, hardware schematics, Firebase telemetry, and mobile app scaffolding planned for Phase 6. | **KEEP AS FUTURE** — Document as optional/future extensions; isolate from MVP path. |
| **E. DEAD / DUPLICATE** | Unreferenced autosave files, duplicate documents, or conflicting legacy guides. | **DEPRECATE / DELETE** — Remove after verifying zero active dependencies. |
| **F. GENERATED / ARTIFACT** | Compiled caches, simulation output MATs, SQLite runtime logs. | **IGNORE / TRACK AS REPRODUCIBLE** — Ensure `.gitignore` coverage. |

---

## 3. Detailed Component Inventory & Action Matrix

### 3.1 Electrical Simulation Subsystem (`IEEE_9bus/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` | A | Pristine 60-Hz WSCC reference model | `tests/test_gate3a_60hz_compatibility.py`, `docs/GATE3A_*` | **ACTIVE CURRENT** | **KEEP (FROZEN)** | Reference baseline; SHA-256 `5D833D8F...` must remain globally frozen. |
| `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx` | A | Working model with 8 disturbance injection blocks | `scripts/run_disturbance_simulation.m`, `scripts/apply_*_to_disturbances_slx.m` | **ACTIVE CURRENT** | **KEEP** | Authoritative model for generating 8-class physical disturbances. |
| `IEEE_9bus/IEEE_9bus_new_o.slx.autosave` | E | Old Simulink autosave | Zero code or script references | **DEAD** | **DELETE** | Leftover autosave artifact from early model import; no runtime value. |

---

### 3.2 Datasets & Feature Stores (`data/`, `Dataset/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `data/ieee9bus_60hz/` (8 subdirectories) | A | Authoritative 8-class 60-Hz physical PQD dataset | `tests/test_gate3*_dataset.py`, `docs/GATE3*_REPORT.md` | **ACTIVE CURRENT** | **KEEP (FROZEN)** | Production ground-truth datasets for Normal, Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient. |
| `data/pq_events.db` | A | SQLite event persistence database | `storage/event_store.py`, `tests/test_event_store.py` | **ACTIVE CURRENT** | **KEEP** | Stores live detected PQ events, waveform slices, and telemetry. |
| `data/ieee9bus_blocks_info.json` | B | Block parameter dump of pristine 9-bus model | `docs/IEEE9BUS_MODEL_AUDIT.md`, `scripts/audit_ieee9bus_model.m` | **REQUIRED SUPPORTING** | **KEEP** | Authoritative electrical parameter reference. |
| `data/matlab_resampled_5k.mat` | B | Calibration MAT-file for 5 kHz resampling | `tests/test_simulink_parity.py` | **REQUIRED SUPPORTING** | **KEEP** | Used in DSP parity verification tests. |
| `data/pqd_features.csv` | C | Legacy 50-Hz 10,000-sample synthetic dataset | `experiments/baseline/`, `data/splits/split_metadata.json` | **HISTORICAL** | **PRESERVE** | Preserved as historical synthetic benchmark baseline; not used for 60-Hz training. |
| `data/splits/` (`train.csv`, `val.csv`, `test.csv`) | C | 70/15/15 splits of legacy 50-Hz dataset | `experiments/baseline/training_config.json` | **HISTORICAL** | **PRESERVE** | Historical record of the 50-Hz synthetic split. |
| `Dataset/BARC DATA.csv` | C | Historical BARC utility recording CSV (10,000 rows) | `doc/PQD_Project_Execution_Plan.md`, `docs/IEEE_ALIGNMENT_AUDIT.md` | **HISTORICAL** | **PRESERVE** | Historical reference dataset cited in early exploratory phase. |

---

### 3.3 DSP & Feature Extraction Subsystem (`dsp/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `dsp/enhanced_features.py` | A | Production 32-feature extraction engine | `pipeline/realtime_pipeline.py`, `tests/test_enhanced_features.py` | **ACTIVE CURRENT** | **KEEP** | Authoritative 32-feature extraction contract (orthogonal projection SNR, harmonic THD, statistical moments). |
| `dsp/waveform_frame.py` | A | Immutable 3-phase waveform container | `dsp/ring_buffer.py`, `pipeline/realtime_pipeline.py` | **ACTIVE CURRENT** | **KEEP** | Validates channel synchrony, sampling rates, and NaN/Inf guards. |
| `dsp/standards_detector.py` | A | Physical threshold & IEEE standard rule engine | `tests/test_standards_detector.py`, `docs/STANDARDS_TRACEABILITY_INDEX.md` | **ACTIVE CURRENT** | **KEEP** | Provides independent physical validation decoupled from ML predictions. |
| `dsp/phase_processor.py` | A | Per-phase sliding window processor | `pipeline/realtime_pipeline.py`, `tests/test_phase_processor.py` | **ACTIVE CURRENT** | **KEEP** | Manages feature extraction across phases L1, L2, L3. |
| `dsp/ring_buffer.py` | A | Multi-channel thread-safe circular buffer | `pipeline/realtime_pipeline.py`, `tests/test_ring_buffer.py` | **ACTIVE CURRENT** | **KEEP** | Handles continuous streaming chunk ingestion at 5 kHz. |
| `dsp/acquisition_adapter.py` | A | Base adapter & concrete Simulink/Sim/HW adapters | `server.py`, `tests/test_simulink_integration.py` | **ACTIVE CURRENT** | **KEEP** | Adapts stream inputs from Simulink HTTP, mock hardware, and simulation. |
| `dsp/feature_extractor.py` | B | Legacy 8-feature extractor | `firmware/src/feature_extraction.cpp`, `tests/test_firmware_parity.py` | **REQUIRED SUPPORTING** | **KEEP** | Preserved for legacy 8-feature parity verification and firmware comparison. |

---

### 3.4 Ingestion Pipeline & Scenarios (`pipeline/`, `scenarios/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `pipeline/realtime_pipeline.py` | A | Core streaming ingestion, DSP, and event pipeline | `server.py`, `tests/test_realtime_pipeline.py` | **ACTIVE CURRENT** | **KEEP** | Orchestrates buffer ingestion, feature extraction, physical rules, and ML inference. |
| `pipeline/disturbance_validator.py` | A | 8-class physical disturbance ground-truth validator | `scripts/build_and_validate_*_dataset.py`, `tests/test_gate3*_dataset.py` | **ACTIVE CURRENT** | **KEEP** | Authoritative rule-based verification against IEEE 1159 / IEEE 519 definitions. |
| `pipeline/frame_queue.py` | A | Thread-safe frame queue for async processing | `pipeline/realtime_pipeline.py` | **ACTIVE CURRENT** | **KEEP** | Queueing layer for live streaming chunks. |
| `scenarios/definitions/` (JSON files) | A | Ground-truth disturbance scenario specifications | `scripts/generate_and_validate_*_scenario.py` | **ACTIVE CURRENT** | **KEEP** | Defines ground-truth physical parameters (onset, duration, severity, switching). |

---

### 3.5 Machine Learning Subsystem (`ml/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `ml/models/model_weights_32.json` | A | Current 32-feature MLP weights (FROZEN) | `server.py`, `dsp/phase_processor.py`, `tests/test_phase_processor.py` | **ACTIVE CURRENT (LEGACY WEIGHTS)** | **KEEP (FROZEN)** | Current runtime weights; marked as `MODEL_DOMAIN_MISMATCH` pending Phase 4 retraining. |
| `ml/models/mlp_deployed.h5` | C | 8-feature Keras MLP model | `ml/compare_models.py`, `server.py` | **HISTORICAL** | **PRESERVE** | 8-feature legacy model trained on 50-Hz synthetic benchmark. |
| `ml/models/mlp_deployed.tflite` | C | 8-feature Int8 quantized TFLite model | `firmware/src/inference.cpp` | **HISTORICAL / FUTURE** | **PRESERVE** | Embedded model for ESP32 TFLite-Micro testing. |
| `ml/models/scaler.pkl` | C | 8-feature StandardScaler | `server.py` | **HISTORICAL** | **PRESERVE** | Scaler for 8-feature legacy model. |
| `ml/models/label_encoder.pkl` | C | LabelEncoder artifact for 8 classes | `server.py` | **HISTORICAL** | **PRESERVE** | Encodes 8 disturbance class strings. |
| `ml/models/model_weights.json` | C | 8-feature exported weights for browser JS | `web/app.js` | **HISTORICAL** | **PRESERVE** | Browser inference weights for 8-feature demo. |
| `ml/compare_models.py` | C | Multi-model benchmark script | `experiments/classical_benchmark/` | **HISTORICAL** | **PRESERVE** | Legacy benchmark comparison (MLP, RF, SVM, KNN). |
| `ml/convert_tflite.py` | C | TFLite conversion & quantization script | `firmware/` | **HISTORICAL / FUTURE** | **PRESERVE** | Used for generating C-array headers for embedded microcontrollers. |
| `ml/generate_dataset.py` | C | Synthetic 50-Hz waveform generator | `Dataset/` | **HISTORICAL** | **PRESERVE** | Historical generator for initial benchmark. |
| `ml/run_diagnostics.py` | C | 12-phase diagnostic investigation script | `doc/PQD_Project_Execution_Plan.md` | **HISTORICAL** | **PRESERVE** | Exploratory diagnostic suite on synthetic data. |

---

### 3.6 Future / Optional Extensions (`firmware/`, `hardware/`, `firebase/`, `mobile_app/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `firmware/` (`src/`, `platformio.ini`) | D | ESP32 C++ firmware (Goertzel DSP, TFLite-Micro) | `tests/test_firmware_parity.py`, `docs/HARDWARE_INTEGRATION.md` | **FUTURE / OPTIONAL** | **KEEP AS FUTURE** | Validated embedded implementation reserved for Phase 6 HIL deployment; parity protected by automated tests. |
| `hardware/` (`safety_checklist.md`) | D | Analog front-end protection & relay schematics | `docs/HARDWARE_EVALUATION.md` | **FUTURE / OPTIONAL** | **KEEP AS FUTURE** | Electrical isolation and Zener clamp specifications for future physical hardware testing. |
| `firebase/` (`firebase_config.py`, `firebase_service.py`) | D | Firebase Realtime Database telemetry bridge | `app_frontend.py`, `docs/PROJECT_AUDIT.md` | **FUTURE / OPTIONAL** | **KEEP AS FUTURE** | Cloud telemetry bridge; decoupled from local streaming pipeline. |
| `mobile_app/` (`src/`, `App.js`, `package.json`) | D | React Native / Flutter monitoring app | `mobile_app/README_MOBILE.md` | **FUTURE / OPTIONAL** | **KEEP AS FUTURE** | Mobile telemetry client scaffolded for cloud event viewing. |

---

### 3.7 Documentation Subsystem (`doc/`, `docs/`)

| Path | Category | Current Usage | Evidence & References | Classification | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|---|
| `docs/GATE_INDEX.md` | A | Master gate verification matrix (Gates 1 to 3X) | `README.md`, `docs/PROJECT_STATUS.md` | **ACTIVE CURRENT** | **KEEP** | Central index of completed gates and audit artifacts. |
| `docs/PROJECT_STATUS.md` | A | Single master project status document | `README.md` | **ACTIVE CURRENT** | **KEEP** | Single human-readable source of project status. |
| `docs/ROADMAP.md` | A | Multi-phase development roadmap | `README.md` | **ACTIVE CURRENT** | **KEEP** | Defines Phases 1 through 6 with strict freeze boundaries. |
| `docs/ARCHITECTURE.md` | A | 7-subsystem architectural specification | `README.md` | **ACTIVE CURRENT** | **KEEP** | Comprehensive simulation-to-telemetry engineering document. |
| `docs/DATASET.md` | A | 8-class physical dataset specification | `docs/GATE3*_REPORT.md` | **ACTIVE CURRENT** | **KEEP** | Detailed documentation of all 60-Hz waveform datasets. |
| `docs/STANDARDS_TRACEABILITY_INDEX.md` | A | 5-tier standards provenance index | IEEE 1159 / IEEE 519 / IEEE 1453 | **ACTIVE CURRENT** | **KEEP** | Maps simulation parameters and DSP thresholds to power standards. |
| `docs/ML_READINESS.md` | A | 10-step protocol for Phase 4 retraining | `docs/PROJECT_STATUS.md` | **ACTIVE CURRENT** | **KEEP** | Criteria and procedures for future 60-Hz ML training. |
| `docs/REPRODUCIBILITY.md` | A | Reproduction recipes, checksums, test guides | All scripts and models | **ACTIVE CURRENT** | **KEEP** | Complete guide for independent reproduction of results. |
| `docs/SOURCE_OF_TRUTH.md` | A | Master registry of authoritative files | Phase 3 Architecture | **ACTIVE CURRENT** | **CREATE** | Explicit single source of truth matrix. |
| `docs/LIVE_MVP_PLAN.md` | A | Phase 5 live demonstration specification | `docs/ROADMAP.md` | **ACTIVE CURRENT** | **CREATE** | Architectural specification for Simulink disturbance rack & MATLAB trigger. |
| `docs/README.md` | A | Documentation navigation landing page | Root repository | **ACTIVE CURRENT** | **CREATE** | Structured directory guide for all project documentation. |
| `docs/GATE3A` to `GATE3X` reports (24 docs) | C | Verified gate reports and quality summaries | Phase 3 audit pipeline | **HISTORICAL EVIDENCE** | **PRESERVE** | Immutable scientific record of physical disturbance implementations. |
| `docs/HARDWARE_EVALUATION.md`, `HARDWARE_INTEGRATION.md`, `REAL_HARDWARE_VALIDATION.md` | D | Early hardware feasibility and HIL studies | Phase 6 planning | **FUTURE / HISTORICAL** | **PRESERVE (TAGGED)** | Add archival/future context banner; preserve technical findings. |
| `doc/` (`PQD_Project_Execution_Plan.md`, `system_design.md`, `Group 11 Proposal.pdf`) | C | Initial academic proposal & preliminary design | Project inception | **HISTORICAL ARCHIVE** | **PRESERVE (TAGGED)** | Add archival context banner; preserve historical proposals. |

---

## 4. Remediation Actions

1. **Delete Dead Files:**
   - Remove `IEEE_9bus/IEEE_9bus_new_o.slx.autosave` (unreferenced autosave artifact).
2. **Standardize Documentation:**
   - Create `docs/SOURCE_OF_TRUTH.md` (Part 4).
   - Create `docs/LIVE_MVP_PLAN.md` (Part 14).
   - Create `docs/README.md` (Part 23).
   - Completely rewrite root `README.md` (Part 10) and `RUNTHISPROJECT.md` (Part 11) to eliminate obsolete 50-Hz / 8-feature / ESP32-first claims.
   - Update `CHANGELOG.md` with modernization milestone (Part 24).
   - Add clear historical/future status banners to older documentation (`doc/`, `docs/HARDWARE_*`).
3. **Verify Integrity & Tests:**
   - Confirm pristine `.slx` and `model_weights_32.json` are byte-for-byte untouched.
   - Run full 302-test pytest regression suite.

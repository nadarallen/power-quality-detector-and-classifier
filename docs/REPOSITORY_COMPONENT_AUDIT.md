# Repository Component Classification & Audit Registry

**Document Version:** 1.0.0  
**Phase Status:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Context:** 60-Hz WSCC IEEE 9-Bus Simulation & Production Python DSP Pipeline  

---

## 1. Classification Taxonomy

Every subsystem, directory, and major artifact across the repository is classified into one of the following strict categories:

1. **CURRENT:** Active production component required for 60-Hz IEEE 9-bus simulation, DSP feature extraction, event detection, or web telemetry.
2. **SUPPORTING:** Required configuration, schemas, fixtures, and utilities necessary for executing tests and data pipelines.
3. **HISTORICAL:** Immutable scientific record of completed gate audits, classical ML baselines, and early academic proposals.
4. **FUTURE:** Planned Phase 5 live demonstration or Phase 6 embedded HIL / cloud extensions.
5. **DEPRECATED:** Legacy 50-Hz or 8-feature implementations preserved solely for backward-compatibility tests.
6. **GENERATED:** Compiler output, AST cache, temporary simulation MAT files, or SQLite runtime databases.
7. **DEAD:** Unreferenced files with zero runtime, testing, or scientific value.

---

## 2. Complete Repository Component Classification Matrix

| Path / Component | Category | Current Usage & Role | Evidence & Test Coverage | Recommended Action | Technical Rationale |
|---|---|---|---|---|---|
| `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` | **CURRENT** | Pristine 60-Hz WSCC reference baseline | SHA-256 `5D833D8F...`, `tests/test_gate3a_60hz_compatibility.py` | **KEEP (FROZEN)** | Authoritative uncorrupted electrical power system model. |
| `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx` | **CURRENT** | Working disturbance generation model (8 injection blocks) | `scripts/run_disturbance_simulation.m`, `scripts/apply_*` | **KEEP** | Authoritative model for physical disturbance synthesis. |
| `data/ieee9bus_60hz/` (8 subdirs) | **CURRENT** | Authoritative 8-class physical datasets (9,216 frames) | `tests/test_gate3*_dataset.py`, `docs/GATE3*_REPORT.md` | **KEEP (FROZEN)** | Production ground-truth datasets for 60-Hz ML training. |
| `data/pq_events.db` | **CURRENT** | SQLite persistence store for detected PQ events | `storage/event_store.py`, `tests/test_event_store.py` | **KEEP** | Real-time event log and waveform snapshot database. |
| `data/pqd_features.csv` | **HISTORICAL** | Legacy 10,000-sample synthetic 50-Hz benchmark | `experiments/baseline/`, `data/splits/` | **ARCHIVE** | Historical benchmark dataset; not used for 60-Hz training. |
| `data/splits/` | **HISTORICAL** | 70/15/15 splits of legacy synthetic benchmark | `experiments/baseline/training_config.json` | **ARCHIVE** | Historical record of early synthetic splitting. |
| `Dataset/BARC DATA.csv` | **HISTORICAL** | Historical utility recordings cited in early proposal | `doc/PQD_Project_Execution_Plan.md` | **ARCHIVE** | Historical exploratory data. |
| `dsp/enhanced_features.py` | **CURRENT** | Authoritative 32-feature extraction engine | `tests/test_enhanced_features.py`, `tests/test_snr_phase_invariance.py` | **KEEP** | Production DSP contract implementing orthogonal SNR and Goertzel H1–H11. |
| `dsp/waveform_frame.py` | **CURRENT** | Multi-channel 3-phase waveform container | `tests/test_waveform_frame.py` | **KEEP** | Ensures 5 kHz rate, 200 ms duration, synchrony, and NaN guards. |
| `dsp/standards_detector.py` | **CURRENT** | Independent physical standards rule engine | `tests/test_standards_detector.py` | **KEEP** | IEEE 1159 / IEEE 519 physical detection decoupled from ML. |
| `dsp/phase_processor.py` | **CURRENT** | Multi-phase sliding window processor | `tests/test_phase_processor.py` | **KEEP** | Sliding window feature extraction over 3 phases. |
| `dsp/ring_buffer.py` | **CURRENT** | Circular streaming buffer (5 kHz) | `tests/test_ring_buffer.py` | **KEEP** | Ingests streaming chunks with zero sample loss. |
| `dsp/acquisition_adapter.py` | **CURRENT** | Concrete streaming adapters (Simulink, Simulation, Mock) | `tests/test_simulink_integration.py` | **KEEP** | Standardized input adapter for live and simulated data streams. |
| `dsp/baseline_features.py` | **DEPRECATED** | Legacy 8-feature extractor | `tests/test_firmware_parity.py` | **KEEP (DEPRECATED)** | Preserved for automated firmware parity verification. |
| `pipeline/realtime_pipeline.py` | **CURRENT** | Core streaming ingestion, DSP & event pipeline | `tests/test_realtime_pipeline.py` | **KEEP** | Orchestrates buffer updates, DSP extraction, rules, and telemetry. |
| `pipeline/disturbance_validator.py` | **CURRENT** | 8-class physical ground-truth validator | `tests/test_gate3*_dataset.py` | **KEEP** | Deterministic physical rule verification across all 8 classes. |
| `scenarios/definitions/` (JSON) | **CURRENT** | Declarative disturbance scenario controller specs | `scripts/generate_and_validate_*` | **KEEP** | Ground truth source for all physical disturbance parameters. |
| `integration/matlab/` | **CURRENT** | Simulink-to-Python HTTP streaming bridge | `tests/test_simulink_integration.py` | **KEEP** | Scripts for automated ingestion and live streaming from Simulink. |
| `ml/models/model_weights_32.json` | **CURRENT (FROZEN)** | Current 32-feature weights (FROZEN pending Phase 4) | `server.py`, `dsp/phase_processor.py` | **KEEP (FROZEN)** | Runtime weights flagging `MODEL_DOMAIN_MISMATCH` pending retraining. |
| `ml/models/mlp_deployed.h5` | **HISTORICAL** | Historical 8-feature Keras MLP model | `ml/compare_models.py` | **ARCHIVE** | Historical model artifact from synthetic 50-Hz benchmark. |
| `firmware/` (`src/`, `platformio.ini`) | **FUTURE** | ESP32 C++ firmware (Goertzel DSP, TFLite-Micro) | `tests/test_firmware_parity.py`, `future/esp32-hil/` | **KEEP AS FUTURE** | Phase 6 optional embedded HIL extension; protected by parity tests. |
| `hardware/` (`safety_checklist.md`) | **FUTURE** | Analog front-end protection & relay schematics | `future/esp32-hil/` | **KEEP AS FUTURE** | Phase 6 hardware safety and isolation specifications. |
| `firebase/` | **FUTURE** | Firebase Realtime Database telemetry sync | `app_frontend.py` | **KEEP AS FUTURE** | Optional cloud telemetry client. |
| `mobile_app/` | **FUTURE** | React Native / Flutter monitoring viewer | `mobile_app/README_MOBILE.md` | **KEEP AS FUTURE** | Optional mobile viewer client. |
| `experiments/` & `reports/` | **HISTORICAL** | Classical ML benchmark CSVs and confusion matrices | `experiments/classical_benchmark/` | **ARCHIVE** | Immutable record of early multi-model comparisons. |
| `doc/` | **HISTORICAL** | Initial project proposals and early system designs | Inception record | **ARCHIVE** | Historical proposals tagged with archival banners. |
| `graphify-out/` | **GENERATED** | Generated AST cache and graph visualizer | External tool cache | **REMOVE FROM GIT** | Generated temporary artifacts; added to `.gitignore`. |
| `IEEE_9bus/IEEE_9bus_new_o.slx.autosave` | **DEAD** | Old unreferenced Simulink autosave | Zero references | **DELETED** | Removed from repository. |

# Power Quality Disturbance Documentation Index

**Project Title:** AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation  
**Project Phase:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Frequency:** 60 Hz (WSCC Transmission Grid Standard)  
**Authoritative Sampling Rate:** 5,000 Hz ($T_s = 200\ \mu\text{s}$, 1,000 samples per 200 ms frame)  

---

## 1. Current Master Project Documentation

These documents define the current authoritative architecture, contracts, procedures, and roadmap for the project:

| Document | Description | Key Focus Area |
|---|---|---|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Single master human-readable project status document. | Lifecycle status, completed phases, strict freeze rules, and metrics. |
| [SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md) | Authoritative source-of-truth registry across all subsystems. | File paths, SHA-256 hashes, dataset directories, and contract owners. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | End-to-end 7-subsystem engineering specification. | IEEE 9-bus physics, Bus 5 observation, 5 kHz DSP, event engine, and UI. |
| [ROADMAP.md](ROADMAP.md) | Multi-phase engineering roadmap (Phases 1 through 6). | Phase 3 Complete, Phase 4 ML Next, Phase 5 Live MVP Future, Phase 6 HIL. |
| [DATASET.md](DATASET.md) | Comprehensive 8-class physical dataset documentation. | Physical mechanisms, parameter ranges, validation results, and SNR profiles. |
| [STANDARDS_TRACEABILITY_INDEX.md](STANDARDS_TRACEABILITY_INDEX.md) | 5-tier standards provenance index. | Traceability across IEEE 1159, IEEE 519, IEEE 1453, and IEC 61000-4-30. |
| [ML_READINESS.md](ML_READINESS.md) | 10-step Phase 4 machine learning retraining protocol. | Grouped splitting, scaler fitting, hyperparameter tuning, and export. |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | Reproduction recipes, environment setup, and test guide. | Conda/Python requirements, MATLAB scripts, checksum verification, pytest. |
| [LIVE_MVP_PLAN.md](LIVE_MVP_PLAN.md) | Planned architecture for Phase 5 live demonstration MVP. | MATLAB trigger API, Simulink disturbance rack, and streaming oscilloscope. |
| [GATE_INDEX.md](GATE_INDEX.md) | Master gate verification matrix (Gates 1 to 3X). | Gate-by-gate pass criteria, artifacts, tests, and audit trail. |
| [REPOSITORY_LEGACY_AUDIT.md](REPOSITORY_LEGACY_AUDIT.md) | Systematic component inventory and classification matrix. | Categorization of active, historical, supporting, and future extensions. |

---

## 2. Scientific Validation Record & Gate Reports

Each completed engineering gate produced an immutable technical report, audit log, and machine-readable summary:

### Phase 1 & 2: Electrical Foundation, 60-Hz Compatibility & DSP Parity
- **Gate 3A (60-Hz Compatibility):** [GATE3A_IEEE9BUS_60HZ_COMPATIBILITY_AUDIT.md](GATE2_60HZ_COMPATIBILITY_AUDIT.md)
- **Gate 3B / 3B.1 (Normal Baseline):** [GATE3B_NORMAL_DATASET_REPORT.md](GATE3B_NORMAL_DATASET_AUDIT.md) | [GATE3B1_NORMAL_DATASET_AUDIT.md](GATE3B1_NORMAL_DATASET_QUALITY_AUDIT.md)
- **Gate 3C (Scenario Controller & Validation):** [GATE3C_DISTURBANCE_SPECIFICATION.md](GATE3C_DISTURBANCE_SPECIFICATION.md) | [GATE3C_STANDARDS_TRACEABILITY.md](GATE3C_STANDARDS_TRACEABILITY.md) | [GATE3C_VALIDATION_PLAN.md](GATE3C_VALIDATION_PLAN.md)

### Phase 3: Physical Disturbance Generation & Quality Audits
- **Voltage Sag (Gates 3D, 3E, 3F):** [GATE3D_SAG_IMPLEMENTATION.md](GATE3D_SAG_IMPLEMENTATION.md) | [GATE3E_SAG_DATASET_REPORT.md](GATE3E_SAG_DATASET_REPORT.md) | [GATE3F_SAG_DATASET_AUDIT.md](GATE3F_SAG_DATASET_AUDIT.md)
- **Voltage Swell (Gates 3G, 3H, 3I):** [GATE3G_SWELL_IMPLEMENTATION.md](GATE3G_SWELL_IMPLEMENTATION.md) | [GATE3H_SWELL_DATASET_REPORT.md](GATE3H_SWELL_DATASET_REPORT.md) | [GATE3I_SWELL_DATASET_AUDIT.md](GATE3I_SWELL_DATASET_AUDIT.md)
- **Voltage Interruption (Gates 3J, 3K, 3L):** [GATE3J_INTERRUPTION_IMPLEMENTATION.md](GATE3J_INTERRUPTION_IMPLEMENTATION.md) | [GATE3K_INTERRUPTION_DATASET_REPORT.md](GATE3K_INTERRUPTION_DATASET_REPORT.md) | [GATE3L_INTERRUPTION_DATASET_AUDIT.md](GATE3L_INTERRUPTION_DATASET_AUDIT.md)
- **Harmonics (Gates 3M, 3N, 3O):** [GATE3M_HARMONICS_IMPLEMENTATION.md](GATE3M_HARMONICS_IMPLEMENTATION.md) | [GATE3N_HARMONICS_DATASET_REPORT.md](GATE3N_HARMONICS_DATASET_REPORT.md) | [GATE3O_HARMONICS_DATASET_AUDIT.md](GATE3O_HARMONICS_DATASET_AUDIT.md)
- **Voltage Flicker (Gates 3P, 3Q, 3R):** [GATE3P_FLICKER_IMPLEMENTATION.md](GATE3P_FLICKER_IMPLEMENTATION.md) | [GATE3Q_FLICKER_DATASET_REPORT.md](GATE3Q_FLICKER_DATASET_REPORT.md) | [GATE3R_FLICKER_DATASET_AUDIT.md](GATE3R_FLICKER_DATASET_AUDIT.md)
- **Voltage Notch (Gates 3S, 3T, 3U):** [GATE3S_NOTCH_IMPLEMENTATION.md](GATE3S_NOTCH_IMPLEMENTATION.md) | [GATE3T_NOTCH_DATASET_REPORT.md](GATE3T_NOTCH_DATASET_REPORT.md) | [GATE3U_NOTCH_DATASET_AUDIT.md](GATE3U_NOTCH_DATASET_AUDIT.md)
- **Oscillatory Transient (Gates 3V, 3W, 3X):** [GATE3V_TRANSIENT_IMPLEMENTATION.md](GATE3V_TRANSIENT_IMPLEMENTATION.md) | [GATE3W_TRANSIENT_DATASET_REPORT.md](GATE3W_TRANSIENT_DATASET_REPORT.md) | [GATE3X_TRANSIENT_DATASET_AUDIT.md](GATE3X_TRANSIENT_DATASET_AUDIT.md)

### Phase 4: Machine Learning Implementation & Independent Test Evaluation
- **Gate 4A (Final Dataset Freeze & Leakage Audit):** [GATE4A_FINAL_DATASET_FREEZE_AUDIT.md](GATE4A_FINAL_DATASET_FREEZE_AUDIT.md)
- **Gate 4B (Leakage-Safe Baseline Model Comparison):** [GATE4B_BASELINE_MODEL_COMPARISON.md](GATE4B_BASELINE_MODEL_COMPARISON.md)
- **Gate 4C (60 Hz MLP Tuning & Candidate Export):** [GATE4C_MLP_TUNING_AUDIT.md](GATE4C_MLP_TUNING_AUDIT.md)
- **Gate 4D (Locked Test Partition Independent Evaluation):** [GATE4D_LOCKED_TEST_EVALUATION.md](GATE4D_LOCKED_TEST_EVALUATION.md)
- **Artifact Reconciliation & Provenance Audit:** [ARTIFACT_INTEGRITY_RECONCILIATION.md](ARTIFACT_INTEGRITY_RECONCILIATION.md)
- **Clean-Clone Reproduction Guide:** [REPRODUCING_PHASE4.md](REPRODUCING_PHASE4.md)

---

## 3. Historical Archives & Future Extensions

These documents preserve early exploratory benchmarks, academic proposals, and optional Phase 6 hardware feasibility studies:

- **Historical Hardware & HIL Feasibility (Phase 6):** [HARDWARE_EVALUATION.md](HARDWARE_EVALUATION.md), [HARDWARE_INTEGRATION.md](HARDWARE_INTEGRATION.md), [REAL_HARDWARE_VALIDATION.md](REAL_HARDWARE_VALIDATION.md), [LATENCY_BENCHMARK.md](LATENCY_BENCHMARK.md).
- **Initial Academic Inception & Proposals:** [PQD_Project_Execution_Plan.md](../doc/PQD_Project_Execution_Plan.md), [system_design.md](../doc/system_design.md).
- **Early Exploratory Benchmarks:** [GATE3_DATASET_TRAINING_AUDIT.md](GATE3_DATASET_TRAINING_AUDIT.md), [PROJECT_AUDIT.md](PROJECT_AUDIT.md), [PROJECT_STATE.md](PROJECT_STATE.md), [AUDIT_STATUS.md](AUDIT_STATUS.md).

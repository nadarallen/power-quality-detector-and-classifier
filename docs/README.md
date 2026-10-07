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
| [PROJECT_STATUS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/PROJECT_STATUS.md) | Single master human-readable project status document. | Lifecycle status, completed phases, strict freeze rules, and metrics. |
| [SOURCE_OF_TRUTH.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/SOURCE_OF_TRUTH.md) | Authoritative source-of-truth registry across all subsystems. | File paths, SHA-256 hashes, dataset directories, and contract owners. |
| [ARCHITECTURE.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ARCHITECTURE.md) | End-to-end 7-subsystem engineering specification. | IEEE 9-bus physics, Bus 5 observation, 5 kHz DSP, event engine, and UI. |
| [ROADMAP.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ROADMAP.md) | Multi-phase engineering roadmap (Phases 1 through 6). | Phase 3 Complete, Phase 4 ML Next, Phase 5 Live MVP Future, Phase 6 HIL. |
| [DATASET.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/DATASET.md) | Comprehensive 8-class physical dataset documentation. | Physical mechanisms, parameter ranges, validation results, and SNR profiles. |
| [STANDARDS_TRACEABILITY_INDEX.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/STANDARDS_TRACEABILITY_INDEX.md) | 5-tier standards provenance index. | Traceability across IEEE 1159, IEEE 519, IEEE 1453, and IEC 61000-4-30. |
| [ML_READINESS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ML_READINESS.md) | 10-step Phase 4 machine learning retraining protocol. | Grouped splitting, scaler fitting, hyperparameter tuning, and export. |
| [REPRODUCIBILITY.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REPRODUCIBILITY.md) | Reproduction recipes, environment setup, and test guide. | Conda/Python requirements, MATLAB scripts, checksum verification, pytest. |
| [LIVE_MVP_PLAN.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/LIVE_MVP_PLAN.md) | Planned architecture for Phase 5 live demonstration MVP. | MATLAB trigger API, Simulink disturbance rack, and streaming oscilloscope. |
| [GATE_INDEX.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE_INDEX.md) | Master gate verification matrix (Gates 1 to 3X). | Gate-by-gate pass criteria, artifacts, tests, and audit trail. |
| [REPOSITORY_LEGACY_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REPOSITORY_LEGACY_AUDIT.md) | Systematic component inventory and classification matrix. | Categorization of active, historical, supporting, and future extensions. |

---

## 2. Scientific Validation Record & Gate Reports

Each completed engineering gate produced an immutable technical report, audit log, and machine-readable summary:

### Phase 1 & 2: Electrical Foundation, 60-Hz Compatibility & DSP Parity
- **Gate 3A (60-Hz Compatibility):** [GATE3A_IEEE9BUS_60HZ_COMPATIBILITY_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3A_IEEE9BUS_60HZ_COMPATIBILITY_AUDIT.md)
- **Gate 3B / 3B.1 (Normal Baseline):** [GATE3B_NORMAL_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3B_NORMAL_DATASET_REPORT.md) | [GATE3B1_NORMAL_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3B1_NORMAL_DATASET_AUDIT.md)
- **Gate 3C (Scenario Controller & Validation):** [GATE3C_DISTURBANCE_SPECIFICATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_DISTURBANCE_SPECIFICATION.md) | [GATE3C_STANDARDS_TRACEABILITY.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_STANDARDS_TRACEABILITY.md) | [GATE3C_VALIDATION_PLAN.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_VALIDATION_PLAN.md)

### Phase 3: Physical Disturbance Generation & Quality Audits
- **Voltage Sag (Gates 3D, 3E, 3F):** [GATE3D_SAG_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3D_SAG_IMPLEMENTATION.md) | [GATE3E_SAG_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3E_SAG_DATASET_REPORT.md) | [GATE3F_SAG_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3F_SAG_DATASET_AUDIT.md)
- **Voltage Swell (Gates 3G, 3H, 3I):** [GATE3G_SWELL_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3G_SWELL_IMPLEMENTATION.md) | [GATE3H_SWELL_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3H_SWELL_DATASET_REPORT.md) | [GATE3I_SWELL_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3I_SWELL_DATASET_AUDIT.md)
- **Voltage Interruption (Gates 3J, 3K, 3L):** [GATE3J_INTERRUPTION_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3J_INTERRUPTION_IMPLEMENTATION.md) | [GATE3K_INTERRUPTION_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3K_INTERRUPTION_DATASET_REPORT.md) | [GATE3L_INTERRUPTION_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3L_INTERRUPTION_DATASET_AUDIT.md)
- **Harmonics (Gates 3M, 3N, 3O):** [GATE3M_HARMONICS_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3M_HARMONICS_IMPLEMENTATION.md) | [GATE3N_HARMONICS_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3N_HARMONICS_DATASET_REPORT.md) | [GATE3O_HARMONICS_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3O_HARMONICS_DATASET_AUDIT.md)
- **Voltage Flicker (Gates 3P, 3Q, 3R):** [GATE3P_FLICKER_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3P_FLICKER_IMPLEMENTATION.md) | [GATE3Q_FLICKER_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3Q_FLICKER_DATASET_REPORT.md) | [GATE3R_FLICKER_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3R_FLICKER_DATASET_AUDIT.md)
- **Voltage Notch (Gates 3S, 3T, 3U):** [GATE3S_NOTCH_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3S_NOTCH_IMPLEMENTATION.md) | [GATE3T_NOTCH_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3T_NOTCH_DATASET_REPORT.md) | [GATE3U_NOTCH_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3U_NOTCH_DATASET_AUDIT.md)
- **Oscillatory Transient (Gates 3V, 3W, 3X):** [GATE3V_TRANSIENT_IMPLEMENTATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3V_TRANSIENT_IMPLEMENTATION.md) | [GATE3W_TRANSIENT_DATASET_REPORT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3W_TRANSIENT_DATASET_REPORT.md) | [GATE3X_TRANSIENT_DATASET_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3X_TRANSIENT_DATASET_AUDIT.md)

---

## 3. Historical Archives & Future Extensions

These documents preserve early exploratory benchmarks, academic proposals, and optional Phase 6 hardware feasibility studies:

- **Historical Hardware & HIL Feasibility (Phase 6):** [HARDWARE_EVALUATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/HARDWARE_EVALUATION.md), [HARDWARE_INTEGRATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/HARDWARE_INTEGRATION.md), [REAL_HARDWARE_VALIDATION.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REAL_HARDWARE_VALIDATION.md), [LATENCY_BENCHMARK.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/LATENCY_BENCHMARK.md).
- **Initial Academic Inception & Proposals:** [PQD_Project_Execution_Plan.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/doc/PQD_Project_Execution_Plan.md), [system_design.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/doc/system_design.md).
- **Early Exploratory Benchmarks:** [GATE3_DATASET_TRAINING_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3_DATASET_TRAINING_AUDIT.md), [PROJECT_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/PROJECT_AUDIT.md), [PROJECT_STATE.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/PROJECT_STATE.md), [AUDIT_STATUS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/AUDIT_STATUS.md).

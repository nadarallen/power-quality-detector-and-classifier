# AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation

> **Current Lifecycle Phase:** Phase 5 — Multi-Model Power Quality Comparative Research (**COMPLETE**)  
> **Primary Research Branch:** `research/pq-comparative-lab`  
> **Stable Baseline Branch:** `main` (Preserved intact at `8a4e567`)  
>
> [![Tests](https://img.shields.io/badge/tests-358%20passed-brightgreen.svg)](tests/)
> [![Sampling](https://img.shields.io/badge/sampling-dual--rate%2020%20kHz%20%26%205%20kHz-blue.svg)](data/ieee9bus_60hz_phase5c/)
> [![Grid](https://img.shields.io/badge/grid-WSCC%2060%20Hz%20IEEE%209--bus-orange.svg)](IEEE_9bus/)
> [![Classes](https://img.shields.io/badge/classes-8%20disturbances%20audited-success.svg)](data/ieee9bus_60hz_phase5c/)
> [![Phase 5](https://img.shields.io/badge/phase%205-COMPLETE%20(Comparative%20Research)-brightgreen.svg)](docs/PHASE5_FINAL_RESEARCH_REPORT.md)
> [![Phase 6](https://img.shields.io/badge/phase%206-FUTURE%20SCOPE%20(Not%20Implemented)-lightgrey.svg)](docs/ROADMAP.md)

---

## Navigation & Quick Links

1. [Project Overview & Limitations](#1-project-overview--limitations)
2. [Getting Started & Installation](#2-getting-started--installation)
3. [Run or Inspect the Simulation Data](#3-run-or-inspect-the-simulation-data)
4. [Simulation Visualization: Visualize Sag and Swell in MATLAB](#4-simulation-visualization-visualize-sag-and-swell-in-matlab)
5. [Explore the ML & Research Results](#5-explore-the-ml--research-results)
6. [Run Tests and Reproduce Results](#6-run-tests-and-reproduce-results)
7. [Research Status & Future Scope](#7-research-status--future-scope)
8. [Comprehensive Documentation Index](#8-comprehensive-documentation-index)

---

## 1. Project Overview & Limitations

This repository implements an end-to-end, scientifically validated, and standards-aligned research framework for simulating, detecting, extracting, and categorizing **Power Quality Disturbances (PQD)** in high-voltage electrical transmission systems.

The primary architecture couples an electromagnetic transient simulation of the **WSCC 3-Machine 9-Bus Network** (operating at $60.0\text{ Hz}$ in MATLAB/Simulink Simscape Electrical) with a high-performance Python Digital Signal Processing (DSP) and machine learning pipeline. The project investigates:
- **Which electrical features distinguish eight disturbance classes** (Normal, Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient).
- **Comparative model performance:** Classical Machine Learning (32 features) vs. Raw-Waveform Deep Learning (1D-CNN, TCN) vs. Multi-Modal Representation Fusion (`HybridPQNet`).
- **Dual-rate acquisition benefits:** Comparing 5 kHz canonical decimated waveforms against 20 kHz high-resolution representations for sub-cycle commutations and high-frequency oscillations.

```
+-----------------------------------------------------------------------------+
|                      CURRENT PRODUCTION ARCHITECTURE                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   |         IEEE 9-Bus WSCC Transmission Model (Simscape 60 Hz)         |   |
|   |  - 3 Generators, 3 Transformers, 9 Transmission Buses, 3 Loads      |   |
|   |  - Authoritative Observation Point: Bus 5 (230 kV Load Bus)         |   |
|   |  - Pristine Reference: IEEE_9bus_PQD_HIL_R2025a.slx (Frozen, R/O)   |   |
|   |  - Working Model:      IEEE_9bus_PQD_DISTURBANCES.slx (7 blocks)    |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Bus 5 Vabc, Iabc (Continuous)       |
|   +---------------------------------------------------------------------+   |
|   |         Dual-Rate Acquisition & Resampling Engine                   |   |
|   |  - High-Rate Branch:  20 kHz (4,000 samples / 200 ms, Ts = 50 us)   |   |
|   |  - Canonical Branch:  5 kHz (1,000 samples / 200 ms, Ts = 200 us)   |   |
|   |  - Zero-phase 8th-order Chebyshev Type I anti-alias filter          |   |
|   |  - Fixed-reference sensor noise (52, 46, 40 dB) & bipolar ADC       |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Dual-Rate Waveforms & Features      |
|   +---------------------------------------------------------------------+   |
|   |         Production 32-Feature DSP Engine & Event Processor          |   |
|   |  - H1–H11 Goertzel Bank, Orthogonal SNR, Half-Cycle Sliding RMS     |   |
|   |  - Constant feature identification (dominant_freq, true_freq)       |   |
|   |  - Numerical parity with MATLAB verified (< 0.000050 tolerance)     |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Multi-Modal Tensors & Features      |
|   +---------------------------------------------------------------------+   |
|   |         Multi-Model Machine Learning Benchmark                      |   |
|   |  - Track A: Classical ML (MLP, RF, ExtraTrees, SVM, HGB, LogReg)    |   |
|   |  - Track B: Raw Waveform DL (Compact 1D-CNN, Temporal ConvNet)      |   |
|   |  - Track C: Hybrid Representation (HybridPQNet: Waveform + Features)|   |
|   |  - Quarantined Challenge Partition (Conditions 33–36, 0 Leakage)    |   |
|   +---------------------------------------------------------------------+   |
|                                      |                                      |
|                                      v  Interactive Telemetry & Plots       |
|   +---------------------------------------------------------------------+   |
|   |         Interactive Research Platform (app.py)                      |   |
|   |  - Tab 1: Dataset Explorer & Dual-Rate Waveform Visualizer          |   |
|   |  - Tab 2: Model Comparison (Classical vs DL vs Hybrid)              |   |
|   |  - Tab 3: Feature Analysis, Permutation Importance & SHAP           |   |
|   |  - Tab 4: Waveform Occlusion Sensitivity & 3-Phase Synchrony Ablation|  |
|   |  - Tab 5: Quarantined Challenge Evaluation & Provenance             |   |
|   +---------------------------------------------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Research Scope & Limitations
- **Electromagnetic Simulation Domain:** All training, validation, and challenge datasets originate from high-fidelity Simscape Electrical simulations on the IEEE 9-bus transmission benchmark. Performance results do not represent physical substation PMU deployments on real-world utility networks.
- **Base Grid Frequency:** The network benchmark operates at $60.0\text{ Hz}$. The constant feature audit established that `dominant_freq` and `true_dominant_freq` remain invariant at 60.0 Hz under transmission bus loading; conclusions do not imply wide-range frequency tracking under islanded microgrid deviations ($\pm 5\text{ Hz}$).
- **Single-Phase Commutation Shunt:** The simulated Notch mechanism employs a commutation short-circuit switching surrogate, which captures the electrical commutation notch morphology without modeling an entire 6-pulse thyristor bridge converter.
- **Phase 6 Firmware & Hardware Deployment:** Microcontroller firmware (`firmware/`), analog front-end schematics (`hardware/`), and physical HIL deployment remain strictly **Planned / Future Scope — Not Yet Implemented**.

---

## 2. Getting Started & Installation

### Prerequisites
- **Python:** 3.10, 3.12, or 3.14 (tested on x86_64 Windows & Linux).
- **MATLAB / Simulink (Optional):** MATLAB R2024b or R2025a with Simscape Electrical is only required if generating new physical simulations. All pre-generated datasets, models, and dashboard features run 100% standalone in Python without MATLAB.

### Setup Instructions
```bash
# 1. Clone the repository on the primary research branch
git clone -b research/pq-comparative-lab https://github.com/nadarallen/power-quality-detector-and-classifier.git
cd power-quality-detector-and-classifier

# 2. Pull Git LFS objects (retrieves the 131.65 MB 20 kHz waveform archive)
git lfs pull

# 3. Create and activate a Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 4. Install base and research dependencies
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

---

## 3. Run or Inspect the Simulation Data

### Available Pre-Computed Datasets
The repository bundles two authoritative, cryptographically verified datasets:

| Dataset | Location | Manifest | Trajectories | Total Frames | Sampling Rates | Audit Report |
|---|---|---|:---:|:---:|---|---|
| **Historical Baseline (Phase 3–4)** | `data/ieee9bus_60hz/` | `dataset_manifest_v1.json` | 284 | 9,184 | 5 kHz (1,000 pts/window) | [docs/DATASET.md](docs/DATASET.md) |
| **Expanded Dual-Rate (Phase 5C)** | `data/ieee9bus_60hz_phase5c/` | `dataset_manifest_v2.json` | 144 | 4,608 | Dual-Rate: 20 kHz & 5 kHz | [docs/PHASE5C_EXPANDED_DATASET_FREEZE_AUDIT.md](docs/PHASE5C_EXPANDED_DATASET_FREEZE_AUDIT.md) |

### Simulation Matrix & Runner Distinction
It is critical to distinguish between the core simulation matrix, the extended matrix design, and the execution caching behavior:
1. **Core Matrix vs. Extended Matrix Design:**
   - **Core Matrix:** [`scenarios/phase5b2_simulation_matrix.json`](scenarios/phase5b2_simulation_matrix.json) defines the **144 core trajectories** (18 per class) executed to produce the **4,608 frozen Phase 5C frames**.
   - **Extended Matrix:** [`scenarios/phase5c_extended_matrix.json`](scenarios/phase5c_extended_matrix.json) is a separate, versioned specification defining 368 independent trajectories across 40 operating conditions (224 supplementary scenarios) intended for future scaled extensions. The current runner specifically simulates the 144 core trajectories.
2. **Initial Simulation Generation vs. Verification/Reuse Run:**
   - The initial electromagnetic generation of the 144 continuous raw trajectories was executed in MATLAB R2025a (wall time: 408.26 s) and committed under commit `5d4cf51`.
   - The runner [`scripts/run_phase5c_bulk_simulation.m`](scripts/run_phase5c_bulk_simulation.m) includes a validation check: if a target `.mat` file exists and has 7,601 rows in `V_cont_20k`, it skips simulation. In subsequent verification runs, `run_phase5c_bulk_simulation()` safely skips all 144 pre-existing files in ~2.09 s with 0 failures, verifying dataset integrity without modifying existing data.

---

## 4. Simulation Visualization: Visualize Sag and Swell in MATLAB

For a beginner-friendly, copy-paste MATLAB tutorial for visualizing existing Sag and Swell simulation recordings without running Simulink or creating separate `.m` scripts, consult:

👉 **[MATLAB Voltage Sag & Swell Waveform Visualization Guide](docs/guides/MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md)**

The guide provides five self-contained MATLAB command blocks (`Block A` through `Block E`) designed to be copied and pasted directly into the MATLAB Command Window in order:
- **Block A:** Configures repository paths and verifies that pre-recorded MAT files exist.
- **Block B:** Inspects variable headers (`whos('-file', ...)`), loads recordings, displays scenario metadata, and runs sanity checks (dimensions, 0 NaNs, 0 Infs).
- **Block C:** Renders **Figure 1** with two vertically stacked panels comparing three-phase Sag and Swell voltage waveforms with shaded disturbance intervals and pre-/during-/post-disturbance annotations.
- **Block D:** Renders **Figure 2** with two vertically stacked panels comparing three-phase transmission line currents for Sag and Swell after verifying current data validity.
- **Block E:** Programmatically verifies sample counts (7,601 at 20 kHz; 1,901 at 5 kHz), sampling intervals ($\Delta t = 50\ \mu\text{s}$ and $200\ \mu\text{s}$), sampling rates, durations ($0.38\text{ s}$), and disturbance timing.

The guide also provides complete instructions on using MATLAB interactive tools (zoom, pan, data cursor tips) and exporting publication-quality figures (`exportgraphics`).

---

## 5. Explore the ML & Research Results

### Launch the Interactive Research Dashboard
The project includes a standalone Streamlit research lab (`app.py`):

```bash
# Launch the dashboard
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

### Operational Modes & Research Tabs
- **Mode A: Recorded Research Explorer (Zero MATLAB Requirement — FULLY VERIFIED):**  
  Fully functional offline without MATLAB. Loads pre-computed waveforms, features, and model weights directly.
  - **Tab 1: Dataset Explorer & Dual-Rate Waveforms:** Compare 5 kHz and 20 kHz representations, compute FFT spectra, and inspect scenario metadata.
  - **Tab 2: Multi-Model Benchmark Comparison:** Side-by-side performance across Classical ML, 1D-CNN, TCN, and `HybridPQNet`.
  - **Tab 3: Feature Analysis & Explainability:** Permutation importance ranking, 5 functional group ablations, and SHAP attribution plots.
  - **Tab 4: Waveform Model Interpretation:** Temporal occlusion sensitivity curves and 3-phase synchrony ablation.
  - **Tab 5: Quarantined Challenge Evaluation:** Audited evaluation on held-out Conditions 33–36 with zero leakage.
- **Mode B: Simulink Live Experiment Runner (SCRIPT HOOKS IMPLEMENTED — RUNTIME EXECUTION UNVERIFIED / OPTIONAL):**  
  Provides UI hooks to parameterize live disturbance injections and trigger MATLAB/Simulink. *Note: Live MATLAB execution is marked UNVERIFIED / NOT TESTED in headless automated environments due to external MATLAB license requirements.*

### Summary of Key Benchmark Findings

| Model Family | Candidate Architecture | Validation Accuracy | Validation Macro F1 | Quarantined Challenge Accuracy | Quarantined Challenge Macro F1 | Generalization Gap ($\Delta\text{F1}$) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Classical ML** (32 Features) | Multi-Layer Perceptron (MLP) | 93.26% | 92.60% | 90.62% | 90.92% | -1.68% |
| **Raw Waveform DL** (20 kHz 3-Phase) | Temporal ConvNet (TCN) | 93.75% | 93.70% | 90.92% | 90.83% | -2.87% |
| **Hybrid Representation** | **`HybridPQNet`** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **0.00%** |

- **Representation Complementarity:** `HybridPQNet` achieved a **+11.08% F1 gain over features alone** and a **+9.13% gain over waveform alone**.
- **Three-Phase Synchrony:** Single-phase processing collapsed performance from **90.16% F1 to 3.91% F1 (-86.25% collapse)**, proving that concurrent cross-phase differential reference is vital.
- **Sub-Cycle Resolution:** 20 kHz sampling resolved 8 discrete samples per 400 $\mu$s notch, allowing deep learning models to classify 100% of notch windows without ambiguity.

---

## 6. Run Tests and Reproduce Results

### Automated Regression Test Suite
The complete test suite contains **360 collected tests**, all passing except 2 conditionally skipped GPU checks:

```bash
# Run the full regression test suite (excluding slow synthesis tests)
pytest tests/ -v -m "not slow"
```

**Verified Test Result:**
```
================= 358 passed, 2 skipped, 2 warnings in 11.61s ==================
```

### Breakdown of Test Suites
- **Gate 3D–3X (Physical Disturbance Acceptance):** 180 tests across all 8 disturbance classes.
- **DSP Engine, SNR Invariants & Pipeline:** 120 tests verifying numerical parity (< 0.000050) and phase-angle invariance.
- **Model Checksums, Invariants & Anti-Leakage:** 43 tests verifying frozen artifact hashes and partition isolation.
- **Phase 5 Interactive Dashboard Backend:** 6 tests verifying manifest loading, dual-rate slicing, and result aggregation.
- **Phase 5C Multi-Model Research Pipeline:** 9 tests verifying dual-rate array shapes, zero operating-condition leakage, and model inference.

---

## 7. Research Status & Future Scope

### Multi-Phase Lifecycle Status

```
  [PHASE 1: ELECTRICAL FOUNDATION] ----------------------> COMPLETE (Gate 3A)
  [PHASE 2: 60-HZ DSP & INTEGRATION BRIDGE] --------------> COMPLETE (Gates 3B, 3C)
  [PHASE 3: PHYSICAL 8-CLASS DATASET & QUALITY AUDITS] --> COMPLETE (Gates 3D - 3X)
  [PHASE 4: PROPER 60-HZ MACHINE LEARNING TRAINING] -----> COMPLETE (Gates 4A - 4D)
  [PHASE 5: MULTI-MODEL COMPARATIVE RESEARCH & DEMO] ----> COMPLETE (Phases 5A - 5G)
  [PHASE 6: EMBEDDED ESP32 HIL EXTENSION] ---------------> FUTURE SCOPE — NOT IMPLEMENTED
```

### Phase 6: Planned / Future Scope — Not Yet Implemented
Phase 6 represents future research extensions that have **not been implemented or authorized**. The active production and research scope of this repository is complete through Phase 5.
- **1. Embedded Edge Inference:** Flash optimized C++ weights or TFLite Micro flatbuffers to microcontroller targets (e.g., ESP32-WROOM-32) and benchmark execution latency.
- **2. Safe Isolated Electrical Front-End:** Design and build galvanic isolation (optocouplers, Zener clamping, fast-blow fusing, and relay disconnection) between high-voltage transducers and ADC inputs.
- **3. Real-Time Hardware-in-the-Loop (HIL):** Couple real-time simulator DAC output channels directly to external hardware ADC pins.
- **4. Physical Hardware Validation:** Benchmark classification reliability, clock drift, thermal stability, and memory footprint on physical embedded devices.

---

## 8. Comprehensive Documentation Index

All project-authored Markdown documents are indexed below by category:

### A. Demonstration Guides & Audit Reports
- [MATLAB Voltage Sag & Swell Waveform Visualization Guide](docs/guides/MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md) — Copy-paste MATLAB tutorial for inspecting and visualizing existing Sag and Swell simulation recordings.
- [Repository-Wide Markdown Documentation Audit Report](docs/audits/MARKDOWN_DOCUMENTATION_AUDIT.md) — Complete audit of all 104 tracked Markdown documents.
- [Docs Directory Navigation Index](docs/README.md) — Technical documentation directory overview.
- [Project Changelog](CHANGELOG.md) — Chronological engineering log and historical phase milestones.
- [Artifact Integrity Reconciliation Audit](docs/ARTIFACT_INTEGRITY_RECONCILIATION.md) — Checksum reconciliation and parity audit.
- [Repository Legacy Component Audit](docs/REPOSITORY_LEGACY_AUDIT.md) — Systematic component classification and archival registry.
- [Repository Component Readiness Audit](docs/REPOSITORY_COMPONENT_AUDIT.md) — Comprehensive subsystem classification and inventory.
- [Repository Deep Clean Report](docs/REPOSITORY_DEEP_CLEAN_REPORT.md) — Structural reorganization and file cleanup record.
- [Repository Modernization Report](docs/REPOSITORY_MODERNIZATION_REPORT.md) — Transition from exploratory prototypes to authoritative 60-Hz architecture.

### B. Master Scientific Research Reports (Phase 5)
- [Phase 5 Master Research Report](docs/PHASE5_FINAL_RESEARCH_REPORT.md) — Comprehensive comparative research monograph.
- [Phase 5A: Feature Analysis & Multi-Model Research Design](docs/PHASE5A_FEATURE_ANALYSIS_AND_COMPARISON_PLAN.md) — Initial feature audit and design.
- [Phase 5B: Simulation Matrix & Bounded Pilot Report](docs/PHASE5B_SIMULATION_MATRIX_AND_PILOT_REPORT.md) — Pilot matrix and preliminary validation.
- [Phase 5B.1: Pre-Bulk Physical Validation & Sampling Audit](docs/PHASE5B1_PREBULK_ENGINEERING_AUDIT.md) — Physical audit of noise, ADC, and solver timesteps.
- [Phase 5B.2: Simulation Pipeline Remediation Report](docs/PHASE5B2_SIMULATION_PIPELINE_REMEDIATION_REPORT.md) — Pipeline fixes for fixed-reference noise and dual-rate logging.
- [Phase 5C: Expanded Dataset Freeze Audit](docs/PHASE5C_EXPANDED_DATASET_FREEZE_AUDIT.md) — Verification of 144 trajectories, 4,608 frames, and zero leakage.
- [Phase 5D: Classical ML Benchmark & Feature Analysis](docs/PHASE5D_CLASSICAL_ML_AND_FEATURE_ANALYSIS.md) — Benchmark of 6 classifiers, feature importance, and 5 group ablations.
- [Phase 5E: Waveform Deep Learning (1D-CNN & TCN)](docs/PHASE5E_WAVEFORM_DEEP_LEARNING.md) — Raw waveform models, temporal occlusion, and 3-phase synchrony.
- [Phase 5F: Hybrid Model Analysis](docs/PHASE5F_HYBRID_MODEL_ANALYSIS.md) — Multi-modal representation fusion and synergy analysis.
- [Phase 5G: Final Comparative & Challenge Evaluation](docs/PHASE5G_FINAL_COMPARATIVE_EVALUATION.md) — One-time evaluation on quarantined Conditions 33–36.

### C. System Architecture, Specifications & Roadmaps
- [Master Project Status](docs/PROJECT_STATUS.md) — Authoritative single-point human-readable project status.
- [Multi-Phase Roadmap](docs/ROADMAP.md) — Chronological phase lifecycle from Phase 1 through Phase 6.
- [System Architecture](docs/ARCHITECTURE.md) — Seven-subsystem technical specification.
- [Authoritative Source of Truth](docs/SOURCE_OF_TRUTH.md) — Cryptographic checksums and authoritative contract definitions.
- [Standards Traceability Index](docs/STANDARDS_TRACEABILITY_INDEX.md) — Traceability across IEEE 1159, IEEE 519, IEEE 1453, and IEC 61000-4-30.
- [Dataset Specification](docs/DATASET.md) — Comprehensive physical dataset documentation.
- [Acquisition Requirements](docs/ACQUISITION_REQUIREMENTS.md) & [Acquisition Format](docs/ACQUISITION_FORMAT.md) — Signal logging and sampling parameters.
- [Gate Index (Gates 1–4D)](docs/GATE_INDEX.md) — Verification criteria for historical project gates.
- [Final Repository Structure](docs/FINAL_REPOSITORY_STRUCTURE.md) — File layout and ownership mapping.

### D. Reproduction & Operational Guides
- [Project Quickstart & Execution Guide](RUNTHISPROJECT.md) — Developer quickstart and verified workflows.
- [Reproducing Phase 4 on a Clean Clone](docs/REPRODUCING_PHASE4.md) — Reproduction recipes for historical 60-Hz ML models.
- [Full Reproducibility Guide](docs/REPRODUCIBILITY.md) — Environment setup, dependency matrices, and test instructions.
- [Live MVP Plan](docs/LIVE_MVP_PLAN.md) — Interactive live demonstration architecture.
- [Live Operation Manual](docs/LIVE_OPERATION.md) — Real-time telemetry server operations.
- [Simulink Integration Guide](docs/SIMULINK_INTEGRATION.md) & [Integration Plan](docs/SIMULINK_INTEGRATION_PLAN.md) — MATLAB bridge architecture.
- [Simulink ML Model Contract](docs/SIMULINK_ML_MODEL_CONTRACT.md) — Interface contract between Simulink and Python DSP.
- [Simulink-Python Feature Validation](docs/SIMULINK_PYTHON_FEATURE_VALIDATION.md) — Feature parity audit between MATLAB and Python.

### E. Historical Engineering Gate Reports (Phases 1–4)
- **Normal Operation:** [Gate 3B Report](docs/GATE3B_NORMAL_DATASET_AUDIT.md) | [Gate 3B.1 Quality Audit](docs/GATE3B1_NORMAL_DATASET_QUALITY_AUDIT.md) | [Gate 3B Spec](docs/GATE3B_NORMAL_DATASET_SPEC.md) | [SNR Propagation](docs/GATE3B1_SNR_DATASET_PROPAGATION.md) | [Gate 3B.1 Traceability](docs/GATE3B1_STANDARDS_TRACEABILITY.md)
- **Disturbance Specification:** [Gate 3C Spec](docs/GATE3C_DISTURBANCE_SPECIFICATION.md) | [Gate 3C Traceability](docs/GATE3C_STANDARDS_TRACEABILITY.md) | [Gate 3C Plan](docs/GATE3C_VALIDATION_PLAN.md)
- **Voltage Sag:** [Gate 3D Implementation](docs/GATE3D_SAG_IMPLEMENTATION.md) | [Gate 3E Report](docs/GATE3E_SAG_DATASET_REPORT.md) | [Gate 3F Audit](docs/GATE3F_SAG_DATASET_AUDIT.md)
- **Voltage Swell:** [Gate 3G Implementation](docs/GATE3G_SWELL_IMPLEMENTATION.md) | [Gate 3H Report](docs/GATE3H_SWELL_DATASET_REPORT.md) | [Gate 3I Audit](docs/GATE3I_SWELL_DATASET_AUDIT.md)
- **Voltage Interruption:** [Gate 3J Implementation](docs/GATE3J_INTERRUPTION_IMPLEMENTATION.md) | [Gate 3K Report](docs/GATE3K_INTERRUPTION_DATASET_REPORT.md) | [Gate 3L Audit](docs/GATE3L_INTERRUPTION_DATASET_AUDIT.md)
- **Harmonics:** [Gate 3M Implementation](docs/GATE3M_HARMONICS_IMPLEMENTATION.md) | [Gate 3N Report](docs/GATE3N_HARMONICS_DATASET_REPORT.md) | [Gate 3O Audit](docs/GATE3O_HARMONICS_DATASET_AUDIT.md)
- **Voltage Flicker:** [Gate 3P Implementation](docs/GATE3P_FLICKER_IMPLEMENTATION.md) | [Gate 3Q Report](docs/GATE3Q_FLICKER_DATASET_REPORT.md) | [Gate 3R Audit](docs/GATE3R_FLICKER_DATASET_AUDIT.md)
- **Voltage Notch:** [Gate 3S Implementation](docs/GATE3S_NOTCH_IMPLEMENTATION.md) | [Gate 3T Report](docs/GATE3T_NOTCH_DATASET_REPORT.md) | [Gate 3U Audit](docs/GATE3U_NOTCH_DATASET_AUDIT.md)
- **Oscillatory Transient:** [Gate 3V Implementation](docs/GATE3V_TRANSIENT_IMPLEMENTATION.md) | [Gate 3W Report](docs/GATE3W_TRANSIENT_DATASET_REPORT.md) | [Gate 3X Audit](docs/GATE3X_TRANSIENT_DATASET_AUDIT.md)
- **Phase 4 ML Gates:** [Gate 4A Dataset Freeze](docs/GATE4A_FINAL_DATASET_FREEZE_AUDIT.md) | [Gate 4B Baseline Models](docs/GATE4B_BASELINE_MODEL_COMPARISON.md) | [Gate 4C MLP Tuning](docs/GATE4C_MLP_TUNING_AUDIT.md) | [Gate 4D Locked Test](docs/GATE4D_LOCKED_TEST_EVALUATION.md)
- **Historical Audits:** [60-Hz Compatibility Audit](docs/GATE2_60HZ_COMPATIBILITY_AUDIT.md) | [Gate 3 Training Audit](docs/GATE3_DATASET_TRAINING_AUDIT.md) | [IEEE 9-Bus Model Audit](docs/IEEE9BUS_MODEL_AUDIT.md) | [IEEE Alignment Audit](docs/IEEE_ALIGNMENT_AUDIT.md) | [Waveform Standard Audit](docs/WAVEFORM_STANDARD_AUDIT.md) | [Data Leakage Audit](docs/DATA_LEAKAGE_AUDIT.md) | [Dataset Generation Audit](docs/DATASET_GENERATION_AUDIT.md) | [Dataset Specification](docs/DATASET_SPECIFICATION.md) | [Dataset Audit](docs/DATASET_AUDIT.md) | [Integration Audit](docs/INTEGRATION.md) | [Integration Regression Report](docs/INTEGRATION_REGRESSION_REPORT.md) | [ML Readiness Audit](docs/ML_READINESS.md) | [Audit Status Matrix](docs/AUDIT_STATUS.md) | [Project Audit Record](docs/PROJECT_AUDIT.md) | [Project State Baseline](docs/PROJECT_STATE.md)

### F. Historical Inception & Future Extension Scaffolding
- [Academic Project Execution Plan (Historical)](doc/PQD_Project_Execution_Plan.md) & [Early System Design](doc/system_design.md).
- [Academic Paper Draft](docs/paper_draft.md).
- [Hardware Evaluation (Phase 6 Scaffolding)](docs/HARDWARE_EVALUATION.md) & [Hardware Integration](docs/HARDWARE_INTEGRATION.md).
- [Real Hardware Validation Protocol (Phase 6)](docs/REAL_HARDWARE_VALIDATION.md) & [Latency Benchmarks](docs/LATENCY_BENCHMARK.md).
- [Hardware Safety Checklist](hardware/safety_checklist.md).
- [ESP32 Embedded HIL Guide (Phase 6 Scaffolding)](future/esp32-hil/README.md) & [Future Extensions Index](future/README.md).
- [Subsystem READMEs: DSP](dsp/README.md) | [ML](ml/README.md) | [Scenarios](scenarios/README.md) | [Scripts](scripts/README.md) | [Tests](tests/README.md) | [Integration](integration/matlab/README.md) | [Mobile App (Future)](mobile_app/README_MOBILE.md) | [Baseline Experiments](experiments/baseline/README.md) | [Classical Experiments](experiments/classical_benchmark/README.md).

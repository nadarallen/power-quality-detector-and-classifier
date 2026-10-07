# Changelog

All notable changes to the Power Quality Disturbance (PQD) Detection and Classification System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Phase 3 Complete] — 2026-10-07

### Added
- **Normal Baseline Dataset (Gates 3B & 3B.1)**:
  - 1,152 unique frames generated across 32 WSCC 9-bus operating conditions at Bus 5 ($230\,\text{kV}$ PCC).
  - Phase-aware orthogonal projection SNR formula applied, eliminating angle-dependent residual error.
- **Voltage Sag Implementation, Dataset & Audit (Gates 3D, 3E, 3F)**:
  - Bus 5 transmission shunt fault switching (`PQD_Fault_Sag`) across three-phase, phase-to-phase, and single-phase-to-ground configurations.
  - 1,152 unique frames synthesized from 36 continuous simulation trajectories ($R_f \in [0.1, 15.0]\,\Omega$).
  - Full 16-domain independent audit passed; anti-interruption separation confirmed (residual $\ge 0.10\,\text{pu}$).
- **Voltage Swell Implementation, Dataset & Audit (Gates 3G, 3H, 3I)**:
  - Shunt capacitor bank energization (`PQD_Breaker_Swell`) injecting $50\text{--}150\,\text{MVAR}$ reactive power at Bus 5.
  - 1,152 unique frames synthesized ($1.10\text{--}1.80\,\text{pu}$ magnitude, $16.7\text{--}120\,\text{ms}$ duration).
  - Full 16-domain audit passed; steady baseline recovery verified within 1 cycle.
- **Voltage Interruption Implementation, Dataset & Audit (Gates 3J, 3K, 3L)**:
  - Series line circuit breaker on Line 4-5 + local feeder isolation breaker (`PQD_Breaker_Interruption`).
  - 1,152 unique frames synthesized with residual voltage strictly $< 0.10\,\text{pu}$ (mean $0.0076\,\text{pu}$).
  - Full 16-domain audit passed; zero sag overlap guaranteed.
- **Harmonics Implementation, Dataset & Audit (Gates 3M, 3N, 3O)**:
  - Controlled non-linear current source injection at Bus 5 (`PQD_Harm_Inj`) across orders $H_2, H_3, H_5, H_7, H_9, H_{11}$.
  - 1,152 unique frames synthesized with Total Harmonic Distortion (THD) between $5.12\%$ and $19.84\%$.
  - Full 16-domain audit passed; IEEE Std 519-2022 compliance and anti-sag/swell preservation verified.
- **Voltage Flicker Implementation, Dataset & Audit (Gates 3P, 3Q, 3R)**:
  - Sub-synchronous dynamic load modulation at Bus 5 (`PQD_Flicker_Mod`) across modulation frequencies $f_m \in [1.0, 25.0]\,\text{Hz}$.
  - 1,152 unique frames synthesized with modulation depths $1.0\%\text{--}10.0\%$.
  - Full 16-domain audit passed; symmetric sideband structure ($60 \pm f_m\,\text{Hz}$) verified per IEEE Std 1453-2022.
- **Voltage Notch Implementation, Dataset & Audit (Gates 3S, 3T, 3U)**:
  - Controlled line-to-line thyristor commutation switching on Bus 5 (`PQD_Notch_Bus5`) with finite commutation resistance ($R_{comm} \in [10, 100]\,\Omega$).
  - 1,152 unique frames synthesized with notch depths $22.9\%\text{--}53.8\%$ and notch widths $0.43\text{--}2.97\,\text{ms}$.
  - Full 16-domain audit passed; Shannon-Nyquist discrete sampling adequacy ($2.2\text{--}14.8$ samples/notch) confirmed at $5\,\text{kHz}$.
- **Oscillatory Transient Implementation, Dataset & Audit (Gates 3V, 3W, 3X)**:
  - Three-phase breaker switched into grounded series RLC branch (`PQD_Breaker_Transient` + `PQD_RLC_Transient`) on Bus 5.
  - 1,152 unique frames synthesized with natural oscillation ringing at $250.2\text{--}299.1\,\text{Hz}$ and peak excursion $0.13\text{--}0.41\,\text{pu}$.
  - Full 16-domain audit passed; IEEE Std 1159-2019 Table 2 low-frequency oscillatory compliance verified with $16.7\text{--}20.0$ samples per oscillation period.
- **Testing & Verification Suite**:
  - Expanded automated test suite to 300 passing tests covering all 8 disturbance classes, physical validation gates, and DSP feature extraction.
- **Master Documentation Infrastructure**:
  - Created `docs/GATE_INDEX.md` (authoritative registry of Gates 1 through 3X).
  - Created `docs/PROJECT_STATUS.md` (master project status and readiness document).
  - Created `docs/ROADMAP.md` (lifecycle roadmap for Phases 1 through 6).
  - Created `docs/DATASET.md` (comprehensive profiles for all 8 datasets).
  - Created `docs/STANDARDS_TRACEABILITY_INDEX.md` (standards cross-reference & 5-tier provenance taxonomy).
  - Created `docs/ML_READINESS.md` (Phase 4 10-step training protocol and success criteria).
  - Created `docs/REPRODUCIBILITY.md` (computational setup, checksum verification, and test execution).

### Changed
- **Working Disturbance Model**:
  - Updated [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) to incorporate all 7 disturbance mechanisms with strict mutual dormancy logic.
- **Scenario Schema**:
  - Enhanced [`docs/GATE3C_SCENARIO_SCHEMA.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_SCENARIO_SCHEMA.json) to support `CIRCUIT_BREAKER` and 5-letter class prefixes.
- **Physical Disturbance Validator**:
  - Updated [`pipeline/disturbance_validator.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/pipeline/disturbance_validator.py) with dedicated physical validators (`validate_sag_frame`, `validate_swell_frame`, `validate_interruption_frame`, `validate_harmonics_frame`, `validate_flicker_frame`, `validate_notch_frame`, and `validate_transient_frame`).
- **Root README**:
  - Completely updated `README.md` to reflect 60-Hz WSCC 9-bus Simscape foundation, 300 passing tests, and Phase 3 completion.

### Maintained & Frozen
- **Pristine Reference Model**:
  - [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) remains byte-for-byte identical (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`).
- **32-Feature DSP Contract**:
  - Feature ordering and extraction signatures in [`dsp/enhanced_features.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/dsp/enhanced_features.py) strictly preserved.
- **Machine Learning Weights**:
  - [`ml/models/model_weights_32.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/ml/models/model_weights_32.json) remains frozen; ML retraining deliberately quarantined to Phase 4.

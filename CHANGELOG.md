# Changelog

All notable changes to the Power Quality Disturbance (PQD) Detection and Classification System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Phase 3 Complete — Repository Modernization] — 2026-10-07

### Modernized & Standardized
- **Master Documentation Architecture**:
  - Established [docs/SOURCE_OF_TRUTH.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/SOURCE_OF_TRUTH.md) defining the single authoritative registry for all simulation models, datasets, DSP contracts, and pipeline components.
  - Created [docs/LIVE_MVP_PLAN.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/LIVE_MVP_PLAN.md) detailing the future Phase 5 live demonstration MVP architecture (Simulink disturbance rack, MATLAB programmatic trigger API, streaming telemetry).
  - Created [docs/README.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/README.md) as the central documentation navigation hub.
  - Created [docs/REPOSITORY_LEGACY_AUDIT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REPOSITORY_LEGACY_AUDIT.md) providing a comprehensive component classification and legacy audit matrix.
  - Rewrote root [README.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/README.md) and [RUNTHISPROJECT.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/RUNTHISPROJECT.md) to eliminate obsolete 50-Hz / 8-feature / ESP32-first claims and present the 60-Hz WSCC 9-bus architecture.
- **Legacy & Future Subsystem Reclassification**:
  - Reclassified ESP32 C++ firmware (`firmware/`) and hardware schematics (`hardware/`) as **Phase 6 Optional Embedded HIL Extension**.
  - Reclassified Firebase real-time service (`firebase/`) and mobile app (`mobile_app/`) as optional cloud/mobile telemetry clients.
  - Tagged historical proposals and preliminary benchmark reports with clear archival context banners.
  - Removed dead unreferenced autosave artifact `IEEE_9bus/IEEE_9bus_new_o.slx.autosave`.
- **Systematic Git Checkpointing**:
  - Created safety checkpoint tag `pre-docs-phase3-checkpoint` at starting commit `e3d41d5`.
  - Created formal release tag `phase-3-pqd-dataset-complete` at commit `86b4ba2`.
  - Created safety checkpoint tag `before-repository-modernization` at commit `53bdc41`.

---

## [Phase 3 Complete — Eight-Class Dataset Generation] — 2026-10-07

### Added
- **Normal Baseline Dataset (Gates 3B & 3B.1)**:
  - 1,152 unique frames generated across 32 WSCC 9-bus operating conditions at Bus 5 ($230\text{ kV}$ PCC).
  - Phase-aware orthogonal projection SNR formula applied, eliminating angle-dependent residual error.
- **Voltage Sag Implementation, Dataset & Audit (Gates 3D, 3E, 3F)**:
  - Bus 5 transmission shunt fault switching (`PQD_Fault_Sag`) across three-phase, phase-to-phase, and single-phase-to-ground configurations.
  - 1,152 unique frames synthesized from 36 continuous simulation trajectories ($R_f \in [0.1, 15.0]\ \Omega$).
  - Full 16-domain independent audit passed; anti-interruption separation confirmed (residual $\ge 0.10\text{ pu}$).
- **Voltage Swell Implementation, Dataset & Audit (Gates 3G, 3H, 3I)**:
  - Shunt capacitor bank energization (`PQD_Breaker_Swell`) injecting $50\text{--}150\text{ MVAR}$ reactive power at Bus 5.
  - 1,152 unique frames synthesized ($1.10\text{--}1.80\text{ pu}$ magnitude, $16.7\text{--}120\text{ ms}$ duration).
  - Full 16-domain audit passed; steady baseline recovery verified within 1 cycle.
- **Voltage Interruption Implementation, Dataset & Audit (Gates 3J, 3K, 3L)**:
  - Series line circuit breaker on Line 4-5 + local feeder isolation breaker (`PQD_Breaker_Interruption`).
  - 1,152 unique frames synthesized with residual voltage strictly $< 0.10\text{ pu}$ (mean $0.0076\text{ pu}$).
  - Full 16-domain audit passed; zero sag overlap guaranteed.
- **Harmonics Implementation, Dataset & Audit (Gates 3M, 3N, 3O)**:
  - Controlled non-linear current source injection at Bus 5 (`PQD_Harm_Inj`) across orders $H_2, H_3, H_5, H_7, H_9, H_{11}$.
  - 1,152 unique frames synthesized with Total Harmonic Distortion (THD) between $5.12\%$ and $19.84\%$.
  - Full 16-domain audit passed; IEEE Std 519-2022 compliance and anti-sag/swell preservation verified.
- **Voltage Flicker Implementation, Dataset & Audit (Gates 3P, 3Q, 3R)**:
  - Sub-synchronous dynamic load modulation at Bus 5 (`PQD_Flicker_Mod`) across modulation frequencies $f_m \in [1.0, 25.0]\text{ Hz}$.
  - 1,152 unique frames synthesized with modulation depths $1.0\%\text{--}10.0\%$.
  - Full 16-domain audit passed; symmetric sideband structure ($60 \pm f_m\text{ Hz}$) verified per IEEE Std 1453-2022.
- **Voltage Notch Implementation, Dataset & Audit (Gates 3S, 3T, 3U)**:
  - Controlled line-to-line thyristor commutation switching on Bus 5 (`PQD_Notch_Bus5`) with finite commutation resistance ($R_{comm} \in [10, 100]\ \Omega$).
  - 1,152 unique frames synthesized with notch depths $22.9\%\text{--}53.8\%$ and notch widths $0.43\text{--}2.97\text{ ms}$.
  - Full 16-domain audit passed; Shannon-Nyquist discrete sampling adequacy ($2.2\text{--}14.8$ samples/notch) confirmed at $5\text{ kHz}$.
- **Oscillatory Transient Implementation, Dataset & Audit (Gates 3V, 3W, 3X)**:
  - Three-phase breaker switched into grounded series RLC branch (`PQD_Breaker_Transient` + `PQD_RLC_Transient`) on Bus 5.
  - 1,152 unique frames synthesized with natural oscillation ringing at $250.2\text{--}299.1\text{ Hz}$ and peak excursion $0.13\text{--}0.41\text{ pu}$.
  - Full 16-domain audit passed; discrete sampling adequacy ($16.7\text{--}20.0$ samples/cycle) confirmed at $5\text{ kHz}$.

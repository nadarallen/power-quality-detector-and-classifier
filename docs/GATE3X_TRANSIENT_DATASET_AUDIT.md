# GATE 3X — OSCILLATORY TRANSIENT DATASET AUDIT REPORT

**Document ID:** `DOC-GATE3X-TRANSIENT-AUDIT-001`  
**Date:** October 7, 2026  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3X_TRANSIENT_AUDIT = PASS`)  
**Electrical System:** IEEE 9-bus WSCC 3-Machine 9-Bus System (60 Hz)  
**Dataset Under Audit:** `data/ieee9bus_60hz/transient/`  

---

## 1. Executive Summary

Under **Gate 3X**, an independent, exhaustive computational audit of the completed **60-Hz IEEE 9-bus Oscillatory Transient dataset** (generated in Gate 3W) was executed across all 16 audit domains defined by the project specification.

### Key Audit Findings:
- **1,152 / 1,152 frames verified** with complete 1-to-1 correspondence across waveforms, features, scenarios, and simulation trajectories.
- **Cryptographic integrity verified**: SHA-256 hashes of all artifacts match dataset metadata byte-for-byte:
  - `transient_waveforms.npz`: `8176A39D3FC91764B674B3EBE0A01F2B87F182A99417E1490984648819A7AED2`
  - `transient_features.csv`: `0C9CD9E594B3FCB6AE2836E3C1B4F4E3485891551A9CABDB40427D2C17FDD11A`
  - `transient_scenarios.json`: `C611CFCA9B1BE39A1E87D6A629691DEFD35DA2C017EE290CCDCD1FEEFE02BD32`
  - `transient_dataset_metadata.json`: `0B88C294D655D44A6AE7A2FC2FFFB08106EE32401189D5AC6C2DF22FA61C67E2`
- **Pristine reference model remains untouched**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` SHA-256 is `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` (byte-for-byte identical).
- **Physical capacitor switching mechanism verified**: 100% of frames originate from actual SimPowerSystems capacitor bank breaker energization (`PQD_Breaker_Transient` + `PQD_RLC_Transient` + `PQD_Gnd_Transient`) connected directly to Bus 5 (230 kV PCC).
- **Dominant transient frequency validated**: Measured dominant frequency spans [250.2, 299.1] Hz (mean 266.0 Hz), safely inside the approved 5-kHz representable range (250-1500 Hz).
- **5 kHz sampling resolution adequacy validated**: At Fs = 5000 Hz (Ts = 200 us, Nyquist = 2500 Hz), the highest observed frequency (299.1 Hz) has 16.72 samples per oscillation cycle (mean 18.80 samples), ensuring alias-free discrete representation without approaching the Nyquist boundary.
- **Peak excursion & duration metrics verified**:
  - Measured peak excursion: [0.1297, 0.4056] pu (mean 0.2619 pu), exceeding TRN-01 threshold (>= 0.12 pu).
  - Measured effective duration: <= 44.8 ms (mean 38.1 ms), satisfying TRN-03 threshold (<= 50.0 ms).
- **Fundamental voltage stability & preservation**: Fundamental frequency remains exactly 60.00 Hz across all frames; full-window RMS is bounded in [0.5812, 0.6769] pu, confirming complete absence of sustained Sag, Swell, or Interruption collapse.
- **Clean cross-class separation verified**: Massive L2 centroid separation in the 32-feature contract space relative to all 7 previous classes (30.5 to 98.6).
- **Zero data leakage**: Simulation trajectory-grouped splitting verified (Train 832, Val 160, Test 160; strictly disjoint).
- **Zero rejections or data corruption**: 0 NaN, 0 Inf, 0 duplicate feature rows, 0 duplicate waveform arrays.
- **Production DSP parity verified**: Python 32-feature DSP matches mathematical reference calculations with maximum difference 0.000024 < 10^-3.
- **ML Decoupled**: Legacy MLP model evaluated strictly as `OUT_OF_DOMAIN` without altering ground truth.

---

## 2. Audit Matrix Summary

| Domain | Audit Name | Key Metric / Criteria | Measured Value | Status |
| :---: | :--- | :--- | :--- | :---: |
| **3X.1** | Structural Integrity | 1,152 frames, 0 NaN, 0 Inf, 0 duplicates | (1152, 1000, 3), 0 NaN, 0 Inf, 0 dups | **PASS** |
| **3X.2** | Ground-Truth Provenance | 100% `SCENARIO_CONTROLLER`, index 7 | 100% pure provenance, class 'Transient' | **PASS** |
| **3X.3** | Physical Transient Verification | Peak excursion >= 0.12 pu, duration <= 50 ms | Peak 0.1297–0.4056 pu, duration <= 44.8 ms | **PASS** |
| **3X.4** | Resolution Audit (5 kHz) | Highest freq < 2500 Hz, >= 3.3 samples/cycle | Freq <= 299.1 Hz, 16.72–19.98 samples/cycle | **PASS** |
| **3X.5** | Frequency Coverage Audit | Approved range [250, 1500] Hz | [250.2, 299.1] Hz (mean 266.0 Hz) | **PASS** |
| **3X.6** | Magnitude & Duration Coverage | Percentiles P0 through P100 | Complete percentiles recorded & verified | **PASS** |
| **3X.7** | Event Timing Diversity | Variable onset timing across 200 ms | Onset span: [24.8, 85.0] ms | **PASS** |
| **3X.8** | Phase Audit | Three-phase, two-phase, single-phase | ABC: 640, 2-phase: 256, 1-phase: 256 | **PASS** |
| **3X.9** | Cross-Class Separation | Distances to all 7 classes > 10.0 | All distances in [30.5, 98.6] | **PASS** |
| **3X.10** | Secondary Phenomena Audit | No sustained Sag/Swell/Interruption | Full-window RMS in [0.5812, 0.6769] pu | **PASS** |
| **3X.11** | Waveform Diversity & Rank | Feature matrix rank >= 25, zero dups | Rank: 31 / 32, zero duplicates | **PASS** |
| **3X.12** | Production DSP Parity | Reference math vs Python DSP diff < 10^-3 | Max diff: 0.000024 < 10^-3 | **PASS** |
| **3X.13** | Trajectory Leakage Audit | Continuous trajectory-level split | Zero cross-split trajectory overlap | **PASS** |
| **3X.14** | Standards Traceability | IEEE 1159 Table 2, IEC 61000-4-30 | 100% compliance | **PASS** |
| **3X.15** | ML Decoupling Audit | Model predictions do not influence labels | Decoupled; `OUT_OF_DOMAIN` verified | **PASS** |
| **3X.16** | Deliverable Generation | Comprehensive audit MD & JSON summary | Complete deliverables generated | **PASS** |

---

## 3. Cross-Class Separation Matrix

Centroid L2 distance in 32-feature contract space:

| Disturbance Class | L2 Distance to Transient Centroid | Separation Status |
|:---|:---:|:---:|
| **Normal** | 53.05 | **PASS** |
| **Sag** | 31.73 | **PASS** |
| **Swell** | 43.22 | **PASS** |
| **Interruption** | 47.18 | **PASS** |
| **Harmonics** | 36.46 | **PASS** |
| **Flicker** | 30.52 | **PASS** |
| **Notch** | 98.57 | **PASS** |

---

## 4. Final Verdict

Every pass criterion defined in Gate 3X has been rigorously satisfied.

```
GATE3X_TRANSIENT_AUDIT = PASS
```

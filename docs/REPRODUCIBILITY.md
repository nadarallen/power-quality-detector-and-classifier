# Reproducibility Guide & Verification Protocols

**Document Reference**: `docs/REPRODUCIBILITY.md`  
**Date**: October 7, 2026  
**Status**: ACTIVE / MANDATORY PROTOCOL  

---

## 1. Computational Environment Requirements

### 1.1 MATLAB & Simulink Environment
- **Version**: MATLAB R2024b or R2025a (64-bit Windows / Linux).
- **Required Toolboxes**:
  - Simulink
  - Simscape
  - Simscape Electrical (Specialized Power Systems library)
  - Signal Processing Toolbox
- **Simulation Solver Configuration**:
  - Solver: `ode23tb` (stiff trapezoidal / TR-BDF2)
  - Relative Tolerance (`RelTol`): $1 \times 10^{-4}$
  - Maximum Step Size (`MaxStep`): $1 \times 10^{-4}\,\text{s}$ ($100\,\mu\text{s}$)
  - Stop Function (`StopFcn`): `''` (disabled during batch runs)

### 1.2 Python Environment
- **Python Version**: Python 3.10, 3.11, 3.12, 3.13, or 3.14 (tested on 3.12 and 3.14.2).
- **Core Dependencies**:
  ```text
  numpy>=1.24.0
  scipy>=1.10.0
  pandas>=2.0.0
  pytest>=7.4.0
  ```
- **Optional Server Dependencies**:
  - Python standard library (`http.server`, `urllib`, `sqlite3`, `hashlib`, `json`, `dataclasses`).

---

## 2. Integrity Verification: Pristine Reference Model

The reference simulation model must remain byte-for-byte identical to baseline. Verify its integrity using Python:

```bash
python -c "import hashlib; h = hashlib.sha256(open('IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx', 'rb').read()).hexdigest().upper(); print('SHA-256:', h); assert h == '5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D', 'INTEGRITY VIOLATION!'"
```

Expected output:
```text
SHA-256: 5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D
```

---

## 3. How to Run the Automated Test Suite

### 3.1 Run Complete Project Regression Suite
To execute all 300 automated unit, physical validation, and regression tests:

```bash
pytest -v
```

Expected result:
```text
================= 300 passed, 2 skipped, 2 warnings in ~8s ==================
```

### 3.2 Run Targeted Disturbance Class Test Suites
- **Voltage Sag**: `pytest tests/test_gate3d_sag.py tests/test_gate3e_sag_dataset.py tests/test_gate3f_sag_audit.py -v`
- **Voltage Swell**: `pytest tests/test_gate3g_swell.py tests/test_gate3h_swell_dataset.py tests/test_gate3i_swell_audit.py -v`
- **Voltage Interruption**: `pytest tests/test_gate3j_interruption.py tests/test_gate3k_interruption_dataset.py tests/test_gate3l_interruption_audit.py -v`
- **Harmonics**: `pytest tests/test_gate3m_harmonics.py tests/test_gate3n_harmonics_dataset.py tests/test_gate3o_harmonics_audit.py -v`
- **Voltage Flicker**: `pytest tests/test_gate3p_flicker.py tests/test_gate3q_flicker_dataset.py tests/test_gate3r_flicker_audit.py -v`
- **Voltage Notch**: `pytest tests/test_gate3s_notch.py tests/test_gate3t_notch_dataset.py tests/test_gate3u_notch_audit.py -v`
- **Oscillatory Transient**: `pytest tests/test_gate3v_transient.py tests/test_gate3w_transient_dataset.py tests/test_gate3x_transient_audit.py -v`

---

## 4. How to Regenerate Disturbance Datasets

Every disturbance class dataset is regenerated in two reproducible stages:
1. **Physical Simulation (Simulink Batch)**: Generates 36 trajectories saved to `raw_<class>_simulations.mat`.
2. **Feature Extraction & Validation (Python DSP)**: Extracts 1,152 frames, computes the 32-feature contract, evaluates physical validation gates, and exports CSV/JSON files.

### 4.1 Commands by Disturbance Class
| Disturbance Class | Step 1: MATLAB Batch Simulation | Step 2: Python Processing & Validation | Step 3: Independent Audit Script |
|:---|:---|:---|:---|
| **Voltage Sag** | `matlab -batch "run('scripts/generate_ieee9bus_sag_dataset.m')"` | `python scripts/build_and_validate_sag_dataset.py` | `python scripts/audit_gate3f_sag_dataset.py` |
| **Voltage Swell** | `matlab -batch "run('scripts/generate_ieee9bus_swell_dataset.m')"` | `python scripts/build_and_validate_swell_dataset.py` | `python scripts/audit_gate3i_swell_dataset.py` |
| **Voltage Interruption** | `matlab -batch "run('scripts/generate_ieee9bus_interruption_dataset.m')"` | `python scripts/build_and_validate_interruption_dataset.py` | `python scripts/audit_gate3l_interruption_dataset.py` |
| **Harmonics** | `matlab -batch "run('scripts/generate_ieee9bus_harmonics_dataset.m')"` | `python scripts/build_and_validate_harmonics_dataset.py` | `python scripts/audit_gate3o_harmonics_dataset.py` |
| **Voltage Flicker** | `matlab -batch "run('scripts/generate_ieee9bus_flicker_dataset.m')"` | `python scripts/build_and_validate_flicker_dataset.py` | `python scripts/audit_gate3r_flicker_dataset.py` |
| **Voltage Notch** | `matlab -batch "run('scripts/generate_ieee9bus_notch_dataset.m')"` | `python scripts/build_and_validate_notch_dataset.py` | `python scripts/audit_gate3u_notch_dataset.py` |
| **Oscillatory Transient** | `matlab -batch "run('scripts/generate_ieee9bus_transient_dataset.m')"` | `python scripts/build_and_validate_transient_dataset.py` | `python scripts/audit_gate3x_transient_dataset.py` |

---

## 5. Authoritative Artifacts & Cryptographic Checksums

The following files under `data/ieee9bus_60hz/` are authoritative:

| Disturbance Class | Authoritative Feature File | Authoritative Scenario File | Checksum Authority |
|:---|:---|:---|:---|
| **Normal** | `data/ieee9bus_60hz/normal/normal_features.csv` | `data/ieee9bus_60hz/normal/operating_conditions.json` | [`docs/gate3b1_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3b1_quality_summary.json) |
| **Sag** | `data/ieee9bus_60hz/sag/sag_features.csv` | `data/ieee9bus_60hz/sag/sag_scenarios.json` | [`docs/gate3f_sag_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3f_sag_quality_summary.json) |
| **Swell** | `data/ieee9bus_60hz/swell/swell_features.csv` | `data/ieee9bus_60hz/swell/swell_scenarios.json` | [`docs/gate3i_swell_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3i_swell_quality_summary.json) |
| **Interruption** | `data/ieee9bus_60hz/interruption/interruption_features.csv` | `data/ieee9bus_60hz/interruption/interruption_scenarios.json` | [`docs/gate3l_interruption_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3l_interruption_quality_summary.json) |
| **Harmonics** | `data/ieee9bus_60hz/harmonics/harmonics_features.csv` | `data/ieee9bus_60hz/harmonics/harmonics_scenarios.json` | [`docs/gate3o_harmonics_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3o_harmonics_quality_summary.json) |
| **Flicker** | `data/ieee9bus_60hz/flicker/flicker_features.csv` | `data/ieee9bus_60hz/flicker/flicker_scenarios.json` | [`docs/gate3r_flicker_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3r_flicker_quality_summary.json) |
| **Notch** | `data/ieee9bus_60hz/notch/notch_features.csv` | `data/ieee9bus_60hz/notch/notch_scenarios.json` | [`docs/gate3u_notch_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3u_notch_quality_summary.json) |
| **Transient** | `data/ieee9bus_60hz/transient/transient_features.csv` | `data/ieee9bus_60hz/transient/transient_scenarios.json` | [`docs/gate3x_transient_quality_summary.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3x_transient_quality_summary.json) |

---

## 6. How to Run the REST Server & Live Dashboard Replay

To run the local telemetry server and view the CRT oscilloscope dashboard:

```bash
python server.py 8500
```

Navigate in any modern web browser to:
```text
http://localhost:8500
```

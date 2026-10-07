# Scripts Subsystem & Automation Registry

**Subsystem:** Simulation, Dataset Generation, Validation & Audit Automation  
**Authoritative Context:** 60-Hz WSCC IEEE 9-Bus Simulation & Production DSP Pipeline  

---

## 1. Script Categories & Operational Matrix

The `scripts/` directory contains automated pipelines for generating physical disturbance datasets from Simulink, extracting 32 features, validating physical invariants, and auditing quality gates:

### 1.1 Dataset Generation Scripts (MATLAB)
These scripts orchestrate batch simulations in Simulink across 32 operating conditions:

| Script | Disturbance Class | Output MAT File | Primary Function |
|---|---|---|---|
| `generate_ieee9bus_normal_dataset.m` | Normal Baseline | `raw_normal_simulations.mat` | Simulates 32 operating conditions across varied generator dispatches and loads. |
| `generate_ieee9bus_sag_dataset.m` | Voltage Sag | `raw_sag_simulations.mat` | Sweeps fault impedances ($R_f \in [0.1, 15.0]\ \Omega$) and fault types (3P, LL, LG). |
| `generate_ieee9bus_swell_dataset.m` | Voltage Swell | `raw_swell_simulations.mat` | Sweeps switched capacitor bank energization ($50\text{--}150\text{ MVAR}$). |
| `generate_ieee9bus_interruption_dataset.m` | Voltage Interruption | `raw_interruption_simulations.mat` | Controls series line breaker opening and feeder isolation. |
| `generate_ieee9bus_harmonics_dataset.m` | Harmonics | `raw_harmonics_simulations.mat` | Injects non-linear load harmonics ($H_2, H_3, H_5, H_7, H_9, H_{11}$). |
| `generate_ieee9bus_flicker_dataset.m` | Voltage Flicker | `raw_flicker_simulations.mat` | Injects sub-synchronous dynamic load modulation ($f_m \in [1, 25]\text{ Hz}$). |
| `generate_ieee9bus_notch_dataset.m` | Voltage Notch | `raw_notch_simulations.mat` | Controls thyristor commutation switching ($R_{\text{comm}} \in [10, 100]\ \Omega$). |
| `generate_ieee9bus_transient_dataset.m` | Oscillatory Transient | `raw_transient_simulations.mat` | Switches grounded series RLC branch energization ($300\text{--}2,200\text{ Hz}$). |
| `run_disturbance_simulation.m` | Unified Runner | Target MAT | Unified MATLAB harness executing individual scenario JSON definitions. |

---

### 1.2 Dataset Builders & Validators (Python)
These scripts extract 32 features from raw simulation MAT-files, create NPZ waveform archives and CSV feature tables, and execute physical rule validation:

- `build_and_validate_sag_dataset.py` (Gate 3E)
- `build_and_validate_swell_dataset.py` (Gate 3H)
- `build_and_validate_interruption_dataset.py` (Gate 3K)
- `build_and_validate_harmonics_dataset.py` (Gate 3N)
- `build_and_validate_flicker_dataset.py` (Gate 3Q)
- `build_and_validate_notch_dataset.py` (Gate 3T)
- `build_and_validate_transient_dataset.py` (Gate 3W)

---

### 1.3 Independent Quality Audit Scripts (Python)
These scripts execute formal 16-domain audits verifying physical parameters, SNR, THD, absence of contamination, and zero trajectory leakage:

- `audit_gate3b1_normal_dataset.py` (Gate 3B.1 Audit)
- `audit_gate3f_sag_dataset.py` (Gate 3F Audit)
- `audit_gate3i_swell_dataset.py` (Gate 3I Audit)
- `audit_gate3l_interruption_dataset.py` (Gate 3L Audit)
- `audit_gate3o_harmonics_dataset.py` (Gate 3O Audit)
- `audit_gate3r_flicker_dataset.py` (Gate 3R Audit)
- `audit_gate3u_notch_dataset.py` (Gate 3U Audit)
- `audit_gate3x_transient_dataset.py` (Gate 3X Audit)

---

### 1.4 Diagnostic & Inspection Scripts (MATLAB)
Diagnostic utilities used during physical model development to inspect wiring, ports, and signal routing at Bus 5:

- `debug_bus5_measurement.m`
- `inspect_bus5_lines.m`
- `inspect_bus5_ports_detail.m`
- `inspect_inside_bus5.m`
- `inspect_line_branches.m`
- `trace_pqd_vabc.m`

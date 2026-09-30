# GATE 3D — Voltage Sag Implementation & Physical Validation

**Document Reference**: `docs/GATE3D_SAG_IMPLEMENTATION.md`  
**Date**: September 30, 2026  
**Status**: COMPLETE — ONE DETERMINISTIC SCENARIO IMPLEMENTED & PHYSICALLY VALIDATED  
**Electrical Network**: IEEE 9-bus benchmark system (60 Hz, Bus 5 measurement, 230 kV nominal)  

---

## 1. Executive Summary

In accordance with Gate 3D requirements, the first deterministic **Voltage Sag** disturbance was implemented, simulated, and independently physically validated in the IEEE 9-bus 60-Hz electrical system.

- **Pristine Reference Model**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` — **100% UNTOUCHED** (SHA256: `5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d`).
- **Disturbance Working Model**: `IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx` — separate copy utilizing Simscape Electrical Specialized Power Systems with `ode23tb` stiff solver.
- **Physical Insertion Mechanism**: Controllable **Fault Impedance** network connection at **Bus 4** (sending substation adjacent to Bus 5).
- **Physical Validation**: **PASS** (100% of mathematical gates in `docs/GATE3C_VALIDATION_PLAN.md` passed).
- **Ground Truth**: **Sag** (Class Index 5), declared strictly by `ScenarioController` without ML feedback.
- **Model Domain Status**: **`MODEL_DOMAIN_MISMATCH`** (ML model predicted *Interruption* with 1.0000 confidence, confirming that the legacy 50-Hz model weights are invalid for native 60-Hz IEEE 9-bus classification as established in Gate 2 and Gate 3A).

---

## 2. Electrical Mechanism & Insertion Point

### 2.1 Network Topology & Injection Node
Rather than synthetic post-simulation waveform multiplication, the voltage sag is produced as a true electrical consequence of grid load-flow redistribution and generator dynamic response.

```
       [Gen 1]
          │ (16.5 kV)
       [GSU 1] (16.5/230 kV)
          │
      [  BUS 4  ] ◄─── [PQD_Fault_Sag: Three-Phase Fault Block]
         /     \       (Switched impedance to ground: Rf = 180 Ω, Rg = 0.01 Ω)
   Line 4-6   Line 4-5 (100 km, 230 kV)
       /         \
   [BUS 6]    [  BUS 5  ] ◄─── Measurement extraction (Vabc_5, Iabc_5)
                 Load A (125 MW, 50 MVAR)
```

- **Insertion Node**: High-voltage bus **Bus 4** (230 kV transmission ring).
- **Block Used**: `powerlib/Elements/Three-Phase Fault` (named `PQD_Fault_Sag` in `IEEE_9bus_PQD_DISTURBANCES.slx`).
- **Connection**:
  - `PQD_Fault_Sag/LConn1` connected to Phase A of Bus 4 (`Line 4 - 5 /RConn1`).
  - `PQD_Fault_Sag/LConn2` connected to Phase B of Bus 4 (`Line 4 - 5 /RConn2`).
  - `PQD_Fault_Sag/LConn3` connected to Phase C of Bus 4 (`Line 4 - 5 /RConn3`).
- **Fault Type**: Balanced three-phase-to-ground fault ($3\Phi\text{-G}$).
- **Switching Control**: Internal transition timer `[t_start, t_end]`.

### 2.2 Fault Impedance vs. Bus 5 Voltage Sag Relationship
The relationship between fault resistance $R_f$ and the residual voltage $V_{\text{residual}}$ measured at Bus 5 was calibrated via continuous Simscape simulations:

| Fault Resistance $R_f$ | Pre-Event RMS | Event RMS | Residual Voltage | Sag Depth |
|:---|:---|:---|:---|:---|
| $50\,\Omega$ | $0.5864\,\text{pu}$ | $0.2284\,\text{pu}$ | **$0.389\,\text{pu}$** | $61.1\%$ |
| $80\,\Omega$ | $0.5864\,\text{pu}$ | $0.3032\,\text{pu}$ | **$0.517\,\text{pu}$** | $48.3\%$ |
| $120\,\Omega$ | $0.5864\,\text{pu}$ | $0.3703\,\text{pu}$ | **$0.632\,\text{pu}$** | $36.8\%$ |
| $180\,\Omega$ | $0.5864\,\text{pu}$ | $0.4308\,\text{pu}$ | **$0.735\,\text{pu}$** | $26.5\%$ |
| $250\,\Omega$ | $0.5864\,\text{pu}$ | $0.4710\,\text{pu}$ | **$0.803\,\text{pu}$** | $19.7\%$ |

For the deterministic first scenario (`SAG_0001_three_phase_symmetric`), $R_f = 180\,\Omega$ was selected, yielding a realistic transmission-level voltage sag with $\approx 66\%–73\%$ residual voltage.

---

## 3. Scenario Definition & Parameter Provenance

The scenario definition is stored in machine-readable JSON format at `scenarios/definitions/SAG_0001_three_phase_symmetric.json` and validated by `jsonschema` against `docs/GATE3C_SCENARIO_SCHEMA.json`:

```json
{
  "schema_version": "1.0",
  "scenario_id": "SAG_0001_three_phase_symmetric",
  "class": "Sag",
  "label_idx": 5,
  "label_source": "SCENARIO_CONTROLLER",
  "electrical_model": {
    "reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
    "working_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx",
    "model_unchanged": true
  },
  "injection_location": {
    "bus": "Bus4",
    "measurement_point": "Vabc_5",
    "mechanism": "FAULT_IMPEDANCE",
    "phase": "ABC"
  },
  "nominal_frequency_hz": 60.0,
  "sampling_rate_hz": 5000.0,
  "window_samples": 1000,
  "window_ms": 200.0,
  "seed": 42,
  "operating_condition_id": 1,
  "parameters": {
    "magnitude_pu": 0.735,
    "fault_resistance_ohms": 180.0,
    "ground_resistance_ohms": 0.01,
    "duration_cycles": 5.0,
    "duration_ms": 83.33,
    "onset_time_ms": 40.0,
    "transition_type": "POINT_ON_WAVE",
    "sensor_noise_snr_db": 52.0
  }
}
```

### Parameter Provenance Table
| Parameter | Value | Provenance Category | Standard Citation / Engineering Basis |
|:---|:---|:---|:---|
| `class` | `"Sag"` | `STANDARD-SUPPORTED` | IEEE 1159-2019 Table 2 |
| `magnitude_pu` | $0.735\,\text{pu}$ | `STANDARD-SUPPORTED` | IEEE 1159-2019 Table 2 (Residual range: $0.10$ to $0.90\,\text{pu}$) |
| `duration_cycles` | $5.0\,\text{cycles}$ | `STANDARD-SUPPORTED` | IEEE 1159-2019 Table 2 (Instantaneous/Momentary: $\ge 0.5\,\text{cycle}$) |
| `duration_ms` | $83.33\,\text{ms}$ | `PROJECT-DESIGN-CHOICE` | Derived from 5.0 cycles at 60.0 Hz |
| `onset_time_ms` | $40.0\,\text{ms}$ | `PROJECT-DESIGN-CHOICE` | Positioned to allow pre-event, event, and recovery within 200 ms |
| `transition_type` | `"POINT_ON_WAVE"` | `ENGINEERING-INTERPRETATION` | Breaker / fault initiation point-on-wave |
| `fault_resistance_ohms` | $180.0\,\Omega$ | `SIMULATION-PARAMETER` | Tuned network impedance to yield $\approx 0.70\,\text{pu}$ residual at Bus 5 |
| `ground_resistance_ohms`| $0.01\,\Omega$ | `SIMULATION-PARAMETER` | Bolted ground return path impedance |
| `sensor_noise_snr_db` | $52.0\,\text{dB}$ | `SIMULATION-PARAMETER` | 16-bit DAQ / VT noise floor model |

---

## 4. Simulation Results & Independent Physical Validation

### 4.1 Numerical Waveform Statistics
- **Simulation Duration**: $0.38\,\text{s}$ total continuous time; sliced to $200.0\,\text{ms}$ window ($1000$ samples @ $5000\,\text{Hz}$).
- **Pre-Event Nominal RMS ($V_a$)**: $0.5887\,\text{pu}$
- **Minimum Event RMS ($V_a$)**: $0.3872\,\text{pu}$
- **Measured Residual Voltage ($U_{\text{res}}$)**: **$0.6577\,\text{pu}$ ($65.8\%$ of nominal)**
- **Event Onset Time ($t_{\text{start}}$)**: $0.0406\,\text{s}$ ($40.6\,\text{ms}$ into frame)
- **Event Clearing Time ($t_{\text{end}}$)**: $0.1280\,\text{s}$ ($128.0\,\text{ms}$ into frame)
- **Measured Event Duration**: **$87.40\,\text{ms}$** (5.24 cycles at 60 Hz)
- **Affected Phases**: Phase A, Phase B, Phase C
- **Phase Configuration**: **Balanced Three-Phase Sag**

### 4.2 Physical Validation Gate Results
Evaluated purely from signal properties without consulting the ML classifier:

| Gate ID | Description | Threshold | Measured Value | Result |
|:---|:---|:---|:---|:---:|
| `SAG-01` | Residual Voltage Lower Bound | $\ge 0.10\,\text{pu}$ | $0.6577\,\text{pu}$ | **PASS** |
| `SAG-02` | Residual Voltage Upper Bound | $< 0.90\,\text{pu}$ | $0.6577\,\text{pu}$ | **PASS** |
| `SAG-03` | Minimum Event Duration | $\ge 8.33\,\text{ms}$ (0.5 cycle) | $87.40\,\text{ms}$ | **PASS** |
| `SAG-04` | Depressed Full-Frame RMS | $< 0.90 \times V_{\text{nom}}$ ($< 0.5298$) | $0.5223\,\text{pu}$ | **PASS** |
| `SAG-05` | Harmonic Distortion Limit | $\text{THD} < 5.0\%$ | $0.1775\%$ | **PASS** |
| `SAG-06` | Frequency Stability | $59.5 \le f_{\text{sys}} \le 60.5\,\text{Hz}$ | $59.9999\,\text{Hz}$ | **PASS** |
| `SAG-ANTI-INTERRUPT` | Distinguish from Interruption | Residual $\ge 0.10\,\text{pu}$ | $0.6577\,\text{pu}$ | **PASS** |
| `SAG-ANTI-SWELL` | Absence of Swell Co-event | Half-cycle $\text{RMS}_{\max} \le 1.10 \times V_{\text{nom}}$ | $0.5891\,\text{pu}$ | **PASS** |
| `WAVEFORM_CONTINUITY` | Absence of Step Discontinuities| Max $\Delta v < 0.20\,\text{pu}$ | $0.1412\,\text{pu}$ | **PASS** |
| **OVERALL** | **Independent Physical Validation** | **All Gates Pass** | **100% Passed** | **PASS** |

---

## 5. Production Feature Extraction (32-Feature Contract)

Extracted using the authoritative production Python pipeline (`dsp/enhanced_features.py`):

```
Feature                  | Value
-------------------------+--------------------------------------------------
rms_voltage              | 0.522274 pu (depressed from 0.5887 normal baseline)
peak_voltage             | 0.835253 pu
crest_factor             | 1.599262
thd                      | 0.1775% (confirms clean fault without harmonics)
duration                 | 92.8000 ms (sliding RMS detection)
dominant_freq            | 60.0000 Hz
system_freq              | 59.9999 Hz
snr                      | 13.3100 dB
h1                       | 0.721951 pu
h2                       | 0.010150 pu
h3                       | 0.000787 pu
h4                       | 0.001805 pu
h5                       | 0.000658 pu
h6                       | 0.001402 pu
h7                       | 0.000767 pu
h8                       | 0.001134 pu
h9                       | 0.000758 pu
h10                      | 0.000711 pu
h11                      | 0.000772 pu
h2_ratio                 | 0.014059
h3_ratio                 | 0.001090
h4_ratio                 | 0.002500
h5_ratio                 | 0.000911
h7_ratio                 | 0.001062
h9_ratio                 | 0.001050
h11_ratio                | 0.001069
harmonic_energy          | 0.000113 pu^2
spectral_centroid        | 60.2100 Hz
spectral_bandwidth       | 6.6900 Hz
spectral_entropy         | 0.0402
spectral_flatness        | 0.000010
true_dominant_freq       | 60.0000 Hz
```

### Feature Comparison: Normal Baseline vs Sag Waveform
| Feature | Normal Baseline (Gate 3B1) | Voltage Sag Waveform (Gate 3D) | Physical Explanation |
|:---|:---:|:---:|:---|
| `rms_voltage` | $0.5887\,\text{pu}$ | **$0.5223\,\text{pu}$** | Depressed due to $87\,\text{ms}$ fault dip |
| `crest_factor`| $1.4144$ | **$1.5993$** | Peak is maintained pre-event while RMS drops |
| `duration` | $0.0\,\text{ms}$ | **$92.8\,\text{ms}$** | Disturbance duration detected by sliding threshold |
| `system_freq` | $60.0000\,\text{Hz}$ | **$59.9999\,\text{Hz}$** | Fundamental 60-Hz grid frequency unchanged |
| `thd` | $0.08\%$ | **$0.18\%$** | Clean sinusoidal dip with minimal harmonic distortion |
| `snr` | $51.70\,\text{dB}$ | **$13.31\,\text{dB}$** | Reduced SNR reflects non-stationary transition steps |

---

## 6. Machine Learning Model Domain Decoupling

The existing MLP (`ml/models/model_weights_32.json`) was evaluated on the extracted 32-feature vector:

- **Ground Truth**: **`Sag`** (Label Index: 5) — provided by `ScenarioController`.
- **Raw Model Prediction**: **`Interruption`** (Confidence: `0.999995`).
- **Model Domain Status**: **`MODEL_DOMAIN_MISMATCH`**.

### Domain Mismatch Analysis
The existing MLP was trained on legacy synthetic 50-Hz waveforms normalized to $1.0\,\text{pu}$ RMS. When presented with native 60-Hz IEEE 9-bus Bus 5 measurements where the per-unit phase-to-ground RMS base is $0.5887\,\text{pu}$ and drops to $0.5223\,\text{pu}$, the un-retrained model misinterprets the lower numerical magnitude as an interruption.

This confirms the architectural necessity of Gate 3:
1. Ground-truth labels must **never** be generated from model inference.
2. The ML model must not be retrained until the full 8-class 60-Hz IEEE 9-bus dataset is generated and validated.

---

## 7. Artifacts & Generated Files

All generated data has been preserved in isolation without overwriting the Normal dataset:
- `data/ieee9bus_60hz/sag/sag_scenario_0001_waveform.npz`: resampled three-phase voltage and current waveforms ($1000 \times 3$).
- `data/ieee9bus_60hz/sag/sag_scenario_0001_features.json`: full 32-feature contracts for Phases A, B, and C.
- `data/ieee9bus_60hz/sag/sag_scenario_0001_validation.json`: independent physical validation metrics and gate evaluations.
- `data/ieee9bus_60hz/sag/sag_scenario_0001_metadata.json`: provenance, scenario configuration, timing, and domain mismatch record.
- `scenarios/scenario_controller.py`: modular scenario controller adhering to `GATE3C_SCENARIO_SCHEMA.json`.
- `scenarios/definitions/SAG_0001_three_phase_symmetric.json`: schema-compliant scenario declaration.
- `pipeline/disturbance_validator.py`: independent physical validator for Voltage Sag.
- `scripts/run_disturbance_simulation.m`: non-destructive MATLAB runner.
- `scripts/generate_and_validate_sag_scenario.py`: end-to-end Python pipeline runner.
- `tests/test_gate3d_sag.py`: automated test suite verifying all 10 Gate 3D criteria (10/10 passed).

---

## 8. Limitations & Scope Boundary

1. **Single Disturbance Class**: Only Voltage Sag was implemented in Gate 3D. Swell, Interruption, Harmonics, Flicker, Notch, and Transient remain strictly un-implemented until subsequent gates.
2. **Deterministic Pilot Run**: Exactly one deterministic scenario (`SAG_0001`) was simulated and validated. Batch generation across multiple operating conditions and parameter ranges will follow in subsequent dataset construction steps.
3. **ML Weights Unchanged**: No retraining was performed; model weights remain in legacy state.
4. **Pristine Model Invariant**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` is guaranteed identical to its initial benchmark state.

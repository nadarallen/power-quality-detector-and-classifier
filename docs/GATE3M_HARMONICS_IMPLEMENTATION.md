# Gate 3M: Deterministic Harmonics Implementation Report

**Status:** PASS  
**Timestamp:** 2026-10-04T07:23:00+05:30  
**Electrical Model:** IEEE 9-bus 60-Hz Power System (`IEEE_9bus_PQD_DISTURBANCES.slx`)  
**Pristine Reference Model:** `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` (Byte-for-byte frozen, SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`)  
**Scenario ID:** `HAR_0001_h3h5h7_typical`  
**Classification:** Harmonics (`label_idx = 1`)  
**Label Source:** `SCENARIO_CONTROLLER`  

---

## 1. Executive Summary

Gate 3M implements the first deterministic, physically grounded **Harmonics** disturbance inside the established IEEE 9-bus disturbance working model (`IEEE_9bus_PQD_DISTURBANCES.slx`). 

In strict adherence to the Gate 3M specifications and Gate 3C architecture:
1. **Actual Electrical Mechanism:** The harmonic distortion is produced electrically inside the SimPowerSystems network using a controlled three-phase harmonic current source connected to Bus 5 (230 kV). No synthetic Python waveform modification or post-processing sine-wave addition was performed.
2. **Zero Intersimulation Interference & Complete Dormancy:** When inactive, the harmonic control inputs are decoupled via a dedicated switch, injecting exactly $0\,\text{A}$ (infinite impedance open circuit). Normal, Sag, Swell, and Interruption simulations remain 100% unaffected.
3. **Pristine Reference Model Untouched:** The pristine reference model (`IEEE_9bus_PQD_HIL_R2025a.slx`) remains byte-for-byte frozen and verified by SHA-256 hash.
4. **Physical & Standards Compliance:** The deterministic scenario exhibits clear odd harmonic distortion ($H_3 = 0.0577\,\text{pu}$, $H_5 = 0.0260\,\text{pu}$, $H_7 = 0.0267\,\text{pu}$) with composite $\text{THD} = 8.24\%$, satisfying the dataset design threshold ($\text{THD} > 5.0\%$) and remaining within the IEEE 519/1159 physical steady-state envelope.
5. **Decoupled Machine Learning:** Ground truth is established purely by `SCENARIO_CONTROLLER`. Legacy 50-Hz neural network predictions are flagged as `OUT_OF_DOMAIN` without corrupting dataset ground truth or physical validation.
6. **MATLAB / Python DSP Numerical Parity:** Production Python DSP and MATLAB reference DSP match to $\Delta_{\text{max}} = 0.000048$ ($4.8 \times 10^{-5}$), easily passing the numerical parity tolerance.

---

## 2. Electrical Insertion & Physical Mechanism

### 2.1 Topology & Circuit Location
Per Gate 3C §4.5, nonlinear industrial loads (e.g., 6-pulse rectifiers, variable frequency drives, arc furnaces) act primarily as harmonic current injectors whose currents interact with the Thevenin source impedance of the network to produce voltage distortion at the Point of Common Coupling (PCC).

- **Bus Location:** Bus 5 (230 kV, Load Bus with 125 MW + 50 MVAR baseline load).
- **Physical Block:** `spsControlledCurrentSourceLib/Controlled Current Source` (SimPowerSystems block).
- **Phases:** 3 independent blocks (`PQD_Harmonics_A`, `PQD_Harmonics_B`, `PQD_Harmonics_C`).
- **Connection:**
  - Positive terminal (`LConn1`) connected to `Bus_5 230 KV/RConn1..3` (Bus 5 load node).
  - Negative terminal (`RConn1`) connected to `spsGroundLib/Ground`.
- **Control Input:** Inport 1 receives the instantaneous continuous harmonic current waveform $i_a(t), i_b(t), i_c(t)$ in Amperes.

### 2.2 Dormancy Architecture
To guarantee that the harmonics mechanism never leaks into other disturbance simulations:
- A Simulink Switch block (`PQD_Harm_Switch`) selects between the harmonic control signal (`PQD_Harm_FromWS`) and a zero vector (`PQD_Harm_Zero`, `[0 0 0]`), controlled by `PQD_Harm_Enable`.
- Default state: `PQD_Harm_Enable = 0`. Current sources inject exactly 0 A, acting as ideal open circuits ($Z = \infty$).
- Validated on baseline Normal mode: Bus 5 voltage is identical to the pristine model ($V_{\text{RMS}} = 0.5887\,\text{pu}$).

---

## 3. Harmonic Parameter Specification & Provenance

In accordance with Gate 3M.2 and Gate 3C §4.5:

| Parameter | Configured Value | Measured Bus 5 Value | Provenance Category | Standard / Reference |
|:---|:---:|:---:|:---:|:---|
| **Disturbance Class** | Harmonics | Harmonics | `SCENARIO_CONTROLLER` | IEEE 1159-2019 Clause 4.4.4.1 |
| **Label Index** | 1 | 1 | `CONTRACT` | `dsp/phase_processor.py` |
| **Fundamental Frequency ($f_1$)** | 60.0 Hz | 60.00 Hz | `GRID-SPEC` | IEEE Std 519-2022 |
| **Harmonic Orders Injected** | {3, 5, 7} | {3, 5, 7} present | `ENGINEERING-INTERPRETATION` | Characteristic 6-pulse & single-phase converter spectrum |
| **Harmonic Current $I_3$** | 45.0 A | — | `SIMULATION-PARAMETER` | Injected current amplitude |
| **Harmonic Current $I_5$** | 28.0 A | — | `SIMULATION-PARAMETER` | Injected current amplitude |
| **Harmonic Current $I_7$** | 16.0 A | — | `SIMULATION-PARAMETER` | Injected current amplitude |
| **Harmonic Voltage $H_3$** | 0.04–0.15 pu | 0.0577 pu (6.93%) | `PHYSICAL-RESPONSE` | Network response ($I_3 \times Z_3$) |
| **Harmonic Voltage $H_5$** | 0.02–0.10 pu | 0.0260 pu (3.12%) | `PHYSICAL-RESPONSE` | Network response ($I_5 \times Z_5$) |
| **Harmonic Voltage $H_7$** | 0.01–0.06 pu | 0.0267 pu (3.20%) | `PHYSICAL-RESPONSE` | Network response ($I_7 \times Z_7$) |
| **Total Harmonic Distortion (THD)** | 5.0–20.0% | 8.24% | `DATASET-DESIGN-CHOICE` | Demarcation from Normal (THD < 0.09%) |
| **Frame Duration** | 200 ms (1000 samples) | 200.0 ms | `ENGINEERING-INTERPRETATION` | Steady-state continuous phenomenon |
| **Operating Condition** | Cond 1 (125 MW + 50 MVAR) | Nominal baseline | `OPERATING-CONDITION` | IEEE 9-bus base case |

> [!NOTE]
> **Standards Demarcation:** Per Gate 3C §4.5 and ST-HAR-05, IEEE 519 Table 1 specifies utility compliance limits at the PCC (e.g., THD ≤ 1.5% at 230 kV). The project classification threshold of $\text{THD} > 5.0\%$ is an engineered dataset design threshold to ensure robust ML discriminability from Normal operating background noise, NOT an IEEE compliance limit.

---

## 4. Physical Measurements & Validation Results

### 4.1 Waveform Geometry & Sampling
- **Sampling Rate:** $F_s = 5000\,\text{Hz}$ ($\Delta t = 200\,\mu\text{s}$)
- **Nyquist Frequency:** $2500\,\text{Hz}$ (H11 = 660 Hz has oversampling ratio $7.6\times$; H7 = 420 Hz has oversampling ratio $11.9\times$)
- **Frame Length:** $N = 1000$ samples ($200.0\,\text{ms}$, 12 full fundamental cycles)
- **Channels:** 3 phases ($V_a, V_b, V_c$), finite, zero NaN, zero Inf.

### 4.2 Multi-Phase Spectral Analysis
All three phases were simulated and analyzed independently:

| Metric | Phase A | Phase B | Phase C | Validation Gate | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Full-Window RMS ($V_{\text{RMS}}$)** | 0.5913 pu | 0.5936 pu | 0.5845 pu | $[0.50, 0.80]\,\text{pu}$ | **PASS** |
| **Dominant Frequency ($f_{\text{dom}}$)** | 60.00 Hz | 60.00 Hz | 60.00 Hz | $[59.5, 60.5]\,\text{Hz}$ | **PASS** |
| **Total Harmonic Distortion (THD)** | 8.24% | 8.48% | 7.97% | $> 5.0\%$ | **PASS** |
| **Fundamental Component ($H_1$)** | 0.8333 pu | 0.8365 pu | 0.8239 pu | — | **PASS** |
| **3rd Harmonic ($H_3$)** | 0.0577 pu | 0.0577 pu | 0.0546 pu | $> 0.03\,\text{pu}$ | **PASS** |
| **5th Harmonic ($H_5$)** | 0.0260 pu | 0.0270 pu | 0.0297 pu | $> 0.01\,\text{pu}$ | **PASS** |
| **7th Harmonic ($H_7$)** | 0.0267 pu | 0.0312 pu | 0.0212 pu | $> 0.01\,\text{pu}$ | **PASS** |
| **Even Harmonics ($H_2, H_4, H_6$)** | < 0.0001 pu | < 0.0001 pu | < 0.0001 pu | Negligible (symmetric) | **PASS** |

### 4.3 Physical Decomposition ($v_{\text{fund}} + v_{\text{harm}} = v_{\text{measured}}$)
To verify that the measured voltage distortion originates directly and exclusively from the physical harmonic injection:
- Fundamental component reconstructed: $V_{\text{fund,RMS}} = 0.5893\,\text{pu}$
- Harmonic components reconstructed: $V_{\text{harm,RMS}} = 0.0486\,\text{pu}$
- Reconstruction Mean Squared Error (MSE): $< 1.0 \times 10^{-6}$
- Relative fit error: **0.01%**

This proves that the fundamental voltage remains physically intact and realistic, while the harmonic current injection accounts for 99.99% of the observed waveform distortion.

### 4.4 Anti-Contamination & Secondary Disturbance Audit
- **Anti-Sag Check:** Minimum half-cycle RMS across all three phases is $0.5821\,\text{pu} \ge 0.90 \times V_{\text{nominal}}$ ($0.5298\,\text{pu}$). No sag contamination.
- **Anti-Swell Check:** Maximum half-cycle RMS across all three phases is $0.5942\,\text{pu} \le 1.10 \times V_{\text{nominal}}$ ($0.6476\,\text{pu}$). No swell contamination.
- **Continuity Check:** Maximum sample-to-sample difference $\max |\Delta v| = 0.076\,\text{pu/sample} < 0.35\,\text{pu/sample}$. Waveform is physically smooth and continuous with no transient step artifacts.

---

## 5. Authoritative 32-Feature Extraction & DSP Parity

The production feature extractor (`extract_enhanced_features`) was executed on the simulated waveform, computing the frozen 32-feature contract:

```json
{
  "rms_voltage": 0.5913,
  "peak_voltage": 0.8147,
  "crest_factor": 1.378,
  "thd": 8.24,
  "duration": 0.0,
  "dominant_freq": 60.0,
  "system_freq": 60.0,
  "snr": 21.68,
  "h1": 0.8333,
  "h2": 0.0,
  "h3": 0.0577,
  "h4": 0.0,
  "h5": 0.026,
  "h6": 0.0,
  "h7": 0.0267,
  "h8": 0.0,
  "h9": 0.0,
  "h10": 0.0,
  "h11": 0.0,
  "h2_ratio": 0.0,
  "h3_ratio": 0.0693,
  "h4_ratio": 0.0,
  "h5_ratio": 0.0312,
  "h7_ratio": 0.032,
  "h9_ratio": 0.0,
  "h11_ratio": 0.0,
  "harmonic_energy": 0.004718,
  "spectral_centroid": 105.82,
  "spectral_bandwidth": 139.46,
  "spectral_entropy": 0.724,
  "spectral_flatness": 0.0003,
  "true_dominant_freq": 60.0
}
```

### MATLAB vs. Python DSP Parity Check

| Metric | MATLAB Reference FFT | Production Python DSP | Absolute Difference | Parity Tolerance | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **RMS Voltage** | 0.5913 pu | 0.5913 pu | 0.000000 | 0.005 | **PASS** |
| **Peak Voltage** | 0.8147 pu | 0.8147 pu | 0.000000 | 0.005 | **PASS** |
| **Crest Factor** | 1.3780 | 1.3780 | 0.000000 | 0.010 | **PASS** |
| **Fundamental $H_1$** | 0.8333 pu | 0.8333 pu | 0.000000 | 0.005 | **PASS** |
| **3rd Harmonic $H_3$** | 0.0577 pu | 0.0577 pu | 0.000000 | 0.005 | **PASS** |
| **5th Harmonic $H_5$** | 0.0260 pu | 0.0260 pu | 0.000000 | 0.005 | **PASS** |
| **7th Harmonic $H_7$** | 0.0267 pu | 0.0267 pu | 0.000000 | 0.005 | **PASS** |
| **THD** | 8.24% | 8.24% | 0.000048 | 0.050 | **PASS** |

---

## 6. Machine Learning Decoupling Audit

In strict compliance with project rules:
- **ML Retraining:** NOT performed.
- **Model Weights:** `ml/models/model_weights_32.json` remains frozen and byte-for-byte unchanged.
- **Inference Evaluation:** The legacy 50-Hz MLP evaluated the 32-feature vector and output:
  - `predicted_class`: `Interruption` (Confidence: 1.0000)
  - `model_domain_status`: `OUT_OF_DOMAIN`
- **Decoupling Enforcement:** The ML classification was recorded for diagnostic tracking only. Ground truth was set strictly to `"Harmonics"` by `SCENARIO_CONTROLLER`. Dataset inclusion and physical validation were 100% independent of the ML output.

---

## 7. Deliverables & Artifact Manifest

The following authoritative artifacts were produced and validated:

| File Path | Description | Checksum / Size |
|:---|:---|:---|
| `scenarios/definitions/HAR_0001_h3h5h7_typical.json` | Scenario specification | Schema validated |
| `data/ieee9bus_60hz/harmonics/raw_sim_har_0001.mat` | Raw MATLAB simulation output | Mat-file (1000 samples, $V_{abc}, I_{abc}$) |
| `data/ieee9bus_60hz/harmonics/harmonics_scenario_0001_waveform.npz` | Resampled 5 kHz waveform | NPZ compressed |
| `data/ieee9bus_60hz/harmonics/harmonics_scenario_0001_features.json` | Authoritative 32 production features | Formatted JSON |
| `data/ieee9bus_60hz/harmonics/harmonics_scenario_0001_validation.json` | Full physical validation report | Formatted JSON |
| `data/ieee9bus_60hz/harmonics/harmonics_scenario_0001_metadata.json` | Scenario provenance and hashes | Formatted JSON |
| `tests/test_gate3m_harmonics.py` | 12 automated unit/integration tests | 12/12 PASS |

---

## 8. Gate 3M Compliance Checklist

| Criterion | Requirement | Result | Status |
|:---:|:---|:---|:---:|
| **1** | Harmonics originate from actual electrical mechanism | SimPowerSystems Controlled Current Sources at Bus 5 | **PASS** |
| **2** | One deterministic scenario is reproducible | `HAR_0001_h3h5h7_typical` fully automated and reproducible | **PASS** |
| **3** | Required harmonic orders physically present | $H_3=0.0577\,\text{pu}, H_5=0.0260\,\text{pu}, H_7=0.0267\,\text{pu}$ | **PASS** |
| **4** | Fundamental frequency remains ~60 Hz | $f_{\text{dom}} = 60.00\,\text{Hz}$ | **PASS** |
| **5** | Harmonic magnitudes measurable in waveform | Extracted via Goertzel & FFT | **PASS** |
| **6** | THD independently measured | $\text{THD} = 8.24\% > 5.0\%$ | **PASS** |
| **7** | Phase behavior verified | Evaluated independently for $V_a, V_b, V_c$ | **PASS** |
| **8** | No unintended severe PQD class contamination | Anti-sag ($V_{\text{min}} \ge 0.90$), anti-swell ($V_{\text{max}} \le 1.10$) pass | **PASS** |
| **9** | Production 32-feature extraction succeeds | Zero NaN, zero Inf, exact schema adherence | **PASS** |
| **10** | MATLAB/Python DSP parity passes | $\Delta_{\text{max}} = 4.8 \times 10^{-5} < 0.05$ | **PASS** |
| **11** | Ground truth from `SCENARIO_CONTROLLER` | Immutable label `"Harmonics"` (`label_idx = 1`) | **PASS** |
| **12** | ML not used for labeling | ML decoupled, `OUT_OF_DOMAIN` flagged | **PASS** |
| **13** | Pristine reference model unchanged | SHA-256 verified byte-for-byte identical | **PASS** |
| **14** | Regression tests pass | 206 passed, 2 skipped, 0 failed across full test suite | **PASS** |

---

## 9. Final Gate 3M Verdict

$$\mathbf{GATE3M\_HARMONICS\_IMPLEMENTATION = PASS}$$

**Execution Stop Notice:** In accordance with the user instructions, execution terminates immediately upon completion of Gate 3M. Harmonics dataset generation (Gate 3N), Flicker, Notch, Transient, and ML retraining have NOT been started.

# Gate 3P: Deterministic Flicker Implementation Report

**Status:** PASS  
**Timestamp:** 2026-10-07T05:40:00+05:30  
**Electrical Model:** IEEE 9-bus 60-Hz Power System (`IEEE_9bus_PQD_DISTURBANCES.slx`)  
**Pristine Reference Model:** `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` (Byte-for-byte frozen, SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`)  
**Scenario ID:** `FLK_0001_fm10hz_depth5pct`  
**Classification:** Flicker (`label_idx = 0`)  
**Label Source:** `SCENARIO_CONTROLLER`  

---

## 1. Executive Summary

Gate 3P implements the first deterministic, physically grounded **Voltage Flicker** disturbance inside the established IEEE 9-bus disturbance working model (`IEEE_9bus_PQD_DISTURBANCES.slx`).

In strict adherence to the Gate 3P specifications, Gate 3C architecture, and IEEE 1159/1453 standards traceability:
1. **Physical Electrical Network Origin:** The voltage envelope modulation is produced electrically inside the SimPowerSystems network through dynamic, periodic load current modulation injected at Bus 5 (230 kV). No post-simulation multiplying of arrays in Python, synthetic waveforms, or post-acquisition envelope scaling was performed.
2. **Zero Intersimulation Interference & Complete Dormancy:** When inactive (`PQD_Flicker_Enable = 0`), the flicker injector switches to a zero vector (`[0 0 0]`), drawing exactly $0\,\text{A}$ (infinite impedance open circuit). Normal, Sag, Swell, Interruption, and Harmonics simulations remain 100% unaffected.
3. **Pristine Reference Model Untouched:** The pristine reference model (`IEEE_9bus_PQD_HIL_R2025a.slx`) remains byte-for-byte frozen and verified by SHA-256 hash.
4. **Physical & Standards Compliance:** The deterministic scenario exhibits clear cyclic amplitude modulation ($f_m = 10.0\,\text{Hz}$, modulation depth $m = 3.79\%$, 2.0 complete modulation cycles in the 200 ms frame) satisfying Gate 3C bounds ($m \in [0.02, 0.15]$, $f_m \in [3.0, 20.0]\,\text{Hz}$) and anti-contamination gates.
5. **Decoupled Machine Learning:** Ground truth is established purely by `SCENARIO_CONTROLLER` (`label_idx = 0`). Raw model predictions from legacy weights are marked `OUT_OF_DOMAIN` without influencing sample validity or ground truth.
6. **MATLAB / Python DSP Numerical Parity:** Production Python DSP and MATLAB reference DSP match to $\Delta_{\text{max}} = 0.000727$ ($7.27 \times 10^{-4}$), easily passing the numerical parity tolerance (< 0.05).

---

## 2. Electrical Insertion & Physical Mechanism

### 2.1 Topology & Circuit Location
Per Gate 3C §4.6 and IEEE 1159-2019 Clause 4.4.3, voltage flicker in power networks is caused by industrial loads with rapid, periodic fluctuations in real and reactive power demand (e.g., electric arc furnaces, welding machines, cyclic motor drives). These fluctuating currents interact with the Thevenin impedance of the transmission grid to produce amplitude modulation of the bus voltage envelope.

- **Bus Location:** Bus 5 (230 kV Load Bus, nominal load 125 MW + 50 MVAR).
- **Physical Block:** `spsControlledCurrentSourceLib/Controlled Current Source` (SimPowerSystems block).
- **Phases:** 3 independent blocks (`PQD_Flicker_A`, `PQD_Flicker_B`, `PQD_Flicker_C`).
- **Connection:**
  - Positive terminals (`LConn1`) connected to `Bus_5 230 KV/RConn1..3`.
  - Negative terminals (`RConn1`) connected to `spsGroundLib/Ground`.
- **Control Input:** Inport 1 receives the instantaneous continuous flicker current waveform:
  $$i_a(t) = I_m \sin(2\pi f_m t + \phi_m) \sin(\omega_0 t)$$
  $$i_b(t) = I_m \sin(2\pi f_m t + \phi_m) \sin(\omega_0 t - 2\pi/3)$$
  $$i_c(t) = I_m \sin(2\pi f_m t + \phi_m) \sin(\omega_0 t + 2\pi/3)$$

### 2.2 Dormancy Architecture
To guarantee that the flicker mechanism never leaks into other disturbance simulations:
- A Simulink Switch block (`PQD_Flicker_Switch`) selects between the flicker control signal (`PQD_Flicker_FromWS`) and a zero vector (`PQD_Flicker_Zero`, `[0 0 0]`), controlled by `PQD_Flicker_Enable`.
- Default state: `PQD_Flicker_Enable = 0`. Current sources inject exactly 0 A, acting as ideal open circuits ($Z = \infty$).
- Validated on baseline Normal mode: Bus 5 voltage is identical to the pristine model ($V_{\text{RMS}} = 0.5887\,\text{pu}$).

---

## 3. Parameter Specification & Provenance

In accordance with Gate 3P.1 and Gate 3C §4.6:

| Parameter | Configured Value | Measured Bus 5 Value | Provenance Category | Standard / Reference |
|:---|:---:|:---:|:---:|:---|
| **Disturbance Class** | Flicker | Flicker | `SCENARIO_CONTROLLER` | IEEE 1159-2019 Clause 4.4.3 |
| **Label Index** | 0 | 0 | `CONTRACT` | `dsp/phase_processor.py` |
| **Grid Frequency ($f_0$)** | 60.0 Hz | 60.00 Hz | `GRID-SPEC` | IEEE Std 1159-2019 |
| **Modulation Frequency ($f_m$)** | 10.0 Hz | 10.00 Hz | `STANDARD-SUPPORTED` | IEEE 1159 range 0.5–30 Hz; IEEE 1453 sensitivity band |
| **Modulation Depth ($m$)** | 0.05 pu (5%) | 0.0379 pu (3.79%) | `STANDARD-SUPPORTED` | IEEE 1159 typical 0.1–10% range |
| **Modulation Cycles in Window** | 2.0 cycles | 2.00 cycles | `DATASET-DESIGN-CHOICE` | $\ge 1.0$ cycle for 200 ms representation |
| **Flicker Current ($I_m$)** | 278.0 A | — | `SIMULATION-PARAMETER` | Derived from Bus 5 Thevenin impedance |
| **Total Harmonic Distortion (THD)** | < 3.0% | 0.01% | `DATASET-DESIGN-CHOICE` | Demarcation from Harmonics class |
| **Sampling Rate ($F_s$)** | 5000 Hz | 5000 Hz | `CONTRACT` | System architecture |
| **Window Duration** | 200 ms (1000 samples) | 199.8 ms | `CONTRACT` | Short-window ML contract |
| **Operating Condition** | Cond 1 (125 MW + 50 MVAR) | Nominal baseline | `OPERATING-CONDITION` | IEEE 9-bus base case |

---

## 4. Physical Measurements & Validation Results

### 4.1 Waveform Geometry & Sampling
- **Sampling Rate:** $F_s = 5000\,\text{Hz}$ ($\Delta t = 200\,\mu\text{s}$)
- **Nyquist Frequency:** $2500\,\text{Hz}$
- **Frame Length:** $N = 1000$ samples ($200.0\,\text{ms}$, 12 full fundamental cycles)
- **Channels:** 3 phases ($V_a, V_b, V_c$), finite, zero NaN, zero Inf.

### 4.2 Multi-Phase Envelope & Spectral Analysis
All three phases were simulated and analyzed independently:

| Metric | Phase A | Phase B | Phase C | Validation Gate | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Full-Window RMS ($V_{\text{RMS}}$)** | 0.5951 pu | 0.5974 pu | 0.5889 pu | $[0.50, 0.80]\,\text{pu}$ | **PASS** |
| **Dominant Frequency ($f_{\text{dom}}$)** | 60.00 Hz | 60.00 Hz | 60.00 Hz | $[59.5, 60.5]\,\text{Hz}$ | **PASS** |
| **Envelope Modulation Depth ($m$)** | 3.71% | 3.77% | 3.79% | $[2.0, 15.0]\%$ | **PASS** |
| **Envelope Frequency ($f_m$)** | 10.00 Hz | 10.00 Hz | 10.00 Hz | $[3.0, 20.0]\,\text{Hz}$ | **PASS** |
| **Modulation Cycles in Window** | 2.00 | 2.00 | 2.00 | $\ge 1.0$ cycle | **PASS** |
| **Total Harmonic Distortion (THD)** | 0.01% | 0.00% | 0.00% | $< 3.0\%$ | **PASS** |
| **Minimum Half-Cycle RMS** | 0.5624 pu | 0.5639 pu | 0.5564 pu | $\ge 0.5298\,\text{pu}$ (no sag) | **PASS** |
| **Maximum Half-Cycle RMS** | 0.6221 pu | 0.6249 pu | 0.6156 pu | $\le 0.6476\,\text{pu}$ (no swell) | **PASS** |

### 4.3 Anti-Contamination & Secondary Disturbance Audit
- **Anti-Sag Check:** Minimum half-cycle RMS across all three phases is $0.5564\,\text{pu} > 0.90 \times V_{\text{nominal}}$ ($0.5298\,\text{pu}$). No sag contamination.
- **Anti-Swell Check:** Maximum half-cycle RMS across all three phases is $0.6249\,\text{pu} < 1.10 \times V_{\text{nominal}}$ ($0.6476\,\text{pu}$). No swell contamination.
- **Anti-Interruption Check:** Minimum half-cycle RMS across all three phases is $0.5564\,\text{pu} \gg 0.10 \times V_{\text{nominal}}$ ($0.0589\,\text{pu}$). No interruption collapse.
- **Harmonics Separation Check:** THD is $0.01\% < 3.0\%$, and all harmonic orders H2–H11 are $< 0.001\,\text{pu}$. Sidebands are located at $60 \pm 10\,\text{Hz}$ (50 Hz and 70 Hz), distinctly separate from integer harmonic orders.
- **Continuity Check:** Maximum sample-to-sample difference $\max |\Delta v| = 0.076\,\text{pu/sample} < 0.35\,\text{pu/sample}$. Waveform is physically smooth and continuous with zero step discontinuity.

---

## 5. Production 32-Feature Extraction & DSP Parity

The production feature extractor (`extract_enhanced_features`) was executed on Phase A, computing the authoritative 32-feature contract:

```json
{
  "rms_voltage": 0.5951,
  "peak_voltage": 0.8659,
  "crest_factor": 1.455,
  "thd": 0.01,
  "duration": 0.0,
  "dominant_freq": 60.0,
  "system_freq": 60.0,
  "snr": 17.03,
  "h1": 0.8415,
  "h2": 0.0,
  "h3": 0.0,
  "h4": 0.0,
  "h5": 0.0,
  "h6": 0.0,
  "h7": 0.0,
  "h8": 0.0,
  "h9": 0.0,
  "h10": 0.0,
  "h11": 0.0,
  "h2_ratio": 0.0,
  "h3_ratio": 0.0,
  "h4_ratio": 0.0,
  "h5_ratio": 0.0,
  "h7_ratio": 0.0,
  "h9_ratio": 0.0,
  "h11_ratio": 0.0,
  "harmonic_energy": 0.0,
  "spectral_centroid": 60.15,
  "spectral_bandwidth": 3.72,
  "spectral_entropy": 0.076,
  "spectral_flatness": 0.0,
  "true_dominant_freq": 60.0
}
```

### MATLAB / Python Parity Evaluation
- `rms_diff`: $0.000000$
- `peak_diff`: $0.000000$
- `crest_diff`: $0.000000$
- `h1_diff`: $0.000000$
- `thd_diff`: $0.000727$
- **Max Absolute Difference:** $\mathbf{0.000727}$ ($7.27 \times 10^{-4} \ll 0.05$). **PASS**.

---

## 6. Machine Learning Diagnostic & Decoupling

- **Ground Truth:** `Flicker` (`label_idx = 0`) from `SCENARIO_CONTROLLER`.
- **Legacy MLP Evaluation:**
  - Raw prediction: `Interruption` (Confidence: 100.00%).
  - Model domain status: `OUT_OF_DOMAIN` (Legacy weights trained on 50-Hz synthetic grid without 60-Hz flicker training).
  - Decoupling assertion: **ML prediction has ZERO influence over scenario validity or ground-truth labeling.**

---

## 7. IEEE Standards Demarcation Boundary

In accordance with Gate 3P.3 and Gate 3C §4.6 / ST-FLK-04:
- **Standard Metric ($P_{st}$):** IEEE Std 1453-2022 defines $P_{st}$ (short-term flicker severity) as a 10-minute cumulative statistical aggregation measured through a compliant flickermeter filter chain (IEC 61000-4-15).
- **Project Short-Window Observable:** The 200 ms frame ($1000$ samples @ 5 kHz) captures the **instantaneous envelope modulation depth ($m$) and modulation frequency ($f_m$)**, which correspond to the canonical sinusoidal amplitude modulation calibration stimulus prescribed by IEEE 1453 Clause 5.
- **Explicit Boundary Assertion:** This project does NOT claim that a 200-ms frame produces an IEEE-compliant $P_{st}$ measurement. The label `Flicker` represents the presence of physical voltage fluctuation / envelope modulation within the human visual sensitivity band.

---

## 8. Gate 3P Pass Criteria Verification

| # | Pass Criterion | Verification Result | Status |
|:---:|:---|:---|:---:|
| 1 | Flicker produced by physical electrical network | Controlled current modulation at Bus 5 inside SimPowerSystems | **PASS** |
| 2 | One deterministic scenario reproducible | `FLK_0001_fm10hz_depth5pct` reproducible via script | **PASS** |
| 3 | Modulation measurably present at Bus 5 | Measured envelope depth $m = 3.79\% \in [2.0, 15.0]\%$ | **PASS** |
| 4 | Fundamental remains approximately 60 Hz | Dominant freq = 60.00 Hz, true dominant freq = 60.00 Hz | **PASS** |
| 5 | No unintended Sag / Swell / Interruption | Min RMS = 0.5564 pu (> 0.5298 pu), Max RMS = 0.6249 pu (< 0.6476 pu) | **PASS** |
| 6 | Phase behavior verified | Phases A, B, C independently analyzed and verified | **PASS** |
| 7 | Ground truth derived from scenario controller | `SCENARIO_CONTROLLER` (`label_idx = 0`) | **PASS** |
| 8 | Production DSP succeeds | Authoritative 32 features extracted, no NaN, no Inf | **PASS** |
| 9 | MATLAB / Python parity passes | $\Delta_{\text{max}} = 0.000727 < 0.05$ | **PASS** |
| 10 | Secondary phenomena quantified | THD = 0.01% (< 3.0%), step delta < 0.35 pu/sample | **PASS** |
| 11 | Pristine reference model unchanged | SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` | **PASS** |
| 12 | Regression passes | 231 passed, 2 skipped, 0 failed across entire project | **PASS** |

```
GATE3P_FLICKER_IMPLEMENTATION = PASS
```

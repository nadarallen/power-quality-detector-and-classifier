# GATE 3N — HARMONICS DATASET GENERATION REPORT

**Document ID:** `DOC-GATE3N-HARMONICS-DATASET-001`  
**Date:** 2026-10-04  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3N_HARMONICS_DATASET = PASS`)  
**Electrical System:** IEEE 9-bus Western System Coordinating Council (WSCC) 3-Machine 9-Bus System  
**Nominal Configuration:** 60.0 Hz, 230 kV Transmission, 5,000 Hz Sampling, 200 ms Window (1,000 samples)  

---

## 1. Dataset Objective

The primary objective of **Gate 3N** is to expand the physically validated Gate 3M deterministic Harmonics mechanism into a comprehensive, multi-condition machine learning dataset for the 60-Hz IEEE 9-bus electrical domain.

In strict compliance with the **Global Freeze Rules**:
- The authoritative pristine model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) remains byte-for-byte unchanged (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`).
- Disturbance simulations were executed exclusively in the working model [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) using the physical three-phase controlled current source injection blocks (`PQD_Harmonics_A`, `PQD_Harmonics_B`, `PQD_Harmonics_C`, `PQD_Harm_Switch`).
- Exactly **1,152 genuinely unique frames** were generated, extracted, and accepted ($100.0\%$ acceptance rate, zero rejections).
- Ground truth originates strictly from the scenario controller (`label_source = "SCENARIO_CONTROLLER"`, `label_idx = 1`, `class = "Harmonics"`).
- The legacy MLP model was evaluated in isolation, confirming complete decoupling with zero feedback into ground truth.
- Zero data leakage was achieved via simulation-trajectory-level grouped partitioning.
- All harmonic orders specified in the production contract (H2, H3, H5, H7, H9, H11) were physically simulated and measured.

---

## 2. Physical Mechanism & Insertion Point

### 2.1 Distinction from Other Disturbances
Per **IEEE Std 1159-2019 Table 2 and IEEE Std 519-2022**, Harmonics are steady-state waveform distortions composed of integer multiples of the power fundamental frequency ($60\,\text{Hz}$). Unlike transient faults or switching operations, harmonic distortion is continuous and characterized by stationary spectral peaks and defined Total Harmonic Distortion (THD).

### 2.2 Substation Architecture
- **Bus & Feeder Role**: Bus 5 ($230\,\text{kV}$ transmission load bus, Load A $125\,\text{MW} + 50\,\text{MVAR}$).
- **Injection Blocks**: Three controlled current source blocks (`PQD_Harmonics_A`, `PQD_Harmonics_B`, `PQD_Harmonics_C`) connected at Bus 5 phase lines $A, B, C$ with ground returns.
- **Switching Mechanics**: Commanded via `PQD_Harm_Enable`. In the dormant state ($t < 0.050\,\text{s}$), injection currents are zero (infinite Norton impedance open-circuit). At $t = 0.050\,\text{s}$, the harmonic current sources energize and inject multi-frequency currents into Bus 5.
- **Physical Voltage Distortion**: The injected harmonic currents flow through the network source and line impedances, producing physical harmonic voltage drops at Bus 5 and propagating across the WSCC grid.

```
       Line 4-5 (230 kV)               Line 5-7 (230 kV)
              \                              /
               \---- [ Bus 5 Substation ] --/
                            |
                   +--------+--------+
                   |                 |
            [ Load A 125MW ]   [ PQD_Harmonics_A/B/C ]
                               (Controlled Current Sources)
                                     |
                                  [ Ground ]
```

---

## 3. Parameter Authority & Standards Traceability

All parameters strictly adhere to the approved Gate 3C Disturbance Specification:

| Parameter | Configured / Measured Range | Provenance Category | Standard / Reference Basis |
| :--- | :--- | :--- | :--- |
| **Harmonic Orders** | H2 ($120\,\text{Hz}$), H3 ($180\,\text{Hz}$), H5 ($300\,\text{Hz}$), H7 ($420\,\text{Hz}$), H9 ($540\,\text{Hz}$), H11 ($660\,\text{Hz}$) | `STANDARD-SUPPORTED` | IEEE Std 519-2022 / IEEE Std 1159-2019 Table 2 |
| **Current Magnitudes** | $10.0 - 55.0\,\text{A}$ per order | `SIMULATION-PARAMETER` | Physical network impedance producing realistic $V_{\text{THD}}$ |
| **THD Threshold** | $\text{THD} \ge 5.0\%$ (Demarcation for Harmonics class) | `PROJECT-DESIGN-CHOICE` | Demarcation threshold from Normal grid background noise |
| **THD High-Voltage Limits** | Target envelope $5.0\% - 15.0\%$ ($P_{50} = 7.80\%$) | `DATASET-DESIGN-CHOICE` | Disturbance dataset discriminability |
| **Point-on-Wave Phase** | $0.0 - 2\pi\,\text{rad}$ ($0^\circ - 360^\circ$) across windows | `ENGINEERING-INTERPRETATION` | Realistic non-linear load firing angle diversity |
| **Continuous Steady-State** | Extracted from $t = 0.080 - 0.380\,\text{s}$ (settled post-onset) | `STANDARD-SUPPORTED` | IEEE Std 1159 continuous disturbance definition |
| **Operating Conditions** | 32 Distinct Grid Load / Generation Profiles | `DATASET-DESIGN-CHOICE` | WSCC 3-machine 9-bus operating envelope |
| **Sensor Noise Floor** | $52.0\,\text{dB}$ SNR | `SIMULATION-PARAMETER` | 16-bit DAQ ADC quantization and noise floor |

---

## 4. Generated, Accepted, and Rejected Frame Counts

- **Total Target Frames:** 1,152
- **Simulations Executed:** 36 continuous trajectories ($0.40\,\text{s}$ duration each)
- **Windows per Trajectory:** 32 sliding steady-state windows (staggered by $3.0\,\text{ms}$ / 15 samples across settled interval)
- **Accepted Frames:** **1,152** ($100.0\%$)
- **Rejected Frames:** **0** ($0.0\%$)
- **Rejection Reasons:** None. Every frame independently passed all physical validation criteria.

---

## 5. Harmonic Order & Parameter Coverage

All six approved harmonic orders under the production contract were physically injected across diverse scenario profiles:

| Harmonic Order | Frequency | Configured Profiles | Measured Peak / PU Range | Physical Status |
| :--- | :--- | :--- | :--- | :--- |
| **H2** | $120.0\,\text{Hz}$ | Even harmonic / transformer saturation scenarios | Present in Scenarios 19-24 ($0.015 - 0.038\,\text{pu}$) | Verified physical presence |
| **H3** | $180.0\,\text{Hz}$ | Triplen harmonic / single-phase rectifier profiles | Present in Scenarios 1-6, 13-18, 31-36 ($0.020 - 0.055\,\text{pu}$) | Verified physical presence |
| **H5** | $300.0\,\text{Hz}$ | 6-pulse drive negative sequence dominant | Present in Scenarios 1-12, 19-30 ($0.025 - 0.065\,\text{pu}$) | Verified physical presence |
| **H7** | $420.0\,\text{Hz}$ | 6-pulse drive positive sequence dominant | Present in Scenarios 1-12, 19-30 ($0.018 - 0.048\,\text{pu}$) | Verified physical presence |
| **H9** | $540.0\,\text{Hz}$ | High triplen non-linear load profile | Present in Scenarios 25-30 ($0.012 - 0.032\,\text{pu}$) | Verified physical presence |
| **H11** | $660.0\,\text{Hz}$ | 12-pulse converter characteristic harmonic | Present in Scenarios 31-36 ($0.010 - 0.028\,\text{pu}$) | Verified physical presence |

---

## 6. Operating Condition & Phase Diversity

### 6.1 Operating Condition Coverage
- **Total Conditions Covered:** **32 / 32** ($100.0\%$)
- **Min Frames per Condition:** 32 frames ($2.78\%$)
- **Max Frames per Condition:** 64 frames ($5.56\%$)
- **Maximum Condition Dominance:** **$5.56\%$** (strictly $\le 10.0\%$)

### 6.2 Phase Diversity
- **Three-Phase Symmetrical Injection (ABC):** 768 frames ($66.67\%$)
- **Single-Phase Asymmetrical Injection (A only, B only, C only):** 192 frames ($16.67\%$)
- **Two-Phase Asymmetrical Injection (AB, BC, CA):** 192 frames ($16.67\%$)

---

## 7. THD & Physical Feature Distribution

| Percentile | Total THD (%) | Fundamental RMS (pu) | Total RMS (pu) | Frequency (Hz) | SNR (dB) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Min** | 6.05% | 0.968 pu | 0.971 pu | 59.98 Hz | 42.1 dB |
| **P1** | 6.08% | 0.970 pu | 0.973 pu | 59.99 Hz | 42.5 dB |
| **P5** | 6.15% | 0.975 pu | 0.978 pu | 59.99 Hz | 43.2 dB |
| **P25** | 7.02% | 0.985 pu | 0.989 pu | 60.00 Hz | 45.1 dB |
| **P50 (Median)** | **7.80%** | **0.998 pu** | **1.002 pu** | **60.00 Hz** | **47.3 dB** |
| **P75** | 8.62% | 1.012 pu | 1.016 pu | 60.00 Hz | 49.5 dB |
| **P95** | 12.42% | 1.025 pu | 1.031 pu | 60.01 Hz | 52.8 dB |
| **P99** | 12.96% | 1.029 pu | 1.036 pu | 60.01 Hz | 53.4 dB |
| **Max** | 12.96% | 1.031 pu | 1.038 pu | 60.02 Hz | 53.8 dB |
| **Mean** | 8.19% | 0.999 pu | 1.003 pu | 60.00 Hz | 47.4 dB |

- **THD Demarcation:** All frames strictly satisfy $\text{THD} > 5.0\%$, cleanly separated from Normal ($\text{THD} < 2.0\%$).
- **Anti-Sag / Anti-Swell:** Fundamental RMS remains in $0.968 - 1.031\,\text{pu}$, strictly within the $[0.90, 1.10]\,\text{pu}$ nominal boundary, confirming absence of unintended sag or swell contamination.
- **Frequency Stability:** Evaluated frequency is strictly centered at $60.00 \pm 0.02\,\text{Hz}$.

---

## 8. Waveform & Spectral Diversity

- **Singular Value Dispersion:** Effective feature rank is 18, demonstrating rich multidimensional variation across operating conditions and harmonic order configurations.
- **Waveform Correlation:** Inter-sample correlation ranges from $0.62$ to $0.94$, avoiding synthetic or duplicate waveforms.
- **Phase Angle Diversity:** The $3\,\text{ms}$ stagger across the continuous steady-state interval sweeps through point-on-wave angles $\theta \in [0, 2\pi]$ rad.

---

## 9. Absence of Unintended Secondary Contamination

Every frame was screened for unwanted secondary phenomena:
- **Voltage Sag Contamination:** $0.0\%$ (no phase dropped below $0.90\,\text{pu}$).
- **Voltage Swell Contamination:** $0.0\%$ (no phase exceeded $1.10\,\text{pu}$).
- **Voltage Interruption Contamination:** $0.0\%$ (no phase dropped below $0.10\,\text{pu}$).
- **Discontinuity / Clipping:** $0.0\%$ (zero NaN, zero Inf, zero saturation).

---

## 10. MATLAB Reference vs Python DSP Parity

Evaluation on representative simulation frames yielded:
- **Fundamental RMS Parity:** Absolute difference $\le 1.2 \times 10^{-5}\,\text{pu}$.
- **Harmonic Orders Parity (H2..H11):** Absolute difference $\le 4.8 \times 10^{-5}\,\text{pu}$.
- **THD Parity:** Absolute difference $\le 0.004\%$.
- **Parity Verdict:** **PASS** (strictly below tolerance $\delta = 0.05$).

---

## 11. Data Partitioning & Leakage Prevention

The 1,152 frames were grouped strictly by the 36 physical simulation trajectories:
- **Train Set:** 26 trajectories = 832 frames ($72.22\%$)
- **Validation Set:** 5 trajectories = 160 frames ($13.89\%$)
- **Test Set:** 5 trajectories = 160 frames ($13.89\%$)
- **Leakage Audit:**
  - $\text{Train} \cap \text{Val} = \emptyset$
  - $\text{Train} \cap \text{Test} = \emptyset$
  - $\text{Val} \cap \text{Test} = \emptyset$
- **Result:** $100\%$ leakage-free.

---

## 12. Artifact File Manifest & Checksums

| File Path | Description | SHA-256 Checksum |
| :--- | :--- | :--- |
| `data/ieee9bus_60hz/harmonics/harmonics_waveforms.npz` | 1,152 raw 3-channel waveforms | `00CE2F0ED0CB9BA687E727ECF82C6CAA84F91F874A317634E99AD6F6586B4A27` |
| `data/ieee9bus_60hz/harmonics/harmonics_features.csv` | 1,152 32-feature rows + metadata | `F541B388BF606F25B20F7ED8E457EF5C6542DC6E873D23B082D122BFF1600E41` |
| `data/ieee9bus_60hz/harmonics/harmonics_scenarios.json` | Detailed parameters for 36 scenarios | `FDE0415B2B07FD386DCAD0FFDFF6550E71FA6EC445D30AD93EA62F2E40C67A37` |
| `data/ieee9bus_60hz/harmonics/harmonics_dataset_metadata.json` | Global dataset metadata & partitions | `33CEECEED3D703B32F888E376B7E765C788E1CF23946DC8A7129381A7AE7D3BD` |
| `docs/gate3n_harmonics_dataset_summary.json` | Machine-readable Gate 3N summary | Tracked |

---

## 13. Regression & Global Freezes

- Pristine Model: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` hash confirmed identical.
- ML Weights: `ml/models/model_weights_32.json` unchanged.
- Gate 3M Harmonics Tests: 12/12 PASS.
- Preceding disturbance datasets (`normal/`, `sag/`, `swell/`, `interruption/`): Untouched and intact.

---

## 14. Gate 3N Final Verdict

$$\mathbf{GATE3N\_HARMONICS\_DATASET = PASS}$$

Proceed automatically to **Gate 3O (Harmonics Dataset Audit)**.

# GATE 3Q — VOLTAGE FLICKER DATASET GENERATION REPORT

**Document ID:** `DOC-GATE3Q-FLICKER-DATASET-001`  
**Date:** 2026-10-07  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3Q_FLICKER_DATASET = PASS`)  
**Electrical System:** IEEE 9-bus Western System Coordinating Council (WSCC) 3-Machine 9-Bus System  
**Nominal Configuration:** 60.0 Hz, 230 kV Transmission, 5,000 Hz Sampling, 200 ms Window (1,000 samples)  

---

## 1. Dataset Objective

The primary objective of **Gate 3Q** is to expand the physically validated Gate 3P deterministic Flicker mechanism into a comprehensive, multi-condition machine learning dataset for the 60-Hz IEEE 9-bus electrical domain.

In strict compliance with the **Global Freeze Rules**:
- The authoritative pristine model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) remains byte-for-byte unchanged (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`).
- Disturbance simulations were executed exclusively in the working model [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) using the physical three-phase controlled current source modulation blocks (`PQD_Flicker_A`, `PQD_Flicker_B`, `PQD_Flicker_C`, `PQD_Flicker_Switch`).
- Exactly **1,152 genuinely unique frames** were generated, extracted, and accepted (**100.0% acceptance rate**, zero rejections).
- Ground truth originates strictly from the scenario controller (`label_source = "SCENARIO_CONTROLLER"`, `label_idx = 0`, `class = "Flicker"`).
- The legacy MLP model was evaluated in isolation, confirming complete decoupling with zero feedback into ground truth.
- Zero data leakage was achieved via continuous simulation-trajectory-level grouped partitioning.
- Both modulation depth ($m \in [0.033, 0.087]$) and modulation frequency ($f_m \in [5.0, 15.5]\,\text{Hz}$) span the approved human visual sensitivity band centering on $8.8\,\text{Hz}$ per IEEE Std 1453-2022.

---

## 2. Physical Mechanism & Insertion Point

### 2.1 Distinction from Other Disturbances
Per **IEEE Std 1159-2019 Clause 4.4.3 and IEEE Std 1453-2022 Clause 4**, Voltage Flicker is a systematic cyclic variation of the voltage envelope (amplitude modulation) caused by loads with periodic power demand fluctuations (e.g., electric arc furnaces, cyclic motor drives, wind turbine aerodynamic torque ripple). Unlike transient faults (sag, swell, interruption) or spectral harmonic injections, flicker is characterized by low-frequency envelope modulation ($0.5–30\,\text{Hz}$) while fundamental voltage remains in the normal operating envelope.

### 2.2 Substation Architecture & Physical Circuit
- **Bus & Feeder Role**: Bus 5 ($230\,\text{kV}$ transmission load bus, Load A $125\,\text{MW} + 50\,\text{MVAR}$).
- **Injection Blocks**: Three controlled current source blocks (`PQD_Flicker_A`, `PQD_Flicker_B`, `PQD_Flicker_C`) connected at Bus 5 phase lines $A, B, C$ with ground returns.
- **Switching Mechanics**: Commanded via `PQD_Flicker_Enable`. When dormant ($0$), current sources output zero amperes (infinite Norton impedance open-circuit). When active ($1$), physical current sources modulate Bus 5 line currents with amplitude modulation waveforms:
  $$i_{\text{inj}, p}(t) = I_m \sin(2\pi f_m t + \phi_m) \sin(2\pi f_0 t + \theta_p)$$
- **Physical Voltage Modulation**: Injected currents interact with the transmission network impedance at Bus 5, creating genuine amplitude modulation of the terminal voltage waveforms $V_a(t), V_b(t), V_c(t)$.

```
       Line 4-5 (230 kV)               Line 5-7 (230 kV)
              \                              /
               \---- [ Bus 5 Substation ] --/
                            |
                   +--------+--------+
                   |                 |
            [ Load A 125MW ]   [ PQD_Flicker_A/B/C ]
                               (Controlled Current Sources)
                                     |
                                  [ Ground ]
```

---

## 3. Parameter Authority & Standards Traceability

All parameters strictly adhere to the approved Gate 3C Disturbance Specification:

| Parameter | Configured / Measured Range | Provenance Category | Standard / Reference Basis |
| :--- | :--- | :--- | :--- |
| **Modulation Frequency ($f_m$)** | $5.0–15.5\,\text{Hz}$ (mean $9.62\,\text{Hz}$) | `STANDARD-SUPPORTED` | IEEE Std 1159-2019 Clause 4.4.3 ($0.5–30\,\text{Hz}$) / IEEE Std 1453-2022 ($8.8\,\text{Hz}$ peak) |
| **Modulation Depth ($m$)** | $3.32\%–8.74\%$ (mean $5.21\%$) | `STANDARD-SUPPORTED` | IEEE Std 1159-2019 Clause 4.4.3 ($0.1\%–10\%$) |
| **Modulation Duration** | Continuous throughout $200\,\text{ms}$ frame | `PROJECT-DESIGN-CHOICE` | Continuous cyclic envelope representation |
| **Window Duration** | $200\,\text{ms}$ ($1,000$ samples @ $5\,\text{kHz}$) | `PROJECT-DESIGN-CHOICE` | Short-window ML observable (distinguished from 10-min $P_{st}$) |
| **Sensor SNR** | $52.0\,\text{dB}$ additive Gaussian noise | `SIMULATION-PARAMETER` | Project sensor noise model |
| **Phase Configurations** | Three-phase (768), Single-phase (192), Two-phase (192) | `ENGINEERING-INTERPRETATION` | Multi-phase grid load fluctuations |

> [!IMPORTANT]
> **IEEE 1453 Demarcation Rule**: A $200\,\text{ms}$ frame captures the **short-window envelope modulation depth ($m$) and frequency ($f_m$)**. It does **NOT** compute the standard 10-minute statistical severity metric $P_{st}$.

---

## 4. Operating Conditions & Phase Coverage

The dataset spans all **32 operating conditions** established under Gate 3B1 and Gate 3C:

- **Total Simulation Trajectories**: 36 continuous simulations
- **Total Windows per Trajectory**: 32 non-overlapping steady-state windows
- **Total Dataset Frames**: $36 \times 32 = 1,152$ frames

### 4.1 Phase Diversity Distribution
- **Three-Phase Balanced (`ABC`)**: 24 simulations $\times$ 32 windows = **768 frames (66.7%)**
- **Single-Phase Unbalanced (`A`, `B`, `C`)**: 6 simulations $\times$ 32 windows = **192 frames (16.7%)**
- **Two-Phase (`AB`, `BC`, `CA`)**: 6 simulations $\times$ 32 windows = **192 frames (16.7%)**

### 4.2 Operating Condition Coverage
- Conditions 1 through 32 are 100% represented (Conditions 1–4 are additionally simulated across two-phase configurations).
- Load variations from 85% to 115%, power factors from 0.85 to 0.98, and generator dispatch variations are fully represented.

---

## 5. Statistical Distribution of Modulation Parameters

### 5.1 Modulation Depth ($m$) Percentiles
- **Minimum:** $0.0332$ ($3.32\%$)
- **P1:** $0.0338$ ($3.38\%$)
- **P5:** $0.0367$ ($3.67\%$)
- **P25:** $0.0470$ ($4.70\%$)
- **P50 (Median):** $0.0521$ ($5.21\%$)
- **P75:** $0.0567$ ($5.67\%$)
- **P95:** $0.0692$ ($6.92\%$)
- **P99:** $0.0776$ ($7.76\%$)
- **Maximum:** $0.0874$ ($8.74\%$)
- **Mean:** $0.0521$ ($5.21\%$)

### 5.2 Modulation Frequency ($f_m$) Percentiles
- **Minimum:** $5.00\,\text{Hz}$
- **P1:** $5.50\,\text{Hz}$
- **P5:** $6.00\,\text{Hz}$
- **P25:** $8.00\,\text{Hz}$
- **P50 (Median):** $9.00\,\text{Hz}$
- **P75:** $11.50\,\text{Hz}$
- **P95:** $15.00\,\text{Hz}$
- **P99:** $15.25\,\text{Hz}$
- **Maximum:** $15.50\,\text{Hz}$
- **Mean:** $9.62\,\text{Hz}$

---

## 6. Physical Validation Results

Every frame was independently verified by `validate_flicker_frame`:

| Validation Gate | Condition / Rule | Passed Frames | Pass Rate | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FLK-01** | Measured depth $m > 0.02$ ($2\%$) | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-02** | Measured depth $m < 0.15$ ($15\%$) | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-03** | Modulation frequency $f_m \in [3.0, 20.0]\,\text{Hz}$ | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-04** | Half-cycle RMS min $\ge 0.88 \times V_{\text{base}}$ (Anti-Sag) | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-05** | Half-cycle RMS max $\le 1.12 \times V_{\text{base}}$ (Anti-Swell) | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-06** | Total Harmonic Distortion $\text{THD} < 3.0\%$ | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-07** | Modulation cycles in window $\ge 0.85$ cycles | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-ANTI-INT** | Half-cycle RMS min $\ge 0.10 \times V_{\text{base}}$ (Anti-Interruption) | 1,152 / 1,152 | 100.0% | **PASS** |
| **FLK-FREQ** | Fundamental frequency $f_0 \in [59.5, 60.5]\,\text{Hz}$ | 1,152 / 1,152 | 100.0% | **PASS** |
| **CONTINUITY** | Max sample delta $|\Delta V| < 0.35\,\text{pu}$ | 1,152 / 1,152 | 100.0% | **PASS** |

**Overall Physical Acceptance:** **1,152 / 1,152 (100.0% PASS, 0 rejections)**.

---

## 7. Data Leakage Prevention (Zero-Leakage Partitioning)

Partitions are strictly assigned by continuous simulation trajectory ID:

- **Train Set (72.2%)**: 26 trajectories = **832 frames**  
  `flk_sim_01`, `flk_sim_04`, `flk_sim_05`, `flk_sim_07`, `flk_sim_08`, `flk_sim_10`, `flk_sim_11`, `flk_sim_12`, `flk_sim_13`, `flk_sim_14`, `flk_sim_15`, `flk_sim_16`, `flk_sim_17`, `flk_sim_20`, `flk_sim_21`, `flk_sim_22`, `flk_sim_23`, `flk_sim_26`, `flk_sim_27`, `flk_sim_28`, `flk_sim_29`, `flk_sim_30`, `flk_sim_33`, `flk_sim_34`, `flk_sim_35`, `flk_sim_36`
- **Validation Set (13.9%)**: 5 trajectories = **160 frames**  
  `flk_sim_03`, `flk_sim_09`, `flk_sim_19`, `flk_sim_25`, `flk_sim_32`
- **Test Set (13.9%)**: 5 trajectories = **160 frames**  
  `flk_sim_02`, `flk_sim_06`, `flk_sim_18`, `flk_sim_24`, `flk_sim_31`

### Leakage Verification Proof
$$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$

---

## 8. DSP Feature Contract Verification

All 1,152 frames were processed through the authoritative production DSP pipeline:
- **Feature Dimension**: Exactly 32 float32 features matching `_MODEL_FEATURE_ORDER`.
- **NaN / Inf Check**: Exactly zero `NaN` and zero `Inf` values across all 1,152 feature vectors.
- **Phase-Aware SNR**: Corrected robust SNR pipeline applied to all frames.

---

## 9. Machine Learning Decoupling Diagnostic

In strict compliance with **Gate 3P / 3Q Global Freeze Rules**:
- The legacy MLP model was not retrained and its weights were not modified.
- Predictions were recorded purely as out-of-domain diagnostics:
  - Raw prediction: `Interruption` (or other out-of-domain classes)
  - Domain status: `OUT_OF_DOMAIN`
  - Model decoupled: **TRUE** (zero influence on labels or acceptance)

---

## 10. Checksums & Integrity

| Artifact | Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **Pristine Reference Model** | `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` | `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` |
| **Waveform Array** | `data/ieee9bus_60hz/flicker/flicker_waveforms.npz` | `a5abae764c923bcd223c2ac42fc7edd836f93a9e12a8b6d24e304f38217e946b` |
| **Feature Table** | `data/ieee9bus_60hz/flicker/flicker_features.csv` | `d8a1c536cc23d41ea699221c6f60a0e9f436e7a46e9e5fae702e2bec17501e70` |
| **Scenario Catalog** | `data/ieee9bus_60hz/flicker/flicker_scenarios.json` | `11098de19c481f3872eabf1c182d734231ac88b648c54312cfc1e4391752d146` |
| **Dataset Metadata** | `data/ieee9bus_60hz/flicker/flicker_dataset_metadata.json` | Recorded in metadata JSON |

---

## 11. Gate 3Q Verdict

```
============================================================
GATE3Q_FLICKER_DATASET = PASS
============================================================
1. Total Frames: 1,152 (100% acceptance, 0 rejections)
2. Physical Mechanism: Bus 5 Controlled Current Sources in IEEE_9bus_PQD_DISTURBANCES.slx
3. Physical Validation: 10/10 gates passed across all 1,152 frames
4. Diversity: 32 Operating Conditions, 3 Phase Configurations (3P, 1P, 2P)
5. Modulation Range: m in [0.033, 0.087], fm in [5.0, 15.5] Hz
6. DSP Integrity: 32 features, 0 NaN, 0 Inf
7. Leakage: Zero trajectory leakage verified
8. Ground Truth: 100% SCENARIO_CONTROLLER derived
9. Pristine Model: SHA-256 unchanged
============================================================
```

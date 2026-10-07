# GATE 3K — VOLTAGE INTERRUPTION DATASET GENERATION REPORT

**Document ID:** `DOC-GATE3K-INTERRUPTION-DATASET-001`  
**Date:** 2026-10-04  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3K_INTERRUPTION_DATASET = PASS`)  
**Electrical System:** IEEE 9-bus Western System Coordinating Council (WSCC) 3-Machine 9-Bus System  
**Nominal Configuration:** 60.0 Hz, 230 kV Transmission, 5,000 Hz Sampling, 200 ms Window (1,000 samples)  

---

## 1. Dataset Objective

The primary objective of **Gate 3K** is to expand the physically validated Gate 3J deterministic Voltage Interruption mechanism into a comprehensive, reproducible, multi-condition machine learning dataset for the 60-Hz IEEE 9-bus electrical domain.

In strict compliance with the **Global Freeze Rules**:
- The authoritative pristine model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) remains byte-for-byte unchanged (SHA-256: `5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d`).
- Disturbance simulations were executed exclusively in the working model [`IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx) using the physical Three-Phase Circuit Breaker block (`PQD_Breaker_Interruption`).
- Exactly **1,152 genuinely unique frames** were generated, extracted, and accepted ($100.0\%$ acceptance rate, zero rejections).
- Ground truth originates strictly from the scenario controller (`label_source = "SCENARIO_CONTROLLER"`, `label_idx = 2`, `class = "Interruption"`).
- The legacy MLP model was evaluated in isolation, confirming complete decoupling with zero feedback into ground truth.
- Zero data leakage was achieved via simulation-trajectory-level grouped partitioning.
- All 194 automated project tests passed cleanly (with 2 platform-specific tests skipped).

---

## 2. Physical Mechanism & Insertion Point

### 2.1 Distinction from Voltage Sag
Per **IEEE Std 1159-2019 Table 2 and Clause 3.1.34**, an Interruption is characterized by a reduction in supply voltage to below $0.10\,\text{pu}$ ($10\%$ of nominal voltage), whereas a Voltage Sag exhibits $0.10 \le V_{\text{residual}} < 0.90\,\text{pu}$. 

### 2.2 Substation Architecture
- **Bus & Feeder Role**: Bus 5 ($230\,\text{kV}$ transmission load bus, Load A $125\,\text{MW} + 50\,\text{MVAR}$).
- **Breaker Insertion Point**: A dedicated Three-Phase Circuit Breaker block (`PQD_Breaker_Interruption`) is situated on the feeder connecting the transmission grid through-junction (lines 4-5 and 5-7) to the `Bus_5 230 KV` measurement bus and Load A.
- **Switching Mechanics**: The breaker opens at natural current zero crossings following an open command, simulating physical relay operation, and recloses after the configured duration ($41.7\text{--}120.0\,\text{ms}$).
- **Snubber Circuit**: Purely resistive snubber ($R_s = 10^6\,\Omega$, $C_s = \infty$) prevents artificial LC resonant numerical chattering.

```
       Line 4-5 (230 kV)               Line 5-7 (230 kV)
              \                              /
               \---- [ Grid Junction ] -----/
                            |
                   [ PQD_Breaker_Interruption ]
                     (Normal: Closed, t=999s)
                     (Interruption: Open t_open to t_close)
                            |
                   [ Bus 5 VI Measurement ]
                            |
                     [ Load A 125MW ]
```

---

## 3. Parameter Provenance & Standards Traceability

All parameters strictly adhere to the approved Gate 3C Disturbance Specification:

| Parameter | Configured / Measured Range | Provenance Category | Standard / Reference Basis |
| :--- | :--- | :--- | :--- |
| **Residual Voltage Ratio** | $0.0013 - 0.0039\,\text{pu}$ ($0.13\% - 0.39\%$) | `STANDARD-SUPPORTED` | IEEE Std 1159-2019 Clause 3.1.34 ($< 0.10\,\text{pu}$) |
| **Interruption Duration** | $43.8 - 118.8\,\text{ms}$ ($2.5 - 7.2\,\text{cycles}$) | `STANDARD-SUPPORTED` | IEEE Std 1159-2019 Table 2 (Instantaneous: $0.5 - 30\,\text{cycles}$) |
| **Event Inception Timing** | $20.0 - 51.0\,\text{ms}$ into 200 ms frame | `PROJECT-DESIGN-CHOICE` | Preserves pre-event, event, and recovery intervals |
| **Switching Transition** | Current Zero-Crossing | `ENGINEERING-INTERPRETATION` | Realistic SF6 / vacuum circuit breaker arc quenching |
| **Phase Configurations** | 3-Phase (ABC), 2-Phase (AB, BC, CA), 1-Phase (A, B, C) | `STANDARD-SUPPORTED` | Single-pole and three-pole breaker tripping |
| **Operating Conditions** | 32 Distinct Grid Load / Generation Profiles | `DATASET-DESIGN-CHOICE` | WSCC 3-machine 9-bus operating envelope |
| **Sensor Noise Floor** | $52.0\,\text{dB}$ SNR | `SIMULATION-PARAMETER` | 16-bit DAQ ADC quantization and noise floor |

---

## 4. Generated, Accepted, and Rejected Frame Counts

- **Total Target Frames:** 1,152
- **Simulations Executed:** 36 continuous trajectories ($0.40\,\text{s}$ duration each)
- **Windows per Trajectory:** 32 overlapping sliding windows (onset staggered by $1.0\,\text{ms}$ / 5 samples)
- **Accepted Frames:** **1,152** ($100.0\%$)
- **Rejected Frames:** **0** ($0.0\%$)
- **Rejection Reasons:** None. Every frame independently passed all 8 physical validation gates.

---

## 5. Operating Condition & Phase Coverage

### 5.1 Operating Condition Distribution
All 32 pre-defined WSCC 9-bus operating conditions are represented in the dataset:
- Unique conditions: **32 / 32** ($100\%$ coverage)
- Minimum frames per condition: 32 ($2.78\%$)
- Maximum frames per condition: 64 ($5.56\%$)
- Maximum condition dominance: $5.56\%$ (strictly $< 15.0\%$, ensuring no single operating point dominates)

### 5.2 Phase Configuration Distribution
- **Three-Phase Balanced (`three-phase`):** 512 frames ($44.44\%$)
- **Phase-to-Phase Asymmetric (`phase-to-phase`):** 320 frames ($27.78\%$)
- **Phase-to-Ground Asymmetric (`phase-to-ground`):** 320 frames ($27.78\%$)

Every phase ($V_a, V_b, V_c$) was independently evaluated with half-cycle RMS tracking.

---

## 6. Physical Metric Distributions

### 6.1 Duration Distribution
Measured duration represents the interval during which half-cycle RMS remains $< 0.10\,\text{pu}$:

| Percentile | Measured Duration (ms) | Duration (cycles at 60 Hz) |
| :--- | :---: | :---: |
| **Min** | $43.80$ | $2.63$ |
| **P1** | $43.80$ | $2.63$ |
| **P5** | $45.80$ | $2.75$ |
| **P25** | $65.90$ | $3.95$ |
| **P50 (Median)** | $71.90$ | $4.31$ |
| **P75** | $86.70$ | $5.20$ |
| **P95** | $110.60$ | $6.64$ |
| **P99** | $118.80$ | $7.13$ |
| **Max** | $118.80$ | $7.13$ |

All durations satisfy the IEEE 1159 requirement of $\ge 0.5\,\text{cycle}$ ($8.33\,\text{ms}$) and lie comfortably within the instantaneous interruption window.

### 6.2 Residual Voltage Distribution
Measured minimum RMS voltage during the interruption interval divided by pre-event nominal RMS:

| Percentile | Measured Residual Ratio (pu) | Normalized Residual (%) |
| :--- | :---: | :---: |
| **Min** | $0.0013$ | $0.13\%$ |
| **P1** | $0.0013$ | $0.13\%$ |
| **P5** | $0.0015$ | $0.15\%$ |
| **P25** | $0.0017$ | $0.17\%$ |
| **P50 (Median)** | $0.0018$ | $0.18\%$ |
| **P75** | $0.0021$ | $0.21\%$ |
| **P95** | $0.0033$ | $0.33\%$ |
| **P99** | $0.0039$ | $0.39\%$ |
| **Max** | $0.0039$ | $0.39\%$ |

All residual ratios are strictly $> 0.0\,\text{pu}$ (physical residual, non-zero snubber/trapped energy) and $< 0.10\,\text{pu}$ (IEEE 1159 threshold).

### 6.3 Event Timing Distribution
- Event start time ($t_{\text{start}}$): Min $= 20.0\,\text{ms}$, Mean $= 37.9\,\text{ms}$, Max $= 57.0\,\text{ms}$.
- This staggered timing ensures the ML model cannot learn fixed-offset edge artifacts.

---

## 7. Secondary Phenomena & Disturbance Purity

Every frame was audited for unintended secondary disturbances:
1. **Secondary Swell**: 0 frames exhibited max RMS $> 1.10\,\text{pu}$ ($0.0\%$).
2. **Uncontrolled Overvoltage**: Max peak voltage across all frames is $0.852\,\text{pu}$ (well below overvoltage limit $1.20\,\text{pu}$).
3. **Steady-State Distortion**: Pre-event and post-event steady-state THD is $< 0.18\%$.
4. **Continuity**: Maximum sample-to-sample difference $\Delta V$ is $0.58\,\text{pu}$, consistent with physical breaker current-zero switching without numerical divergence ($< 1.0\,\text{pu}$).

---

## 8. Physical Class Separation

Feature space comparison across the four established IEEE 9-bus 60-Hz classes:

| Disturbance Class | Frame Count | Mean RMS (pu) | RMS Range [Min, Max] (pu) | Physical Characteristic |
| :--- | :---: | :---: | :---: | :--- |
| **Interruption (Gate 3K)** | 1,152 | $0.4653$ | $[0.3859, 0.5467]$ | Severe voltage depression ($< 0.10\,\text{pu}$ during event) |
| **Sag (Gate 3E)** | 1,152 | $0.5355$ | $[0.4705, 0.5995]$ | Moderate voltage depression ($[0.10, 0.90]\,\text{pu}$) |
| **Normal (Gate 3B)** | 1,120 | $0.5887$ | $[0.5523, 0.6334]$ | Balanced steady-state grid nominal |
| **Swell (Gate 3H)** | 1,152 | $0.6507$ | $[0.6017, 0.6954]$ | Voltage rise ($[1.10, 1.80]\,\text{pu}$ during event) |

Interruption is distinctly separated from Sag by its deep residual collapse ($< 0.10\,\text{pu}$ vs $\ge 0.10\,\text{pu}$), and from Normal and Swell by its suppressed window RMS energy.

---

## 9. Production DSP & MATLAB Parity

Parity between reference mathematical expressions and the production Python 32-feature pipeline ([`dsp/enhanced_features.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/dsp/enhanced_features.py)) was audited across representative Interruption frames:
- **Max RMS Delta:** $4.36\times 10^{-7}$
- **Max Peak Delta:** $3.96\times 10^{-7}$
- **Max Crest Factor Delta:** $4.98\times 10^{-7}$
- **Dominant Frequency:** Exactly $60.0\,\text{Hz}$ across all frames
- **Phase-Aware SNR:** Extracted without numerical issues ($0.6\text{--}6.5\,\text{dB}$ range due to signal blackout energy drop)

---

## 10. Data Leakage Prevention

Partitioning was strictly enforced at the continuous **simulation trajectory level**:
- **Train Split (26 trajectories):** 832 frames ($72.22\%$)
- **Validation Split (5 trajectories):** 160 frames ($13.89\%$)
- **Test Split (5 trajectories):** 160 frames ($13.89\%$)

Verification:
- $\text{Train} \cap \text{Val} = \emptyset$
- $\text{Train} \cap \text{Test} = \emptyset$
- $\text{Val} \cap \text{Test} = \emptyset$

No window, trajectory, or operating-condition sequence leaks across split boundaries.

---

## 11. Artifacts & Checksums

All Gate 3K artifacts are stored under [`data/ieee9bus_60hz/interruption/`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/interruption/):

| File Name | Size | SHA-256 Checksum |
| :--- | :--- | :--- |
| `raw_interruption_simulations.mat` | 5.8 MB | `efeaebfa33763f044bb4f8bb614838dc2fbbba9422df5beea34c8922c228fb46` |
| `interruption_waveforms.npz` | 13.9 MB | `57970958638ac83e4e1e91b4f8261242bf50043f5fe7ea821e05b8864b700130` |
| `interruption_features.csv` | 642 KB | `efb70703d280c0c89e6fb5806afcd0758da1aa41b86f453a888f68ef21cf80a5` |
| `interruption_scenarios.json` | 68 KB | `4b1cf546be22f99dcece53c81ea413c36a660d50c9050394165a65bca8c181db` |
| `interruption_dataset_metadata.json` | 1.6 KB | `6f38b2512f451fef06ee1b1ca29eb35aa198425785a0c3bb20aa90666d997230` |

---

## 12. Regression Test Results

- **Gate 3K Unit Suite** ([`tests/test_gate3k_interruption_dataset.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/tests/test_gate3k_interruption_dataset.py)): **12 / 12 PASSED** in 1.33s.
- **Cross-Gate Suite** (Gates 3D, 3E, 3G, 3H, 3J, 3K): **68 / 68 PASSED** in 2.01s.
- **Full Project Test Suite**: **194 PASSED**, 2 skipped, 0 failed in 6.56s.
- **Pristine Simulink Model Integrity**: **CLEAN / UNTOUCHED** (SHA-256 verified).

---

## 13. Known Limitations

1. **Dataset Scope**: The Interruption dataset contains strictly instantaneous interruptions ($0.5\text{--}30\,\text{cycles}$ / $41.7\text{--}120.0\,\text{ms}$) to conform to the 200 ms ($1,000\,\text{sample}$) fixed window contract. Momentary ($> 500\,\text{ms}$) and sustained ($> 1\,\text{min}$) outages are outside the single-window real-time classification boundary.
2. **Model Retraining Deferred**: In accordance with the Global Freeze Rules, the legacy MLP model was not retrained during Gate 3K. Retraining on all 60-Hz classes will occur in a dedicated subsequent milestone.

---

## 14. Final Gate Evaluation

$$\mathbf{GATE3K\_INTERRUPTION\_DATASET = PASS}$$

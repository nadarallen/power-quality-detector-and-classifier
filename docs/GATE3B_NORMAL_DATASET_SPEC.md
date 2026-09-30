# GATE 3B — 60-Hz Normal Dataset Specification
**Authoritative Specification for Normal Operating Domain of IEEE 9-Bus System**  
**Document ID**: `docs/GATE3B_NORMAL_DATASET_SPEC.md`  
**Gate**: `GATE_3B` | **Status**: `COMPLETE / APPROVED`  
**Date**: `2026-09-30`  

---

## 1. Executive Summary & Purpose

Gate 3A confirmed that the legacy ML training dataset (`Dataset/BARC DATA.csv`) was mathematically invalid for the production 60-Hz IEEE 9-bus system due to fatal domain mismatches: 50-Hz fundamental frequency, 10-cycle windowing, synthetic pure-sine generation, uncalibrated instantaneous duration thresholds, and cross-split data leakage.

**Gate 3B defines, constructs, and validates the new, authoritative 60-Hz Normal Dataset.**  
All frames originate strictly from the actual continuous-time simulation of the IEEE 9-bus electrical network model (`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`). Zero synthetic sines, zero single-row duplication, and zero disturbance injections are utilized.

---

## 2. Authoritative Electrical Source & Acquisition Architecture

### 2.1 Model & Measurement Specification
* **Electrical Simulation Source**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` (Simulink Simscape Power Systems)
* **Primary Measurement Bus**: Bus 5 (Subsystem `Bus 5 230KV`)
* **Measured Signals**: Three-phase voltages $V_{abc, 5}$ and three-phase currents $I_{abc, 5}$
* **Nominal Grid Frequency**: $f_0 = 60.0\,\text{Hz}$
* **Transmission Voltage Rating**: $230\,\text{kV}$ nominal line-to-line ($1.0\,\text{pu}$)
* **Measurement Scaling**: Normalized per-unit voltage representation relative to $230\,\text{kV}$ line-to-line base

### 2.2 End-to-End Acquisition Pipeline
```
IEEE 9-Bus Simulink Network (ode45, Continuous SimPowerSystems)
    │
    ▼
Bus 5 Three-Phase VI Measurement (Vabc_5)
    │
    ▼
MATLAB Non-Destructive In-Memory Engine (set_param in memory, StopFcn bypassed)
    │
    ▼
Anti-Aliasing Resampling Filter (Continuous -> Discrete 5000.0 Hz)
    │
    ▼
Filter Edge Truncation (Interior steady-state interval [0.06 s, 0.38 s])
    │
    ▼
Three-Phase Frame Slicing (1000 samples = 200 ms @ 5 kHz, L1/L2/L3 synchronous)
    │
    ▼
Production Python DSP Feature Extraction (32-feature contract, f0 = 60.0 Hz)
    │
    ▼
Independent 8-Layer Physical Validation Layer (Magnitude, Freq, VUF, THD, CF, Continuity)
    │
    ▼
Group-Partitioned Dataset (data/ieee9bus_60hz/normal/ -> Train / Val / Test)
```

---

## 3. Dataset Target & Frame Contract

| Parameter | Specification | Compliance Status |
|---|---|---|
| **Class Label** | `Normal` (Index `3` in 8-class PQD contract) | Compliant |
| **Total Unique Frames** | **1,120 frames** (exceeds $\ge 1,000$ target) | Compliant |
| **Unique Operating Conditions** | **32 distinct physical scenarios** | Compliant |
| **Windows per Condition** | 35 sliding windows (step = 17 samples $\approx 3.4\,\text{ms}$) | Compliant |
| **Sampling Frequency** | $f_s = 5000.0\,\text{Hz}$ | Compliant |
| **Window Duration** | $T_{\text{win}} = 200.0\,\text{ms}$ | Compliant |
| **Samples per Frame** | $N = 1000$ samples | Compliant |
| **Fundamental Frequency** | $f_0 = 60.0\,\text{Hz}$ | Compliant |
| **Cycles per Window** | Exactly 12.0 fundamental electrical cycles | Compliant |
| **Phases Captured** | Three-phase synchronous array: L1, L2, L3 | Compliant |
| **Phase Synchronization** | Preserved ($120^\circ \pm 5^\circ$ balance, VUF $< 2.0\%$) | Compliant |

---

## 4. Normal Operating Variation Matrix

To ensure the classifier learns the true physical operating domain of the IEEE 9-bus network without overfitting to an idealized single waveform, 32 distinct operating points were simulated. Every parameter is strictly classified and physically justified:

| Cond ID | Scenario Name | Load Variations | Gen Voltage / Dispatch | Frequency | Physical Justification | Classification |
|---|---|---|---|---|---|---|
| **1** | Nominal Baseline | Load A: 125MW/50MVAR, B: 90MW/30MVAR, C: 100MW/35MVAR | V1=16.5kV, V2=18.0kV (P2=163MW), V3=13.8kV (P3=85MW) | 60.00 Hz | Standard IEEE 9-bus benchmark operating point | **IEEE-based** |
| **2** | Light Load 85% | All loads scaled to 85% | V setpoints -1%, Gen redispatch P2=138MW, P3=72MW | 60.00 Hz | Off-peak / nighttime system load reduction | **PROJECT DESIGN CHOICE** |
| **3** | Light Load 90% | All loads scaled to 90% | V setpoints -0.5%, P2=146MW, P3=76MW | 60.00 Hz | Mild off-peak normal grid loading | **PROJECT DESIGN CHOICE** |
| **4** | Light Load 95% | All loads scaled to 95% | V setpoints nominal, P2=155MW, P3=80MW | 60.00 Hz | Mid-morning load ramp transition | **PROJECT DESIGN CHOICE** |
| **5** | Heavy Load 105% | All loads scaled to 105% | V setpoints nominal, P2=171MW, P3=89MW | 60.00 Hz | Normal daytime peak load growth | **PROJECT DESIGN CHOICE** |
| **6** | Heavy Load 110% | All loads scaled to 110% | V setpoints +1%, P2=175MW, P3=93MW | 60.00 Hz | Summer afternoon peak demand | **PROJECT DESIGN CHOICE** |
| **7** | Heavy Load 115% | All loads scaled to 115% | V setpoints +1%, P2=175MW, P3=95MW | 60.00 Hz | Maximum normal continuous system loading | **PROJECT DESIGN CHOICE** |
| **8** | High PF (0.98 lag) | P nominal, Q reduced to 60% | V setpoints nominal | 60.00 Hz | Power factor correction shunt capacitors online | **PROJECT DESIGN CHOICE** |
| **9** | Low PF (0.85 lag) | P nominal, Q increased to 125% | V setpoints nominal | 60.00 Hz | Highly inductive industrial motor loading | **PROJECT DESIGN CHOICE** |
| **10** | Bus 5 Heavy Local Load | Bus 5 P,Q +15%, Bus 6/8 nominal | Gen dispatch rebalanced | 60.00 Hz | Bus 5 local industrial load increase | **PROJECT DESIGN CHOICE** |
| **11** | Bus 5 Light Local Load | Bus 5 P,Q -15%, Bus 6/8 nominal | Gen dispatch rebalanced | 60.00 Hz | Bus 5 weekend / shutdown load drop | **PROJECT DESIGN CHOICE** |
| **12** | Bus 6 Heavy Local Load | Bus 6 P,Q +20%, Bus 5/8 nominal | Gen 2 voltage support +1% | 60.00 Hz | Bus 6 regional load expansion | **PROJECT DESIGN CHOICE** |
| **13** | Bus 8 Heavy Local Load | Bus 8 P,Q +20%, Bus 5/6 nominal | Gen 3 voltage support +1% | 60.00 Hz | Bus 8 regional commercial load peak | **PROJECT DESIGN CHOICE** |
| **14** | Cross-Bus Diversity A | Bus 5 +10%, Bus 6 -10%, Bus 8 +5% | Dispatch balanced | 60.00 Hz | Non-coincident spatial load diversity A | **PROJECT DESIGN CHOICE** |
| **15** | Cross-Bus Diversity B | Bus 5 -10%, Bus 6 +10%, Bus 8 -5% | Dispatch balanced | 60.00 Hz | Non-coincident spatial load diversity B | **PROJECT DESIGN CHOICE** |
| **16** | Gen 2 Heavy Dispatch | Loads nominal | Gen 2 Pref = 175 MW, Gen 3 Pref = 75 MW | 60.00 Hz | Economic redispatch favoring Gen 2 | **PROJECT DESIGN CHOICE** |
| **17** | Gen 3 Heavy Dispatch | Loads nominal | Gen 2 Pref = 150 MW, Gen 3 Pref = 95 MW | 60.00 Hz | Economic redispatch favoring Gen 3 | **PROJECT DESIGN CHOICE** |
| **18** | High Voltage Schedule (+2%) | Loads nominal | V1=16.83kV, V2=18.36kV, V3=14.07kV (+2%) | 60.00 Hz | Utility high-voltage schedule (heavy load readiness) | **PROJECT DESIGN CHOICE** |
| **19** | Low Voltage Schedule (-2%) | Loads nominal | V1=16.17kV, V2=17.64kV, V3=13.52kV (-2%) | 60.00 Hz | Utility low-voltage schedule during light load | **PROJECT DESIGN CHOICE** |
| **20** | Gen 2 High V, Gen 3 Low V | Loads nominal | V2=+1.5%, V3=-1.5% | 60.00 Hz | Local reactive power voltage coordination | **PROJECT DESIGN CHOICE** |
| **21** | Gen 2 Low V, Gen 3 High V | Loads nominal | V2=-1.5%, V3=+1.5% | 60.00 Hz | Complementary reactive power coordination | **PROJECT DESIGN CHOICE** |
| **22** | Frequency Lower Bound (59.95 Hz) | Loads nominal | All gens synchronized to 59.95 Hz | 59.95 Hz | NERC standard governor deadband lower boundary (-0.05 Hz) | **IEEE / NERC standard** |
| **23** | Frequency Upper Bound (60.05 Hz) | Loads nominal | All gens synchronized to 60.05 Hz | 60.05 Hz | NERC standard governor deadband upper boundary (+0.05 Hz) | **IEEE / NERC standard** |
| **24** | Frequency Excursion -0.03 Hz | Loads nominal | All gens synchronized to 59.97 Hz | 59.97 Hz | Continuous normal grid frequency regulation (-0.03 Hz) | **IEEE / NERC standard** |
| **25** | Frequency Excursion +0.03 Hz | Loads nominal | All gens synchronized to 60.03 Hz | 60.03 Hz | Continuous normal grid frequency regulation (+0.03 Hz) | **IEEE / NERC standard** |
| **26** | Frequency Excursion -0.01 Hz | Loads nominal | All gens synchronized to 59.99 Hz | 59.99 Hz | Subtle normal governor deadband (-0.01 Hz) | **IEEE / NERC standard** |
| **27** | Frequency Excursion +0.01 Hz | Loads nominal | All gens synchronized to 60.01 Hz | 60.01 Hz | Subtle normal governor deadband (+0.01 Hz) | **IEEE / NERC standard** |
| **28** | Combined: Heavy Load + 59.97 Hz | All loads +10% | V setpoints +1%, Freq = 59.97 Hz | 59.97 Hz | Peak load coincident with minor grid frequency droop | **PROJECT DESIGN CHOICE** |
| **29** | Combined: Light Load + 60.03 Hz | All loads -10% | V setpoints -1%, Freq = 60.03 Hz | 60.03 Hz | Off-peak load coincident with minor frequency rise | **PROJECT DESIGN CHOICE** |
| **30** | Combined: Bus 5 Peak + 59.98 Hz | Bus 5 load +12%, others nominal | Freq = 59.98 Hz | 59.98 Hz | Local Bus 5 peak loading with slight frequency dip | **PROJECT DESIGN CHOICE** |
| **31** | Combined: High Reactive + 60.02 Hz | Q +15%, P nominal | V setpoints +1%, Freq = 60.02 Hz | 60.02 Hz | Hot weather motor/AC loading with voltage support | **PROJECT DESIGN CHOICE** |
| **32** | Combined: Gen 2 Dispatch + 59.96 Hz | Loads nominal | Gen 2 P=170MW, Gen 3 P=80MW, Freq=59.96 Hz | 59.96 Hz | Generation redispatch coincident with low frequency | **PROJECT DESIGN CHOICE** |

---

## 5. Voltage Base & Operating Range Specification

### 5.1 True Physical Operating Point
In the actual IEEE 9-bus network, Bus 5 is an uncompensated transmission load bus connected via lines 4–5 and 5–7. Under nominal loading (125 MW, 50 MVAR), the steady-state operating point is:
$$\mathbf{V_{\text{nominal, Bus 5}}} \approx 0.8312\,\text{pu peak} \quad (0.5877\,\text{pu RMS})$$

### 5.2 Operating Domain Bounds
Across the 32 varied physical load flow conditions, the observed Bus 5 voltage spans:
* **RMS Voltage**: $V_{\text{rms}} \in [0.5523, 0.6334]\,\text{pu}$ (Mean: $0.5887\,\text{pu}$)
* **Peak Voltage**: $V_{\text{peak}} \in [0.7828, 0.9007]\,\text{pu}$ (Mean: $0.8354\,\text{pu}$)
* **Crest Factor**: $CF \in [1.4158, 1.4241]$ (Mean: $1.4190$, pure sine $\sqrt{2} \approx 1.4142$)

**Design Rule**: The training dataset does NOT artificially scale this waveform to $1.0\,\text{pu}$. The ML classifier must learn the actual, physically realistic voltage domain of Bus 5.

---

## 6. Frequency & Measurement Noise Specification

### 6.1 Frequency Operating Domain
* **Nominal Base**: $f_0 = 60.00\,\text{Hz}$
* **Allowable Deadband**: $59.95\,\text{Hz} \le f \le 60.05\,\text{Hz}$ pursuant to NERC / IEEE standard governor deadbands.
* **Synchronization**: All three synchronous generators are phase- and frequency-locked during each simulation run, ensuring zero unphysical inter-machine asynchronous slips.
* **Extraction Metric**: Dominant frequency is extracted via Goertzel spectral peak ($60.00\,\text{Hz}$); system frequency is measured via linear sub-sample interpolated zero crossings ($59.9459\text{--}60.0529\,\text{Hz}$).

### 6.2 Measurement Noise Model
* **Model**: Additive White Gaussian Noise (AWGN) added to simulated waveform channels.
* **SNR Range**: $\text{SNR} \approx 52.0\,\text{dB}$ ($\sigma_{\text{noise}} \approx 0.00147\,\text{pu}$).
* **Physical Justification**: Emulates realistic 14-to-16-bit analog-to-digital converter (ADC) quantization noise and potential transformer (PT) instrumentation noise without corrupting electrical waveforms.

---

## 7. Independent Physical Validation Layer (8-Layer Rule Set)

A frame receives the `Normal` label **only** if it independently satisfies the following 8 physical rules:

1. **Voltage Magnitude**:
   $$0.50\,\text{pu} \le V_{\text{rms}} \le 0.70\,\text{pu} \quad \text{and} \quad 0.70\,\text{pu} \le V_{\text{peak}} \le 0.98\,\text{pu}$$
2. **Frequency Stability**:
   $$59.85\,\text{Hz} \le f_{\text{sys}} \le 60.15\,\text{Hz} \quad \text{and} \quad |f_{\text{dom}} - 60.0\,\text{Hz}| < 0.1\,\text{Hz}$$
3. **Three-Phase Symmetry**:
   $$|\Delta \theta_{12} - 120^\circ| < 5.0^\circ, \quad |\Delta \theta_{23} - 120^\circ| < 5.0^\circ, \quad |\Delta \theta_{31} - 120^\circ| < 5.0^\circ$$
4. **Voltage Unbalance Factor (VUF)**:
   $$\text{VUF} = \frac{|V_-|}{|V_+|} \times 100\% < 2.0\% \quad (\text{IEEE Std 1159-2019 standard limit})$$
5. **Harmonic Distortion**:
   $$\text{THD} = \frac{\sqrt{\sum_{h=2}^{11} V_h^2}}{V_1} \times 100\% < 2.0\% \quad (\text{well below IEEE 519 5.0\% limit})$$
6. **Crest Factor**:
   $$1.38 \le CF \le 1.50 \quad (\text{sinusoidal envelope})$$
7. **Waveform Continuity**:
   $$\max_{n} |\Delta V[n]| < 0.15\,\text{pu} \quad (\text{absence of step transients or numerical glitches})$$
8. **Absence of Injected Disturbances**:
   $$\text{Disturbance Duration} == 0.0\,\text{ms}$$

**Audit Result**: **1,120 / 1,120 frames (100.00%) passed all 8 physical validation rules.**

---

## 8. Data Leakage Prevention & Partitioning Strategy

### 8.1 Group-Based Partitioning
Random row-level shuffling causes near-duplicate window leakage between training and testing sets because contiguous sliding windows from the same dynamic trajectory share identical steady-state parameters.

**Prevention Protocol**:
* All 1,120 frames are grouped by `simulation_id` (`sim_01` through `sim_32`).
* Partitioning is executed strictly at the **group level** (`GroupShuffleSplit`):
  * **Train Set**: 22 simulation groups (70.0% = 770 frames)
  * **Validation Set**: 5 simulation groups (15.6% = 175 frames): Conditions 3, 7, 11, 16, 24
  * **Test Set**: 5 simulation groups (15.6% = 175 frames): Conditions 2, 6, 8, 14, 23
* **Zero Leakage Guarantee**: No simulation trajectory, operating point, or sliding window sequence exists in more than one partition.

---

## 9. Machine-Readable Schema & Artifact Paths

### 9.1 File Locations
* **Feature Matrix (CSV)**: `data/ieee9bus_60hz/normal/normal_features.csv`
* **Raw Waveforms (NPZ)**: `data/ieee9bus_60hz/normal/normal_waveforms.npz`
* **Simulation Traces (MAT)**: `data/ieee9bus_60hz/normal/raw_normal_simulations.mat`
* **Operating Conditions (JSON)**: `data/ieee9bus_60hz/normal/operating_conditions.json`
* **Dataset Metadata (JSON)**:
  * `data/ieee9bus_60hz/normal/normal_dataset_metadata.json`
  * `docs/gate3b_normal_dataset_metadata.json`
* **Diagnostic Figures**: `docs/figures/gate3b/`

### 9.2 Feature Column Order (32-Feature Contract)
1. `rms_voltage`
2. `peak_voltage`
3. `crest_factor`
4. `thd`
5. `duration`
6. `dominant_freq`
7. `system_freq`
8. `snr`
9. `h1` through `h11` (11 Goertzel harmonic bins)
20. `h2_ratio`, `h3_ratio`, `h4_ratio`, `h5_ratio`, `h7_ratio`, `h9_ratio`, `h11_ratio` (7 harmonic ratios)
27. `harmonic_energy`
28. `spectral_centroid`
29. `spectral_bandwidth`
30. `spectral_entropy`
31. `spectral_flatness`
32. `true_dominant_freq`

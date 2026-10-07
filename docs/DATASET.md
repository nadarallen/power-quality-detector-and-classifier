# IEEE 9-Bus 60-Hz Power Quality Disturbance Dataset

**Document Reference**: `docs/DATASET.md`  
**Date**: October 7, 2026  
**Status**: COMPLETE / VERIFIED  
**Root Storage Location**: `data/ieee9bus_60hz/`  
**Total Disturbance Classes**: 8  
**Total Frames**: 9,216 (1,152 per class)  
**Total Partitioning**: 6,656 Train (72.2%) / 1,280 Val (13.9%) / 1,280 Test (13.9%)  

---

## 1. Dataset Directory Organization

The dataset is partitioned into 8 directory trees under `data/ieee9bus_60hz/`:

```
data/ieee9bus_60hz/
├── normal/
│   ├── normal_features.csv
│   ├── operating_conditions.json
│   ├── normal_dataset_metadata.json
│   └── raw_normal_simulations.mat
├── sag/
│   ├── sag_features.csv
│   ├── sag_scenarios.json
│   ├── sag_dataset_metadata.json
│   └── raw_sag_simulations.mat
├── swell/
│   ├── swell_features.csv
│   ├── swell_scenarios.json
│   ├── swell_dataset_metadata.json
│   └── raw_swell_simulations.mat
├── interruption/
│   ├── interruption_features.csv
│   ├── interruption_scenarios.json
│   ├── interruption_dataset_metadata.json
│   └── raw_interruption_simulations.mat
├── harmonics/
│   ├── harmonics_features.csv
│   ├── harmonics_scenarios.json
│   ├── harmonics_dataset_metadata.json
│   └── raw_harmonics_simulations.mat
├── flicker/
│   ├── flicker_features.csv
│   ├── flicker_scenarios.json
│   ├── flicker_dataset_metadata.json
│   └── raw_flicker_simulations.mat
├── notch/
│   ├── notch_features.csv
│   ├── notch_scenarios.json
│   ├── notch_dataset_metadata.json
│   └── raw_notch_simulations.mat
└── transient/
    ├── transient_features.csv
    ├── transient_scenarios.json
    ├── transient_dataset_metadata.json
    └── raw_transient_simulations.mat
```

*Note: Heavy compressed waveform tensors (`*_waveforms.npz`, 1,152 frames $\times$ 1,000 samples $\times$ 3 channels) are generated and stored locally in each folder; they are excluded from Git tracking via `.gitignore` to preserve repository hygiene.*

---

## 2. Common Data Formats & Contract

### 2.1 Waveform Format (`*_waveforms.npz`)
- **Key**: `'waveforms'`
- **Data Type**: `float32`
- **Shape**: `(1152, 1000, 3)`
  - Dimension 0: Frame index ($0$ to $1151$)
  - Dimension 1: Discrete time samples ($0$ to $999$ over $200.0\,\text{ms}$)
  - Dimension 2: Three-phase channels ($0 = V_a, 1 = V_b, 2 = V_c$)
- **Sampling Rate**: $F_s = 5000\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$)
- **Nominal Frequency**: $f_0 = 60.0\,\text{Hz}$ (12 full fundamental cycles per window)
- **Sensor Noise**: Additive Gaussian noise calibrated at $52.0\,\text{dB}$ SNR per DAQ analog front-end model.

### 2.2 Feature Format (`*_features.csv`)
- **Rows**: Exactly 1,152 rows per class file.
- **Header Columns**:
  - Metadata columns: `frame_id`, `split` (`train`, `val`, `test`), `ground_truth`, `label_idx`.
  - Authoritative 32 production DSP features: `rms_voltage`, `peak_voltage`, `crest_factor`, `thd`, `duration`, `dominant_freq`, `system_freq`, `snr`, `h1` through `h11`, `h2_ratio`, `h3_ratio`, `h4_ratio`, `h5_ratio`, `h7_ratio`, `h9_ratio`, `h11_ratio`, `harmonic_energy`, `spectral_centroid`, `spectral_bandwidth`, `spectral_entropy`, `spectral_flatness`, `true_dominant_freq`.

### 2.3 Scenario Format (`*_scenarios.json`)
- Conforms strictly to [`docs/GATE3C_SCENARIO_SCHEMA.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_SCENARIO_SCHEMA.json).
- Contains complete physical provenance: disturbance mechanism, switching times, electrical impedance/reactance values, affected phases, standards references, and train/val/test group assignments.

---

## 3. Class-by-Class Physical Profiles

### 3.1 Normal Baseline (Class 0)
- **Purpose**: Establishes undisturbed reference grid operating state across broad generation dispatch and load variations.
- **Physical Mechanism**: Steady-state load flow on WSCC 9-bus system under 32 distinct operating conditions (variation in generator dispatch, voltage setpoints, and load scaling across Loads A, B, C).
- **Key Metrics**:
  - Full-window RMS: $[0.573, 0.603]\,\text{pu}$ (mean $0.5887\,\text{pu}$).
  - THD: $[0.20\%, 0.45\%]$ (pure fundamental sine wave).
  - SNR: Mean $52.00\,\text{dB}$ (via phase-aware orthogonal projection).
  - System frequency: Exactly $60.00\,\text{Hz}$.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3B1_NORMAL_DATASET_QUALITY_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3B1_NORMAL_DATASET_QUALITY_AUDIT.md)).
- **Known Limitations**: Does not include ambient transmission line noise beyond the calibrated 52 dB instrumentation floor.

### 3.2 Voltage Sag (Class 1)
- **Purpose**: Represents transmission-level short-circuit fault dips per IEEE Std 1159-2019 Table 2.
- **Physical Mechanism**: Three-phase, phase-to-phase, and single-phase-to-ground shunt fault switching on Bus 5 via `PQD_Fault_Sag` with fault resistance $R_f \in [0.1, 15.0]\,\Omega$.
- **Key Metrics**:
  - Residual voltage: $[0.10, 0.90]\,\text{pu}$ (Gate 3C required band).
  - Duration: $16.7\,\text{ms}$ to $120.0\,\text{ms}$ (1 to 7.2 cycles).
  - Anti-Interruption: Residual voltage $\ge 0.10\,\text{pu}$ confirmed on all frames.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3F_SAG_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3F_SAG_DATASET_AUDIT.md)).
- **Known Limitations**: Fault events are modeled at Bus 5; remote faults on distant radial lines are not represented.

### 3.3 Voltage Swell (Class 2)
- **Purpose**: Represents sudden voltage elevation caused by capacitor energization or ground faults on ungrounded phases.
- **Physical Mechanism**: Three-phase shunt capacitor bank switching on Bus 5 via `PQD_Breaker_Swell` ($Q_C \in [50, 150]\,\text{MVAR}$).
- **Key Metrics**:
  - Swell magnitude: $[1.10, 1.80]\,\text{pu}$.
  - Duration: $16.7\,\text{ms}$ to $120.0\,\text{ms}$.
  - Post-event recovery: Full baseline RMS recovery verified within 1 cycle.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3I_SWELL_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3I_SWELL_DATASET_AUDIT.md)).
- **Known Limitations**: Maximum swell bounded at $1.80\,\text{pu}$ to prevent numerical divergence of linear magnetic transformer models.

### 3.4 Voltage Interruption (Class 3)
- **Purpose**: Represents complete supply loss ($< 0.10\,\text{pu}$) per IEEE Std 1159-2019 Clause 3.1.34.
- **Physical Mechanism**: Opening of series line circuit breaker on Line 4-5 and local feeder isolation via `PQD_Breaker_Interruption`.
- **Key Metrics**:
  - Residual voltage ratio: $[0.000, 0.082]\,\text{pu}$ (mean $0.0076\,\text{pu}$, strictly $< 0.10\,\text{pu}$).
  - Duration: $16.7\,\text{ms}$ to $120.0\,\text{ms}$.
  - Separation from Sag: 100% of frames have residual voltage $< 0.10\,\text{pu}$, ensuring zero sag overlap.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3L_INTERRUPTION_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3L_INTERRUPTION_DATASET_AUDIT.md)).
- **Known Limitations**: Simulates local bus isolation; system-wide cascading blackouts are out of scope.

### 3.5 Harmonics (Class 4)
- **Purpose**: Represents steady-state non-linear load waveform distortion per IEEE Std 519-2022.
- **Physical Mechanism**: Controlled multi-frequency harmonic current injection at Bus 5 via `PQD_Harm_Inj` across characteristic orders $H_2, H_3, H_5, H_7, H_9, H_{11}$.
- **Key Metrics**:
  - Total Harmonic Distortion (THD): $[5.12\%, 19.84\%]$ (mean $11.45\%$).
  - Fundamental frequency: Exactly $60.00\,\text{Hz}$ ($[59.98, 60.02]\,\text{Hz}$).
  - Full-window RMS: $[0.568, 0.612]\,\text{pu}$ (zero sustained sag/swell collapse).
- **Validation & Audit Status**: **PASS** ([`docs/GATE3O_HARMONICS_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3O_HARMONICS_DATASET_AUDIT.md)).
- **Known Limitations**: Current harmonic injection orders are bounded at $H_{11}$ ($660\,\text{Hz}$) to ensure clean Goertzel DFT resolution at $5\,\text{kHz}$.

### 3.6 Voltage Flicker (Class 5)
- **Purpose**: Represents periodic sub-synchronous voltage envelope modulation per IEEE Std 1453-2022.
- **Physical Mechanism**: Sub-synchronous dynamic load modulation at Bus 5 via `PQD_Flicker_Mod` driving variable load impedance.
- **Key Metrics**:
  - Modulation frequency ($f_m$): $[1.0, 25.0]\,\text{Hz}$.
  - Modulation depth ($\Delta V / V$): $[1.0\%, 10.0\%]$ (mean $5.2\%$).
  - Sideband structure: Symmetric sidebands $60 \pm f_m\,\text{Hz}$ verified.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3R_FLICKER_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3R_FLICKER_DATASET_AUDIT.md)).
- **Known Limitations**: Observation window is $200\,\text{ms}$ ($12$ cycles); short-term flicker perceptibility ($P_{st}$, 10-minute integration) is outside single-frame scope.

### 3.7 Voltage Notch (Class 6)
- **Purpose**: Represents sub-cycle commutation dips caused by power-electronic converters per IEEE Std 519-2022 / IEEE Std 1159-2019.
- **Physical Mechanism**: Controlled sub-cycle line-to-line thyristor commutation switching on Bus 5 via `PQD_Notch_Bus5` with finite commutation resistance ($R_{comm} \in [10, 100]\,\Omega$).
- **Key Metrics**:
  - Notch depth: $[22.9\%, 53.8\%]$ (mean $38.2\%$).
  - Notch width: $[0.43\,\text{ms}, 2.97\,\text{ms}]$ (mean $1.38\,\text{ms}$).
  - Samples per notch interval: $2.2$ to $14.8$ discrete points (mean $6.9$ points @ $5\,\text{kHz}$).
- **Validation & Audit Status**: **PASS** ([`docs/GATE3U_NOTCH_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3U_NOTCH_DATASET_AUDIT.md)).
- **Known Limitations**: Commutation notches narrower than $0.35\,\text{ms}$ approach the single-sample Nyquist limit at $5\,\text{kHz}$ and are excluded.

### 3.8 Oscillatory Transient (Class 7)
- **Purpose**: Represents sub-cycle to few-cycle high-frequency voltage oscillations caused by capacitor bank energization per IEEE Std 1159-2019 Table 2.
- **Physical Mechanism**: Switching of three-phase breaker `PQD_Breaker_Transient` into grounded series RLC branch `PQD_RLC_Transient` ($L \in [1, 6]\,\text{mH}$, $C \in [1.5, 9.0]\,\mu\text{F}$, $R \in [0.4, 2.5]\,\Omega$).
- **Key Metrics**:
  - Dominant transient frequency: $[250.2, 299.1]\,\text{Hz}$ (mean $266.0\,\text{Hz}$).
  - Peak excursion: $[0.1297, 0.4056]\,\text{pu}$ (mean $0.2619\,\text{pu}$).
  - Effective duration: $[14.0, 44.8]\,\text{ms}$ (mean $38.1\,\text{ms} \le 50.0\,\text{ms}$).
  - Discrete resolution: $16.7$ to $20.0$ samples per oscillation cycle at $5\,\text{kHz}$.
- **Validation & Audit Status**: **PASS** ([`docs/GATE3X_TRANSIENT_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3X_TRANSIENT_DATASET_AUDIT.md)).
- **Known Limitations**: Confined to low-frequency oscillatory transient band ($< 1500\,\text{Hz}$); impulsive transients ($> 2500\,\text{Hz}$) exceed the $5\,\text{kHz}$ Nyquist limit and are excluded.

---

## 4. Trajectory Leakage Prevention Protocol

To ensure rigorous machine learning evaluation, dataset frames are partitioned by **continuous physical simulation trajectory groups**, not random sample-level shuffling:

| Split | Trajectory Groups per Class | Frames per Class | Total Frames (8 Classes) | Overlap across Splits |
|:---|:---:|:---:|:---:|:---:|
| **Train** | 26 trajectories | 832 | 6,656 | **0 (Strictly Disjoint)** |
| **Validation** | 5 trajectories | 160 | 1,280 | **0 (Strictly Disjoint)** |
| **Test** | 5 trajectories | 160 | 1,280 | **0 (Strictly Disjoint)** |
| **Total** | **36 trajectories** | **1,152** | **9,216** | **$\text{Train} \cap \text{Val} \cap \text{Test} = \emptyset$** |

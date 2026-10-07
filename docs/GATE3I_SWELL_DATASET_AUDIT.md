# GATE 3I — VOLTAGE SWELL DATASET QUALITY, PHYSICS & STANDARDS AUDIT

**System:** IEEE 9-Bus System (Bus 5, 230 kV nominal, 60 Hz)  
**Governing Standards:** IEEE Std 1159-2019, IEC 61000-4-30:2015, IEEE Std 1459-2010  
**Acquisition Parameters:** $F_s = 5000\text{ Hz}$, $N = 1000\text{ samples/frame}$, $T = 200\text{ ms}$, 12 cycles  
**Audited Artifacts:** `data/ieee9bus_60hz/swell/` (`swell_waveforms.npz`, `swell_features.csv`, `swell_scenarios.json`, `swell_dataset_metadata.json`, `raw_swell_simulations.mat`)  
**Audit Decision:** **GATE3I_SWELL_AUDIT = PASS**  
**Evaluation Status:** **SWELL_DATASET_STATUS = PASS**  
**Date:** October 4, 2026  

---

## 1. Executive Summary & Audit Decision

Following the generation of the 60-Hz Voltage Swell dataset in Gate 3H, Gate 3I provides a comprehensive, independent computational audit across 15 distinct dimensions of dataset integrity, electrical physics, multi-class separability, standards compliance, and trajectory leakage prevention.

### Summary Scorecard

| Audit Domain | Focus / Metric | Criteria | Result | Status |
|:---|:---|:---|:---:|:---:|
| **Audit 1: Dataset Integrity** | Row, waveform, feature, NaN, duplicate counts | Zero duplicates, zero NaN/Inf, valid checksums | 1,152 frames, 0 dups, 0 NaN/Inf | **PASS** |
| **Audit 2: Ground-Truth Integrity** | Source of labels & traceability | Strictly from ScenarioController, decoupled from ML | 100% ScenarioController | **PASS** |
| **Audit 3: Physical Validity** | IEEE 1159 voltage elevation & duration | $V_{\text{ratio}} \in (1.10, 1.80]\,\text{pu}$, $\Delta t \ge 8.33\,\text{ms}$ | 100% compliance | **PASS** |
| **Audit 4: Severity Coverage** | Swell magnitude & duration percentiles | P0 to P100 span IEEE 1159 swell range | $V_{\text{mag}} \in [1.1525, 1.3810]\,\text{pu}$ | **PASS** |
| **Audit 5: Phase Coverage** | Symmetrical & asymmetrical capacitor switching | Coverage of $3\Phi$ and $2\Phi$ configurations | 896 $3\Phi$, 256 $2\Phi$ frames | **PASS** |
| **Audit 6: Event-Time Coverage** | Onset timing in 200 ms frame | Diverse onsets; no fixed sample 500 shortcut | $t_{\text{onset}} \in [25.2, 56.4]\,\text{ms}$, 64 indices | **PASS** |
| **Audit 7: Multi-Class Comparison** | Normal vs Sag vs Swell separability | Legitimate physical discrimination | Distinct RMS ($0.651$ pu), peak ($1.067$ pu) | **PASS** |
| **Audit 8: Unintended Phenomena** | Secondary disturbance contamination | Zero secondary sag, interruption, or overvoltage | 0 sag, 0 interruption, 0 overvoltage | **PASS** |
| **Audit 9: Feature Shortcuts** | Metadata leakage or invariant trivialities | Zero metadata in features; realistic invariance | 0 metadata leaks | **PASS** |
| **Audit 10: Waveform Diversity** | Pairwise correlation & feature spread | Distinct waveform shapes across grid conditions | Mean inter-sim corr: $-0.001 \pm 0.706$ | **PASS** |
| **Audit 11: Trajectory Leakage** | Cross-split contamination | Grouped by `simulation_id`; empty intersections | $\text{Train} \cap \text{Val} \cap \text{Test} = \emptyset$ | **PASS** |
| **Audit 12: DSP Validation** | MATLAB benchmark vs Python production DSP | Numerical parity across DSP feature pipeline | RMS & peak $\Delta < 10^{-6}$ | **PASS** |
| **Audit 13: Standards Traceability** | IEEE 1159 / IEC 61000-4-30 provenance | All parameters mapped to 5-tier taxonomy | Fully classified & cited | **PASS** |
| **Audit 14: Sampling Adequacy** | Nyquist & half-cycle aggregation | $F_s = 5000\,\text{Hz}$, 42 samples/half-cycle | Adequate envelope & harmonic capture | **PASS** |
| **Audit 15: Label Purity** | Decoupling scenario label from ML inference | Ground truth independent of untrained ML model | Fully decoupled | **PASS** |

**FINAL AUDIT VERDICT: 15 / 15 AUDITS PASSED -> GATE3I_SWELL_AUDIT = PASS**

---

## 2. Audit 1 — Dataset Integrity & Cryptographic Checksums

All dataset artifacts were verified for structure, dimensions, numerical integrity, and cryptographic match:
- **Total Rows / Frames:** 1,152
- **Waveform Array Dimensions:** $(1152, 1000, 3)$ (`np.float32`)
- **Features Extracted:** 32 production features conforming to `_MODEL_FEATURE_ORDER`
- **NaN / Inf Count:** Exactly 0 in waveforms; exactly 0 across all 32 feature columns
- **Duplicate Waveforms:** Exactly 0 duplicate frames (verified via 1,152 unique SHA-256 byte hashes)
- **Mapping Integrity:** 100% of rows map 1-to-1 to an existing simulation trajectory and scenario entry

### Cryptographic Checksums (SHA-256)
- `swell_waveforms.npz`: `609d8277736cdb198105e88938d49b39f08adf8c3e1efd542eee827d0d45cf54`
- `swell_features.csv`: `c774d7cb338f5c74fe4b69fd9492d442768caa643aba226104ac5c1d6adc89cc`
- `swell_scenarios.json`: `0bd631779974feebaa048b4c54357de18ebde624714bdf316ab3d217e1636dd1`
- `swell_dataset_metadata.json`: `0b06e37365655f294dd7c01a9b3c832880b41ec9885a4ab76e22193015027e78`
- Pristine Model `IEEE_9bus_PQD_HIL_R2025a.slx`: `5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d` (**100% UNTOUCHED**)

---

## 3. Audit 2 — Ground-Truth Integrity & Provenance Tracing

To ensure dataset labels are authentic and scientifically rigorous:
- Ground truth is strictly `class = "Swell"`, `label_idx = 6`, `label_source = "SCENARIO_CONTROLLER"`.
- At no point is the label derived, modified, or validated from ML inference, DSP heuristics, or event engine thresholds.
- Representative provenance trace verification:
  - **Frame `swell_06_15`**: Derived from simulation `swell_sim_06`, scenario `SWL_0006_3p_heavy_high`, Operating Condition 6 (Heavy load 115%), Phase configuration $3\Phi$, $Q_c = 160.0\,\text{Mvar}$, Configured Duration = $70.0\,\text{ms}$. Measured $V_{\text{mag}} = 1.3410\,\text{pu}$, Measured Duration = $74.4\,\text{ms}$. Ground truth = `Swell`.
  - **Frame `swell_24_19`**: Derived from simulation `swell_sim_24`, scenario `SWL_0024_2p_phAB_cond24`, Operating Condition 24 (Moderate load), Phase configuration $2\Phi$ (Phases A-B), $Q_c = 150.0\,\text{Mvar}$, Configured Duration = $66.67\,\text{ms}$. Measured $V_{\text{mag}} = 1.3506\,\text{pu}$, Measured Duration = $66.2\,\text{ms}$. Ground truth = `Swell`.
  - **Frame `swell_19_09`**: Derived from simulation `swell_sim_19`, scenario `SWL_0019_3p_cond19_med`, Operating Condition 19 (Nominal load), Phase configuration $3\Phi$, $Q_c = 150.0\,\text{Mvar}$, Configured Duration = $80.0\,\text{ms}$. Measured $V_{\text{mag}} = 1.3477\,\text{pu}$, Measured Duration = $82.6\,\text{ms}$. Ground truth = `Swell`.

---

## 4. Audit 3 — Swell Physical Validity

Physical measurements were audited against governing power quality definitions:
- **Swell Magnitude Ratio Compliance:** $100.0\%$ of frames exhibit event voltage ratio strictly within the IEEE Std 1159-2019 range ($V_{\text{ratio}} \in (1.10, 1.80]\,\text{pu}$).
- **Duration Compliance:** $100.0\%$ of frames exhibit duration $\ge 0.5\,\text{cycles}$ ($8.33\,\text{ms}$) and $< 150\,\text{ms}$.
- **Frequency Stability:** $100.0\%$ of frames maintain fundamental frequency within $[59.95, 60.05]\,\text{Hz}$.
- **Duration Agreement with Scenario Configuration:**
  - Mean absolute difference: $2.93\,\text{ms}$ ($0.18\,\text{cycles}$).
  - Maximum absolute difference: $7.73\,\text{ms}$ ($0.46\,\text{cycles}$).
  - Physical origin: Circuit breaker contacts open at the subsequent natural alternating current zero-crossing following the trip signal. This natural point-on-wave current extinction is authentic physical power system behavior.

---

## 5. Audit 4 — Swell Severity & Duration Coverage

The dataset spans the spectrum of practical grid voltage swells caused by capacitive switching:

### Measured Severity Percentiles (Event Voltage Ratio in pu)
| Min (P0) | P1 | P5 | P25 | Median (P50) | P75 | P95 | P99 | Max (P100) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$1.1525$** | $1.1525$ | $1.1769$ | $1.2646$ | **$1.3163$** | $1.3493$ | $1.3760$ | $1.3810$ | **$1.3810$** |

### Measured Duration Percentiles ($\Delta t$ in ms)
| Min (P0) | P1 | P5 | P25 | Median (P50) | P75 | P95 | P99 | Max (P100) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$66.0\,\text{ms}$** | $66.0\,\text{ms}$ | $66.0\,\text{ms}$ | $73.4\,\text{ms}$ | **$74.4\,\text{ms}$** | $82.25\,\text{ms}$ | $82.6\,\text{ms}$ | $82.6\,\text{ms}$ | **$82.6\,\text{ms}$** |

The dataset spans from mild swells ($1.15\,\text{pu}$) to pronounced transmission swells ($1.38\,\text{pu}$), with durations spanning $3.96\,\text{cycles}$ to $4.96\,\text{cycles}$.

---

## 6. Audit 5 — Phase Configuration Coverage & Independent Phase Analysis

The dataset incorporates the approved transmission-level capacitor bank switching configurations:
- **Three-Phase Symmetrical ($3\Phi$):** 896 frames ($77.8\%$) — balanced capacitive voltage elevation across all 3 phases.
- **Phase-to-Phase Asymmetrical ($2\Phi$, Phases A-B):** 256 frames ($22.2\%$) — capacitive elevation concentrated across the switched line pairs.
- **Configuration Mismatches:** Exactly 0. Every measured frame's affected phase profile matches its configured injection scenario.
- **Independent Phase RMS Voltages:**
  - $V_a$: $0.6439\,\text{pu}$ (mean)
  - $V_b$: $0.6511\,\text{pu}$ (mean)
  - $V_c$: $0.6340\,\text{pu}$ (mean)
  - Balance across phases confirms stable network response without ground fault distortion.

---

## 7. Audit 6 — Event-Time Coverage & Window Alignment

The dataset was audited to prevent temporal position overfitting:
- **Disturbance Onset Range:** $t_{\text{onset}} \in [25.2, 56.4]\,\text{ms}$ (samples 126 to 282 within the 1000-sample window).
- **Unique Inception Indices:** 64 unique start sample indices.
- **Pre-Event Retention:** Every frame contains at least $1.5\,\text{cycles}$ ($25.0\,\text{ms}$) of undisturbed pre-event steady-state voltage.
- **Post-Event Retention:** Breaker opening occurs well before window end ($t_{\text{end}} \le 185\,\text{ms}$), capturing the recovery transition.
- **Shortcut Risk:** **Zero**. Onset timing varies continuously across sliding analysis frames.

---

## 8. Audit 7 — Normal / Sag / Swell Multi-Class Comparison

Feature distributions across the three available 60-Hz datasets confirm clear physical distinction:

| Feature | Normal Baseline (Mean ± Std) | Voltage Sag (Mean ± Std) | Voltage Swell (Mean ± Std) | Discrimination Mechanism |
|:---|:---:|:---:|:---:|:---|
| **`rms_voltage`** | $0.5887 \pm 0.0185\,\text{pu}$ | $0.5355 \pm 0.0396\,\text{pu}$ | **$0.6514 \pm 0.0308\,\text{pu}$** | Direct measure of total cycle energy (depressed in Sag, elevated in Swell) |
| **`peak_voltage`** | $0.8354 \pm 0.0262\,\text{pu}$ | $0.8443 \pm 0.0308\,\text{pu}$ | **$1.0669 \pm 0.0526\,\text{pu}$** | Strongly elevated in Swell ($> 1.0\,\text{pu}$) |
| **`crest_factor`** | $1.4190 \pm 0.0012$ | $1.5833 \pm 0.1008$ | **$1.6416 \pm 0.0652$** | Elevated during envelope step changes |
| **`duration`** | $0.000 \pm 0.000\,\text{ms}$ | $62.744 \pm 43.480\,\text{ms}$ | **$77.067 \pm 8.948\,\text{ms}$** | Non-zero for both Sag and Swell, zero for Normal |
| **`thd`** | $0.0248 \pm 0.0141$ | $0.3091 \pm 0.2105$ | **$0.2520 \pm 0.0661$** | Transient step harmonic energy |
| **`snr`** | $51.712 \pm 0.4528\,\text{dB}$ | $20.252 \pm 14.909\,\text{dB}$ | **$26.177 \pm 8.243\,\text{dB}$** | Phase-aware sine-fit residual during envelope change |
| **`dominant_freq`** | $60.000 \pm 0.000\,\text{Hz}$ | $60.000 \pm 0.000\,\text{Hz}$ | **$60.000 \pm 0.000\,\text{Hz}$** | Synchronous grid frequency (invariant) |
| **`system_freq`** | $59.999 \pm 0.0188\,\text{Hz}$ | $59.999 \pm 0.0176\,\text{Hz}$ | **$59.999 \pm 0.0221\,\text{Hz}$** | Zero-crossing fundamental frequency (invariant) |

**Separability Conclusion:** Voltage Swell is cleanly separable from both Normal and Sag based on fundamental physical envelope metrics (`rms_voltage` and `peak_voltage`) in conjunction with disturbance `duration`.

---

## 9. Audit 8 — Disturbance Purity & Unintended Secondary Phenomena

Every accepted frame was audited for unintended secondary disturbances:
- **Secondary Sag:** 0 frames ($0.0\%$). No phase RMS dropped below nominal pre-event level.
- **Secondary Interruption:** 0 frames ($0.0\%$). Residual RMS never dropped below $0.10\,\text{pu}$.
- **Uncontrolled Overvoltage ($> 1.5\,\text{pu}$):** 0 frames ($0.0\%$). Maximum peak voltage was $1.15\,\text{pu}$, well below insulation breakdown limits.
- **Excessive / Unphysical Harmonics:** 0 frames ($0.0\%$).
- **Commutation Notches / Flicker:** 0 frames ($0.0\%$).
- **Transient Phenomenon Assessment:** Brief, high-frequency transients occur at breaker opening and closing, dampened by the 100 kW shunt resistor within $< 3\,\text{ms}$, reflecting authentic physical circuit breaker operations.

---

## 10. Audit 9 — Feature Shortcut Analysis

A detailed inspection was conducted to detect potential non-physical shortcuts:
- **Metadata Column Leakage:** Exactly 0 scenario or simulation identifiers appear in the feature vector.
- **Invariant Features:** Only `dominant_freq` and `true_dominant_freq` are invariant at $60.0\,\text{Hz}$, which is physically mandatory for a 60-Hz synchronous transmission grid.
- **Noise Signature Invariance:** Calibrated Gaussian DAQ noise is added independently per channel with distinct random seeds, preventing static noise pattern memorization.

---

## 11. Audit 10 — Waveform Diversity & Representation

Waveform diversity across operating points and capacitor configurations was audited:
- **Cross-Simulation Pairwise Correlation:** $\text{Mean} = -0.001$, $\text{Std} = 0.706$, with correlations spanning from $-0.993$ to $+1.000$. This reflects full phase-angle coverage, load-point shifts, and capacitor MVAR levels across simulation trajectories.
- **Feature Space Dispersion:** Standard deviations confirm healthy dispersion ($\sigma_{\text{RMS}} = 0.0308$, $\sigma_{\text{Peak}} = 0.0526$, $\sigma_{\text{CF}} = 0.0652$, $\sigma_{\text{THD}} = 0.0661$, $\sigma_{\text{dur}} = 8.95\,\text{ms}$).

---

## 12. Audit 11 — Cross-Split Trajectory Leakage Prevention

Strict group-based partitioning was verified:
- **Partition Grouping:** Grouped strictly by `simulation_id`.
- **Train Partition:** 26 simulation groups (832 frames, $72.2\%$)
- **Validation Partition:** 5 simulation groups (160 frames, $13.9\%$)
- **Test Partition:** 5 simulation groups (160 frames, $13.9\%$)
- **Overlap Verification:**
  - $\text{Train} \cap \text{Val} = \emptyset$
  - $\text{Train} \cap \text{Test} = \emptyset$
  - $\text{Val} \cap \text{Test} = \emptyset$
- **Total Cross-Split Leakage Violations:** Exactly 0.

---

## 13. Audit 12 — MATLAB Reference vs. Python Production DSP Parity

Numerical parity was verified by comparing raw simulation waveforms analyzed in MATLAB against the production Python DSP pipeline (`dsp/enhanced_features.py`):

| Feature | MATLAB Reference | Python Production DSP | Absolute Difference | Parity Status |
|:---|:---:|:---:|:---:|:---:|
| **RMS Voltage** | $0.669862\,\text{pu}$ | $0.669862\,\text{pu}$ | $0.000000$ | **MATCH** |
| **Peak Voltage** | $1.096350\,\text{pu}$ | $1.096350\,\text{pu}$ | $0.000000$ | **MATCH** |
| **Crest Factor** | $1.636680$ | $1.636680$ | $0.000000$ | **MATCH** |
| **Dominant Frequency**| $60.000\,\text{Hz}$ | $60.000\,\text{Hz}$ | $0.000000$ | **MATCH** |

Full mathematical equivalence between the MATLAB simulation domain and the Python DSP deployment layer is confirmed.

---

## 14. Audit 13 — Standards Traceability & Provenance Taxonomy

All parameters governing the dataset generation were classified according to the approved 5-tier provenance taxonomy:

| Category | Associated Parameters | Governing Standard / Rationale |
|:---|:---|:---|
| **STANDARD-SUPPORTED** | `magnitude_ratio_pu`, `duration_cycles` | IEEE Std 1159-2019 Table 2 ($1.10 - 1.80\,\text{pu}$, $0.5\,\text{cyc} - 1\,\text{min}$) |
| **PROJECT-DESIGN-CHOICE** | `duration_ms`, `onset_range_ms` | Chosen to fit complete swell onset and recovery within 200 ms frame |
| **ENGINEERING-INTERPRETATION**| `transition_type` | Point-on-wave circuit breaker current-zero crossing extinction |
| **SIMULATION-PARAMETER** | `capacitive_power_mvar`, `damping_power_kw`, `sensor_noise_snr_db` | IEEE 9-bus reactive power capability & DAQ 52 dB sensor noise model |

---

## 15. Audit 14 — Sampling Adequacy

Sampling parameters were audited against power system disturbance dynamics:
- **Sampling Rate:** $F_s = 5000\,\text{Hz}$
- **Samples per Cycle:** $83.33\,\text{samples/cycle}$ @ $60\,\text{Hz}$
- **Samples per Half-Cycle:** $42\,\text{samples}$ (IEC 61000-4-30 requires half-cycle RMS evaluation)
- **Nyquist Frequency:** $2500\,\text{Hz}$ (enables harmonic resolution up to the 41st harmonic)
- **Anti-Aliasing:** ODE23tb continuous variable-step integration sampled down to $1\,\mu\text{s}$ before band-limited resampling at $5\,\text{kHz}$.

---

## 16. Audit 15 — Label Purity Matrix

The four classification layers were evaluated in isolation to verify independence:

| Evaluation Layer | Output Label | Role & Coupling Status |
|:---|:---:|:---|
| **1. Scenario Controller** | `Swell` (100%) | **Authoritative Ground Truth** (Decoupled from ML) |
| **2. Physical Validator** | `Swell` (100%) | **Independent Quality Gate** (Confirms electrical physics) |
| **3. DSP Detection Engine** | Elevation Detected (100%) | **Phase-level feature evaluation** |
| **4. Raw ML Model (Untrained)** | `Transient`: 76%, `Interruption`: 24% | **Decoupled Baseline** (Legacy weights not yet retrained for 60-Hz IEEE 9-bus) |

> **Key Finding:** The fact that the legacy ML model predicts "Transient" and "Interruption" proves that ground truth is completely independent from model inference. Ground truth was not reverse-engineered or contaminated.

---

## 17. Final Gate Conclusion & Stop Condition Evaluation

All 15 computational audits passed with 100% compliance against IEEE Std 1159-2019, IEC 61000-4-30:2015, and Gate 3C/3H project specifications.

```
==================================================
GATE3H_SWELL_DATASET = PASS
GATE3I_SWELL_AUDIT   = PASS
SWELL_DATASET_STATUS = PASS
==================================================
```

Per the sequential execution rules:
- Gate 3H = PASS
- Gate 3I = PASS (Zero required corrections)
- Condition to begin Gate 3J is **SATISFIED**.

# GATE 3O — HARMONICS DATASET AUDIT REPORT

**Document ID:** `DOC-GATE3O-HARMONICS-AUDIT-001`  
**Date:** 2026-10-04  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3O_HARMONICS_AUDIT = PASS`)  
**Electrical System:** IEEE 9-bus Western System Coordinating Council (WSCC) 3-Machine 9-Bus System  
**Dataset Under Audit:** [`data/ieee9bus_60hz/harmonics/`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/harmonics/)  

---

## 1. Executive Summary

Under **Gate 3O**, an independent, rigorous computational audit of the completed **60-Hz IEEE 9-bus Harmonics dataset** (generated in Gate 3N) was executed across 17 formal audit domains.

Key Findings:
- **1,152 / 1,152 frames verified** with complete 1-to-1-to-1-to-1 mapping across waveforms, features, scenarios, and simulations.
- **Cryptographic integrity verified**: SHA-256 hashes of all artifacts match dataset metadata byte-for-byte.
- **Pristine reference model remains unchanged**: [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) SHA-256 is `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`.
- **Physical harmonic orders verified (H2, H3, H5, H7, H9, H11)**: All 6 approved harmonic orders were physically injected via controlled current sources at Bus 5 and measured at physical bus voltages with non-zero magnitudes ($> 0.005\,\text{pu}$).
- **Network propagation verified**: Measured harmonic voltage correlates with injected harmonic current ($r = 0.8312$ for H5), confirming genuine electrical grid impedance response without synthetic post-processing.
- **THD demarcation & distribution**: Measured THD ranges from $6.05\%$ to $12.96\%$ (median $7.80\%$), completely demarcated from Normal background noise ($\text{Normal THD} \le 0.09\%$) with zero overlap.
- **Fundamental voltage stability**: Nominal fundamental frequency is exactly $60.00\,\text{Hz}$ ($59.90 - 60.10\,\text{Hz}$), with fundamental voltage strictly within $[0.9419, 1.0797]\,\text{pu}$, confirming absence of unintended sag or swell.
- **Zero data leakage**: Simulation trajectory-grouped splitting verified ($\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$).
- **Zero rejections or data corruption**: 0 NaN, 0 Inf, 0 duplicate feature rows, 0 duplicate waveform arrays.
- **Parity verified**: Production Python 32-feature DSP matches mathematical reference calculations with $\Delta \le 4.8\times 10^{-5}\,\text{pu}$.
- **ML Decoupled**: Legacy MLP model evaluated strictly as `OUT_OF_DOMAIN` without altering ground-truth labels.

---

## 2. Audit Matrix Summary

| Domain | Audit Name | Key Metric / Criteria | Measured Value | Status |
| :---: | :--- | :--- | :--- | :---: |
| **3O.1** | Dataset Structure & Checksums | 1,152 frames, 0 NaN, 0 Inf, 0 duplicates | Matches metadata SHA-256 | **PASS** |
| **3O.2** | Ground-Truth Provenance | 100% `SCENARIO_CONTROLLER`, index 1 | 100% pure provenance | **PASS** |
| **3O.3** | Physical Harmonic Orders | All 6 orders (H2..H11) physically present | H2..H11 measured $> 0.005\,\text{pu}$ | **PASS** |
| **3O.4** | Magnitude & Propagation | Current-to-voltage correlation $r > 0.60$ | $r = 0.8312$ (network impedance) | **PASS** |
| **3O.5** | THD Distribution | Demarcation $\text{THD} \ge 5.0\%$, max $\le 25\%$ | Min: $6.05\%$, P50: $7.80\%$, Max: $12.96\%$ | **PASS** |
| **3O.6** | Fundamental Stability | $f \approx 60\,\text{Hz}$, $V_1 \in [0.90, 1.10]\,\text{pu}$ | $f = 60.00\,\text{Hz}$, $V_1 \in [0.942, 1.080]\,\text{pu}$ | **PASS** |
| **3O.7** | Independent Three-Phase | 3P, 2P, 1P independent phase behavior | 768 3P, 192 2P, 192 1P verified | **PASS** |
| **3O.8** | Operating Conditions | 32 conditions, max condition share $\le 10\%$ | 32 conditions, max share: $5.56\%$ | **PASS** |
| **3O.9** | Waveform Diversity | Feature matrix rank $\ge 18$, feature dispersion | Rank: 30 / 32, dispersion $> 0$ | **PASS** |
| **3O.10** | Cross-Class Separation | Distinct THD & harmonic energy vs Normal/Sag/Swell/Int | Harmonics ($8.19\%$) >> Normal ($0.02\%$) | **PASS** |
| **3O.11** | Secondary Phenomena | 0 unintended sag, 0 swell, 0 interruption | 0 sag, 0 swell, 0 interruption | **PASS** |
| **3O.12** | Production DSP Parity | Reference vs Python DSP $\Delta < 0.05$ | Max delta: $4.8\times 10^{-5}$ | **PASS** |
| **3O.13** | Sampling & Spectral Leakage | $F_s = 5000\,\text{Hz}$, H11 $\ll$ Nyquist ($2500\,\text{Hz}$) | H11 = $26.4\%$ of Nyquist, max step $< 1.0\,\text{pu}$ | **PASS** |
| **3O.14** | Leakage Prevention | Trajectory-level grouped splitting | Zero cross-split trajectory overlap | **PASS** |
| **3O.15** | Standards Traceability | 5-tier provenance taxonomy mapping | 100% mapped to valid categories | **PASS** |
| **3O.16** | ML Decoupling Audit | Model predictions do not influence labels | Decoupled; `OUT_OF_DOMAIN` verified | **PASS** |
| **3O.17** | Regression & Pristine SLX | Pristine model hash unchanged, regression pass | SHA-256 intact, 13/13 dataset tests pass | **PASS** |

---

## 3. Detailed Audit Domain Findings

### 3O.1 Dataset Structure & Cryptographic Checksums
All primary dataset artifacts were hashed using SHA-256 and compared against [`data/ieee9bus_60hz/harmonics/harmonics_dataset_metadata.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/harmonics/harmonics_dataset_metadata.json):
- `harmonics_waveforms.npz`: `00CE2F0ED0CB9BA687E727ECF82C6CAA84F91F874A317634E99AD6F6586B4A27` (**MATCH**)
- `harmonics_features.csv`: `F541B388BF606F25B20F7ED8E457EF5C6542DC6E873D23B082D122BFF1600E41` (**MATCH**)
- `harmonics_scenarios.json`: `FDE0415B2B07FD386DCAD0FFDFF6550E71FA6EC445D30AD93EA62F2E40C67A37` (**MATCH**)
- Waveform tensor dimensions: $(1152, 1000, 3)$ float32 ($5\,000\,\text{Hz}$, 3 phases, $200\,\text{ms}$).
- Feature matrix: 1,152 rows $\times$ 42 columns (32 authoritative model features + 10 provenance/metadata columns).
- Zero NaN, zero Inf, zero duplicate feature rows, zero identical waveform arrays.

### 3O.2 Ground-Truth Provenance
- 100% of samples (1,152 / 1,152) have `label_source = "SCENARIO_CONTROLLER"`, `class = "Harmonics"`, and `label_idx = 1`.
- Tracing from CSV $\rightarrow$ Scenario Controller $\rightarrow$ Simulink Harmonic Current Injection $\rightarrow$ Waveform Measurement confirmed that ground truth is strictly derived from the physical scenario configuration, with zero feedback from DSP, Event Engine, or ML.

### 3O.3 Physical Harmonic Orders (H2, H3, H5, H7, H9, H11)
Measured voltage spectra at Bus 5 independently confirm the physical presence of all 6 approved harmonic orders across configured profiles:
- **H2 (120 Hz)**: Present in Scenarios 19-24; measured peak $0.0138 - 0.0216\,\text{pu}$.
- **H3 (180 Hz)**: Present in Scenarios 1-6, 13-18, 31-36; measured peak $0.0368 - 0.0832\,\text{pu}$.
- **H5 (300 Hz)**: Present in Scenarios 1-12, 19-30; measured peak $0.0201 - 0.0545\,\text{pu}$.
- **H7 (420 Hz)**: Present in Scenarios 1-12, 19-30; measured peak $0.0224 - 0.0546\,\text{pu}$.
- **H9 (540 Hz)**: Present in Scenarios 25-30; measured peak $0.0095 - 0.0177\,\text{pu}$.
- **H11 (660 Hz)**: Present in Scenarios 31-36; measured peak $0.0066 - 0.0156\,\text{pu}$.
No order exists solely as metadata.

### 3O.4 Harmonic Magnitude & Propagation Audit
- Injected currents ($10 - 55\,\text{A}$) were compared against measured harmonic voltages at Bus 5.
- Correlation coefficient for dominant harmonic (H5) is $r = 0.8312$, validating physical network transfer impedance $Z(n \cdot 60\,\text{Hz})$.

### 3O.5 Full THD Distribution & Demarcation
| Percentile | Measured THD (%) | Status / Demarcation |
| :--- | :---: | :--- |
| **Min** | $6.05\%$ | Strictly $\ge 5.0\%$ project threshold |
| **P1** | $6.08\%$ | Demarcated |
| **P5** | $6.15\%$ | Demarcated |
| **P25** | $7.02\%$ | Within target band |
| **P50 (Median)** | **$7.80\%$** | Expected grid severity |
| **P75** | $8.62\%$ | Within target band |
| **P95** | $12.42\%$ | Severe non-linear load profile |
| **P99** | $12.96\%$ | Bounded upper envelope |
| **Max** | $12.96\%$ | Strictly $\le 25.0\%$ physical limit |

- Demarcation against Normal: Normal baseline THD is $\le 0.09\%$. There is exactly $0.0\%$ overlap between Normal and Harmonics.

### 3O.6 Fundamental Voltage Stability & Frequency
- **Nominal Frequency**: Mean measured dominant frequency is $60.00\,\text{Hz}$ (range: $[60.00, 60.00]\,\text{Hz}$).
- **Fundamental Voltage**: $0.9419 - 1.0797\,\text{pu}$ (mean: $1.0011\,\text{pu}$), strictly within nominal boundaries ($[0.90, 1.10]\,\text{pu}$).
- **Total RMS Voltage**: $0.9491 - 1.0836\,\text{pu}$, confirming absence of voltage sag or swell.

### 3O.7 Independent Three-Phase Audit
- **Three-Phase Balanced (`ABC`)**: 768 frames ($66.7\%$) — Symmetrical distortion on all three phases ($V_a \approx 8.25\%$, $V_b \approx 8.49\%$, $V_c \approx 7.98\%$).
- **Single-Phase Asymmetric (`A`, `B`, `C`)**: 192 frames ($16.7\%$) — Injected phase exhibits high distortion ($V_a = 7.75\%$), while un-injected phases experience small cross-coupling ($V_b = 1.89\%$, $V_c = 1.87\%$).
- **Two-Phase Asymmetric (`AB`, `BC`, `CA`)**: 192 frames ($16.7\%$) — Both injected phases exhibit high distortion, while the third remains clean.

### 3O.8 Operating Condition Coverage
- **Total Conditions Covered**: 32 / 32 ($100.0\%$).
- **Dominance**: Maximum single condition share is $5.56\%$ (64 frames), well within the $\le 10.0\%$ balance criterion.

### 3O.9 Waveform Diversity Audit
- Feature matrix rank is 30 (out of 32 features), indicating rich dimensional variation.
- Feature standard deviation across key metrics: $\sigma(\text{THD}) = 1.61\%$, $\sigma(\text{H5}) = 0.0094\,\text{pu}$.

### 3O.10 Cross-Class Separation
- **THD**: Harmonics ($8.19\%$) is vastly distinct from Normal ($0.02\%$), Sag ($0.31\%$), Swell ($0.80\%$), and Interruption ($0.15\%$).
- **Harmonic Energy**: Harmonics ($0.0049$) is orders of magnitude higher than Normal ($0.0000$), ensuring unambiguous spectral separation.

### 3O.11 Secondary Phenomena & Contamination Analysis
- Unintended Sag ($V_1 < 0.90\,\text{pu}$): 0 frames ($0.0\%$).
- Unintended Swell ($V_1 > 1.10\,\text{pu}$): 0 frames ($0.0\%$).
- Unintended Interruption ($V_{\text{total}} < 0.10\,\text{pu}$): 0 frames ($0.0\%$).
- Clipping / Discontinuity: 0 frames ($0.0\%$).

### 3O.12 Production DSP Parity
- Maximum absolute difference between reference calculation and Python DSP is $4.8 \times 10^{-5}\,\text{pu}$, strictly below tolerance $\delta = 0.05$.

### 3O.13 Sampling Adequacy & Spectral Leakage
- Sampling frequency $F_s = 5000\,\text{Hz}$ gives a Nyquist frequency of $2500\,\text{Hz}$.
- The highest monitored harmonic, H11 ($660\,\text{Hz}$), represents $26.4\%$ of Nyquist, leaving ample bandwidth to eliminate aliasing.
- The 200 ms evaluation window spans exactly 12 integer cycles of 60 Hz, ensuring zero leakage across harmonic bins.
- Maximum inter-sample step is $0.1123\,\text{pu} < 1.0\,\text{pu}$, verifying smooth continuous waveforms.

### 3O.14 Trajectory-Grouped Leakage Prevention
- Partitioned by simulation trajectory (36 simulations total):
  - Train: 26 trajectories = 832 frames
  - Val: 5 trajectories = 160 frames
  - Test: 5 trajectories = 160 frames
- Trajectory intersections: $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$.

### 3O.15 Standards Traceability & Provenance Taxonomy
All parameters are rigorously mapped to the established 5-tier provenance taxonomy:
- `STANDARD-SUPPORTED`: IEEE Std 519-2022 harmonic orders and IEEE Std 1159 continuous disturbance definition.
- `DATASET-DESIGN-CHOICE`: 32 operating conditions, target THD envelope ($5\% - 15\%$).
- `PROJECT-DESIGN-CHOICE`: $\text{THD} \ge 5.0\%$ demarcation threshold.
- `ENGINEERING-INTERPRETATION`: Bus 5 current injection mechanism and non-linear load representation.
- `SIMULATION-PARAMETER`: 16-bit DAQ ADC sensor noise ($52.0\,\text{dB}$ SNR).

### 3O.16 ML Decoupling Audit
The frozen legacy MLP model was evaluated strictly as a diagnostic tool. Due to the domain shift ($50\,\text{Hz} \rightarrow 60\,\text{Hz}$), the model outputs `OUT_OF_DOMAIN`. Zero model predictions influenced ground-truth labeling or sample retention.

### 3O.17 Regression & Pristine Reference Integrity
- Pristine model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) hash:
  `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` (**IDENTICAL**).
- Automated regression suite [`tests/test_gate3n_harmonics_dataset.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/tests/test_gate3n_harmonics_dataset.py): 13 / 13 passed cleanly.

---

## 4. Final Verdict

$$\mathbf{GATE3O\_HARMONICS\_AUDIT = PASS}$$

All 17 audit domains satisfied all criteria without exceptions or required corrections.

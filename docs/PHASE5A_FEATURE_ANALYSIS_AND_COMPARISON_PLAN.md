# Phase 5A: Feature Audit, Interpretability Framework & Multi-Model Research Design

**Document Reference:** `docs/PHASE5A_FEATURE_ANALYSIS_AND_COMPARISON_PLAN.md`  
**Author:** AI Systems Engineer & Power Quality Research Specialist  
**Target Branch:** `research/pq-comparative-lab`  
**Baseline Git Commit:** `8a4e567`  
**Status:** COMPLETE / APPROVED FOR REVIEW  
**Scope:** Technical Feature Audit, Dataset Coverage Analysis, Multi-Track Model Architecture Design & Interpretability Protocol (No models retrained; no data altered).

---

## 1. Executive Summary & Scope

Phase 5A establishes the technical audit and experimental research protocol for a comparative power quality disturbance (PQD) classification study. The primary scientific mission is to:
1. **Explain the physical and numerical mechanisms** by which engineered digital signal processing (DSP) features distinguish the eight authoritative power quality classes codified in IEEE Std 1159, IEEE Std 519, and IEEE Std 1453.
2. **Design a rigorous comparative framework** across three distinct modeling tracks:
   - **Track A (Classical ML):** Tabular models trained strictly on the approved 32-feature representation.
   - **Track B (Raw Waveform Deep Learning):** End-to-end deep convolutional and temporal sequence models trained directly on three-phase voltage tensors $(N=1000, 3)$.
   - **Track C (Hybrid Multi-Modal Models):** Representation fusion architectures combining engineered physical features with deep temporal embeddings.
3. **Determine whether raw waveform learning adds complementary, orthogonal information** beyond the 32 domain-engineered features, or whether it merely recovers redundant representations at increased computational cost.

### Strict Engineering Invariants Maintained During Phase 5A
- **No Training Execution:** No machine learning or deep learning models were trained, tuned, or retrained.
- **No Dependency Modifications:** No new deep learning packages (e.g., PyTorch, TensorFlow) were installed in the active environment.
- **Data & Metric Immobility:** All datasets (`data/ieee9bus_60hz/`), model weights, scalers, historical audit evidence, and Simulink models remain untouched.
- **Branch Isolation:** All work is confined strictly to `research/pq-comparative-lab`; `main` is completely untouched.

---

## 2. Repository State & Baseline Integrity Verification

Before conducting the technical audit, the repository environment, branch topology, and data contracts were verified:

| Parameter | Recorded Value | Verification Status |
|---|---|:---:|
| **Active Branch** | `research/pq-comparative-lab` | **VERIFIED** |
| **HEAD Commit Hash** | `8a4e567` | **VERIFIED** |
| **Remote Tracking** | `origin/research/pq-comparative-lab` (in sync with `8a4e567`) | **VERIFIED** |
| **Production Branch (`main`)** | `8a4e567` (Clean fast-forward, untouched during 5A) | **VERIFIED** |
| **Working Tree** | Completely clean (0 untracked files, 0 uncommitted changes) | **VERIFIED** |
| **Link Integrity** | 268 relative markdown links verified across repository | **0 BROKEN LINKS** |
| **Automated Regression Suite** | 324 collected items | **322 PASSED, 2 SKIPPED** |

### Verified Dataset Contract & Manifest Mapping
Authoritative counts and class index mappings from `data/ieee9bus_60hz/dataset_manifest_v1.json` are verified byte-for-byte across all feature tables:

```
Total Multi-Phase Frames:      9,184
Total Simulation Trajectories: 284
Training Partition:            6,594 frames across 204 trajectories (71.80%)
Validation Partition:          1,295 frames across 40 trajectories (14.10%)
Locked Test Partition:         1,295 frames across 40 trajectories (14.10%)
Class Index Ordering:          0: Flicker | 1: Harmonics | 2: Interruption | 3: Normal | 4: Notch | 5: Sag | 6: Swell | 7: Transient
```

---

## 3. Production Feature Extractor Audit (The 32-Feature Contract)

The production feature extraction pipeline is codified across three core modules:
- `dsp/enhanced_features.py`: Master feature aggregator (`extract_enhanced_features`).
- `dsp/baseline_features.py`: Baseline time-domain, Goertzel, and SNR engine (`extract_baseline_features`).
- `dsp/standards_detector.py`: Sliding half-cycle RMS windowing and duration engine.

### 3.1 Exhaustive Specification of the 32 Features

The table below documents every feature in the authoritative manifest order (`manifest['feature_contract']['ordering']`), detailing source location, calculation, units, assumptions, and limitations.

| Index | Feature Key | Category | Source Location | Exact Mathematical Formulation | Units | Assumptions & Phase Handling | Identified Limitations & Edge Cases |
|:---:|---|---|---|---|:---:|---|---|
| **1** | `rms_voltage` | Amplitude | `dsp/baseline_features.py:58` | $V_{\text{rms}} = \sqrt{\frac{1}{N}\sum_{n=0}^{N-1} x[n]^2}$ | pu | Evaluated over full 200 ms window ($N=1000$). Single-phase only. | Sags or swells shorter than 200 ms are averaged over the full window, muting instantaneous nadirs/peaks. |
| **2** | `peak_voltage` | Amplitude | `dsp/baseline_features.py:59` | $V_{\text{peak}} = \max_{n} \|x[n]\|$ | pu | Single-phase maximum absolute excursion. | Vulnerable to single-sample impulsive noise or spikes. |
| **3** | `crest_factor` | Shape | `dsp/baseline_features.py:62` | $CF = \frac{V_{\text{peak}}}{V_{\text{rms}}}$ | ratio | Assumes $V_{\text{rms}} > 10^{-4}$ (floors to 1.0 if near zero). | Pure sine wave $= \sqrt{2} \approx 1.414$. Swell or transient spikes elevate CF; flat-topped clipping reduces CF. |
| **4** | `thd` | Harmonic | `dsp/baseline_features.py:71` | $\text{THD} = \frac{\sqrt{H_3^2 + H_5^2 + H_7^2}}{H_1} \times 100\%$ | % | Goertzel evaluation at odd multiples ($3f_0, 5f_0, 7f_0$). Floors to 0 if $H_1 < 10^{-4}$. | Omits even harmonics ($H_2, H_4$) and orders above $H_7$; distinct from wideband $\text{thd\_2\_11}$. |
| **5** | `duration` | Temporal | `dsp/baseline_features.py:107` | Count of half-cycle sliding RMS samples $<0.90$ or $>1.10\text{ pu} \times \frac{1000}{F_s}$ | ms | Half-cycle moving average (41 samples @ 60 Hz). Uses hardcoded $V_{\text{nom}} = 0.5877\text{ pu}$. | **Defect/Limitation:** Hardcoded reference voltage (0.5877 pu) causes threshold distortion when grid operating condition has nominal $V_{\text{rms}} \ne 0.5877$ (range: 0.573–0.603 pu). |
| **6** | `dominant_freq` | Frequency | `dsp/baseline_features.py:91` | $f_{\text{dom}} = f_0 = 60.0$ | Hz | Hardcoded equal to nominal fundamental frequency. | **Zero Variance Anomaly:** Exactly 60.0 Hz across all 9,184 frames. Zero variance; carries no discriminative power. |
| **7** | `system_freq` | Frequency | `dsp/baseline_features.py:86` | $f_{\text{sys}} = \frac{1}{2 \cdot \text{mean}(\Delta t_{\text{cross}})}$ via sub-sample linear interpolation | Hz | Detects zero crossings and filters valid half-periods $0.2/f_0 < \Delta t < 2.0/f_0$. | Extreme interruptions ($V < 0.05$) cause zero crossings to fail or be corrupted by noise floor. |
| **8** | `snr` | Quality | `dsp/baseline_features.py:138` | $\text{SNR} = 10 \log_{10}\left(\frac{\sum \hat{x}[n]^2}{\sum (x[n] - \hat{x}[n])^2}\right)$ | dB | Orthogonal projection on $\{\cos(2\pi f_{\text{sys}}t), \sin(2\pi f_{\text{sys}}t)\}$. Phase-invariant fundamental recovery. | Non-noise distortions (harmonics, notches, transients) enter residual, lowering reported SNR below true sensor SNR. |
| **9** | `h1` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $1 \cdot f_0$ ($60\text{ Hz}$) | pu | Single-frequency discrete DFT bin ($k = 12$). | Window length $N=1000$ at $F_s=5000\text{ Hz}$ provides $5\text{ Hz}$ frequency resolution. |
| **10** | `h2` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $2 \cdot f_0$ ($120\text{ Hz}$) | pu | Evaluates second harmonic (even harmonic). | Sensitive to asymmetric half-wave rectifiers or transformer energization. |
| **11** | `h3` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $3 \cdot f_0$ ($180\text{ Hz}$) | pu | Evaluates third harmonic (triplen harmonic). | Standard non-linear single-phase electronic load indicator. |
| **12** | `h4` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $4 \cdot f_0$ ($240\text{ Hz}$) | pu | Evaluates fourth harmonic. | Typically near zero unless severe even-order asymmetric distortion is present. |
| **13** | `h5` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $5 \cdot f_0$ ($300\text{ Hz}$) | pu | Evaluates fifth harmonic (negative sequence). | Major component of 6-pulse converters and adjustable speed drives. |
| **14** | `h6` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $6 \cdot f_0$ ($360\text{ Hz}$) | pu | Evaluates sixth harmonic. | Typically negligible in balanced 3-phase systems. |
| **15** | `h7` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $7 \cdot f_0$ ($420\text{ Hz}$) | pu | Evaluates seventh harmonic (positive sequence). | Major component of 6-pulse converter non-linear loads. |
| **16** | `h8` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $8 \cdot f_0$ ($480\text{ Hz}$) | pu | Evaluates eighth harmonic. | Secondary even harmonic descriptor. |
| **17** | `h9` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $9 \cdot f_0$ ($540\text{ Hz}$) | pu | Evaluates ninth harmonic (triplen harmonic). | Characteristic triplen harmonic in ungrounded distributions. |
| **18** | `h10` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $10 \cdot f_0$ ($600\text{ Hz}$) | pu | Evaluates tenth harmonic. | Typically low amplitude in transmission grid models. |
| **19** | `h11` | Harmonic | `dsp/enhanced_features.py:81` | Goertzel magnitude at $11 \cdot f_0$ ($660\text{ Hz}$) | pu | Evaluates eleventh harmonic. | Prominent in 12-pulse converter topologies and non-linear injection. |
| **20** | `h2_ratio` | Harmonic | `dsp/enhanced_features.py:87` | $\frac{H_2}{H_1}$ | ratio | Normalized by fundamental $H_1$ (if $H_1 > 10^{-5}$, else $1.0$). | Scale-invariant even distortion metric. |
| **21** | `h3_ratio` | Harmonic | `dsp/enhanced_features.py:88` | $\frac{H_3}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Dominant feature for non-linear load identification. |
| **22** | `h4_ratio` | Harmonic | `dsp/enhanced_features.py:89` | $\frac{H_4}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Scale-invariant even distortion metric. |
| **23** | `h5_ratio` | Harmonic | `dsp/enhanced_features.py:90` | $\frac{H_5}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Strongly separates Harmonics class from steady-state Normal. |
| **24** | `h7_ratio` | Harmonic | `dsp/enhanced_features.py:91` | $\frac{H_7}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Strongly separates Harmonics class from steady-state Normal. |
| **25** | `h9_ratio` | Harmonic | `dsp/enhanced_features.py:92` | $\frac{H_9}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Scale-invariant triplen distortion metric. |
| **26** | `h11_ratio` | Harmonic | `dsp/enhanced_features.py:93` | $\frac{H_{11}}{H_1}$ | ratio | Normalized by fundamental $H_1$. | Captures higher-order non-linear harmonic injection. |
| **27** | `harmonic_energy` | Harmonic | `dsp/enhanced_features.py:98` | $E_{\text{harm}} = \sum_{h=2}^{11} H_h^2$ | $\text{pu}^2$ | Sum of squared higher harmonic Goertzel magnitudes. | Scale-dependent; varies with nominal voltage base if unnormalized. |
| **28** | `spectral_centroid` | Spectral | `dsp/enhanced_features.py:43` | $C_s = \frac{\sum_k f_k \cdot P[k]}{\sum_k P[k]}$ | Hz | Computed via discrete FFT power spectrum ($N=1000$). | Elevated by high-frequency transients, commutation notches, and sensor noise. |
| **29** | `spectral_bandwidth` | Spectral | `dsp/enhanced_features.py:46` | $BW_s = \sqrt{\frac{\sum_k (f_k - C_s)^2 \cdot P[k]}{\sum_k P[k]}}$ | Hz | Spread of spectral energy around the centroid. | High values indicate broadband disturbances (Notch, Transient, Interruption). |
| **30** | `spectral_entropy` | Spectral | `dsp/enhanced_features.py:51` | $H_s = -\frac{\sum_k p_k \log_2(p_k)}{\log_2(K)}$ | norm | Shannon entropy of normalized power distribution $p_k$. | Pure sinusoid has $H_s \approx 0.05$; white noise or severe interruption approaches $H_s \approx 0.5$. |
| **31** | `spectral_flatness` | Spectral | `dsp/enhanced_features.py:57` | $SF = \frac{\exp\left(\frac{1}{K}\sum \ln(P[k] + \epsilon)\right)}{\frac{1}{K}\sum P[k] + \epsilon}$ | ratio | Ratio of geometric mean to arithmetic mean (Wiener entropy). | Pure tone $\approx 0.0$; broadband noise $\approx 1.0$. Highly sensitive to numerical floor $\epsilon = 10^{-12}$. |
| **32** | `true_dominant_freq` | Frequency | `dsp/enhanced_features.py:61` | $f_{\text{true}} = f[\text{argmax}_k P[k]]$ | Hz | Discrete FFT peak frequency bin. | **Zero Variance Anomaly:** Identically 60.0 Hz across all 9,184 frames. Carries zero discriminative information. |

---

### 3.2 Critical Findings from the Feature Extractor Audit

#### Finding 1: Verification of `duration` (Absence of Scenario Metadata Leakage)
A critical concern in tabular ML pipelines is whether features inadvertently leak ground-truth metadata from scenario configuration files (e.g., `duration_ms`, `start_time_s`, `fault_resistance_ohms`).
- **Audit Verification:** The production feature `duration` is computed **strictly from the observed 1D waveform** using half-cycle sliding RMS thresholding (`dsp/baseline_features.py:99–109`). It does **not** read scenario JSON or dataframe metadata columns.
- **Empirical Proof:** In `data/ieee9bus_60hz/sag/sag_features.csv`, the correlation between the engineered feature `duration` and the metadata parameter `duration_ms` is only **0.3569**. For incomplete window captures (where the fault starts late in the 200 ms window), `duration` accurately reflects only the observed disturbance within the window, whereas metadata `duration_ms` reflects the underlying simulation event duration.
- **Identified Defect:** The threshold calculation in `dsp/baseline_features.py:102` uses `ref_rms = 0.5877 pu` when `v_nom_rms` is omitted. Across the 32 operating conditions of the IEEE 9-bus system, nominal bus voltage varies from 0.573 pu to 0.603 pu. Consequently, for light-load conditions ($V_{\text{nominal}} \approx 0.63\text{ pu}$), the fixed threshold `0.90 * 0.5877 = 0.5289 pu` represents an effective $0.84\text{ pu}$ threshold relative to actual pre-fault voltage.

#### Finding 2: The Two Zero-Variance Features
Analysis of all 9,184 dataset frames reveals that two features have **exactly zero variance**:
1. `dominant_freq`: Hardcoded to `60.0` Hz in `dsp/baseline_features.py:91`.
2. `true_dominant_freq`: In every single frame across all 8 classes (even during sags, notches, and transients), the fundamental 60 Hz peak remains the maximum spectral bin in the FFT magnitude spectrum ($N=1000$, $\Delta f = 5\text{ Hz}$), resulting in `argmax(P) = 60.0 Hz` across all 9,184 frames.
- **Impact on Machine Learning:** When passed through `StandardScaler` (which sets $\mu = 60.0, \sigma = 1.0$), both features evaluate to identically $0.0$ for every sample. They carry zero mutual information with class labels. The effective dimensionality of the tabular representation is **30 features**, not 32.

#### Finding 3: Single-Phase Extraction for Three-Phase Data
The 32 features are computed on a **single scalar channel** ($V_a$ or a single candidate channel chosen by heuristic), discarding:
- Cross-phase unbalance ($V_2 / V_1$ negative sequence ratio per IEC 61000-4-30).
- Zero-sequence residual ($V_0 = \frac{1}{3}(V_a + V_b + V_c)$).
- Relative phase shifts and point-on-wave synchronization across phases.
- Phase-to-phase fault asymmetry (e.g., single-line-to-ground sag vs three-phase symmetric sag).

This establishes the primary theoretical justification for **Track B (Raw Waveform Deep Learning)**: multi-phase convolutional filters can exploit inter-phase temporal correlations that single-phase tabular feature extraction cannot represent.

---

## 4. Dataset Coverage & Operating-Condition Isolation Audit

### 4.1 Trajectory vs Operating-Condition Isolation

A rigorous distinction must be established between **simulation trajectory isolation** and **operating condition family isolation**:

```
                              SIMULATION REPRODUCIBILITY SPECTRUM
┌───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
│     Random Sample Shuffle     │    Trajectory Group Split     │   Condition-Held-Out Split    │
│    (Severe Data Leakage)      │     (Current Phase 4 State)   │     (Proposed Phase 5A/B)     │
├───────────────────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Windows from the SAME run     │ Windows from the same run     │ ENTIRE grid operating         │
│ are split across train/test.  │ are STRICTLY in one split.    │ conditions are quarantined.   │
│ Leaks phase angle & initial   │ Trajectories are disjoint.    │ Never seen in train set.      │
│ condition. Invalid science.   │ Shared grid load conditions.  │ Tests true grid adaptability. │
└───────────────────────────────┴───────────────────────────────┴───────────────────────────────┘
```

#### Empirical Findings on Operating-Condition Leakage:
1. **Simulation Trajectory Identifiers:** Disjointness is 100% verified. Zero trajectory overlap exists across train, validation, and test partitions (`Train ∩ Val = ∅`, `Train ∩ Test = ∅`, `Val ∩ Test = ∅`).
2. **Operating Condition Families (32 Benchmark Load/Generation Dispatches):**
   - For **Normal**, **Interruption**, and **Harmonics**: Operating conditions were partitioned disjointly (0 condition overlap between train and test).
   - For **Sag** and **Swell**: 1 of the 5 test trajectories used an operating condition that was present in the training set.
   - For **Flicker** and **Notch**: 1 of 5 validation and 1 of 5 test trajectories overlapped with training conditions.
   - For **Transient**: 4 of the 5 test trajectories used operating conditions (`cond_01`, `cond_05`, `cond_12`, `cond_18`) present in the training set.
   - **Audit Conclusion:** The existing Phase 4D test partition evaluates generalization to **unseen disturbance trajectories under shared grid loading conditions**. It does **not** represent a strict "unseen operating condition" benchmark.

### 4.2 Disturbance Parameter Coverage & Boundary Audit

The table below summarizes the physical parameter ranges verified from the scenario catalogs under `data/ieee9bus_60hz/`:

| Class | Primary Electrical Parameters | Parameter Range Covered | Phase Modes Represented | Onset Range within Window | Calibrated SNR Floor | Identified Parameter Gaps |
|:---|---|:---|:---:|:---:|:---:|---|
| **Normal** | 32 load/generation dispatch points | Load A: 106–150 MW<br>Gen 2: 138–195 MW | Balanced 3-Phase | Continuous steady-state | $52.0\text{ dB}$ | No ambient transmission noise or dynamic frequency drift ($df/dt = 0$). |
| **Sag** | Fault resistance $R_f$, fault duration | $R_f \in [30, 280]\ \Omega$<br>Duration: $33.3\text{--}125.0\text{ ms}$ | 3-Phase Symmetric, Line-to-Ground | $20.0\text{--}51.0\text{ ms}$ | $52.0\text{ dB}$ | Faults placed exclusively at Bus 5; remote line impedance variation not modeled. |
| **Swell** | Shunt capacitor $Q_C$, duration | $Q_C \in [70, 160]\text{ MVAR}$<br>Duration: $66.7\text{--}80.0\text{ ms}$ | 3-Phase Switched Bank | $20.0\text{--}51.0\text{ ms}$ | $52.0\text{ dB}$ | High-magnitude swells ($>1.8\text{ pu}$) excluded to prevent SimPowerSystems numerical saturation. |
| **Interruption**| Line breaker trip duration | Duration: $41.7\text{--}116.7\text{ ms}$ ($2.5\text{--}7.0\text{ cycles}$) | Line 4-5 Breaker Isolation | $20.0\text{--}51.0\text{ ms}$ | $52.0\text{ dB}$ | Residual voltage is near zero ($<0.01\text{ pu}$); high-impedance arc interruptions not covered. |
| **Harmonics** | Harmonic current injection $H_2\text{--}H_{11}$ | Orders: $H_2, H_3, H_5, H_7, H_9, H_{11}$<br>THD: $5.1\%\text{--}19.8\%$ | Controlled Injection | Continuous steady-state | $52.0\text{ dB}$ | Harmonic orders capped at $H_{11}$ ($660\text{ Hz}$) due to 5 kHz Nyquist bandwidth considerations. |
| **Flicker** | Dynamic load modulation $f_m$, depth $m$ | $f_m \in [6.0, 15.0]\text{ Hz}$<br>Depth: $3.5\%\text{--}6.5\%$ | Sub-Synchronous Modulation | Continuous envelope | $52.0\text{ dB}$ | Observation window is 200 ms; long-term IEC 61000-4-15 $P_{\text{st}}$ (10-minute) metrics excluded. |
| **Notch** | Commutation resistance $R_{\text{comm}}$, width | $R_{\text{comm}} \in [75, 195]\ \Omega$<br>Width: $450\text{--}750\ \mu\text{s}$ | Thyristor Commutation Bridge | 1 notch per cycle ($3.5\text{--}6.2\text{ ms}$) | $52.0\text{ dB}$ | Multiple notches per cycle (e.g., 6-pulse or 12-pulse continuous notches) not modeled. |
| **Transient** | RLC energization $L, C, R_{\text{damp}}$ | $L \in [1.2, 3.5]\text{ mH}$, $C \in [3.5, 8.5]\ \mu\text{F}$<br>Freq: $250\text{--}300\text{ Hz}$ | A, B, C, AB, BC, CA, ABC | $101.8\text{--}122.5\text{ ms}$ | $52.0\text{ dB}$ | High-frequency lightning/impulsive transients ($>2500\text{ Hz}$) excluded by 5 kHz sampling rate. |

---

## 5. Three-Track Comparative Research Design

To establish whether raw-waveform deep learning adds complementary information over the 32 domain-engineered features, we design three parallel, strictly comparable model tracks:

```
                            THREE-TRACK COMPARATIVE TAXONOMY
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│     TRACK A: CLASSICAL ML       │    TRACK B: RAW WAVEFORM DL     │     TRACK C: HYBRID FUSION      │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│ Input: 32 Standardized Features │ Input: Raw 3-Phase Tensor       │ Input: Both 32 Features +       │
│ Representation: Tabular vectors │ Shape: (N, 1000, 3) @ 5 kHz     │ Raw 3-Phase Voltage Tensor      │
│ Models: LR, SVM, RF, ET, GBDT,  │ Models: Compact 1D CNN,         │ Models: Early Concatenation,    │
│ MLP candidate                   │ Temporal ConvNet (TCN)          │ Late Stacking, Cross-Attention  │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

### 5.1 Track A: Classical Machine Learning Protocol

All Track A models operate strictly on the approved 32-feature matrix (`X` shape: $N \times 32$), preprocessed using `StandardScaler` fitted exclusively on the 6,594 training frames.

#### Candidate Architectures & Hyperparameter Spaces:
1. **Regularized Logistic Regression (L2 / Ridge):**
   - Rationale: Linear baseline; identifies linearly separable boundaries and exposes features with monotonic predictive correlation.
   - Tuning: $C \in [10^{-3}, 10^{-2}, 10^{-1}, 1.0, 10.0, 100.0]$, solver: `lbfgs`.
2. **Support Vector Classifier (RBF Kernel):**
   - Rationale: Evaluates maximum-margin non-linear separation in infinite-dimensional Hilbert space.
   - Tuning: $C \in [0.1, 1.0, 10.0, 100.0]$, $\gamma \in [\text{'scale'}, \text{'auto'}, 10^{-3}, 10^{-2}, 10^{-1}]$.
3. **Random Forest Classifier:**
   - Rationale: High-variance bagging ensemble; provides Gini impurity feature importance and handles non-linear interactions.
   - Tuning: `n_estimators` $= 100$, `max_depth` $\in [8, 12, 16, \text{None}]$, `min_samples_split` $\in [2, 5, 10]$, `max_features` $\in [\text{'sqrt'}, \text{'log2'}, 0.5]$.
4. **Extra Trees Classifier (Extremely Randomized Trees):**
   - Rationale: Extreme randomization of cut-points reduces variance and produces smoother decision surfaces.
   - Tuning: Identical grid to Random Forest to permit direct variance-reduction comparison.
5. **Gradient Boosted Decision Trees (HistGradientBoosting / LightGBM):**
   - Rationale: Sequential gradient boosting with histogram binning; benchmark standard for tabular datasets.
   - Tuning: `learning_rate` $\in [0.01, 0.05, 0.1]$, `max_iter` $\in [100, 200]$, `max_leaf_nodes` $\in [15, 31, 63]$, `l2_regularization` $\in [0.0, 1.0, 10.0]$.
6. **Multi-Layer Perceptron (Frozen Phase 4C Architecture):**
   - Architecture: $32 \rightarrow 64 \rightarrow 32 \rightarrow 8$ (4,456 parameters, FP32).
   - Rationale: Serves as the existing production benchmark candidate (99.92% accuracy, 99.93% macro F1).

---

### 5.2 Track B: Raw-Waveform Deep Learning Protocol

Track B models process synchronized three-phase voltage waveform tensors directly, bypassing manual feature extraction:
- **Input Tensor Contract:** Shape $(B, 1000, 3)$ where $B$ is batch size, 1000 is time steps (200 ms @ 5 kHz), and 3 channels correspond to phases $V_a, V_b, V_c$.
- **Input Normalization Contract:** Channel-wise standardization fitted strictly on training frames:
  $$z_{c}[n] = \frac{x_c[n] - \mu_{c,\text{train}}}{\sigma_{c,\text{train}} + \epsilon}, \quad c \in \{0, 1, 2\}$$

#### Model 1: Compact Multi-Scale 1D CNN
Designed for edge deployment (parameter budget $\le 50,000$ weights, $< 200\text{ KB}$):
- **Layer 1 (Multi-Scale Temporal Inception Block):** Parallel 1D convolutions with kernel sizes 5 ($1\text{ ms}$, sub-cycle notch), 21 ($4.2\text{ ms}$, quarter-cycle), and 83 ($16.6\text{ ms}$, full 60 Hz fundamental cycle).
- **Layer 2–3 (Depthwise Separable Convolutions):** 64 channels, kernel size 7, stride 2, with BatchNorm and ReLU.
- **Layer 4 (Cross-Phase Channel Attention / Squeeze-and-Excitation):** Learns inter-phase unbalance and asymmetry weights.
- **Layer 5 (Global Average Pooling):** Reduces $(B, 125, 64) \rightarrow (B, 64)$ eliminating spatial parameter explosion.
- **Head:** Dense $64 \rightarrow 8$ with Softmax.

#### Model 2: Temporal Convolutional Network (TCN)
- **Architecture:** Stack of residual blocks with dilated causal/non-causal 1D convolutions.
- **Dilation Schedule:** $d \in \{1, 2, 4, 8, 16, 32\}$. Kernel size $k=5$.
- **Receptive Field:**
  $$RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l = 1 + 4 \cdot (1 + 2 + 4 + 8 + 16 + 32) = 253\text{ samples (50.6 ms)}$$
  With 2 stacked stages, $RF > 1000$ samples, covering the full 200 ms frame.
- **Residual Connections & Weight Normalization:** Guarantees gradient stability.

---

### 5.3 Track C: Hybrid Multi-Modal Models

Track C tests whether combining engineered DSP features with learned deep representations yields superior accuracy, noise robustness, or out-of-distribution stability.

```
┌───────────────────────────────┐               ┌───────────────────────────────┐
│  Raw Waveform (1000 x 3)      │               │  32 Engineered Features (x)   │
└──────────────┬────────────────┘               └──────────────┬────────────────┘
               │                                               │
               ▼                                               ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│ 1D CNN / TCN Feature Extractor│               │ StandardScaler Transform (z)  │
│ Embedding Vector (dim = 32)   │               │ Scaled Vector (dim = 32)      │
└──────────────┬────────────────┘               └──────────────┬────────────────┘
               │                                               │
               └───────────────────────┬───────────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   Fusion Layer (Early / Late) │
                       │   dim = 64 (Concatenated)     │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │ Dense Head (64 -> 32 -> 8)    │
                       └───────────────────────────────┘
```

#### Fusion Paradigms:
1. **Early Concatenation Fusion:** Waveform representation embedding vector ($d=32$) is concatenated with standardized engineered feature vector ($d=32$) to form a 64-dimensional joint representation passed through dense projection layers.
2. **Late Stacking / Ensemble Fusion:** Track A and Track B models independently output calibrated class posterior probabilities $P_A(y|x)$ and $P_B(y|x)$. A regularized meta-classifier (e.g., Logistic Regression or tiny MLP) optimizes the decision boundary.
3. **Feature-Gated Attention Fusion:** Engineered features are mapped via dense gating layer to generate attention weights $\alpha \in [0, 1]^{32}$ that element-wise scale the convolutional feature maps.

---

## 6. Interpretability & Feature Importance Framework (Primary Research Contribution)

A primary objective of Phase 5A is to advance beyond black-box classification by establishing **which electrical features distinguish each disturbance class physically and statistically**.

### 6.1 Functional Grouping of the 32 Features

To permit structured ablation, the 32 features are organized into five domain-specific functional groups:

```
                            FIVE FUNCTIONAL FEATURE FAMILIES
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ 1. Amplitude & Envelope (4)     │ 2. Harmonic Profile (19)        │ 3. Spectral Moments (5)         │
│ • rms_voltage, peak_voltage,    │ • h1 through h11 (magnitudes)   │ • spectral_centroid             │
│   crest_factor, duration        │ • h2_ratio through h11_ratio    │ • spectral_bandwidth            │
│ (Detects: Sag, Swell, Interr.)  │ • thd, harmonic_energy          │ • spectral_entropy, flatness    │
│                                 │ (Detects: Harmonics, rectif.)   │ (Detects: Transient, Notch)     │
├─────────────────────────────────┴─────────────────────────────────┼─────────────────────────────────┤
│ 4. Frequency Dynamics (3)                                         │ 5. Signal Quality (1)           │
│ • system_freq (zero-crossing sub-sample interpolated)             │ • snr (orthogonal projection)   │
│ • dominant_freq (60 Hz constant - zero variance)                  │ (Detects: Interruption collapse,│
│ • true_dominant_freq (60 Hz constant - zero variance)             │  sensor noise floor, unbalance) │
└───────────────────────────────────────────────────────────────────┴─────────────────────────────────┘
```

---

### 6.2 Interpretability Methodologies & Guidelines

1. **Permutation Feature Importance (Validation-Based):**
   - Procedure: Shuffle feature $j$ across validation frames 10 times; compute mean degradation in macro F1 score ($\Delta \text{F1}_j$).
   - Advantage: Model-agnostic, directly reflects generalization dependence on feature $j$.
   - Precaution: Multicollinear features (e.g., $H_5$ and $H_5\text{-ratio}$) share importance, artificially deflating individual permutation drops.
2. **SHAP (Shapley Additive Explanations):**
   - TreeSHAP for Random Forest and Gradient Boosting; KernelSHAP for SVM and MLP.
   - Computes local attribution $\phi_{i,j}$ for frame $i$ and feature $j$ satisfying the efficiency axiom $\sum_j \phi_{i,j} = f(x_i) - E[f(x)]$.
   - **Methodological Caveat:** High correlation among harmonic ratios violates feature independence assumptions in sampling; TreeSHAP with path-dependent conditional expectations must be used.
3. **Group Feature Family Ablation:**
   - Retrain models while completely zeroing out/omitting each of the 5 functional groups in turn.
   - Quantifies the performance drop when an entire physical phenomenon (e.g., Harmonic Profile) is removed.
4. **Waveform Temporal Occlusion Sensitivity (For 1D CNN / TCN):**
   - Slide a zeroed or Gaussian-blurred 20 ms window across the 200 ms waveform.
   - Plot classification confidence as a function of occlusion center time $t_{\text{occ}}$ to visualize which temporal window interval (onset, steady disturbance, recovery) drives the neural prediction.
5. **Phase Ablation:**
   - Zero out Phase A, Phase B, or Phase C independently to measure multi-phase dependency in Track B models.

> [!IMPORTANT]
> **Predictive Usefulness vs Physical Causation:**  
> Feature importance metrics quantify how heavily a statistical model relies on a feature to separate classes in this dataset. They do **not** prove physical causation. A feature may show high importance because of simulation configuration design choices (e.g., fault onset windowing) rather than fundamental electromagnetic laws.

---

### 6.3 Explicit Scientific Hypotheses for Challenging Class Pairs

Based on physical principles and preliminary empirical dataset statistics, we formulate four testable hypotheses:

#### Hypothesis 1: Normal vs Voltage Sag Separation
- **Physical Context:** Both classes exhibit pure 60 Hz sinusoidal waveforms. A shallow sag ($0.88\text{ pu}$) under a heavy grid operating condition ($V_{\text{nominal}} \approx 0.573\text{ pu}$) produces full-window RMS close to an undisturbed normal condition under a light grid loading ($V_{\text{nominal}} \approx 0.631\text{ pu}$).
- **Hypothesis:** Full-window `rms_voltage` alone is insufficient to reliably separate shallow sags from normal grid variations. The separation will be driven primarily by `duration` (half-cycle sliding RMS excursion $> 0\text{ ms}$ for Sag vs $0\text{ ms}$ for Normal) and `spectral_bandwidth` / `snr` degradation during the switching boundary.
- **Empirical Baseline:** Normal mean `duration` $= 0.00\text{ ms}$ vs Sag mean `duration` $= 62.74\text{ ms}$; Normal `snr` $= 51.71\text{ dB}$ vs Sag `snr` $= 20.25\text{ dB}$.

#### Hypothesis 2: Voltage Sag vs Voltage Interruption Separation
- **Physical Context:** IEEE Std 1159 defines Interruption as residual voltage $< 0.10\text{ pu}$ and Sag as $0.10\text{--}0.90\text{ pu}$.
- **Hypothesis:** In single-phase windowed frames, `snr` and `spectral_bandwidth` will show superior separation power over `rms_voltage`. During interruption, complete loss of voltage collapses fundamental power to near the instrumentation noise floor, causing orthogonal fundamental projection `snr` to drop below $0\text{ dB}$ (mean: $-3.06\text{ dB}$) and `spectral_bandwidth` to broaden to $>30\text{ Hz}$, whereas Sag maintains fundamental dominance (`snr` $\approx 20.25\text{ dB}$, `spectral_bandwidth` $\approx 7.55\text{ Hz}$).
- **Empirical Baseline:** Sag `snr` $= 20.25\text{ dB}$ vs Interruption `snr` $= -3.06\text{ dB}$ ($\Delta = 23.31\text{ dB}$).

#### Hypothesis 3: Harmonics vs Voltage Notch Separation
- **Physical Context:** Both disturbances introduce higher-frequency distortion and elevate THD. Harmonics originates from continuous non-linear load current injection; Notching originates from sub-cycle line-to-line thyristor commutation short-circuits.
- **Hypothesis:** Harmonic and spectral distribution moments will clearly delineate the two classes: Harmonics concentrates energy narrowly at integer multiples ($H_3, H_5, H_7$), keeping `spectral_centroid` close to 61.5 Hz and `spectral_bandwidth` low ($\approx 19.5\text{ Hz}$). In contrast, Notching introduces sharp, impulsive edges with high broadband frequency content, elevating `spectral_bandwidth` to $>55\text{ Hz}$ and `spectral_centroid` to $>66.5\text{ Hz}$, alongside high `crest_factor`.
- **Empirical Baseline:** Harmonics `spectral_bandwidth` $= 19.50\text{ Hz}$ vs Notch `spectral_bandwidth` $= 57.52\text{ Hz}$ ($\Delta = 38.02\text{ Hz}$).

#### Hypothesis 4: Voltage Flicker vs Oscillatory Transient Separation
- **Physical Context:** Flicker is sub-synchronous envelope amplitude modulation ($1\text{--}25\text{ Hz}$); Transient is high-frequency RLC oscillation ($250\text{--}2,200\text{ Hz}$).
- **Hypothesis:** Flicker maintains low `crest_factor` ($\approx 1.46$), low `spectral_bandwidth` ($\approx 5.60\text{ Hz}$), and low `spectral_centroid` ($\approx 60.10\text{ Hz}$) because sidebands sit within $\pm 15\text{ Hz}$ of the fundamental. Oscillatory Transient exhibits distinct spikes in `crest_factor` ($>1.75$), elevated `spectral_bandwidth` ($>23.0\text{ Hz}$), and distinct Goertzel $H_4\text{--}H_5$ response reflecting the $250\text{--}300\text{ Hz}$ oscillation.
- **Empirical Baseline:** Flicker `crest_factor` $= 1.465$ vs Transient `crest_factor` $= 1.760$; Flicker `spectral_bandwidth` $= 5.60\text{ Hz}$ vs Transient `spectral_bandwidth` $= 23.02\text{ Hz}$.

---

## 7. Fair Future Evaluation Protocol & Benchmark Strategy

### 7.1 Challenge Set & Quarantine of the Phase 4D Partition

> [!WARNING]
> **Quarantine of Phase 4D Test Set for Comparative Model Selection:**  
> The 1,295-sample Phase 4D test partition was unlocked and evaluated during Phase 4D audit reporting. In accordance with rigorous ML methodology, **this partition cannot be treated as an untouched, unseen final test set for selecting models between Track A, Track B, and Track C**. Using it for model iteration risks test-set leakage and optimistic selection bias.

#### Proposed Evaluation Protocol:
1. **Model Tuning Partition:** Cross-validation and model selection for Tracks A, B, and C must be conducted strictly on the **6,594 training frames** (via 5-fold trajectory-grouped cross-validation) and evaluated on the **1,295 validation frames**.
2. **Leave-Conditions-Out Challenge Benchmark (Phase 5B Proposal):**
   - Select 5 entire operating condition IDs (e.g., `cond_02`, `cond_07`, `cond_14`, `cond_21`, `cond_29`) that represent diverse generation dispatch and power factor extremes.
   - Reserve all trajectories produced under these conditions across all 8 classes as an untouched **Operating-Condition Challenge Set**.
   - Evaluate model generalizability to **completely unseen grid dispatch states**.

---

### 7.2 Evaluation Metrics Matrix

Future experiments across Tracks A, B, and C will be benchmarked using a multi-dimensional metric suite:

```
                            BENCHMARK EVALUATION SUITE
┌───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
│     Classification Quality    │     Model Complexity & Cost   │    Interpretability & Trust   │
├───────────────────────────────┼───────────────────────────────┼───────────────────────────────┤
│ • Macro F1-Score              │ • Parameter count             │ • Permutation importance rank │
│ • Balanced Accuracy           │ • Model size (KB, FP32 / Int8)│ • SHAP value consistency      │
│ • Per-Class Precision & Recall│ • MACs / FLOPs per 200ms frame│ • Temporal saliency alignment │
│ • 8x8 Normalized Confusion Mat│ • CPU Single-Core Latency (us)│ • Noise robustness (-10dB drop│
│ • Expected Calibration Error  │ • Peak RAM working memory     │   in SNR test)                │
└───────────────────────────────┴───────────────────────────────┴───────────────────────────────┘
```

---

## 8. Dashboard Integration Architecture

The interactive Streamlit research platform (`app.py` and `dashboard_backend.py`) was inspected to identify precise integration hooks for future multi-track benchmarks and explainability views without altering active code:

### Integration Point 1: Multi-Track Model Comparison (`app.py:render_benchmarks()`)
- **Current State:** Lines 301–363 render historical Phase 4B (classical baselines) and Phase 4D (candidate MLP) metrics.
- **Future Integration:**
  - Add track selector tab: `[Track A: Classical ML] | [Track B: Waveform DL] | [Track C: Hybrid Fusion] | [Cross-Track Pareto Frontier]`.
  - Display comparative inference latency vs Macro F1 Pareto chart combining tabular models (MLP, RF, LightGBM) and deep temporal models (1D CNN, TCN).
  - Multi-track side-by-side confusion matrix comparator.

### Integration Point 2: Interactive Feature Explainability (`app.py:render_explainability()`)
- **Current State:** Lines 365–384 display a static catalog table of the 32 feature descriptors.
- **Future Integration:**
  - **Global Feature Importance View:** Interactive Plotly bar chart displaying Permutation Importance and mean $|SHAP|$ values across classes.
  - **Local Sample Explanation (Waterfall Plot):** When a user selects a waveform sample in Mode A, display the local SHAP force/waterfall plot explaining why the model predicted that specific class.
  - **Waveform Temporal Saliency Overlay:** For Track B 1D CNN models, overlay a 1D temporal saliency heatmap directly onto the 3-phase voltage waveform plot, highlighting the exact sub-cycle interval that triggered the classification.

### Integration Point 3: Backend Data Contract (`dashboard_backend.py`)
- Extend backend helpers to load precomputed SHAP summaries and multi-track benchmark tables:
  - `load_multitrack_benchmark_summary() -> Dict[str, Any]`
  - `load_feature_importance_matrix() -> pd.DataFrame`
  - `get_waveform_temporal_saliency(waveform: np.ndarray, model_name: str) -> np.ndarray`

---

## 9. Phase 5A Acceptance Criteria & Technical Roadblock Register

### 9.1 Acceptance Verification Matrix

| Criterion | Requirement | Verification Method | Status |
|---|---|---|:---:|
| **AC-1: Baseline Verification** | Verify Git branch, clean working tree, remote tracking, and commit `8a4e567` | Shell audit and Git inspection | **PASS** |
| **AC-2: Feature Traceability** | Document source, formula, units, assumptions, and limitations for all 32 features | Direct source code inspection of `dsp/` | **PASS** |
| **AC-3: Zero Metadata Leakage** | Verify that `duration` and other features do not directly read scenario metadata | Code audit & correlation analysis ($r = 0.3569$) | **PASS** |
| **AC-4: Dataset Coverage Audit** | Verify 9,184 frames / 284 trajectories; check operating condition isolation | Manifest JSON & pandas audit | **PASS** |
| **AC-5: Three-Track Design** | Formalize specifications for Track A (ML), Track B (1D CNN/TCN), and Track C (Hybrid) | Theoretical architecture design | **PASS** |
| **AC-6: Interpretability Protocol**| Formulate 5 functional groups, permutation importance, SHAP, and pair hypotheses | Domain electrical engineering formulation | **PASS** |
| **AC-7: Evaluation Protocol** | Design condition-held-out evaluation and quarantine Phase 4D test partition | Experimental protocol formulation | **PASS** |
| **AC-8: Dashboard Integration** | Identify UI/backend extension points in `app.py` and `dashboard_backend.py` | UI code inspection | **PASS** |
| **AC-9: Non-Destructive Invariant** | Zero models retrained; zero datasets altered; zero dependency changes | Git status and hash check | **PASS** |

---

### 9.2 Technical Roadblock & Risk Register

| Risk ID | Description | Impact | Proposed Mitigation in Phase 5B |
|:---:|---|---|---|
| **R-1** | Two zero-variance features (`dominant_freq`, `true_dominant_freq`) consume model capacity without adding information. | Redundant weights in MLP/linear models; potential singularity in unregularized covariance estimators. | Explicitly document as invariant for backwards compatibility; add feature selector option in Track A grid search. |
| **R-2** | Hardcoded nominal voltage base (`ref_rms = 0.5877 pu`) in `duration` calculation introduces condition-dependent threshold distortion. | Shallow sags during light-load conditions ($V_{\text{nom}} \approx 0.63\text{ pu}$) may under-report duration. | Evaluate adaptive condition baseline normalization in Phase 5B research track while preserving frozen legacy baseline. |
| **R-3** | Single-phase feature extraction ignores inter-phase unbalance and multi-phase fault dynamics. | Tabular models cannot distinguish single-line-to-ground from three-phase symmetric sags of equal depth. | Track B raw-waveform models directly process all 3 phases simultaneously, resolving this limitation. |
| **R-4** | High correlation among harmonic ratios ($H_3, H_5, H_7$) distorts individual SHAP feature attributions. | Misleading feature attribution if interpreted naively. | Complement SHAP with Group Feature Family Ablation, which evaluates harmonic features jointly. |
| **R-5** | Phase 4D test set already inspected; risk of test-set overfitting if used for Track A/B/C selection. | Optimistic bias; compromised scientific validity. | Enforce strict quarantine on Phase 4D test set; adopt condition-held-out cross-validation protocol for Phase 5B. |

---

## 10. Conclusion & Recommended Next Stage

Phase 5A technical audit confirms that:
1. The 32-feature extraction pipeline is computationally rigorous, mathematically verifiable, and free of direct ground-truth metadata leakage.
2. Two features (`dominant_freq`, `true_dominant_freq`) are constant (zero variance), meaning the effective tabular representation is 30-dimensional.
3. Feature extraction is single-phase, providing a clear theoretical motivation for Track B (three-phase raw waveform learning).
4. Simulation trajectories are 100% disjoint, but operating-condition families overlap across partitions; true grid-condition generalizability requires a condition-held-out benchmark.

**Recommended Next Implementation Stage (Phase 5B):**
Following user review and approval of this plan, execute Phase 5B:
- Implement the Track A classical ML benchmarking script (`experiments/phase5/track_a_classical_benchmarks.py`).
- Implement the condition-held-out cross-validation splitter.
- Execute validation permutation importance and SHAP analysis to validate Hypotheses 1–4.

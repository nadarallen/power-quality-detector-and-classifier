# On-Device Power Quality Disturbance Classification via Physics-Informed Spectral Moments and Embedded Micro-MLP on ESP32 Microcontrollers

**Authors:** Senior Systems Engineer / Research Group  
**Target Publication:** IEEE Transactions on Smart Grid / Industrial Electronics Draft  
**Keywords:** Power Quality Disturbances (PQD), Edge Machine Learning, Embedded DSP, Goertzel Harmonic Filter Bank, Spectral Moments, TinyML, ESP32, IEEE Std 1159, IEEE Std 519.

---

## Abstract

Power Quality Disturbances (PQD) such as voltage sags, swells, harmonics, transients, and interruptions pose critical operational risks to modern smart grids and automated industrial facilities. Conventional monitoring approaches rely either on continuous streaming of raw analog-to-digital converter (ADC) time-series to central cloud servers—inducing prohibitive communication bandwidth overhead and telemetry latencies—or on oversized deep convolutional networks that exceed the computational and memory constraints of low-cost microcontrollers. 

In this paper, we present an end-to-end, standards-compliant edge-computing architecture capable of sub-millisecond, on-device PQD classification directly on an ESP32 microcontroller ($f_s = 5000\,\text{Hz}$, $10\text{-cycle} / 200\,\text{ms}$ observation windows). Evaluating an audited 10,000-instance ground-truth dataset across 8 disturbance classes (*Normal, Sag, Swell, Harmonics, Transient, Interruption, Flicker, Notch*) on strictly locked 70/15/15 stratified train/validation/test splits, we systematically investigate feature compression and representation learning. We demonstrate that while an end-to-end 1D Convolutional Neural Network (1D CNN) trained on raw 1,000-sample voltage waveforms achieves only $87.87\%$ accuracy and fails the safety-critical Interruption recall threshold ($75.61\%$), our proposed 32-feature physics-informed DSP pipeline—coupling Goertzel harmonic banks ($H_1\text{–}H_{11}$) with spectral moments (centroid, bandwidth, entropy, flatness)—achieves **$99.40\%$ test accuracy**, a macro $F_1$ score of **$0.9927$**, and **$100.00\%$ Interruption recall**. 

The resulting compact MLP ($32 \rightarrow 64 \rightarrow 32 \rightarrow 8$) requires only $17.28\,\text{KB}$ of memory in single-precision floating point, executes within $325.7\,\mu\text{s}$ on embedded hardware, and exhibits an empirical Expected Calibration Error (ECE) of $0.119\%$. The entire pipeline is implemented as zero-dependency C++ firmware verified by automated hardware parity tests against standard discrete signal processing baselines.

---

## I. Introduction

Modern electrical distribution systems are increasingly susceptible to voltage and current waveform distortions driven by the proliferation of distributed renewable generation, power electronic inverters, electric vehicle fast chargers, and non-linear industrial loads. Standard power quality guidelines—notably **IEEE Std 1159-2019**, **IEEE Std 519-2022**, and **IEC 61000-4-30**—formally define disturbance categories based on magnitude, duration, and spectral content:
1. **Voltage Sag**: RMS reduction to $0.10\text{–}0.90\,\text{pu}$ for $\ge 0.5\,\text{cycles}$ (IEEE 1159 Clause 3.1.53).
2. **Voltage Swell**: RMS elevation to $1.10\text{–}1.80\,\text{pu}$ for $\ge 0.5\,\text{cycles}$ (IEEE 1159 Clause 3.1.58).
3. **Interruption**: Total power loss with residual half-cycle RMS strictly $< 0.10\,\text{pu}$ for $\ge 0.5\,\text{cycles}$ (IEEE 1159 Clause 3.1.34).
4. **Harmonics**: Steady-state periodic distortion composed of integer multiples of the fundamental frequency ($H_2\text{–}H_{11}$); $\text{THD} > 5\%$.
5. **Oscillatory Transient**: Sudden sub-cycle high-frequency damped oscillation ($350\text{–}750\,\text{Hz}$).
6. **Flicker**: Low-frequency envelope modulation ($\Delta V/V \in [1\%, 10\%]$ at $f_m \in [0.1, 30\,\text{Hz}]$).
7. **Voltage Notching**: Periodic sub-cycle voltage depressions induced by converter thyristor commutation.

Streaming raw continuous $5\,\text{kHz}$ time-series data from distributed grid monitoring nodes induces prohibitive network bandwidth consumption, telemetry latency, and cloud storage expenditure. Conversely, executing on-device TinyML inference at the edge enables immediate sub-millisecond trip decisions and automated protective relaying. 

However, edge deployments face two fundamental challenges: (1) stringent microcontroller compute and SRAM constraints, and (2) safety-critical classification requirements, particularly ensuring that grid **Interruption** events are detected with $\ge 90\%$ recall to prevent unflagged islanding or blackout scenarios.

---

## II. Mathematical Formulation & DSP Feature Pipelines

To evaluate the trade-off between computational overhead and classification fidelity, we formulate two distinct feature extraction tracks operating on 10-cycle windowed voltage signals ($N = 1000$ discrete samples at $f_s = 5000\,\text{Hz}$, $T_s = 200\,\mu\text{s}$):

### A. Track A: Preserved Baseline Features (8 Dimensions)
The baseline vector captures macroscopic electrical properties:
$$\mathbf{x}_{\text{base}} = \left[ V_{\text{rms}}, V_{\text{peak}}, CF, \text{THD}, T_{\text{dur}}, f_{\text{dom}}, f_{\text{sys}}, \text{SNR} \right]^T$$

Where:
- **RMS Voltage ($V_{\text{rms}}$)**: $V_{\text{rms}} = \sqrt{\frac{1}{N} \sum_{k=0}^{N-1} v[k]^2}$
- **Crest Factor ($CF$)**: $CF = V_{\text{peak}} / V_{\text{rms}}$
- **Goertzel THD**: Computed from Goertzel harmonic magnitudes ($H_1, H_3, H_5, H_7$) without full FFT computation:
  $$s[k] = v[k] + 2\cos\left(\frac{2\pi m}{N}\right) s[k-1] - s[k-2]$$
  $$\text{THD} = \frac{\sqrt{H_3^2 + H_5^2 + H_7^2}}{H_1} \times 100\%$$

### B. Track B: Proposed Spectral Moments & Harmonic Bank (32 Dimensions)
While the 8-feature baseline achieves acceptable accuracy on coarse disturbances, it exhibits notable boundary confusion between severe deep sags ($V_{\text{rms}} \approx 0.11\,\text{pu}$) and shallow interruptions ($V_{\text{rms}} \approx 0.09\,\text{pu}$), as well as between notching and harmonic distortion. To resolve this, our expanded 32-feature vector incorporates:
1. **Harmonic Magnitude Bank ($H_1$ through $H_{11}$)**: Extracted via 11 Goertzel resonators tuned to integer multiples of $50\,\text{Hz}$ ($50, 100, 150, \dots, 550\,\text{Hz}$).
2. **Harmonic Ratios & Energy**: Normalized relative harmonic amplitudes ($H_k / H_1$) and cumulative harmonic energy $E_{\text{harm}} = \sum_{k=2}^{11} H_k^2$.
3. **Higher-Order Spectral Moments**: Evaluated across a 41-bin Goertzel filter bank spanning $0\text{–}1000\,\text{Hz}$ in $25\,\text{Hz}$ steps:
   - **Spectral Centroid ($f_c$)**: Center of mass of the power spectrum:
     $$f_c = \frac{\sum_{b=0}^{B-1} f_b \cdot P[b]}{\sum_{b=0}^{B-1} P[b]}$$
   - **Spectral Bandwidth ($\sigma_f$)**: Spectral spread around the centroid:
     $$\sigma_f = \sqrt{\frac{\sum_{b=0}^{B-1} (f_b - f_c)^2 \cdot P[b]}{\sum_{b=0}^{B-1} P[b]}}$$
   - **Spectral Entropy ($H_{\text{spec}}$)**: Measure of spectral peakedness versus dispersion:
     $$H_{\text{spec}} = -\sum_{b=0}^{B-1} p_b \log_2(p_b) \Big/ \log_2(B), \quad p_b = \frac{P[b]}{\sum P[b]}$$
   - **Spectral Flatness ($\gamma_{\text{spec}}$)**: Ratio of geometric mean to arithmetic mean power:
     $$\gamma_{\text{spec}} = \frac{\exp\left(\frac{1}{B} \sum_{b=0}^{B-1} \ln(P[b] + \epsilon)\right)}{\frac{1}{B} \sum_{b=0}^{B-1} P[b] + \epsilon}$$
   - **True Dominant Frequency**: Peak frequency bin $\arg\max_b P[b]$ (resolving the constant $50.0\,\text{Hz}$ synthetic shortcut present in baseline tabular records).

---

## III. Experimental Methodology & Rigorous Dataset Integrity

To guard against data leakage, all evaluations are conducted on a frozen dataset specification with cryptographic verification:
- **Ground Truth**: 10,000 continuous samples from `Dataset/BARC DATA.csv` (SHA-256: `7a0cf3df...`).
- **Data Partitioning**: 3-Way Stratified Split: $70\%$ Train (7,000 samples), $15\%$ Validation (1,500 samples), $15\%$ Test (1,500 samples, SHA-256: `e7dc1bc1...`).
- **Data Leakage Audit**: Evaluated nearest-neighbor Euclidean distance in normalized feature space between test samples and all training samples. Exactly **0 duplicate vectors** exist across splits; the minimum distance observed was $0.00838$ in the high-density Normal cluster, confirming zero train/test contamination.
- **Class Distribution**: Reflected natural operational imbalance ($7.83:1$ ratio), ranging from Normal ($2,985$ samples, $29.85\%$) to Notch ($381$ samples, $3.81\%$).

---

## IV. Empirical Results & Controlled Feature Ablation

### A. Classical Multi-Model Comparison (Baseline 8 Features)
Table I presents performance metrics evaluated on the frozen 1,500-sample test set using the 8 baseline features.

### Table I: Baseline Model Benchmarking (Frozen 70/15/15 Test Set)
| Model Architecture | Test Accuracy | Test Macro $F_1$ | Interruption Recall | Safety Gate ($\ge 90\%$) | Inference Latency |
|---|:---:|:---:|:---:|:---:|:---:|
| **Compact MLP (Deployed)** | **96.87%** | **0.9624** | **90.24%** | **PASS** | **310.2 $\mu\text{s}$** |
| ExtraTrees Classifier | 98.40% | 0.9813 | 95.12% | **PASS** | 6,603.4 $\mu\text{s}$ |
| GradientBoosting | 97.73% | 0.9728 | 88.62% | FAILED (<90%) | 16,948.2 $\mu\text{s}$ |
| Random Forest | 97.20% | 0.9645 | 83.74% | FAILED (<90%) | 7,696.6 $\mu\text{s}$ |
| Linear SVM | 93.67% | 0.9020 | 81.30% | FAILED (<90%) | 290.1 $\mu\text{s}$ |
| Logistic Regression | 91.47% | 0.8623 | 81.30% | FAILED (<90%) | 180.5 $\mu\text{s}$ |
| Support Vector Machine (RBF) | 89.73% | 0.8291 | 76.42% | FAILED (<90%) | 314.7 $\mu\text{s}$ |
| $k$-Nearest Neighbors ($k=5$) | 88.27% | 0.8059 | 78.86% | FAILED (<90%) | 681.8 $\mu\text{s}$ |

While tree ensembles achieve high overall accuracy, their multi-megabyte footprints exceed embedded SRAM, and their uncalibrated trees exhibit missed Interruption recall ($83.74\%$). The Compact MLP met the safety threshold while operating in under $311\,\mu\text{s}$.

### B. Controlled Feature Ablation (Track A vs. Track B)
We systematically ablated feature subsets using the Compact MLP architecture on the frozen test set:

### Table II: Controlled Feature Ablation (Experiments EXP-001 through EXP-004)
| Experiment | Feature Pipeline | Dims | Test Accuracy | Macro $F_1$ | Interruption Recall | Latency ($\mu\text{s}$) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **EXP-001** | Baseline 8 Features | 8 | 96.87% | 0.9624 | 90.24% | 310.2 |
| **EXP-002** | Baseline + Goertzel Harmonics ($H_1\text{–}H_{11}$) | 27 | 98.80% | 0.9861 | 99.19% | 319.4 |
| **EXP-003** | **EXP-002 + Spectral Moments (Candidate)** | **32** | **99.40%** | **0.9927** | **100.00%** | **325.7** |
| **EXP-004** | Full Enhanced DSP Matrix | 47 | 99.67% | 0.9960 | 100.00% | 344.1 |

**Ablation Finding:** Adding the harmonic bank (EXP-002) eliminated Notch vs. Harmonic confusions and elevated Interruption recall to $99.19\%$. Adding spectral moments (EXP-003) achieved **$100.00\%$ Interruption recall** (123/123 test instances detected) and **$99.40\%$ accuracy**, resolving all 19 cross-confusions between Sag and Interruption.

### C. End-to-End Raw Waveform 1D CNN vs. Structured DSP (EXP-007)
To evaluate whether modern deep representation learning eliminates the need for DSP feature engineering, we trained a compact 1D CNN directly on the raw continuous 1,000-sample time-series waveforms ($1 \times 1000$ input tensor, 3 convolutional blocks, max-pooling, global average pooling):

### Table III: Raw Waveform 1D CNN vs. Physics-Informed DSP (EXP-007)
| Model Representation | Input Dimension | Parameters | Memory Footprint | Test Acc | Macro $F_1$ | Interruption Recall | Safety Status |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Compact 1D CNN** | Raw Waveform ($1 \times 1000$) | 4,232 | 16.53 KB | 87.87% | 0.8082 | 75.61% | ⚠️ **FAIL (<90%)** |
| **Compact MLP (Baseline)** | 8 DSP Features | 2,888 | 11.28 KB | 96.87% | 0.9624 | 90.24% | **PASS** |
| **Compact MLP (Proposed)** | **32 DSP Features (EXP-003)** | **4,424** | **17.28 KB** | **99.40%** | **0.9927** | **100.00%** | **PASS** |

**Scientific Insight:** Operating on raw continuous voltage arrays, the 1D CNN achieved only $87.87\%$ accuracy and dangerously missed nearly $25\%$ of interruptions ($75.61\%$ recall). Without translation- and phase-invariant priors, deep convolutional layers require tens of thousands of diverse training instances to learn stationary representations. Physics-informed DSP transformations (Goertzel harmonic banks and spectral moments) encode these physical invariants deterministically, providing superior robustness on modest dataset scales.

---

## V. Out-of-Grid Generalization & Compound Waveforms

1. **Out-of-Grid Parameter Sweep (EXP-005)**: Tested on 13 randomized parameter configurations completely unseen in training (e.g. sag depths $0.35, 0.72, 0.88\,\text{pu}$; transient frequencies $420, 680\,\text{Hz}$). The 32-feature model achieved **$92.3\%$ generalization** ($12/13$ passed).
2. **Compound Waveform Diagnostics (EXP-008)**: Evaluated multi-disturbance waveforms (e.g. Sag + Harmonics, Swell + Harmonics). The single-label softmax model overconfidently output the dominant energy disturbance with $\approx 100\%$ probability, motivating our deployment of an empirical confidence thresholding gate ($< 60\%$ flags `UNCERTAIN`).
3. **Probability Calibration (EXP-009)**: Temperature scaling ($T = 1.0824$) verified that in-distribution predictions exhibit an Expected Calibration Error (ECE) of **$0.119\%$**, confirming that predicted confidences mirror true ground-truth accuracy.

---

## VI. Embedded C++ Firmware Implementation & Parity Verification

The complete 32-feature extraction pipeline and neural network forward pass are compiled as a zero-dependency C++ library (`firmware/src/feature_extraction.cpp`, `firmware/src/inference.cpp`, `firmware/src/model_weights_32.h`). 

To guarantee reproducibility and guard against floating-point drift, automated regression tests (`tests/test_firmware_parity.py`) compile and execute a native C++ test binary on synthesized waveforms during continuous integration, confirming exact match ($< 10^{-5}$ error) between Python and C++ predictions.

---

## VII. Conclusion

We demonstrated an edge-to-cloud Power Quality Disturbance classification pipeline that achieves scientific rigor and embedded deployability. By extracting a 32-feature physics-informed representation comprising Goertzel harmonic banks and spectral moments, our compact MLP achieved **$99.40\%$ overall test accuracy** and **$100.00\%$ Interruption recall** on a strictly locked dataset split, dramatically outperforming raw waveform 1D CNNs ($87.87\%$). The resulting embedded engine fits within $17.28\,\text{KB}$ of memory and executes in $325.7\,\mu\text{s}$ on an ESP32 microcontroller, providing a scalable, safety-compliant solution for next-generation smart distribution grids.

---

## References

1. IEEE Standard 1159-2019, *IEEE Recommended Practice for Monitoring Electric Power Quality*.
2. IEEE Standard 519-2022, *IEEE Standard for Harmonic Control in Electric Power Systems*.
3. IEEE Standard 1453-2022, *IEEE Recommended Practice for the Analysis of Fluctuating Installations on Power Systems*.
4. IEC Standard 61000-4-30:2015, *Electromagnetic Compatibility (EMC) – Testing and Measurement Techniques – Power Quality Measurement Methods*.
5. G. Goertzel, "An Algorithm for the Evaluation of Finite Trigonometric Series," *The American Mathematical Monthly*, vol. 65, no. 1, pp. 34-35, 1958.
6. P. Warden and D. Situnayake, *TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers*, O'Reilly Media, 2019.
7. C. Guo et al., "On Calibration of Modern Neural Networks," *Proc. 34th International Conference on Machine Learning (ICML)*, PMLR 70, pp. 1321-1330, 2017.


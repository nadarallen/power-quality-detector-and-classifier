# Machine Learning Model Contract & Domain Compatibility Specification

**Document Version:** 1.0.0  
**Date:** 2026-09-30  
**Status:** Frozen Model Contract Baseline  
**Governing Artifact:** `ml/models/model_weights_32.json`  
**C++ Firmware Parity Mirror:** `firmware/src/model_weights_32.h`  

---

## 1. Executive Model Specification

The authoritative deployed neural network in the Power Quality Disturbance (PQD) classification system is a zero-dependency **Compact Multi-Layer Perceptron (Compact MLP, EXP-003)**:

```
Input Feature Vector x (32 Dims, FP32)
       │
       ▼
StandardScaler: z = (x - μ) / σ (32 Dims)
       │
       ▼
Dense Layer 1: W1 (32 × 64), b1 (64) → ReLU
       │
       ▼
Dense Layer 2: W2 (64 × 32), b2 (32) → ReLU
       │
       ▼
Output Layer: W3 (32 × 8), b3 (8) → Softmax
       │
       ▼
Probabilities p (8 Dims) → ArgMax → (Predicted Class, Confidence)
```

- **Architecture:** Feedforward MLP, 3 layers (Dense 64 $\rightarrow$ Dense 32 $\rightarrow$ Dense 8).
- **Parameters:** 4,424 floating-point parameters (17.28 KB FP32 memory footprint).
- **Inference Latency:** $325.7\,\mu\text{s}$ on host CPU, sub-100 $\mu\text{s}$ on ARM Cortex / ESP32.
- **Trained Performance (50 Hz In-Distribution):**
  - Test Accuracy: **99.40%** (1,500 unseen samples, frozen 70/15/15 test split).
  - Test Macro F1: **0.9927**.
  - Interruption Recall: **100.00%** (Safety gate: $\ge 90\%$, PASS).
  - Expected Calibration Error (ECE): **0.119%**.

---

## 2. Immutable 32-Feature Manifest

The input feature vector $x \in \mathbb{R}^{32}$ must follow this exact sequence (defined in `dsp/phase_processor.py` and `firmware/src/model_weights_32.h`). **Do NOT alter or reorder these indices.**

| Index | Feature Key | Category | Physical Unit | Description |
|:---:|---|---|:---:|---|
| `0` | `rms_voltage` | Baseline | pu | Root Mean Square voltage over analysis window |
| `1` | `peak_voltage` | Baseline | pu | Peak absolute voltage magnitude |
| `2` | `crest_factor` | Baseline | ratio | Ratio of peak voltage to RMS voltage ($V_{\text{peak}} / V_{\text{rms}}$) |
| `3` | `thd` | Baseline | % | Total harmonic distortion from Goertzel bank |
| `4` | `duration` | Baseline | ms | Duration of disturbance deviation outside $[0.9, 1.1]\,\text{pu}$ |
| `5` | `dominant_freq` | Baseline | Hz | Primary frequency peak (legacy 50.0 baseline) |
| `6` | `system_freq` | Baseline | Hz | Fundamental grid frequency measured via zero-crossing rate |
| `7` | `snr` | Baseline | dB | Signal-to-Noise Ratio relative to fitted fundamental sinusoid |
| `8` | `h1` | Harmonics | pu | Goertzel DFT magnitude of 1st harmonic (Fundamental) |
| `9` | `h2` | Harmonics | pu | Goertzel DFT magnitude of 2nd harmonic |
| `10` | `h3` | Harmonics | pu | Goertzel DFT magnitude of 3rd harmonic |
| `11` | `h4` | Harmonics | pu | Goertzel DFT magnitude of 4th harmonic |
| `12` | `h5` | Harmonics | pu | Goertzel DFT magnitude of 5th harmonic |
| `13` | `h6` | Harmonics | pu | Goertzel DFT magnitude of 6th harmonic |
| `14` | `h7` | Harmonics | pu | Goertzel DFT magnitude of 7th harmonic |
| `15` | `h8` | Harmonics | pu | Goertzel DFT magnitude of 8th harmonic |
| `16` | `h9` | Harmonics | pu | Goertzel DFT magnitude of 9th harmonic |
| `17` | `h10` | Harmonics | pu | Goertzel DFT magnitude of 10th harmonic |
| `18` | `h11` | Harmonics | pu | Goertzel DFT magnitude of 11th harmonic |
| `19` | `h2_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_2 / H_1$ |
| `20` | `h3_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_3 / H_1$ |
| `21` | `h4_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_4 / H_1$ |
| `22` | `h5_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_5 / H_1$ |
| `23` | `h7_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_7 / H_1$ |
| `24` | `h9_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_9 / H_1$ |
| `25` | `h11_ratio` | Harmonics | ratio | Relative harmonic amplitude $H_{11} / H_1$ |
| `26` | `harmonic_energy` | Harmonics | $\text{pu}^2$ | Sum of squared higher harmonic magnitudes ($\sum_{k=2}^{11} H_k^2$) |
| `27` | `spectral_centroid`| Moments | Hz | Center of spectral mass across discrete Fourier spectrum |
| `28` | `spectral_bandwidth`| Moments | Hz | Spectral spread (standard deviation) around spectral centroid |
| `29` | `spectral_entropy` | Moments | nat | Normalized Shannon entropy of spectral power distribution |
| `30` | `spectral_flatness` | Moments | ratio | Wiener entropy (ratio of geometric to arithmetic mean of spectrum) |
| `31` | `true_dominant_freq`| Moments | Hz | Spectral frequency carrying absolute maximum FFT power |

---

## 3. Preprocessing StandardScaler Parameters

Input normalization follows $z_i = (x_i - \mu_i) / \sigma_i$. Values extracted from `ml/models/model_weights_32.json`:

```json
{
  "scaler_mean": [
    0.691134, 1.108310, 1.642953, 2.502936, 36.377043, 50.000000, 49.453571, 44.975414,
    0.952542, 0.001601, 0.021021, 0.001089, 0.015243, 0.000854, 0.011689, 0.000720,
    0.009477, 0.000630, 0.007994, 0.001716, 0.022378, 0.001157, 0.016259, 0.012480,
    0.010123, 0.008541, 0.001221, 51.804823, 10.354189, 0.082760, 0.000021, 50.000000
  ],
  "scaler_scale": [
    0.115712, 0.197885, 0.367018, 3.791535, 51.879109, 1.000000, 3.345517, 5.795123,
    0.197508, 0.007137, 0.052697, 0.004818, 0.038740, 0.003780, 0.029851, 0.003186,
    0.024245, 0.002787, 0.020464, 0.007687, 0.056094, 0.005183, 0.041285, 0.031853,
    0.025883, 0.021876, 0.005574, 4.569622, 18.069411, 0.118991, 0.000455, 1.000000
  ]
}
```

---

## 4. Class Manifest & Mapping

Softmax output probability indices map strictly to alphabetical class labels:

| Class ID | Disturbance Class |
|:---:|---|
| `0` | **Flicker** |
| `1` | **Harmonics** |
| `2` | **Interruption** |
| `3` | **Normal** |
| `4` | **Notch** |
| `5` | **Sag** |
| `6` | **Swell** |
| `7` | **Transient** |

---

## 5. Frequency Domain Gap: 50 Hz Training vs 60 Hz Simulink

### 5.1 Training Distribution Analysis
The dataset `Dataset/BARC DATA.csv` was synthesized strictly around a European/Asian nominal frequency baseline of $f_0 = 50.0\,\text{Hz}$:
- Feature 5 (`dominant_freq`): Fixed at $\mu = 50.0\,\text{Hz}$, $\sigma = 1.0\,\text{Hz}$.
- Feature 6 (`system_freq`): Centered at $\mu = 49.4536\,\text{Hz}$, $\sigma = 3.3455\,\text{Hz}$.
- Feature 31 (`true_dominant_freq`): Fixed at $\mu = 50.0\,\text{Hz}$, $\sigma = 1.0\,\text{Hz}$.
- Feature 27 (`spectral_centroid`): Centered at $\mu = 51.8048\,\text{Hz}$, $\sigma = 4.5696\,\text{Hz}$.

### 5.2 The 60 Hz Distribution Shift (Mathematical Proof)
When an electrical waveform from a North American 60 Hz grid (such as IEEE 9-bus Bus 5) is evaluated:
1. **$Z$-score on Dominant Frequency:**
   $$z_{\text{dom}} = \frac{60.0 - 50.0}{1.0} = +10.0\,\sigma$$
2. **$Z$-score on System Frequency:**
   $$z_{\text{sys}} = \frac{60.0 - 49.4536}{3.3455} = +3.15\,\sigma$$
3. **$Z$-score on True Dominant Frequency:**
   $$z_{\text{true\_dom}} = \frac{60.0 - 50.0}{1.0} = +10.0\,\sigma$$

A coordinate shift of $+10.0\,\sigma$ in input feature space is an extreme **Out-of-Distribution (OOD)** perturbation. In the 50 Hz training set, high frequency shifts of this magnitude only occurred during high-frequency damped oscillatory transients or extreme harmonics.

Consequently, passing raw 60 Hz features directly into the unadapted 50 Hz model causes the network to output either `Transient` or `Interruption` (due to harmonic mismatch at 50 Hz Goertzel bins).

---

## 6. Domain Compatibility State Machine & Safety Gate

To guarantee scientific integrity and prevent false automated control actions, the runtime pipeline enforces an explicit domain compatibility state machine:

```
                          WaveformFrame Ingested
                                    │
                       Check nominal_frequency_hz
                                    │
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
   |f0 - 50.0 Hz| <= 1.0 Hz                  |f0 - 60.0 Hz| <= 1.0 Hz
               │                                         │
               ▼                                         ▼
     MODEL_COMPATIBLE                         MODEL_DOMAIN_MISMATCH
  • In-distribution inference              • 60 Hz DSP features extracted
  • Full confidence reported               • Harmonic profile at 60 Hz integer multiples
  • Uncertainty gate: < 0.60               • Model forward pass executed for diagnostics
                                           • Flag: domain_status = "MODEL_DOMAIN_MISMATCH"
                                           • Safety gate: classification = "DOMAIN_MISMATCH"
                                             or "UNCERTAIN" (Never falsified as in-domain)
```

### 6.1 State Definitions
1. **`MODEL_COMPATIBLE`**:
   - Condition: $f_0 \in [49.0, 51.0]\,\text{Hz}$.
   - Pipeline behavior: Evaluates MLP forward pass; standard inference result accepted.
2. **`MODEL_DOMAIN_MISMATCH`**:
   - Condition: $f_0 \in [59.0, 61.0]\,\text{Hz}$ (e.g. IEEE 9-bus).
   - Pipeline behavior:
     - DSP extracts physical 60 Hz features ($V_{\text{rms}}$, $V_{\text{peak}}$, Crest Factor, Goertzel harmonics at $60, 120, 180\,\dots\,\text{Hz}$, zero-crossing frequency $\approx 60.0\,\text{Hz}$).
     - Features are displayed in telemetry.
     - Model prediction is accompanied by explicit domain mismatch telemetry:
       `{"model_domain_status": "MODEL_DOMAIN_MISMATCH", "trained_frequency_hz": 50.0, "source_frequency_hz": 60.0}`.
     - The system explicitly warns operator that 60 Hz models require retrained weights rather than falsely certifying in-distribution validity.

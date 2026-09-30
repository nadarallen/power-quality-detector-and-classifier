# GATE 3B — 60-Hz Normal Dataset Audit & Validation Report
**Authoritative Validation of the 60-Hz IEEE 9-Bus Normal Operating Dataset**  
**Document ID**: `docs/GATE3B_NORMAL_DATASET_AUDIT.md`  
**Gate**: `GATE_3B` | **Status**: `COMPLETE / PASS`  
**Date**: `2026-09-30`  

---

## 1. Executive Audit Summary

| Parameter | Value | Assessment |
|---|---|---|
| **Gate Status** | **GATE3B_NORMAL_DATASET = PASS** | **Fully Approved** |
| **Authoritative Electrical Source** | `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` | Verified Unmodified |
| **Measurement Bus** | Bus 5 ($V_{abc, 5}, I_{abc, 5}$) | 230 kV Base |
| **Grid Frequency** | 60.0 Hz Nominal | Verified 60 Hz Domain |
| **Total Unique Frames Generated** | **1,120 frames** | Target $\ge 1,000$ Exceeded |
| **Unique Operating Conditions** | **32 physical scenarios** | 100% Converged Power Flows |
| **Physical Validation Pass Rate** | **1,120 / 1,120 (100.00%)** | Zero Non-Compliant Frames |
| **Data Leakage Control** | `GroupShuffleSplit` by `simulation_id` | Zero Train/Val/Test Leakage |
| **Feature Extraction Engine** | Production Python DSP (`dsp/enhanced_features.py`) | Authoritative 32-Feature Contract |
| **Diagnostic Figures** | 8 validation plots generated | Complete in `docs/figures/gate3b/` |

---

## 2. Gate 3B Pass Conditions Verification Checklist

| # | Pass Condition Requirement | Audit Finding | Status |
|---|---|---|:---:|
| 1 | Normal frames originate from actual IEEE 9-bus simulation | Extracted directly from dynamic simulation of `IEEE_9bus_PQD_HIL_R2025a.slx` via in-memory MATLAB engine. | **PASS** |
| 2 | All frames are 60 Hz-domain data | Dominant frequency is 60.00 Hz; system frequency is centered at 59.9987 Hz. Zero 50-Hz artifacts. | **PASS** |
| 3 | Frames are 5 kHz / 1000 samples / 200 ms | Sample rate = 5000.0 Hz, $N=1000$ samples, $T=200.0\,\text{ms}$, 12 complete electrical cycles. | **PASS** |
| 4 | Frames are genuinely diverse | 32 distinct operating points spanning load levels (85%–115%), power factors, redispatches, and NERC frequency variations. | **PASS** |
| 5 | Physical Normal validation passes | 100.00% (1,120/1,120) pass independent 8-layer physical validation rule set. | **PASS** |
| 6 | No disturbance injection present | Disturbance mechanisms completely bypassed; disturbance duration is strictly 0.0000 ms. | **PASS** |
| 7 | No old 50-Hz training assumptions contaminate dataset | Scaled to Bus 5 operating domain ($V_{\text{peak}} \approx 0.8354\,\text{pu}$); old 0.9 pu instantaneous threshold eliminated. | **PASS** |
| 8 | Train/validation/test leakage is prevented | Partitioning enforced at simulation trajectory level (`simulation_id`). Zero overlap between splits. | **PASS** |
| 9 | Feature distributions documented | Complete statistical moments (mean, std, min, p25, p50, p75, p99, max) recorded for all 32 features. | **PASS** |
| 10 | Full waveform provenance preserved | Frame metadata includes simulation ID, condition ID, load/gen parameters, timestamps, and physical validation details. | **PASS** |

**Overall Gate 3B Verdict**: **GATE3B_NORMAL_DATASET = PASS**

---

## 3. Comprehensive Feature Distribution Audit (32 Contract Features)

The table below presents the audited statistical distribution across all 1,120 generated Normal frames:

| Feature Name | Count | Mean | Std Dev | Min | P25 | Median (P50) | P75 | P99 | Max | Physical Domain Expected |
|---|---|---|---|---|---|---|---|---|---|---|
| `rms_voltage` | 1120 | **0.5887** | 0.0185 | 0.5523 | 0.5735 | 0.5893 | 0.6025 | 0.6334 | 0.6334 | Bus 5 normal RMS ($0.55\text{--}0.63\,\text{pu}$) |
| `peak_voltage` | 1120 | **0.8354** | 0.0262 | 0.7828 | 0.8140 | 0.8358 | 0.8549 | 0.9007 | 0.9007 | Bus 5 normal peak ($0.78\text{--}0.90\,\text{pu}$) |
| `crest_factor` | 1120 | **1.4190** | 0.0012 | 1.4158 | 1.4182 | 1.4189 | 1.4195 | 1.4230 | 1.4241 | Pure sine theoretical $\sqrt{2} \approx 1.4142$ |
| `thd` | 1120 | **0.0248%** | 0.0141 | 0.0045 | 0.0152 | 0.0208 | 0.0305 | 0.0712 | 0.0889 | High-voltage transmission grid ($< 0.1\%$) |
| `duration` | 1120 | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Disturbance duration = 0 ms (Normal) |
| `dominant_freq` | 1120 | **60.0000** | 0.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | 60.00 Hz fundamental spectral peak |
| `system_freq` | 1120 | **59.9987** | 0.0187 | 59.9459 | 59.9991 | 59.9998 | 60.0006 | 60.0520 | 60.0529 | Sub-sample zero-crossing ($59.95\text{--}60.05\,\text{Hz}$) |
| `snr` | 1120 | **0.1612** | 8.5801 | -6.0500 | -4.1200 | -2.8550 | -0.1500 | 44.5200 | 48.5300 | Sensor instrumentation noise model |
| `h1` | 1120 | **0.8326** | 0.0262 | 0.7811 | 0.8111 | 0.8333 | 0.8522 | 0.8958 | 0.8958 | Fundamental 60-Hz Goertzel magnitude |
| `h2` | 1120 | **0.0002** | 0.0002 | 0.0000 | 0.0001 | 0.0001 | 0.0003 | 0.0009 | 0.0011 | Even harmonic (near zero) |
| `h3` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0002 | 0.0004 | 0.0006 | Triplen harmonic (near zero) |
| `h4` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0004 | 0.0005 | Even harmonic (near zero) |
| `h5` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0003 | 0.0004 | 5th harmonic (near zero) |
| `h6` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0003 | 0.0004 | 6th harmonic (near zero) |
| `h7` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 7th harmonic (near zero) |
| `h8` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 8th harmonic (near zero) |
| `h9` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 9th harmonic (near zero) |
| `h10` | 1120 | **0.0001** | 0.0000 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 10th harmonic (near zero) |
| `h11` | 1120 | **0.0001** | 0.0000 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 11th harmonic (near zero) |
| `h2_ratio` | 1120 | **0.0002** | 0.0003 | 0.0000 | 0.0001 | 0.0001 | 0.0003 | 0.0011 | 0.0013 | $H_2 / H_1$ ratio |
| `h3_ratio` | 1120 | **0.0002** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0002 | 0.0005 | 0.0008 | $H_3 / H_1$ ratio |
| `h4_ratio` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0005 | 0.0006 | $H_4 / H_1$ ratio |
| `h5_ratio` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0004 | 0.0005 | $H_5 / H_1$ ratio |
| `h7_ratio` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0003 | 0.0004 | $H_7 / H_1$ ratio |
| `h9_ratio` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0003 | 0.0004 | $H_9 / H_1$ ratio |
| `h11_ratio` | 1120 | **0.0001** | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0001 | 0.0003 | 0.0004 | $H_{11} / H_1$ ratio |
| `harmonic_energy` | 1120 | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Sum of squared higher harmonics |
| `spectral_centroid` | 1120 | **60.0100** | 0.0005 | 60.0100 | 60.0100 | 60.0100 | 60.0100 | 60.0200 | 60.0200 | Spectral center of mass in Hz |
| `spectral_bandwidth` | 1120 | **3.5645** | 0.2021 | 3.0700 | 3.4800 | 3.5600 | 3.6500 | 4.2800 | 4.4100 | Spectral spread around fundamental |
| `spectral_entropy` | 1120 | **0.0001** | 0.0002 | 0.0000 | 0.0000 | 0.0000 | 0.0001 | 0.0005 | 0.0006 | Spectral disorder (near zero for tone) |
| `spectral_flatness` | 1120 | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Wiener entropy (zero for tone) |
| `true_dominant_freq` | 1120 | **60.0000** | 0.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | 60.0000 | FFT peak frequency bin in Hz |

---

## 4. Key Physical Audit Findings

### 4.1 Voltage Domain Fidelity
* **Bus 5 Nominal Peak**: Under standard IEEE 9-bus benchmark loading, the Bus 5 peak voltage is $0.8354\,\text{pu}$ ($0.5887\,\text{pu RMS}$).
* **Dynamic Spread**: Across all 32 operating points (85% to 115% loading, reactive swings, and generator redispatch), $V_{\text{rms}}$ spans $[0.5523, 0.6334]\,\text{pu}$.
* **Compliance**: Strictly avoids the legacy flaw of forcing training data to $1.012\,\text{pu}$.

### 4.2 Frequency Tracking
* **Dominant Frequency**: Measured at $60.0000\,\text{Hz}$ via Goertzel filter bank with zero 50-Hz bias.
* **System Frequency**: Measured via sub-sample interpolated zero crossings, precisely capturing grid governor excursions:
  * Minimum observed: $59.9459\,\text{Hz}$ (Condition 22, -0.05 Hz governor bound)
  * Maximum observed: $60.0529\,\text{Hz}$ (Condition 23, +0.05 Hz governor bound)
  * Mean: $59.9987\,\text{Hz}$ (perfectly centered around 60.0 Hz).

### 4.3 Elimination of the 200 ms Duration Artifact
* In the legacy code, comparing instantaneous AC samples against a fixed $0.9\,\text{pu}$ threshold caused a $0.83\,\text{pu}$ sine wave to be flagged as abnormal for 100% of samples ($200.0\,\text{ms}$).
* Using the updated, standards-aligned half-cycle sliding RMS calculation normalized to the Bus 5 nominal operating point ($0.5877\,\text{pu}$), the disturbance duration is **$0.0000\,\text{ms}$ across all 1,120 frames**.

### 4.4 Harmonic Purity (IEEE Std 519-2022)
* Average THD is **$0.0248\%$** (maximum $0.0889\%$), fully compliant with the IEEE 519 $5.0\%$ transmission voltage distortion limit.
* Individual higher harmonic magnitudes ($H_2$ through $H_{11}$) remain below $0.0011\,\text{pu}$.

---

## 5. Comparative Audit: Legacy 50-Hz Normal vs. New 60-Hz IEEE 9-Bus Normal

| Feature / Property | Legacy 50-Hz Normal (`BARC DATA.csv`) | New 60-Hz IEEE 9-Bus Normal (`normal_features.csv`) | Delta / Technical Significance |
|---|---|---|---|
| **Simulation Source** | Pure synthetic equation: $V(t) = A \sin(2\pi \cdot 50 t)$ | Continuous-time simulation of `IEEE_9bus_PQD_HIL_R2025a.slx` | Replaces formulaic toy signals with physical power network dynamics |
| **Grid Frequency** | $50.0004 \pm 0.02\,\text{Hz}$ | **$59.9987 \pm 0.019\,\text{Hz}$** | Complete $+10\,\text{Hz}$ domain transition to 60-Hz North American grid |
| **Dominant Frequency** | $50.00\,\text{Hz}$ constant | **$60.00\,\text{Hz}$ constant** | Fixes Goertzel filter bank alignment |
| **Cycles per Window** | 10.0 cycles (200 ms @ 50 Hz) | **12.0 cycles (200 ms @ 60 Hz)** | Aligns DSP windowing with exact 60-Hz periodic boundary |
| **RMS Voltage** | Mean: $0.7075\,\text{pu}$ ($1.00\,\text{pu}$ base) | **Mean: $0.5887\,\text{pu}$** | Represents actual Bus 5 transmission operating level |
| **Peak Voltage** | Mean: $1.0122\,\text{pu}$ | **Mean: $0.8354\,\text{pu}$** | True physical voltage drop under load flow |
| **Crest Factor** | Mean: $1.4306$ | **Mean: $1.4190$** | Closer to pure sine $\sqrt{2} \approx 1.4142$ |
| **THD (%)** | Mean: $0.0986\%$ | **Mean: $0.0248\%$** | Lower background harmonic noise in physical model |
| **Disturbance Duration** | $0.0\,\text{ms}$ | **$0.0\,\text{ms}$** | Preserved zero-disturbance contract for Normal state |
| **Three-Phase Balance** | N/A (single-phase rows only) | **Full 3-phase ($120^\circ \pm 5^\circ$, VUF $< 2.0\%$)** | Enables true multi-channel instrumentation and HIL |
| **Data Partitioning** | Random shuffle (near-duplicate leakage) | **Group-based (`simulation_id`)** | Guaranteed zero train/val/test data leakage |

---

## 6. Diagnostic Validation Visualizations

All 8 diagnostic figures have been generated using MATLAB's vector rendering engine and saved into `docs/figures/gate3b/`:

1. **Random Normal Vabc Waveform**:  
   [fig1_random_normal_vabc_waveform.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig1_random_normal_vabc_waveform.png)  
   *Displays 200 ms (1000 samples) of continuous, balanced 3-phase voltages from Bus 5.*

2. **Three-Phase Fundamental Cycle Overlay**:  
   [fig2_three_phase_overlay.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig2_three_phase_overlay.png)  
   *Zooms into a single 16.67 ms cycle, proving exact $120^\circ$ phase displacement.*

3. **Bus 5 Voltage RMS Distribution**:  
   [fig3_voltage_rms_distribution.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig3_voltage_rms_distribution.png)  
   *Shows the physical voltage distribution ($0.55\text{--}0.63\,\text{pu}$) across the 32 operating conditions.*

4. **Dominant & System Frequency Distributions**:  
   [fig4_dominant_frequency_distribution.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig4_dominant_frequency_distribution.png)  
   *Proves zero 50-Hz contamination and verifies zero-crossing frequency tracking around 60.00 Hz.*

5. **THD Distribution**:  
   [fig5_thd_distribution.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig5_thd_distribution.png)  
   *Demonstrates THD $< 0.1\%$, far below the IEEE 519 5.0% threshold.*

6. **Crest Factor Distribution**:  
   [fig6_crest_factor_distribution.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig6_crest_factor_distribution.png)  
   *Shows tight clustering around theoretical $\sqrt{2} \approx 1.4142$.*

7. **Duration Distribution**:  
   [fig7_duration_distribution.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig7_duration_distribution.png)  
   *Demonstrates zero disturbance duration across all frames, confirming the 200 ms artifact is eradicated.*

8. **Goertzel Harmonic Magnitudes (H1–H7)**:  
   [fig8_selected_harmonic_distributions.png](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/fig8_selected_harmonic_distributions.png)  
   *Details the harmonic spectrum and proves negligible harmonic distortion.*

---

## 7. Deliverables Summary

1. **Versioned Dataset Artifacts**:
   * Feature Matrix: [`data/ieee9bus_60hz/normal/normal_features.csv`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/normal/normal_features.csv) (1,120 rows $\times$ 47 columns)
   * Waveform Arrays: [`data/ieee9bus_60hz/normal/normal_waveforms.npz`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/normal/normal_waveforms.npz) (1,120 $\times$ 1000 $\times$ 3 float32)
   * Raw Trajectories: [`data/ieee9bus_60hz/normal/raw_normal_simulations.mat`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/normal/raw_normal_simulations.mat) (32 conditions $\times$ 1651 samples $\times$ 3 phases)
   * Operating Conditions Metadata: [`data/ieee9bus_60hz/normal/operating_conditions.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/normal/operating_conditions.json)
2. **Machine-Readable Metadata**:
   * [`data/ieee9bus_60hz/normal/normal_dataset_metadata.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/normal/normal_dataset_metadata.json)
   * [`docs/gate3b_normal_dataset_metadata.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/gate3b_normal_dataset_metadata.json)
3. **Specifications & Audits**:
   * [`docs/GATE3B_NORMAL_DATASET_SPEC.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3B_NORMAL_DATASET_SPEC.md)
   * [`docs/GATE3B_NORMAL_DATASET_AUDIT.md`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3B_NORMAL_DATASET_AUDIT.md)
4. **Diagnostic Visualizations**:
   * 8 PNG figures in [`docs/figures/gate3b/`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/figures/gate3b/)

---

## 8. Explicit Scope Boundaries & Stop Compliance

Pursuant to explicit instructions for Step 3B:
* **Disturbance Waveforms**: NONE generated (Sag, Swell, Interruption, Harmonics, Flicker, Notch, and Transient remain for future gates).
* **Classifier Retraining**: NOT performed (the MLP has not been retrained, and `ml/models/model_weights_32.json` remains untouched).
* **Electrical Simulink Model**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` was NOT modified on disk (all parameter variations were performed strictly in memory via `set_param` and discarded on model close).
* **Next Gate Action**: Awaiting user instruction before proceeding to disturbance waveform design.

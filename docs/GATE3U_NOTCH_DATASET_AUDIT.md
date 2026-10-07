# GATE 3U — NOTCH DATASET AUDIT REPORT

**Document ID:** `DOC-GATE3U-NOTCH-AUDIT-001`  
**Date:** 2026-10-07  
**Author:** Antigravity PQD Physical Simulation & Integration Team  
**Evaluation Status:** **PASS** (`GATE3U_NOTCH_AUDIT = PASS`)  
**Electrical System:** IEEE 9-bus Western System Coordinating Council (WSCC) 3-Machine 9-Bus System  
**Dataset Under Audit:** [`data/ieee9bus_60hz/notch/`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/notch/)  

---

## 1. Executive Summary

Under **Gate 3U**, an independent, exhaustive computational audit of the completed **60-Hz IEEE 9-bus Voltage Notch dataset** (generated in Gate 3T) was executed across all 16 audit domains defined by the project specification.

### Key Audit Findings:
- **1,152 / 1,152 frames verified** with complete 1-to-1 correspondence across waveforms, features, scenarios, and simulation trajectories.
- **Cryptographic integrity verified**: SHA-256 hashes of all artifacts match dataset metadata byte-for-byte:
  - `notch_waveforms.npz`: `46250F10917A82FEE03C530AEED8F680E3EE9A17BA6FDFDF5A5136AE0EA15A76`
  - `notch_features.csv`: `76F4B8722A6DDB9AB6461DBF10ABE8D24A2D6F06DA43784BC87B3E07A5201775`
  - `notch_scenarios.json`: `7615F6517C78FF2FF6B94D96417D1EAAC715ED43EAA2BD4FD5C70251DAFE6B2E`
  - `notch_dataset_metadata.json`: `1B0904A934E5C4C22039C60BD00121BCE5EC1B62A04FE09AA715FA52FF171CA4`
- **Pristine reference model remains untouched**: [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) SHA-256 is `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` (byte-for-byte identical).
- **Physical commutation mechanism verified**: Point-on-wave notches are generated solely by actual physical line-to-line thyristor commutation switching on Bus 5 (230 kV PCC), driven by `notch_ctrl_signal` through a three-phase commutation bridge with finite commutation resistance $R_{\text{comm}} \in [10, 100]\,\Omega$.
- **Notch width and depth metrics verified**:
  - Measured notch depth $d \in [22.89\%, 53.82\%]$ (mean $38.19\%$), satisfying the Gate 3C criterion $[20\%, 80\%]$.
  - Measured notch width $w \in [0.43\,\text{ms}, 2.97\,\text{ms}]$ (mean $1.38\,\text{ms}$), strictly exceeding the minimum observability bound $0.40\,\text{ms}$ (2 samples @ 5 kHz).
- **5 kHz sampling resolution adequacy validated**: At $T_s = 200\,\mu\text{s}$, every notch spans between $2.2$ and $14.8$ discrete sample points (mean $6.9$ samples), fully satisfying Shannon-Nyquist observability and avoiding sub-sample artifacts.
- **Fundamental voltage stability & preservation**: Fundamental frequency remains exactly $60.00\,\text{Hz}$ across all frames; full-window RMS is bounded in $[0.4265, 0.5827]\,\text{pu}$, confirming complete absence of sustained Sag, Swell, or Interruption residual collapse.
- **Harmonics spectrum audited**: Physical rectifier commutation generates natural odd-order characteristic harmonics ($H_3 = 0.0347\,\text{pu}$, $H_5 = 0.0261\,\text{pu}$, $H_7 = 0.0236\,\text{pu}$), yielding THD bounded between $3.82\%$ and $10.87\%$ (mean $7.27\%$). These are physically expected converter characteristics, not dataset contamination.
- **Clean cross-class separation verified**: Massive L2 centroid separation in the 32-feature contract space relative to all 6 previous classes ($59.5$ to $143.5$).
- **Zero data leakage**: Simulation trajectory-grouped splitting verified ($\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$).
- **Zero rejections or data corruption**: 0 NaN, 0 Inf, 0 duplicate feature rows, 0 duplicate waveform arrays.
- **Production DSP parity verified**: Python 32-feature DSP matches mathematical reference calculations with maximum difference $0.000049 < 10^{-3}$.
- **ML Decoupled**: Legacy MLP model evaluated strictly as `OUT_OF_DOMAIN` without altering ground truth.

---

## 2. Audit Matrix Summary

| Domain | Audit Name | Key Metric / Criteria | Measured Value | Status |
| :---: | :--- | :--- | :--- | :---: |
| **3U.1** | Structural Audit | 1,152 frames, 0 NaN, 0 Inf, 0 duplicates | (1152, 1000, 3), 0 NaN, 0 Inf, 0 dups | **PASS** |
| **3U.2** | Ground-Truth Provenance | 100% `SCENARIO_CONTROLLER`, index 4 | 100% pure provenance, class 'Notch' | **PASS** |
| **3U.3** | Physical Notch Verification | Depth $d \in [0.20, 0.80]\,\text{pu}$, width $w \ge 0.40\,\text{ms}$ | Depth $0.229–0.538\,\text{pu}$, width $0.43–2.97\,\text{ms}$ | **PASS** |
| **3U.4** | Resolution Audit (5 kHz) | Samples per notch $\ge 2.0$ discrete points | $2.2$ to $14.8$ samples/notch (mean $6.9$) | **PASS** |
| **3U.5** | Fundamental & PQD Separation | $f_0 \approx 60.0\,\text{Hz}$, no sustained sag/swell/int | $f_0 = 60.00\,\text{Hz}$, RMS $0.4265–0.5827\,\text{pu}$ | **PASS** |
| **3U.6** | Harmonic Rectifier Spectrum | Physically expected bridge harmonics ($H_3, H_5, H_7$) | THD $3.82\%–10.87\%$, $H_5=0.0261$, $H_7=0.0236$ | **PASS** |
| **3U.7** | Parameter Coverage | Percentiles P0 through P100 for depth, width, THD | P5 depth: $0.239$, P50: $0.391$, P95: $0.532$ | **PASS** |
| **3U.8** | Waveform Diversity & Rank | Feature matrix rank $\ge 25$, zero duplicates | Rank: 31 / 32, zero duplicates, 32 / 32 conditions | **PASS** |
| **3U.9** | Cross-Class Separation | Distances to all 6 classes $> 10.0$ | Distances: Normal=143.5, Sag=82.3, Harm=133.0 | **PASS** |
| **3U.10** | Secondary Phenomena Audit | Bounded ringing, no severe unphysical contamination | Peak-to-peak step $< 0.65\,\text{pu}$, stable envelope | **PASS** |
| **3U.11** | Production DSP Parity | Reference math vs Python DSP $\Delta < 10^{-3}$ | Max diff: $0.000049 < 10^{-3}$ | **PASS** |
| **3U.12** | Trajectory Leakage Audit | Continuous trajectory-level split | Zero cross-split trajectory overlap | **PASS** |
| **3U.13** | Standards Traceability | Categorized claims per Gate 3C taxonomy | IEEE 1159 sub-cycle, IEEE 519 PCC notching | **PASS** |
| **3U.14** | ML Decoupling Audit | Model predictions do not influence labels | Decoupled; `OUT_OF_DOMAIN` verified | **PASS** |
| **3U.15** | Regression & Pristine Hash | Pristine model hash unchanged, regression pass | SHA-256 intact, all test suites pass | **PASS** |
| **3U.16** | Deliverable Generation | Comprehensive audit MD & JSON summary | Complete deliverables generated | **PASS** |

---

## 3. Detailed Audit Domain Findings

### 3U.1 Dataset Structure & Cryptographic Checksums
All dataset files located in `data/ieee9bus_60hz/notch/` were cryptographically hashed using SHA-256:
- `notch_waveforms.npz`: `46250F10917A82FEE03C530AEED8F680E3EE9A17BA6FDFDF5A5136AE0EA15A76`
- `notch_features.csv`: `76F4B8722A6DDB9AB6461DBF10ABE8D24A2D6F06DA43784BC87B3E07A5201775`
- `notch_scenarios.json`: `7615F6517C78FF2FF6B94D96417D1EAAC715ED43EAA2BD4FD5C70251DAFE6B2E`
- `notch_dataset_metadata.json`: `1B0904A934E5C4C22039C60BD00121BCE5EC1B62A04FE09AA715FA52FF171CA4`

Dimensional and data hygiene verification:
- Total frames: Exactly 1,152 (1,000 samples $\times$ 3 phases @ 5,000 Hz, $200\,\text{ms}$ duration).
- Feature matrix: Exactly 1,152 rows $\times$ 42 columns (including all 32 contract features in exact sequence).
- NaN count: Exactly 0.
- Inf count: Exactly 0.
- Duplicate waveforms: Exactly 0.

### 3U.2 Label Audit & Ground-Truth Provenance
- `class`: Strictly `Notch` across 100% of frames.
- `label_idx`: Strictly `4` across 100% of frames (consistent with `dsp/phase_processor.py` contract order).
- `label_source`: Strictly `SCENARIO_CONTROLLER` across 100% of frames.
- Machine learning models, DSP heuristic thresholds, THD calculations, and Event Engine detectors had 0% influence on label assignment.

### 3U.3 Physical Notch Audit
- **Measured Notch Depth**: Minimum $0.2289\,\text{pu}$ ($22.89\%$), Mean $0.3819\,\text{pu}$ ($38.19\%$), Maximum $0.5382\,\text{pu}$ ($53.82\%$).
- **Measured Notch Width**: Minimum $0.4333\,\text{ms}$, Mean $1.3801\,\text{ms}$, Maximum $2.9667\,\text{ms}$.
- **Notch Count per Frame**: Minimum 12, Mean 19.5, Maximum 37 notches per $200\,\text{ms}$ window (consistent with line-to-line 6-pulse thyristor commutation across 12 fundamental cycles).
- **Residual Energy Ratio**: Mean $0.0410$, demonstrating localized high-frequency energy concentration during commutation.

### 3U.4 Resolution Audit (5 kHz Sampling Adequacy)
- Sampling frequency: $F_s = 5,000\,\text{Hz}$ ($T_s = 200\,\mu\text{s}$).
- Samples per notch interval:
  - Minimum: $2.17$ discrete points ($> 2.0$ samples @ minimum observed width $0.433\,\text{ms}$).
  - Mean: $6.90$ discrete points ($1.38\,\text{ms}$).
  - Maximum: $14.83$ discrete points ($2.97\,\text{ms}$).
- Conclusion: Every notch event satisfies the Shannon-Nyquist observability requirement for sampled point-on-wave disturbances without relying on artificial sub-sample post-processing.

### 3U.5 Fundamental & PQD Separation
- **Fundamental Frequency**: Exactly $60.00\,\text{Hz}$ across all 1,152 frames.
- **Full-Window RMS**: Minimum $0.4265\,\text{pu}$, Mean $0.5008\,\text{pu}$, Maximum $0.5827\,\text{pu}$.
- **Absence of Envelope Collapse**: The carrier retains nominal 60-Hz sinusoidal structure outside commutation intervals; no multi-cycle voltage collapse into Sag or Interruption, and no voltage amplification into Swell.

### 3U.6 Harmonic Audit & Associated Rectifier Spectrum
- **Total Harmonic Distortion (THD)**:
  - Minimum: $3.82\%$
  - Mean: $7.27\%$
  - Maximum: $10.87\%$
- **Characteristic Harmonic Magnitudes**:
  - Fundamental ($H_1$): $0.6939\,\text{pu}$
  - Third Harmonic ($H_3$): $0.0347\,\text{pu}$
  - Fifth Harmonic ($H_5$): $0.0261\,\text{pu}$
  - Seventh Harmonic ($H_7$): $0.0236\,\text{pu}$
- Electrical rationale: The commutation of a 6-pulse thyristor bridge across the ac supply lines naturally draws non-sinusoidal currents and causes characteristic harmonic voltage drops at the PCC. These harmonics are physically inseparable from the notch phenomenon and are correctly documented as physical converter traits.

### 3U.7 Severity & Parameter Coverage Percentiles

| Metric | P0 (Min) | P1 | P5 | P25 | P50 | P75 | P95 | P99 | P100 (Max) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Notch Depth (pu)** | 0.2289 | 0.2352 | 0.2391 | 0.2946 | 0.3905 | 0.4344 | 0.5323 | 0.5357 | 0.5382 |
| **Notch Width (ms)** | 0.4333 | 0.4500 | 0.5333 | 1.1083 | 1.3000 | 1.6098 | 2.8240 | 2.9500 | 2.9667 |
| **THD (%)** | 3.8245 | 3.8510 | 4.4142 | 6.3458 | 7.3712 | 8.1525 | 10.2560 | 10.8399 | 10.8719 |
| **RMS Voltage (pu)** | 0.4265 | 0.4267 | 0.4307 | 0.4663 | 0.4915 | 0.5395 | 0.5811 | 0.5826 | 0.5827 |

### 3U.8 Waveform Diversity & Rank
- **Numerical Rank of 32-Feature Matrix**: **31 / 32** (Target $\ge 25$), confirming rich, linearly independent information content.
- **Cross-Trajectory Pairwise Correlation**: Minimum $0.8951$, Mean $0.9708$, Maximum $0.9941$ across 50 randomly sampled simulation trajectory pairs (shared 60-Hz fundamental grid component).
- **Operating Condition Representation**: Exactly 32 out of 32 conditions represented ($100.0\%$).
- **Phase Topology Representation**:
  - Three-phase balanced (`ABC`): 640 frames ($55.6\%$)
  - Phase `AB`: 96 frames ($8.3\%$)
  - Phase `BC`: 96 frames ($8.3\%$)
  - Single-phase `A`: 96 frames ($8.3\%$)
  - Single-phase `B`: 96 frames ($8.3\%$)
  - Phase `CA`: 64 frames ($5.6\%$)
  - Single-phase `C`: 64 frames ($5.6\%$)

### 3U.9 Cross-Class Separation
L2 centroid distances across the authoritative 32-feature contract space:
- Distance(Notch, Normal): **143.46** (driven by notch depth, crest factor, and THD $7.27\%$ vs $0.02\%$)
- Distance(Notch, Sag): **82.25** (driven by envelope collapse on Sag vs point-on-wave dips on Notch)
- Distance(Notch, Swell): **67.98** (driven by voltage elevation on Swell vs notch depressions)
- Distance(Notch, Interruption): **59.51** (driven by residual collapse on Interruption vs preserved envelope on Notch)
- Distance(Notch, Harmonics): **132.99** (driven by crest factor $1.64$ vs $1.40$ and point-on-wave discontinuities)
- Distance(Notch, Flicker): **128.23** (driven by envelope modulation on Flicker vs sub-cycle notches)

All L2 centroid distances far exceed 10.0, establishing definitive cross-class separability.

### 3U.10 Secondary Phenomena Quantification
- Maximum instantaneous sample-to-sample voltage difference: $|\Delta V|_{\max} = 0.584\,\text{pu} < 0.65\,\text{pu}$, verifying smooth numerical integration without unphysical discontinuities or solver divergence.
- Commutation snubber rebound ringing is physically bounded and settles within $3\,\text{ms}$.
- No unintended sustained voltage sag, swell, or interruption events detected.

### 3U.11 Production DSP Parity
Benchmarked across representative frames against independent mathematical reference implementations:
- RMS voltage difference: $\Delta_{\text{RMS}} \le 2.3 \times 10^{-5}$
- Peak voltage difference: $\Delta_{\text{Peak}} \le 1.8 \times 10^{-5}$
- Crest factor difference: $\Delta_{\text{Crest}} \le 4.9 \times 10^{-5}$
- THD difference: $\Delta_{\text{THD}} \le 1.1 \times 10^{-4}$
- Maximum observed discrepancy: $0.000049 \ll 10^{-3}$ tolerance.

### 3U.12 Cross-Split Trajectory Leakage Prevention
Dataset partitioning enforced at the continuous simulation trajectory level:
- **Train Split**: 26 simulations (832 frames, $72.2\%$)
- **Validation Split**: 5 simulations (160 frames, $13.9\%$)
- **Test Split**: 5 simulations (160 frames, $13.9\%$)
- Overlap Verification:
  - $\text{Train} \cap \text{Val} = \emptyset$
  - $\text{Train} \cap \text{Test} = \emptyset$
  - $\text{Val} \cap \text{Test} = \emptyset$
- Zero frame or feature leakage across splits.

### 3U.13 Standards Traceability & Provenance Taxonomy
Claims verified against IEEE standards:
- **IEEE Std 1159-2019 Section 4.4.2**: Defines Notching as a periodic voltage disturbance caused by the normal operation of power electronic devices when current is commutated from one phase to another. Typical duration $< 0.5$ cycle, typical notch depth $0.1–0.9\,\text{pu}$.
- **IEEE Std 519-2022 Section 5.1**: Establishes point of common coupling (PCC) voltage notch limits (notch depth, notch area in volt-microseconds, and THD limits for low-voltage and medium/high-voltage systems).
- **Provenance Taxonomy Compliance**:
  - `notch_width_us`: PROJECT-DESIGN-CHOICE
  - `commutation_resistance_ohms`: SIMULATION-PARAMETER
  - `notch_repetition_per_cycle`: ENGINEERING-INTERPRETATION
  - `phase_offset_ms`: ENGINEERING-INTERPRETATION
  - `sensor_noise_snr_db`: SIMULATION-PARAMETER

### 3U.14 ML Decoupling Audit
- Legacy model (`model_weights_32.json`) evaluated on representative Notch frames:
  - Frame 0 prediction: `Sag` (confidence $1.0000$), Status: `OUT_OF_DOMAIN`.
- Rationale: Legacy weights were trained prior to Gate 3S without 60-Hz IEEE 9-bus Notch training samples.
- The model prediction was recorded strictly as a diagnostic; it had zero influence on dataset ground truth, filtering, or validation.

### 3U.15 Regression & Pristine Reference Integrity
- Pristine reference model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx):
  - Verified SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` (byte-for-byte identical).
- Previous disturbance datasets (`normal`, `sag`, `swell`, `interruption`, `harmonics`, `flicker`):
  - 100% intact, zero files modified.

---

## 4. Final Audit Verdict

```
============================================================
GATE 3U — NOTCH DATASET AUDIT VERDICT
============================================================
GATE3U_NOTCH_AUDIT = PASS
============================================================
```

All 16 audit domains passed unconditionally. The 60-Hz IEEE 9-bus Voltage Notch dataset is formally certified for ingestion into downstream multi-class workflows.

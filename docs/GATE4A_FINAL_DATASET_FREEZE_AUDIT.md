# GATE 4A — FINAL DATASET FREEZE & ML READINESS AUDIT REPORT

**Document Reference:** `docs/GATE4A_FINAL_DATASET_FREEZE_AUDIT.md`  
**Stage:** Phase 4A — Final Dataset Freeze & ML Readiness Audit  
**Date:** October 11, 2026  
**Auditor:** Senior Machine Learning Engineer, Power-Quality Researcher & Dataset Auditor  
**Audit Gate Decision:** **PASS** (Frozen Baseline Established)  
**Authoritative Manifest:** [`data/ieee9bus_60hz/dataset_manifest_v1.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/dataset_manifest_v1.json)  
**Verification Script:** [`scripts/verify_dataset_freeze.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/scripts/verify_dataset_freeze.py)  

---

## 1. Executive Summary & Gate Decision

A comprehensive forensic audit of the empirical dataset artifacts stored in `data/ieee9bus_60hz/` was conducted to establish a leakage-safe, reproducible baseline for **Phase 4: 60-Hz ML Model Training**.

### Gate Classification: **`PASS`**

All mandatory checks passed without violation:
1. **Pristine Reference Model Preserved:** Simulink model `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` SHA-256 confirmed unchanged (`5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`).
2. **Empirical Dataset Integrity:** 100% agreement between waveform tensors, feature tables, and metadata files. Zero missing values, zero NaNs, zero Infs, zero duplicate rows across all 8 classes.
3. **Trajectory Leakage Audit:** Grouped, trajectory-safe partitioning strictly prevents overlapping or adjacent frames from the same continuous simulation trajectory across training, validation, and test sets. Overlap is **0.0%**.
4. **Authoritative 32-Feature Contract:** Exactly 32 features are present in the immutable production order defined in `dsp/phase_processor.py`. The phase-aware orthogonal projection SNR algorithm remains intact. Feature re-extraction from raw waveforms achieved **0.000000e+00** numerical drift across all classes.
5. **Existing Model Artifact Audited:** The current model artifact (`ml/models/model_weights_32.json`) is confirmed to be the legacy 50-Hz model trained on `Dataset/BARC DATA.csv` and is completely out-of-domain for 60-Hz IEEE 9-bus data (producing 0.00% accuracy on 60-Hz normal frames). Legacy artifacts remain preserved and untouched.

---

## 2. Actual Dataset Inventory vs. Historical Estimates

### 2.1 Resolution of Historical Projection Discrepancy
Historical project reports (including `docs/GATE_INDEX.md` and initial estimates) projected a dataset total of **9,216 frames** based on a nominal expectation of 1,152 frames across all 8 classes ($8 \times 1,152 = 9,216$).

Empirical inspection of actual disk artifacts reveals:
- The **7 disturbance classes** (Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient) each contain exactly **1,152 frames** (generated from 36 simulation trajectories $\times$ 32 sliding windows).
- The **Normal baseline class** contains exactly **1,120 frames** (generated from 32 steady-state power flow operating conditions $\times$ 35 non-overlapping windows).
- The **verified ground-truth dataset total is exactly 9,184 frames**.

Both the waveform arrays (`.npz`) and feature tables (`.csv`) for Normal contain 1,120 rows, supported by 100% passed physical validation. This count is mathematically sound, preserves clean integer partitioning, and is codified in `dataset_manifest_v1.json`.

### 2.2 Per-Class Verified Dimensions & Counts

| Class Index | Class Name | Waveform File | Waveform Shape | Feature CSV Shape | Total Trajectories | Train Frames | Val Frames | Test Frames | Physical Status |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0** | **Normal** | `normal_waveforms.npz` | `[1120, 1000, 3]` | `[1120, 47]` | 32 conditions | 770 (22 trajs) | 175 (5 trajs) | 175 (5 trajs) | PASS (100%) |
| **1** | **Sag** | `sag_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 48]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **2** | **Swell** | `swell_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 48]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **3** | **Interruption** | `interruption_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 49]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **4** | **Harmonics** | `harmonics_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 42]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **5** | **Flicker** | `flicker_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 46]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **6** | **Notch** | `notch_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 42]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **7** | **Transient** | `transient_waveforms.npz` | `[1152, 1000, 3]` | `[1152, 53]` | 36 scenarios | 832 (26 trajs) | 160 (5 trajs) | 160 (5 trajs) | PASS (100%) |
| **TOTAL** | **8 Classes** | — | **9,184 frames** | **9,184 rows** | **284 trajs** | **6,594 (71.8%)** | **1,295 (14.1%)** | **1,295 (14.1%)** | **PASS** |

### 2.3 Stored Physical Channels Audit
An audit was conducted on stored signal channels within each `.npz` container:
- **Voltage Waveforms:** All 8 classes store the canonical three-phase voltage array under key `'waveforms'` with shape `[N, 1000, 3]` ($V_a, V_b, V_c$ at Bus 5 in per-unit).
- **Current Waveforms:** Three-phase current arrays under key `'currents'` with shape `[1152, 1000, 3]` are stored ONLY for `sag`, `swell`, `interruption`, `harmonics`, and `flicker`. They are **NOT** stored for `normal`, `notch`, or `transient`.
- **Contract Confirmation:** The production DSP pipeline and ML classifier input contract are strictly based on **voltage waveforms**.

---

## 3. Trajectory Leakage Audit

To prevent synthetic over-optimism and data snooping, frames originating from the same physical simulation trajectory must never span train, validation, or test sets.

### 3.1 Partitioning Methodology
- Partitioning is group-based, assigned at the continuous simulation trajectory level.
- Disturbance classes: 26 trajectories assigned to Train (72.2%), 5 to Validation (13.9%), 5 to Test (13.9%).
- Normal baseline: 22 operating condition trajectories to Train (68.75%), 5 to Validation (15.625%), 5 to Test (15.625%).

### 3.2 Partition Overlap Verification
- **Train $\cap$ Validation Overlap:** Exactly **0** trajectories across all 8 classes.
- **Train $\cap$ Test Overlap:** Exactly **0** trajectories across all 8 classes.
- **Validation $\cap$ Test Overlap:** Exactly **0** trajectories across all 8 classes.
- **Verdict:** Trajectory leakage is mathematically eliminated.

### 3.3 Trajectory Allocation Table

| Class | Train Trajectories (N=count) | Validation Trajectories | Test Trajectories |
|:---|:---|:---|:---|
| **Normal** | `sim_01`, `sim_04`, `sim_05`, `sim_09`, `sim_10`, `sim_12`, `sim_13`, `sim_15`, `sim_17`, `sim_18`, `sim_19`, `sim_20`, `sim_21`, `sim_22`, `sim_25`, `sim_26`, `sim_27`, `sim_28`, `sim_29`, `sim_30`, `sim_31`, `sim_32` (22) | `sim_03`, `sim_07`, `sim_11`, `sim_16`, `sim_24` (5) | `sim_02`, `sim_06`, `sim_08`, `sim_14`, `sim_23` (5) |
| **Sag** | `sag_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `sag_sim_03`, `09`, `14`, `22`, `30` (5) | `sag_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Swell** | `swell_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `swell_sim_03`, `09`, `14`, `22`, `30` (5) | `swell_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Interruption** | `int_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `int_sim_03`, `09`, `14`, `22`, `30` (5) | `int_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Harmonics** | `har_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `har_sim_03`, `09`, `14`, `22`, `30` (5) | `har_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Flicker** | `flk_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `flk_sim_03`, `09`, `14`, `22`, `30` (5) | `flk_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Notch** | `not_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `not_sim_03`, `09`, `14`, `22`, `30` (5) | `not_sim_02`, `06`, `11`, `21`, `28` (5) |
| **Transient** | `tran_sim_01`, `04`, `05`, `07`, `08`, `10`, `12`, `13`, `15`, `16`, `17`, `18`, `19`, `20`, `23`, `24`, `25`, `26`, `27`, `29`, `31`, `32`, `33`, `34`, `35`, `36` (26) | `tran_sim_03`, `09`, `14`, `22`, `30` (5) | `tran_sim_02`, `06`, `11`, `21`, `28` (5) |

---

## 4. Production 32-Feature Contract Audit

### 4.1 Strict Feature Order & Index Alignment
The 32 features are verified to be present across all 8 feature tables in identical sequence matching `_MODEL_FEATURE_ORDER` in `dsp/phase_processor.py`:

```
Index  0: rms_voltage           Index 11: h4                    Index 22: h5_ratio
Index  1: peak_voltage          Index 12: h5                    Index 23: h7_ratio
Index  2: crest_factor          Index 13: h6                    Index 24: h9_ratio
Index  3: thd                   Index 14: h7                    Index 25: h11_ratio
Index  4: duration              Index 15: h8                    Index 26: harmonic_energy
Index  5: dominant_freq         Index 16: h9                    Index 27: spectral_centroid
Index  6: system_freq           Index 17: h10                   Index 28: spectral_bandwidth
Index  7: snr                   Index 18: h11                   Index 29: spectral_entropy
Index  8: h1                    Index 19: h2_ratio              Index 30: spectral_flatness
Index  9: h2                    Index 20: h3_ratio              Index 31: true_dominant_freq
Index 10: h3                    Index 21: h4_ratio
```

### 4.2 Signal-to-Noise Ratio (SNR) Formula Integrity
The phase-aware orthogonal fundamental projection algorithm implemented in `dsp/baseline_features.py` (lines 111–139) remains intact:
$$x_{\text{fund}}[n] = A_1 \cos(2\pi f_0 t[n]) + B_1 \sin(2\pi f_0 t[n])$$
$$\text{SNR}_{\text{dB}} = 10 \log_{10} \left( \frac{\sum x_{\text{fund}}[n]^2}{\sum (x[n] - x_{\text{fund}}[n])^2} \right)$$
Phase invariance and absence of phase-angle distortion are confirmed.

### 4.3 Feature Extraction Reproducibility Verification
Raw waveforms from `*_waveforms.npz` across all 8 classes were passed through `extract_enhanced_features(..., f0=60.0)` in Python. The resulting feature values were compared with the values stored in `*_features.csv`:
- Maximum absolute difference across all 32 features and all classes: **`0.000000e+00`** (bit-exact parity).

---

## 5. Existing Model Compatibility Audit

### 5.1 Inspection of `ml/models/model_weights_32.json`
- **Model Identity:** Legacy 50-Hz Compact MLP (EXP-003), trained on `Dataset/BARC DATA.csv` (10,000 samples).
- **Embedded Scaler:**
  - `dominant_freq`: $\mu = 50.00\,\text{Hz}$, $\sigma = 1.00$
  - `system_freq`: $\mu = 49.45\,\text{Hz}$, $\sigma = 3.35$
  - `rms_voltage`: $\mu = 0.6911\,\text{pu}$, $\sigma = 0.1157$
  - `peak_voltage`: $\mu = 1.1083\,\text{pu}$, $\sigma = 0.1979$

### 5.2 60-Hz Incompatibility Demonstration
When `model_weights_32.json` is evaluated on the 60-Hz IEEE 9-bus Normal frames ($N=1,120$):
- **Prediction:** 1,120 / 1,120 frames (100.0%) predicted as **`Interruption`** (confidence: 1.0000).
- **Classification Accuracy:** **0.00%**.
- **Root Cause:** In the 50-Hz standardized feature space, a 60.0 Hz signal lies at $z = +3.15\sigma$, and Bus 5 nominal voltage ($0.588\,\text{pu}$ RMS) produces extreme negative excursion in the legacy scaler, driving the network to fire the Interruption unit.
- **Audit Conclusion:** The legacy model is confirmed **OUT-OF-DOMAIN** and must not be used for 60-Hz deployment. It is safely decoupled and preserved. Legacy splits in `data/splits/` belong to the 50-Hz dataset and must not be used for 60-Hz training.

---

## 6. Cryptographic Artifact Checksum Registry

All 24 primary files comprising the frozen 60-Hz baseline have been fingerprinted with SHA-256:

| Class | Waveform NPZ SHA-256 | Feature CSV SHA-256 | Metadata JSON SHA-256 |
|:---|:---|:---|:---|
| **Normal** | `0C63A2ACE6CA02C5F5948CD54D77A2A4AEAF3B006422728B7DA3CC23CC7009DA` | `E649944B51453429B9935EC8ED45E2DEDFEAEBB2AAB774FB18DA67259EA649CC` | `AC459FB22C9C4FAA2BDF9FB58DFED2611A38B7E3E5044FF77E26831D740F31C0` |
| **Sag** | `2186F152FB714D3EAFA317FB3C395944AD0799A5EBEBBE1A04446735FC4AD40F` | `55C8FB355A87656A501DA287093C7E79203C4D065AE1044C04A82A82340B68E1` | `8CB67EFEADC71ECAAFAE096C1AA2A6C950D42F87B90257A3B88DC78F75335934` |
| **Swell** | `609D8277736CDB198105E88938D49B39F08ADF8C3E1EFD542EEE827D0D45CF54` | `C774D7CB338F5C74FE4B69FD9492D442768CAA643ABA226104AC5C1D6ADC89CC` | `0B06E37365655F294DD7C01A9B3C832880B41EC9885A4AB76E22193015027E78` |
| **Interruption** | `57970958638AC83E4E1E91B4F8261242BF50043F5FE7EA821E05B8864B700130` | `EFB70703D280C0C89E6FB5806AFCD0758DA1AA41B86F453A888F68EF21CF80A5` | `FA611048423CDF0E95AC54D55D27A8652B575A2AFFA558B63BC0CE3D65F7B2DE` |
| **Harmonics** | `00CE2F0ED0CB9BA687E727ECF82C6CAA84F91F874A317634E99AD6F6586B4A27` | `F541B388BF606F25B20F7ED8E457EF5C6542DC6E873D23B082D122BFF1600E41` | `33CEECEED3D703B32F888E376B7E765C788E1CF23946DC8A7129381A7AE7D3BD` |
| **Flicker** | `A5ABAE764C923BCD223C2AC42FC7EDD836F93A9E12A8B6D24E304F38217E946B` | `D8A1C536CC23D41EA699221C6F60A0E9F436E7A46E9E5FAE702E2BEC17501E70` | `2C4DCBACAAE434538369D9D394BC4C68E6BF024E62F6422D029D76B2462EBC66` |
| **Notch** | `46250F10917A82FEE03C530AEED8F680E3EE9A17BA6FDFDF5A5136AE0EA15A76` | `76F4B8722A6DDB9AB6461DBF10ABE8D24A2D6F06DA43784BC87B3E07A5201775` | `1B0904A934E5C4C22039C60BD00121BCE5EC1B62A04FE09AA715FA52FF171CA4` |
| **Transient** | `8176A39D3FC91764B674B3EBE0A01F2B87F182A99417E1490984648819A7AED2` | `0C9CD9E594B3FCB6AE2836E3C1B4F4E3485891551A9CABDB40427D2C17FDD11A` | `0B88C294D655D44A6AE7A2FC2FFFB08106EE32401189D5AC6C2DF22FA61C67E2` |

- **Pristine Reference Model (`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`):**  
  `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`

---

## 7. Freeze Readiness & Stop Condition Compliance

1. **Preconditions Satisfied:** All 8 disturbance classes are physically validated and leak-free.
2. **Reproducibility Automated:** [`scripts/verify_dataset_freeze.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/scripts/verify_dataset_freeze.py) confirms that all checksums match with zero drift.
3. **Artifact Integrity:** The authoritative dataset manifest [`data/ieee9bus_60hz/dataset_manifest_v1.json`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/data/ieee9bus_60hz/dataset_manifest_v1.json) is established.
4. **Stop Condition:** No model training, hyperparameter tuning, or weight modification was initiated. Phase 4A stops here.

---

## 8. Exact Next Step for Phase 4B

With the dataset frozen, the exact next step upon user authorization is **Phase 4B: 60-Hz Model Training Pipeline Construction & Baseline Training**:
1. Implement a dedicated 60-Hz data loader reading from `data/ieee9bus_60hz/` using `dataset_manifest_v1.json`.
2. Fit `StandardScaler` strictly on the 6,594 training frames, recording $\mu$ and $\sigma$ for all 32 features.
3. Train the canonical $32 \to 64 \to 32 \to 8$ MLP architecture on the 60-Hz training partition.
4. Evaluate convergence on the validation partition (1,295 frames) and lock in final test evaluation (1,295 frames).
5. Export updated, verified model weights (`model_weights_60hz.json`) and C header (`model_weights_60hz.h`).

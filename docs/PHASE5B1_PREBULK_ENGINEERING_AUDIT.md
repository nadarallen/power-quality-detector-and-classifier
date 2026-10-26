# Phase 5B.1 — Pre-Bulk Physical Validation and Sampling Adequacy Audit Report

**Subsystem:** Simulation Infrastructure, Signal Acquisition, and Physical Ground-Truth Validation  
**Branch:** `research/pq-comparative-lab`  
**Repository:** `https://github.com/nadarallen/power-quality-detector-and-classifier`  
**Status:** COMPLETE (Audit Findings & Recommendations Delivered)  
**Date:** October 2026  
**Auditor:** Antigravity Comparative PQ Lab Audit Subsystem  
**Scope:** Read-only audit of Phase 5B pilot artifacts, Simscape disturbance model, scenario matrix arithmetic, and measurement perturbation definitions prior to Phase 5C bulk generation.

---

## 1. Executive Summary & Baseline State

This engineering audit independently evaluates the physical validity, sampling adequacy, mathematical contracts, and matrix structure established in Phase 5B before authorizing bulk dataset generation (Phase 5C: 4,608 frames).

### Repository Baseline Verification
- **Current Branch:** `research/pq-comparative-lab`
- **Current HEAD Commit:** `876e348` (`docs(phase5b): complete simulation matrix, pilot generation, and physical validation`)
- **Pristine Reference Integrity:** [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](../IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) confirmed untouched (SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`).
- **Frozen Baseline Integrity:** [`data/ieee9bus_60hz/dataset_manifest_v1.json`](../data/ieee9bus_60hz/dataset_manifest_v1.json) intact with 9,184 frames, 8 classes, and locked splits.
- **Pilot Dataset Status:** 24 pilot trajectories in [`data/ieee9bus_60hz_phase5b_pilot/`](../data/ieee9bus_60hz_phase5b_pilot/) (24 raw `.mat` + 24 processed `.npz`) verified against [`checksums_sha256.txt`](../data/ieee9bus_60hz_phase5b_pilot/checksums_sha256.txt).

### Audit Verdict Summary

| Subsystem / Dimension | Evaluated Requirement | Audit Status | Key Finding |
|---|---|:---:|---|
| **Sampling Adequacy** | 5 kHz ($T_s = 200\ \mu\text{s}$) representation for notches ($300\text{--}1000\ \mu\text{s}$) & transients ($\le 2.2\text{ kHz}$) | **CONDITIONAL PASS** (Adequate for 32 Features; Marginal for Raw Waveform DL) | 5 kHz Nyquist is 2.5 kHz; 300 $\mu$s notch spans only 1.5 samples; 2.2 kHz transient has only 2.27 samples/cycle. Multi-rate strategy recommended for deep learning. |
| **Swell Normalization** | Voltage base, reference RMS, and IEEE 1159-2019 conformity | **PHYSICALLY VERIFIED** (Reporting Clarification Required) | Swell half-cycle RMS reaches $0.723\text{--}0.798\text{ pu}$ ($122.9\%\text{--}135.5\%$ of nominal $0.5887\text{ pu}$). Reported $1.045\text{--}1.142\text{ pu}$ is peak instantaneous voltage, not RMS. |
| **Notch Mechanism** | Single-phase ground return (`GroundFault = 'on'`) validity | **PHYSICALLY VERIFIED** (Documented as Shunt Commutation Surrogate) | Waveform confirms genuine sub-cycle notch ($800\ \mu\text{s}$ duration, depth 0.40 pu, sub-cycle recovery). Does not induce sustained sag, but represents shunt commutation rather than line-to-line converter commutation. |
| **Interruption Mechanism** | Bus 5 electrical disconnection and supply paths | **PHYSICALLY VERIFIED** (Substation Incomer Topology Clarified) | `PQD_Breaker_Interruption` is wired as a Dual Incomer Breaker isolating Bus 5 from *both* Line 4-5 and Line 5-7 simultaneously. Truly isolates Bus 5 with zero alternate supply paths. |
| **Matrix Arithmetic** | 4,608-frame count reconciliation & split quarantine | **RECONCILED WITH ACTION REQUIRED** | 4,608 frames represents 144 trajectories $\times$ 32 sliding windows. `phase5b_simulation_matrix.json` currently registers only 24 pilot runs and 17 conditions; full 144-trajectory table required for Phase 5C. |
| **Measurement Noise** | AWGN equation, SNR semantics, and ADC quantization | **REVISION REQUIRED** | Existing noise scales by disturbed frame power rather than fixed instrument full-scale power. ADC quantization (12/14-bit) is declared in matrix metadata but unimplemented in code. |

---

## 2. Sampling Adequacy Audit

### Technical Specification
- **Sampling Frequency ($f_s$):** $5,000\text{ Hz}$
- **Sampling Interval ($T_s$):** $\frac{1}{f_s} = 200\ \mu\text{s} = 0.2\text{ ms}$
- **Analysis Window:** $200\text{ ms}$ (12 fundamental 60-Hz cycles)
- **Samples per Window ($N$):** $1,000\text{ samples}$ per phase channel
- **Nyquist Cutoff ($f_{\text{Nyq}}$):** $\frac{f_s}{2} = 2,500\text{ Hz} = 2.5\text{ kHz}$

### Mathematical Resolution Analysis

#### 1. Voltage Notch Morphology (Widths: $300\text{--}1,000\ \mu\text{s}$)
The discrete sample count $k$ spanning a notch of width $w_{\text{notch}}$ at $T_s = 200\ \mu\text{s}$ is:
$$k = \frac{w_{\text{notch}}}{T_s}$$

| Notch Width ($w_{\text{notch}}$) | Samples at 5 kHz ($T_s = 200\ \mu\text{s}$) | Samples at 10 kHz ($T_s = 100\ \mu\text{s}$) | Samples at 20 kHz ($T_s = 50\ \mu\text{s}$) | Morphological Retention at 5 kHz |
|:---:|:---:|:---:|:---:|---|
| **$300\ \mu\text{s}$** | **$1.5\text{ samples}$** | $3.0\text{ samples}$ | $6.0\text{ samples}$ | **Severe distortion:** Single-sample impulse; commutation ramp and depth lost |
| **$400\ \mu\text{s}$** | **$2.0\text{ samples}$** | $4.0\text{ samples}$ | $8.0\text{ samples}$ | **Marginal:** V-shaped notch represented by 2 discrete points |
| **$500\ \mu\text{s}$ (Pilot 20)** | **$2.5\text{ samples}$** | $5.0\text{ samples}$ | $10.0\text{ samples}$ | **Sub-Nyquist shape:** Detectable as notch, but recovery slope smoothed |
| **$600\ \mu\text{s}$ (Pilot 19)** | **$3.0\text{ samples}$** | $6.0\text{ samples}$ | $12.0\text{ samples}$ | **Detectable:** 3 points define entry, trough, and exit |
| **$800\ \mu\text{s}$ (Pilot 21)** | **$4.0\text{ samples}$** | $8.0\text{ samples}$ | $16.0\text{ samples}$ | **Adequate for detection:** 4 points define flat bottom and recovery |
| **$1,000\ \mu\text{s}$** | **$5.0\text{ samples}$** | $10.0\text{ samples}$ | $20.0\text{ samples}$ | **Well-resolved:** 5 points preserve notch area and duration |

#### 2. Oscillatory Transient Frequencies (up to $2.2\text{ kHz}$)
The number of discrete samples per oscillation cycle $N_{\text{osc}}$ at frequency $f_{\text{osc}}$ is:
$$N_{\text{osc}} = \frac{f_s}{f_{\text{osc}}}$$

| Transient Frequency ($f_{\text{osc}}$) | Samples / Cycle at 5 kHz | Fraction of Nyquist ($f_{\text{osc}} / f_{\text{Nyq}}$) | Phase Jitter & Aliasing Risk |
|:---:|:---:|:---:|---|
| **$800\text{ Hz}$** | $6.25\text{ samples}$ | $32.0\%$ | Low; smooth sinusoidal oscillation resolved |
| **$1,260\text{ Hz}$ (Pilot 22)** | $3.97\text{ samples}$ | $50.4\%$ | Moderate; ~4 points per cycle, envelope decay clearly visible |
| **$1,800\text{ Hz}$** | $2.78\text{ samples}$ | $72.0\%$ | High; triangularized waveform, peak amplitude varies with POW |
| **$2,200\text{ Hz}$** | **$2.27\text{ samples}$** | **$88.0\%$** | **Severe:** Near Nyquist limit; severe amplitude modulation from discrete sampling phase |

### Raw Artifact Inspection
Inspection of `data/ieee9bus_60hz_phase5b_pilot/raw/` revealed that the raw simulation outputs are saved as `V_frame` with $T_s = 200\ \mu\text{s}$ ($dt = 0.0002\text{ s}$). In [`scripts/run_phase5b_pilot_simulation.m`](../scripts/run_phase5b_pilot_simulation.m), the continuous Simscape simulation output (`simOut.PQD_Vabc` from variable-step solver `ode23tb`) is resampled via MATLAB's `resample(Vts.Data, Vts.Time, 5000)` inside the runner before writing the `.mat` artifact to disk. The physical validators in `pipeline/disturbance_validator.py` operate on this resampled 5 kHz representation.

### Distinct Requirements: Classical ML vs Raw Waveform Deep Learning
1. **Classical ML Baseline (32 DSP Features):** **5 kHz is Fully Adequate.**  
   Features such as half-cycle RMS, THD, spectral energy ratio, fundamental amplitude, and statistical moments integrate energy across the window. A 3-point notch still injects elevated high-frequency energy ratio ($E_{\text{ratio}} > 0.001$), triggering correct classification.
2. **Raw-Waveform Deep Learning (CNN / TCN / Transformer):** **5 kHz is Marginal.**  
   A 1D convolutional kernel of size $k=5$ or $k=7$ spanning $1.0\text{--}1.4\text{ ms}$ spans the entire notch and adjacent fundamental cycles, blurring sharp commutation edges. A $2.2\text{ kHz}$ oscillation represented by $2.27$ samples per cycle exhibits significant discrete phase distortion depending on where the discrete samples land relative to the oscillation peaks.

### Recommended Multi-Rate Strategy
To maintain scientific rigor without breaking historical compatibility:
1. **Preserve Frozen 5 kHz Baseline:** Retain `data/ieee9bus_60hz/` exactly as frozen for all classical feature comparisons.
2. **Dual-Rate Generation in Phase 5C:** Modify the MATLAB runner to archive continuous simulation data and export two synchronized representations:
   - **Canonical Representation (5 kHz):** 1,000 samples per frame ($T_s = 200\ \mu\text{s}$) for 32-feature parity and historical benchmarks.
   - **High-Resolution Representation (20 kHz):** 4,000 samples per frame ($T_s = 50\ \mu\text{s}$) for 1D CNN / raw-waveform research. At 20 kHz, a $300\ \mu\text{s}$ notch has 6 samples, a $600\ \mu\text{s}$ notch has 12 samples, and a $2.2\text{ kHz}$ transient has $9.1$ samples/cycle.
3. **Anti-Aliasing Compliance:** Apply an 8th-order Chebyshev Type I lowpass filter ($f_{\text{cutoff}} = 2.25\text{ kHz}$) before any downsampling to 5 kHz.
4. **Storage Impact:** 4,608 frames at 5 kHz is ~320 MB compressed. At 20 kHz, storage is ~1.28 GB compressed—well within repository capacity.

---

## 3. Swell Normalization and Label Criteria Recheck

### Normalization Architecture in Simscape Model
In `IEEE_9bus_PQD_DISTURBANCES.slx`, Bus 5 nominal voltage is $230\text{ kV}$ line-to-line RMS. The Simscape three-phase voltage sensor outputs phase-to-ground voltage normalized by the line-to-line base:
$$V_{\text{base,LL}} = 230,000\text{ V RMS}$$
$$V_{\text{base,LN,peak}} = 230,000 \times \sqrt{\frac{2}{3}} \approx 187,794\text{ V peak}$$
$$V_{\text{nom,LN,RMS}}(\text{in pu of } V_{\text{base,LL}}) = \frac{1}{\sqrt{3}} \approx 0.57735\text{ pu}$$

At Bus 5, the nominal scheduled operating voltage under load flow is $1.02\text{ pu}$ line-to-line. Therefore:
$$V_{\text{nom,Bus5,RMS}} = 1.02 \times \frac{1}{\sqrt{3}} \approx 0.58889\text{ pu}$$
This establishes the authoritative baseline constant: `nominal_baseline_rms = 0.5887`.

### Independent Numerical Verification of Swell Pilot Runs

| Metric | Pilot 7 (`P5B_SWL_0001_3p_moderate_nom`) | Pilot 8 (`P5B_SWL_0002_3p_mild_light`) | Pilot 9 (`P5B_SWL_0003_3p_challenge`) |
|---|:---:|:---:|:---:|
| **Operating Condition** | Cond 1 (Nominal 100%) | Cond 2 (Light Load 85%) | Cond 5 (Heavy Load 105%) |
| **Grid Baseline Voltage Schedule** | $1.00\text{ pu}$ | $0.99\text{ pu}$ (Light Load dispatch) | $1.00\text{ pu}$ |
| **Pre-Event Local RMS ($V_{\text{pre}}$)** | $0.5897\text{ pu}$ | $0.6335\text{ pu}$ | $0.5750\text{ pu}$ |
| **Event Swell Max RMS ($V_{\text{event}}$)** | **$0.7919\text{ pu}$** | **$0.7976\text{ pu}$** | **$0.7233\text{ pu}$** |
| **Peak Instantaneous Voltage ($V_{\text{peak}}$)** | **$1.142\text{ pu}$** | **$1.045\text{ pu}$** | **$1.098\text{ pu}$** |
| **Post-Event Recovery RMS ($V_{\text{post}}$)** | $0.5890\text{ pu}$ | $0.6329\text{ pu}$ | $0.5743\text{ pu}$ |
| **Event Duration** | $82.6\text{ ms}$ (4.96 cycles) | $76.0\text{ ms}$ (4.56 cycles) | $89.6\text{ ms}$ (5.38 cycles) |
| **Event Onset Time** | $45.4\text{ ms}$ | $44.6\text{ ms}$ | $37.4\text{ ms}$ |
| **Ratio to Nominal Baseline ($0.5887$)** | **$1.3451\text{ pu}$ ($134.5\%$)** | **$1.3548\text{ pu}$ ($135.5\%$)** | **$1.2287\text{ pu}$ ($122.9\%$)** |
| **Ratio to Local Pre-Event RMS** | **$1.3429\text{ pu}$ ($134.3\%$)** | **$1.2590\text{ pu}$ ($125.9\%$)** | **$1.2579\text{ pu}$ ($125.8\%$)** |
| **IEEE 1159-2019 Table 2 Criterion** | $1.10\text{--}1.80\text{ pu}$ for $0.5\text{ cyc}\text{--}1\text{ min}$ | $1.10\text{--}1.80\text{ pu}$ for $0.5\text{ cyc}\text{--}1\text{ min}$ | $1.10\text{--}1.80\text{ pu}$ for $0.5\text{ cyc}\text{--}1\text{ min}$ |
| **Physical Status** | **PHYSICALLY VERIFIED** | **PHYSICALLY VERIFIED** | **PHYSICALLY VERIFIED** |

### Clarification of Reported Values
In Table 6 of [`docs/PHASE5B_SIMULATION_MATRIX_AND_PILOT_REPORT.md`](PHASE5B_SIMULATION_MATRIX_AND_PILOT_REPORT.md), the values $1.045\text{--}1.142\text{ pu}$ represent **peak instantaneous voltage** relative to the line-to-line base. Because nominal peak is $\sqrt{2/3} \approx 0.8165\text{ pu}$, a peak voltage of $1.142\text{ pu}$ represents:
$$\frac{1.142}{0.8165} = 1.399\text{ pu of nominal peak}$$
The actual half-cycle RMS swell ratio is **$1.229\text{--}1.355\text{ pu}$** relative to nominal baseline and **$1.258\text{--}1.343\text{ pu}$** relative to local pre-event voltage. Both ratios fall solidly within IEEE 1159-2019 Table 2 swell bounds ($1.10\text{--}1.80\text{ pu}$).

---

## 4. Revalidation of the Notch Mechanism

### Circuit Architecture Audit
In `IEEE_9bus_PQD_DISTURBANCES.slx`, the `PQD_Notch_Bus5` block is an SPS Three-Phase Fault block connected across Bus 5 phases A, B, and C with external switching control:
- **Switching Signal:** `PQD_Notch_FromWS` reads `notch_ctrl_signal` from the base workspace.
- **Commutation Resistance ($R_{\text{comm}}$):** $80\text{--}180\ \Omega$.
- **Snubber Resistance:** $1\text{ M}\Omega$, Snubber Capacitance: $\infty$ (dormant when open).

### The Single-Phase `GroundFault = 'on'` Behavior
During Phase 5B execution, line 306 of `scripts/run_phase5b_pilot_simulation.m` was modified:
```matlab
if length(ph_str) == 1
    set_param(notch_blk, 'GroundFault', 'on');
else
    set_param(notch_blk, 'GroundFault', 'off');
end
```

#### Detailed Physical Analysis of Pilot 21 (`P5B_NOT_0003_1p_w800us_challenge`):
1. **Event Periodicity:** Notches occur at indices 72, 156, 239, 322, 406, 489, 572, 656, 739, 822, 906, 989. Spacing is exactly $83\text{--}84\text{ samples}$ ($16.6\text{--}16.8\text{ ms} \approx 1\text{ cycle}$ at 60 Hz).
2. **Event Duration:** At index 72 ($t = 14.40\text{ ms}$), Phase A voltage drops from $0.744\text{ pu}$ to $0.222\text{ pu}$ over 4 discrete samples ($800\ \mu\text{s}$) and immediately recovers to normal sinusoidal tracking at index 76 ($t = 15.20\text{ ms}$).
3. **Current Profile:** Branch current jumps from $0.70\text{ pu}$ to $2.38\text{ pu}$ during the $800\ \mu\text{s}$ pulse and immediately returns to normal load current ($0.54\text{ pu}$).
4. **RMS Stability:** Full-window RMS is $0.548\text{ pu}$, pre-event RMS is $0.589\text{ pu}$, mid-event RMS is $0.525\text{ pu}$, and post-event RMS is $0.561\text{ pu}$.

#### Distinguishing Notch from Voltage Sag
IEEE 1159-2019 Clause 3.1.58 defines a Voltage Sag as a decrease in RMS voltage to $0.10\text{--}0.90\text{ pu}$ for a duration of **0.5 cycle to 1 minute** ($\ge 8.33\text{ ms}$ at 60 Hz).  
The observed event in Pilot 21 lasts only **$0.80\text{ ms}$ ($0.048\text{ cycle}$)**, which is less than one-tenth of the minimum duration required for a sag. The voltage recovers fully within the same cycle. Therefore, this is **physically a notch, not a fault or sag**.

#### Subsystem Limitation & Circuit Classification
In industrial power electronics (e.g. 6-pulse or 12-pulse line-commutated rectifiers), commutation occurs between pairs of AC lines (Line-to-Line: A-B, B-C, C-A) when current shifts from one thyristor to another. A rectifier bridge does not commutate a single phase to ground.  
- **Multi-Phase Notches (`ABC`, `AB`, `BC`, `CA`):** True physical line-to-line commutation between phases.
- **Single-Phase Notches (`A`, `B`, `C`):** Sub-cycle pulsed shunt connection to ground through $100\ \Omega$.  
**Classification:** **PHYSICALLY VERIFIED** as a sub-cycle switching notch surrogate. For the bulk matrix in Phase 5C, single-phase notches should be explicitly documented as *single-phase shunt commutation equivalents*.

---

## 5. Revalidation of the Interruption Mechanism

### Complete Topology Inspection
A potential concern was whether opening a breaker labeled "Line 4-5 breaker" leaves Bus 5 supplied via Line 5-7. To resolve this, MATLAB's `PortConnectivity` API was executed directly on `IEEE_9bus_PQD_DISTURBANCES.slx`:

```
Block: IEEE_9bus_PQD_DISTURBANCES/PQD_Breaker_Interruption
Port LConn1 connects to:
  DstBlock: Load Flow Bus2
  DstBlock: Line 4 - 5 
  DstBlock: Line 5 - 7 
Port LConn2 connects to:
  DstBlock: Line 4 - 5 
  DstBlock: Line 5 - 7 
Port LConn3 connects to:
  DstBlock: Line 4 - 5 
  DstBlock: Line 5 - 7 
Port RConn1 connects to:
  DstBlock: Bus_5 230 KV
Port RConn2 connects to:
  DstBlock: Bus_5 230 KV
Port RConn3 connects to:
  DstBlock: Bus_5 230 KV
```

### Physical Findings
1. **Actual Wiring Topology:** `PQD_Breaker_Interruption` is **NOT placed solely on Line 4-5**. It is placed directly between the transmission line junctions (`Line 4-5` AND `Line 5-7`) and `Bus 5 230 KV`.
2. **Dual-Incomer Substation Isolation:** When `PQD_Breaker_Interruption` opens, it simultaneously disconnects Bus 5 from **both incoming lines (Line 4-5 and Line 5-7)**.
3. **Absence of Alternate Supply Paths:** Bus 5 has only one load (Load A: 125 MW, 50 MVAR) and zero local generation. Once this breaker opens, there are **zero alternate energized paths** supplying Bus 5.
4. **Measured Physical Response:**
   - In Pilot 10 (`P5B_INT_0001_3p_standard_nom`), Bus 5 voltage collapses from $0.589\text{ pu}$ to **$0.000\text{ pu}$ ($0.0\%$)** during the interruption interval ($t = 0.12\text{--}0.19\text{ s}$).
   - Measured line current drops from $0.54\text{ pu}$ to **$0.000\text{ A}$**.
   - Upon breaker reclosing at $t = 0.19\text{ s}$, voltage recovers cleanly within $1.5\text{ ms}$.

**Classification:** **PHYSICALLY VERIFIED.** The mechanism produces an indisputable, 100% complete voltage interruption conforming to IEEE 1159-2019 Table 2 ($< 0.10\text{ pu}$ residual). The documentation must be clarified to describe this block as the *Bus 5 Substation Dual-Incomer Isolation Breaker*.

---

## 6. Simulation Matrix Arithmetic & Condition Reconciliation

### Matrix Factorial Explosion vs Controlled Selection
A complete Cartesian product across all theoretical parameter combinations would yield:
$$N_{\text{Cartesian}} = 9\text{ families} \times 36\text{ conditions} \times 8\text{ classes} \times 3\text{ severities} \times 7\text{ phases} \times 4\text{ POW} = 174,182\text{ scenarios}$$
This is computationally intractable and physically unmeaningful (e.g. Normal has no phase asymmetry or severity; Interruption has no harmonic order).

### Reconciliation of the 4,608-Frame Target
The target of **4,608 unique frames** is structured as a balanced, fractional design:
$$N_{\text{total frames}} = 144\text{ continuous trajectories} \times 32\text{ frames per trajectory} = 4,608\text{ frames}$$
$$\text{Per-Class Allocation} = \frac{4,608\text{ frames}}{8\text{ classes}} = 576\text{ frames per class}$$
$$\text{Trajectories Per Class} = \frac{576\text{ frames}}{32\text{ frames/trajectory}} = 18\text{ independent simulation trajectories per class}$$

### Audit of `scenarios/phase5b_simulation_matrix.json`
Inspection of the current machine-readable matrix file reveals:
- **Scenario Count:** Currently registers **24 pilot scenarios** (`in_pilot = True`). The remaining 120 trajectories for bulk generation have not yet been populated.
- **Operating Condition Catalog:** Currently contains **17 conditions** (Cond 1, 2, 5, 6, 8, 9, 11, 14, 16, 17, 18, 21, 28, 33, 34, 35, 36). Conditions 3, 4, 7, 10, 12, 13, 15, 19, 20, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32 must be populated in the catalog before Phase 5C execution.

### Evaluation of Quarantined Challenge Conditions
The four challenge conditions are:
- **Family F (Cond 33):** High renewable inverter penetration (G2: 180 MW, G3: 60 MW).
- **Family G (Cond 34):** Cross-bus reactive imbalance (Bus 5: $Q=140\%$, Bus 6: $Q=50\%$, Bus 8: $Q=60\%$).
- **Family H (Cond 35):** Asymmetric substation loading (Bus 5: $P=112\%$, Bus 6: $P=78\%$, Bus 8: $P=110\%$).
- **Family I (Cond 36):** Stressed transmission import (Load A at 72%, remote Loads B and C at 120%, freq 59.97 Hz).

#### Generalization Coverage Limits:
These four conditions represent **4 discrete boundary operating points**, not an exhaustive distribution of power system operational states. Research claims comparing classical ML vs deep learning on this challenge partition must be scoped as:
> *"Evaluating generalization performance on 4 stressed, condition-held-out grid dispatch regimes withheld during training and hyperparameter selection."*

---

## 7. Measurement Perturbation Definitions Audit

### Current Noise Formulation in `scripts/validate_phase5b_pilot.py`
```python
def add_sensor_noise(vabc: np.ndarray, target_snr_db: float = 52.0, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    noisy_vabc = np.zeros_like(vabc)
    for ch in range(3):
        sig = vabc[:, ch]
        p_sig = np.mean(sig**2)
        p_noise = p_sig / (10.0 ** (target_snr_db / 10.0))
        noise = rng.normal(0.0, np.sqrt(p_noise), size=sig.shape)
        noisy_vabc[:, ch] = sig + noise
    return noisy_vabc
```

### Identified Flaws & Required Corrections
1. **Dynamic Signal Power Scaling Flaw:**  
   Computing $p_{\text{sig}} = \text{mean}(\text{sig}^2)$ on the disturbed frame means that during an Interruption or Sag, $p_{\text{sig}}$ collapses, which artificially scales down the noise power! Conversely, during a Swell, noise power is amplified.  
   **Correction:** Sensor noise is an instrument property. Noise power must be scaled relative to the **nominal full-scale fundamental power** ($p_{\text{nom}} = V_{\text{nom,RMS}}^2 = 0.5887^2 \approx 0.3466$):
   $$p_{\text{noise}} = \frac{p_{\text{nom}}}{10^{\text{SNR} / 10}} = \frac{0.3466}{10^{5.2}} \approx 2.187 \times 10^{-6}$$
   $$\sigma_{\text{noise}} = \sqrt{p_{\text{noise}}} \approx 0.001479\text{ pu}$$
2. **Quantization Modeling Gap:**  
   ADC quantization (12-bit and 14-bit) is documented in the matrix schema but completely unimplemented in code.  
   **Specification for Phase 5C Robustness Experiment:**
   $$q = \frac{2 \cdot V_{\text{FS}}}{2^{N_{\text{bits}}}} = \frac{2 \cdot 1.8\text{ pu}}{4096} \approx 0.0008789\text{ pu for 12-bit}$$
   $$v_{\text{quant}} = \text{round}\left(\frac{v}{q}\right) \cdot q$$

---

## 8. Explicit Pass / Fail / Block Status

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               PHASE 5B.1 PRE-BULK AUDIT GATES                                    │
├───────────────────────────────────┬──────────────┬───────────────────────────────────────────────┤
│ AUDIT CRITERION                   │    STATUS    │ REMEDIATION REQUIRED BEFORE PHASE 5C          │
├───────────────────────────────────┼──────────────┼───────────────────────────────────────────────┤
│ 1. Reference & Baseline Integrity │    PASSED    │ None. Pristine model & Phase 4 locked.        │
│ 2. Sampling Adequacy (Classical)  │    PASSED    │ 5 kHz fully adequate for 32 DSP features.     │
│ 3. Sampling Adequacy (Deep Learn) │ CONDITIONAL  │ Implement dual-rate generation (5k & 20k Hz). │
│ 4. Swell Normalization & Physics  │    PASSED    │ Clarify peak instantaneous vs RMS in reports. │
│ 5. Single-Phase Notch Ground Path │    PASSED    │ Document single-phase shunt surrogate.        │
│ 6. Interruption Isolation Path    │    PASSED    │ Update text to "Dual Incomer Breaker".        │
│ 7. Simulation Matrix Definition   │ ACTION REQ   │ Populate full 144-scenario table in JSON/CSV. │
│ 8. Fixed-Power Noise Equation     │ ACTION REQ   │ Change p_sig to fixed p_nom in noise helper.  │
│ 9. ADC Quantization Implementation│ ACTION REQ   │ Implement quantize_adc function for tests.    │
└───────────────────────────────────┴──────────────┴───────────────────────────────────────────────┘
```

---

## 9. Minimal Remediation Plan for Phase 5C

Before launching bulk dataset generation in Phase 5C, execute the following bounded actions:

1. **Populate Complete 144-Trajectory Matrix:** Expand [`scripts/generate_phase5b_simulation_matrix.py`](../scripts/generate_phase5b_simulation_matrix.py) to write the full 144 scenario specifications across all 36 operating conditions into [`scenarios/phase5b_simulation_matrix.json`](../scenarios/phase5b_simulation_matrix.json).
2. **Correct Sensor Noise Helper:** Update `add_sensor_noise` in `scripts/validate_phase5b_pilot.py` and downstream pipelines to compute $p_{\text{noise}} = p_{\text{nom}} / 10^{\text{SNR}/10}$ using fixed nominal base power ($0.3466\text{ pu}^2$) rather than instantaneous frame power.
3. **Implement Quantization Utility:** Add explicit `quantize_adc(v, bits=12, v_fs=1.8)` in `pipeline/` for the measurement perturbation experiment layer.
4. **Implement Dual-Rate Waveform Export in Runner:** Update `scripts/run_phase5b_pilot_simulation.m` to export both 5 kHz (1,000 samples) and 20 kHz (4,000 samples) frames for multi-model research.
5. **Update Topology Nomenclature:** Update scenario schema descriptions from "Line 4-5 breaker" to "Bus 5 Dual-Incomer Breaker (Lines 4-5 and 5-7)".

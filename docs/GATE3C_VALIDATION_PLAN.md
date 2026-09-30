# GATE 3C — Independent Validation Plan

**Document Reference**: `docs/GATE3C_VALIDATION_PLAN.md`
**Date**: September 30, 2026
**Scope**: Physical validation gates for all 8 PQD classes. All tests are independent of the ML model.

---

## 1. Validation Principles

1. **ML-independent**: Every validation test is computed from signal features alone. The ML classifier is never invoked.
2. **Class-specific**: Each class has unique validation criteria derived from its physical definition.
3. **Binary gate**: Each frame either PASSES or FAILS. Failed frames are excluded from the dataset.
4. **Ground-truth provenance**: The pass/fail result is recorded alongside the scenario metadata, not derived from ML output.
5. **Fail-safe**: A frame that fails its own class validation cannot enter the training set for that class.

---

## 2. Feature Definitions Used in Validation

All features are computed by the production DSP pipeline (`dsp/enhanced_features.py`, `dsp/baseline_features.py`):

| Feature | Definition |
|:---|:---|
| `rms_full_pu` | √(mean(x²)) over full 200 ms window |
| `windowed_rms_min_pu` | Minimum of sliding half-cycle RMS trace |
| `windowed_rms_max_pu` | Maximum of sliding half-cycle RMS trace |
| `peak_pu` | max(|x|) |
| `thd_percent` | THD = √(ΣH_n²)/H1 × 100% |
| `h_n_pu` | Goertzel magnitude at harmonic n |
| `crest_factor` | peak_pu / rms_full_pu |
| `system_freq_hz` | Measured via zero-crossing interpolation |
| `duration_ms` | Sliding RMS abnormal sample count × (1000/Fs) |
| `snr_db` | Phase-aware orthogonal projection SNR |
| `envelope_depth` | Peak-to-peak amplitude of Hilbert envelope |
| `envelope_freq_hz` | Dominant frequency of Hilbert envelope |
| `notch_depth_pu` | Max instantaneous voltage depression below expected |
| `notch_energy_ratio` | High-pass residual energy / total energy |
| `transient_peak_pu` | Peak of high-pass filtered (> 100 Hz) signal |
| `transient_freq_hz` | Dominant frequency of high-pass residual |
| `transient_duration_ms` | Duration of transient envelope > 10% of peak |

---

## 3. Class-by-Class Validation Gates

---

### 3.1 Normal

The Normal class uses the existing 8-layer validation from Gate 3B (`scripts/build_and_validate_normal_dataset.py`).

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| N-01 | `rms_full_pu` | ∈ | [0.50, 0.70] | Bus 5 physical operating range |
| N-02 | `peak_pu` | ∈ | [0.70, 0.98] | Bus 5 physical operating range |
| N-03 | `system_freq_hz` | ∈ | [59.90, 60.10] | NERC BAL-003-2 frequency deadband |
| N-04 | Phase balance (VUF) | < | 2.0% | IEEE 1159-2019 Clause 4.4.6 |
| N-05 | `thd_percent` | < | 2.0% | IEEE 519-2022 Table 1 (operational reference) |
| N-06 | `crest_factor` | ∈ | [1.38, 1.50] | Theoretical √2 ± 5% |
| N-07 | Waveform continuity (max Δv) | < | 0.15 pu/sample | No discontinuity artifact |
| N-08 | `duration_ms` | == | 0.0 | No disturbance interval detected |

**Normal Contamination Rule:** A frame labeled Normal that fails any gate above is excluded. No exceptions.

---

### 3.2 Voltage Sag

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| SAG-01 | `windowed_rms_min_pu` | ≥ | 0.10 | IEEE 1159-2019 Clause 3.1.58 lower bound |
| SAG-02 | `windowed_rms_min_pu` | < | 0.90 | IEEE 1159-2019 Clause 3.1.58 upper bound |
| SAG-03 | `duration_ms` | ≥ | 8.33 | ≥ 0.5 cycle minimum (IEEE 1159 Table 2) |
| SAG-04 | `rms_full_pu` | < | 0.90 | Full-window average depressed below Normal lower bound |
| SAG-05 | `thd_percent` | < | 5.0 | No harmonic co-event during sag (class isolation) |
| SAG-06 | `system_freq_hz` | ∈ | [59.5, 60.5] | Frequency not disturbed |
| SAG-ANTI-INTERRUPT | `windowed_rms_min_pu` | ≥ | 0.10 | Distinguishes from Interruption (< 0.10 pu) |

**Anti-contamination:** A sag frame must satisfy `windowed_rms_min_pu ≥ 0.10 pu` (else it is an Interruption).

---

### 3.3 Voltage Swell

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| SWL-01 | `windowed_rms_max_pu` | > | 1.10 | IEEE 1159-2019 Clause 3.1.65 lower bound |
| SWL-02 | `windowed_rms_max_pu` | ≤ | 1.80 | IEEE 1159-2019 Clause 3.1.65 upper bound |
| SWL-03 | `duration_ms` | ≥ | 8.33 | ≥ 0.5 cycle minimum (IEEE 1159 Table 2) |
| SWL-04 | `peak_pu` | > | 1.13 | Peak above Normal upper bound (1.10 × √2 × 0.99) |
| SWL-05 | `crest_factor` | > | 1.50 | Crest factor elevated (excludes balanced flicker) |
| SWL-06 | `system_freq_hz` | ∈ | [59.5, 60.5] | Frequency not disturbed |
| SWL-07 | `thd_percent` | < | 5.0 | No harmonic co-event |

**Anti-contamination:** `windowed_rms_max_pu > 1.10` proves this is not Normal (Normal max ≈ 0.98).

---

### 3.4 Voltage Interruption

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| INT-01 | `windowed_rms_min_pu` | < | 0.10 | IEEE 1159-2019 Clause 3.1.34 |
| INT-02 | `windowed_rms_min_pu` | > | 0.0 | Residual non-zero (motor back-EMF model) |
| INT-03 | `duration_ms` | ≥ | 8.33 | ≥ 0.5 cycle (sub-cycle is Notch, not Interruption) |
| INT-04 | `duration_ms` | ≤ | 500.0 | Within instantaneous category (≤ 30 cycles) |
| INT-05 | `rms_full_pu` | < | 0.70 | Full-window average substantially depressed |
| INT-SAG-BOUNDARY | `windowed_rms_min_pu` | < | 0.10 | Hard boundary with Sag. No engineered buffer. |

**Anti-contamination:** `windowed_rms_min_pu < 0.10` proves this is not a Sag. `duration_ms ≥ 8.33` proves it is not a sub-cycle event.

---

### 3.5 Harmonics

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| HAR-01 | `thd_percent` | > | 5.0 | Clear disturbance above Normal THD (< 0.09%) |
| HAR-02 | Active harmonic count | ≥ | 2 | At least 2 harmonic orders elevated |
| HAR-03 | At least one of {h3_pu, h5_pu, h7_pu} | > | 0.03 | Characteristic odd harmonics present |
| HAR-04 | `rms_full_pu` | ∈ | [0.50, 0.80] | RMS within physical range (harmonics add energy but not dramatically) |
| HAR-05 | `system_freq_hz` | ∈ | [59.5, 60.5] | Fundamental not disturbed |
| HAR-06 | `windowed_rms_min_pu` | > | 0.90 | No sag co-event (class isolation) |
| HAR-07 | Duration | == | "full window" | Harmonics are steady-state; must persist throughout frame |

**Anti-contamination check:** `thd_percent > 5.0` proves this is not Normal (Normal THD < 0.09% at Bus 5). Any frame where `thd_percent < 3.0%` fails HAR-01 and is excluded.

**Note on IEEE 519 THD limits:** The 5% threshold is a *dataset design choice* for ML discriminability. The IEEE 519-2022 Table 1 limit at 230 kV PCC is 1.5%. These are different thresholds with different purposes.

---

### 3.6 Flicker

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| FLK-01 | `envelope_depth` | > | 0.02 | Modulation depth > 2% (IEEE 1159: 0.1–10% range) |
| FLK-02 | `envelope_depth` | < | 0.15 | Depth < 15% (not swell/sag co-event) |
| FLK-03 | `envelope_freq_hz` | ∈ | [3.0, 20.0] | Modulation frequency in physiological sensitivity band |
| FLK-04 | `windowed_rms_min_pu` | > | 0.90 | RMS stays within Normal band (no sag co-event) |
| FLK-05 | `windowed_rms_max_pu` | < | 1.10 | RMS stays within Normal band (no swell co-event) |
| FLK-06 | `thd_percent` | < | 3.0 | No harmonic co-event |
| FLK-07 | Modulation cycles in window | ≥ | 1.0 | At least 1 complete modulation cycle for feature extraction |

**Anti-contamination:** `envelope_depth > 0.02` AND `windowed_rms ∈ [0.90, 1.10]` distinguishes Flicker from both Normal (no modulation) and Sag/Swell (RMS excursion).

**Implementation note:** `envelope_depth` and `envelope_freq_hz` are computed via the analytic signal (Hilbert transform of Phase A).

---

### 3.7 Notch

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| NOT-01 | `notch_depth_pu` | > | 0.20 | Min notch depth visible above noise |
| NOT-02 | `notch_depth_pu` | ≤ | 0.85 | Max notch depth (less than interruption) |
| NOT-03 | Max notch duration | < | 8.33 ms | Sub-cycle per IEEE 1159 Clause 4.4.4.2 |
| NOT-04 | `notch_energy_ratio` | > | threshold | High-frequency residual energy elevated |
| NOT-05 | Notch periodicity | Detected | — | At least 2 notches present with consistent spacing |
| NOT-06 | `rms_full_pu` | ∈ | [0.50, 0.80] | RMS not grossly disturbed |
| NOT-07 | `system_freq_hz` | ∈ | [59.5, 60.5] | Fundamental not disturbed |

**`notch_depth_pu` computation:** For each expected notch location (from commutation timing), compute:
$$\text{notch\_depth} = 1 - \frac{v[n_{notch}]}{V_m \sin(\theta_{notch})}$$
where $\theta_{notch}$ is the expected phase angle at the notch time.

**`notch_energy_ratio` computation:** High-pass filter (Butterworth, cutoff 500 Hz) the signal, then:
$$\text{notch\_energy\_ratio} = \frac{\sum x_{HP}^2[n]}{\sum x^2[n]}$$

**Anti-contamination:** Notch produces high-frequency spectral energy without sustained THD elevation. THD alone is insufficient to identify notches — the sub-cycle localized structure is diagnostic.

---

### 3.8 Transient

| Gate | Metric | Operator | Threshold | Standard Basis |
|:---:|:---|:---:|:---:|:---|
| TRN-01 | `transient_peak_pu` | > | 1.15 | Peak above Normal envelope (Normal peak < 1.10 pu) |
| TRN-02 | `transient_peak_pu` | ≤ | 4.0 | Within IEEE 1159 Table 2 maximum (0–4 pu) |
| TRN-03 | `transient_freq_hz` | ∈ | [200, 1500] | Oscillatory frequency above power frequency |
| TRN-04 | `transient_duration_ms` | ∈ | [0.3, 50.0] | Duration per IEEE 1159 Table 2 low-frequency transient |
| TRN-05 | `transient_duration_ms` | < | 167.0 | < 10 cycles (not a sustained swell or sag) |
| TRN-06 | High-pass energy ratio | > | 0.05 | Significant non-fundamental energy |
| TRN-07 | `rms_full_pu` | ∈ | [0.40, 0.90] | RMS modestly elevated; not sustained swell |

**`transient_peak_pu` computation:** High-pass filter signal (Butterworth, cutoff 100 Hz), compute max(|x_HP|).

**`transient_freq_hz` computation:** Find peak frequency of |FFT(x_HP)|² in [200, 2500] Hz.

**`transient_duration_ms` computation:** Time interval where |x_HP[n]| > 0.10 × transient_peak.

**Anti-contamination:** A frame must have `transient_peak_pu > 1.15` (proves it is not Normal) AND `transient_duration_ms < 50 ms` (proves it is not a swell). THD may be briefly elevated during transient — do not use THD alone to gate transients.

---

## 4. Normal Contamination Matrix

**Rule:** Before any disturbance frame is added to the dataset, it must pass its own class gates (section 3) AND fail the following Normal contamination check (proving it is not Normal).

| Disturbance Class | Contamination Detector | Cannot Enter Dataset If... |
|:---|:---|:---|
| Sag | `windowed_rms_min_pu` | ≥ 0.90 pu (would pass as Normal) |
| Swell | `windowed_rms_max_pu` | ≤ 1.10 pu (would pass as Normal) |
| Interruption | `windowed_rms_min_pu` | ≥ 0.10 pu (would be Sag) or ≥ 0.90 (Normal) |
| Harmonics | `thd_percent` | ≤ 3.0% (indistinguishable from Normal) |
| Flicker | `envelope_depth` | ≤ 1.0% (indistinguishable from Normal) |
| Notch | `notch_energy_ratio` | ≤ calibrated Normal baseline + 5σ |
| Transient | `transient_peak_pu` | ≤ 1.10 pu (within Normal envelope) |

---

## 5. Validation Implementation Plan

Each validation gate maps to a Python function in `scripts/validate_disturbance_frame.py` (to be created at Gate 3D):

```python
def validate_frame(waveform: np.ndarray, declared_class: str,
                   scenario_metadata: dict, fs: float = 5000.0,
                   f0: float = 60.0) -> dict:
    """
    Returns:
        {
            'validation_passed': bool,
            'gates_passed': [str, ...],
            'gates_failed': [str, ...],
            'contamination_check': bool,
            'metrics': dict  # all computed validation metrics
        }
    DOES NOT USE THE ML MODEL.
    """
```

The function must:
1. Extract all validation metrics (windowed RMS, envelope, harmonic content, etc.)
2. Apply the declared class's gate conditions (section 3)
3. Apply the Normal contamination check (section 4)
4. Return a structured result that is stored alongside the frame in the dataset

---

## 6. Validation Statistics Requirements

At the end of each disturbance class generation batch, report:

| Statistic | Requirement |
|:---|:---|
| Total frames generated | N |
| Frames passing all gates | N_pass |
| Validation pass rate | N_pass / N ≥ 95% |
| Contamination failures | Must be 0 for any frame entering dataset |
| Unexpected Normal-class contamination | Must be 0 |

> [!IMPORTANT]
> A validation pass rate below 95% indicates a systematic problem with parameter selection or injection mechanism, not a data quality issue. Do not lower thresholds to increase pass rate. Fix the parameters.

---

## 7. Cross-Class Feature Separation Check

After all classes are generated, compute the following to verify class separability before training:

| Feature Pair | Expected Separation |
|:---|:---|
| `rms_full_pu`: Normal vs Sag | Sag < 0.90; Normal 0.50–0.70 |
| `windowed_rms_min_pu`: Sag vs Interruption | Interruption < 0.10; Sag ≥ 0.10 |
| `windowed_rms_max_pu`: Swell vs Normal | Swell > 1.10; Normal ≤ 1.10 |
| `thd_percent`: Harmonics vs Normal | Harmonics > 5%; Normal < 0.09% |
| `envelope_depth`: Flicker vs Normal | Flicker > 2%; Normal < 0.5% |
| `notch_energy_ratio`: Notch vs Normal | Notch elevated; Normal baseline |
| `transient_peak_pu`: Transient vs Normal | Transient > 1.15; Normal < 1.10 |

These must be verified by a scatter plot and statistical separation test (Cohen's d ≥ 2.0) before training begins.

---

## 8. Dataset Provenance Chain

```
MATLAB Simulation (IEEE 9-bus, Bus 5)
        ↓
PQD_Scenario_Controller (declares class + parameters + seed)
        ↓
Working Simulink Model (injection active)
        ↓
Bus 5 Vabc_5 waveform (1000 samples × 3 phases)
        ↓
Production DSP pipeline (extract_enhanced_features)
        ↓
validate_frame() — ALL GATES CHECKED, NO ML
        ↓ PASS
Frame added to dataset with:
    - ground_truth = scenario_controller.class
    - scenario_metadata (parameters, provenance, seed)
    - validation_results (all gate outcomes)
    - NPZ waveform + CSV features
        ↓ FAIL
Frame logged to rejection_log.csv — NOT added to dataset
```

**Invariant:** Ground truth label is set exactly once, by the scenario controller, before any feature extraction or validation.

---

## Gate 3C Validation Plan Status

```
GATE3C_VALIDATION_PLAN = COMPLETE

Per-class validation gates: 8 classes × ~7 gates = 56 validation conditions defined
Normal contamination matrix: 7 rules (one per disturbance class)
Implementation plan: defined (Gate 3D deliverable)
Provenance chain: fully specified
No ML model is used in any validation step
```

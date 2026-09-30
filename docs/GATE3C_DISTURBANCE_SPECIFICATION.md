# GATE 3C — PQ Disturbance Specification & Scenario Architecture

**Document Reference**: `docs/GATE3C_DISTURBANCE_SPECIFICATION.md`
**Date**: September 30, 2026
**Status**: SPECIFICATION ONLY — No waveforms generated. No retraining. Simulink model unchanged.

---

## 1. Scope & Constraints

This document specifies the disturbance generation architecture for the IEEE 9-bus 60-Hz Power Quality Disturbance (PQD) dataset. It is a design-only document.

**Hard constraints throughout:**
- IEEE 9-bus Simulink model `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` is **pristine and unchanged**
- No disturbance waveforms are generated here
- ML model weights are unchanged
- Ground-truth labels originate exclusively from the scenario controller
- Every parameter provenance is declared explicitly

**Provenance taxonomy:**

| Tag | Meaning |
|:---|:---|
| `STANDARD-SUPPORTED` | Range/value explicitly stated in the cited standard clause |
| `ENGINEERING-INTERPRETATION` | Derived from standard principles; accepted in power-engineering literature |
| `PROJECT-DESIGN-CHOICE` | Selected for dataset coverage; not mandated by any standard |
| `SIMULATION-PARAMETER` | Discretization, solver, or model artifact |
| `DATASET-DESIGN-CHOICE` | Statistical balance, class count, or windowing decision |

---

## 2. Target Taxonomy

| Label Index | Class | IEEE 1159-2019 Category |
|:---:|:---|:---|
| 0 | Normal | Nominal steady-state |
| 1 | Sag | Short-duration RMS variation — sag/dip |
| 2 | Swell | Short-duration RMS variation — swell |
| 3 | Interruption | Short-duration RMS variation — interruption |
| 4 | Harmonics | Spectral distortion — harmonics |
| 5 | Flicker | Voltage fluctuation |
| 6 | Notch | Waveform distortion — notching |
| 7 | Transient | Transient — oscillatory |

> [!IMPORTANT]
> Label indices 0–7 match `_CLASS_LABELS` in `dsp/phase_processor.py`. The Normal class occupies index 3 in the existing production code. **This must be reconciled before training.** The mapping above is the proposed target; the actual index assignment must match the model contract.

---

## 3. Disturbance Model Architecture

### 3.1 Pristine Reference vs Working Model

```
IEEE_9bus_PQD_HIL_R2025a.slx          ← PRISTINE. Never modified.
    │  (reference electrical network)
    ▼  (copy for disturbance work)
IEEE_9bus_PQD_DISTURBANCES.slx         ← Working model for injection
    │
    ├── PQD_Scenario_Controller         ← Reads scenario JSON, enables ONE class
    ├── PQD_Disturbance_Manager         ← Routes to exactly one injector block
    │
    ├── PQD_Sag                         ← Fault impedance at Bus 4/5
    ├── PQD_Swell                       ← Load trip / fault on unfaulted phases
    ├── PQD_Interruption                ← Breaker + fault impedance
    ├── PQD_Harmonics                   ← Controlled current source (nonlinear load)
    ├── PQD_Flicker                     ← Cyclic load / arc furnace model
    ├── PQD_Notch                       ← 6-pulse thyristor bridge or controlled switch
    └── PQD_Transient                   ← Shunt capacitor bank switching
```

**Working model derivation rule:**
- Copy `IEEE_9bus_PQD_HIL_R2025a.slx` to `IEEE_9bus_PQD_DISTURBANCES.slx`
- Verify MD5/SHA-256 of reference model before and after every batch
- Reference model is write-protected at OS level

### 3.2 Scenario Controller Design

```
PQD_Scenario_Controller
├── Reads: GATE3C_SCENARIO_SCHEMA.json (one scenario object)
├── Sets:  active_class  ∈ {Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient}
│         enable_flags:  exactly ONE = 1, all others = 0
│         parameters:    forwarded to the active injector only
│         seed:          passed to stochastic blocks
├── Emits: scenario_metadata (carried alongside waveform)
├── Rule:  No hidden activation. enable flags are logged.
└── Rule:  No multi-class simultaneous injection (one scenario = one class).
```

### 3.3 Ground-Truth Label Generation

```
scenario_controller declares class → ground_truth = that class
                                   ↓
                          written to scenario_metadata
                                   ↓
                          attached to every waveform frame
                                   ↓
                    feature CSV: class column + label_idx column

The ML model is NEVER consulted for labeling.
The ML model is trained on these labels.
```

---

## 4. Class-by-Class Specification

---

### 4.1 Normal (Reference Class — Already Generated)

**Status**: 1,120 frames complete. No further generation needed here.

- Physical phenomenon: Sinusoidal voltage at 60 Hz, nominal Bus 5 amplitude, zero disturbance
- Measurement: `Vabc_5` Phase A RMS = 0.5887 pu, THD < 0.09%, SNR ≈ 51.7 dB
- See `docs/GATE3B1_NORMAL_DATASET_QUALITY_AUDIT.md` for complete specification

---

### 4.2 Voltage Sag

#### Physical Phenomenon
A reduction in RMS voltage at power frequency, resulting from a system fault, large motor starting, or transformer energization. The voltage at the measurement bus drops during the disturbance interval, then recovers.

#### IEEE 1159-2019 Definition (Clause 3.1.58, Table 2)
- Residual voltage: **0.10 to 0.90 pu** — `STANDARD-SUPPORTED`
- Duration: **0.5 cycle to 1 minute** — `STANDARD-SUPPORTED`

#### Measurement Quantity
Windowed half-cycle RMS (IEC 61000-4-30 §5.2): `U_rms(1/2)` tracked across the 200 ms frame.

#### Proposed Injection Location & Mechanism
**Preferred mechanism: Three-phase-to-ground fault impedance at Bus 4 or Bus 7 (the supply buses adjacent to Bus 5).**

- Insert a three-phase fault block with controllable impedance $Z_f$ between Bus 4/7 and ground
- Increasing $Z_f$ reduces fault current and sag depth, allowing parametric control of residual magnitude at Bus 5
- Network-level mechanism — voltage change is real, driven by actual load-flow redistribution
- **Alternative (approved for use):** Single-phase-to-ground fault for phase-specific sags; line-to-line fault for two-phase sags

**Do NOT use:** Post-simulation multiplication of Bus 5 voltages. This destroys physical current-voltage coupling and produces waveforms inconsistent with real fault physics.

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Residual voltage magnitude | 0.10–0.90 pu | `STANDARD-SUPPORTED` |
| Duration | 0.5–8 cycles (8.33–133 ms at 60 Hz) | `PROJECT-DESIGN-CHOICE` (within IEEE bounds) |
| Onset time within window | 15–50 ms | `PROJECT-DESIGN-CHOICE` |
| Transition type | Zero-crossing or point-on-wave | `ENGINEERING-INTERPRETATION` |
| Phase scope | Three-phase (balanced); single-phase (unbalanced) | `PROJECT-DESIGN-CHOICE` |
| Fault impedance $Z_f$ | Parametric (derived from target residual) | `SIMULATION-PARAMETER` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- `windowed_rms_min_pu ∈ [0.10, 0.90)` during event interval
- `sag_duration_ms ≥ 8.33 ms` (0.5 cycle minimum)
- Full-window RMS lower than Normal lower bound (0.90 pu)
- No THD spike during sag (confirms fault, not harmonic source)

#### Distinction from Interruption
Sag: residual ≥ 0.10 pu. Interruption: residual < 0.10 pu. Boundary is explicit per IEEE 1159 Clause 3.1.34.

---

### 4.3 Voltage Swell

#### Physical Phenomenon
A temporary increase in RMS voltage at power frequency. Primary causes: single-line-to-ground fault on an unfaulted phase (Ferranti effect), sudden large load disconnection, or capacitor bank energization without adequate controls.

#### IEEE 1159-2019 Definition (Clause 3.1.65, Table 2)
- Magnitude: **1.10 to 1.80 pu** — `STANDARD-SUPPORTED`
- Duration: **0.5 cycle to 1 minute** — `STANDARD-SUPPORTED`

#### Measurement Quantity
Windowed half-cycle RMS exceeding 1.10 pu on at least one phase.

#### Proposed Injection Location & Mechanism
**Preferred: Single-line-to-ground fault at Bus 4 or Bus 7 creates voltage rise on the unfaulted phases (B, C) at Bus 5 due to ground potential shift.**

- Alternatively: Sudden disconnection of Load C (Bus 9) as a load-trip step produces transient swell at Bus 5 through reduced reactive-power consumption
- Generator voltage schedule upward step (AVR setpoint increase) produces sustained swell — validated via Simulink generator block

**Do NOT use:** Post-simulation multiplication. Physically, swells are driven by network topology changes, not by scaling a measurement.

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Swell peak magnitude | 1.10–1.80 pu | `STANDARD-SUPPORTED` |
| Duration | 0.5–8 cycles | `PROJECT-DESIGN-CHOICE` |
| Onset time within window | 15–50 ms | `PROJECT-DESIGN-CHOICE` |
| Phase scope | Single-phase (SLG source) or three-phase (load trip) | `PROJECT-DESIGN-CHOICE` |
| Transition type | Zero-crossing preferred | `ENGINEERING-INTERPRETATION` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- `windowed_rms_max_pu ∈ (1.10, 1.80]` during event interval
- `swell_duration_ms ≥ 8.33 ms`
- Crest factor > 1.50 (distinguishes swell from Normal)
- Peak voltage > 1.13 pu (Normal upper bound 1.10 pu × √2 peak limit)

---

### 4.4 Voltage Interruption

#### Physical Phenomenon
Near-complete loss of supply voltage, caused by protective relay operation (recloser, circuit breaker), blown fuse, or temporary fault clearing. The voltage drops to near zero for the interruption interval, then recovers (for momentary/temporary interruption).

#### IEEE 1159-2019 Definition (Clause 3.1.34, Table 2)
- Residual voltage: **< 0.10 pu** — `STANDARD-SUPPORTED`
- Duration categories:
  - Instantaneous: 0.5–30 cycles (8.33–500 ms) — `STANDARD-SUPPORTED`
  - Momentary: 30 cycles–3 s — `STANDARD-SUPPORTED`
  - Temporary: 3–60 s — `STANDARD-SUPPORTED`
  - Sustained: > 1 min — `STANDARD-SUPPORTED`

**Dataset scope:** Instantaneous interruption only (within 200 ms window constraint). — `DATASET-DESIGN-CHOICE`

#### Measurement Quantity
Windowed half-cycle RMS < 0.10 pu during the event interval (IEC 61000-4-30).

> [!IMPORTANT]
> Sub-cycle voltage dropouts (< 0.5 cycle = < 8.33 ms) are **NOT** interruptions per IEEE 1159. They are Notches or Transients. The duration gate must enforce the 0.5-cycle minimum.

#### Distinction from Severe Sag
- Sag: 0.10 ≤ residual < 0.90 pu
- Interruption: residual < 0.10 pu
- This boundary is **IEEE-SPECIFIED** (1159-2019 Clause 3.1.34). No engineered buffer zone should be added.

#### Proposed Injection Location & Mechanism
**Preferred: Three-phase circuit breaker block inserted on the Bus 4–Bus 5 transmission line. Controlled open/close event.**

- Breaker opens at zero-crossing of phase A current (simulates relay operation)
- Motor back-EMF and trapped-energy capacitance produce the residual 0.01–0.09 pu during the open interval
- Breaker recloses after the interruption interval

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Residual voltage | 0.00–0.095 pu | `STANDARD-SUPPORTED` (must remain < 0.10) |
| Duration | 1–10 cycles (16.7–167 ms) | `PROJECT-DESIGN-CHOICE` (within instantaneous category) |
| Onset time | 15–40 ms | `PROJECT-DESIGN-CHOICE` |
| Transition | Zero-crossing (breaker model) | `ENGINEERING-INTERPRETATION` |
| Phase scope | Three-phase (fault isolation) | `ENGINEERING-INTERPRETATION` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- `windowed_rms_min_pu < 0.10` during event interval
- `interruption_duration_ms ≥ 8.33 ms` (≥ 0.5 cycle)
- `windowed_rms_min_pu > 0.0` (residual present — not hard zero)

---

### 4.5 Harmonics

#### Physical Phenomenon
Steady-state sinusoidal voltage components at integer multiples of the fundamental frequency, produced by nonlinear loads (six-pulse rectifiers, variable-frequency drives, switched-mode power supplies, arc furnaces, transformers in saturation).

#### Applicable Standards
- **IEEE 1159-2019**, Clause 4.4.4.1 — Harmonic definition: $f_n = n \times f_1$
- **IEEE 519-2022**, Clause 3.1.25, Table 1 — Voltage distortion limits at PCC

#### Demarcation: Standard Limit ≠ Dataset Classification Threshold

IEEE 519-2022 Table 1 establishes **grid-operation compliance limits** at the PCC (e.g. THD ≤ 1.5% at 230 kV). These are **NOT** the ML classification thresholds. The ML classifier must learn to distinguish harmonic waveforms from Normal regardless of whether they exceed grid limits.

**Dataset classification criterion:** A frame is labeled Harmonics if and only if the waveform was generated by the PQD_Harmonics injector block. — `DATASET-DESIGN-CHOICE`

#### Harmonic Orders and Physical Sources

| Order | Frequency (60 Hz) | Primary Physical Source |
|:---:|:---:|:---|
| H2 | 120 Hz | Asymmetric half-wave rectifiers, transformer saturation |
| H3 | 180 Hz | Single-phase loads (dominant zero-sequence harmonic) |
| H5 | 300 Hz | Six-pulse converters (characteristic odd harmonic, negative sequence) |
| H7 | 420 Hz | Six-pulse converters (characteristic odd harmonic, positive sequence) |
| H9 | 540 Hz | Three-phase unbalanced loads |
| H11 | 660 Hz | Twelve-pulse converters |

#### Proposed Injection Mechanism
**Preferred: Controlled harmonic current source block at Bus 5 load bus.**

- Inject a multi-component current source $I_{harm}(t) = \sum_{n} I_n \sin(n \omega_0 t + \phi_n)$ at the Bus 5 load node
- Bus 5 voltage is modified by network impedance × injected current (physically correct)
- Alternative: NonLinear Load SimPowerSystems block (more physically realistic, harder to parametrize)
- Parameter control: individual harmonic amplitudes $I_n$, phase angles $\phi_n$

> [!NOTE]
> THD alone is insufficient as a classification feature. The individual harmonic profile (H2, H3, H5, H7, H9, H11 magnitudes and ratios) provides the discriminative signature.

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Active harmonic orders | Subset of {2,3,5,7,9,11} | `ENGINEERING-INTERPRETATION` |
| H3 magnitude | 0.04–0.15 pu | `ENGINEERING-INTERPRETATION` (dominant odd harmonic) |
| H5 magnitude | 0.02–0.10 pu | `ENGINEERING-INTERPRETATION` |
| H7 magnitude | 0.01–0.06 pu | `ENGINEERING-INTERPRETATION` |
| H2 magnitude | 0.005–0.04 pu | `ENGINEERING-INTERPRETATION` |
| H9, H11 magnitudes | 0.002–0.04 pu | `ENGINEERING-INTERPRETATION` |
| Harmonic phase angles φ_n | Uniform random [0, 2π] | `SIMULATION-PARAMETER` |
| Composite THD | 5–20% | `DATASET-DESIGN-CHOICE` (disturbance visible, not just noise) |
| Duration | Continuous (full 200 ms window) | `ENGINEERING-INTERPRETATION` (steady-state phenomenon) |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- THD > 5% (clear disturbance signal above Normal THD < 0.09%)
- At least 2 harmonic orders with magnitude > 0.01 pu
- Goertzel magnitude at active harmonic frequencies > Normal baseline + 3σ

---

### 4.6 Voltage Flicker

#### Physical Phenomenon
Systematic cyclic variation of the voltage envelope (amplitude modulation) caused by loads with periodic power demand fluctuations: electric arc furnaces, welding machines, cyclic motor loads, wind turbine blade-pass torque. The resulting luminance fluctuation in incandescent lamps causes visual discomfort.

#### Applicable Standards
- **IEEE 1159-2019**, Clause 4.4.3 — Voltage fluctuation phenomenon
- **IEEE 1453-2022**, Clause 4 — Flickermeter specification; short-term flicker severity $P_{st}$

#### Important Demarcation
IEEE 1453-2022 defines **$P_{st}$** (short-term flicker severity) as a 10-minute aggregate metric. A 200 ms window cannot compute a valid $P_{st}$. The 200 ms dataset frame captures **instantaneous envelope modulation depth** and **modulation frequency**, not $P_{st}$.

**This is a `DATASET-DESIGN-CHOICE`**: the project uses sinusoidal AM as the observable because it is the canonical IEC 61000-4-15 / IEEE 1453 flickermeter calibration stimulus, and its features (sideband presence, modulation depth) are extractable in 200 ms.

#### Why Sinusoidal AM Is Appropriate Here
- IEEE 1453-2022 Clause 5 mandates sinusoidal voltage fluctuation as the calibration signal for flickermeters
- Sinusoidal AM generates symmetric sidebands at $(f_0 \pm f_m)$ which are measurable via Goertzel or FFT in a 200 ms window
- Arc furnace flicker is approximately modeled as broadband AM; sinusoidal AM is the deterministic approximation used in standards calibration

#### Injection Mechanism
**Preferred: Cyclic load switching at Bus 5 or Bus 6 (resistive/reactive load with programmable duty cycle).**

- A controllable resistance/load block switches at modulation frequency $f_m$, causing periodic reactive-power demand that modulates Bus 5 voltage
- Alternatively: Direct amplitude modulation of the voltage setpoint of a generator or controlled voltage source feeding Bus 5

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Modulation frequency $f_m$ | 0.5–30 Hz (IEEE 1159 range) | `STANDARD-SUPPORTED` |
| $f_m$ simulation sub-range | 5–15 Hz | `PROJECT-DESIGN-CHOICE` (peak human sensitivity ~8.8 Hz per IEEE 1453) |
| Modulation depth $m$ (peak) | 0.03–0.10 (3–10%) | `STANDARD-SUPPORTED` (IEEE 1159 typical range 0.1–10%) |
| Duration | Full 200 ms window | `PROJECT-DESIGN-CHOICE` |
| Phase scope | Three-phase (symmetric load fluctuation) | `ENGINEERING-INTERPRETATION` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Sampling Adequacy for Flicker
- Modulation frequencies 5–15 Hz produce 1.0–3.0 full modulation cycles within the 200 ms window — sufficient for envelope tracking
- Native DFT bin width (1/0.2 = 5 Hz) cannot resolve $f_m$ < 5 Hz without zero-padding — `PROJECT-DESIGN-CHOICE` to avoid sub-5 Hz $f_m$

#### Validation Metrics
- Envelope modulation detected via Hilbert transform or analytic signal: modulation depth $m \in [0.03, 0.10]$
- Modulation frequency recovered via zero-padded FFT of envelope: $f_m \in [5, 15]$ Hz
- Waveform RMS remains within [0.90, 1.10] pu (flicker is NOT a sag/swell)

---

### 4.7 Voltage Notch

#### Physical Phenomenon
A periodic sub-cycle voltage reduction caused by commutation of a power electronic converter. During current commutation between phases of a thyristor bridge (e.g., six-pulse rectifier), both thyristors in consecutive phases conduct simultaneously for a brief interval, creating a line-to-line short circuit that drives the bus voltage toward zero. The resulting notch is:
- Narrow width (~100–1000 μs, typically < 1 ms)
- Repeats every fundamental cycle (or at a multiple of the commutation frequency)
- Associated with a sharp dip in instantaneous voltage, not in RMS

#### Applicable Standards
- **IEEE 1159-2019**, Clause 4.4.4.2, Table 2 — Notching as waveform distortion
- **IEEE 519-2022**, Clause 5.3 — Voltage notch depth and area limits

#### Why Not Copy Legacy 600 μs Notch
The legacy dataset used a fixed 600 μs notch width. This was a simulation convenience, not derived from a specific converter type. The correct approach is to:
1. Select a converter type (6-pulse or 12-pulse thyristor bridge)
2. Derive notch width from commutation reactance: $\Delta t_{notch} = \frac{L_{comm} \cdot I_{dc}}{\sqrt{2} V_{LL}}$
3. Allow parametric variation in notch width, depth, and phase offset

#### Proposed Injection Mechanism
**Preferred: 6-pulse thyristor rectifier block connected as load at Bus 5.**

- A three-phase fully-controlled thyristor rectifier (6-pulse) load at Bus 5 inherently produces periodic commutation notches at $6 \times f_0 = 360$ Hz (6 notches per fundamental cycle)
- Firing angle $\alpha$ controls notch depth and DC current
- Commutation reactance $L_{comm}$ controls notch width
- Alternative: Controlled switching element inserted on phase conductors with programmable pulse timing (simpler to parametrize, less physically rigorous)

#### Notch Width & Sampling Adequacy
At 5 kHz, a 200 μs notch spans 1 sample, a 1 ms notch spans 5 samples.

| Notch Width | Samples at 5 kHz | Adequacy |
|:---:|:---:|:---|
| 200 μs | 1 | Borderline — aliasing risk. Waveform is correct but features degrade |
| 400 μs | 2 | Acceptable for energy detection |
| 600 μs | 3 | Adequate for Goertzel harmonic content |
| 1000 μs | 5 | Good — 5-point notch clearly resolved |

> [!WARNING]
> Notch widths below 400 μs (< 2 samples at 5 kHz) approach the Nyquist limit. High-fidelity notch features require at least 3–5 samples per notch. Use notch widths ≥ 400 μs (`PROJECT-DESIGN-CHOICE`).

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Notch depth fraction | 0.20–0.80 pu | `ENGINEERING-INTERPRETATION` (IEEE 519 Table 2 notch area limits) |
| Notch width | 0.4–1.2 ms | `PROJECT-DESIGN-CHOICE` (≥ 2 samples at 5 kHz) |
| Notch repetition | 1 per cycle (6-pulse = 6 per cycle) | `ENGINEERING-INTERPRETATION` |
| Phase offset within cycle | Near zero-crossing of each commutation | `ENGINEERING-INTERPRETATION` |
| Duration | Full 200 ms window (steady-state converter load) | `ENGINEERING-INTERPRETATION` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- Instantaneous voltage depression > 20% of peak at notch times
- Notch periodicity confirmed: inter-notch interval ≈ 16.67 ms (1 cycle) or 2.78 ms (6/cycle)
- Notch width < 0.5 cycle (< 8.33 ms) — per IEEE 1159 sub-cycle requirement
- High-frequency spectral energy increase (Goertzel at notch harmonics)

---

### 4.8 Oscillatory Transient

#### Physical Phenomenon
A sudden, non-power-frequency voltage change containing both positive and negative polarity components, damped at a rate determined by system resistance. Physical causes include:
- Capacitor bank energization (produces oscillatory voltage of 200–1000 Hz)
- Transformer back-to-back switching
- Cable discharge after fault clearing
- Load rejection

#### Applicable Standard
- **IEEE 1159-2019**, Clause 4.4.1.2, Table 2 — Low-frequency oscillatory transient: < 5 kHz, duration 0.3–50 ms

#### Frequency Classification (IEEE 1159 Table 2)

| Category | Frequency | Duration |
|:---|:---:|:---:|
| High frequency | > 500 kHz | < 5 μs |
| Medium frequency | 5–500 kHz | 20 μs–50 ms |
| **Low frequency** | **< 5 kHz** | **0.3–50 ms** |

**This project targets low-frequency oscillatory transients exclusively.** — `DATASET-DESIGN-CHOICE`

#### Transient Bandwidth vs 5 kHz Sampling — Critical Analysis

> [!WARNING]
> **5 kHz Sampling Limitation for Transients**
>
> The IEEE 1159 low-frequency transient band extends to 5 kHz. The Nyquist frequency at 5 kHz sampling is 2500 Hz. Therefore:
>
> - Transient frequencies **300–2000 Hz**: Adequately captured at 5 kHz (OSR ≥ 2.5)
> - Transient frequencies **2000–2500 Hz**: Captured but near-Nyquist; aliasing risk grows
> - Transient frequencies **> 2500 Hz**: **ALIASED**. Cannot be represented at 5 kHz
>
> **Decision:** Restrict simulated transient frequencies to 300–1200 Hz at 5 kHz sampling. This is a `PROJECT-DESIGN-CHOICE` driven by sampling constraints. Transients at higher frequencies require a higher-rate data path (e.g., 20–50 kHz acquisition) for correct representation.
>
> **Higher-rate path requirement:** If future HIL hardware provides > 20 kHz sampling, transients up to 5 kHz can be captured. For the current 5 kHz dataset, the dataset label "Transient" covers only the 300–1200 Hz sub-band. This must be documented in the dataset README.

#### Proposed Injection Mechanism
**Preferred: Three-phase capacitor bank switching at Bus 5 or Bus 6 using a breaker block with pre-insertion inductor.**

- A shunt capacitor bank is switched onto the bus at a controlled point-on-wave
- The LC natural frequency $f_n = \frac{1}{2\pi\sqrt{LC}}$ determines transient oscillation frequency
- $L$ = system inductance at bus; $C$ = capacitor bank size
- Parametric control: bank size → frequency; switching angle → peak magnitude; system resistance → damping
- Alternative: Controlled voltage step superimposed on Bus 5 with exponentially-damped sinusoidal shape (less physically rigorous, simpler to implement)

#### Analytical Model (for data-generation validation)
$$v_{trans}(t) = A_{trans} \cdot V_m \cdot e^{-(t-t_s)/\tau} \cdot \sin(2\pi f_{trans}(t-t_s)) \cdot u(t-t_s)$$

where:
- $f_{trans} \in [300, 1200]$ Hz — `PROJECT-DESIGN-CHOICE`
- $A_{trans} \in [0.40, 1.20]$ pu — `ENGINEERING-INTERPRETATION`
- $\tau \in [2, 8]$ ms — `ENGINEERING-INTERPRETATION`
- $t_s \in [40, 120]$ ms — `PROJECT-DESIGN-CHOICE`

#### Parameters

| Parameter | Range | Provenance |
|:---|:---|:---|
| Transient frequency | 300–1200 Hz | `PROJECT-DESIGN-CHOICE` (5 kHz Nyquist constraint) |
| Peak transient amplitude | 0.40–1.20 pu | `ENGINEERING-INTERPRETATION` |
| Damping time constant $\tau$ | 2–8 ms | `ENGINEERING-INTERPRETATION` |
| Onset time | 40–120 ms | `PROJECT-DESIGN-CHOICE` |
| Duration (effective) | 3τ to 5τ (6–40 ms) | `ENGINEERING-INTERPRETATION` |
| Sensor noise | 52 dB SNR | `SIMULATION-PARAMETER` |

#### Validation Metrics
- Peak instantaneous voltage > 1.20 pu (Normal peak < 1.10 pu)
- High-pass filtered signal (> 100 Hz) energy concentrated in [300, 1200] Hz band
- Transient duration (amplitude > 10% of peak) ≤ 50 ms (IEEE 1159 low-frequency category)
- No sustained THD elevation (transient is impulsive, not steady-state harmonic)

---

## 5. Sampling Requirements Summary

| Class | Min Required Fs | Project Fs | Adequacy |
|:---|:---:|:---:|:---|
| Normal | 1 kHz | 5 kHz | ✅ Full |
| Sag | 1 kHz | 5 kHz | ✅ Full |
| Swell | 1 kHz | 5 kHz | ✅ Full |
| Interruption | 1 kHz | 5 kHz | ✅ Full |
| Harmonics (H11 = 660 Hz) | 1.5 kHz | 5 kHz | ✅ OSR = 7.6× |
| Flicker ($f_m$ ≤ 15 Hz envelope) | 100 Hz | 5 kHz | ✅ Full |
| Notch (width ≥ 400 μs) | 5 kHz | 5 kHz | ⚠️ Marginal (3–6 samples) |
| Transient (300–1200 Hz) | 2.5 kHz | 5 kHz | ✅ OSR = 2.1–8× |
| Transient (1200–2500 Hz) | 5 kHz | 5 kHz | ⚠️ Near-Nyquist |
| Transient (> 2500 Hz) | > 5 kHz | 5 kHz | ❌ Not representable |

> [!IMPORTANT]
> **Notch and high-frequency transients are the only classes where 5 kHz is marginal or insufficient.** For the current project scope (300–1200 Hz transients, ≥ 400 μs notches), 5 kHz is acceptable with documented limitations.

---

## 6. Normal Contamination Check

Before any disturbance frame enters the dataset, an independent (non-ML) validation must confirm it does NOT resemble the Normal class.

| Class | Contamination Detector | Threshold |
|:---|:---|:---|
| Sag | `windowed_rms_min_pu` | < 0.90 pu |
| Swell | `windowed_rms_max_pu` | > 1.10 pu |
| Interruption | `windowed_rms_min_pu` | < 0.10 pu |
| Harmonics | `thd_percent` | > 3.0% (Normal < 0.09%) |
| Flicker | `envelope_modulation_depth` | > 2.0% |
| Notch | `notch_energy_ratio` | > threshold (to be calibrated) |
| Transient | `peak_instantaneous_pu` | > 1.15 pu |

**Rule:** Any frame that passes the Normal contamination check (i.e., could be mistaken for Normal based on the detector) must be flagged and excluded before entering the training set.

---

## 7. Dataset Leakage Prevention Strategy

**Group-based partition (identical to Normal dataset approach):**

```
Simulation trajectory → Group ID
                      → All frames from this trajectory → same split (train / val / test)

No random splitting of overlapping windows from the same simulation run.
```

**Leakage types addressed:**

| Leakage Type | Prevention |
|:---|:---|
| Temporal leakage (overlapping windows) | Group-by-trajectory, no cross-trajectory splitting |
| Label leakage | Ground truth from scenario_controller only |
| Feature leakage | Features extracted only from the waveform; no future information |
| Model leakage | ML model not used for labeling, only for inference |
| Condition leakage | Operating condition IDs assigned to fixed splits |

---

## 8. Proposed Disturbance Working Model Structure

```
IEEE_9bus_PQD_DISTURBANCES.slx (not yet created)
├── Top-level: Copy of IEEE_9bus_PQD_HIL_R2025a.slx
│
├── PQD_Scenario_Controller (subsystem)
│   ├── Input: scenario_config_file (string path)
│   ├── Outputs: enable_sag, enable_swell, ..., enable_transient (boolean)
│   │            sag_params, swell_params, ... (parameter buses)
│   └── Rule: exactly ONE enable = 1 at runtime
│
├── PQD_Disturbance_Manager (subsystem)
│   ├── Routes PQD_Scenario_Controller outputs to injectors
│   └── Prevents simultaneous multi-injector activation
│
├── PQD_Sag (subsystem, disabled unless enable_sag=1)
│   ├── Input: Bus 4 voltage + fault impedance Z_f
│   └── Implements: Three-phase fault with Z_f between Bus 4 and ground
│
├── PQD_Swell (subsystem, disabled unless enable_swell=1)
│   ├── Input: Bus 7 + load-trip event
│   └── Implements: Load C disconnection step
│
├── PQD_Interruption (subsystem, disabled unless enable_interruption=1)
│   ├── Input: Bus 4–Bus 5 line breaker
│   └── Implements: Three-phase breaker with controlled open/close timing
│
├── PQD_Harmonics (subsystem, disabled unless enable_harmonics=1)
│   ├── Input: Bus 5 load node
│   └── Implements: Multi-component harmonic current source
│
├── PQD_Flicker (subsystem, disabled unless enable_flicker=1)
│   ├── Input: Bus 5 or Bus 6 load
│   └── Implements: Cyclic resistive load switching at f_m
│
├── PQD_Notch (subsystem, disabled unless enable_notch=1)
│   ├── Input: Bus 5 load node
│   └── Implements: 6-pulse thyristor rectifier or controlled switch
│
└── PQD_Transient (subsystem, disabled unless enable_transient=1)
    ├── Input: Bus 5 shunt branch
    └── Implements: Capacitor bank switching with pre-insertion inductor
```

---

## 9. Unresolved Questions

| # | Question | Impact | Resolution Required Before |
|:---:|:---|:---|:---|
| Q1 | What $Z_f$ values produce the exact Bus 5 residual voltage targets for Sag? | Sag parameter calibration | Gate 3D (implementation) |
| Q2 | Does single-phase SLG fault produce sufficient swell magnitude at Bus 5 without impacting Bus 4/7 measurements? | Swell injection location | Gate 3D |
| Q3 | Can the 6-pulse thyristor block in SimPowerSystems be parametrized to independently control notch width and depth? | Notch implementation | Gate 3D |
| Q4 | What is the minimum detectable modulation depth for Flicker at 5 kHz after phase-aware SNR correction? | Flicker feature validity | Gate 3D |
| Q5 | Does the capacitor bank switching model in SimPowerSystems produce reproducible transient frequency for given L, C values? | Transient parameter calibration | Gate 3D |
| Q6 | Label index mapping: Normal is index 3 in production code but index 0 in the proposed taxonomy. Must be reconciled before training. | Label contract | Before dataset merge |
| Q7 | How many frames per class are needed for balanced training? (Normal = 1,120 frames) | Dataset balance | Gate 3D |

---

## Gate 3C Pass Criteria Status

| Criterion | Status |
|:---|:---:|
| 1. Every class has explicit physical definition | ✅ |
| 2. Every class has proposed physical injection mechanism | ✅ |
| 3. Every parameter has provenance | ✅ |
| 4. Standards claims are traceable | ✅ |
| 5. Ground-truth labeling independent of ML | ✅ |
| 6. Scenario selection is modular | ✅ |
| 7. Pristine IEEE 9-bus model remains untouched | ✅ |
| 8. Validation method defined for each class | ✅ |
| 9. Sampling requirements understood | ✅ |
| 10. Dataset leakage strategy defined | ✅ |

```
GATE3C = PASS
```

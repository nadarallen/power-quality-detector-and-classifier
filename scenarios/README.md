# Disturbance Scenario Controller & Ground-Truth Registry

**Subsystem:** Scenarios & Ground-Truth Generation  
**Schema Version:** 1.0 ([docs/GATE3C_SCENARIO_SCHEMA.json](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE3C_SCENARIO_SCHEMA.json))  
**Electrical System:** WSCC 3-Machine 9-Bus System (60 Hz, Simscape Electrical)  
**Observation Point:** Bus 5 ($V_{abc}, I_{abc}$)  

---

## 1. Overview & Ground-Truth Principle

In this repository, **ground-truth class labels originate strictly from physical scenario controller definitions and simulation metadata**, never from ML model predictions. 

Each scenario definition is a declarative JSON file specifying:
1. Exact physical switching mechanism and injection block in `IEEE_9bus_PQD_DISTURBANCES.slx`.
2. Discrete timing parameters (onset instant, duration, point-on-wave angle).
3. Electrical disturbance parameters (fault resistance, capacitor MVAR, harmonic orders, modulation depth, commutation resistance, RLC damping).
4. Standards traceability and independent mathematical validation gates.

---

## 2. Disturbance Class Mapping & Physical Mechanisms

| Class | Label Index | Scenario Definition File | Physical Injection Subsystem | Primary Physical Mechanism | Standards Reference |
|---|:---:|---|---|---|---|
| **Normal** | 0 | `NORM_0001_steady_state_baseline.json` | Steady-state grid load flow | Varied operating conditions (G1–G3 dispatch, load scaling) | IEEE 1159 Cl. 3.1.53 |
| **Voltage Sag** | 1 | `SAG_0001_three_phase_symmetric.json` | `PQD_Fault_Sag` | Shunt fault switching on Bus 4/5 ($R_f \in [0.1, 15.0]\ \Omega$) | IEEE 1159 Cl. 3.1.58 |
| **Voltage Swell** | 2 | `SWELL_0001_three_phase_symmetric.json` | `PQD_Breaker_Swell` | Switched shunt capacitor bank ($50\text{--}150\text{ MVAR}$) | IEEE 1159 Cl. 3.1.58 |
| **Interruption** | 3 | `INT_0001_three_phase_symmetric.json` | `PQD_Breaker_Interruption` | Series circuit breaker opening on Line 4-5 + feeder isolation | IEEE 1159 Cl. 3.1.34 |
| **Harmonics** | 4 | `HAR_0001_h3h5h7_typical.json` | `PQD_Harm_Inj` | Controlled non-linear load current injection ($H_2\text{--}H_{11}$) | IEEE 519-2022 Table 1 |
| **Flicker** | 5 | `FLK_0001_fm10hz_depth5pct.json` | `PQD_Flicker_Mod` | Sub-synchronous dynamic load modulation ($f_m \in [1, 25]\text{ Hz}$) | IEEE 1453-2022 / IEC |
| **Notch** | 6 | `NOT_0001_width600us_depth40pct.json` | `PQD_Notch_Bus5` | Thyristor commutation line-to-line switching ($R_{comm} \in [10, 100]\ \Omega$) | IEEE 1159 Cl. 3.1.48 |
| **Transient** | 7 | `TRAN_0001_three_phase_typical.json` | `PQD_Breaker_Transient` | Switched series RLC branch energization ($300\text{--}2,200\text{ Hz}$) | IEEE 1159 Cl. 3.1.57 |

---

## 3. Parameter Provenance Hierarchy

To maintain scientific integrity, every scenario parameter is tagged with a provenance level:

1. **STANDARD-SUPPORTED:** Parameter directly prescribed by IEEE 1159 / IEEE 519 / IEEE 1453 standards (e.g., sag magnitude $0.10\text{--}0.90\text{ pu}$, swell magnitude $1.10\text{--}1.80\text{ pu}$, interruption $< 0.10\text{ pu}$, harmonics THD $> 5.0\%$).
2. **ENGINEERING-INTERPRETATION:** Practical implementation of standard principles in discrete simulation (e.g., point-on-wave angle selection, half-cycle RMS window aggregation).
3. **PROJECT-DESIGN-CHOICE:** Explicit system design constants (e.g., 200 ms analysis window, 5 kHz discrete sampling rate, 12 fundamental 60-Hz cycles).
4. **SIMULATION-PARAMETER:** Physical electrical circuit parameters in Simscape (e.g., $R_{\text{fault}}$, $C_{\text{bank}}$, $L_{\text{transient}}$, $R_{\text{comm}}$).
5. **DATASET-DESIGN-CHOICE:** Machine learning dataset structuring rules (e.g., 1,152 frames/class, 32 operating conditions, trajectory grouping).

---

## 4. Relationship to Production Datasets

The scenario definitions under `scenarios/definitions/` directly generate the authoritative 8-class physical datasets located in:
```
data/ieee9bus_60hz/
├── normal/        # Normal baseline dataset & metadata
├── sag/           # Voltage Sag dataset & metadata
├── swell/         # Voltage Swell dataset & metadata
├── interruption/  # Voltage Interruption dataset & metadata
├── harmonics/     # Harmonics dataset & metadata
├── flicker/       # Voltage Flicker dataset & metadata
├── notch/         # Voltage Notch dataset & metadata
└── transient/     # Oscillatory Transient dataset & metadata
```

All 8 datasets are generated with **zero inter-trajectory leakage** and verified by independent rule-based validators in `pipeline/disturbance_validator.py`.

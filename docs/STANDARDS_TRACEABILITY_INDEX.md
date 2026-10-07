# Standards Traceability Index & Provenance Taxonomy

**Document Reference**: `docs/STANDARDS_TRACEABILITY_INDEX.md`  
**Date**: October 7, 2026  
**Status**: ACTIVE / CONSOLIDATED  
**Referenced Standards**: IEEE Std 1159-2019, IEEE Std 519-2022, IEEE Std 1453-2022, IEC 61000-4-30 Class A, ANSI C84.1  

---

## 1. Provenance Taxonomy Definition

To maintain rigorous scientific clarity and prevent unsupportable claims, every metric, threshold, and operational parameter in this project is explicitly classified under one of five provenance categories:

| Category | Definition | Authority |
|:---|:---|:---|
| **STANDARD-SUPPORTED** | Direct mathematical, physical, or categorical definition explicitly specified in an internationally recognized power engineering standard. | IEEE / IEC / ANSI published standard clause |
| **ENGINEERING-INTERPRETATION** | Application of a standard measurement concept to a specific electrical topology or finite-duration discrete observation window. | Power engineering physical derivation |
| **PROJECT-DESIGN-CHOICE** | Deliberate system architecture selection made to balance computational efficiency, embedded feasibility, and machine learning representation. | Project engineering architecture |
| **SIMULATION-PARAMETER** | Numerical configuration of numerical solvers, snubber impedances, breaker resistances, or generator dispatch setpoints in SimPowerSystems. | Numerical simulation fidelity |
| **DATASET-DESIGN-CHOICE** | Target parameter ranges, sampling intervals, frame counts, and train/val/test splits established for machine learning diversity and anti-leakage. | Machine learning experimental design |

---

## 2. Standards Cross-Reference Matrix

### 2.1 Voltage Sag (Class 1)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| Sag definition | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Clause 3.1.58 | Residual RMS $0.10\text{--}0.90\,\text{pu}$ | True physical voltage reduction |
| Sag duration band | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | $0.5$ cycle to $1\,\text{min}$ | Project spans $16.7\text{--}120.0\,\text{ms}$ ($1\text{--}7.2$ cycles) |
| Half-cycle RMS tracking | **STANDARD-SUPPORTED** | IEC 61000-4-30 Clause 5.2 | Sliding $8.33\,\text{ms}$ window | Calculated on $41\text{--}42$ samples at $5\,\text{kHz}$ |
| Shunt fault simulation | **SIMULATION-PARAMETER** | Simscape Electrical | $R_f \in [0.1, 15.0]\,\Omega$ | Grounded and ungrounded fault impedances |
| Minimum frame duration | **PROJECT-DESIGN-CHOICE** | Project DAQ Spec | $200.0\,\text{ms}$ ($12$ cycles) | Standard 1000-sample observation window |

### 2.2 Voltage Swell (Class 2)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| Swell definition | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Clause 3.1.66 | RMS magnitude $1.10\text{--}1.80\,\text{pu}$ | Instantaneous voltage elevation |
| Swell duration band | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | $0.5$ cycle to $1\,\text{min}$ | Evaluated across $16.7\text{--}120.0\,\text{ms}$ |
| Shunt capacitor switching | **SIMULATION-PARAMETER** | Simscape Electrical | $Q_C \in [50, 150]\,\text{MVAR}$ | Three-phase reactive power injection |
| Anti-Sag / Anti-Interruption | **ENGINEERING-INTERPRETATION** | IEEE Std 1159-2019 Table 2 | Min RMS $\ge 0.90\,\text{pu}$ | Disqualifies sag or interruption states |

### 2.3 Voltage Interruption (Class 3)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---|:---:|
| Interruption definition | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Clause 3.1.34 | Residual voltage $< 0.10\,\text{pu}$ | Complete supply collapse |
| Interruption threshold | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | Residual voltage $< 0.10\,\text{pu}$ | Measured $[0.000, 0.082]\,\text{pu}$ |
| Non-zero residual trapped charge | **ENGINEERING-INTERPRETATION** | Simscape Physical Physics | Residual $> 0.0\,\text{pu}$ | Snubber and transformer decay |
| Series line breaker topology | **SIMULATION-PARAMETER** | Simscape Electrical | Line 4-5 series breaker | Isolates Bus 5 from generation |

### 2.4 Harmonics (Class 4)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| THD definition | **STANDARD-SUPPORTED** | IEEE Std 519-2022 Clause 3.1 | $\text{THD} = \frac{\sqrt{\sum V_h^2}}{V_1} \times 100\%$ | Calculated on orders $H_2\text{--}H_{11}$ |
| Point of Common Coupling (PCC) | **STANDARD-SUPPORTED** | IEEE Std 519-2022 Clause 5.1 | Bus 5 ($230\,\text{kV}$) | Transmission measurement interface |
| Goertzel harmonic binning | **PROJECT-DESIGN-CHOICE** | Project DSP Spec | Single-bin DFT @ $60 k\,\text{Hz}$ | Efficient embedded spectral evaluation |
| Non-linear injection orders | **DATASET-DESIGN-CHOICE** | Project Scenario Design | $H_2, H_3, H_5, H_7, H_9, H_{11}$ | Covers characteristic rectifier harmonics |

### 2.5 Voltage Flicker (Class 5)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| Envelope modulation concept | **STANDARD-SUPPORTED** | IEEE Std 1453-2022 Clause 3.1 | $V(t) = V_0 [1 + m \cos(\omega_m t)] \sin(\omega_0 t)$ | Amplitude modulation waveform |
| Modulation frequency range | **ENGINEERING-INTERPRETATION** | IEEE Std 1453-2022 Table 1 | $f_m \in [1.0, 25.0]\,\text{Hz}$ | Encompasses human eye maximum sensitivity ($8.8\,\text{Hz}$) |
| Modulation depth range | **DATASET-DESIGN-CHOICE** | Project Scenario Design | $\Delta V / V \in [1.0\%, 10.0\%]$ | Resolvable within single 200-ms frame |
| Short-term flicker perceptibility ($P_{st}$) | **STANDARD-SUPPORTED** | IEC 61000-4-15 | **EXCLUDED** from 200-ms frame | Requires 10-minute continuous statistical integration |

### 2.6 Voltage Notch (Class 6)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| Commutation notch definition | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Clause 4.4.4.2 | Sub-cycle periodic dip ($< 0.5$ cycle) | Converter commutation overlap |
| Commutation notch depth limit | **STANDARD-SUPPORTED** | IEEE Std 519-2022 Table 2 | Depth $20\%\text{--}80\%$ at PCC | Measured $22.9\%\text{--}53.8\%$ |
| Minimum notch width observability | **PROJECT-DESIGN-CHOICE** | Project Sampling Spec | Width $\ge 0.40\,\text{ms}$ ($\ge 2$ samples @ 5 kHz) | Guarantees discrete Shannon-Nyquist resolvability |
| Line-to-line bridge switching | **SIMULATION-PARAMETER** | Simscape Electrical | $R_{\text{comm}} \in [10, 100]\,\Omega$ | Finite commutation resistance |

### 2.7 Oscillatory Transient (Class 7)
| Claim / Metric | Provenance Category | Standard & Clause | Value in Project | Traceability & Scope Boundary |
|:---|:---:|:---|:---:|:---|
| Low-frequency oscillatory transient | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | Frequency $< 5\,\text{kHz}$, duration $0.3\text{--}50\,\text{ms}$ | Capacitor energization transient |
| Typical capacitor switching frequency | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | $300\text{--}900\,\text{Hz}$ nominal | Measured dominant: $250.2\text{--}299.1\,\text{Hz}$ |
| Peak voltage excursion | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | $1.1\text{--}2.0\,\text{pu}$ peak magnitude | Measured instantaneous: $1.00\text{--}1.25\,\text{pu}$ |
| Nyquist frequency limit | **PROJECT-DESIGN-CHOICE** | Shannon-Nyquist Theorem | $F_{\text{Nyquist}} = 2500\,\text{Hz}$ | Transient representation bounded below $1500\,\text{Hz}$ |
| High-frequency / impulsive transients | **STANDARD-SUPPORTED** | IEEE Std 1159-2019 Table 2 | **EXCLUDED** from 5 kHz DAQ | Frequencies $> 2.5\,\text{kHz}$ cannot be represented |

---

## 3. Critical Architectural Boundaries & Scope Clarifications

1. **ML Classification Thresholds vs Utility Compliance Limits**:
   - The boundaries established in [`pipeline/disturbance_validator.py`](file:///d:/my%20study/Project/power-quality-detector-and-classifier/pipeline/disturbance_validator.py) (e.g. $10\%$ sag depth threshold, $5\%$ flicker modulation) are **dataset synthesis and pattern classification bounds**, not utility grid penalty limits.
2. **200-ms Window vs Long-Term Power Quality Metrics**:
   - A single 200-ms observation window ($12$ cycles) provides instantaneous point-on-wave classification. It does not replace 10-minute IEC 61000-4-30 $P_{st}$ flicker indices or 7-day IEEE 519 harmonic compliance surveys.
3. **5-kHz Sampling Bandwidth Limitation**:
   - At $F_s = 5000\,\text{Hz}$, the discrete Nyquist bandwidth is strictly $2500\,\text{Hz}$. Lightning surges, sub-microsecond impulsive transients, and ultra-high-frequency arc transients are **physically outside the representation capacity** of this system and are explicitly excluded from claims.

# Real Hardware Validation Protocol & Empirical Status

This document defines the validation protocol for physical three-phase electrical measurements and establishes the clear boundary between synthetic research benchmarks and real-world validation.

---

## 1. Current Empirical Validation Status

| Milestone Dimension | Current Status | Description / Evidence |
|---|---|---|
| **Synthetic Dataset Benchmark** | **COMPLETED & LOCKED** | 10,000 samples (`Dataset/BARC DATA.csv`), 70/15/15 stratified train/val/test splits (`data/splits/`), 99.40% test accuracy on EXP-003 Compact MLP. |
| **Firmware Native Parity** | **COMPLETED & TESTED** | C++ Goertzel and `model_weights_32.h` forward pass verified at machine precision ($< 1\times 10^{-4}$ error) against Python in `tests/test_firmware_parity.py`. |
| **Continuous Ring Buffer Pipeline** | **COMPLETED & TESTED** | 1000-sample sliding windows with 50% overlap, multi-window event deduplication, and cross-phase event correlation verified across 105 unit/integration tests. |
| **Hardware-Agnostic Acquisition Interface** | **COMPLETED & TESTED** | `HardwareAdapter` family, `ThreePhaseCalibration` (raw counts $\to$ Volts $\to$ pu), rail saturation detection, and canonical dual `.json`/`.npz` capture format implemented and verified. |
| **Actual Physical Electrical Measurement** | **NOT PERFORMED** | **Reason**: Waiting for physical acquisition hardware and certified isolated potential transformer (PT) front-end selection before wiring to live conductors. |

> [!IMPORTANT]
> **NO LIVE MAINS CLAIMS**  
> The repository makes **ZERO CLAIMS** of real-world physical electrical validation. The system is classified as **Hardware-Agnostic & Acquisition-Ready**.

---

## 2. Real-World Physical Validation Procedure (Phase 6 Protocol)

Once an isolated measurement device is connected, the following two-stage physical validation procedure must be executed:

### Stage 1: Steady-State Normal Grid Verification
1. Connect 3 isolated potential transformers (PTs) to a known 3-phase low-voltage laboratory distribution bus (e.g. 110 V or 230 V L-N).
2. Configure `ChannelCalibration` with:
   - Measured turns ratio ($K_{\text{sensor}}$)
   - Zero-offset trim ($V_{\text{offset}}$)
   - ADC full-scale reference ($V_{\text{ref}}$)
   - Nominal base RMS voltage ($V_{\text{nominal\_rms}}$)
3. Stream continuous frames into the acquisition pipeline at $5000\text{ Hz}$.
4. Verify:
   - $V_{\text{RMS}}$ on `L1`, `L2`, `L3` resides within $[0.95, 1.05]\text{ pu}$.
   - Grid fundamental frequency resides within $[49.5, 50.5]\text{ Hz}$ (or $[59.5, 60.5]\text{ Hz}$).
   - Total Harmonic Distortion ($\text{THD}_{2\_11}$) is $< 2.0\%$.
   - Compact MLP outputs `Normal` classification with confidence $\ge 0.95$.
   - Event engine generates zero false disturbance triggers.

### Stage 2: Controlled Disturbance Verification
1. Using a programmable AC power source or autotransformer in a certified electrical laboratory:
   - Step Phase B (`L2`) voltage down to $0.70\text{ pu}$ for $200\text{ ms}$ (IEEE 1159 Voltage Sag).
   - Inject known 3rd and 5th harmonic distortion ($10\% H_3, 5\% H_5$).
2. Ingest continuous waveform stream through `HardwareAdapter`.
3. Verify:
   - Pipeline detects disturbance onset without human intervention.
   - `ThreePhaseEventEngine` identifies `affected_phases = ['L2']`.
   - Disturbance is classified as `Voltage Sag` with high confidence ($\ge 0.90$).
   - Captured raw traces are serialized to canonical `.npz` storage for regression testing.

---

## 3. Real Validation Dataset Governance

To prevent data contamination and invalid benchmark claims:
1. **Strict Dataset Separation**: Real captured waveforms must be saved in `data/real_captures/` and **NEVER** merged into `data/splits/` or the training distribution.
2. **Provenance Tracking**: Every capture file must preserve complete metadata:
   - Timestamp (UTC ISO 8601)
   - Hardware model and serial number
   - Applied calibration profile ID and scale factors
   - Measured ambient laboratory conditions
   - True ground-truth electrical event label
3. **Separate Reporting**: Benchmark reports must publish synthetic test accuracy and real-world validation accuracy as separate independent metrics.

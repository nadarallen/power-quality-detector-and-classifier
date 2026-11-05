# IEEE 9-Bus Power Quality Detector and Classifier
## Academic & Technical Presentation Guide

---

## 1. Quick Start — One-Command Launch

On any Windows 11 system with Python and MATLAB:

```cmd
Start-Presentation.cmd
```

This single command automatically:
1. Validates Python environment and dependencies via `presentation/presentation_preflight.py`.
2. Verifies cryptographic hashes for the Phase 4C MLP weights and standard scaler.
3. Confirms integrity of the protected reference model `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`.
4. Starts the lightweight multithreaded backend server on `http://127.0.0.1:8500`.
5. Verifies TCP streamer port `8502` for high-speed MATLAB telemetry.
6. Launches the web dashboard in your default browser.
7. Prompts to start either **Mode A (Fast 5s Scenario)** or **Mode B (Continuous Interactive SIL)**.

To stop the presentation at any time:
```cmd
Stop-Presentation.cmd
```

---

## 2. Presentation Modes Explained

### Mode A — Fast Scenario Demonstration (5 Seconds)
- **Use Case:** Concise, repeatable live demonstration of specific fault scenarios.
- **Duration:** Fixed 5.0 seconds simulated time.
- **Workflow:** Runs Simulink solver with scheduled fault injection at $t = 1.0\text{ s}$ to $t = 1.2\text{ s}$, streaming 5 kHz waveforms to the dashboard and auto-stopping.
- **Best For:** Review committees and quick verification of individual classes.

### Mode B — Continuous Interactive Demonstration (SIL)
- **Use Case:** Full interactive exhibition with real-time on-the-fly injection.
- **Duration:** Continuous real-time execution ($StopTime = \infty$, Pacing = 1.0 s/s).
- **Workflow:** The Level-2 S-Function streamer acquires Bus 5 voltage and line current at 5 kHz, buffering 250-sample chunks (50 ms) to an in-memory FIFO and pushing via TCP. The user can inject Sags, Swells, Harmonics, Flicker, Notches, and Transients live and witness instantaneous physical changes and independent ML classification.
- **Recovery:** Click **Reset to Normal** to restore balanced 60 Hz sinusoidal steady state without restarting MATLAB.

---

## 3. Approved Live Demonstration Sequence

During your presentation, follow this calibrated sequence for flawless demonstration:

| Step | Action | UI Control | Physical Observation | Independent ML Output |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Normal Baseline** | System Initial State | Balanced 3-phase voltages ($0.589\text{ pu}$ raw / $1.02\text{ pu}$ IEEE), $60.0\text{ Hz}$, $\text{THD} < 0.1\%$ | **Normal** ($100.0\%$, Domain: VALID) |
| **2** | **Voltage Sag** | Select `SAG`, click `[INJECT]` | Bus 5 RMS voltage drops to $\approx 0.41\text{ pu}$ for 3.0 s | **Sag** ($> 99\%$, Domain: VALID) |
| **3** | **Recovery** | Click `RESET TO NORMAL` | Fault de-energized; voltage rebounds smoothly to $1.02\text{ pu}$ | **Normal** ($100.0\%$, Domain: VALID) |
| **4** | **Voltage Swell** | Select `SWELL`, click `[INJECT]` | 150 MVAr capacitor bank energizes; voltage surges to $\approx 1.25\text{ pu}$ | **Swell** ($> 99\%$, Domain: VALID) |
| **5** | **Recovery** | Click `RESET TO NORMAL` | Shunt capacitor breaker trips; voltage recovers nominal baseline | **Normal** ($100.0\%$, Domain: VALID) |
| **6** | **Harmonics** | Select `HARMONICS`, click `[INJECT]` | Nonlinear distortion (H3, H5, H7); $\text{THD} > 15\%$ on FFT | **Harmonics** ($> 95\%$, Domain: VALID) |
| **7** | **Flicker** | Select `FLICKER`, click `[INJECT]` | Low-frequency 8 Hz amplitude envelope modulation | **Flicker** ($> 95\%$, Domain: VALID) |
| **8** | **Notch** | Select `NOTCH`, click `[INJECT]` | Periodic thyristor commutation notches appear per half-cycle | **Notch** ($> 95\%$, Domain: VALID) |
| **9** | **Transient** | Select `TRANSIENT`, click `[INJECT]` | High-frequency oscillatory voltage spike ($> 1\text{ kHz}$) | **Transient** ($> 90\%$, Domain: VALID) |

---

## 4. Key Architectural Highlights to Present

1. **Decoupled 3-Way Assessment:**
   Explain that the system strictly decouples:
   - **Commanded Injection:** User request.
   - **Measured Physical Metrics:** IEEE Std 1159 voltage/current physical assessment.
   - **Independent Machine Learning:** Pure 32-feature Phase 4C MLP classification. The ML output is never forced or hardcoded to match the button.

2. **Event-Aware Adaptive Windowing:**
   Explain why naive fixed sliding windows misclassify short events as Notches due to boundary step discontinuities, and how the event-aware windowing isolates active disturbance epochs.

3. **Honest Out-of-Distribution (OOD) Protection:**
   Show the Mahalanobis distance boundary ($D_M \le 12.01$) and how the model reports `OUT_OF_DISTRIBUTION` or `INSUFFICIENT_WINDOW` instead of hallucinating when given invalid inputs.

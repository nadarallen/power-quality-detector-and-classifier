# Presentation Setup & Quick-Start Guide
## IEEE 9-Bus Power Quality Detector and Classifier

This guide provides instructions to verify, start, and demonstrate the IEEE 9-bus Power Quality Classification platform on Windows 11.

---

## 1. Quick Start (One Command)

From the project root directory:

```cmd
Start-Presentation.cmd
```

This single command performs the complete startup sequence:
1. Runs `presentation/presentation_preflight.py` to verify Python version, required packages, and file hashes.
2. Checks model integrity for `candidate_mlp_weights.json` and `scaler_phase4c_params.json`.
3. Verifies protected reference model `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`.
4. Starts the multithreaded backend server on `http://127.0.0.1:8500`.
5. Opens the dashboard in your default browser.
6. Prompts you to select your presentation demonstration mode:
   - **Mode A:** Fast 5-Second Scheduled Scenario Demonstration
   - **Mode B:** Continuous Interactive 1:1 Real-Time SIL Demonstration
   - **Mode C:** Dashboard Only / Manual Exploration

To stop the presentation environment at any time:
```cmd
Stop-Presentation.cmd
```

---

## 2. Environment Prerequisites

- **Operating System:** Windows 11 (or Windows 10 64-bit)
- **Python:** 3.10, 3.11, 3.12, or 3.14 (Verified on Python 3.14.2)
- **MATLAB:** R2025a (or R2024b / R2024a)
- **Required MATLAB Toolboxes:**
  - Simulink
  - Simscape
  - Simscape Electrical
- **Network Ports:**
  - Port `8500`: Python REST & SSE Backend
  - Port `8502`: TCP Streamer Port (Level-2 S-Function to Python)

---

## 3. Manual Startup & Recovery Procedure

If the one-command launcher is blocked by system policy, start the services manually:

### Step 1: Preflight Verification
```powershell
python presentation/presentation_preflight.py
```
Ensure all items return `[  OK  ]`.

### Step 2: Start Backend Server
```powershell
python server.py 8500
```
Verify the server responds:
```powershell
curl http://127.0.0.1:8500/api/health
```

### Step 3: Launch Live Simulink Session (Mode B)
In MATLAB:
```matlab
cd 'd:\my study\Project\power-quality-detector-and-classifier'
addpath(genpath('.'));
run_continuous_simulation('presentation/presentation_config.json');
```

### Step 4: Open the Dashboard
Open your browser and navigate to:
```text
http://127.0.0.1:8500
```

---

## 4. Live Demonstration Workflow

1. **Overview Page:** Walk through project objectives, IEEE 9-bus topology, and 8 IEEE Std 1159 disturbance classes.
2. **Live Simulink Page:**
   - Observe balanced 3-phase waveforms on the Voltage Oscilloscope ($0.589\text{ pu}$ raw / $1.02\text{ pu}$ IEEE) and Current Oscilloscope ($174\text{ A}$ / $0.69\text{ pu}$).
   - Verify FFT fundamental spectrum at $60.00\text{ Hz}$ with $\text{THD} < 0.1\%$.
   - Point out the three decoupled indicators: Commanded Disturbance (`Normal`), Physical Assessment (`Normal`), and Independent ML Prediction (`Normal`, $100.0\%$, Domain: `VALID_CLASSIFICATION`).
3. **Disturbance Lab:**
   - Inject **Voltage Sag** ($R_f = 2.0\,\Omega$, duration $3.0\text{ s}$). Observe voltage drop to $0.41\text{ pu}$ and real-time ML detection.
   - Click **Reset to Normal** to restore balanced sinusoidal state.
   - Inject **Voltage Swell** ($Q_c = 150\text{ MVAr}$). Observe voltage surge to $1.25\text{ pu}$ and ML Swell detection.
   - Inject **Harmonics** (H3, H5, H7). Inspect harmonic orders on the FFT Spectrum.
   - Inject **Flicker**, **Notch**, and **Transient** to demonstrate full 8-class coverage.
4. **Model Diagnostics:**
   - Review frozen SHA-256 hashes for model weights and scaler.
   - Inspect the 32-feature extraction table and Mahalanobis distance domain boundary ($D_M \le 12.01$).

---

## 5. Troubleshooting & Diagnostics

- **Port Conflict (8500 or 8502 in use):**
  Run `scripts/stop_presentation.ps1` to terminate lingering processes.
- **Waveforms not updating:**
  Verify MATLAB is streaming by querying:
  `http://127.0.0.1:8500/api/live/simulation/status`
- **Protected Model Verification Error:**
  If `IEEE_9bus_PQD_HIL_R2025a.slx` hash differs from `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`, restore it from git:
  `git checkout IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`

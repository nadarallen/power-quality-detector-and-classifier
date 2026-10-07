# Project Quickstart & Execution Guide

**Project Title:** AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation  
**Current Status:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Frequency:** 60 Hz  
**Authoritative Sampling Rate:** 5,000 Hz ($T_s = 200\ \mu\text{s}$, $N = 1,000$ samples per 200 ms frame)  

---

## 1. Environment Setup

### 1.1 Python Environment
Requires Python 3.10+ (tested on Python 3.10, 3.12, 3.14).

```bash
# Clone repository and navigate to root
cd power-quality-detector-and-classifier

# Install dependencies
pip install numpy scipy pandas scikit-learn pytest requests
```

### 1.2 MATLAB / Simulink Environment (Optional for Simulation)
- **Version:** MATLAB R2024b or R2025a
- **Toolboxes:** Simulink, Simscape Electrical (Specialized Power Systems)
- **Note:** All pre-generated datasets under `data/ieee9bus_60hz/` are bundled directly in the repository; MATLAB is only required for re-running physical simulations or generating new grid scenarios.

---

## 2. Verified Active Workflows

### Workflow 1: Run the Complete Automated Test Suite

Verify all DSP algorithms, SNR phase invariance, physical disturbance validators, and streaming adapters:

```bash
pytest -v
```

**Expected Result:**
```
================= 300 passed, 2 skipped, 2 warnings in 7.80s ==================
```
*(2 skipped tests correspond to GPU/CUDA acceleration checks on CPU-only machines).*

---

### Workflow 2: Launch the REST Server & Laboratory Oscilloscope UI

Start the lightweight REST & Server-Sent Events (SSE) telemetry server:

```bash
python server.py
```

Then open your web browser to:
```
http://localhost:8500
```

**Features available on the dashboard:**
- **CRT Oscilloscope:** Real-time canvas rendering of 3-phase Bus 5 voltages ($L_1, L_2, L_3$).
- **FFT Spectrum Analyzer:** Real-time harmonic spectrum (H1–H11).
- **32-Feature Parameter Matrix:** Instantaneous DSP metric values.
- **Physical Event Logger:** Live logging of detected disturbances with timestamps and RMS nadirs.

---

### Workflow 3: Run Simulink-to-Python Ingestion Bridge (Simulation Mode)

In MATLAB:
```matlab
% Add integration path
addpath('integration/matlab');

% Run automated simulation and stream chunks to http://localhost:8500
send_simulink_pqd_auto('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx');
```

The MATLAB script will:
1. Execute the 60-Hz IEEE 9-bus simulation.
2. Capture continuous three-phase voltages at Bus 5.
3. Resample to 5,000 Hz.
4. Stream 50 ms chunks via HTTP POST to `/api/simulink/ingest_chunk`.
5. Display live waveform oscillations in the web dashboard.

---

### Workflow 4: Inspect Audited 60-Hz Disturbance Datasets

All 8 audited disturbance classes are organized under `data/ieee9bus_60hz/`:

```python
import numpy as np
import pandas as pd

# Load Sag features
sag_features = pd.read_csv("data/ieee9bus_60hz/sag/sag_features.csv")
print(f"Sag dataset shape: {sag_features.shape}") # (1152, 33)

# Load raw Sag waveforms
sag_waveforms = np.load("data/ieee9bus_60hz/sag/sag_waveforms.npz")
print(f"Sag waveform tensor: {sag_waveforms['V'].shape}") # (1152, 1000, 3)
```

---

### Workflow 5: Run Production 32-Feature DSP on Custom Signals

```python
import numpy as np
from dsp.enhanced_features import extract_32_features

# Generate 200 ms 60-Hz test signal at 5 kHz (1,000 samples)
t = np.linspace(0, 0.200, 1000, endpoint=False)
v_test = np.sin(2 * np.pi * 60.0 * t) + 0.05 * np.sin(2 * np.pi * 300.0 * t)

# Extract authoritative 32-feature vector
features = extract_32_features(v_test, sampling_rate_hz=5000.0, nominal_frequency_hz=60.0)

print(f"RMS Voltage: {features['rms_voltage']:.4f} pu")
print(f"Total Harmonic Distortion (THD): {features['thd']:.2f}%")
print(f"Orthogonal Projection SNR: {features['snr_db']:.2f} dB")
```

---

## 3. Future & Planned Workflows (Post-Phase 3)

The following workflows represent planned future engineering phases:

### Phase 4 (Next): 60-Hz Machine Learning Retraining
- **Objective:** Train 60-Hz MLP, Random Forest, and XGBoost classifiers on the audited 8-class physical datasets using trajectory-grouped cross-validation.
- **Protocol:** Specified in [docs/ML_READINESS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ML_READINESS.md).
- **Status:** PENDING (Do not retrain during Phase 3 maintenance).

### Phase 5 (Future): Live Demonstration MVP
- **Objective:** Interactive disturbance triggering via MATLAB API (`pqd.sag(...)`, `pqd.reset()`) and Simulink dashboard controls during continuous live simulation.
- **Specification:** Detailed in [docs/LIVE_MVP_PLAN.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/LIVE_MVP_PLAN.md).
- **Status:** PENDING.

### Phase 6 (Optional Extension): Embedded ESP32 Hardware-in-the-Loop
- **Objective:** Microcontroller ADC acquisition and on-device inference using TFLite-Micro on ESP32 hardware.
- **Codebase:** Preserved in `firmware/` and `hardware/` with automated firmware parity tests in `tests/test_firmware_parity.py`.
- **Status:** OPTIONAL FUTURE EXTENSION.

---

## 4. Documentation Index

For in-depth technical specifications, consult the master documentation:

- [Documentation Index](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/README.md)
- [Master Project Status](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/PROJECT_STATUS.md)
- [Source of Truth Registry](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/SOURCE_OF_TRUTH.md)
- [Multi-Phase Roadmap](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ROADMAP.md)
- [System Architecture](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ARCHITECTURE.md)
- [Dataset Specification](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/DATASET.md)
- [Gate Registry (Gates 1–3X)](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/GATE_INDEX.md)
- [Full Reproducibility Guide](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/REPRODUCIBILITY.md)

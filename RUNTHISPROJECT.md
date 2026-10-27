# Project Quickstart & Execution Guide

**Project Title:** AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning with IEEE 9-Bus Simulation  
**Current Status:** Phase 5 Complete (Multi-Model Comparative Research Study & Dashboard)  
**Authoritative Frequency:** 60 Hz  
**Authoritative Sampling Rate:** Dual-Rate: 20,000 Hz (Waveform Deep Learning) & 5,000 Hz ($T_s = 200\ \mu\text{s}$, $N = 1,000$, 32-Feature DSP Contract)  

---

## 1. Environment Setup

### 1.1 Python Environment
Requires Python 3.10+ (tested on Python 3.10, 3.12, 3.14).

```bash
# Clone repository and navigate to root
cd power-quality-detector-and-classifier

# Install dependencies
pip install numpy scipy pandas scikit-learn pytest requests jsonschema matplotlib
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
================= 358 passed, 2 skipped, 2 warnings in 11.61s ==================
```
*(2 skipped tests correspond to GPU/CUDA acceleration checks on CPU-only machines).*

---

### Workflow 2: Launch the Interactive Research Dashboard

Launch the Streamlit research platform to explore frozen IEEE 9-bus recorded experiments, view 3-phase waveforms, inspect 32-feature extractions, evaluate models, and view audit evidence:

```bash
streamlit run app.py
```

Then open your web browser to:
```
http://localhost:8501
```

**Features available on the research dashboard:**
- **Tab 1: Dataset Explorer & Dual-Rate Waveforms:** Compare 5 kHz canonical and 20 kHz high-resolution three-phase waveforms from the verified Phase 5C dataset, view harmonic FFT spectra, and inspect electrical metadata.
- **Tab 2: Multi-Model Benchmark Comparison:** Compare validation and challenge metrics (Accuracy, Macro F1, Recall, Confusion Matrices) side-by-side across Classical ML, 1D-CNN, TCN, and HybridPQNet.
- **Tab 3: Feature Analysis & Explainability:** Interactive 32-feature parameter table, permutation feature importances, functional group ablations, and SHAP attribution plots.
- **Tab 4: Waveform Model Interpretation:** Temporal occlusion sensitivity curves ($t \in [40, 80]\text{ ms}$ onset impact), three-phase vs. single-phase synchrony ablation (-86.25% collapse on single phase), and sampling rate sensitivity.
- **Tab 5: Quarantined Challenge Evaluation & Provenance:** Audit trail on held-out Conditions 33–36 with zero-leakage verification.
- **Operational Modes:**
  - *Mode A (Recorded Experiment Explorer):* Fully functional standalone without MATLAB or Simulink.
  - *Mode B (Simulink Live Experiment Runner):* Optional execution hooks requiring local MATLAB R2024b/R2025a and Simscape Electrical (unverified in headless CI).

---

### Workflow 3: Launch the REST Server & Laboratory Oscilloscope UI

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

### Workflow 4: Run Simulink-to-Python Ingestion Bridge (Simulation Mode)

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

## 3. Engineering Phases & Future Workflows

### Phase 4 (Completed): 60-Hz Machine Learning Training & Evaluation
- **Objective:** Trajectory-grouped dataset splitting, train-only scaler fitting, 5-baseline classifier benchmarking, hyperparameter tuning, and independent evaluation on locked test partition (99.92% accuracy, 99.93% macro F1).
- **Reproduction Guide:** Specified in [docs/REPRODUCING_PHASE4.md](docs/REPRODUCING_PHASE4.md).
- **Integrity Audit:** Reconciled in [docs/ARTIFACT_INTEGRITY_RECONCILIATION.md](docs/ARTIFACT_INTEGRITY_RECONCILIATION.md).
- **Status:** **COMPLETE (Gates 4A–4D Passed)**.

### Phase 5 (Completed): Multi-Model Comparative Research Study & Dashboard
- **Objective:** Comparative research study evaluating Classical ML (32 features), Raw-Waveform Deep Learning (1D-CNN, TCN), and Hybrid Representations (HybridPQNet) on IEEE 9-bus dual-rate waveforms (20 kHz & 5 kHz) across 144 core trajectories (4,608 frames).
- **Findings:** HybridPQNet achieved 100.00% Macro F1 on quarantined challenge conditions (+11.08% over features alone, +9.13% over waveform alone). Three-phase synchrony confirmed essential (-86.25% collapse on single phase).
- **Monograph:** Detailed in [docs/PHASE5_FINAL_RESEARCH_REPORT.md](docs/PHASE5_FINAL_RESEARCH_REPORT.md).
- **Status:** **COMPLETE**.

### Phase 6 (Planned / Future Scope — Not Yet Implemented): Embedded Hardware-in-the-Loop
- **Objective:** Microcontroller ADC acquisition, isolated analog front-end, and on-device inference using TFLite-Micro on physical hardware.
- **Status:** **PLANNED / FUTURE SCOPE — NOT YET IMPLEMENTED** (No firmware deployment or live electrical grid connection has been implemented or authorized).

---

## 4. Documentation Index

For in-depth technical specifications, consult the master documentation:

- [Documentation Index](docs/README.md)
- [MATLAB Sag & Swell Visualization Guide](docs/guides/MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md)
- [Markdown Documentation Audit Report](docs/audits/MARKDOWN_DOCUMENTATION_AUDIT.md)
- [Phase 5 Master Research Report](docs/PHASE5_FINAL_RESEARCH_REPORT.md)
- [Phase 5C Dataset Freeze Audit](docs/PHASE5C_EXPANDED_DATASET_FREEZE_AUDIT.md)
- [Phase 5D Classical ML & Feature Analysis](docs/PHASE5D_CLASSICAL_ML_AND_FEATURE_ANALYSIS.md)
- [Phase 5E Waveform Deep Learning Report](docs/PHASE5E_WAVEFORM_DEEP_LEARNING.md)
- [Phase 5F Hybrid Model Analysis](docs/PHASE5F_HYBRID_MODEL_ANALYSIS.md)
- [Phase 5G One-Time Challenge Evaluation](docs/PHASE5G_FINAL_COMPARATIVE_EVALUATION.md)
- [Master Project Status](docs/PROJECT_STATUS.md)
- [Multi-Phase Roadmap](docs/ROADMAP.md)
- [Reproducing Phase 4 on a Clean Clone](docs/REPRODUCING_PHASE4.md)
- [Full Reproducibility Guide](docs/REPRODUCIBILITY.md)

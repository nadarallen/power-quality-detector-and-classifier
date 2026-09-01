# ⚡ How to Run This Project

**AI-Based Real-Time Power Quality Disturbance Classification Using Machine Learning**

---

## 📋 Prerequisites

| Requirement | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | ML training, server, diagnostics |
| **uv** *(recommended)* or pip | latest | Python package manager |
| **Git** | any | Clone/version control |
| **Node.js** | 18+ | *(Optional)* Only needed for mobile app |
| **PlatformIO CLI** | latest | *(Optional)* Only for ESP32 firmware flashing |
| **Modern Browser** | Chrome / Firefox / Edge | Dashboard UI |

---

## 🚀 Mode 1 — Simulation Dashboard (No Hardware Required)

This is the primary demo mode. The dashboard runs a fully client-side Keras MLP inference engine in the browser using exported weights, simulating real waveforms and performing live ML classification.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/nadarallen/power-quality-detector-and-classifier.git
cd power-quality-detector-and-classifier
```

### Step 2 — Start the Python Server

**Option A: Using `uv` (recommended — auto-installs dependencies)**

```bash
uv run --python 3.12 --with numpy python server.py 8500
```

**Option B: Using standard pip**

```bash
pip install numpy
python server.py 8500
```

You should see:

```
========================================================
  PQD RETRO LABORATORY SERVER ONLINE AT: http://localhost:8500
========================================================
```

### Step 3 — Open the Dashboard

Open your browser and navigate to:

```
http://localhost:8500
```

### Step 4 — Inject a Disturbance & Run ML Pipeline

1. Select a disturbance from the **DISTURBANCE INJECTOR** panel (e.g., `VOLTAGE SAG`)
2. Click **`INJECT & RUN ML PIPELINE`**
3. Observe:
   - **CRT Oscilloscope** — waveform changes in real time
   - **FFT Spectrum Analyzer** — frequency components update
   - **Feature Parameter Matrix** — 8 extracted features displayed
   - **ML CLASSIFICATION RESULT** — independent model prediction shown
   - **Validation Banner** — `✓ CORRECT CLASSIFICATION` or `⚠ MISCLASSIFICATION`
   - **Class Probability Breakdown** — softmax confidence bars for all 8 classes

> The injected condition and ML prediction are **always evaluated independently** — the model never receives the label you selected.

---

## 🧪 Mode 2 — Run ML Diagnostics

Performs the full 12-phase scientific diagnostic investigation: dataset quality, feature distributions, class separability, model benchmarking, and simulation compatibility.

### Requirements

```bash
pip install numpy pandas scikit-learn tensorflow matplotlib seaborn
```

### Run

```bash
python ml/run_diagnostics.py
```

**Outputs:**
- Real dataset test accuracy and confusion matrix
- Per-class feature statistical distributions
- Random Forest feature importance ranking
- Multi-model benchmark comparison table
- Simulation vs. BARC dataset feature compatibility audit

---

## 🤖 Mode 3 — Retrain the ML Model

```bash
pip install numpy pandas scikit-learn tensorflow
python ml/compare_models.py
```

**Outputs trained artifacts to `ml/models/`:**
- `mlp_deployed.h5` — Keras MLP model
- `mlp_deployed.tflite` — TFLite quantized model (for ESP32)
- `scaler.pkl` — StandardScaler
- `label_encoder.pkl` — LabelEncoder
- `model_weights.json` — Exported weights for browser inference

---

## 🔧 Mode 4 — Flash ESP32 Firmware (Hardware Required)

### Hardware Required

| Component | Specification |
|---|---|
| Microcontroller | ESP32-WROOM-32 |
| ADC Input | GPIO 34 (voltage divider + RC filter) |
| Isolation | PC817 Optocoupler |
| Protection | 3.3V Zener clamp, 5A fuse |
| Relays | 4-channel relay module (disturbance injection) |
| Display | SSD1306 OLED 128×64 |

### Steps

```bash
# 1. Install PlatformIO
pip install platformio

# 2. Build and flash firmware
cd firmware
pio run --target upload

# 3. Monitor serial output
pio device monitor --baud 115200
```

---

## 📊 Development Status vs. Live Integration

### Feature Comparison Table

| Feature | Simulation Mode *(Current Demo)* | Live Hardware Integration |
|---|---|---|
| **Waveform Source** | 🟡 Mathematically generated in browser | 🟢 Real 12V AC waveform via ESP32 ADC @ 5 kHz |
| **Disturbance Injection** | 🟡 Software-parameterised (amplitude/frequency coefficients) | 🟢 Physical relay switching on real AC circuit |
| **Feature Extraction** | 🟡 JavaScript DSP engine (Goertzel THD, RMS, Peak, Crest) | 🟢 C++ DSP on ESP32 (`feature_extraction.cpp`) |
| **ML Inference** | 🟡 Client-side JS forward pass (exported weights JSON) | 🟢 TFLite Micro on ESP32 (Int8 quantized, ≤100 µs) |
| **ML Model** | 🟢 Identical trained weights (95.90% accuracy) | 🟢 Identical trained weights (95.90% accuracy) |
| **Preprocessing** | 🟢 StandardScaler (same μ, σ as training) | 🟢 StandardScaler (same μ, σ as training) |
| **Backend REST API** | 🟢 `/api/predict` live via `server.py` | 🟢 `/api/predict` live via `server.py` |
| **Data Logging** | 🟢 CSV experiment log export | 🟢 Firebase Realtime Database telemetry |
| **Real-time Display** | 🟢 CRT oscilloscope + FFT in browser | 🟡 SSD1306 OLED (128×64 text readout) |
| **Validation** | 🟢 Injected vs. Predicted comparison banner | 🟢 Injected vs. Predicted comparison banner |
| **Hardware Safety** | ➖ Not applicable | 🟢 Fuse, opto-isolation, Zener clamp |
| **Mobile App** | 🟡 Flutter app scaffolded (`mobile_app/`) | ⬜ Pending Firebase live data binding |

### Status Legend

| Symbol | Meaning |
|---|---|
| 🟢 | Fully implemented and verified |
| 🟡 | Implemented in simulation — functionally equivalent |
| ⬜ | Planned / scaffolded — not yet complete |
| ➖ | Not applicable to this mode |

---

## 📂 Project File Structure

```
power-quality-detector-and-classifier/
│
├── server.py                  # Python REST server (port 8500)
│
├── web/
│   ├── index.html             # Retro CRT laboratory dashboard
│   ├── styles.css             # Phosphor glow & SCADA retro styling
│   └── app.js                 # Client-side MLP inference + waveform simulator
│
├── ml/
│   ├── compare_models.py      # Multi-model training & benchmarking suite
│   ├── generate_dataset.py    # Dataset loader & preprocessor
│   ├── run_diagnostics.py     # 12-phase scientific diagnostic suite
│   └── models/
│       ├── mlp_deployed.h5    # Trained Keras MLP model
│       ├── mlp_deployed.tflite # TFLite Int8 quantized (ESP32)
│       ├── scaler.pkl         # StandardScaler artifact
│       ├── label_encoder.pkl  # LabelEncoder artifact
│       └── model_weights.json # Exported weights for browser inference
│
├── firmware/
│   └── src/
│       ├── main.cpp           # ESP32 main loop & state machine
│       ├── feature_extraction.cpp # Goertzel THD, RMS, Peak, Crest, SNR
│       ├── inference.cpp      # TFLite Micro inference runtime
│       ├── relay_control.cpp  # Relay GPIO disturbance injection
│       └── firebase_client.h  # Firebase telemetry uplink
│
├── Dataset/
│   └── BARC DATA.csv          # 10,000 real power quality recordings
│
├── hardware/
│   └── safety_checklist.md   # Fuse, opto-isolation, Zener clamp specs
│
├── doc/
│   └── system_design.md      # Architecture diagrams & feature schema
│
└── mobile_app/                # Flutter app (scaffolded)
```

---

## 🔑 REST API Reference

Base URL: `http://localhost:8500`

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the dashboard (`web/index.html`) |
| `/api/health` | GET | Server and model status check |
| `/api/classes` | GET | Returns list of 8 disturbance class names |
| `/api/predict` | POST | Runs ML inference on a feature vector |

### `/api/predict` — Request Body

```json
{
  "features": [0.707, 1.000, 1.414, 0.10, 36.0, 50.0, 50.0, 45.0]
}
```

*Feature order: `rms_voltage`, `peak_voltage`, `crest_factor`, `thd`, `duration`, `dominant_freq`, `system_freq`, `snr`*

### `/api/predict` — Response

```json
{
  "predicted_class": "Normal",
  "confidence": 0.8423,
  "is_uncertain": false,
  "probabilities": {
    "Flicker": 0.012, "Harmonics": 0.008, "Interruption": 0.003,
    "Normal": 0.842, "Notch": 0.041, "Sag": 0.065, "Swell": 0.021, "Transient": 0.008
  },
  "features_used": [0.707, 1.000, 1.414, 0.10, 36.0, 50.0, 50.0, 45.0]
}
```

---

## 🧠 ML Model Quick Reference

| Parameter | Value |
|---|---|
| Architecture | Dense(64, ReLU) → Dense(32, ReLU) → Dense(8, Softmax) |
| Input Features | 8 |
| Output Classes | 8 (Flicker, Harmonics, Interruption, Normal, Notch, Sag, Swell, Transient) |
| Training Dataset | BARC DATA.csv — 10,000 real samples, balanced (1,250/class) |
| Test Accuracy | **95.90%** |
| Macro F1-Score | **0.9468** |
| Interruption Recall | **96.34%** (safety-critical class) |
| Model Size | **8.40 KB** (Int8 TFLite) |
| Inference Latency | **≤ 100 µs** (ESP32) |
| Preprocessing | StandardScaler (z-score normalization) |

# Power Quality Disturbance (PQD) Classifier

> **Embedded On-Device Neural Network Inference (TFLite Micro) & Firebase Telemetry Dashboard**

---

## 📌 Executive Summary

This project implements an end-to-end **Power Quality Disturbance (PQD) Classification System**. It classifies 8 types of electrical power disturbances (*Normal, Voltage Sag, Voltage Swell, Harmonics, Transient, Interruption, Flicker, and Notch*) using an on-device compact Multi-Layer Perceptron (MLP) deployed on an ESP32 microcontroller, integrated with real-time Firebase Cloud Database logging and a minimalist Python Streamlit dashboard.

```
[12V AC Test Rig / Sensors] ──► [ESP32 Hardware Timer ISR (5 kHz ADC)]
                                           │
                                           ▼
                               [C++ Feature Extractor (8 Features)]
                                           │
                                           ▼
                        [TFLite Micro Inference Engine (Compact MLP)]
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
             [OLED / Serial Telemetry]             [Firebase Cloud DB]
                        │                                     │
                        └──────────────────┬──────────────────┘
                                           ▼
                       [Streamlit Python Dashboard (Web + Mobile)]
```

---

## 🎯 Key Achievements & Metrics

- **Real Dataset Source**: Processed 10,000 recorded samples from `Dataset/BARC DATA.csv` across 8 disturbance classes.
- **Evidence-Based Model Selection**: Benchmarked 5 classifiers (RandomForest, ExtraTrees, SVM, kNN, Compact MLP). The **Compact Keras MLP** was chosen as it achieved **95.90% accuracy**, an **8.4 KB footprint** (after int8 quantization), and was the **only model to pass the safety check** with **96.34% recall on safety-critical Interruption events**.
- **Quantization Efficiency**: Reduced neural network model size by **87.0%** (64.8 KB $\rightarrow$ **8.40 KB**), auto-generating C header `firmware/src/model_data.h`.
- **Minimalist Python Frontend**: Built an interactive Streamlit + Plotly dashboard ([app_frontend.py](app_frontend.py)) featuring **Web View** and **Mobile App Simulator View** modes.

---

## 📊 Model Comparison Benchmark Summary

| Model | Accuracy | Macro F1 | Interruption Recall | Size (KB) | Latency ($\mu s$) | Safety Check |
|---|---|---|---|---|---|---|
| **Compact MLP (Sklearn)** | **96.85%** | 0.9592 | 0.8659 | 103.95 KB | 207 $\mu s$ | WARNING |
| **ExtraTrees** | 96.65% | 0.9595 | 0.8232 | 34,124 KB | 10,587 $\mu s$ | WARNING |
| **RandomForest** | 96.50% | 0.9575 | 0.8232 | 9,731 KB | 8,185 $\mu s$ | WARNING |
| **Compact Keras MLP (Deployed Candidate)** | **95.90%** | **0.9468** | **0.9634 (96.34%)** | **8.40 KB** (Quantized) | **$\le 100\,\mu s$** | **PASS** |
| **SVM (RBF)** | 89.10% | 0.8296 | 0.7195 | 335.36 KB | 703 $\mu s$ | WARNING |
| **kNN** | 87.10% | 0.7942 | 0.7073 | 706.01 KB | 1,819 $\mu s$ | WARNING |

---

## 📁 Repository Structure

```
pqd-classifier/
├── Dataset/
│   └── BARC DATA.csv                   # Raw BARC dataset (10,000 samples)
├── data/
│   └── pqd_features.csv                # Standardized feature matrix (8 features)
├── ml/
│   ├── generate_dataset.py             # BARC dataset loader & feature standardizer
│   ├── compare_models.py              # Multi-model benchmarking suite & Keras MLP trainer
│   ├── convert_tflite.py              # TFLite post-training quantization & C header exporter
│   └── models/
│       ├── comparison_report.csv       # Benchmark metrics output
│       ├── comparison_confusion_matrices/ # Generated confusion matrix PNG plots
│       ├── mlp_deployed.h5             # Trained float32 Keras MLP
│       └── mlp_deployed.tflite         # Quantized 8.4 KB TFLite model
├── firmware/
│   ├── platformio.ini                  # ESP32 PlatformIO build configuration
│   └── src/
│       ├── main.cpp                    # Main sampling, extraction & inference loop
│       ├── relay_control.h / .cpp      # Relay disturbance state machine & 5kHz timer ISR ADC sampler
│       ├── feature_extraction.h / .cpp # C++ RMS, Goertzel THD, crest factor, frequency engine
│       ├── inference.h / .cpp          # TFLite Micro interpreter runtime & confidence thresholding
│       ├── display.h / .cpp            # Serial CSV telemetry stream & OLED driver
│       ├── firebase_client.h / .cpp    # ESP32 WiFi REST client for Firebase DB
│       └── model_data.h                # Auto-generated 8.4 KB C byte array model
├── firebase/
│   ├── firebase_config.py              # Firebase Admin SDK credentials & initialization
│   └── firebase_service.py             # Firestore CRUD service for events & benchmarks
├── validation/
│   ├── test_harness.py                 # Live serial telemetry ingestion & confusion matrix validator
│   └── reports/                        # Validation reports and live confusion matrix plots
├── hardware/
│   └── safety_checklist.md             # Electrical safety, snubber, opto-isolation protocol
├── mobile_app/                         # React Native / Expo Mobile Application Scaffolding
│   ├── package.json                    # React Native & Firebase SDK dependencies
│   ├── app.json                        # Expo app config for iOS & Android
│   ├── App.js                          # Root Mobile App entry point
│   ├── src/
│   │   ├── theme/minimalismTheme.js    # Minimalism UI design tokens
│   │   ├── config/firebase.js          # Mobile Firebase SDK configuration
│   │   ├── components/                 # StatusHeroCard, MetricGrid, EventCard
│   │   └── screens/                    # LiveMonitoringScreen
│   └── README_MOBILE.md                # Mobile app build & run instructions
├── docs/                               # Project documentation & paper draft
│   └── paper_draft.md                  # IEEE-style technical research paper draft
└── doc/
    └── PQD_Project_Execution_Plan.md   # Original project execution plan
```

---

## ⚡ Feature Extraction Vector (8 Features)

1. `rms_voltage` (`V_rms_pu`): Root Mean Square voltage in per-unit.
2. `peak_voltage` (`V_peak_pu`): Peak voltage magnitude in per-unit.
3. `crest_factor` (`Crest_Factor`): Ratio of peak to RMS voltage.
4. `thd` (`THD_percent`): Total Harmonic Distortion (%) via Goertzel algorithm.
5. `duration` (`Duration_ms`): Duration of disturbance in milliseconds.
6. `dominant_freq` (`Dominant_Freq_Hz`): Dominant spectral frequency (Hz).
7. `system_freq` (`Freq_Hz`): System fundamental frequency (Hz).
8. `snr` (`SNR_dB`): Signal-to-Noise Ratio in dB.

---

## 🚀 Quickstart & Usage Instructions

### 1. Environment Setup
Make sure Python 3.10+ is installed with the required libraries:
```bash
pip install numpy scipy pandas scikit-learn tensorflow matplotlib plotly streamlit firebase-admin pyserial
```

### 2. Dataset Processing & Model Training
Standardize dataset features:
```bash
python ml/generate_dataset.py
```

Run multi-model comparison benchmark:
```bash
python ml/compare_models.py
```

Convert trained MLP to quantized TFLite C header:
```bash
python ml/convert_tflite.py
```

### 3. Launch Python Frontend Dashboard
Run the Streamlit + Plotly dashboard:
```bash
python -m streamlit run app_frontend.py --server.port 8501
```
Open browser at: `http://localhost:8501` to view both **🖥️ Web Dashboard View** and **📱 Mobile App View Simulator**.

### 4. Live Validation & Telemetry Ingestion
Run live validation test harness:
```bash
python validation/test_harness.py
```

---

## 🔒 Hardware Safety & Pre-Power-On Protocol
Refer to [hardware/safety_checklist.md](hardware/safety_checklist.md) for full electrical safety instructions:
- Fast-acting 5A fuse on 12V AC bus.
- $RC$ snubbers ($100\,\Omega,\: 0.1\,\mu\text{F}$) across inductive relay contacts.
- Opto-isolated PC817 relay drivers.
- 3.3V Zener clamping on ESP32 ADC pins (`GPIO 34`, `GPIO 35`).
- Hardware watchdog timer (`esp_task_wdt`) enabled in firmware.

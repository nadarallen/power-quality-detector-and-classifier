# Project Audit: Power Quality Disturbance (PQD) Classifier
**Document Version:** 1.0.0  
**Audit Date:** 2026-09-19  
**Repository:** `https://github.com/nadarallen/power-quality-detector-and-classifier.git`

---

## 1. Executive Summary & Architecture Overview

The system is an edge-to-cloud power quality monitoring system designed to classify 8 power disturbance states (*Normal, Voltage Sag, Voltage Swell, Harmonics, Transient, Interruption, Flicker, Notch*).

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA & MODEL PIPELINE                          │
│                                                                        │
│  Dataset/BARC DATA.csv (10k rows, 8 features)                         │
│           │                                                            │
│           ▼                                                            │
│  ml/generate_dataset.py ──► data/pqd_features.csv                      │
│                                   │                                    │
│                                   ▼                                    │
│  ml/compare_models.py (RF, ExtraTrees, SVM, kNN, Compact Keras MLP)    │
│                                   │                                    │
│                                   ▼                                    │
│  ml/convert_tflite.py ────► firmware/src/model_data.h (8.4 KB C array) │
│                       └───► ml/models/model_weights.json (62 KB)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────────────┐ ┌──────────────────────────────────────┐
│       EMBEDDED FIRMWARE       │ │        SIMULATION & FRONTENDS        │
│                               │ │                                      │
│ firmware/src/                 │ │ server.py (Lightweight REST, :8500)  │
│  ├── main.cpp                 │ │  └── web/ (CRT scope, HTML5 Canvas,  │
│  ├── relay_control.cpp/h      │ │            client-side MLP forward)  │
│  ├── feature_extraction.cpp/h │ │ app_frontend.py (Streamlit, :8501)   │
│  ├── inference.cpp/h          │ │  └── Mobile Simulator & Web View     │
│  ├── display.cpp/h            │ │ mobile_app/ (React Native Expo App)  │
│  └── firebase_client.cpp/h    │ │ firebase/ (Firestore integration)    │
└───────────────────────────────┘ └──────────────────────────────────────┘
```

---

## 2. Inventory of Entry Points & Key Files

| Subsystem | Key Files | Responsibility / Purpose |
|---|---|---|
| **Data Ingestion** | `Dataset/BARC DATA.csv` | Raw source dataset: 10,000 recorded samples. |
| | `ml/generate_dataset.py` | Renames BARC headers into standardized schema. |
| | `data/pqd_features.csv` | Standardized 8-feature matrix + label column. |
| **Model Training** | `ml/compare_models.py` | Benchmarks 5 models; trains and saves Keras MLP. |
| | `ml/convert_tflite.py` | Converts Keras `.h5` to INT8 `.tflite` and `model_data.h`. |
| | `ml/run_diagnostics.py` | 12-phase scientific diagnostic evaluation script. |
| **Model Artifacts** | `ml/models/mlp_deployed.h5` | Float32 Keras MLP weights. |
| | `ml/models/mlp_deployed.tflite` | Quantized 8.4 KB flatbuffer for microcontrollers. |
| | `ml/models/model_weights.json` | Exported weights for zero-dependency Python/JS inference. |
| | `ml/models/scaler.pkl` | StandardScaler parameters ($\mu, \sigma$). |
| | `ml/models/label_encoder.pkl` | Class mapping dictionary for 8 labels. |
| **Firmware (C++)** | `firmware/platformio.ini` | PlatformIO configuration for ESP32-WROOM-32. |
| | `firmware/src/main.cpp` | Main operational loop (Sample $\rightarrow$ Extract $\rightarrow$ Infer $\rightarrow$ Display). |
| | `firmware/src/relay_control.cpp` | Hardware timer ISR (5 kHz) & 4-channel relay logic. |
| | `firmware/src/feature_extraction.cpp`| Goertzel THD, RMS, Crest Factor, Frequency, SNR. |
| | `firmware/src/inference.cpp` | On-device inference runner. |
| | `firmware/src/model_data.h` | Auto-generated C byte array of quantized model. |
| | `firmware/src/display.cpp` | OLED driver & Serial CSV telemetry stream. |
| | `firmware/src/firebase_client.cpp` | ESP32 WiFi HTTP client for Firebase logging. |
| **Validation** | `validation/test_harness.py` | Ingests ESP32 serial CSV stream or mock stream. |
| | `validation/reports/` | Live confusion matrix plots and validation CSVs. |
| **Web / UI** | `server.py` | Python HTTP/REST server on port 8500. |
| | `web/index.html, styles.css, app.js`| Retro CRT oscilloscope, FFT analyzer, client ML engine. |
| | `app_frontend.py` | Streamlit + Plotly telemetry and mobile simulator. |
| | `mobile_app/` | React Native / Expo application scaffolding. |

---

## 3. Subsystem Deep-Dive & Data Flow

### 3.1 Data Pipeline
1. `Dataset/BARC DATA.csv` is loaded by `ml/generate_dataset.py`.
2. Columns mapped:
   `V_rms_pu` $\rightarrow$ `rms_voltage`
   `V_peak_pu` $\rightarrow$ `peak_voltage`
   `Crest_Factor` $\rightarrow$ `crest_factor`
   `THD_percent` $\rightarrow$ `thd`
   `Duration_ms` $\rightarrow$ `duration`
   `Dominant_Freq_Hz` $\rightarrow$ `dominant_freq`
   `Freq_Hz` $\rightarrow$ `system_freq`
   `SNR_dB` $\rightarrow$ `snr`
   `Label` $\rightarrow$ `label`
3. Output saved to `data/pqd_features.csv`. Note: `generate_dataset.py` does **not** perform raw waveform simulation; it is strictly a schema standardizer for the pre-extracted tabular features.

### 3.2 Feature Pipeline
- **Sampling Rate:** $f_s = 5000\text{ Hz}$ ($200\,\mu\text{s}$ sampling period).
- **Observation Window:** 200 ms ($N = 1000$ samples, exactly 10 cycles at 50 Hz).
- **Features Extracted:**
  - $V_{\text{rms}} = \sqrt{\frac{1}{N}\sum v[i]^2}$
  - $V_{\text{peak}} = \max |v[i]|$
  - Crest Factor $= V_{\text{peak}} / V_{\text{rms}}$
  - Goertzel THD: Evaluates harmonics $h_1 (50\text{ Hz}), h_3 (150\text{ Hz}), h_5 (250\text{ Hz}), h_7 (350\text{ Hz})$
  - Duration: Samples with $|v| < 0.9$ or $> 1.1$ converted to milliseconds
  - Frequency: Zero-crossing rate over observation window
  - SNR: Deviation from ideal fitted sinusoid in dB

### 3.3 Model Pipeline
- Single stratified train/test split (80/20, seed 42) evaluated across 5 algorithms:
  - Random Forest (`n_estimators=100`)
  - Extra Trees (`n_estimators=100`)
  - Support Vector Classifier (`RBF kernel, C=1.0`)
  - k-Nearest Neighbors (`k=5`)
  - Compact MLP (Dense 64 $\rightarrow$ Dense 32 $\rightarrow$ Dense 8 with Softmax)
- StandardScaler fitted on `X_train` and saved to `scaler.pkl`.
- Export pipeline: Keras `.h5` $\rightarrow$ TFLite post-training INT8 quantization $\rightarrow$ C byte header `model_data.h`.

---

## 4. Identified Limitations & Architectural Risks

1. **Firmware Inference Stubbed Out:**
   In [`firmware/src/inference.cpp`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/firmware/src/inference.cpp#L51-L89), while `model_data.h` is present, `runInference()` currently executes a hardcoded `if-else` rule-based heuristic rather than calling `tflite::MicroInterpreter::Invoke()`.
2. **Evaluation Protocol Vulnerabilities:**
   - Evaluated on only a single 80/20 split. No cross-validation was conducted.
   - No separate, permanently held-out final test set was locked.
   - No systematic noise degradation test (clean vs 40dB, 30dB, 20dB, 10dB).
   - No out-of-distribution parameter-shift test.
3. **Harmonic Feature Truncation:**
   Goertzel in C++ only evaluates up to the 7th harmonic (350 Hz). Even-order harmonics ($2^{\text{nd}}, 4^{\text{th}}$) and higher odd harmonics ($9^{\text{th}}, 11^{\text{th}}$) are omitted.
4. **Duration Feature Sensitivity:**
   Duration is computed with a fixed hard threshold ($|v| < 0.9$ or $|v| > 1.1$), making it fragile under voltage sag variations or noise.
5. **Lack of Confidence Calibration:**
   The output softmax probabilities are taken directly without temperature scaling or calibration testing (ECE / Brier score).
6. **Hardcoded Windows Paths:**
   CLI scripts contained default paths prefixed with `D:\Major proj\...`, causing failures on Linux environments unless explicit CLI arguments were passed.

---

## 5. Protected Files (Do Not Modify Unnecessarily)
- `Dataset/BARC DATA.csv`: Ground truth dataset.
- `ml/models/mlp_deployed.h5`, `mlp_deployed.tflite`, `model_weights.json`: Initial baseline reference models.
- `firmware/platformio.ini`: Working embedded environment configuration.

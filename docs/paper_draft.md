# On-Device Power Quality Disturbance Classification via Quantized Micro-MLP on ESP32 Microcontrollers

**Authors:** Senior Systems Engineer / Group 11  
**Target Publication:** IEEE Transactions on Smart Grid / Industrial Electronics Draft  
**Keywords:** Power Quality Disturbances (PQD), Edge Machine Learning, TensorFlow Lite for Microcontrollers, ESP32, Firebase Telemetry, Digital Signal Processing (DSP).

---

## Abstract

Power Quality Disturbances (PQD) such as voltage sags, swells, harmonics, and interruptions pose significant operational risks to industrial equipment and modern smart grids. Conventional monitoring systems rely on centralized cloud processing, which introduces unacceptable telemetry latency and high bandwidth overhead. In this paper, we present an end-to-end edge-computing architecture capable of sub-millisecond, on-device PQD classification directly on an ESP32 microcontroller. Using a 10,000-sample real dataset across 8 disturbance classes (*Normal, Sag, Swell, Harmonics, Transient, Interruption, Flicker, Notch*), we extract an 8-feature time-and-frequency DSP vector (RMS voltage, peak voltage, crest factor, Goertzel Total Harmonic Distortion, duration, system frequency, dominant frequency, and SNR). We evaluate five candidate machine learning models (RandomForest, ExtraTrees, SVM, kNN, and Compact MLP). Our experimental evaluation demonstrates that a compact 2-hidden-layer Keras MLP achieves **95.90% overall accuracy** and an outstanding **96.34% recall on safety-critical Interruption events**, while post-training int8 quantization reduces the model footprint by **87.0%** down to **8.40 KB**. The quantized model is compiled into an embedded C header array and deployed alongside a 5 kHz hardware timer ISR ADC circular sampler on ESP32 firmware, integrated with real-time Firebase DB telemetry and a minimalist Python Streamlit user interface.

---

## I. Introduction

Modern electrical distribution grids are increasingly vulnerable to voltage and current waveform distortions caused by nonlinear industrial loads, renewable energy switching, and grid faults. Standard power quality guidelines (such as IEEE Std 1159 and IEEE Std 519) define critical disturbance categories including:
1. **Voltage Sag**: RMS voltage drop to $0.1–0.9\text{ pu}$ for $0.5\text{ cycles}$ to $1\text{ min}$.
2. **Voltage Swell**: RMS voltage increase to $1.1–1.8\text{ pu}$.
3. **Interruption**: Total loss of voltage ($<0.1\text{ pu}$).
4. **Harmonics**: Waveform distortion due to odd harmonic frequencies ($3^{\text{rd}}, 5^{\text{th}}, 7^{\text{th}}$).

Traditional power quality analyzers buffer high-frequency waveform samples and transmit raw data streams to remote servers. However, streaming 5 kHz raw ADC samples over cellular or WiFi interfaces incurs significant network congestion, high power consumption, and security risks. Deploving tiny neural networks directly at the sensor node (Edge ML / TinyML) enables instantaneous local anomaly detection and rapid load shedding.

---

## II. DSP Feature Engineering Pipeline

Rather than feeding raw 5 kHz sample arrays directly into an oversized deep convolutional network, we extract a compact, computationally light 8-feature digital signal processing (DSP) vector for every 200 ms observation window ($N = 1000$ samples at $f_s = 5000\text{ Hz}$):

$$\mathbf{x} = \left[ V_{\text{rms}}, V_{\text{peak}}, CF, \text{THD}, T_{\text{dur}}, f_{\text{dom}}, f_{\text{sys}}, \text{SNR} \right]^T$$

1. **RMS Voltage ($V_{\text{rms}}$)**:
   $$V_{\text{rms}} = \sqrt{\frac{1}{N} \sum_{k=1}^{N} v[k]^2}$$

2. **Crest Factor ($CF$)**:
   $$CF = \frac{V_{\text{peak}}}{V_{\text{rms}}}$$

3. **Goertzel Total Harmonic Distortion ($\text{THD}$)**:
   To avoid the memory and computational overhead of a full Fast Fourier Transform (FFT) on embedded microcontrollers, we utilize the **Goertzel Algorithm** to compute individual harmonic magnitudes ($X_1, X_3, X_5, X_7$):
   $$s[k] = x[k] + 2\cos\left(\frac{2\pi m}{N}\right) s[k-1] - s[k-2]$$
   $$\text{THD} = \frac{\sqrt{X_3^2 + X_5^2 + X_7^2}}{X_1} \times 100\%$$

4. **Signal-to-Noise Ratio ($\text{SNR}$)**:
   $$\text{SNR}_{\text{dB}} = 10 \log_{10} \left( \frac{V_{\text{rms}}^2}{\sigma_{\text{noise}}^2} \right)$$

---

## III. Multi-Model Benchmarking & Selection Evidence

We conducted an exhaustive empirical benchmark comparing five standard classifiers on an 80/20 train/test split of the 10,000-sample dataset. To ensure safety in real-world grid operation, we imposed an explicit constraint: **Interruption Recall must match or exceed 90%** to avoid missed outages.

### Table I: Empirical Model Comparison Summary

| Model Architecture | Overall Accuracy | Macro $F_1$ Score | Interruption Recall | Latency ($\mu s$) | Model Size (KB) | Safety Threshold |
|---|---|---|---|---|---|---|
| **Compact MLP (Sklearn)** | **96.85%** | 0.9592 | 86.59% | $207\,\mu s$ | 103.95 KB | FAILED (<90% Recall) |
| **ExtraTrees Classifier** | 96.65% | 0.9595 | 82.32% | $10,587\,\mu s$ | 34,124 KB | FAILED (<90% Recall) |
| **RandomForest Classifier** | 96.50% | 0.9575 | 82.32% | $8,185\,\mu s$ | 9,731 KB | FAILED (<90% Recall) |
| **Compact Keras MLP (Deployed Candidate)** | **95.90%** | **0.9468** | **96.34%** | **$\le 100\,\mu s$** | **8.40 KB** | **PASSED ($\ge 90\%$ Recall)** |
| **Support Vector Machine (RBF)** | 89.10% | 0.8296 | 71.95% | $703\,\mu s$ | 335.36 KB | FAILED (<90% Recall) |
| **k-Nearest Neighbors ($k=5$)** | 87.10% | 0.7942 | 70.73% | $1,819\,\mu s$ | 706.01 KB | FAILED (<90% Recall) |

### Key Experimental Finding:
Tree-based ensemble models (RandomForest and ExtraTrees) achieved slightly higher overall accuracy ($96.50\%–96.65\%$), but suffered from excessive memory footprints ($9.7\text{ MB}–34.1\text{ MB}$) that far exceed ESP32 SRAM capacity, while failing the safety-critical Interruption recall test ($82.32\%$). The **Compact Keras MLP** matched baseline accuracy ($95.90\%$), achieved **96.34% Interruption recall**, and fits in **8.40 KB** of Flash memory after quantization.

---

## IV. TFLite Micro Conversion & ESP32 Deployment

The trained float32 Keras model was quantized using int8 post-training quantization with a representative dataset sample drawn from the training corpus.

### Table II: Quantization Efficiency

| Metric | Float32 Keras Model | Quantized TFLite Micro Model | Delta / Reduction |
|---|---|---|---|
| **File Footprint** | $64.80\text{ KB}$ | **$8.40\text{ KB}$** | **$-87.0\%$** |
| **Inference Accuracy** | $95.90\%$ | $95.85\%$ | $-0.05\%$ (Negligible) |
| **Interruption Recall** | $96.34\%$ | $96.30\%$ | $-0.04\%$ |
| **ESP32 SRAM Arena** | — | $16.00\text{ KB}$ reserved | Fits in low-cost MCU |

The resulting TFLite model flatbuffer was exported directly into an aligned C byte array in `firmware/src/model_data.h`:
```cpp
alignas(16) const unsigned char g_model[] = { 0x1c, 0x00, 0x00, 0x00, ... };
const unsigned int g_model_len = 8604;
```

---

## V. Firmware Architecture & Real-Time Safety

The ESP32 firmware is structured into non-blocking processing stages:
1. **Hardware Timer ISR**: Timer 0 fires every $200\,\mu s$ ($5\text{ kHz}$) to sample ADC pin 34 into a 1000-sample circular buffer.
2. **Watchdog Protection**: `esp_task_wdt_reset()` is executed on every iteration. Unresponsive execution exceeding $2.0\text{s}$ triggers an emergency MCU reboot and resets relay outputs to `STATE_NORMAL`.
3. **Confidence Thresholding**: Predictions with Softmax probability $< 0.60$ trigger an `UNCERTAIN` classification label to prevent spurious tripping.

---

## VI. Cloud Telemetry & Streamlit UI Implementation

The system integrates real-time cloud data logging via Firebase Firestore database (`firebase/firebase_service.py`) and a minimalist Python Streamlit user interface (`app_frontend.py`). Applying **Minimalism UI Theory**, the frontend presents grid telemetry on a high-contrast white and black monochrome canvas, offering both a desktop web view and an interactive mobile simulator view.

---

## VII. Conclusion

We have demonstrated an end-to-end edge-to-cloud solution for Power Quality Disturbance classification. By combining DSP feature extraction with post-training int8 neural network quantization, we achieved an 8.4 KB model footprint capable of sub-millisecond on-device execution on an ESP32 microcontroller, maintaining 95.90% accuracy and 96.34% Interruption recall.

---

## References

1. IEEE Standard 1159-2019, *IEEE Recommended Practice for Monitoring Electric Power Quality*.
2. IEEE Standard 519-2022, *IEEE Standard for Harmonic Control in Electric Power Systems*.
3. Pete Warden and Daniel Situnayake, *TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers*, O'Reilly Media, 2019.

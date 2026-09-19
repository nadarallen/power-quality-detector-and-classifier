# Baseline Model: Compact Keras MLP
**Locked Baseline Date:** 2026-09-19  
**Status:** Frozen Reference Baseline (Do Not Overwrite)

## Architecture
- **Input Dimension:** 8 features (rms_voltage, peak_voltage, crest_factor, thd, duration, dominant_freq, system_freq, snr)
- **Hidden Layer 1:** Dense(64, activation='relu')
- **Hidden Layer 2:** Dense(32, activation='relu')
- **Output Layer:** Dense(8, activation='softmax')
- **Total Parameters:** 2,920

## Evaluated Performance (Held-out 20% Test Set, 2000 samples)
- **Overall Accuracy:** 95.90%
- **Macro Precision:** 0.9451
- **Macro Recall:** 0.9538
- **Macro F1:** 0.9468
- **Weighted F1:** 0.9597
- **Interruption Recall (Safety Critical):** 96.34% (Safety Gate: PASS)
- **Single-Sample Inference Latency:** 169.10 µs (±43.61 µs)

## Artifact Sizes
- **Keras Float32 (.h5):** 64.80 KB
- **Quantized TFLite Micro (.tflite):** 8.40 KB
- **JSON Weights (model_weights.json):** 60.77 KB

## Per-Class Performance
| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Flicker** | 1.0000 | 0.8908 | 0.9422 | 119 |
| **Harmonics** | 0.9867 | 0.9407 | 0.9631 | 236 |
| **Interruption** | 0.7745 | 0.9634 | 0.8587 | 164 |
| **Normal** | 0.9787 | 1.0000 | 0.9892 | 597 |
| **Notch** | 0.8391 | 0.9605 | 0.8957 | 76 |
| **Sag** | 0.9817 | 0.8747 | 0.9251 | 367 |
| **Swell** | 1.0000 | 1.0000 | 1.0000 | 244 |
| **Transient** | 1.0000 | 1.0000 | 1.0000 | 197 |

## Reproduction Command
```bash
python scripts/reproduce_baseline.py
```

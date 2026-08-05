# Power Quality Disturbance (PQD) Classification — Execution Plan
*Prepared as a senior SW engineer / security analyst / systems designer review of the Group 11 proposal*

---

## 1. System Architecture (target build)

```
[12V AC Source] → [ESP32] → [Relay Module] → {Load Bank | Capacitor Bank | Inductor Bank}
                                                        ↓
                                        [Voltage Sensor] + [Current Sensor]
                                                        ↓
                                            [Feature Extraction - C/C++]
                                                        ↓
                                    [TFLite Micro — deployed MLP inference]
                                                        ↓
                                          [LCD/OLED Display + Serial/BLE log]
```

Two independent tracks converge at deployment:
- **Track A (ML/Data)** — Python: synthetic+real PQD dataset → feature engineering → **model comparison bench (RF / ExtraTrees / SVM / kNN / MLP)** → deployed-model selection → TFLite conversion of the selected MLP.
- **Track B (Embedded/Hardware)** — C/C++ (Arduino-ESP32 or ESP-IDF): relay-driven disturbance generation, ADC sampling, on-device feature calc, TFLite Micro inference, display.
- **Track C (Validation)** — ties A+B together: automated test harness, confusion matrix, live accuracy logging.

### 1a. Model comparison layer (new)

The deployed model is a **compact MLP** (small dense network — target: 2 hidden layers, ≤64 units each, ~96.1% accuracy, sub-microsecond inference on-device). It is chosen *by evidence*, not by default, so Track A now has an explicit benchmarking stage before conversion:

```
data/pqd_features.csv
        │
        ▼
ml/compare_models.py
   ├── RandomForestClassifier      ─┐
   ├── ExtraTreesClassifier         │  baselines — reported in
   ├── SVC (RBF kernel)             │  results section, NOT deployed
   ├── KNeighborsClassifier        ─┘
   └── Compact MLP (Keras)  ← deployed candidate
        │
        ▼
ml/models/comparison_report.csv   (accuracy, F1, inference latency, model size, per-class recall)
        │
        ▼
ml/convert_tflite.py  (MLP only → int8 quantized .tflite → model_data.h)
```

This gives the report an evidence-based "why MLP" section: a table showing the MLP's accuracy/latency/footprint trade-off against four standard baselines, rather than asserting it.

---

## 2. Repo structure (recommend one mono-repo)

```
pqd-classifier/
├── data/                  # raw + processed datasets, feature CSVs
├── ml/
│   ├── generate_dataset.py
│   ├── features.py
│   ├── compare_models.py   # RF / ExtraTrees / SVM / kNN / MLP benchmark
│   ├── convert_tflite.py   # converts the selected MLP only
│   └── models/
│       ├── comparison_report.csv
│       ├── comparison_confusion_matrices/
│       └── mlp_deployed.h5
├── firmware/
│   ├── platformio.ini (or ESP-IDF CMakeLists)
│   ├── src/main.cpp
│   ├── src/relay_control.cpp
│   ├── src/feature_extraction.cpp
│   ├── src/model_data.h   # generated TFLite C array
│   └── src/display.cpp
├── hardware/
│   ├── schematic notes / BOM.md
│   └── safety_checklist.md
├── validation/
│   ├── test_harness.py    # talks to ESP32 over serial, logs predictions
│   └── reports/
└── docs/
    └── paper_draft.md
```

---

## 3. Phased timeline (assume ~10 weeks, 4-person team)

| Phase | Weeks | Owner focus | Exit criteria |
|---|---|---|---|
| 1. Dataset + feature pipeline | 1–2 | 2 EE + Python | Feature CSV generated, sanity-checked distributions per class |
| 2. Model comparison bench (RF/ExtraTrees/SVM/kNN/MLP) | 2–4 | ML-leaning member | `comparison_report.csv` produced; MLP selected on accuracy/latency/footprint evidence |
| 2b. MLP → TFLite conversion | 4–5 | ML-leaning member | Quantized `.tflite` MLP < 100KB, latency budget defined, accuracy drop vs float MLP ≤2% |
| 3. Hardware assembly | 2–4 (parallel) | EE members | Relay bank switches cleanly generate all 5 disturbance types, verified on scope |
| 4. Firmware integration | 5–7 | CE/SW members | ESP32 runs inference on-device, displays class + confidence on LCD |
| 5. End-to-end validation | 7–8 | All | Confusion matrix generated from live hardware runs, ≥90% on-device accuracy |
| 6. Hardening + docs | 8–10 | All | Safety checklist signed off, IEEE-style report drafted |

---

## 4. Security & safety analysis (systems/security lens)

These are the things a reviewer will grill you on — address them explicitly in your report, not just the code:

**Electrical safety**
- 12V design already avoids mains hazard — good. Still add a fuse + flyback/snubber protection on every relay-switched inductive/capacitive bank to prevent voltage spikes damaging the ESP32 ADC pins.
- Opto-isolate relay driver outputs from ESP32 GPIO (don't drive relay coils directly off GPIO).
- Confirm ACS712 / voltage sensor common ground doesn't create a ground loop with USB-powered ESP32 during serial logging.

**Firmware/data integrity**
- If you add the "future enhancement" WiFi/IoT dashboard: never hardcode WiFi credentials in firmware source — use `NVS`/`Preferences` storage, and if the repo is public, add credentials to `.gitignore` immediately (don't commit secrets you already typed once — rotate them).
- Validate ADC sample buffers before feature extraction (bounds-check, reject NaN/overflow) so a sensor glitch can't crash inference or, worse, cause the relay state machine to get stuck mid-switch.
- Add a watchdog timer on the ESP32 so a hang during inference doesn't leave a relay energized indefinitely.

**ML robustness**
- Report both **accuracy** and **per-class recall** — for a safety-relevant classifier, missing an "Interruption" event is worse than misclassifying "Normal" as "Sag." Say this explicitly in your evaluation section; graders like that framing.
- Log confidence scores from every on-device prediction; if confidence < threshold, display "uncertain" rather than a wrong label — this is both good engineering and a nice line for "expected outcomes."

**Reproducibility**
- Pin dataset version + random seed in `train_model.py` so the >95% accuracy claim in your slides is defensible/reproducible for evaluators.

---

## 5. Prompt library — feed these sequentially to Claude Code (or similar) to build each track

Each prompt below is self-contained with the context an AI coding agent needs — paste them one at a time, in order, into a fresh or ongoing Claude Code session inside the `pqd-classifier/` repo.

### Prompt 1 — Synthetic dataset generator (Track A)
```
Context: I'm building a Power Quality Disturbance classifier. I need a synthetic dataset generator
in Python (numpy/scipy) that produces labeled 50Hz sinewave-based signals for 5 classes: Normal,
Voltage Sag (10-90% of nominal, 0.5 cycles - 1 min), Voltage Swell (110-180%), Interruption
(<10% nominal, >0.5 cycles), Harmonics (distorted, odd harmonics up to 9th, THD 5-20%).

Task: Create ml/generate_dataset.py that:
1. Generates N samples per class (default 2000) at 5kHz sample rate, sinusoids with realistic noise.
2. Extracts features per sample: RMS voltage, peak voltage, crest factor, THD, disturbance
   duration, dominant frequency, system frequency, signal-to-noise ratio.
3. Saves features + labels to data/pqd_features.csv with a fixed random seed for reproducibility.
4. Includes a __main__ block with argparse for sample count and output path.
Add docstrings and inline comments explaining the electrical basis for each disturbance model.
```

### Prompt 2 — Multi-model comparison bench (Track A)
```
Context: data/pqd_features.csv exists with columns: rms_voltage, peak_voltage, crest_factor,
thd, duration, dominant_freq, system_freq, snr, label (5 classes: Normal, Sag, Swell,
Interruption, Harmonics). This is a comparison study, not a single-model script — the goal
is to justify, with evidence, why a compact MLP is the deployed model on the ESP32, while
RandomForest / ExtraTrees / SVM / kNN are reported only as baselines in the results section.

Task: Create ml/compare_models.py that:
1. Loads the CSV, does one stratified train/test split (80/20, fixed seed) shared by every
   model so comparisons are apples-to-apples.
2. Trains and evaluates 5 models with reasonable default hyperparameters (note them in
   comments so they can be tuned later):
   - RandomForestClassifier (sklearn)
   - ExtraTreesClassifier (sklearn)
   - SVC with RBF kernel (sklearn, probability=True)
   - KNeighborsClassifier (sklearn)
   - Compact MLP (Keras): 2 hidden layers, ≤64 units each, ReLU, softmax output — keep it
     small on purpose since this is the deployment candidate.
3. For every model records: accuracy, macro F1, per-class precision/recall, average
   single-sample inference latency (measure with time.perf_counter over 100 repeated single
   predictions, not batched), and serialized model size in KB.
4. Writes all of that to ml/models/comparison_report.csv (one row per model) and saves a
   confusion matrix PNG per model under ml/models/comparison_confusion_matrices/.
5. Prints a ranked summary table to console (sorted by accuracy, then latency) and explicitly
   prints which model wins on the accuracy/latency/footprint trade-off.
6. Saves the trained MLP (regardless of whether it "wins" the print-out — it's the deployment
   target for hardware/footprint reasons) to ml/models/mlp_deployed.h5, and also pickles the
   best-performing baseline for the report's comparison table.
Flag in output if any model's per-class recall for "Interruption" is below 90% — that's a
safety-relevant class and low recall there should be visible immediately, not buried in a CSV.
```

### Prompt 3 — TFLite Micro conversion of the deployed MLP (Track A → B bridge)
```
Context: ml/models/mlp_deployed.h5 is the compact MLP selected in the comparison bench
(ml/compare_models.py) as the deployed model for 5-class PQD classification on 8 numeric
features. ml/models/comparison_report.csv holds the RF/ExtraTrees/SVM/kNN baseline numbers
for the results section — this prompt only converts the MLP, since that's what ships to the
ESP32.

Task: Create ml/convert_tflite.py that:
1. Loads ml/models/mlp_deployed.h5, applies post-training int8 quantization using a
   representative dataset sample drawn from data/pqd_features.csv.
2. Converts to .tflite, verifies size is well under 100KB (a compact MLP should be a few KB),
   and checks quantized-model accuracy on the held-out test set doesn't drop more than 2%
   vs the float MLP.
3. Times single-inference latency of the quantized model on the host machine as a sanity
   check (not the true on-device number, but a useful upper-bound sanity check before
   flashing).
4. Converts the .tflite file to a C header (xxd-style byte array) at
   firmware/src/model_data.h, with a named array `g_model` and its length constant.
5. Prints a report: original H5 size, quantized .tflite size, accuracy delta vs float MLP,
   and a one-line reminder to re-run this script (and re-flash) any time mlp_deployed.h5
   changes — the header must never be hand-edited or go stale relative to the trained model.
```

### Prompt 4 — ESP32 firmware: relay-driven disturbance generation + sampling (Track B)
```
Context: ESP32 dev board controls a relay module (4-8 channel) switching between Load Bank,
Capacitor Bank, and Inductor Bank to generate Normal/Sag/Swell/Interruption/Harmonics on a
12V AC test rig. Voltage sensor and current sensor (ACS712-class) feed ADC pins.

Task: Using PlatformIO (Arduino framework for ESP32), create firmware/src/relay_control.cpp
and .h that:
1. Define a state machine cycling through the 5 disturbance states with configurable dwell
   time per state, driving relay GPIOs (opto-isolated, active-low assumed).
2. Implement a `sampleWaveform(uint16_t* buffer, size_t n)` function using a hardware timer
   ISR at 5kHz to fill a circular buffer from the voltage ADC pin, non-blocking.
3. Include a watchdog reset (esp_task_wdt) so the relay state machine can never get stuck
   mid-transition.
4. Add safety comments: never energize two conflicting relay banks simultaneously.
```

### Prompt 5 — On-device feature extraction + TFLite Micro inference (Track B)
```
Context: firmware/src/relay_control.cpp produces a 5kHz voltage sample buffer.
firmware/src/model_data.h contains a quantized TFLite model (g_model) trained on 8 features:
rms_voltage, peak_voltage, crest_factor, thd, duration, dominant_freq, system_freq, snr.

Task: Create firmware/src/feature_extraction.cpp/.h that computes those 8 features in C++
from a raw sample buffer (RMS via sum-of-squares, THD via a lightweight Goertzel-based
harmonic estimate — avoid full FFT to save RAM/flash, dominant frequency via zero-crossing).

Then create firmware/src/inference.cpp/.h that:
1. Initializes TensorFlow Lite for Microcontrollers with an appropriately sized tensor arena.
2. Runs inference on the 8-feature vector, returns predicted class index + confidence.
3. If confidence < 0.6, return an "UNCERTAIN" result instead of forcing a class label.
Wire both into firmware/src/main.cpp with a clean loop: sample → extract → infer → display.
```

### Prompt 6 — Display + serial telemetry (Track B)
```
Context: main.cpp runs sample→extract→infer each cycle and needs to show results on an I2C
LCD/OLED (16x2 or SSD1306) and also emit a CSV line over Serial for validation logging.

Task: Create firmware/src/display.cpp/.h that:
1. Shows predicted class + confidence % on the LCD/OLED, refreshing without flicker.
2. Prints "timestamp,true_state,predicted_class,confidence,rms,thd" to Serial at 115200 baud
   each inference cycle (true_state comes from the relay state machine for validation).
```

### Prompt 7 — End-to-end validation harness (Track C)
```
Context: The ESP32 firmware prints CSV telemetry lines over serial as described above.

Task: Create validation/test_harness.py that:
1. Opens the serial port (pyserial), reads N cycles of telemetry.
2. Computes live accuracy, per-class precision/recall/F1, and a confusion matrix comparing
   true_state (ground truth from relay state) vs predicted_class.
3. Saves a report (CSV + confusion_matrix.png) to validation/reports/ with a timestamp.
4. Flags any class whose live on-device recall is more than 5 points below its offline
   (ml/train_model.py) test recall — this indicates a train/deploy skew worth investigating.
```

### Prompt 8 — Hardware safety checklist (Track: Hardware)
```
Context: 12V AC rig with ESP32, relay module, load/capacitor/inductor banks, voltage +
current sensors, opto-isolated relay drivers.

Task: Write hardware/safety_checklist.md covering: fuse ratings per bank, flyback diode/
snubber placement on inductive loads, opto-isolation verification steps, ground loop check
between sensor commons and ESP32 USB ground, and a pre-power-on checklist to run before
each test session.
```

---

## 6. Notes for you as the team

- Run Prompts 1→3 and 4→6 in parallel (different members), then Prompt 7 once both tracks produce real output — don't fake the confusion matrix from Track A alone; the "expected outcomes" slide claims >95% accuracy, so get it from live hardware, not just offline CSV, before you put that number in a report.
- Keep the "8 features" list identical across Prompts 1, 2, 3, and 5 — a mismatch here is the #1 way these projects break at integration time.
- The `model_data.h` byte array must exactly match what `convert_tflite.py` emits — regenerate it any time you retrain, and don't hand-edit it.
- In your results section, lead with `comparison_report.csv` as a table (model / accuracy / macro-F1 / latency / size), then state the MLP selection as a conclusion drawn from that table — e.g. "MLP matched or exceeded tree-based and kernel baselines on accuracy while being an order of magnitude smaller and faster at inference, making it the only candidate viable for on-device deployment." That's the evidence-based framing your proposal claims; the table is what makes it defensible rather than asserted.
- If your own measured MLP accuracy differs from the ~96.1% target once you actually run Prompt 2 on your real dataset, report the number you measured — don't force the figure to match a target from a different dataset/paper.

# Integration Guide: Real-Time 3-Phase Pipeline

> **Milestone:** 1 — Real 3-Phase Data Pipeline Foundation  
> **Tests:** 78 / 78 passing  
> **Last Updated:** 2026-09-20

This document describes how to connect, configure, and extend the acquisition-to-event pipeline introduced in Milestone 1.

---

## Pipeline Flow

```
SIGNAL SOURCE
    │
    ├── SimulationAdapter      (synthetic 3-phase generation)
    ├── CSVReplayAdapter       (offline replay from CSV)
    └── [Future] DAQAdapter    (real hardware — see §Hardware Boundary)
    │
    ▼
WaveformFrame (dsp/waveform_frame.py)
    timestamp_utc | sampling_rate_hz | L1/L2/L3 arrays
    nominal_frequency_hz | device_id | source_type
    │
    ▼
WaveformFrame.validate()
    ✓ sampling_rate_hz > 0
    ✓ L1, L2, L3 present
    ✓ All channels equal length
    ✓ No NaN / Infinite values
    ✓ No unphysical amplitude (|V| > 10 pu)
    │
    ├── INVALID → ValueError raised, frame discarded
    │
    ▼
process_waveform_frame()           (dsp/phase_processor.py)
    │
    ├── L1 → extract_enhanced_features() → 32-feature vector → MLP → PhaseMeasurement
    ├── L2 → extract_enhanced_features() → 32-feature vector → MLP → PhaseMeasurement
    └── L3 → extract_enhanced_features() → 32-feature vector → MLP → PhaseMeasurement
    │
    ▼
ThreePhaseEventEngine.process_frame()   (dsp/event_engine.py)
    │
    ├── Correlates simultaneous multi-phase disturbances
    ├── Emits PQEvent on state transition (Normal→Anomaly→Normal)
    └── affected_phases[] = e.g. ["L1", "L2"] for a partial sag
    │
    ▼
EventStore.save_event(PQEvent)     (storage/event_store.py)
    │
    ▼
REST API  (server.py :8500)
GET /api/events | /api/events/stats | /api/telemetry
```

---

## Module Reference

### `dsp/waveform_frame.py` — WaveformFrame

Canonical synchronized multi-channel data container. Hardware-independent.

```python
from dsp.waveform_frame import WaveformFrame
import numpy as np

frame = WaveformFrame(
    timestamp_utc=time.time(),
    sampling_rate_hz=5000.0,
    nominal_frequency_hz=50.0,
    source_type="csv_replay",      # "simulation" | "csv_replay" | "daq" | "pq_meter"
    device_id="METER_01",
    sequence_number=42,
    phases={
        "L1": np.array([...], dtype=np.float32),   # 1000 samples @ 5 kHz = 10 cycles
        "L2": np.array([...], dtype=np.float32),
        "L3": np.array([...], dtype=np.float32),
    }
)
ok, errors = frame.validate()
if not ok:
    raise ValueError(f"Invalid frame: {errors}")
```

**Key properties:**
- `frame.num_samples` — samples per channel
- `frame.duration_seconds` — window length in seconds
- `frame.duration_cycles` — window length in grid cycles
- `frame.available_phases` — sorted list of phases present
- `frame.to_dict()` / `WaveformFrame.from_dict(d)` — JSON serialization for REST API

**Supported `source_type` values:**

| Value | Meaning |
|---|---|
| `"simulation"` | `SimulationAdapter` — synthetic 3-phase generation |
| `"csv_replay"` | `CSVReplayAdapter` — offline CSV file |
| `"daq"` | Future: hardware DAQ adapter |
| `"esp32"` | Future: ESP32 serial stream adapter |
| `"pq_meter"` | Future: commercial PQ meter Modbus/IEC 61850 adapter |
| `"network"` | Received via POST `/api/ingest` |

---

### `dsp/acquisition_adapter.py` — Adapters

#### AcquisitionAdapter (abstract base)

```python
from dsp.acquisition_adapter import AcquisitionAdapter

class MyAdapter(AcquisitionAdapter):
    def connect(self) -> bool: ...
    def disconnect(self) -> None: ...
    def acquire_frame(self) -> Optional[WaveformFrame]: ...
```

#### SimulationAdapter

Synthesizes continuous, balanced 3-phase waveforms using the existing
`dsp/waveform_generator.py`. Supports per-phase disturbance injection.

```python
from dsp.acquisition_adapter import SimulationAdapter

sim = SimulationAdapter(
    sampling_rate_hz=5000.0,
    nominal_frequency_hz=50.0,
    window_samples=1000,          # 10 grid cycles
    device_id="SIM_01",
)
sim.connect()

# Inject a Sag on L2 only
sim.set_phase_disturbance("L2", "Sag")

frame = sim.acquire_frame()      # Returns WaveformFrame
sim.disconnect()
```

Supported disturbance classes for injection:

```
Normal | Sag | Swell | Interruption | Harmonics |
Transient | Flicker | Notch
```

#### CSVReplayAdapter

Replays pre-recorded measurements from a CSV file.

**Required CSV format:**

```csv
L1,L2,L3
0.001,0.002,-0.001
...
```

Column aliases `V_L1`, `V_L2`, `V_L3` are also accepted.

```python
from dsp.acquisition_adapter import CSVReplayAdapter

adapter = CSVReplayAdapter(
    csv_path="data/recording.csv",
    sampling_rate_hz=5000.0,
    nominal_frequency_hz=50.0,
    window_samples=1000,
    device_id="CSV_REPLAY_01",
)
adapter.connect()           # Raises ValueError if columns missing or sampling_rate <= 0

while True:
    frame = adapter.acquire_frame()   # Returns None at end of stream
    if frame is None:
        break
    # ... process frame ...

adapter.disconnect()
```

**Fail-clearly contract:**

| Condition | Exception |
|---|---|
| Missing L1/L2/L3 columns | `ValueError: missing required phase column` |
| `sampling_rate_hz <= 0` | `ValueError: invalid sampling_rate_hz` |
| `acquire_frame()` before `connect()` | `RuntimeError: before connect` |
| NaN in data slice | `ValueError: NaN values` |
| Inf in data slice | `ValueError: Infinite values` |

---

### `dsp/phase_processor.py` — Per-Phase DSP + ML

> **Important:** This module does NOT define a new model. It wires the existing
> trained MLP (`ml/models/model_weights_32.json`, EXP-003) into the 3-phase pipeline.

#### `process_waveform_frame(frame, phases_to_process=None)`

```python
from dsp.phase_processor import process_waveform_frame

# Returns Dict[str, PhaseMeasurement]
results = process_waveform_frame(frame)

for phase, pm in results.items():
    print(f"{phase}: {pm.classification} (conf={pm.confidence:.3f})")
    print(f"  RMS={pm.rms_voltage:.4f} pu  THD={pm.thd_2_11:.2f}%")
    print(f"  H1={pm.harmonics.get('h1', 0):.4f}")
```

#### `classify_phase_signal(signal, sample_rate)` → `(class, confidence, probabilities)`

Lower-level function: classifies a single 1D array without building a WaveformFrame.

#### ML inference chain

```
signal (np.ndarray, float32)
    ↓
extract_enhanced_features()          # dsp/enhanced_features.py
    ↓
32-element feature vector            # ordered by _MODEL_FEATURE_ORDER
    ↓
StandardScaler (scaler_mean / scaler_scale from model_weights_32.json)
    ↓
32 → 64 → 32 → 8 MLP (ReLU + Softmax)  # EXP-003, 99.40% test accuracy
    ↓
(class_label, confidence, probabilities[8])
```

#### Uncertainty gate

Predictions with `confidence < 0.60` (= `UNCERTAINTY_THRESHOLD`) are returned as:
```
classification = "UNCERTAIN"
```
This matches the safety gate in `firmware/src/inference.cpp`.

---

### `dsp/event_engine.py` — ThreePhaseEventEngine

```python
from dsp.event_engine import ThreePhaseEventEngine

engine = ThreePhaseEventEngine(
    classifier_fn=None,          # None = uses process_waveform_frame() internally
    confidence_threshold=0.60,
    max_correlation_window_sec=0.100
)

# Feed frames in sequence
for frame in adapter_stream:
    completed_events = engine.process_frame(frame)

# Access all completed events
for evt in engine.completed_events:
    print(evt.event_class, evt.affected_phases, evt.duration_ms)
```

**PQEvent fields:**

| Field | Type | Description |
|---|---|---|
| `event_id` | str | UUID |
| `start_time_utc` | float | Unix epoch |
| `end_time_utc` | float | Unix epoch |
| `duration_ms` | float | Duration in milliseconds |
| `event_class` | str | One of 8 PQ classes |
| `overall_confidence` | float | Softmax confidence |
| `affected_phases` | List[str] | e.g. `["L1", "L2"]` |
| `phase_metrics` | Dict[str, PhaseMeasurement] | Per-phase DSP measurements |
| `device_id` | str | Source device identifier |
| `source_type` | str | Acquisition source |

---

## Firmware Accuracy Disclosure

> This section documents known limitations to avoid misleading reporting.

### Inference type: heuristic fallback (NOT TFLite Micro)

`firmware/src/inference.cpp` **does not execute TFLite Micro** when the TFLite C++ runtime is absent. Instead it uses a rule-based heuristic:

```cpp
// Rule-based / linear classifier fallback for embedded simulation
// NOTE: This heuristic is strictly an uncalibrated fallback when TFLite Micro
// is linking or uninitialized. It does NOT define IEEE standards boundaries.
// All fallback decisions are explicitly flagged as uncertain.
res.is_uncertain = true;
```

This is correctly disclosed in the source. The Python MLP (`dsp/phase_processor.py`) is the authoritative inference path.

### Baseline THD: H3, H5, H7 only (not H2–H11)

`dsp/baseline_features.py` computes THD using only three harmonics (H3, H5, H7):

```python
# THD via Goertzel H1, H3, H5, H7
thd = (sqrt(h3^2 + h5^2 + h7^2) / h1) * 100
```

The trained MLP uses `dsp/enhanced_features.py` which computes the full H1–H11 Goertzel bank and stores `thd_2_11` (H2–H11), matching IEEE 519-2022.  
The baseline 8-feature THD is for backward compatibility and firmware parity only.

### Harmonic classification threshold: 5% THD

The heuristic fallback uses `THD > 5.0%` as the Harmonics detection threshold. This is an engineering approximation, not a mandatory IEEE 519-2022 PCC limit. IEEE 519 defines limits on the utility's PCC — not on individual measurements.

---

## Hardware Boundary

This milestone implements the **software side only**.

The intended final hardware path is:

```
REAL 3-PHASE AC MAINS
        ↓
Appropriately rated measurement/sensing front-end
  (e.g., voltage transformers, differential probes, optocouplers)
        ↓
Safe acquisition device
  (e.g., National Instruments DAQ, Dewetron PQ meter,
         Yokogawa WT3000, or custom isolated ADC board)
        ↓
DAQAdapter / PQMeterAdapter (Milestone 2)
        ↓
WaveformFrame (this layer — hardware independent)
        ↓
process_waveform_frame() → ThreePhaseEventEngine → EventStore
```

> ⚠️ **Do NOT connect an ESP32 ADC directly to mains voltage.**  
> The final acquisition front-end requires galvanic isolation, appropriate  
> voltage transformation, surge protection, and regulatory compliance.  
> No mains wiring instructions are provided in this repository.

---

## Quickstart: End-to-End Pipeline from CSV

```python
import numpy as np
import pandas as pd
from dsp.acquisition_adapter import CSVReplayAdapter
from dsp.phase_processor import process_waveform_frame
from dsp.event_engine import ThreePhaseEventEngine

adapter = CSVReplayAdapter("data/recording.csv", sampling_rate_hz=5000.0, window_samples=1000)
adapter.connect()  # Raises ValueError on bad CSV structure

engine = ThreePhaseEventEngine()

while True:
    frame = adapter.acquire_frame()
    if frame is None:
        break

    ok, errs = frame.validate()
    if not ok:
        print(f"Frame rejected: {errs}")
        continue

    results = process_waveform_frame(frame)
    for phase, pm in results.items():
        print(f"{phase}: {pm.classification} (conf={pm.confidence:.3f})")

    engine.process_frame(frame)

adapter.disconnect()

for evt in engine.completed_events:
    print(f"EVENT: {evt.event_class} on {evt.affected_phases} for {evt.duration_ms:.1f} ms")
```

---

## Test Coverage for This Integration Layer

| Test File | Tests | What Is Verified |
|---|---|---|
| `test_phase_processor.py` | 10 | Feature vector, MLP inference, uncertainty gate, per-phase measurements, invalid frame rejection |
| `test_acquisition_adapter.py` | 6 | SimulationAdapter stream, CSV replay happy path, 4× fail-clearly validation cases |
| `test_end_to_end_pipeline.py` | 6 | Full CSV→WaveformFrame→DSP→ML→PQEvent integration, per-phase sag detection, simulation adapter integration |
| **Total new in Milestone 1** | **22** | |
| **Full suite** | **78** | 100% passing |

# Operational Guide: Modes of Acquisition & Telemetry Streaming

This guide explains how to operate the Power Quality Monitoring system across different data acquisition sources, switch operational modes dynamically, ingest chunks, and monitor real-time telemetry.

---

## 1. Operational Acquisition Modes

The system architecture supports four distinct operational modes without modifying any downstream DSP, machine learning, or event storage components:

| Mode Identifier | Adapter Class | Description | Intended Use |
|---|---|---|---|
| `simulation` | `SimulationAdapter` | Continuous mathematical synthesis of balanced 3-phase waveforms with controllable disturbance injections. | Software development, UI testing, fault scenario benchmarking. |
| `mock_hardware` | `MockHardwareAdapter` | Synthesizes realistic 16-bit integer ADC counts, converts them through `ThreePhaseCalibration` (Counts $\to$ Volts $\to$ pu), models rail saturation clipping, and tracks hardware sequence counters. | Hardware interface validation, driver testing, protocol verification without physical equipment. |
| `replay` | `CSVReplayAdapter` / `WaveformFrame.load` | Streams recorded `.npz`, `.json`, or `.csv` waveform captures sequentially at realistic time cadences. | Regression testing against historically captured real-world field events. |
| `hardware` | `DAQAdapter` / `NetworkAdapter` / `SerialAdapter` | Connects to physical multi-channel DAQ devices or receives external raw ADC chunks via REST/socket. | Production grid monitoring on certified isolated transducer hardware. |

> [!NOTE]
> Until an isolated physical measurement front-end is connected and verified, the system must **NEVER** be reported as "real-world validated". It is classified as **Hardware-Agnostic & Acquisition-Ready**.

---

## 2. Dynamic Source Switching

The active acquisition source can be changed on-the-fly via the REST API without restarting the server:

### Switching via REST API
```bash
curl -X POST http://localhost:8500/api/adapter/source \
  -H "Content-Type: application/json" \
  -d '{"source": "mock_hardware", "sampling_rate": 5000.0}'
```

Response:
```json
{
  "status": "success",
  "active_source": "mock_hardware",
  "sampling_rate": 5000.0
}
```

### Checking System Health & Source Mode
```bash
curl http://localhost:8500/api/health
```

Response:
```json
{
  "status": "ok",
  "db_connected": true,
  "events_count": 42,
  "acquisition_source": "mock_hardware",
  "sampling_rate": 5000.0
}
```

---

## 3. Real-Time Ingestion Endpoints

### 3.1 Calibrated Voltage Ingestion (`POST /api/ingest`)
Accepts pre-calibrated floating-point values in per-unit (pu) or engineering Volts:

```bash
curl -X POST http://localhost:8500/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "sampling_rate": 5000.0,
    "timestamp": 1726830000.0,
    "device_id": "FIELD-DAQ-01",
    "channels": {
      "L1": [0.0, 0.05, 0.1, ...],
      "L2": [-0.86, -0.80, -0.75, ...],
      "L3": [0.86, 0.75, 0.65, ...]
    }
  }'
```

### 3.2 Raw ADC Chunk Ingestion (`POST /api/ingest/chunk`)
Accepts raw integer ADC counts from external microcontrollers or DAQ drivers, automatically running them through the calibrated conversion pipeline and saturation checker:

```bash
curl -X POST http://localhost:8500/api/ingest/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "STM32-DAQ-01",
    "sequence_id": 1042,
    "sampling_rate": 5000.0,
    "timestamp": 1726830001.25,
    "raw_counts": {
      "L1": [120, 1500, 3100, ...],
      "L2": [-2500, -1800, -900, ...],
      "L3": [2380, 300, -2200, ...]
    },
    "dropped_samples": 0
  }'
```

---

## 4. End-to-End Pipeline Execution

Regardless of whether samples originate from `SimulationAdapter`, `MockHardwareAdapter`, or `POST /api/ingest/chunk`, the execution path remains strictly identical:

1. **Ingestion & Validation**: Channel length consistency, NaN/Inf checks, sequence gap detection, and saturation flags.
2. **Circular Buffering**: `MultiChannelRingBuffer` accumulates synchronized continuous samples and extracts sliding analysis windows (e.g., 200 ms / 1000 samples at 5 kHz with 50% overlap).
3. **Feature Extraction & DSP**: `PhaseProcessor` extracts 32 statistical, higher-order spectral ($H_1\text{--}H_{11}$), and shape features per phase.
4. **Machine Learning Inference**: Evaluates the trained Compact MLP (`model_weights_32.json`) forward pass per phase; applies uncertainty gating ($P(\text{class}) \ge 0.60$).
5. **Event Aggregation**: `ThreePhaseEventEngine` correlates single-phase and multi-phase disturbances, monitors nadir/peak duration, merges overlapping windows, and avoids spurious duplicates.
6. **Persistence**: Saves confirmed `PQEvent` records into SQLite (`data/pq_events.db`).
7. **Telemetry**: Broadcasts live waveform snapshots and event notifications via Server-Sent Events (`/api/telemetry/stream`) to connected dashboard clients.

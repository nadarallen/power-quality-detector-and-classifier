# Canonical Waveform Acquisition Format Specification

This document defines the canonical file and interchange formats for raw and calibrated three-phase electrical waveforms within the Power Quality Monitoring system.

A single canonical format enables seamless capture and replay across:
1. Physical Data Acquisition Hardware (DAQ)
2. Synthetic laboratory simulation (`SimulationAdapter`)
3. Tabular recording files (`CSVReplayAdapter`)
4. Synthetic or captured benchmark datasets (`.npz` files)

---

## 1. Dual Representation: JSON & NPZ

The platform provides two interchangeable serialization backends via `WaveformFrame.save(filepath)` and `WaveformFrame.load(filepath)`:

| Format | File Extension | Primary Use Case | Advantages |
|---|---|---|---|
| **JSON Interchange** | `.json` | REST API, debug inspections, metadata-rich archives | Human-readable, schema-validatable, ubiquitous language support |
| **NumPy Compressed** | `.npz` | High-frequency continuous logging, mass offline benchmarks | Fast zero-copy binary deserialization, 10x smaller file size, native Python array storage |

---

## 2. Format Specifications

### 2.1 JSON Format Specification

The JSON format preserves complete trace arrays alongside per-channel calibration and acquisition metadata:

```json
{
  "frame_id": "frame_1726830000125_L1L2L3",
  "sampling_rate": 5000.0,
  "timestamp": 1726830000.125,
  "nominal_voltage": 1.0,
  "device_id": "MOCK-3PH-001",
  "dropped_samples_count": 0,
  "is_clipped": false,
  "calibration_id": "DEFAULT_3PH_CALIB",
  "metadata": {
    "source": "mock_hardware",
    "adc_resolution_bits": 16,
    "input_range_volts": 10.0
  },
  "channel_metadata": {
    "L1": {
      "channel_id": "L1",
      "units": "pu",
      "scale_factor": 1.0,
      "offset": 0.0,
      "phase_angle_nominal_deg": 0.0,
      "calibrated": true,
      "sensor_type": "PT",
      "extra": {"gain": 0.000305, "sensor_ratio": 3.39}
    },
    "L2": {
      "channel_id": "L2",
      "units": "pu",
      "scale_factor": 1.0,
      "offset": 0.0,
      "phase_angle_nominal_deg": 120.0,
      "calibrated": true,
      "sensor_type": "PT",
      "extra": {"gain": 0.000305, "sensor_ratio": 3.39}
    },
    "L3": {
      "channel_id": "L3",
      "units": "pu",
      "scale_factor": 1.0,
      "offset": 0.0,
      "phase_angle_nominal_deg": 240.0,
      "calibrated": true,
      "sensor_type": "PT",
      "extra": {"gain": 0.000305, "sensor_ratio": 3.39}
    }
  },
  "channels": {
    "L1": [0.012, 0.089, 0.165, ...],
    "L2": [-0.854, -0.791, -0.720, ...],
    "L3": [0.842, 0.702, 0.555, ...]
  }
}
```

### 2.2 Compressed NPZ Specification

The `.npz` container stores multi-dimensional numerical arrays as raw float64 binary blocks, with metadata serialized in a JSON-encoded string array:

- **`L1`**: 1D float64 array of length $N$
- **`L2`**: 1D float64 array of length $N$
- **`L3`**: 1D float64 array of length $N$
- **`__meta__`**: 0-dimensional or scalar array containing JSON string of top-level frame attributes (`sampling_rate`, `timestamp`, `nominal_voltage`, `device_id`, `dropped_samples_count`, `is_clipped`, `calibration_id`, `metadata`, `channel_metadata`).

---

## 3. Mandatory Validation Rules

Upon loading any persisted capture file, the acquisition validation engine enforces:
1. **Channel Synchronization**: All channel arrays (`L1`, `L2`, `L3`) must possess strictly identical length ($N$).
2. **Numerical Validity**: Zero NaN (Not-a-Number) and zero Inf (Infinity) values allowed in any sample.
3. **Sampling Rate**: Must be positive and non-zero ($f_s > 0$).
4. **Saturation Indication**: If digital clipping occurred during acquisition, `is_clipped` is set to `true`.
5. **Data Discontinuity**: Sequence jumps or buffer overruns must be reported in `dropped_samples_count`.

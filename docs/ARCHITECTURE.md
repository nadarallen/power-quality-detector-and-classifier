# Architecture: Real-Time Three-Phase Power Quality Monitoring System

> **Last Updated:** 2026-09-20  
> **Test Suite:** 58 / 58 passing  
> **Git Branch:** `main`

---

## System Overview

This system evolves from a single-phase research ML benchmark into a **real-time, three-phase power quality monitoring and AI classification platform**. The architecture is a production-grade streaming pipeline with strict standards compliance, embedded firmware parity, and a REST API-backed live dashboard.

---

## Full Pipeline Diagram

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │              SIGNAL ACQUISITION LAYER                                   │
 │                                                                         │
 │  Hardware (3-phase DAQ/ESP32) ──► Safety Front-End (galvanic ISO,       │
 │  Zener clamps, RC snubbers)   ──► 5 kHz ADC ISR (200 µs per sample)    │
 │                                                                         │
 │  OR: SimulationAdapter (three 120°-spaced synthetic sinusoids)           │
 │  OR: CSVReplayAdapter  (offline waveform replay from CSV files)          │
 │  OR: POST /api/ingest  (WaveformFrame JSON from remote edge devices)     │
 │                                                                         │
 │  ─────────────────────────────────────────────────────────────────────  │
 │  Output: WaveformFrame  (dsp/waveform_frame.py)                         │
 │          { timestamp_utc, sampling_rate_hz=5000, L1/L2/L3 arrays,       │
 │            device_id, source_type, is_valid, validation_errors }        │
 └──────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │              WAVEFORM VALIDATION                                         │
 │                                                                         │
 │  WaveformFrame.validate():                                              │
 │   ✓ sampling_rate_hz > 0                                                │
 │   ✓ L1, L2, L3 all present                                             │
 │   ✓ Channel length sync (all same sample count)                         │
 │   ✓ No NaN / Inf values                                                 │
 │   ✓ No unphysical amplitude (|V| > 10 pu)                              │
 └──────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │              DSP & FEATURE EXTRACTION                                   │
 │                                                                         │
 │  Per-phase, independently applied:                                      │
 │                                                                         │
 │  Track A — 8 Baseline Features (dsp/baseline_features.py)              │
 │    RMS, Peak, Crest Factor, Goertzel THD(2-11), Duration,              │
 │    Dominant Frequency, System Frequency, SNR                            │
 │                                                                         │
 │  Track B — 32 Enhanced Features (dsp/enhanced_features.py)             │
 │    H1–H11 Goertzel magnitudes + Spectral Centroid, Bandwidth,          │
 │    Entropy, Flatness, Kurtosis, Skewness, Spectral Peak                │
 │                                                                         │
 │  Standards Measurement (dsp/standards_detector.py)                     │
 │    Half-cycle sliding RMS (10 ms window, U_rms(1/2))                   │
 │    Residual RMS < 0.10 pu → Interruption (IEEE 1159 Clause 3.1.34)    │
 │    FFT H2–H11 with THD_2_11 computation                                │
 └──────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │              ML CLASSIFIER                                              │
 │                                                                         │
 │  Compact MLP (32 → 64 → 32 → 8), EXP-003 validated:                   │
 │    • Parameters:  4,424                                                 │
 │    • FP32 footprint: 17.28 KB                                           │
 │    • Test accuracy: 99.40%                                              │
 │    • Macro F1: 0.9927                                                   │
 │    • Interruption recall: 100.00%                                       │
 │    • Inference latency: 325.7 µs                                        │
 │    • UNCERTAIN gate: confidence < 60% → escalated review               │
 │                                                                         │
 │  Heuristic fallback (physics-based, no model file required):           │
 │    RMS < 0.10 → Interruption                                           │
 │    0.10–0.90 → Sag                                                      │
 │    > 1.10 → Swell                                                       │
 │    THD > 5% → Harmonics                                                │
 │    else Normal                                                          │
 └──────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │              THREE-PHASE EVENT ENGINE (dsp/event_engine.py)            │
 │                                                                         │
 │  ThreePhaseEventEngine:                                                 │
 │   • Tracks per-phase lifecycle: L1, L2, L3 independently               │
 │   • Multi-window deduplication via seen_ids set                        │
 │   • Cross-phase correlation: merges simultaneous disturbances           │
 │   • PQEvent emitted when state transitions Normal→Anomaly→Normal       │
 │   • active_events_by_phase tracks open events per phase                │
 │   • completed_events accumulates closed events for persistence         │
 │                                                                         │
 │  PQEvent fields:                                                        │
 │   event_id, start_time_utc, end_time_utc, duration_ms, event_class,   │
 │   overall_confidence, affected_phases[], phase_metrics{},              │
 │   device_id, source_type, is_active                                    │
 │                                                                         │
 │  PhaseMeasurement fields:                                              │
 │   phase, rms_voltage, min_rms, max_rms, thd_2_11,                     │
 │   fundamental_frequency, peak_voltage, crest_factor, harmonics{},     │
 │   classification, confidence                                            │
 └─────────┬────────────────────────────────────────────────┬─────────────┘
           │                                                │
           ▼                                                ▼
 ┌─────────────────────────────┐        ┌──────────────────────────────────┐
 │ PERSISTENCE                 │        │  REST API  (server.py :8500)     │
 │ (storage/event_store.py)    │        │                                  │
 │                             │        │  GET  /api/health                │
 │ SQLite database:            │        │  GET  /api/events                │
 │  pq_events table            │        │  GET  /api/events/<id>           │
 │  - event_id (PK)            │        │  GET  /api/events/stats          │
 │  - start_time_utc           │        │  GET  /api/telemetry             │
 │  - end_time_utc             │        │  POST /api/ingest                │
 │  - duration_ms              │        │  POST /api/simulation/disturbance│
 │  - event_class              │        │  POST /api/predict               │
 │  - overall_confidence       │        │  GET  /api/classes               │
 │  - affected_phases (JSON)   │        └───────────────────┬──────────────┘
 │  - phase_metrics_json       │                            │
 │  - device_id, source_type   │                            ▼
 │                             │        ┌──────────────────────────────────┐
 │ Indexes:                    │        │  LIVE DASHBOARD (web/index.html) │
 │  idx_event_time             │        │                                  │
 │  idx_event_class            │        │  • 3-Phase Grid Bus Bar          │
 │                             │        │    L1 (0°) / L2 (-120°) / L3    │
 │ Methods:                    │        │  • Events persisted counter      │
 │  save_event(PQEvent)        │        │  • System status badge           │
 │  get_event(id)              │        │  • CRT Oscilloscope (HTML5)      │
 │  query_events(...)          │        │  • FFT Spectrum Analyzer         │
 │  get_event_stats()          │        │  • ML probability bars           │
 └─────────────────────────────┘        │  • Disturbance injection UI      │
                                        │  • Event experiment log          │
                                        └──────────────────────────────────┘
```

---

## Module Reference

| Module | File | Role |
|---|---|---|
| **WaveformFrame** | [`dsp/waveform_frame.py`](../dsp/waveform_frame.py) | Canonical 3-phase synchronized data frame with validation and JSON serialization. Ref: [IEEE 1159.3-2025 COMTRADE schema](WAVEFORM_STANDARD_AUDIT.md) |
| **AcquisitionAdapter** | [`dsp/acquisition_adapter.py`](../dsp/acquisition_adapter.py) | Abstract base + `SimulationAdapter` (continuous per-phase disturbance injection) + `CSVReplayAdapter` |
| **DSP Feature Engine** | [`dsp/baseline_features.py`](../dsp/baseline_features.py) | 8-feature Track A extraction. Exact parity with firmware C++ Goertzel resonators. [Parity tests](../tests/test_firmware_parity.py) |
| **Enhanced Features** | [`dsp/enhanced_features.py`](../dsp/enhanced_features.py) | 32-feature Track B: H1–H11, spectral moments, windowed event duration |
| **Standards Detector** | [`dsp/standards_detector.py`](../dsp/standards_detector.py) | Half-cycle sliding RMS (U_rms(1/2)), IEEE 1159 interruption threshold, FFT H2–H11. Ref: [IEEE 1159-2019 Clause 3.1.34](IEEE_ALIGNMENT_AUDIT.md) |
| **Event Engine** | [`dsp/event_engine.py`](../dsp/event_engine.py) | `ThreePhaseEventEngine`: state machine, cross-phase correlation, `PQEvent` lifecycle. `get_active_events()` for live monitoring |
| **EventStore** | [`storage/event_store.py`](../storage/event_store.py) | Embedded SQLite persistence, phase-indexed queries, `get_event_stats()` with `by_class` and `by_phase` breakdown |
| **Realtime Pipeline** | [`pipeline/realtime_pipeline.py`](../pipeline/realtime_pipeline.py) | Streaming engine: auto-connects adapter, calls `validate()`, feeds engine, persists events, fires callbacks |
| **REST Server** | [`server.py`](../server.py) | HTTP server: serves dashboard + exposes `/api/events`, `/api/ingest`, `/api/telemetry` |
| **Live Dashboard** | [`web/index.html`](../web/index.html) + [`web/app.js`](../web/app.js) | CRT oscilloscope UI with 3-phase bus bar polling (`/api/events/stats` + `/api/telemetry`) every 2s |
| **Embedded Firmware** | [`firmware/src/`](../firmware/src/) | C++ DSP + TFLite Micro inference. `model_weights_32.h` for zero-dependency 32-feature MLP forward pass |

---

## 8 Immutable Physical Classes

| Class | IEEE Standard | Detection Rule |
|---|---|---|
| **Normal** | Baseline | RMS ∈ [0.95, 1.05] pu, THD < 1.5% |
| **Voltage Sag** | IEEE 1159 §3.1.53 | Half-cycle RMS ∈ [0.10, 0.90) pu, ≥0.5 cycles |
| **Voltage Swell** | IEEE 1159 §3.1.58 | Half-cycle RMS ∈ (1.10, 1.80] pu, ≥0.5 cycles |
| **Interruption** | IEEE 1159 §3.1.34 | Residual half-cycle RMS < 0.10 pu, ≥0.5 cycles |
| **Harmonics** | IEEE 519-2022 | THD_2_11 > 5.0% from Goertzel H2–H11 |
| **Oscillatory Transient** | IEEE 1159 §3.1.66 | Sub-cycle damped oscillation 350–750 Hz |
| **Flicker** | IEEE 1453/IEC 61000-4-15 | Envelope mod ΔV/V ∈ [1%,10%] at fm ∈ [0.1,30 Hz] |
| **Notch** | IEEE 1159 §3.1.50 | Localized crest factor depression at commutation angle |

> ⚠️ Detection thresholds above are physics-calibrated **engineering detectors**. They should not be presented as mandatory IEEE PCC compliance limits.

---

## Test Coverage Map

| Test File | Count | What Is Tested |
|---|---|---|
| `test_classification_rules.py` | 11 | IEEE interruption boundary, THD analytical, harmonic phases |
| `test_waveform_acceptance.py` | 26 | IEEE 1159.3 metadata, Nyquist, buffers |
| `test_firmware_parity.py` | 6 | Python↔C++ Goertzel parity, H1–H11, THD_2_11, MLP forward pass |
| `test_waveform_frame.py` | 3 | 3-phase frame creation, sync validation, NaN/Inf detection |
| `test_acquisition_adapter.py` | 2 | SimulationAdapter generation, CSVReplayAdapter |
| `test_event_engine.py` | 2 | Per-phase tracking, cross-phase multi-event correlation |
| `test_event_store.py` | 2 | SQLite save/retrieve, phase/class filtering, stats |
| `test_realtime_pipeline.py` | 2 | Normal stream, Sag lifecycle detection end-to-end |
| `test_server_endpoints.py` | 3 | `/api/health`, `/api/events`, `/api/ingest` |
| `test_dsp_features.py` | 1 | Baseline feature preservation |
| **Total** | **58** | **100% passing** |

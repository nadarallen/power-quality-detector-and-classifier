# Automated Test Suite Guide & Registry

**Subsystem:** Automated Testing & Continuous Verification  
**Test Runner:** `pytest` (configured in `pytest.ini`)  
**Current Test Metrics:** 302 collected, 300 passed, 2 skipped, 0 failed (~7.8s)  

---

## 1. Test Suite Architecture

The test suite provides exhaustive coverage across physical disturbance generation, numerical DSP parity, streaming ingestion, multi-window event aggregation, and API endpoints:

```
+-----------------------------------------------------------------------------+
|                      AUTOMATED TEST SUITE MATRIX (300 PASSING)              |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. Physical Disturbance & Dataset Tests (Gates 3A–3X)                      |
|     - test_gate3a_60hz_compatibility.py   --> 60-Hz WSCC 9-Bus Model Checks |
|     - test_gate3b_normal_dataset.py       --> Normal Baseline Frames (1,152)|
|     - test_gate3d_sag.py / test_gate3e... --> Sag Implementation & Dataset  |
|     - test_gate3g_swell.py / test_gate3h. --> Swell Implementation & Dataset|
|     - test_gate3j_interruption.py / 3k... --> Interruption Pipeline & Audit |
|     - test_gate3m_harmonics.py / 3n...    --> Harmonics H2–H11 & THD Checks |
|     - test_gate3p_flicker.py / 3q...      --> Flicker Sidebands & Mod Depth |
|     - test_gate3s_notch.py / 3t / 3u...   --> Thyristor Commutation Notches |
|     - test_gate3v_transient.py / 3w / 3x. --> RLC Oscillatory Transients    |
|                                                                             |
|  2. Digital Signal Processing & Numerical Parity                            |
|     - test_enhanced_features.py           --> 32-Feature Contract Extraction|
|     - test_snr_phase_invariance.py        --> Orthogonal Projection SNR     |
|     - test_simulink_parity.py             --> MATLAB <-> Python Parity Check|
|     - test_standards_detector.py          --> Independent Physical Rules    |
|     - test_waveform_frame.py              --> 3-Phase Synchrony & NaN Guards|
|                                                                             |
|  3. Streaming Pipeline, Ring Buffer & Storage                               |
|     - test_realtime_pipeline.py           --> Sliding Window Ingestion      |
|     - test_ring_buffer.py                 --> Circular Buffer Wraparound    |
|     - test_multi_window_merging.py        --> Event Lifecycles & Merging    |
|     - test_simulink_integration.py        --> HTTP Chunk Streaming Bridge   |
|     - test_server_endpoints.py            --> REST API, SSE & Event Query   |
|     - test_event_store.py                 --> SQLite Persistence & Querying |
|                                                                             |
|  4. Supporting Parity Tests                                                 |
|     - test_firmware_parity.py             --> Goertzel C++ Parity Checks    |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 2. Test Execution Instructions

```bash
# Run the entire test suite
pytest -v

# Run targeted physical disturbance dataset tests
pytest tests/test_gate3*.py -v

# Run targeted DSP feature extraction & parity tests
pytest tests/test_enhanced_features.py tests/test_snr_phase_invariance.py tests/test_simulink_parity.py -v

# Run streaming pipeline and server tests
pytest tests/test_realtime_pipeline.py tests/test_simulink_integration.py tests/test_server_endpoints.py -v
```

---

## 3. Test Invariants & Strict Rules

1. **No Artificial Greening:** Tests must not be altered, relaxed, or disabled merely to pass.
2. **Deterministic Verification:** All tests use fixed random seeds (`seed=42`) and deterministic mathematical models.
3. **Decoupled Verification:** Physical disturbance tests verify ground truth against scenario controller metadata, never against ML predictions.

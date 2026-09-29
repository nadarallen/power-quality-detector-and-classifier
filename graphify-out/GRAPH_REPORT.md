# Graph Report - .  (2026-09-30)

## Corpus Check
- 142 files · ~429,650 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 810 nodes · 1412 edges · 42 communities (36 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40

## God Nodes (most connected - your core abstractions)
1. `WaveformFrame` - 72 edges
2. `generate_pqd_waveform()` - 36 edges
3. `ChannelCalibration` - 30 edges
4. `EventStore` - 30 edges
5. `PQEvent` - 26 edges
6. `RealtimePQPipeline` - 24 edges
7. `SimulationAdapter` - 23 edges
8. `ThreePhaseCalibration` - 23 edges
9. `ThreePhaseEventEngine` - 23 edges
10. `MultiChannelRingBuffer` - 23 edges

## Surprising Connections (you probably didn't know these)
- `RealtimePQPipeline` --uses--> `AcquisitionAdapter`  [INFERRED]
  pipeline/realtime_pipeline.py → dsp/acquisition_adapter.py
- `PQDServerRequestHandler` --uses--> `SimulationAdapter`  [INFERRED]
  server.py → dsp/acquisition_adapter.py
- `PQDServerRequestHandler` --uses--> `HardwareAdapter`  [INFERRED]
  server.py → dsp/acquisition_adapter.py
- `PQDServerRequestHandler` --uses--> `MockHardwareAdapter`  [INFERRED]
  server.py → dsp/acquisition_adapter.py
- `EventStore` --uses--> `PhaseMeasurement`  [INFERRED]
  storage/event_store.py → dsp/event_engine.py

## Import Cycles
- None detected.

## Communities (42 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (60): classify_phase_signal(), _features_to_vector(), _get_classifier(), _heuristic_classify(), MLPClassifier, process_waveform_frame(), ndarray, Phase Processor — Per-Phase DSP + ML Integration Layer… (+52 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (39): PQDFeatures, PQDFeatures32, initDisplay(), sendSerialTelemetry(), updateDisplay(), computeGoertzelMagnitude(), PQDFeatures, PQDFeatures32 (+31 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (33): BARC_DATASET_SAMPLES, CLASSES, computeQuickRmsThd(), currentWaveform, DISTURBANCE_COLORS, experimentLog, extractFeaturesDSP(), generateWaveform() (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (38): analyze_harmonic_spectrum(), classify_harmonic_disturbance(), classify_interruption_duration(), compute_windowed_rms(), detect_interruption(), measure_windowed_event_duration(), Any, ndarray (+30 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (28): Any, Serializes frame metadata and optionally waveform arrays to dictionary., Reconstructs WaveformFrame from dictionary., Saves canonical waveform frame to .npz or .json format., PQDServerRequestHandler, Executes forward pass of the Compact Keras MLP model (Dense 64 -> Dense 32 ->…, relu(), run_python_ml_inference() (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (14): DAQAdapter, HardwareAdapter, NetworkAdapter, PQMeterAdapter, Abstract base class for physical data acquisition devices. Encapsulates…, Interface for multi-channel USB/PCIe DAQ hardware (e.g. LabJack, NI DAQ)., Interface for Serial/UART streaming frontends (e.g. isolated MCU / optical USB…, Interface for Ethernet / TCP / UDP / Modbus TCP / MQTT streaming… (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (33): generate_pqd_waveform(), Any, ndarray, Generates a single 1000-sample discrete waveform for a specified disturbance.…, parametrize, measure_fundamental_frequency(), measure_window_rms(), ndarray (+25 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (31): @babel/core, expo, expo-status-bar, firebase, dependencies, expo, expo-status-bar, firebase (+23 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (20): ndarray, Converts raw integer ADC samples to a validated per-unit WaveformFrame using…, Fetches the next time-synchronized WaveformFrame., Returns list of phase identifiers available in this frame., Executes strict physical and structural integrity verification: 1. Checks…, Loads canonical waveform frame from .npz or .json format., Canonical multi-channel, time-synchronized waveform frame. Guarantees…, Returns the number of samples per channel (assuming synchronized channels). (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (23): MultiChannelRingBuffer, ndarray, Returns True if enough samples have accumulated for at least one analysis…, Extracts the next window of length `window_size` and advances read pointer by…, Resets the ring buffer state., Continuous multi-channel sliding ring buffer for 3-phase electrical waveforms., Current number of unconsumed samples remaining in the buffer., Total number of WaveformFrame windows yielded by get_next_window(). (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (22): generate_plotly_waveform_bw(), get_disturbance_metrics(), init_session_state(), main(), Power Quality Disturbance (PQD) Classifier — Minimalist Python Frontend…, Initializes Streamlit session state variables with default telemetry logs., Generates a 50Hz AC voltage waveform Plotly figure for a specified disturbance…, Calculates RMS, THD %, duration, and confidence metrics for a given disturbance… (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (14): Connection, Row, EventStore, Any, Fetches a single event by ID., Returns the total count of events matching filter criteria., Queries recorded events with filtering and pagination., Calculates aggregate event statistics by disturbance class and phase. (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (20): MockHardwareAdapter, Deterministic hardware mock simulating physical 3-phase acquisition hardware:…, Configures disturbance condition for mock hardware channel., Hardware Acquisition, Calibration, and Mock Integration Tests…, Verify MockHardwareAdapter emits valid, time-synchronized 3-phase frames., Verify hardware adapter tracks sequence gaps and dropped samples correctly., Verify hardware saturation simulation triggers is_clipped flag and validation…, Verify complete end-to-end execution: MockHardwareAdapter -> RealtimePQPipeline… (+12 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (23): backgroundColor, foregroundImage, adaptiveIcon, package, expo, android, assetBundlePatterns, icon (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (11): ABC, AcquisitionAdapter, Acquisition Adapter Interface & Baseline Adapters…, Abstract base class for all power quality waveform acquisition sources., Initializes connection to signal source., Closes connection to signal source., Multi-Channel Continuous Ring Buffer & Sliding Window Slicer…, Canonical Three-Phase Waveform Representation… (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (17): CSVReplayAdapter, Replays pre-recorded continuous multi-phase electrical waveforms from CSV…, Opens the CSV file and validates its structure. Raises ------ FileNotFoundError…, Returns the next WaveformFrame window from the replay stream. Returns None when…, _make_normal_csv(), Unit Tests for Acquisition Adapters (Simulation & CSV Replay)…, connect() must raise ValueError if L1/L2/L3 columns are absent., connect() must raise ValueError if sampling_rate_hz <= 0. (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (17): Real-time state machine that ingests WaveformFrames, extracts per-phase DSP…, Parameters ---------- classifier_fn : callable, optional Custom classifier:…, Returns unique currently active unclosed PQEvents across all phases., ThreePhaseEventEngine, _make_sinusoid(), Integration Tests for Multi-Window Disturbance Merging & Lifecycle…, If disturbance class changes (e.g. Sag transitioning directly into Swell), the…, Section 17: Disturbance starts on L1, then spreads to L2 in the next window.… (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.19
Nodes (16): extract_baseline_features(), goertzel_magnitude(), ndarray, Baseline DSP Feature Extraction (Track: Preservation)…, Computes DFT magnitude at target_freq using the Goertzel algorithm. Identical…, Extracts the 8 standard baseline features from a 1D waveform array., compute_harmonic_profile(), compute_spectral_features() (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (10): ndarray, Direct end-to-end transformation: raw ADC counts → per-unit (pu)., Converts per-unit voltage back to engineering Volts., Synthesizes realistic raw ADC counts from per-unit waveform (for hardware…, Evaluates whether raw ADC samples reached the hardware clipping rails. Returns…, Retrieves calibration for the specified phase., Converts raw ADC arrays for all phases to per-unit float32 arrays., Checks clipping and rail saturation on all raw phase arrays. (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.16
Nodes (14): PhaseMeasurement, PQEvent, Three-Phase Power Quality Event Engine & Multi-Phase Correlator…, Per-phase electrical metrics captured during a disturbance., Unified Power Quality Disturbance Event representation. Tracks both system-…, True if disturbance concurrently affects more than one phase., Computes maximum deviation from nominal 1.0 pu or highest THD across affected…, Embedded Power Quality Event Store & Persistence Layer… (+6 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (13): AcquisitionState, Standard operational states for hardware and simulated acquisition adapters., ChannelCalibration, Hardware Acquisition Calibration & Scaling Abstraction Layer…, Calibration parameters for an individual acquisition channel (voltage or…, Maximum possible count for this ADC resolution., Minimum possible count for this ADC resolution., Volts at the ADC pin per discrete ADC quantization step. (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.21
Nodes (10): styles, EventCard(), styles, MetricGrid(), styles, StatusHeroCard(), styles, LiveMonitoringScreen() (+2 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (16): cpp_goertzel_simulation(), ndarray, Automated Test for Python <-> C++ Firmware Parity (Goertzel & DSP Features)…, Verify comprehensive H2, H3, H5, H7, H9, H11 and THD_2_11 parity between Python…, Verify exact equivalence between Python MLP and C++ model_weights_32.h forward…, Directly compiles feature_extraction.cpp and inference.cpp with native g++ and…, Exact simulation of firmware/src/feature_extraction.cpp…, Verify Goertzel magnitude parity on a pure 1.0 pu 50 Hz fundamental. (+8 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (9): Synthesizes continuous, time-synchronized three-phase (L1, L2, L3) waveforms…, Configures disturbance state for a specific phase (e.g. set L2 to 'Sag') or…, SimulationAdapter, ChannelMetadata, Metadata and calibration parameters for an individual acquisition channel., Switches the active acquisition adapter (simulation vs mock_hardware)., set_active_source(), Verify SimulationAdapter connects and streams valid 3-phase frames. (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.21
Nodes (8): Real-time pipeline module for 3-phase PQ monitoring., Runs the pipeline for a fixed number of frames (useful in batch/tests)., Continuous streaming pipeline for 3-phase power quality analysis., Processes a single synchronized multi-channel WaveformFrame. Validates frame,…, RealtimePQPipeline, Unit and integration tests for RealtimePQPipeline., test_realtime_pipeline_disturbance_detection(), test_realtime_pipeline_normal_stream()

### Community 25 - "Community 25"
Cohesion: 0.20
Nodes (7): _get_phase_processor(), ndarray, Classifies an individual phase waveform. Priority order: 1. External…, Builds a PhaseMeasurement from the enhanced DSP feature set. Uses…, Processes an incoming multi-channel WaveformFrame. Returns any newly completed…, Returns the dsp.phase_processor module (lazy, loaded once)., Updates event end time and duration in milliseconds.

### Community 26 - "Community 26"
Cohesion: 0.24
Nodes (9): Calibrated PQD Waveform Generator --------------------------------- Generates…, extract_waveform_params_from_row(), generate_split_waveforms(), main(), Prepare Raw Waveform Dataset for 1D CNN & Deep Learning Models…, Verifies the integrity of all generated waveform splits., Extracts calibrated physical generation parameters from a dataset split row,…, Generates and saves 1000-sample raw waveforms for a given split name. Uses fast… (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.27
Nodes (10): format_callout_text(), get_curated_params(), main(), plot_consolidated_grid(), plot_single_waveform(), IEEE Std 1159 & IEEE Std 519 Waveform Visualization & Parameter Annotation…, Plots standard 3-panel representation with physical overlay and parameters., Plots a consolidated 8-panel grid showing all disturbance classes together. (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.33
Nodes (8): build_compact_keras_mlp(), load_dataset(), main(), measure_single_inference_latency(), plot_and_save_cm(), Multi-Model Comparison Bench — PQD Disturbance Classification…, Builds compact Keras MLP: 2 hidden layers (64, 32 units), ReLU, Softmax. Target…, Measures average single-sample inference latency in microseconds (us).

### Community 29 - "Community 29"
Cohesion: 0.33
Nodes (8): convert_keras_to_tflite(), convert_pickle_mlp_to_header(), export_c_header(), main(), TFLite Micro Model Conversion Script (Track A -> Track B Bridge)…, Fallback C header exporter for Sklearn MLP model weights when TF/Keras is…, Converts raw tflite model bytes into a C array header file., Converts Keras H5 MLP model to quantized TFLite model and C header.

### Community 30 - "Community 30"
Cohesion: 0.29
Nodes (4): Any, Serializes calibration profile to a JSON-compatible dictionary., Reconstructs ChannelCalibration from dictionary., Serializes three-phase calibration profile.

### Community 31 - "Community 31"
Cohesion: 0.32
Nodes (7): _make_frame(), Unit Tests for ThreePhaseEventEngine & Multi-Phase Correlator…, Builds a raw sinusoidal 3-phase frame for state machine testing. Amplitude <…, State machine: single-phase sag on L2 → open → extend → close, correct metadata., State machine: simultaneous sag on L1+L2 merges into one correlated event., test_event_engine_multi_phase_correlation(), test_event_engine_single_phase_event()

### Community 32 - "Community 32"
Cohesion: 0.40
Nodes (5): load_and_prepare_barc_dataset(), main(), DataFrame, Power Quality Disturbance (PQD) Dataset Loader & Standardizer…, Loads BARC DATA.csv, validates columns, maps headers to standardized names, and…

### Community 33 - "Community 33"
Cohesion: 0.53
Nodes (5): forward_pass(), main(), Reproduce and Lock Baseline Model Evaluation…, relu(), softmax()

### Community 34 - "Community 34"
Cohesion: 0.60
Nodes (4): get_candidate_models(), measure_latency(), Enhanced Classical ML Benchmark & 5-Fold Cross-Validation (Phase 10 & 11)…, run_benchmark()

## Knowledge Gaps
- **59 isolated node(s):** `class_id`, `class_name`, `confidence`, `is_uncertain`, `class_id` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WaveformFrame` connect `Community 8` to `Community 0`, `Community 35`, `Community 4`, `Community 5`, `Community 36`, `Community 9`, `Community 12`, `Community 14`, `Community 15`, `Community 16`, `Community 19`, `Community 20`, `Community 23`, `Community 24`, `Community 25`, `Community 31`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Why does `generate_pqd_waveform()` connect `Community 6` to `Community 0`, `Community 3`, `Community 8`, `Community 14`, `Community 17`, `Community 22`, `Community 23`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `ChannelCalibration` connect `Community 20` to `Community 5`, `Community 12`, `Community 14`, `Community 15`, `Community 18`, `Community 23`, `Community 30`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `WaveformFrame` (e.g. with `AcquisitionAdapter` and `AcquisitionState`) actually correct?**
  _`WaveformFrame` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ChannelCalibration` (e.g. with `AcquisitionAdapter` and `AcquisitionState`) actually correct?**
  _`ChannelCalibration` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `EventStore` (e.g. with `RealtimePQPipeline` and `PQDServerRequestHandler`) actually correct?**
  _`EventStore` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `PQEvent` (e.g. with `WaveformFrame` and `RealtimePQPipeline`) actually correct?**
  _`PQEvent` has 3 INFERRED edges - model-reasoned connections that need verification._
# Final Repository Structure & System Navigation Guide

**Document Version:** 1.0.0  
**Status:** Phase 3 Complete (Eight Disturbance Classes Audited)  
**Authoritative Architecture:** 60-Hz WSCC IEEE 9-Bus Simscape Simulation & Python 32-Feature DSP Pipeline  

---

## 1. High-Level Repository Architecture

The repository is organized into focused, single-responsibility subsystems designed for clarity, mathematical reproducibility, and modular progression across engineering phases:

```
power-quality-detector-and-classifier/
├── README.md                      # Primary GitHub project presentation & status
├── RUNTHISPROJECT.md              # Developer quickstart and execution workflows
├── CHANGELOG.md                   # Formal chronological engineering release log
├── .gitignore                     # Git hygiene and exclusion rules
├── pytest.ini                     # Pytest runner configuration
├── server.py                      # REST & SSE Telemetry server (port 8500)
├── app_frontend.py                # Alternative dashboard UI launcher
│
├── IEEE_9bus/                     # Power system electromagnetic simulation (MATLAB/Simulink R2025a)
│   ├── IEEE_9bus_PQD_HIL_R2025a.slx  # Pristine frozen reference baseline (SHA-256: 5D833D8F...)
│   └── IEEE_9bus_PQD_DISTURBANCES.slx # Working disturbance generation model (8 injection blocks)
│
├── data/                          # Authoritative datasets and runtime storage
│   ├── ieee9bus_60hz/             # 8 audited physical 60-Hz datasets (9,216 total multi-phase frames)
│   │   ├── normal/                # 1,152 frames, 32 operating conditions
│   │   ├── sag/                   # 1,152 frames, shunt fault switching
│   │   ├── swell/                 # 1,152 frames, switched capacitor energization
│   │   ├── interruption/          # 1,152 frames, series line breaker opening
│   │   ├── harmonics/             # 1,152 frames, non-linear load current injection
│   │   ├── flicker/               # 1,152 frames, sub-synchronous load modulation
│   │   ├── notch/                 # 1,152 frames, thyristor commutation switching
│   │   └── transient/             # 1,152 frames, high-frequency RLC energization
│   └── pq_events.db               # SQLite database for real-time event persistence
│
├── docs/                          # Comprehensive technical documentation & scientific record
│   ├── README.md                  # Documentation navigation landing page
│   ├── PROJECT_STATUS.md          # Master single human-readable project status
│   ├── SOURCE_OF_TRUTH.md         # Master authoritative file and contract registry
│   ├── ARCHITECTURE.md            # 7-subsystem engineering specification
│   ├── ROADMAP.md                 # Multi-phase roadmap (Phases 1 through 6)
│   ├── DATASET.md                 # Comprehensive 8-class physical dataset specification
│   ├── STANDARDS_TRACEABILITY_INDEX.md # Standards mapping (IEEE 1159, 519, 1453, IEC)
│   ├── ML_READINESS.md            # 10-step protocol for Phase 4 ML training
│   ├── REPRODUCIBILITY.md         # Environment setup and reproduction recipes
│   ├── LIVE_MVP_PLAN.md           # Phase 5 live demonstration specification
│   ├── GATE_INDEX.md              # Gate verification matrix (Gates 1 to 3X)
│   ├── REPOSITORY_COMPONENT_AUDIT.md # Component classification and action matrix
│   ├── REPOSITORY_DEEP_CLEAN_REPORT.md # Deep clean execution report
│   ├── FINAL_REPOSITORY_STRUCTURE.md # This directory guide
│   └── GATE3A to GATE3X reports   # 24 immutable gate reports and quality summaries
│
├── scenarios/                     # Declarative disturbance scenario controller definitions
│   ├── README.md                  # Scenario controller guide and provenance taxonomy
│   ├── scenario_controller.py     # Scenario loader and validator
│   └── definitions/               # JSON scenario specs (SAG, SWELL, INT, HAR, FLK, NOT, TRAN, NORM)
│
├── dsp/                           # Digital Signal Processing subsystem
│   ├── README.md                  # Production DSP guide and 32-feature contract definition
│   ├── enhanced_features.py       # Canonical production 32-feature extraction engine
│   ├── waveform_frame.py          # Multi-channel waveform container & NaN guards
│   ├── standards_detector.py      # Independent IEEE physical rule engine
│   ├── phase_processor.py         # Multi-phase sliding window processor
│   ├── ring_buffer.py             # Circular streaming acquisition buffer (5 kHz)
│   ├── acquisition_adapter.py     # Streaming adapters (Simulink, Simulation, Mock)
│   ├── baseline_features.py       # Legacy 8-feature extractor (supporting parity tests)
│   └── waveform_generator.py      # Synthetic signal generator for test fixtures
│
├── pipeline/                      # Ingestion and validation pipelines
│   ├── realtime_pipeline.py       # Core streaming ingestion, DSP & event pipeline
│   ├── disturbance_validator.py   # Ground-truth physical rule validator (8 classes)
│   └── frame_queue.py             # Thread-safe frame queue for async processing
│
├── integration/                   # Simulation-to-Python integration bridge
│   └── matlab/                    # Streaming & auto-ingestion MATLAB scripts
│
├── ml/                            # Machine learning models and training scripts
│   ├── README.md                  # ML subsystem overview and Phase 4 retraining plan
│   └── models/
│       └── model_weights_32.json  # Current 32-feature weights (FROZEN pending Phase 4)
│
├── scripts/                       # Dataset generators, validators, and audit scripts
│   └── README.md                  # Automation script catalog and operational matrix
│
├── tests/                         # Complete automated test suite (300 passed, 2 skipped)
│   └── README.md                  # Test suite architecture and execution guide
│
├── web/                           # Live laboratory oscilloscope dashboard UI
│   ├── index.html                 # CRT Oscilloscope and FFT Analyzer interface
│   ├── styles.css                 # Retro SCADA / Phosphor terminal stylesheet
│   └── app.js                     # Canvas waveform renderer and telemetry client
│
└── future/                        # Optional and future extension subsystems (Phase 6)
    ├── README.md                  # Optional extensions overview
    └── esp32-hil/                 # Embedded microcontroller acquisition & inference
        ├── README.md              # ESP32 HIL deployment and parity guide
        ├── firmware/              # C++ PlatformIO firmware (Goertzel DSP, TFLite-Micro)
        └── hardware/              # Analog front-end schematics & safety checklist
```

---

## 2. Root Directory Subsystem Responsibilities

| Subsystem / Directory | Lifecycle Role | Owner of Responsibility | Key Entry Point |
|---|---|---|---|
| **`IEEE_9bus/`** | Electrical Simulation | Power Systems / Grid Physics | `IEEE_9bus_PQD_DISTURBANCES.slx` |
| **`data/`** | Ground-Truth Data & Storage | Data Engineering / Telemetry | `data/ieee9bus_60hz/` |
| **`docs/`** | Master Specifications & Audits | Systems Engineering / Scientific Record | `docs/README.md` |
| **`scenarios/`** | Disturbance Scenario Controllers | Simulation Control & Ground Truth | `scenarios/definitions/` |
| **`dsp/`** | Signal Processing & Feature Extraction | Digital Signal Processing (DSP) | `dsp/enhanced_features.py` |
| **`pipeline/`** | Ingestion & Real-Time Orchestration | Backend Systems Pipeline | `pipeline/realtime_pipeline.py` |
| **`integration/`** | MATLAB / Simulink Bridge | Co-Simulation Interface | `integration/matlab/send_simulink_pqd_auto.m` |
| **`ml/`** | ML Classification & Inference | Machine Learning Engineering | `ml/models/model_weights_32.json` |
| **`scripts/`** | Automation & Quality Audits | Automation & Verification | `scripts/` |
| **`tests/`** | Automated Regression Suite | Quality Assurance & Verification | `pytest` |
| **`web/`** | Laboratory Dashboard UI | Frontend Telemetry Interface | `http://localhost:8500` (`server.py`) |
| **`future/`** | Optional Phase 6 Extensions | Embedded Systems & Hardware | `future/README.md` |

# Digital Signal Processing (DSP) Subsystem Guide

**Subsystem:** Digital Signal Processing & Feature Extraction  
**Authoritative Frequency ($f_0$):** 60.0 Hz (WSCC Grid Standard)  
**Authoritative Sampling Rate ($F_s$):** 5,000 Hz ($T_s = 200\ \mu\text{s}$)  
**Authoritative Frame Contract:** $N = 1,000$ discrete samples (200 ms duration, 12 fundamental cycles)  

---

## 1. Production DSP Components (Active Path)

When working on or integrating with the 60-Hz IEEE 9-bus pipeline, use these canonical modules:

```
+-----------------------------------------------------------------------------+
|                      PRODUCTION DSP PIPELINE ARCHITECTURE                   |
+-----------------------------------------------------------------------------+
|                                                                             |
|   1. Acquisition & Ingestion                                                |
|      - dsp/acquisition_adapter.py  --> Simulink / Simulation / Mock Stream  |
|      - dsp/ring_buffer.py          --> Multi-channel 5 kHz Circular Buffer  |
|                                                                             |
|   2. Waveform Framing & Integrity                                           |
|      - dsp/waveform_frame.py       --> 3-Phase Container (L1, L2, L3)       |
|                                        Strict 5 kHz, 200 ms, NaN/Inf Guards |
|                                                                             |
|   3. Feature Extraction (Production 32-Feature Contract)                    |
|      - dsp/enhanced_features.py    --> Authoritative 32-Feature Extractor   |
|                                        * Goertzel Filter Bank H1–H11        |
|                                        * Phase-Aware Orthogonal SNR         |
|                                        * Half-Cycle Sliding RMS             |
|                                        * Statistical Moments & Entropy      |
|                                                                             |
|   4. Physical Standards & Rules (Decoupled from ML)                         |
|      - dsp/standards_detector.py   --> IEEE 1159 / IEEE 519 Detection Rules |
|      - dsp/phase_processor.py      --> Multi-phase State Aggregator         |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 2. DSP Module Directory & Responsibilities

| File | Subsystem Role | Key Features & Functions | Status |
|---|---|---|:---:|
| **`dsp/enhanced_features.py`** | **CANONICAL PRODUCTION DSP** | `extract_32_features()`: Computes exact 32-feature vector ($V_{\text{rms}}$, $V_{\text{peak}}$, Crest, Form, THD, SNR, H1–H11, Mean, Variance, Skewness, Kurtosis, Energy, Shannon Entropy, Zero Crossings, Frequency, DC Component). | **PRODUCTION** |
| **`dsp/waveform_frame.py`** | **WAVEFORM CONTAINER** | `WaveformFrame`: Immutable multi-channel waveform slice ensuring channel synchrony, sampling rate enforcement ($5,000\text{ Hz}$), temporal duration ($200\text{ ms}$), and numerical sanity. | **PRODUCTION** |
| **`dsp/standards_detector.py`** | **PHYSICAL RULE DETECTOR** | `StandardsDetector`: Implements IEEE 1159 / IEEE 519 deterministic thresholding ($V_{\text{rms}} < 0.90\text{ pu}$ for Sag, $V_{\text{rms}} > 1.10\text{ pu}$ for Swell, $V_{\text{rms}} < 0.10\text{ pu}$ for Interruption, $\text{THD} > 5.0\%$ for Harmonics). | **PRODUCTION** |
| **`dsp/phase_processor.py`** | **MULTI-PHASE PROCESSOR** | `MultiPhaseProcessor`: Sliding window analysis over 3-phase waveforms, per-phase DSP extraction, and model contract verification. | **PRODUCTION** |
| **`dsp/ring_buffer.py`** | **STREAMING BUFFER** | `MultiChannelRingBuffer`: Thread-safe circular buffer ingesting variable-sized streaming chunks at 5 kHz with zero sample drop. | **PRODUCTION** |
| **`dsp/acquisition_adapter.py`** | **STREAMING ADAPTERS** | `SimulinkAdapter`, `SimulationAdapter`, `MockHardwareAdapter`: Concrete source adapters for streaming inputs into the pipeline. | **PRODUCTION** |
| `dsp/baseline_features.py` | Supporting / Legacy | `extract_baseline_features()`: Legacy 8-feature extractor preserved for backward-compatibility parity tests with C++ firmware. | **SUPPORTING** |
| `dsp/waveform_generator.py` | Supporting / Synthetic | Synthetic signal generator for unit tests and calibration fixtures. | **SUPPORTING** |

---

## 3. The 32-Feature Production Contract

The authoritative feature order extracted by `dsp/enhanced_features.py` matches the production ML contract:

```
Index  Feature Name         Physical Description
[0]    rms_voltage          Total True RMS voltage (pu)
[1]    peak_voltage         Maximum absolute peak voltage (pu)
[2]    crest_factor         Ratio of Peak to RMS
[3]    form_factor          Ratio of RMS to Mean Absolute Value
[4]    thd                  Total Harmonic Distortion (H2–H11, %)
[5]    snr_db               Phase-Aware Orthogonal Projection SNR (dB)
[6]    h1_mag               Fundamental component magnitude (60 Hz)
[7]    h2_mag               2nd Harmonic magnitude (120 Hz)
[8]    h3_mag               3rd Harmonic magnitude (180 Hz)
[9]    h4_mag               4th Harmonic magnitude (240 Hz)
[10]   h5_mag               5th Harmonic magnitude (300 Hz)
[11]   h6_mag               6th Harmonic magnitude (360 Hz)
[12]   h7_mag               7th Harmonic magnitude (420 Hz)
[13]   h8_mag               8th Harmonic magnitude (480 Hz)
[14]   h9_mag               9th Harmonic magnitude (540 Hz)
[15]   h10_mag              10th Harmonic magnitude (600 Hz)
[16]   h11_mag              11th Harmonic magnitude (660 Hz)
[17]   mean_v               Statistical mean
[18]   variance_v           Statistical variance
[19]   skewness_v           Moment skewness (waveform asymmetry)
[20]   kurtosis_v           Moment kurtosis (impulsive transient peakiness)
[21]   energy_v             Signal energy ($\sum v[n]^2$)
[22]   entropy_v            Shannon spectral entropy (spectral disorder)
[23]   zero_crossings       Zero-crossing count per 200 ms frame
[24]   freq_estimate        Fundamental frequency estimate (Hz)
[25]   dc_component         DC offset component (pu)
[26]   half_cycle_rms_min   Minimum half-cycle sliding RMS (pu)
[27]   half_cycle_rms_max   Maximum half-cycle sliding RMS (pu)
[28]   half_cycle_rms_std   Standard deviation of half-cycle RMS
[29]   spec_flatness        Spectral flatness measure
[30]   spec_centroid        Spectral power centroid (Hz)
[31]   spec_rolloff         Spectral rolloff frequency (85% power, Hz)
```

Mathematical parity between Python and MATLAB DSP implementations is verified in `tests/test_simulink_parity.py` with maximum absolute error $< 0.000050$.

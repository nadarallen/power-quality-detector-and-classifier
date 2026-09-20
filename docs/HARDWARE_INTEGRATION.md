# Real Three-Phase Hardware Integration Specification

This document defines the software-side interface contract, architectural requirements, and safety boundaries for integrating real physical data acquisition (DAQ) hardware into the Power Quality Detector & Classifier platform.

---

## 1. Safety Boundary & Electrical Isolation Disclaimer

> [!CAUTION]
> **CRITICAL ELECTRICAL SAFETY BOUNDARY**  
> Under **NO CIRCUMSTANCES** should mains voltage (110 V / 230 V / 415 V AC) ever be connected directly to microcontroller GPIO pins (ESP32, Arduino, Raspberry Pi), generic audio inputs, or non-isolated computer measurement cards. Doing so risks lethal electric shock, explosive arc flash, and catastrophic destruction of computer hardware.

The software stack assumes that an **appropriately certified, galvanically isolated measurement front-end** attenuates and isolates high-voltage AC lines before signals reach any analog-to-digital converter:
- **Potential Transformers (PTs)** or **Hall-Effect / Fluxgate Voltage Transducers** with rated dielectric withstand voltages conforming to applicable local and international installation categories (e.g., CAT III / CAT IV).
- **Anti-aliasing active filters** matched to the target Nyquist frequency.
- High-impedance differential analog buffers ensuring common-mode rejection.

The software engineering task defined in this repository is strictly **the digital acquisition interface** receiving digitised samples over standard communication buses (USB, Ethernet, SPI, UART, or PCIe). The software does not certify electrical safety ratings.

---

## 2. Core Architectural Model

The physical acquisition device is decoupled from the downstream digital signal processing (DSP), neural network inference, and event engine via the `AcquisitionAdapter` and `HardwareAdapter` abstractions:

```
┌─────────────────────────────────────────────────────────────┐
│               PHYSICAL THREE-PHASE AC MAINS                 │
│                      (L1, L2, L3, N)                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           ISOLATED MEASUREMENT FRONT-END (PT/CT)            │
│         Galvanic isolation, attenuation, anti-alias         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              MULTI-CHANNEL ADC / DAQ HARDWARE               │
│        Synchronous sampling, 16/24-bit delta-sigma/SAR      │
└──────────────────────────────┬──────────────────────────────┘
                               │ Digital Packets (USB/Net/Serial)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           HARDWARE ADAPTER (dsp/acquisition_adapter.py)     │
│   DAQAdapter / SerialAdapter / NetworkAdapter / MockAdapter │
│   - Ingests raw ADC chunks                                  │
│   - Applies ThreePhaseCalibration (Counts -> Volts -> pu)   │
│   - Validates sequence counters & detects dropped samples   │
│   - Validates saturation / rail clipping                    │
│   - Constructs canonical WaveformFrame                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ WaveformFrame (L1, L2, L3)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               EXISTING REAL-TIME PIPELINE                   │
│   RealtimePQPipeline -> RingBuffer -> PhaseProcessor        │
│   -> Compact MLP -> ThreePhaseEventEngine -> EventStore     │
└─────────────────────────────────────────────────────────────┘
```

The core processing pipeline (`PhaseProcessor`, `RealtimePQPipeline`, `EventEngine`) remains **entirely unaware** of the physical hardware make and model.

---

## 3. Hardware Requirements Contract

Any acquisition device interfacing with this platform must satisfy the following software-side contract:

### 3.1 Channel Topology & Synchronization
- **Channels**: Minimum 3 independent voltage channels (`L1`, `L2`, `L3`). Optional 4th channel (`N` / neutral voltage) and current channels (`I1`, `I2`, `I3`).
- **Simultaneous Sampling**: Channels must be sampled simultaneously. True simultaneous sampling ADC architectures (e.g., dedicated SAR or Delta-Sigma ADC per channel) are required. Multiplexed ADCs with inter-channel phase delay exceeding $1\,\mu\text{s}$ are unacceptable unless hardware phase-compensation interpolation is applied prior to frame emission.
- **Phase Continuity**: The sample count across all active phases in any acquisition chunk must be strictly identical ($N_{\text{L1}} == N_{\text{L2}} == N_{\text{L3}}$).

### 3.2 Sampling Rate & Frequency Support
- **Configurability**: The sampling rate $f_s$ must be explicitly communicated in the frame metadata.
- **Nominal Rate**: The reference research configuration is $5000\text{ Hz}$ (100 samples per cycle at 50 Hz, 83.33 samples per cycle at 60 Hz).
- **Supported Range**: $1000\text{ Hz} \le f_s \le 20000\text{ Hz}$.
- **Transient Representation**: The system will not assert or classify high-frequency transients above the Nyquist limit ($f_{\text{Nyquist}} = f_s / 2$).

### 3.3 Dynamic Range, Resolution & Saturation
- **Resolution**: Minimum 16-bit signed integer (`int16`, $-32768$ to $+32767$) or 24-bit signed integer (`int32`).
- **Headroom**: Nominal peak voltage should occupy approximately $50\%\text{--}70\%$ of full-scale ADC range to preserve headroom for Class 3 Voltage Swell ($1.80\text{ pu}$) and sub-cycle transient overshoots without clipping.
- **Saturation Detection**: Any sample reaching digital rail ($V_{\text{raw}} \le V_{\text{min\_rail}}$ or $V_{\text{raw}} \ge V_{\text{max\_rail}}$) flags `is_clipped = True`, signaling downstream pipelines that spectral metrics may be corrupted by harmonic flattop clipping.

### 3.4 Timestamping & Sequence Tracking
- **Timestamps**: Every packet/frame must deliver:
  - High-precision timestamp in UTC epoch seconds (float with microsecond resolution).
  - Monotonic hardware sequence counter (`sequence_number`: unsigned 32-bit integer).
- **Dropped Sample Detection**: Discontinuities in `sequence_number` indicate dropped packets or buffer overruns in the transmission bus. The adapter calculates `dropped_samples_count` and marks the frame.

---

## 4. Calibration & Engineering Unit Conversion

Raw ADC values must never be assumed equal to engineering units. The transformation follows a three-stage mathematical pipeline defined in `dsp/calibration.py`:

$$V_{\text{engineering}} = (V_{\text{raw}} - \text{offset}) \times \text{gain} \times \text{sensor\_ratio}$$

$$\text{Value}_{[\text{pu}]} = \frac{V_{\text{engineering}}}{V_{\text{nominal\_peak}}}$$

Where:
- $V_{\text{raw}}$: Raw ADC integer code.
- $\text{offset}$: ADC zero-voltage offset error (in ADC counts).
- $\text{gain}$: Volts per ADC count ($V_{\text{ref}} / 2^{B-1}$).
- $\text{sensor\_ratio}$: Potential transformer / voltage divider step-down ratio ($V_{\text{primary}} / V_{\text{secondary}}$).
- $V_{\text{nominal\_peak}}$: Grid base peak voltage, e.g., $V_{\text{RMS\_nom}} \times \sqrt{2}$. For a 12.0 V RMS laboratory bus, $V_{\text{nominal\_peak}} \approx 16.97\text{ V}$. For a 230 V RMS distribution line, $V_{\text{nominal\_peak}} \approx 325.27\text{ V}$.

The calibration parameters are preserved in `ChannelCalibration` and attached to `ChannelMetadata`.

---

## 5. Packet & Chunk Streaming Formats

When streaming data over TCP/UDP, Serial, or REST (`POST /api/ingest/chunk`), acquisition devices should format chunks as follows:

```json
{
  "device_id": "DAQ-3PH-001",
  "sequence_id": 14205,
  "sampling_rate": 5000.0,
  "timestamp": 1726830000.125000,
  "raw_counts": {
    "L1": [-1240, 1502, ...],
    "L2": [2500, -890, ...],
    "L3": [-1260, -612, ...]
  },
  "dropped_samples": 0
}
```

Alternatively, pre-calibrated floating point arrays may be ingested directly through `POST /api/ingest` conforming to `WaveformFrame.to_dict()` format.

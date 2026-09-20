# Hardware Evaluation: Physical Acquisition Candidates for 3-Phase PQD

This document systematically assesses hardware candidates and interface categories against the requirements defined in [`docs/ACQUISITION_REQUIREMENTS.md`](file:///home/salmo/Projects/major%20project/power-quality-detector-and-classifier/docs/ACQUISITION_REQUIREMENTS.md).

---

## 1. Candidate Comparison Matrix

| Candidate Category | Representative Device | Synchronous Sampling | Resolution & Max $f_s$ | Galvanic Isolation | Linux / Python Driver Support | Streaming Latency | Relative Cost |
|---|---|---|---|---|---|---|---|
| **Category A: Precision USB DAQ** | **Measurement Computing USB-1608FS-Plus** | Yes (4 dedicated 16-bit SAR ADCs) | 16-bit, up to $100\text{ kS/s/ch}$ | None on-board (Requires external isolated PT/differential probe) | Excellent (`libuldaq` official C/Python Linux drivers) | Very low ($< 5\text{ ms}$ buffer chunks) | Moderate (~$500–$700) |
| **Category A2: Laboratory USB DAQ** | **LabJack T7-Pro** | Pseudo-simultaneous (High-speed multiplexer or burst) | 16-bit/24-bit, up to $100\text{ kS/s}$ aggregate | Channel-to-ground isolation limited; requires external PT | Excellent (`LJM` C/Python library, cross-platform) | Low ($10\text{ ms}$ streaming blocks) | Moderate (~$600–$900) |
| **Category B: Industrial Class A PQ Meter** | **Janitza UMG 604E / Satec PM180** | Yes (Internal multi-channel simultaneous DSP) | 16-bit, $20\text{ kHz}$ to $28\text{ kHz}$ | Native CAT III 600V galvanic isolation | Modbus TCP / IEC 61850 over Ethernet (Standard Python socket/pymodbus) | Moderate (Polled registers or periodic snapshot stream) | High ($1,500–$3,500) |
| **Category C: Dedicated Simultaneous $\Sigma\Delta$ ADC Board** | **TI ADS131M04 EVM / ADI ADE9000** | Yes (True simultaneous $\Delta\Sigma$ converters on 4 channels) | 24-bit, up to $32\text{ kS/s/ch}$ | High isolation when paired with AMC1301/AMC1311 | SPI bus to Raspberry Pi or USB FTDI bridge (Custom Python SPI wrapper) | Extremely low ($< 2\text{ ms}$ DMA stream) | Low-to-Moderate (~$150–$350) |
| **Category D: Microcontroller Isolated Sensor Shield** | **STM32H7 / ESP32-S3 + AMC1301 Isolated Amplifiers** | Hardware-dependent (Dual ADC or external SPI ADC) | 12-bit to 16-bit, up to $20\text{ kS/s}$ | Reinforced isolation ($5\text{ kV}_{\text{RMS}}$) via AMC1301 | UART / USB CDC serial binary stream to host Python | Low-to-Moderate ($5–15\text{ ms}$) | Low (~$80–$150) |

---

## 2. In-Depth Technical Assessment

### 2.1 Category A: Precision USB DAQ (e.g. Measurement Computing USB-1608FS-Plus)
- **Documented Specifications**:
  - 8 single-ended / 4 true differential analog inputs.
  - Dedicated A/D converter per channel (simultaneous sampling, zero phase skew).
  - 16-bit resolution, sampling rates up to $100\text{ kS/s}$ per channel.
  - Supported on Linux via the open-source `libuldaq` C library and `uldaq` Python package.
- **Engineering Evaluation**:
  - **Pros**: Outstanding Linux support with native Python streaming bindings; zero inter-channel phase delay ensures rigorous 3-phase synchronization; configurable buffer chunk sizes perfectly fit the `MultiChannelRingBuffer`.
  - **Cons**: The analog inputs accept only $\pm 10\text{ V}$. An external isolated front-end (e.g., 3 high-voltage potential transformers or LEM voltage transducers) is mandatory before connecting to AC mains.

### 2.2 Category B: Industrial Power Quality Instrument (e.g. Janitza / Satec)
- **Documented Specifications**:
  - Direct 3-phase + neutral voltage inputs (up to 690 V L-L, CAT III 600 V).
  - Internal DSP computing harmonic spectra up to the 40th or 63rd harmonic.
  - Modbus TCP / IEC 61850 / raw Ethernet communication.
- **Engineering Evaluation**:
  - **Pros**: Direct connection to live switchgear without building custom transducer front-ends; certified electrical isolation and safety ratings.
  - **Cons**: High cost; many commercial units expose aggregated 10-cycle or 200 ms RMS and THD registers rather than raw uncompressed 5 kHz instantaneous waveform samples, limiting research into novel deep learning classifiers unless the high-speed waveform capture option is unlocked.

### 2.3 Category C: Simultaneous Sampling $\Delta\Sigma$ ADC (e.g. TI ADS131M04)
- **Documented Specifications**:
  - 4 simultaneously sampling, 24-bit delta-sigma analog-to-digital converters.
  - Dynamic range $> 102\text{ dB}$ at $4\text{ kS/s}$, clock-synchronized conversion.
  - SPI serial interface with checksum / CRC verification.
- **Engineering Evaluation**:
  - **Pros**: Exceptional dynamic range ($>100\text{ dB}$) resolves both microvolt commutation notching and high-voltage transient overshoots; low hardware cost; ideal 4-channel topology (`L1`, `L2`, `L3`, `N`).
  - **Cons**: Requires a host processor with SPI DMA capability (e.g., Raspberry Pi 4 / Compute Module 4 or STM32 MCU) to stream continuous samples to the host PC via USB or Ethernet.

### 2.4 Category D: Microcontroller Isolated Sensor Shield (Current Repository Firmware Basis)
- **Documented Specifications**:
  - ESP32 / STM32 with onboard SAR ADCs (12-bit).
  - Serial UART / USB CDC stream at 921,600 baud.
- **Engineering Evaluation**:
  - **Pros**: Leverages existing PlatformIO firmware base in `firmware/`; low BOM cost.
  - **Cons**: The built-in ESP32 internal SAR ADCs suffer from notable non-linearity (INL/DNL errors), offset drift, and multiplexed sampling skew between ADC1 and ADC2. If a microcontroller is selected, an external synchronous ADC (such as the ADS131M04 via SPI) is strongly recommended over raw ESP32 GPIO analog pins.

---

## 3. Hardware Selection Decision Gate

> [!IMPORTANT]
> **DECISION GATE: AWAITING USER HARDWARE SELECTION**  
> Physical acquisition hardware has not yet been procured or locked by the user.  
> 
> To maintain strict architectural cleanliness and avoid implementing dead vendor-specific drivers:
> 1. The software architecture exposes a clean, decoupled `HardwareAdapter` interface (`DAQAdapter`, `SerialAdapter`, `NetworkAdapter`).
> 2. The ingestion endpoint `POST /api/ingest/chunk` accepts raw integer ADC counts and calibrated per-unit float arrays from any external hardware daemon.
> 3. The system halts at the hardware-selection gate until the user selects or provides the physical measurement instrument.

---

## 4. Recommended Next Path Once Hardware is Procured

1. **If a USB DAQ is chosen** (e.g., MCC USB-1608FS-Plus):
   - Implement `DAQAdapter` by wrapping `uldaq.DaDevice.a_in_scan()` with a ring-buffer callback.
2. **If an Isolated Microcontroller Front-End is chosen** (e.g., STM32 / ESP32 with external ADC):
   - Implement `SerialAdapter` to read the binary frame packet protocol over USB CDC at 921,600 baud.
3. **If an Industrial Network Meter is chosen**:
   - Implement `NetworkAdapter` streaming over Modbus TCP or raw UDP socket.

# Real Three-Phase Power Quality Data Acquisition Requirements Specification

This document defines the rigorous physical, electrical, and software engineering requirements for physical acquisition hardware intended to interface with the Power Quality Monitoring and Classification system.

---

## 1. Safety Boundary & Front-End Isolation

> [!CAUTION]
> **ELECTRICAL SAFETY MANDATE**  
> Direct connection of power distribution lines (110 V / 230 V / 400 V / 415 V AC) to microcontrollers, single-board computer GPIOs, unisolated USB ADCs, or sound cards is strictly prohibited. Connecting unisolated hardware to mains leads to fatal shock hazards, catastrophic flashover, and immediate destruction of instrumentation.

### 1.1 Galvanic Isolation Requirements
- **Measurement Category**: Front-end measurement apparatus must comply with **IEC 61010-1** and **IEC 61010-2-030** installation category **CAT III 600V / 300V** or **CAT IV 600V** depending on point of common coupling (PCC) location.
- **Dielectric Breakdown Withstand**: Minimum **$2.5\,\text{kV}_{\text{RMS}}$ (50/60 Hz, 1 minute)** between primary high-voltage terminals and secondary low-voltage digital acquisition circuits.
- **Transducer Options**:
  1. Precision instrument potential transformers (PTs) with rated accuracy class 0.2 or 0.5.
  2. Isolated closed-loop Hall-effect or fluxgate voltage transducers (e.g., LEM LV 25-P series).
  3. High-voltage differential probes with integrated active isolation amplifiers (e.g., Texas Instruments AMC1301/AMC1311 reinforced isolation amplifiers with $\ge 5\,\text{kV}_{\text{RMS}}$ isolation).

---

## 2. Analog & Digital Acquisition Specifications

| Parameter | Research Configuration (Current) | Target Real Hardware Requirement | Engineering Justification |
|---|---|---|---|
| **Voltage Channels** | 3 independent (`L1`, `L2`, `L3`) | **3 independent phases + 1 neutral (`L1`, `L2`, `L3`, `N`)** | Resolves unbalance, line-to-neutral sags, and zero-sequence ground faults. |
| **Current Channels (Optional)** | None | **3 current channels (`I1`, `I2`, `I3`)** | Enables power factor, active/reactive power, and directional disturbance tracking. |
| **Channel Synchronization** | Simultaneous software synthesis | **True simultaneous sampling ($\le 1\,\mu\text{s}$ inter-channel skew)** | Multiplexed successive-approximation (SAR) ADCs introduce artificial inter-phase delay unless hardware-compensated. |
| **Sampling Rate ($f_s$)** | $5000\text{ Hz}$ (100 samples/cycle at 50 Hz) | **Configurable: $5000\text{ Hz}$ to $20000\text{ Hz}$** (IEC 61000-4-30 Class A typically uses $10.24\text{ kHz}$ to $20.48\text{ kHz}$) | Nyquist requires $f_s \ge 2 \times f_{\max}$. For $H_{11}$ ($550\text{ Hz}$), $5000\text{ Hz}$ provides 9.09 samples/cycle of the 11th harmonic. |
| **ADC Resolution** | 32-bit floating point simulation | **Minimum 16-bit signed integer (prefer 24-bit $\Sigma\Delta$)** | 16-bit provides $96\text{ dB}$ dynamic range ($\approx 0.003\%$ resolution); 24-bit provides $> 110\text{ dB}$ effective number of bits (ENOB). |
| **Input Full-Scale Headroom** | $1.0\text{ pu}$ nominal | **$\ge 2.0\text{ pu}$ instantaneous peak headroom** | Voltage Swells reach $1.80\text{ pu}$; sub-cycle transient impulses can peak at $2.0\text{ pu}$ without digital rail clipping. |
| **Analog Anti-Aliasing Filter** | Ideal numerical filter | **Active 4th-order low-pass (Butterworth/Bessel)** with $f_{-3\text{dB}} \approx 0.4 \times f_s$ | Prevents out-of-band RF interference and inverter PWM switching spikes from aliasing into low-order harmonics. |
| **Timestamp Precision** | Python `time.time()` float | **Hardware monotonic timer ($\le 10\,\mu\text{s}$ resolution)** synchronized via PTP (IEEE 1588) or NTP/GPS PPS | Required for cross-device event correlation and accurate duration measurement down to half-cycle ($10\text{ ms}$). |

---

## 3. Streaming Chunk Ingestion Contract

Physical acquisition devices stream digitized data as discrete packets (chunks) over USB, Ethernet, or Serial interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                 HARDWARE ACQUISITION PACKET                 │
├──────────────────────┬──────────────────────────────────────┤
│ Header               │ Magic bytes (0xAA55), Device ID      │
│ Sequence Counter     │ uint32 (detects dropped packets)     │
│ Timestamp            │ uint64 (microseconds since epoch)    │
│ Sampling Rate        │ float32 (actual clock in Hz)         │
│ Payload Length       │ uint16 (samples per channel, e.g. 50) │
│ Status Flags         │ Saturation bitmask, PLL lock, Sync   │
│ Channel L1 Raw       │ int16[N] ADC counts                  │
│ Channel L2 Raw       │ int16[N] ADC counts                  │
│ Channel L3 Raw       │ int16[N] ADC counts                  │
│ Checksum / CRC       │ CRC32 / Fletcher16                   │
└──────────────────────┴──────────────────────────────────────┘
```

Downstream software contract:
1. **Sequence Continuity**: Every received packet must increment `sequence_number` by 1. A gap $\Delta > 1$ immediately triggers `dropped_samples_count += (\Delta - 1) \times N`.
2. **Channel Length Equivalence**: All phases within a chunk must have strictly identical length.
3. **Saturation Bitmask**: If hardware clipping was detected by the analog front-end, `is_clipped` is propagated to the `WaveformFrame`.

---

## 4. Calibration & Engineering Unit Conversion

Raw ADC counts ($C$) are transformed into per-unit grid voltage ($V_{\text{pu}}$) via:

$$V_{\text{engineering}} = (C - \text{offset}) \times \left(\frac{2 \times V_{\text{ref}}}{2^B}\right) \times K_{\text{sensor}} \times K_{\text{trim}}$$

$$V_{\text{pu}} = \frac{V_{\text{engineering}}}{V_{\text{nominal\_peak}}}$$

Where:
- $B$: ADC resolution in bits (e.g. 16 or 24).
- $V_{\text{ref}}$: Precision voltage reference (e.g. 2.5 V or 3.3 V).
- $K_{\text{sensor}}$: Primary-to-secondary turns or divider ratio (e.g. $230\text{ V} / 2.3\text{ V} = 100.0$).
- $K_{\text{trim}}$: Fine calibration multiplier determined against laboratory voltage calibrator.
- $V_{\text{nominal\_peak}}$: $V_{\text{RMS\_nominal}} \times \sqrt{2}$.

---

## 5. Summary Distinction: Research Prototype vs Production DAQ

| Dimension | Current Research Prototype | Production Real-Hardware Goal |
|---|---|---|
| **Signal Source** | Synthetic Python Generator (`SimulationAdapter`) / Replay | Isolated Potential Transformers + Physical AC Bus |
| **Ingestion Path** | Internal loop / `POST /api/ingest` | Continuous DMA buffer / USB-Ethernet packet stream |
| **Clock Source** | Host operating system software clock | Hardware crystal oscillator / GPS PPS synchronized |
| **Safety State** | Software simulated | Galvanically isolated CAT III front-end |

# ESP32 Hardware-in-the-Loop (HIL) & Embedded Firmware Guide (Phase 6)

**Subsystem:** Embedded Microcontroller Acquisition & On-Device Inference  
**Lifecycle Target:** Phase 6 — Optional Embedded HIL Deployment  
**Hardware Platform:** ESP32-WROOM-32 (Dual-Core Tensilica Xtensa LX6 @ 240 MHz)  
**Primary Toolchain:** PlatformIO / ESP-IDF  

---

## 1. Overview & Architecture

> [!NOTE]
> **Optional Extension Notice:** The ESP32 embedded firmware and hardware front-end schematics represent an **optional Phase 6 research extension**. The primary production architecture of this repository is the 60-Hz WSCC IEEE 9-bus simulation in MATLAB/Simulink and the Python 32-feature DSP pipeline.

The embedded HIL architecture is designed to validate edge inference feasibility on low-cost microcontrollers:
1. **Sampling:** 12-bit SAR ADC on GPIO 34 sampling at 5 kHz via hardware timer interrupt (`feature_extraction.cpp`).
2. **On-Device DSP:** Optimized Goertzel filter bank computing single-bin DFT magnitudes for fundamental and harmonics $H_2\text{--}H_{11}$.
3. **Embedded Inference:** TensorFlow Lite for Microcontrollers (TFLite-Micro) running an Int8 quantized Compact MLP model ($< 10\text{ KB}$ flash footprint, $< 100\ \mu\text{s}$ latency).
4. **Protection:** Analog front-end with PC817 optocouplers, 3.3V Zener clamping diodes, and 5A fast-acting fuses (`hardware/safety_checklist.md`).

---

## 2. Directory Layout & Artifacts

```
future/esp32-hil/ (and root firmware/ & hardware/ mirrors)
├── README.md                      # Embedded HIL subsystem guide
│
├── firmware/
│   ├── platformio.ini             # PlatformIO build & toolchain configuration
│   └── src/
│       ├── main.cpp               # FreeRTOS tasks & ISR timer sampling
│       ├── feature_extraction.cpp # Goertzel single-precision DSP extraction
│       ├── feature_extraction.h   # DSP header & function declarations
│       ├── inference.cpp          # TFLite-Micro forward pass runtime
│       ├── inference.h            # Inference header & class definitions
│       ├── model_weights_32.h     # Exported 32-feature weights C-array
│       ├── relay_control.cpp      # GPIO relay switching for physical injection
│       └── display.cpp            # SSD1306 I2C OLED driver (128x64)
│
└── hardware/
    └── safety_checklist.md        # Hardware protection & electrical safety rules
```

---

## 3. Automated Firmware Parity Testing

To ensure that the C++ firmware logic never diverges from the Python scientific DSP pipeline, automated parity tests are executed as part of the regression suite:

```bash
pytest tests/test_firmware_parity.py -v
```

**Parity Guarantees:**
- Goertzel magnitude MAE between Python and C++ float32 is strictly $< 10^{-5}$.
- Total Harmonic Distortion (THD) numerical parity verified across $H_2\text{--}H_{11}$.
- Forward pass logits parity verified across synthetic sags, swells, and harmonics.

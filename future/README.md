# Future & Optional Extension Subsystems

**Directory Role:** Optional and Future Lifecycle Extensions (Phases 5 & 6)  
**Authoritative Context:** WSCC IEEE 9-Bus Simulation (60 Hz) & Python DSP Pipeline  

---

## 1. Scope & Status Notice

> [!NOTE]
> **Optional Extension Notice:** Subsystems housed or referenced in this directory represent **optional future research extensions** (e.g., embedded microcontrollers, cloud databases, mobile viewers). They are **decoupled from the primary 60-Hz simulation and Python DSP architecture** and are not required for core simulation, dataset generation, or ML training.

---

## 2. Extension Subsystems Matrix

| Subsystem | Target Phase | Primary Technologies | Directory Location | Status |
|---|:---:|---|---|:---:|
| **ESP32 Hardware-in-the-Loop (HIL)** | Phase 6 | ESP32-WROOM-32, C++, PlatformIO, Goertzel DSP, TFLite-Micro | `future/esp32-hil/` & `firmware/` | **OPTIONAL FUTURE** |
| **Analog Front-End Schematics** | Phase 6 | PC817 Optocoupler, 3.3V Zener clamp, 5A fuse, relay isolation | `future/esp32-hil/hardware/` & `hardware/` | **OPTIONAL FUTURE** |
| **Firebase Cloud Telemetry** | Phase 6 | Firebase Realtime Database, REST telemetry sync | `firebase/` | **OPTIONAL FUTURE** |
| **Mobile Monitoring Client** | Phase 6 | React Native / Flutter mobile telemetry viewer | `mobile_app/` | **OPTIONAL FUTURE** |

---

## 3. Engineering Guidelines for Future Work

1. **Decoupling Integrity:** Any development on future embedded or cloud extensions must import from the production contracts in `dsp/` and `pipeline/` without introducing breaking changes to 60-Hz simulation workflows.
2. **Parity Testing:** Embedded DSP implementations (e.g., C++ Goertzel magnitude in `firmware/src/feature_extraction.cpp`) must maintain verified numerical parity ($< 10^{-5}$ error) against Python implementations, as continuously validated by `tests/test_firmware_parity.py`.

# Hardware Safety & Electrical Protection Protocol

*Prepared for the 12V AC Power Quality Disturbance (PQD) Test Rig with ESP32 Control*

---

## 1. Fuse Ratings & Overcurrent Protection

| Circuit / Subsystem | Voltage Nominal | Fuse Type / Rating | Purpose |
|---|---|---|---|
| **Main 12V AC Bus** | 12V AC | Fast-Acting 5A Fuse | Protects 12V transformer secondary against dead shorts |
| **Capacitor Bank** | 12V AC | Fast-Acting 3A Fuse | Protects against capacitive inrush current spikes |
| **Inductor Bank** | 12V AC | Slow-Blow 3A Fuse | Handles inductive inrush without nuisance tripping |
| **ESP32 5V Input** | 5V DC | Resettable PTC Fuse 1A | Protects ESP32 & sensors from overvoltage/short |

---

## 2. Snubber & Flyback Diode Placement

- **Inductive Load Protection**: Every relay switching an inductive bank (choke / transformer / inductor coil) **MUST** have an $RC$ snubber circuit ($100\,\Omega,\: 0.1\,\mu\text{F}$ 250V AC capacitor) wired directly across the relay contacts to suppress high-voltage back-EMF spikes during relay opening.
- **Relay Coil Protection**: Flyback diodes (1N4007) must be connected reverse-biased across all 5V/12V relay coils to absorb inductive kickback and protect transistor drivers.

---

## 3. Opto-Isolation & Signal Conditioning Verification

> [!CAUTION]
> **GPIO Isolation Rule**: Never connect ESP32 GPIO pins directly to relay coils or high-current AC loads.

- **Relay Board Isolation**: Use opto-isolated relay modules (e.g., PC817 optocouplers). Verify jumper `JD-VCC` is isolated from ESP32 `VCC` if driving relay coils from an external 5V supply.
- **Voltage Sensor Conditioning**: The voltage sensor divider must clamp maximum peak AC voltage to $\le 3.3\text{V peak-to-peak}$ centered around a $1.65\text{V DC}$ offset (using an op-amp buffer or resistor divider with $10\,\mu\text{F}$ DC blocking capacitor).

---

## 4. Ground Loop & Sensor Protection Checklist

- [x] **Ground Loop Check**: Verify common ground between ACS712 current sensor, AC voltage sensor divider, and ESP32 `GND`. Ensure no dual-ground loops exist when ESP32 is powered via USB while connected to line-powered test equipment.
- [x] **ADC Pin Clamping**: Place 3.3V Zener diodes across ESP32 ADC input pins (`GPIO 34`, `GPIO 35`) to clamp transient overvoltage spikes to safe levels.
- [x] **Watchdog Timer Signoff**: Ensure `esp_task_wdt` is active in firmware so a frozen MCU automatically opens all relays after 2 seconds of unresponsiveness.

---

## 5. Pre-Power-On Inspection Checklist (Run Before Every Session)

1. [ ] **Visual Inspection**: Check all terminal blocks, screw terminals, and wire insulation for exposed conductors.
2. [ ] **Multimeter Continuity Test**: Measure resistance across AC lines with power OFF — verify no short circuit between line and neutral.
3. [ ] **Relay Logic Check**: Power up ESP32 logic (5V) before applying 12V AC power to the relay bank. Verify default relay state is `NORMAL` (only resistive load connected).
4. [ ] **Emergency Cutoff**: Confirm primary emergency kill-switch / breaker is within reach of the operator.

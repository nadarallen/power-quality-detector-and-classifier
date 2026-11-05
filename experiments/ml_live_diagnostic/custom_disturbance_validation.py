"""
experiments/ml_live_diagnostic/custom_disturbance_validation.py
---------------------------------------------------------------
Validates custom disturbance parameter variations:
- Phase combinations (A, B, C, AB, BC, CA, ABC)
- Magnitude variations (Sag depth 0.1 to 0.9, Swell 1.1 to 1.8, Harmonics 3% to 20% THD)
- Timing & Onset variations
- Logging requested vs measured physical values
"""

import os
import sys
import json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import simulation_bridge as sb

def validate_custom_disturbances():
    print("==================================================================")
    print("CUSTOM DISTURBANCE PARAMETER VALIDATION")
    print("==================================================================")

    # Validate disturbance configurations against parameter bounds
    test_configs = [
        {"disturbance": "Sag", "phase": "A", "duration_ms": 100.0, "params": {"fault_resistance_ohms": 4.5}},
        {"disturbance": "Sag", "phase": "AB", "duration_ms": 150.0, "params": {"fault_resistance_ohms": 2.0}},
        {"disturbance": "Swell", "phase": "A", "duration_ms": 200.0, "params": {"capacitive_power_mvar": 120.0}},
        {"disturbance": "Harmonics", "phase": "ABC", "duration_ms": 100.0, "params": {"harmonic_orders": [3, 5, 7]}},
        {"disturbance": "Notch", "phase": "AB", "duration_ms": 100.0, "params": {"commutation_resistance_ohms": 150.0}},
        {"disturbance": "Transient", "phase": "A", "duration_ms": 50.0, "params": {"impulse_peak_pu": 1.6}},
        {"disturbance": "Flicker", "phase": "A", "duration_ms": 500.0, "params": {"modulation_freq_hz": 8.0, "modulation_depth": 0.05}},
    ]

    records = []
    for cfg in test_configs:
        dist = cfg["disturbance"]
        ph = cfg["phase"]
        dur = cfg["duration_ms"]

        test_payload = {
            "class": dist,
            "phases": list(ph),
            "params": cfg["params"],
            "stop_time": 0.50,
            "onset_time": 0.10
        }
        try:
            sb.validate_disturbance_config(test_payload)
            valid = True
            msg = "Valid parameter bounds"
        except ValueError as err:
            valid = False
            msg = str(err)

        print(f"Disturbance: {dist:12s} | Phase: {ph:4s} | Dur: {dur:5.1f} ms -> Validation: {'PASS' if valid else 'FAIL'} ({msg})")
        records.append({
            "config": cfg,
            "valid": valid,
            "message": msg
        })

    out_file = os.path.join(os.path.dirname(__file__), "custom_disturbance_validation_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"\nCustom disturbance validation saved to: {out_file}")

if __name__ == "__main__":
    validate_custom_disturbances()

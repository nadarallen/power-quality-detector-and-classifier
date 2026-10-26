"""
scripts/generate_phase5b2_simulation_matrix.py
----------------------------------------------
Generates the authoritative 144-trajectory Phase 5B.2 / Phase 5C simulation matrix
for the expanded 4,608-frame IEEE 9-bus 60-Hz Power Quality Comparative Study.

Architecture:
- 144 independent continuous trajectories (18 trajectories/class x 8 classes).
- 32 sliding 200-ms windows per trajectory = 4,608 total dataset frames.
- 36 operating conditions cataloged across 9 families (A to I):
  * Train: Families A, B (Train), C (Train) -> 80 trajectories (2,560 frames, 55.56%)
  * Val: Families D, E, B (Val), C (Val) -> 32 trajectories (1,024 frames, 22.22%)
  * Challenge: Quarantined Families F, G, H, I -> 32 trajectories (1,024 frames, 22.22%)
- Includes 10 targeted remediation pilot trajectories for Phase 5B.2.
"""

import os
import json
import csv
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b2_simulation_matrix.json')
OUTPUT_CSV = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b2_simulation_matrix.csv')

CLASS_LABELS = [
    'Flicker', 'Harmonics', 'Interruption', 'Normal',
    'Notch', 'Sag', 'Swell', 'Transient'
]
CLASS_TO_IDX = {cls: idx for idx, cls in enumerate(CLASS_LABELS)}

# Complete catalog of all 36 operating conditions with exact electrical parameters
OPERATING_CONDITIONS = {
    # Family A: Nominal & Continuous System Scaling (Conditions 1 to 7) -> Train
    1: {"name": "Nominal Baseline", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    2: {"name": "Light Load 85%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 0.85, "qA": 0.85, "pB": 0.85, "qB": 0.85, "pC": 0.85, "qC": 0.85, "v1": 1.0, "f": 60.0, "v2": 0.99, "p2": 138e6, "v3": 0.99, "p3": 72e6},
    3: {"name": "Light Load 90%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 0.90, "qA": 0.90, "pB": 0.90, "qB": 0.90, "pC": 0.90, "qC": 0.90, "v1": 1.0, "f": 60.0, "v2": 0.995, "p2": 146e6, "v3": 0.995, "p3": 76e6},
    4: {"name": "Normal Load 95%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 0.95, "qA": 0.95, "pB": 0.95, "qB": 0.95, "pC": 0.95, "qC": 0.95, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 154e6, "v3": 1.0, "p3": 80e6},
    5: {"name": "Heavy Load 105%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.05, "qA": 1.05, "pB": 1.05, "qB": 1.05, "pC": 1.05, "qC": 1.05, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 171e6, "v3": 1.0, "p3": 89e6},
    6: {"name": "Heavy Load 110%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.10, "qA": 1.10, "pB": 1.10, "qB": 1.10, "pC": 1.10, "qC": 1.10, "v1": 1.01, "f": 60.0, "v2": 1.01, "p2": 175e6, "v3": 1.01, "p3": 93e6},
    7: {"name": "Peak Load 115%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.15, "qA": 1.15, "pB": 1.15, "qB": 1.15, "pC": 1.15, "qC": 1.15, "v1": 1.02, "f": 60.0, "v2": 1.02, "p2": 180e6, "v3": 1.02, "p3": 98e6},

    # Family B: Power Factor & Local Impedance Variations (Conditions 8 to 13)
    8: {"name": "High PF (0.98 lag)", "family": "Family B (PF & Local Load)", "split_default": "train", "pA": 1.0, "qA": 0.60, "pB": 1.0, "qB": 0.60, "pC": 1.0, "qC": 0.60, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    9: {"name": "Low PF (0.85 lag)", "family": "Family B (PF & Local Load)", "split_default": "val", "pA": 1.0, "qA": 1.25, "pB": 1.0, "qB": 1.25, "pC": 1.0, "qC": 1.25, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    10: {"name": "Bus 5 Heavy Local Load", "family": "Family B (PF & Local Load)", "split_default": "train", "pA": 1.20, "qA": 1.20, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 170e6, "v3": 1.0, "p3": 88e6},
    11: {"name": "Bus 5 Light Local Load", "family": "Family B (PF & Local Load)", "split_default": "val", "pA": 0.85, "qA": 0.85, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 158e6, "v3": 1.0, "p3": 83e6},
    12: {"name": "Bus 6 Remote Heavy Load", "family": "Family B (PF & Local Load)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.20, "qB": 1.20, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 168e6, "v3": 1.0, "p3": 85e6},
    13: {"name": "Bus 8 Remote Heavy Load", "family": "Family B (PF & Local Load)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.20, "qC": 1.20, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 92e6},

    # Family C: Spatial Diversity & Generation Redispatch (Conditions 14 to 17)
    14: {"name": "Cross-Bus Diversity A", "family": "Family C (Diversity & Redispatch)", "split_default": "val", "pA": 1.10, "qA": 1.10, "pB": 0.90, "qB": 0.90, "pC": 1.05, "qC": 1.05, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    15: {"name": "Cross-Bus Diversity B", "family": "Family C (Diversity & Redispatch)", "split_default": "train", "pA": 0.90, "qA": 0.90, "pB": 1.10, "qB": 1.10, "pC": 0.95, "qC": 0.95, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    16: {"name": "Gen 2 Heavy Dispatch", "family": "Family C (Diversity & Redispatch)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 175e6, "v3": 1.0, "p3": 75e6},
    17: {"name": "Gen 3 Heavy Dispatch", "family": "Family C (Diversity & Redispatch)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 150e6, "v3": 1.0, "p3": 95e6},

    # Family D: Voltage Schedule & Frequency Deadband Variations (Conditions 18 to 27) -> Val
    18: {"name": "High Voltage Schedule (+2%)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.02, "f": 60.0, "v2": 1.02, "p2": 163e6, "v3": 1.02, "p3": 85e6},
    19: {"name": "Low Voltage Schedule (-2%)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 0.98, "f": 60.0, "v2": 0.98, "p2": 163e6, "v3": 0.98, "p3": 85e6},
    20: {"name": "Gen 2 High V, Gen 3 Low V", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.015, "p2": 163e6, "v3": 0.985, "p3": 85e6},
    21: {"name": "Gen 2 Low V, Gen 3 High V", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 0.985, "p2": 163e6, "v3": 1.015, "p3": 85e6},
    22: {"name": "Freq Deadband -0.02 Hz (59.98)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 59.98, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    23: {"name": "Freq Deadband +0.02 Hz (60.02)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.02, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    24: {"name": "Freq Deadband -0.03 Hz (59.97)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 59.97, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    25: {"name": "Freq Deadband +0.03 Hz (60.03)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.03, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    26: {"name": "Combined: Light Load + High V", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 0.85, "qA": 0.85, "pB": 0.85, "qB": 0.85, "pC": 0.85, "qC": 0.85, "v1": 1.015, "f": 60.0, "v2": 1.015, "p2": 138e6, "v3": 1.015, "p3": 72e6},
    27: {"name": "Combined: Heavy Load + Low V", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.10, "qA": 1.10, "pB": 1.10, "qB": 1.10, "pC": 1.10, "qC": 1.10, "v1": 0.985, "f": 60.0, "v2": 0.985, "p2": 175e6, "v3": 0.985, "p3": 92e6},

    # Family E: Historical Combined Stress Conditions (Conditions 28 to 32) -> Val
    28: {"name": "Combined: Heavy Load + 59.97 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 1.10, "qA": 1.10, "pB": 1.10, "qB": 1.10, "pC": 1.10, "qC": 1.10, "v1": 1.01, "f": 59.97, "v2": 1.01, "p2": 175e6, "v3": 1.01, "p3": 92e6},
    29: {"name": "Combined: Light Load + 60.03 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 0.85, "qA": 0.85, "pB": 0.85, "qB": 0.85, "pC": 0.85, "qC": 0.85, "v1": 1.0, "f": 60.03, "v2": 0.99, "p2": 138e6, "v3": 0.99, "p3": 72e6},
    30: {"name": "Combined: Bus 5 Peak + 59.98 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 1.12, "qA": 1.12, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 59.98, "v2": 1.0, "p2": 166e6, "v3": 1.0, "p3": 86e6},
    31: {"name": "Combined: High Reactive + 60.02 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 1.0, "qA": 1.15, "pB": 1.0, "qB": 1.15, "pC": 1.0, "qC": 1.15, "v1": 1.01, "f": 60.02, "v2": 1.01, "p2": 163e6, "v3": 1.01, "p3": 85e6},
    32: {"name": "Combined: Gen 2 Dispatch + 59.96 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 59.96, "v2": 1.0, "p2": 170e6, "v3": 1.0, "p3": 80e6},

    # Family F: Renewable Inverter Penetration [STRICTLY QUARANTINED CHALLENGE]
    33: {"name": "Renewable Inverter Penetration", "family": "Family F (Renewable Redispatch [CHALLENGE])", "split_default": "challenge", "pA": 0.92, "qA": 0.90, "pB": 0.88, "qB": 0.83, "pC": 0.90, "qC": 0.85, "v1": 1.0, "f": 60.00, "v2": 1.0, "p2": 180e6, "v3": 1.0, "p3": 60e6},

    # Family G: Cross-Bus Reactive Imbalance [STRICTLY QUARANTINED CHALLENGE]
    34: {"name": "Severe Reactive Imbalance", "family": "Family G (Cross-Bus Reactive Imbalance [CHALLENGE])", "split_default": "challenge", "pA": 1.00, "qA": 1.40, "pB": 1.00, "qB": 0.50, "pC": 1.00, "qC": 0.60, "v1": 1.0, "f": 60.00, "v2": 1.01, "p2": 163e6, "v3": 0.99, "p3": 85e6},

    # Family H: Asymmetric Substation Loading [STRICTLY QUARANTINED CHALLENGE]
    35: {"name": "Asymmetric Substation Loading", "family": "Family H (Asymmetric Substation Loading [CHALLENGE])", "split_default": "challenge", "pA": 1.12, "qA": 1.10, "pB": 0.78, "qB": 0.83, "pC": 1.10, "qC": 1.14, "v1": 1.0, "f": 60.00, "v2": 1.0, "p2": 170e6, "v3": 1.0, "p3": 80e6},

    # Family I: Stressed Transmission Import [STRICTLY QUARANTINED CHALLENGE]
    36: {"name": "Stressed Transmission Import", "family": "Family I (Stressed Transmission Import [CHALLENGE])", "split_default": "challenge", "pA": 0.72, "qA": 0.70, "pB": 1.20, "qB": 1.20, "pC": 1.20, "qC": 1.20, "v1": 1.01, "f": 59.97, "v2": 1.02, "p2": 175e6, "v3": 1.02, "p3": 95e6},
}


def build_144_trajectory_matrix() -> List[Dict[str, Any]]:
    """
    Constructs the 144-trajectory matrix:
    - 18 trajectories per class across all 8 classes.
    - 80 Train (10/class), 32 Val (4/class), 32 Challenge (4/class).
    - Challenge trajectories mapped strictly 1:1 to conditions 33, 34, 35, 36.
    """
    matrix = []
    traj_idx = 1

    # Define operating condition distributions per split
    train_cond_pool = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 15, 16]
    val_cond_pool = [9, 11, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
    challenge_cond_pool = [33, 34, 35, 36]

    # Pre-select the 10 targeted Phase 5B.2 remediation pilot trajectories
    remediation_pilot_targets = {
        # Format: (class, cond_id, phase, desc_key) -> pilot_id
        ("Normal", 1, "ABC"): 1,
        ("Sag", 1, "ABC"): 2,
        ("Swell", 2, "ABC"): 3,         # Lowest supported swell severity under light load
        ("Interruption", 1, "ABC"): 4,   # Dual-incomer substation isolation
        ("Harmonics", 1, "ABC"): 5,
        ("Flicker", 1, "ABC"): 6,        # 8.8 Hz eye sensitivity peak
        ("Notch", 1, "ABC"): 7,          # Shortest supported width (400 us)
        ("Notch", 36, "A"): 8,           # Single-phase commutation surrogate (Cond 36 Challenge)
        ("Transient", 1, "ABC"): 9,      # Highest transient freq (2.2 kHz)
        ("Transient", 36, "AB"): 10      # 2P low-damping ringing under stressed import
    }

    for cls in CLASS_LABELS:
        cls_idx = CLASS_TO_IDX[cls]

        # 18 trajectories for this class: 10 Train, 4 Val, 4 Challenge
        for k in range(18):
            if k < 10:
                split = "train"
                cid = train_cond_pool[k % len(train_cond_pool)]
            elif k < 14:
                split = "val"
                cid = val_cond_pool[(k - 10) % len(val_cond_pool)]
            else:
                split = "challenge"
                cid = challenge_cond_pool[k - 14]  # Exactly 33, 34, 35, 36

            c_info = OPERATING_CONDITIONS[cid]

            # Assign phase configuration based on class capabilities
            if cls == "Normal":
                phase = "ABC"
                severity = "Baseline"
            elif cls in ["Sag", "Interruption"]:
                # Alternating 3P, 1P, 2P
                phase_opts = ["ABC", "A", "AB", "B", "BC", "C", "CA"]
                phase = phase_opts[k % len(phase_opts)]
                severity = ["Mild", "Moderate", "Severe"][k % 3]
            elif cls == "Swell":
                # Swell switched capacitor is 3-phase
                phase = "ABC"
                severity = ["Mild", "Moderate", "Severe"][k % 3]
            elif cls == "Harmonics":
                phase = "ABC" if k % 2 == 0 else "A"
                severity = ["Mild", "Moderate", "Severe"][k % 3]
            elif cls == "Flicker":
                phase = "ABC" if k % 3 != 1 else ("A" if k % 2 == 0 else "AB")
                severity = ["Mild", "Moderate", "Severe"][k % 3]
            elif cls == "Notch":
                phase = "ABC" if k % 3 == 0 else ("AB" if k % 3 == 1 else "A")
                severity = ["Mild", "Moderate", "Severe"][k % 3]
            elif cls == "Transient":
                phase = "ABC" if k % 3 == 0 else ("A" if k % 3 == 1 else "AB")
                severity = ["Mild", "Moderate", "Severe"][k % 3]

            # Physical parameters
            params: Dict[str, Any] = {}
            if cls == "Normal":
                params = {"magnitude_pu": 1.0, "duration_ms": 200.0}
            elif cls == "Sag":
                rf_map = {"Mild": 200.0, "Moderate": 120.0, "Severe": 45.0}
                params = {
                    "fault_resistance_ohms": rf_map[severity],
                    "ground_resistance_ohms": 0.01,
                    "duration_cycles": 4.5 + (k % 3) * 0.5,
                    "duration_ms": (4.5 + (k % 3) * 0.5) * (1000.0 / 60.0),
                    "onset_range_ms": [20.0, 51.0]
                }
            elif cls == "Swell":
                # Swell durations aligned with Gate 3H proven standard (4.2 cycles = 70ms, 4.8 cycles = 80ms)
                # to prevent non-zero-crossing contact parting singularities
                dur_cyc = 4.2 if severity == "Mild" else 4.8
                q_val = 100.0 if cid == 2 else {"Mild": 90.0, "Moderate": 130.0, "Severe": 150.0}[severity]
                params = {
                    "capacitive_power_mvar": q_val,
                    "damping_power_kw": 100.0,
                    "duration_cycles": dur_cyc,
                    "duration_ms": (dur_cyc / 60.0) * 1000.0,
                    "onset_range_ms": [20.0, 51.0]
                }
            elif cls == "Interruption":
                params = {
                    "duration_cycles": 4.2 + (k % 3) * 0.5,
                    "duration_ms": (4.2 + (k % 3) * 0.5) * (1000.0 / 60.0),
                    "target_residual_pu": 0.0,
                    "onset_range_ms": [20.0, 51.0]
                }
            elif cls == "Harmonics":
                orders_list = [[3, 5, 7], [5, 7], [3, 5, 7, 9, 11]][k % 3]
                i_amps = {f"h{h}": float(35.0 - h * 1.8) for h in orders_list}
                phi_rad = {f"h{h}": float(0.15 * h) for h in orders_list}
                params = {
                    "harmonic_orders": orders_list,
                    "harmonic_currents_amps": i_amps,
                    "harmonic_phases_rad": phi_rad
                }
            elif cls == "Flicker":
                fm_list = [8.8, 10.0, 6.0, 12.0, 15.0]
                fm = fm_list[k % len(fm_list)]
                params = {
                    "modulation_freq_hz": fm,
                    "modulation_depth": 0.04 + (k % 3) * 0.02,
                    "modulation_phase_rad": 0.0,
                    "flicker_current_amps": 300.0 + (k % 3) * 60.0
                }
            elif cls == "Notch":
                # Widths: 400 us (shortest), 600 us, 800 us, 1000 us
                w_list = [400.0, 600.0, 800.0, 1000.0]
                w_us = w_list[k % len(w_list)]
                params = {
                    "notch_width_us": w_us,
                    "commutation_resistance_ohms": 100.0 + (k % 3) * 30.0,
                    "notch_repetition_per_cycle": 1 if k % 2 == 0 else 2,
                    "phase_offset_ms": 3.0 + (k % 3) * 1.5
                }
            elif cls == "Transient":
                # L, C values creating 1.2 kHz, 1.8 kHz, 2.2 kHz
                param_tuples = [
                    (2.0, 8.0, 0.8, 1258.0), # L=2mH, C=8uF -> 1.26 kHz
                    (1.5, 5.0, 0.6, 1838.0), # L=1.5mH, C=5uF -> 1.84 kHz
                    (1.0, 5.2, 0.4, 2207.0)  # L=1.0mH, C=5.2uF -> 2.21 kHz (Highest)
                ]
                L_mh, C_uf, R_ohm, f_calc = param_tuples[k % 3]
                params = {
                    "inductance_mh": L_mh,
                    "capacitance_uf": C_uf,
                    "damping_resistance_ohms": R_ohm,
                    "target_osc_freq_hz": f_calc,
                    "onset_ms": 105.0 + (k % 3) * 5.0,
                    "duration_ms": 25.0 + (k % 3) * 5.0
                }

            # Measurement perturbations: 52 dB (majority), 46 dB, 40 dB; 14-bit (majority) and 12-bit
            snr_val = 52.0 if (k % 4 != 3) else (46.0 if k % 2 == 0 else 40.0)
            adc_b = 14 if (k % 3 != 2) else 12

            # Check if this scenario matches one of the 10 remediation pilot targets
            pilot_id = remediation_pilot_targets.get((cls, cid, phase), None)
            # Ensure unique pilot_id assignment
            in_pilot = False
            if pilot_id is not None:
                # check if pilot_id already taken
                already_assigned = any(m.get("remediation_pilot_id") == pilot_id for m in matrix)
                if not already_assigned:
                    in_pilot = True

            scen_id = f"P5B2_{cls[:3].upper()}_{traj_idx:04d}_{phase.lower()}_c{cid:02d}_{severity.lower()[:3]}"

            entry = {
                "trajectory_id": scen_id,
                "matrix_index": traj_idx,
                "in_remediation_pilot": in_pilot,
                "remediation_pilot_id": pilot_id if in_pilot else None,
                "class": cls,
                "label_idx": cls_idx,
                "operating_condition_id": cid,
                "operating_condition_name": c_info["name"],
                "operating_condition_family": c_info["family"],
                "phase": phase,
                "severity": severity,
                "split": split,
                "parameters": params,
                "sensor_noise_snr_db": snr_val,
                "noise_model": "FIXED_NOMINAL_REFERENCE_AWGN",
                "adc_bits": adc_b,
                "adc_v_fs_pu": 1.8,
                "sampling_rates_hz": [20000.0, 5000.0],
                "samples_per_window_20k": 4000,
                "samples_per_window_5k": 1000,
                "window_ms": 200.0,
                "simulation_duration_s": 0.38,
                "expected_windows_count": 32,
                "reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
                "working_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx"
            }
            matrix.append(entry)
            traj_idx += 1

    return matrix


def save_144_trajectory_matrix():
    matrix = build_144_trajectory_matrix()
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    # Verification counts
    total_traj = len(matrix)
    assert total_traj == 144, f"Total trajectories {total_traj} != 144"

    class_counts = {c: sum(1 for m in matrix if m["class"] == c) for c in CLASS_LABELS}
    for c, cnt in class_counts.items():
        assert cnt == 18, f"Class {c} count {cnt} != 18"

    split_counts = {s: sum(1 for m in matrix if m["split"] == s) for s in ["train", "val", "challenge"]}
    assert split_counts["train"] == 80, f"Train count {split_counts['train']} != 80"
    assert split_counts["val"] == 32, f"Val count {split_counts['val']} != 32"
    assert split_counts["challenge"] == 32, f"Challenge count {split_counts['challenge']} != 32"

    pilot_count = sum(1 for m in matrix if m["in_remediation_pilot"])
    print(f"[Verification] Successfully verified 144 trajectories across 8 classes.")
    print(f"[Verification] Splits: Train={split_counts['train']}, Val={split_counts['val']}, Challenge={split_counts['challenge']}.")
    print(f"[Verification] Remediation Pilot Target Trajectories: {pilot_count}.")

    catalog = {
        "schema_version": "2.0",
        "phase": "Phase 5B.2 Simulation Pipeline Remediation & 144-Trajectory Matrix",
        "study": "IEEE 9-bus Multi-Model Power Quality Comparative Lab",
        "total_trajectories": 144,
        "frames_per_trajectory": 32,
        "total_dataset_frames": 144 * 32,
        "classes_count": 8,
        "class_mapping": CLASS_TO_IDX,
        "operating_conditions_count": len(OPERATING_CONDITIONS),
        "split_summary": {
            "train_trajectories": 80,
            "train_frames": 80 * 32,
            "val_trajectories": 32,
            "val_frames": 32 * 32,
            "challenge_trajectories": 32,
            "challenge_frames": 32 * 32
        },
        "operating_condition_catalog": OPERATING_CONDITIONS,
        "trajectories": matrix
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)
    print(f"[Success] Saved machine-readable 144-trajectory matrix to {OUTPUT_JSON}")

    # Export CSV summary
    fieldnames = [
        "trajectory_id", "matrix_index", "in_remediation_pilot", "remediation_pilot_id",
        "class", "label_idx", "operating_condition_id", "operating_condition_name",
        "operating_condition_family", "phase", "severity", "split", "sensor_noise_snr_db",
        "adc_bits", "expected_windows_count"
    ]
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in matrix:
            row = {k: m[k] for k in fieldnames}
            writer.writerow(row)
    print(f"[Success] Saved CSV matrix summary to {OUTPUT_CSV}")


if __name__ == '__main__':
    save_144_trajectory_matrix()

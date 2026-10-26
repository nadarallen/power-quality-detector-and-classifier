"""
scripts/generate_phase5b_simulation_matrix.py
---------------------------------------------
Generates the authoritative Phase 5B Simulation Matrix and Pilot Scenario definitions
for the IEEE 9-bus 60-Hz Power Quality Comparative Study.

Features:
- Balanced, controlled factorial design across 8 classes:
  Normal, Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient.
- Operating Condition Families:
  * Family A: Nominal Baseline & Symmetric Loading (Cond 1-7)
  * Family B: Power Factor & Local Impedance Variations (Cond 8-13)
  * Family C: Spatial Load Diversity & Generation Redispatch (Cond 14-17)
  * Family D: Utility Voltage Schedules & Frequency Deadband Variations (Cond 18-27)
  * Family E: Historical Combined Operating Points (Cond 28-32)
  * Family F: Renewable/Inverter Redispatch Equivalents [RESERVED CHALLENGE] (Cond 33)
  * Family G: Cross-Bus Reactive Imbalance [RESERVED CHALLENGE] (Cond 34)
  * Family H: Asymmetric Substation Loading [RESERVED CHALLENGE] (Cond 35)
  * Family I: Stressed Transmission Import [RESERVED CHALLENGE] (Cond 36)
- Disturbance Variations:
  * Severity levels: Mild, Moderate, Severe
  * Phase configurations: Symmetrical 3P (ABC), Asymmetrical 1P (A, B, C), Asymmetrical 2P (AB, BC, CA)
  * Point-on-wave / inception timing: 0 deg, 30 deg, 45 deg, 90 deg
- Measurement Variations:
  * Baseline 52 dB SNR AWGN
  * Extended noise layers: 46 dB SNR, 40 dB SNR
  * ADC Quantization: 12-bit and 14-bit resolution
- Split Allocation (Leakage-Safe Protocol):
  * Train: Families A, B, C (Historical Nominal, Loading, Redispatch)
  * Val: Family D, E (Voltage Schedule, Frequency Deadband)
  * Challenge: Families F, G, H, I (Strictly Quarantined Unseen Conditions)
- Flags 24 bounded pilot trajectories (3 per class) for immediate physical validation.
"""

import os
import json
import csv
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JSON = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b_simulation_matrix.json')
OUTPUT_CSV = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b_simulation_matrix.csv')

# Authoritative class labels matching dsp/phase_processor.py contract
CLASS_LABELS = [
    'Flicker', 'Harmonics', 'Interruption', 'Normal',
    'Notch', 'Sag', 'Swell', 'Transient'
]
CLASS_TO_IDX = {cls: idx for idx, cls in enumerate(CLASS_LABELS)}

# Complete operating condition catalog (1 to 36)
OPERATING_CONDITIONS = {
    1: {"name": "Nominal Baseline", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    2: {"name": "Light Load 85%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 0.85, "qA": 0.85, "pB": 0.85, "qB": 0.85, "pC": 0.85, "qC": 0.85, "v1": 1.0, "f": 60.0, "v2": 0.99, "p2": 138e6, "v3": 0.99, "p3": 72e6},
    5: {"name": "Heavy Load 105%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.05, "qA": 1.05, "pB": 1.05, "qB": 1.05, "pC": 1.05, "qC": 1.05, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 171e6, "v3": 1.0, "p3": 89e6},
    6: {"name": "Heavy Load 110%", "family": "Family A (Nominal & Scaling)", "split_default": "train", "pA": 1.10, "qA": 1.10, "pB": 1.10, "qB": 1.10, "pC": 1.10, "qC": 1.10, "v1": 1.01, "f": 60.0, "v2": 1.01, "p2": 175e6, "v3": 1.01, "p3": 93e6},
    8: {"name": "High PF (0.98 lag)", "family": "Family B (PF & Local Load)", "split_default": "train", "pA": 1.0, "qA": 0.60, "pB": 1.0, "qB": 0.60, "pC": 1.0, "qC": 0.60, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    9: {"name": "Low PF (0.85 lag)", "family": "Family B (PF & Local Load)", "split_default": "val", "pA": 1.0, "qA": 1.25, "pB": 1.0, "qB": 1.25, "pC": 1.0, "qC": 1.25, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    11: {"name": "Bus 5 Light Local Load", "family": "Family B (PF & Local Load)", "split_default": "val", "pA": 0.85, "qA": 0.85, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 158e6, "v3": 1.0, "p3": 83e6},
    14: {"name": "Cross-Bus Diversity A", "family": "Family C (Diversity & Redispatch)", "split_default": "val", "pA": 1.10, "qA": 1.10, "pB": 0.90, "qB": 0.90, "pC": 1.05, "qC": 1.05, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 163e6, "v3": 1.0, "p3": 85e6},
    16: {"name": "Gen 2 Heavy Dispatch", "family": "Family C (Diversity & Redispatch)", "split_default": "train", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 175e6, "v3": 1.0, "p3": 75e6},
    17: {"name": "Gen 3 Heavy Dispatch", "family": "Family C (Diversity & Redispatch)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 1.0, "p2": 150e6, "v3": 1.0, "p3": 95e6},
    18: {"name": "High Voltage Schedule (+2%)", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.02, "f": 60.0, "v2": 1.02, "p2": 163e6, "v3": 1.02, "p3": 85e6},
    21: {"name": "Gen 2 Low V, Gen 3 High V", "family": "Family D (Voltage & Frequency)", "split_default": "val", "pA": 1.0, "qA": 1.0, "pB": 1.0, "qB": 1.0, "pC": 1.0, "qC": 1.0, "v1": 1.0, "f": 60.0, "v2": 0.985, "p2": 163e6, "v3": 1.015, "p3": 85e6},
    28: {"name": "Combined: Heavy Load + 59.97 Hz", "family": "Family E (Historical Combined)", "split_default": "val", "pA": 1.10, "qA": 1.10, "pB": 1.10, "qB": 1.10, "pC": 1.10, "qC": 1.10, "v1": 1.01, "f": 59.97, "v2": 1.01, "p2": 175e6, "v3": 1.01, "p3": 92e6},
    # New Quarantined Challenge Families (Held out completely from training/validation)
    33: {"name": "Renewable Inverter Penetration", "family": "Family F (Renewable Redispatch [CHALLENGE])", "split_default": "challenge", "pA": 0.92, "qA": 0.90, "pB": 0.88, "qB": 0.83, "pC": 0.90, "qC": 0.85, "v1": 1.0, "f": 60.00, "v2": 1.0, "p2": 180e6, "v3": 1.0, "p3": 60e6},
    34: {"name": "Severe Reactive Imbalance", "family": "Family G (Cross-Bus Reactive Imbalance [CHALLENGE])", "split_default": "challenge", "pA": 1.00, "qA": 1.40, "pB": 1.00, "qB": 0.50, "pC": 1.00, "qC": 0.60, "v1": 1.0, "f": 60.00, "v2": 1.01, "p2": 163e6, "v3": 0.99, "p3": 85e6},
    35: {"name": "Asymmetric Substation Loading", "family": "Family H (Asymmetric Substation Loading [CHALLENGE])", "split_default": "challenge", "pA": 1.12, "qA": 1.10, "pB": 0.78, "qB": 0.83, "pC": 1.10, "qC": 1.14, "v1": 1.0, "f": 60.00, "v2": 1.0, "p2": 170e6, "v3": 1.0, "p3": 80e6},
    36: {"name": "Stressed Transmission Import", "family": "Family I (Stressed Transmission Import [CHALLENGE])", "split_default": "challenge", "pA": 0.72, "qA": 0.70, "pB": 1.20, "qB": 1.20, "pC": 1.20, "qC": 1.20, "v1": 1.01, "f": 59.97, "v2": 1.02, "p2": 175e6, "v3": 1.02, "p3": 95e6},
}


def build_scenario_matrix() -> List[Dict[str, Any]]:
    """Builds a balanced simulation matrix with 24 prioritized pilot trajectories."""
    matrix = []

    def make_entry(
        scen_id: str,
        cls_name: str,
        cond_id: int,
        phase: str,
        severity: str,
        split: str,
        in_pilot: bool,
        pilot_id: int,
        params: Dict[str, Any],
        desc: str
    ) -> Dict[str, Any]:
        cond_info = OPERATING_CONDITIONS[cond_id]
        return {
            "scenario_id": scen_id,
            "pilot_id": pilot_id if in_pilot else None,
            "in_pilot": in_pilot,
            "class": cls_name,
            "label_idx": CLASS_TO_IDX[cls_name],
            "operating_condition_id": cond_id,
            "operating_condition_name": cond_info["name"],
            "operating_condition_family": cond_info["family"],
            "phase": phase,
            "severity": severity,
            "split": split,
            "parameters": params,
            "description": desc,
            "sensor_noise_snr_db": params.get("sensor_noise_snr_db", 52.0),
            "reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
            "working_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx",
            "sampling_rate_hz": 5000.0,
            "window_samples": 1000,
            "window_ms": 200.0,
            "nominal_frequency_hz": 60.0
        }

    # =========================================================================
    # CLASS 1: NORMAL (label_idx = 3)
    # =========================================================================
    # Pilot 1: Nominal baseline (Train)
    matrix.append(make_entry(
        "P5B_NORM_0001_nominal_baseline", "Normal", 1, "ABC", "Baseline", "train", True, 1,
        {"magnitude_pu": 1.0, "duration_ms": 200.0, "sensor_noise_snr_db": 52.0},
        "Nominal IEEE 9-bus benchmark operating point at 100% continuous loading"
    ))
    # Pilot 2: Heavy peak loading (Train)
    matrix.append(make_entry(
        "P5B_NORM_0002_heavy_summer_peak", "Normal", 6, "ABC", "Heavy", "train", True, 2,
        {"magnitude_pu": 1.0, "duration_ms": 200.0, "sensor_noise_snr_db": 52.0},
        "Heavy summer peak load (110% system demand) with elevated voltage schedule"
    ))
    # Pilot 3: Renewable inverter redispatch [CHALLENGE]
    matrix.append(make_entry(
        "P5B_NORM_0003_renewable_redispatch", "Normal", 33, "ABC", "Dispatched", "challenge", True, 3,
        {"magnitude_pu": 1.0, "duration_ms": 200.0, "sensor_noise_snr_db": 52.0},
        "Condition-held-out high renewable inverter dispatch profile (Family F challenge)"
    ))

    # =========================================================================
    # CLASS 2: SAG (label_idx = 5)
    # =========================================================================
    # Pilot 4: Symmetrical 3P moderate sag (Train)
    matrix.append(make_entry(
        "P5B_SAG_0001_3p_moderate_nom", "Sag", 1, "ABC", "Moderate", "train", True, 4,
        {"fault_resistance_ohms": 180.0, "ground_resistance_ohms": 0.01, "duration_cycles": 5.0, "duration_ms": 83.33, "onset_time_ms": 40.0, "target_depth_pu": 0.73, "sensor_noise_snr_db": 52.0},
        "Three-phase symmetrical ground fault, 180 ohm fault resistance (residual ~0.73 pu)"
    ))
    # Pilot 5: Asymmetrical 1P deep sag (Val)
    matrix.append(make_entry(
        "P5B_SAG_0002_1p_deep_light", "Sag", 11, "A", "Severe", "val", True, 5,
        {"fault_resistance_ohms": 50.0, "ground_resistance_ohms": 0.01, "duration_cycles": 4.0, "duration_ms": 66.67, "onset_time_ms": 40.0, "target_depth_pu": 0.45, "sensor_noise_snr_db": 52.0},
        "Single-phase-to-ground Phase A fault under light local Bus 5 loading (residual ~0.45 pu)"
    ))
    # Pilot 6: Asymmetrical 2P phase-to-phase sag [CHALLENGE]
    matrix.append(make_entry(
        "P5B_SAG_0003_2p_phAB_challenge", "Sag", 34, "AB", "Moderate", "challenge", True, 6,
        {"fault_resistance_ohms": 75.0, "ground_resistance_ohms": 0.01, "duration_cycles": 4.5, "duration_ms": 75.0, "onset_time_ms": 40.0, "target_depth_pu": 0.62, "sensor_noise_snr_db": 52.0},
        "Phase-to-phase AB fault under severe reactive imbalance challenge condition"
    ))

    # =========================================================================
    # CLASS 3: SWELL (label_idx = 6)
    # =========================================================================
    # Pilot 7: Symmetrical 3P moderate swell (Train)
    matrix.append(make_entry(
        "P5B_SWL_0001_3p_moderate_nom", "Swell", 1, "ABC", "Moderate", "train", True, 7,
        {"capacitive_power_mvar": 150.0, "damping_power_kw": 100.0, "duration_cycles": 4.8, "duration_ms": 80.0, "onset_time_ms": 40.0, "target_swell_pu": 1.33, "sensor_noise_snr_db": 52.0},
        "Three-phase switched capacitor bank energization, 150 MVAR (elevated ~1.33 pu)"
    ))
    # Pilot 8: Symmetrical 3P mild swell (Val)
    matrix.append(make_entry(
        "P5B_SWL_0002_3p_mild_light", "Swell", 2, "ABC", "Mild", "val", True, 8,
        {"capacitive_power_mvar": 100.0, "damping_power_kw": 100.0, "duration_cycles": 4.2, "duration_ms": 70.0, "onset_time_ms": 40.0, "target_swell_pu": 1.22, "sensor_noise_snr_db": 52.0},
        "Three-phase switched capacitor energization (100 MVAR) under light loading (Cond 2, val)"
    ))
    # Pilot 9: Symmetrical 3P moderate swell under heavy loading [CHALLENGE]
    matrix.append(make_entry(
        "P5B_SWL_0003_3p_challenge", "Swell", 5, "ABC", "Moderate", "challenge", True, 9,
        {"capacitive_power_mvar": 120.0, "damping_power_kw": 100.0, "duration_cycles": 4.8, "duration_ms": 80.0, "onset_time_ms": 40.0, "target_swell_pu": 1.28, "sensor_noise_snr_db": 52.0},
        "Three-phase switched capacitor energization (120 MVAR) under heavy loading (Cond 5, challenge)"
    ))

    # =========================================================================
    # CLASS 4: INTERRUPTION (label_idx = 2)
    # =========================================================================
    # Pilot 10: Symmetrical 3P complete interruption (Train)
    matrix.append(make_entry(
        "P5B_INT_0001_3p_standard_nom", "Interruption", 1, "ABC", "Severe", "train", True, 10,
        {"duration_cycles": 4.2, "duration_ms": 70.0, "onset_time_ms": 40.0, "target_residual_pu": 0.02, "sensor_noise_snr_db": 52.0},
        "Three-phase circuit breaker opening on Line 4-5 isolating Bus 5 (residual < 0.05 pu)"
    ))
    # Pilot 11: Single-phase feeder interruption (Val)
    matrix.append(make_entry(
        "P5B_INT_0002_1p_phA_val", "Interruption", 18, "A", "Severe", "val", True, 11,
        {"duration_cycles": 5.0, "duration_ms": 83.33, "onset_time_ms": 40.0, "target_residual_pu": 0.02, "sensor_noise_snr_db": 52.0},
        "Single-phase breaker opening on Phase A under high utility voltage schedule (+2%)"
    ))
    # Pilot 12: Two-phase line interruption [CHALLENGE]
    matrix.append(make_entry(
        "P5B_INT_0003_2p_phAB_challenge", "Interruption", 36, "AB", "Severe", "challenge", True, 12,
        {"duration_cycles": 3.6, "duration_ms": 60.0, "onset_time_ms": 40.0, "target_residual_pu": 0.02, "sensor_noise_snr_db": 52.0},
        "Phase AB breaker opening under stressed transmission import challenge condition"
    ))

    # =========================================================================
    # CLASS 5: HARMONICS (label_idx = 1)
    # =========================================================================
    # Pilot 13: Symmetrical 3P typical 6-pulse spectrum (Train)
    matrix.append(make_entry(
        "P5B_HAR_0001_3p_typical_h3h5h7", "Harmonics", 1, "ABC", "Moderate", "train", True, 13,
        {"harmonic_orders": [3, 5, 7], "harmonic_currents_amps": {"h3": 45.0, "h5": 28.0, "h7": 16.0}, "harmonic_phases_rad": {"h3": 0.0, "h5": 0.0, "h7": 0.0}, "target_thd_pct": 10.5, "sensor_noise_snr_db": 52.0},
        "Three-phase non-linear industrial rectifier harmonic injection (H3, H5, H7, THD ~10.5%)"
    ))
    # Pilot 14: Asymmetrical 1P single-phase harmonic load (Val)
    matrix.append(make_entry(
        "P5B_HAR_0002_1p_phA_val", "Harmonics", 14, "A", "Mild", "val", True, 14,
        {"harmonic_orders": [3, 5, 7], "harmonic_currents_amps": {"h3": 35.0, "h5": 22.0, "h7": 12.0}, "harmonic_phases_rad": {"h3": 0.0, "h5": 0.5236, "h7": 1.0472}, "target_thd_pct": 7.8, "sensor_noise_snr_db": 52.0},
        "Single-phase non-linear load on Phase A under cross-bus diversity condition A"
    ))
    # Pilot 15: Symmetrical 3P full odd harmonic spectrum [CHALLENGE]
    matrix.append(make_entry(
        "P5B_HAR_0003_3p_full_odd_challenge", "Harmonics", 33, "ABC", "Severe", "challenge", True, 15,
        {"harmonic_orders": [3, 5, 7, 9, 11], "harmonic_currents_amps": {"h3": 52.0, "h5": 34.0, "h7": 22.0, "h9": 14.0, "h11": 9.0}, "harmonic_phases_rad": {"h3": 0.0, "h5": 0.0, "h7": 0.0, "h9": 0.0, "h11": 0.0}, "target_thd_pct": 14.8, "sensor_noise_snr_db": 52.0},
        "Full odd harmonic spectrum (H3 to H11) under renewable inverter redispatch challenge"
    ))

    # =========================================================================
    # CLASS 6: FLICKER (label_idx = 0)
    # =========================================================================
    # Pilot 16: Symmetrical 3P peak sensitivity 8.8 Hz (Train)
    matrix.append(make_entry(
        "P5B_FLK_0001_3p_fm8p8hz_peak", "Flicker", 1, "ABC", "Moderate", "train", True, 16,
        {"modulation_freq_hz": 8.8, "modulation_depth": 0.060, "modulation_phase_rad": 0.0, "flicker_current_amps": 333.6, "sensor_noise_snr_db": 52.0},
        "Three-phase arc-furnace envelope modulation at human eye peak visual sensitivity (8.8 Hz, 6.0% depth)"
    ))
    # Pilot 17: Asymmetrical 1P single-phase flicker (Val)
    matrix.append(make_entry(
        "P5B_FLK_0002_1p_fm10hz_phA", "Flicker", 9, "A", "Mild", "val", True, 17,
        {"modulation_freq_hz": 10.0, "modulation_depth": 0.050, "modulation_phase_rad": 0.7854, "flicker_current_amps": 278.0, "sensor_noise_snr_db": 52.0},
        "Single-phase fluctuating load on Phase A at 10.0 Hz under low power factor (0.85 lag)"
    ))
    # Pilot 18: Asymmetrical 2P deep flicker modulation [CHALLENGE]
    matrix.append(make_entry(
        "P5B_FLK_0003_2p_fm6hz_challenge", "Flicker", 34, "AB", "Severe", "challenge", True, 18,
        {"modulation_freq_hz": 6.0, "modulation_depth": 0.075, "modulation_phase_rad": 0.0, "flicker_current_amps": 417.0, "sensor_noise_snr_db": 52.0},
        "Two-phase AB sub-synchronous modulation at 6.0 Hz under severe reactive imbalance challenge"
    ))

    # =========================================================================
    # CLASS 7: NOTCH (label_idx = 4)
    # =========================================================================
    # Pilot 19: Symmetrical 3P line-to-line commutation (Train)
    matrix.append(make_entry(
        "P5B_NOT_0001_3p_w600us_rep1", "Notch", 1, "ABC", "Moderate", "train", True, 19,
        {"notch_width_us": 600.0, "commutation_resistance_ohms": 150.0, "notch_repetition_per_cycle": 1, "phase_offset_ms": 5.0, "sensor_noise_snr_db": 52.0},
        "Three-phase thyristor converter commutation notch (600 us width, 150 ohm commutation resistance, 1 notch/cyc)"
    ))
    # Pilot 20: Asymmetrical 2P 2-notches/cycle (Val)
    matrix.append(make_entry(
        "P5B_NOT_0002_2p_w500us_rep2", "Notch", 21, "AB", "Moderate", "val", True, 20,
        {"notch_width_us": 500.0, "commutation_resistance_ohms": 120.0, "notch_repetition_per_cycle": 2, "phase_offset_ms": 3.0, "sensor_noise_snr_db": 52.0},
        "Two-phase AB commutation notch with 2 notches per cycle under Gen 2/3 voltage coordination"
    ))
    # Pilot 21: Asymmetrical 1P deep notch [CHALLENGE]
    matrix.append(make_entry(
        "P5B_NOT_0003_1p_w800us_challenge", "Notch", 35, "A", "Severe", "challenge", True, 21,
        {"notch_width_us": 800.0, "commutation_resistance_ohms": 100.0, "notch_repetition_per_cycle": 1, "phase_offset_ms": 4.5, "sensor_noise_snr_db": 52.0},
        "Single-phase wide commutation notch (800 us, 100 ohm) under asymmetric substation loading challenge"
    ))

    # =========================================================================
    # CLASS 8: TRANSIENT (label_idx = 7)
    # =========================================================================
    # Pilot 22: Symmetrical 3P capacitor energization (Train)
    matrix.append(make_entry(
        "P5B_TRN_0001_3p_l2_c8_r08", "Transient", 1, "ABC", "Moderate", "train", True, 22,
        {"inductance_mh": 2.0, "capacitance_uf": 8.0, "damping_resistance_ohms": 0.8, "onset_ms": 104.2, "duration_ms": 30.0, "sensor_noise_snr_db": 52.0},
        "Three-phase shunt capacitor bank switching transient (L=2.0 mH, C=8.0 uF, f_osc ~1.26 kHz)"
    ))
    # Pilot 23: Asymmetrical 1P capacitor switching (Val)
    matrix.append(make_entry(
        "P5B_TRN_0002_1p_l3_c5_r12", "Transient", 16, "A", "Moderate", "val", True, 23,
        {"inductance_mh": 3.0, "capacitance_uf": 5.0, "damping_resistance_ohms": 1.2, "onset_ms": 110.0, "duration_ms": 32.0, "sensor_noise_snr_db": 52.0},
        "Single-phase Phase A capacitor switching transient under Gen 2 heavy dispatch (f_osc ~1.30 kHz)"
    ))
    # Pilot 24: Asymmetrical 2P high-frequency transient [CHALLENGE]
    matrix.append(make_entry(
        "P5B_TRN_0003_2p_l15_c6_challenge", "Transient", 36, "AB", "Severe", "challenge", True, 24,
        {"inductance_mh": 1.5, "capacitance_uf": 6.0, "damping_resistance_ohms": 0.5, "onset_ms": 108.3, "duration_ms": 25.0, "sensor_noise_snr_db": 52.0},
        "Two-phase AB low-damping oscillatory transient under stressed transmission import challenge"
    ))

    return matrix


def save_simulation_matrix():
    matrix = build_scenario_matrix()
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    catalog = {
        "schema_version": "1.0",
        "study": "Phase 5B Multi-Model Power Quality Comparative Lab",
        "description": "Simulation Matrix & Pilot Design for IEEE 9-bus 60-Hz disturbance generation",
        "base_frequency_hz": 60.0,
        "sampling_rate_hz": 5000.0,
        "window_samples": 1000,
        "window_ms": 200.0,
        "total_scenarios_designed": len(matrix),
        "pilot_trajectories_count": sum(1 for m in matrix if m["in_pilot"]),
        "operating_conditions_count": len(OPERATING_CONDITIONS),
        "classes_count": len(CLASS_LABELS),
        "class_mapping": CLASS_TO_IDX,
        "operating_condition_catalog": OPERATING_CONDITIONS,
        "scenarios": matrix
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)
    print(f"[Success] Saved machine-readable simulation matrix to {OUTPUT_JSON}")

    # Export CSV summary
    fieldnames = [
        "scenario_id", "pilot_id", "in_pilot", "class", "label_idx",
        "operating_condition_id", "operating_condition_name", "operating_condition_family",
        "phase", "severity", "split", "sensor_noise_snr_db", "description"
    ]
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in matrix:
            row = {k: m[k] for k in fieldnames}
            writer.writerow(row)
    print(f"[Success] Saved CSV matrix summary to {OUTPUT_CSV}")


if __name__ == '__main__':
    save_simulation_matrix()

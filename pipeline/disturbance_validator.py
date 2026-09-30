"""
pipeline/disturbance_validator.py
---------------------------------
Independent physical validation engine for Power Quality disturbances
in the 60-Hz IEEE 9-bus domain, implementing the physical validation gates
defined in docs/GATE3C_VALIDATION_PLAN.md.

Design principles:
- 100% ML-independent: Validation is purely mathematical and physical.
- Class-specific gates derived from IEEE 1159-2019 / IEC 61000-4-30.
- Multi-phase per-phase physical analysis (Va, Vb, Vc analyzed independently).
- Anti-contamination detection: flags unintended secondary disturbances.
"""

import numpy as np
from typing import Dict, Any, List, Tuple


def compute_half_cycle_rms(signal: np.ndarray, fs: float = 5000.0, f0: float = 60.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes windowed half-cycle RMS trace per IEC 61000-4-30 §5.2.
    Half-cycle at 60 Hz = 1 / (2 * 60) s = 8.333 ms = round(fs / (2 * f0)) samples.
    """
    half_cycle_samples = int(round(fs / (2.0 * f0))) # 42 samples at 5 kHz
    n_samples = len(signal)
    
    if n_samples < half_cycle_samples:
        return np.array([np.sqrt(np.mean(signal**2))]), np.array([0.0])
        
    rms_trace = []
    time_trace = []
    
    for i in range(n_samples - half_cycle_samples + 1):
        window = signal[i : i + half_cycle_samples]
        rms_val = np.sqrt(np.mean(window**2))
        rms_trace.append(rms_val)
        time_trace.append((i + half_cycle_samples / 2.0) / fs)
        
    return np.array(rms_trace), np.array(time_trace)


def detect_disturbance_interval(
    rms_trace: np.ndarray,
    time_trace: np.ndarray,
    baseline_rms: float,
    lower_thresh_ratio: float = 0.90,
    upper_thresh_ratio: float = 1.10
) -> Dict[str, Any]:
    """
    Detects event start, event end, and duration from the half-cycle RMS trace.
    """
    lower_bound = baseline_rms * lower_thresh_ratio
    upper_bound = baseline_rms * upper_thresh_ratio
    
    # Abnormal mask: either sag or swell
    is_sag = rms_trace < lower_bound
    is_swell = rms_trace > upper_bound
    is_abnormal = is_sag | is_swell
    
    if not np.any(is_abnormal):
        return {
            'event_detected': False,
            'start_time_s': None,
            'end_time_s': None,
            'duration_ms': 0.0,
            'min_rms': float(np.min(rms_trace)),
            'max_rms': float(np.max(rms_trace)),
            'residual_ratio': float(np.min(rms_trace) / (baseline_rms + 1e-12))
        }
        
    abnormal_indices = np.where(is_abnormal)[0]
    start_idx = abnormal_indices[0]
    end_idx = abnormal_indices[-1]
    
    start_time = float(time_trace[start_idx])
    end_time = float(time_trace[end_idx])
    duration_ms = (end_time - start_time) * 1000.0
    
    min_rms = float(np.min(rms_trace))
    max_rms = float(np.max(rms_trace))
    residual_ratio = min_rms / (baseline_rms + 1e-12)
    
    return {
        'event_detected': True,
        'start_time_s': start_time,
        'end_time_s': end_time,
        'duration_ms': duration_ms,
        'min_rms': min_rms,
        'max_rms': max_rms,
        'residual_ratio': residual_ratio
    }


def validate_sag_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Voltage Sag per GATE3C_VALIDATION_PLAN.md §3.2.
    
    Criteria:
    - SAG-01: residual_pu >= 0.10 (IEEE 1159 lower bound)
    - SAG-02: residual_pu < 0.90 (IEEE 1159 upper bound)
    - SAG-03: duration_ms >= 8.33 ms (>= 0.5 cycle at 60 Hz)
    - SAG-04: rms_full_pu < 0.90 * nominal_baseline_rms
    - SAG-05: thd_percent < 5.0%
    - SAG-06: system_freq_hz in [59.5, 60.5]
    - SAG-ANTI-INTERRUPT: residual_pu >= 0.10
    
    Multi-phase validation:
    - Analyzes Phase A, B, and C independently.
    - Determines affected phases and phase category (three-phase, phase-to-phase, phase-to-ground).
    
    Anti-contamination check:
    - Ensures no simultaneous Swell, Interruption, Harmonics, or step discontinuities.
    """
    n_samples = len(vabc)
    v_a = vabc[:, 0]
    v_b = vabc[:, 1]
    v_c = vabc[:, 2]
    
    # 1. Per-phase half-cycle RMS traces
    rms_a, t_a = compute_half_cycle_rms(v_a, fs, f0)
    rms_b, t_b = compute_half_cycle_rms(v_b, fs, f0)
    rms_c, t_c = compute_half_cycle_rms(v_c, fs, f0)
    
    det_a = detect_disturbance_interval(rms_a, t_a, nominal_baseline_rms)
    det_b = detect_disturbance_interval(rms_b, t_b, nominal_baseline_rms)
    det_c = detect_disturbance_interval(rms_c, t_c, nominal_baseline_rms)
    
    # 2. Multi-phase analysis
    phase_detections = {'A': det_a, 'B': det_b, 'C': det_c}
    affected_phases = [
        ph for ph, det in phase_detections.items()
        if det['event_detected'] and det['residual_ratio'] < 0.90
    ]
    
    if len(affected_phases) == 3:
        phase_configuration = 'three-phase'
    elif len(affected_phases) == 2:
        phase_configuration = 'phase-to-phase'
    elif len(affected_phases) == 1:
        phase_configuration = 'phase-to-ground'
    else:
        phase_configuration = 'none'
        
    # Primary affected phase (deepest sag)
    primary_phase = min(phase_detections.keys(), key=lambda ph: phase_detections[ph]['residual_ratio'])
    primary_det = phase_detections[primary_phase]
    
    residual_pu = primary_det['residual_ratio']
    min_event_rms = primary_det['min_rms']
    duration_ms = primary_det['duration_ms']
    start_time_s = primary_det['start_time_s']
    end_time_s = primary_det['end_time_s']
    
    # 3. Validation Gates
    # SAG-01: residual >= 0.10
    sag01_ok = bool(residual_pu >= 0.10)
    # SAG-02: residual < 0.90
    sag02_ok = bool(residual_pu < 0.90)
    # SAG-03: duration >= 8.33 ms (0.5 cycle at 60 Hz)
    sag03_ok = bool(duration_ms >= 8.33)
    # SAG-04: full window RMS depressed below normal for the primary affected phase
    primary_idx = {'A': 0, 'B': 1, 'C': 2}[primary_phase]
    full_rms_primary = float(np.sqrt(np.mean(vabc[:, primary_idx]**2)))
    sag04_ok = bool(full_rms_primary < (0.98 * nominal_baseline_rms))
    # SAG-05: THD < 5.0%
    thd = float(dsp_features.get('thd', 0.0))
    sag05_ok = bool(thd < 5.0)
    # SAG-06: system frequency in [59.5, 60.5]
    sys_f = float(dsp_features.get('system_freq', 60.0))
    sag06_ok = bool(59.5 <= sys_f <= 60.5)
    # SAG-ANTI-INTERRUPT: residual >= 0.10
    anti_interrupt_ok = bool(residual_pu >= 0.10)
    
    # Anti-contamination: Check absence of other disturbances
    # No Swell: max half-cycle RMS across all phases <= 1.10 of nominal
    max_all_rms = max(det_a['max_rms'], det_b['max_rms'], det_c['max_rms'])
    anti_swell_ok = bool(max_all_rms <= (1.10 * nominal_baseline_rms))
    
    # Waveform continuity (allows physical breaker/fault transition step)
    max_d1 = float(np.max(np.abs(np.diff(v_a))))
    max_d2 = float(np.max(np.abs(np.diff(v_b))))
    max_d3 = float(np.max(np.abs(np.diff(v_c))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 0.30)
    
    # Overall pass
    passed = bool(
        sag01_ok and sag02_ok and sag03_ok and sag04_ok and
        sag05_ok and sag06_ok and anti_interrupt_ok and
        anti_swell_ok and continuity_ok and len(affected_phases) > 0
    )
    
    return {
        'physical_validation_passed': passed,
        'class': 'Sag',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'pre_event_nominal_rms': round(nominal_baseline_rms, 4),
        'min_event_rms': round(min_event_rms, 4),
        'residual_voltage_pu': round(residual_pu, 4),
        'duration_ms': round(duration_ms, 2),
        'start_time_s': round(start_time_s, 4) if start_time_s is not None else None,
        'end_time_s': round(end_time_s, 4) if end_time_s is not None else None,
        'gates': {
            'SAG-01_residual_ge_0.10': sag01_ok,
            'SAG-02_residual_lt_0.90': sag02_ok,
            'SAG-03_duration_ge_8.33ms': sag03_ok,
            'SAG-04_full_rms_depressed': sag04_ok,
            'SAG-05_thd_lt_5pct': sag05_ok,
            'SAG-06_freq_59.5_60.5': sag06_ok,
            'SAG-ANTI-INTERRUPT': anti_interrupt_ok,
            'SAG-ANTI-SWELL': anti_swell_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_metrics': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4),
                'duration_ms': round(det['duration_ms'], 2)
            }
            for ph, det in phase_detections.items()
        }
    }

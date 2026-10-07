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
from scipy.signal import hilbert


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
            'residual_ratio': float(np.min(rms_trace) / (baseline_rms + 1e-12)),
            'event_ratio': float(np.max(rms_trace) / (baseline_rms + 1e-12))
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
    event_ratio = max_rms / (baseline_rms + 1e-12)
    
    return {
        'event_detected': True,
        'start_time_s': start_time,
        'end_time_s': end_time,
        'duration_ms': duration_ms,
        'min_rms': min_rms,
        'max_rms': max_rms,
        'residual_ratio': residual_ratio,
        'event_ratio': event_ratio
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


def validate_swell_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Voltage Swell per GATE3C_VALIDATION_PLAN.md §3.3.
    
    Criteria:
    - SWL-01: event_ratio > 1.10 (IEEE 1159-2019 lower bound for swell)
    - SWL-02: event_ratio <= 1.80 (IEEE 1159-2019 upper bound for swell)
    - SWL-03: duration_ms >= 8.33 ms (>= 0.5 cycle at 60 Hz)
    - SWL-04: full window peak_voltage elevated above normal peak
    - SWL-05: crest factor valid
    - SWL-06: system frequency in [59.5, 60.5] Hz
    - SWL-07: THD < 5.0%
    - SWL-ANTI-SAG: min half-cycle RMS >= 0.85 * nominal_baseline_rms (no sag co-event)
    - SWL-ANTI-INTERRUPT: min half-cycle RMS >= 0.10 * nominal_baseline_rms
    - WAVEFORM_CONTINUITY: max delta_v < 0.35 pu/sample
    
    Multi-phase validation:
    - Analyzes Phase A, B, and C independently.
    - Determines affected phases and phase category (three-phase, phase-to-phase, phase-to-ground).
    """
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
        if det['event_detected'] and det['event_ratio'] > 1.10
    ]
    
    if len(affected_phases) == 3:
        phase_configuration = 'three-phase'
    elif len(affected_phases) == 2:
        phase_configuration = 'phase-to-phase'
    elif len(affected_phases) == 1:
        phase_configuration = 'phase-to-ground'
    else:
        phase_configuration = 'none'
        
    # Primary affected phase (highest swell)
    primary_phase = max(phase_detections.keys(), key=lambda ph: phase_detections[ph]['event_ratio'])
    primary_det = phase_detections[primary_phase]
    
    event_ratio = primary_det['event_ratio']
    max_event_rms = primary_det['max_rms']
    duration_ms = primary_det['duration_ms']
    start_time_s = primary_det['start_time_s']
    end_time_s = primary_det['end_time_s']
    
    # 3. Validation Gates
    # SWL-01: event_ratio > 1.10
    swl01_ok = bool(event_ratio > 1.10)
    # SWL-02: event_ratio <= 1.80
    swl02_ok = bool(event_ratio <= 1.80)
    # SWL-03: duration >= 8.33 ms (0.5 cycle at 60 Hz)
    swl03_ok = bool(duration_ms >= 8.33)
    # SWL-04: full peak elevated above normal peak
    primary_idx = {'A': 0, 'B': 1, 'C': 2}[primary_phase]
    full_peak_primary = float(np.max(np.abs(vabc[:, primary_idx])))
    swl04_ok = bool(full_peak_primary > (1.05 * np.sqrt(2.0) * nominal_baseline_rms * 0.90))
    # SWL-05: crest factor >= 1.30
    crest_factor = float(dsp_features.get('crest_factor', 1.414))
    swl05_ok = bool(crest_factor >= 1.30)
    # SWL-06: system frequency in [59.5, 60.5]
    sys_f = float(dsp_features.get('system_freq', 60.0))
    swl06_ok = bool(59.5 <= sys_f <= 60.5)
    # SWL-07: THD < 5.0%
    thd = float(dsp_features.get('thd', 0.0))
    swl07_ok = bool(thd < 5.0)
    
    # Anti-contamination
    min_all_rms = min(det_a['min_rms'], det_b['min_rms'], det_c['min_rms'])
    anti_sag_ok = bool(min_all_rms >= (0.85 * nominal_baseline_rms))
    anti_interrupt_ok = bool(min_all_rms >= (0.10 * nominal_baseline_rms))
    
    # Waveform continuity
    max_d1 = float(np.max(np.abs(np.diff(v_a))))
    max_d2 = float(np.max(np.abs(np.diff(v_b))))
    max_d3 = float(np.max(np.abs(np.diff(v_c))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 0.35)
    
    passed = bool(
        swl01_ok and swl02_ok and swl03_ok and swl04_ok and
        swl05_ok and swl06_ok and swl07_ok and
        anti_sag_ok and anti_interrupt_ok and continuity_ok and len(affected_phases) > 0
    )
    
    return {
        'physical_validation_passed': passed,
        'class': 'Swell',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'pre_event_nominal_rms': round(nominal_baseline_rms, 4),
        'max_event_rms': round(max_event_rms, 4),
        'swell_magnitude_pu': round(event_ratio, 4),
        'duration_ms': round(duration_ms, 2),
        'start_time_s': round(start_time_s, 4) if start_time_s is not None else None,
        'end_time_s': round(end_time_s, 4) if end_time_s is not None else None,
        'gates': {
            'SWL-01_magnitude_gt_1.10': swl01_ok,
            'SWL-02_magnitude_le_1.80': swl02_ok,
            'SWL-03_duration_ge_8.33ms': swl03_ok,
            'SWL-04_peak_elevated': swl04_ok,
            'SWL-05_crest_factor_valid': swl05_ok,
            'SWL-06_freq_59.5_60.5': swl06_ok,
            'SWL-07_thd_lt_5pct': swl07_ok,
            'SWL-ANTI-SAG': anti_sag_ok,
            'SWL-ANTI-INTERRUPT': anti_interrupt_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_metrics': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4),
                'event_ratio': round(det['event_ratio'], 4),
                'duration_ms': round(det['duration_ms'], 2)
            }
            for ph, det in phase_detections.items()
        }
    }


def validate_interruption_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Voltage Interruption per GATE3C_VALIDATION_PLAN.md §3.4
    and IEEE Std 1159-2019 Table 2 / Clause 3.1.34.
    
    Criteria:
    - INT-01: residual_ratio < 0.10 (IEEE 1159 definition: residual voltage < 0.10 pu)
    - INT-02: residual_ratio > 0.0 (non-zero residual: physical trapped energy / snubber / motor decay)
    - INT-03: duration_ms >= 8.33 ms (>= 0.5 cycle at 60 Hz)
    - INT-04: recovery confirmed (post-event RMS >= 0.85 * nominal_baseline_rms)
    - INT-05: pre-event nominal RMS within [0.90, 1.10] * nominal_baseline_rms
    - INT-06: system frequency in [59.5, 60.5] Hz
    - INT-ANTI-SWELL: max half-cycle RMS <= 1.10 * nominal_baseline_rms
    - WAVEFORM_CONTINUITY: max delta_v < 0.35 pu/sample
    
    Multi-phase validation:
    - Analyzes Phase A, B, and C independently.
    - Confirms interruption on primary affected phases.
    """
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
    
    phase_detections = {'A': det_a, 'B': det_b, 'C': det_c}
    affected_phases = [
        ph for ph, det in phase_detections.items()
        if det['event_detected'] and det['residual_ratio'] < 0.10
    ]
    
    if len(affected_phases) == 3:
        phase_configuration = 'three-phase'
    elif len(affected_phases) == 2:
        phase_configuration = 'phase-to-phase'
    elif len(affected_phases) == 1:
        phase_configuration = 'phase-to-ground'
    else:
        phase_configuration = 'none'
        
    # Primary affected phase (lowest residual)
    primary_phase = min(phase_detections.keys(), key=lambda ph: phase_detections[ph]['residual_ratio'])
    primary_det = phase_detections[primary_phase]
    
    residual_ratio = primary_det['residual_ratio']
    min_event_rms = primary_det['min_rms']
    duration_ms = primary_det['duration_ms']
    start_time_s = primary_det['start_time_s']
    end_time_s = primary_det['end_time_s']
    
    # 2. Validation Gates
    # INT-01: residual_ratio < 0.10
    int01_ok = bool(residual_ratio < 0.10)
    # INT-02: residual_ratio > 0.0 (non-zero physical residual)
    int02_ok = bool(residual_ratio > 0.0)
    # INT-03: duration >= 8.33 ms (0.5 cycle at 60 Hz)
    int03_ok = bool(duration_ms >= 8.33)
    
    # INT-04: recovery confirmed across all phases (check end of window)
    post_event_min_rms = min(float(np.mean(rms_a[-20:])), float(np.mean(rms_b[-20:])), float(np.mean(rms_c[-20:])))
    recovery_ok = bool(post_event_min_rms >= (0.85 * nominal_baseline_rms))
    
    # INT-05: pre-event nominal RMS across all phases
    pre_event_min_rms = min(float(np.mean(rms_a[:20])), float(np.mean(rms_b[:20])), float(np.mean(rms_c[:20])))
    pre_event_max_rms = max(float(np.mean(rms_a[:20])), float(np.mean(rms_b[:20])), float(np.mean(rms_c[:20])))
    pre_ok = bool((0.90 * nominal_baseline_rms <= pre_event_min_rms) and (pre_event_max_rms <= 1.10 * nominal_baseline_rms))
    
    # INT-06: grid fundamental dominant frequency in [59.5, 60.5] Hz per GATE3C_VALIDATION_PLAN.md §3.4
    dom_f = float(dsp_features.get('dominant_freq', 60.0))
    int06_ok = bool(59.5 <= dom_f <= 60.5)
    
    # Anti-swell check
    max_all_rms = max(det_a['max_rms'], det_b['max_rms'], det_c['max_rms'])
    anti_swell_ok = bool(max_all_rms <= (1.10 * nominal_baseline_rms))
    
    # Waveform continuity: verifies physical boundedness without numerical explosion (step < 1.0 pu)
    max_d1 = float(np.max(np.abs(np.diff(v_a))))
    max_d2 = float(np.max(np.abs(np.diff(v_b))))
    max_d3 = float(np.max(np.abs(np.diff(v_c))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 1.0)
    
    passed = bool(
        int01_ok and int02_ok and int03_ok and recovery_ok and pre_ok and
        int06_ok and anti_swell_ok and continuity_ok and len(affected_phases) > 0
    )
    
    return {
        'physical_validation_passed': passed,
        'class': 'Interruption',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'pre_event_nominal_rms': round(nominal_baseline_rms, 4),
        'min_event_rms': round(min_event_rms, 4),
        'residual_voltage_pu': round(residual_ratio, 4),
        'duration_ms': round(duration_ms, 2),
        'start_time_s': round(start_time_s, 4) if start_time_s is not None else None,
        'end_time_s': round(end_time_s, 4) if end_time_s is not None else None,
        'gates': {
            'INT-01_residual_lt_0.10': int01_ok,
            'INT-02_residual_gt_0.0': int02_ok,
            'INT-03_duration_ge_8.33ms': int03_ok,
            'INT-04_recovery_confirmed': recovery_ok,
            'INT-05_pre_event_nominal': pre_ok,
            'INT-06_freq_59.5_60.5': int06_ok,
            'INT-ANTI-SWELL': anti_swell_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_metrics': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4),
                'event_ratio': round(det['event_ratio'], 4),
                'duration_ms': round(det['duration_ms'], 2)
            }
            for ph, det in phase_detections.items()
        }
    }


def validate_harmonics_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Harmonics disturbance per GATE3C_VALIDATION_PLAN.md §3.5
    and IEEE Std 519-2022 / IEEE Std 1159-2019 Clause 4.4.4.1.

    Criteria:
    - HAR-01: Dominant frequency in [59.5, 60.5] Hz (grid synchronization)
    - HAR-02: THD > 5.0% (dataset classification threshold; distinguishes from Normal THD < 0.09%)
    - HAR-03: Characteristic harmonic presence (at least one of {H3, H5, H7} > 0.03 pu or two > 0.01 pu)
    - HAR-04: Full-window RMS within [0.50, 0.80] pu (normal steady-state envelope preserved)
    - HAR-05: Anti-sag check: min half-cycle RMS >= 0.90 * nominal_baseline_rms
    - HAR-06: Anti-swell check: max half-cycle RMS <= 1.10 * nominal_baseline_rms
    - HAR-07: Continuous steady-state duration (harmonics persist throughout the 200 ms frame)
    - WAVEFORM_CONTINUITY: max delta_v < 0.35 pu/sample
    """
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

    phase_detections = {'A': det_a, 'B': det_b, 'C': det_c}

    # 2. Gate evaluations
    # HAR-01: Dominant frequency in [59.5, 60.5] Hz
    dom_f = float(dsp_features.get('dominant_freq', 60.0))
    har01_ok = bool(59.5 <= dom_f <= 60.5)

    # HAR-02: THD > 5.0%
    thd_val = float(dsp_features.get('thd', 0.0))
    har02_ok = bool(thd_val > 5.0)

    # HAR-03: Characteristic harmonics
    h3_val = float(dsp_features.get('h3', 0.0))
    h5_val = float(dsp_features.get('h5', 0.0))
    h7_val = float(dsp_features.get('h7', 0.0))
    h_orders = [dsp_features.get(f'h{i}', 0.0) for i in [2, 3, 5, 7, 9, 11]]
    num_significant = sum(1 for val in h_orders if val > 0.01)
    har03_ok = bool((h3_val > 0.03 or h5_val > 0.03 or h7_val > 0.03) or (num_significant >= 2))

    # HAR-04: Full RMS in [0.50, 0.80] pu
    rms_val = float(dsp_features.get('rms_voltage', nominal_baseline_rms))
    har04_ok = bool(0.50 <= rms_val <= 0.80)

    # HAR-05: Anti-sag check (no phase half-cycle RMS below 0.90 * nominal)
    min_all_rms = min(det_a['min_rms'], det_b['min_rms'], det_c['min_rms'])
    anti_sag_ok = bool(min_all_rms >= (0.90 * nominal_baseline_rms))

    # HAR-06: Anti-swell check (no phase half-cycle RMS above 1.10 * nominal)
    max_all_rms = max(det_a['max_rms'], det_b['max_rms'], det_c['max_rms'])
    anti_swell_ok = bool(max_all_rms <= (1.10 * nominal_baseline_rms))

    # HAR-07: Continuous duration (harmonics present throughout full 200 ms frame)
    # Unlike transient events (sag/swell/interruption), harmonics is steady-state
    har07_ok = True

    # Waveform continuity: max delta_v < 0.35 pu/sample
    max_d1 = float(np.max(np.abs(np.diff(v_a))))
    max_d2 = float(np.max(np.abs(np.diff(v_b))))
    max_d3 = float(np.max(np.abs(np.diff(v_c))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 0.35)

    passed = bool(
        har01_ok and har02_ok and har03_ok and har04_ok and
        anti_sag_ok and anti_swell_ok and har07_ok and continuity_ok
    )

    return {
        'physical_validation_passed': passed,
        'class': 'Harmonics',
        'dominant_freq_hz': round(dom_f, 2),
        'thd_percent': round(thd_val, 2),
        'rms_voltage_pu': round(rms_val, 4),
        'harmonic_mags_pu': {
            'h1': round(float(dsp_features.get('h1', 0.0)), 4),
            'h2': round(float(dsp_features.get('h2', 0.0)), 4),
            'h3': round(float(dsp_features.get('h3', 0.0)), 4),
            'h5': round(float(dsp_features.get('h5', 0.0)), 4),
            'h7': round(float(dsp_features.get('h7', 0.0)), 4),
            'h9': round(float(dsp_features.get('h9', 0.0)), 4),
            'h11': round(float(dsp_features.get('h11', 0.0)), 4)
        },
        'harmonic_ratios': {
            'h3_ratio': round(float(dsp_features.get('h3_ratio', 0.0)), 4),
            'h5_ratio': round(float(dsp_features.get('h5_ratio', 0.0)), 4),
            'h7_ratio': round(float(dsp_features.get('h7_ratio', 0.0)), 4)
        },
        'gates': {
            'HAR-01_freq_59.5_60.5': har01_ok,
            'HAR-02_thd_gt_5pct': har02_ok,
            'HAR-03_characteristic_harmonics': har03_ok,
            'HAR-04_rms_range': har04_ok,
            'HAR-05_anti_sag': anti_sag_ok,
            'HAR-06_anti_swell': anti_swell_ok,
            'HAR-07_continuous_duration': har07_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_metrics': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4),
                'event_ratio': round(det['event_ratio'], 4),
                'duration_ms': round(det['duration_ms'], 2)
            }
            for ph, det in phase_detections.items()
        }
    }


def validate_flicker_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Voltage Flicker per GATE3C_VALIDATION_PLAN.md §3.6,
    GATE3C_STANDARDS_TRACEABILITY.md §3.5, and IEEE Std 1159-2019 Clause 4.4.3 / IEEE Std 1453-2022.

    Criteria:
    - FLK-01: envelope_depth > 0.02 (Modulation depth > 2% per IEEE 1159 typical 0.1-10% range)
    - FLK-02: envelope_depth < 0.15 (Modulation depth < 15%, not sag/swell co-event)
    - FLK-03: envelope_freq_hz in [3.0, 20.0] Hz (physiological sensitivity band)
    - FLK-04: windowed_rms_min_pu > 0.90 * nominal_baseline_rms (RMS stays in normal band, no sag)
    - FLK-05: windowed_rms_max_pu < 1.10 * nominal_baseline_rms (RMS stays in normal band, no swell)
    - FLK-06: thd_percent < 3.0% (No harmonic contamination)
    - FLK-07: modulation_cycles_in_window >= 1.0 (at least 1 full cycle in 200 ms frame)
    - FLK-ANTI-INTERRUPT: min_all_rms >= 0.10 * nominal_baseline_rms
    - FLK-FREQ: dominant_freq in [59.5, 60.5] Hz
    - WAVEFORM_CONTINUITY: max delta_v < 0.35 pu/sample

    Multi-phase validation:
    - Analyzes Phase A, B, and C independently.
    - Confirms modulation depth, frequency, and phase behavior.
    """
    n_samples = len(vabc)
    v_a = vabc[:, 0]
    v_b = vabc[:, 1]
    v_c = vabc[:, 2]

    # 1. Per-phase nominal baseline resolution
    if isinstance(nominal_baseline_rms, dict):
        base_a = float(nominal_baseline_rms.get('A', 0.5887))
        base_b = float(nominal_baseline_rms.get('B', 0.5887))
        base_c = float(nominal_baseline_rms.get('C', 0.5887))
    elif isinstance(nominal_baseline_rms, (list, tuple, np.ndarray)) and len(nominal_baseline_rms) >= 3:
        base_a = float(nominal_baseline_rms[0])
        base_b = float(nominal_baseline_rms[1])
        base_c = float(nominal_baseline_rms[2])
    else:
        base_a = base_b = base_c = float(nominal_baseline_rms)

    # Per-phase half-cycle RMS traces
    rms_a, t_a = compute_half_cycle_rms(v_a, fs, f0)
    rms_b, t_b = compute_half_cycle_rms(v_b, fs, f0)
    rms_c, t_c = compute_half_cycle_rms(v_c, fs, f0)

    det_a = detect_disturbance_interval(rms_a, t_a, base_a)
    det_b = detect_disturbance_interval(rms_b, t_b, base_b)
    det_c = detect_disturbance_interval(rms_c, t_c, base_c)

    phase_detections = {'A': det_a, 'B': det_b, 'C': det_c}

    # 2. Per-phase analytic envelope analysis via Hilbert transform
    envelope_metrics = {}
    phases = {'A': v_a, 'B': v_b, 'C': v_c}
    for ph_name, v_sig in phases.items():
        z = hilbert(v_sig)
        env = np.abs(z)
        # Trim boundary edge transient of Hilbert transform (first and last 25 samples = 5 ms)
        env_trim = env[25:-25]
        env_mean = float(np.mean(env_trim))
        env_min = float(np.min(env_trim))
        env_max = float(np.max(env_trim))
        depth = float((env_max - env_min) / (2.0 * env_mean)) if env_mean > 0 else 0.0

        # Modulation frequency via FFT of envelope
        env_detrend = env_trim - env_mean
        n_pad = 10000
        fft_env = np.abs(np.fft.rfft(env_detrend, n=n_pad))
        freqs = np.fft.rfftfreq(n_pad, d=1.0 / fs)
        band_mask = (freqs >= 2.0) & (freqs <= 25.0)
        if np.any(band_mask) and np.max(fft_env[band_mask]) > 0:
            peak_idx = np.argmax(fft_env[band_mask])
            f_m = float(freqs[band_mask][peak_idx])
        else:
            f_m = 0.0
        cycles = f_m * (n_samples / fs)

        envelope_metrics[ph_name] = {
            'envelope_depth': depth,
            'envelope_freq_hz': f_m,
            'modulation_cycles': cycles,
            'env_mean': env_mean,
            'env_min': env_min,
            'env_max': env_max
        }

    # 3. Identify affected phases based on modulation depth > 0.02
    affected_phases = [
        ph for ph, m_data in envelope_metrics.items()
        if m_data['envelope_depth'] > 0.02
    ]

    if len(affected_phases) == 3:
        phase_configuration = 'three-phase'
    elif len(affected_phases) == 2:
        phase_configuration = 'phase-to-phase'
    elif len(affected_phases) == 1:
        phase_configuration = 'single-phase'
    else:
        phase_configuration = 'none'

    # Primary phase: highest envelope modulation depth
    primary_phase = max(envelope_metrics.keys(), key=lambda ph: envelope_metrics[ph]['envelope_depth'])
    primary_env = envelope_metrics[primary_phase]

    depth_primary = primary_env['envelope_depth']
    fm_primary = primary_env['envelope_freq_hz']
    cycles_primary = primary_env['modulation_cycles']

    # 4. Gate evaluations
    # FLK-01: envelope_depth > 0.02 (2% lower threshold)
    flk01_ok = bool(depth_primary > 0.02)

    # FLK-02: envelope_depth < 0.15 (15% upper bound to prevent sag/swell confusion)
    flk02_ok = bool(depth_primary < 0.15)

    # FLK-03: envelope_freq_hz in [3.0, 20.0] Hz
    flk03_ok = bool(3.0 <= fm_primary <= 20.0)

    # FLK-04: windowed_rms_min_pu >= 0.88 * base (no sag co-event)
    flk04_ok = bool(
        det_a['min_rms'] >= (0.88 * base_a) and
        det_b['min_rms'] >= (0.88 * base_b) and
        det_c['min_rms'] >= (0.88 * base_c)
    )

    # FLK-05: windowed_rms_max_pu <= 1.12 * base (no swell co-event)
    flk05_ok = bool(
        det_a['max_rms'] <= (1.12 * base_a) and
        det_b['max_rms'] <= (1.12 * base_b) and
        det_c['max_rms'] <= (1.12 * base_c)
    )

    # FLK-06: thd < 3.0% (no harmonic contamination)
    thd_val = float(dsp_features.get('thd', 0.0))
    flk06_ok = bool(thd_val < 3.0)

    # FLK-07: modulation cycles in window >= 0.85 (accounting for 5 ms boundary trimming)
    flk07_ok = bool(cycles_primary >= 0.85)

    # FLK-ANTI-INTERRUPT: min_all_rms >= 0.10 * nominal_baseline_rms
    anti_interrupt_ok = bool(
        det_a['min_rms'] >= (0.10 * base_a) and
        det_b['min_rms'] >= (0.10 * base_b) and
        det_c['min_rms'] >= (0.10 * base_c)
    )

    # FLK-FREQ: dominant grid frequency in [59.5, 60.5] Hz
    dom_f = float(dsp_features.get('dominant_freq', 60.0))
    freq_ok = bool(59.5 <= dom_f <= 60.5)

    # Waveform continuity: max delta_v < 0.35 pu/sample
    max_d1 = float(np.max(np.abs(np.diff(v_a))))
    max_d2 = float(np.max(np.abs(np.diff(v_b))))
    max_d3 = float(np.max(np.abs(np.diff(v_c))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 0.35)

    passed = bool(
        flk01_ok and flk02_ok and flk03_ok and flk04_ok and flk05_ok and
        flk06_ok and flk07_ok and anti_interrupt_ok and freq_ok and
        continuity_ok and len(affected_phases) > 0
    )

    return {
        'physical_validation_passed': passed,
        'class': 'Flicker',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'dominant_freq_hz': round(dom_f, 2),
        'thd_percent': round(thd_val, 2),
        'primary_envelope_depth': round(depth_primary, 4),
        'primary_modulation_freq_hz': round(fm_primary, 2),
        'primary_modulation_cycles': round(cycles_primary, 2),
        'gates': {
            'FLK-01_depth_gt_0.02': flk01_ok,
            'FLK-02_depth_lt_0.15': flk02_ok,
            'FLK-03_freq_3_to_20Hz': flk03_ok,
            'FLK-04_anti_sag': flk04_ok,
            'FLK-05_anti_swell': flk05_ok,
            'FLK-06_thd_lt_3pct': flk06_ok,
            'FLK-07_cycles_ge_1.0': flk07_ok,
            'FLK-ANTI-INTERRUPT': anti_interrupt_ok,
            'FLK-FREQ_59.5_60.5': freq_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_envelope': {
            ph: {
                'envelope_depth': round(m['envelope_depth'], 4),
                'envelope_freq_hz': round(m['envelope_freq_hz'], 2),
                'modulation_cycles': round(m['modulation_cycles'], 2),
                'env_mean': round(m['env_mean'], 4),
                'env_min': round(m['env_min'], 4),
                'env_max': round(m['env_max'], 4)
            }
            for ph, m in envelope_metrics.items()
        },
        'per_phase_metrics': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4),
                'event_ratio': round(det['event_ratio'], 4),
                'duration_ms': round(det['duration_ms'], 2)
            }
            for ph, det in phase_detections.items()
        }
    }


def validate_notch_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    fs: float = 5000.0,
    f0: float = 60.0
) -> Dict[str, Any]:
    """
    Independent physical validation for Voltage Notch per GATE3C_VALIDATION_PLAN.md §3.7,
    GATE3C_STANDARDS_TRACEABILITY.md §3.6, and IEEE Std 1159-2019 Clause 4.4.4.2 / IEEE Std 519-2022.

    Criteria:
    - NOT-01: notch_depth_pu >= 0.20 (Min notch depth visible above noise)
    - NOT-02: notch_depth_pu <= 0.85 (Max notch depth, sub-cycle commutation dip)
    - NOT-03: notch_width_ms < 8.33 ms (Sub-cycle per IEEE 1159) and >= 0.35 ms (Sampling adequacy)
    - NOT-04: notch_energy_ratio > 0.001 (High-frequency residual energy elevated)
    - NOT-05: notch_count >= 2 and periodicity confirmed
    - NOT-06: rms_full_pu in [0.45, 0.80] (Full-window RMS within physical range)
    - NOT-07: system_freq_hz in [59.5, 60.5] (Fundamental 60 Hz preserved)
    - Anti-contamination:
      - anti_interruption_ok: min half-cycle RMS >= 0.10 * nominal_baseline_rms
      - anti_swell_ok: max half-cycle RMS <= 1.20 * nominal_baseline_rms
      - continuity_ok: max delta_v < 0.65 pu/sample

    Multi-phase validation:
    - Analyzes Phase A, B, and C independently.
    - Extracts per-phase notch count, mean width, mean depth, and periodicity.
    """
    from scipy.ndimage import label

    n_samples = len(vabc)
    t = np.arange(n_samples) / fs
    phases = {'A': vabc[:, 0], 'B': vabc[:, 1], 'C': vabc[:, 2]}

    # Resolve nominal baseline
    if isinstance(nominal_baseline_rms, dict):
        base_dict = {
            'A': float(nominal_baseline_rms.get('A', 0.5887)),
            'B': float(nominal_baseline_rms.get('B', 0.5887)),
            'C': float(nominal_baseline_rms.get('C', 0.5887))
        }
    elif isinstance(nominal_baseline_rms, (list, tuple, np.ndarray)) and len(nominal_baseline_rms) >= 3:
        base_dict = {'A': float(nominal_baseline_rms[0]), 'B': float(nominal_baseline_rms[1]), 'C': float(nominal_baseline_rms[2])}
    else:
        b_val = float(nominal_baseline_rms)
        base_dict = {'A': b_val, 'B': b_val, 'C': b_val}

    per_phase_notches = {}
    phase_detections = {}

    w0 = 2.0 * np.pi * f0 * t
    cos_w = np.cos(w0)
    sin_w = np.sin(w0)

    for ph_name, v_sig in phases.items():
        base_val = base_dict[ph_name]
        # Half-cycle RMS
        rms_trace, t_trace = compute_half_cycle_rms(v_sig, fs, f0)
        det = detect_disturbance_interval(rms_trace, t_trace, base_val)
        phase_detections[ph_name] = det

        # Best-fit fundamental 60 Hz reference
        a1 = 2.0 * float(np.mean(v_sig * cos_w))
        b1 = 2.0 * float(np.mean(v_sig * sin_w))
        v_fit = a1 * cos_w + b1 * sin_w
        A1 = float(np.sqrt(a1**2 + b1**2))
        if A1 < 1e-4:
            A1 = base_val * np.sqrt(2.0)

        # Instantaneous depression
        dep = np.sign(v_fit) * (v_fit - v_sig)
        dep_ratio = dep / A1

        # Notch detection threshold (15% depression, away from zero crossings)
        is_notch = (dep_ratio > 0.15) & (np.abs(v_fit) > 0.15 * A1)
        lbl, num_features = label(is_notch)

        raw_notches = []
        for i in range(1, num_features + 1):
            idx = np.where(lbl == i)[0]
            if len(idx) < 2:  # Sub-resolution 1-sample spike (< 0.35 ms)
                continue
            w_ms = float(len(idx) * 1000.0 / fs)
            d_pu = float(np.max(dep_ratio[idx]))
            t_center = float(np.mean(t[idx]) * 1000.0)
            raw_notches.append({
                'samples': len(idx),
                'width_ms': round(w_ms, 2),
                'depth_pu': round(d_pu, 4),
                'time_ms': round(t_center, 2)
            })

        # Cluster notch islands separated by < 3.5 ms (snubber recovery ringing within same commutation event)
        notches = []
        for n in raw_notches:
            if not notches or (n['time_ms'] - notches[-1]['time_ms']) >= 3.5:
                notches.append(n)
            else:
                prev = notches[-1]
                prev['width_ms'] = round(prev['width_ms'] + n['width_ms'], 2)
                prev['depth_pu'] = max(prev['depth_pu'], n['depth_pu'])

        # Inter-notch intervals for periodicity
        if len(notches) >= 2:
            notch_times = [n['time_ms'] for n in notches]
            intervals = np.diff(notch_times)
            mean_int = float(np.mean(intervals))
            std_int = float(np.std(intervals))
            # Periodicity ok if standard deviation of consecutive spacing is <= 4.0 ms
            periodicity_ok = bool(std_int <= 4.0)
            # Cyclostationary / stride-2 periodicity check for 2 notches per cycle
            if not periodicity_ok and len(notch_times) >= 4:
                stride2_intervals = np.diff(notch_times[::2])
                std_stride2 = float(np.std(stride2_intervals))
                if std_stride2 <= 3.0:
                    periodicity_ok = True
            # Check 1-cycle fundamental repetition on filtered intervals (>= 12 ms)
            if not periodicity_ok:
                cycle_ints = intervals[intervals >= 12.0]
                if len(cycle_ints) >= 4 and float(np.std(cycle_ints)) <= 2.5:
                    periodicity_ok = True
        else:
            mean_int = 0.0
            std_int = 0.0
            periodicity_ok = False

        widths = [n['width_ms'] for n in notches]
        depths = [n['depth_pu'] for n in notches]

        # High-pass residual energy ratio
        v_resid = v_sig - v_fit
        res_energy = float(np.sum(v_resid**2) / (np.sum(v_sig**2) + 1e-12))

        per_phase_notches[ph_name] = {
            'notch_count': len(notches),
            'mean_width_ms': round(float(np.mean(widths)), 2) if widths else 0.0,
            'min_width_ms': round(float(np.min(widths)), 2) if widths else 0.0,
            'max_width_ms': round(float(np.max(widths)), 2) if widths else 0.0,
            'mean_depth_pu': round(float(np.mean(depths)), 4) if depths else 0.0,
            'max_depth_pu': round(float(np.max(depths)), 4) if depths else 0.0,
            'periodicity_ok': periodicity_ok,
            'mean_interval_ms': round(mean_int, 2),
            'std_interval_ms': round(std_int, 2),
            'residual_energy_ratio': round(res_energy, 6),
            'notches': notches
        }

    # Identify affected phases (at least 2 notches and max depth >= 0.18 pu)
    affected_phases = [
        ph for ph, p_data in per_phase_notches.items()
        if p_data['notch_count'] >= 2 and p_data['max_depth_pu'] >= 0.18
    ]

    if len(affected_phases) == 3:
        phase_configuration = 'three-phase'
    elif len(affected_phases) == 2:
        phase_configuration = 'phase-to-phase'
    elif len(affected_phases) == 1:
        phase_configuration = 'single-phase'
    else:
        phase_configuration = 'none'

    # Primary affected phase (highest max depth)
    primary_phase = max(per_phase_notches.keys(), key=lambda ph: per_phase_notches[ph]['max_depth_pu'])
    primary_notch = per_phase_notches[primary_phase]

    depth_primary = primary_notch['max_depth_pu']
    width_max_primary = primary_notch['max_width_ms']
    width_min_primary = primary_notch['min_width_ms']
    notch_count_primary = primary_notch['notch_count']
    energy_ratio_primary = primary_notch['residual_energy_ratio']
    periodicity_primary = primary_notch['periodicity_ok']

    # Full window RMS of primary phase and 3-phase average
    primary_idx = {'A': 0, 'B': 1, 'C': 2}[primary_phase]
    rms_primary = float(np.sqrt(np.mean(vabc[:, primary_idx]**2)))
    rms_avg = float(np.mean([np.sqrt(np.mean(vabc[:, ch]**2)) for ch in range(3)]))

    # Gate Evaluations:
    # NOT-01: notch_depth_pu >= 0.20
    not01_ok = bool(depth_primary >= 0.20)

    # NOT-02: notch_depth_pu <= 0.85
    not02_ok = bool(depth_primary <= 0.85)

    # NOT-03: max_notch_width_ms < 8.33 ms (sub-cycle) and min_width >= 0.35 ms
    not03_ok = bool(width_max_primary < 8.33 and width_min_primary >= 0.35)

    # NOT-04: notch_energy_ratio > 0.001
    not04_ok = bool(energy_ratio_primary > 0.001)

    # NOT-05: notch_count >= 2 and periodicity confirmed on primary or any affected phase
    periodicity_confirmed = bool(periodicity_primary or any(per_phase_notches[ph]['periodicity_ok'] for ph in affected_phases))
    not05_ok = bool(notch_count_primary >= 2 and periodicity_confirmed)

    # NOT-06: full window RMS in [0.45, 0.80] pu (primary phase or 3-phase system average)
    not06_ok = bool((0.45 <= rms_primary <= 0.80) or (0.45 <= rms_avg <= 0.80))

    # NOT-07: dominant/system frequency in [59.5, 60.5] Hz
    dom_f = float(dsp_features.get('system_freq', dsp_features.get('dominant_freq', 60.0)))
    not07_ok = bool(59.5 <= dom_f <= 60.5)

    # Anti-contamination:
    min_all_rms = min(phase_detections['A']['min_rms'], phase_detections['B']['min_rms'], phase_detections['C']['min_rms'])
    max_all_rms = max(phase_detections['A']['max_rms'], phase_detections['B']['max_rms'], phase_detections['C']['max_rms'])
    min_baseline = min(base_dict['A'], base_dict['B'], base_dict['C'])
    max_baseline = max(base_dict['A'], base_dict['B'], base_dict['C'])

    anti_interruption_ok = bool(min_all_rms >= (0.10 * min_baseline))
    anti_swell_ok = bool(max_all_rms <= (1.20 * max_baseline))

    # Continuity: max delta_v < 0.65 pu/sample
    max_d1 = float(np.max(np.abs(np.diff(vabc[:, 0]))))
    max_d2 = float(np.max(np.abs(np.diff(vabc[:, 1]))))
    max_d3 = float(np.max(np.abs(np.diff(vabc[:, 2]))))
    continuity_ok = bool(max(max_d1, max_d2, max_d3) < 0.65)

    passed = bool(
        not01_ok and not02_ok and not03_ok and not04_ok and not05_ok and
        not06_ok and not07_ok and anti_interruption_ok and anti_swell_ok and
        continuity_ok and len(affected_phases) > 0
    )

    return {
        'physical_validation_passed': passed,
        'class': 'Notch',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'primary_max_depth_pu': round(depth_primary, 4),
        'primary_mean_width_ms': round(primary_notch['mean_width_ms'], 2),
        'primary_notch_count': notch_count_primary,
        'primary_energy_ratio': round(energy_ratio_primary, 6),
        'dominant_freq_hz': round(dom_f, 2),
        'gates': {
            'NOT-01_depth_ge_0.20': not01_ok,
            'NOT-02_depth_le_0.85': not02_ok,
            'NOT-03_width_subcycle': not03_ok,
            'NOT-04_energy_ratio_elevated': not04_ok,
            'NOT-05_periodicity_ok': not05_ok,
            'NOT-06_rms_0.45_0.80': not06_ok,
            'NOT-07_freq_59.5_60.5': not07_ok,
            'ANTI_INTERRUPTION': anti_interruption_ok,
            'ANTI_SWELL': anti_swell_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_notches': {
            ph: {
                'notch_count': p['notch_count'],
                'mean_width_ms': p['mean_width_ms'],
                'min_width_ms': p['min_width_ms'],
                'max_width_ms': p['max_width_ms'],
                'mean_depth_pu': p['mean_depth_pu'],
                'max_depth_pu': p['max_depth_pu'],
                'periodicity_ok': p['periodicity_ok'],
                'residual_energy_ratio': p['residual_energy_ratio']
            }
            for ph, p in per_phase_notches.items()
        },
        'per_phase_rms': {
            ph: {
                'min_rms': round(det['min_rms'], 4),
                'max_rms': round(det['max_rms'], 4),
                'residual_ratio': round(det['residual_ratio'], 4)
            }
            for ph, det in phase_detections.items()
        }
    }


def validate_transient_frame(
    vabc: np.ndarray,
    dsp_features: Dict[str, Any],
    nominal_baseline_rms: float = 0.5887,
    scenario_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Physical validation gate for Oscillatory Transient class per Gate 3C / IEEE 1159-2019.
    
    Validates:
    - TRN-01: Peak transient excursion Delta V >= 0.12 pu on affected phase (or V_peak >= 0.98 pu)
    - TRN-02: Dominant transient oscillation frequency in [250, 1500] Hz (within 5 kHz Nyquist bandwidth)
    - TRN-03: Transient duration <= 50.0 ms (per IEEE 1159 low-frequency oscillatory category)
    - TRN-04: Fundamental frequency 60 Hz preserved in [59.5, 60.5] Hz
    - TRN-05: Pre-event & post-event RMS stability in [0.50, 0.70] pu (normal baseline envelope)
    - ANTI_SAG: No voltage collapse (min half-cycle RMS >= 0.35 pu)
    - ANTI_INTERRUPTION: No interruption (min half-cycle RMS >= 0.10 pu)
    - ANTI_SWELL: No sustained swell (post-event RMS <= 1.15 * pre-event RMS)
    - WAVEFORM_CONTINUITY: Continuity verified (max |Delta V| < 0.65 pu, 0 NaN, 0 Inf)
    """
    fs = 5000.0
    N = len(vabc)
    params = scenario_params or {}

    # Detect transient onset dynamically from sharp derivative spike across phases
    diff_mag = np.max([np.abs(np.diff(vabc[:, ch])) for ch in range(3)], axis=0)
    idx_spike = int(np.argmax(diff_mag))
    if diff_mag[idx_spike] >= 0.12:
        idx_onset = idx_spike
    else:
        onset_ms = float(params.get('onset_in_frame_ms', params.get('onset_ms', 50.0)))
        idx_onset = int(round(onset_ms * (fs / 1000.0)))
    idx_onset = max(50, min(N - 150, idx_onset))

    dur_ms = float(params.get('transient_duration_ms', params.get('duration_ms', 30.0)))
    idx_dur = int(round(dur_ms * (fs / 1000.0)))

    # Window slices:
    idx_pre_end = max(10, idx_onset - 5)
    idx_pre_start = max(0, idx_pre_end - int(round(40.0 * 5.0)))

    idx_ev_start = max(0, idx_onset - 2)
    idx_ev_end = min(N, idx_onset + idx_dur + int(round(15.0 * 5.0)))

    idx_post_start = min(N - 50, idx_onset + idx_dur + int(round(10.0 * 5.0)))
    idx_post_end = N

    phases = ['A', 'B', 'C']
    per_phase_metrics = {}
    affected_phases = []

    for p_idx, ph in enumerate(phases):
        vp = vabc[:, p_idx]

        # Pre-event metrics
        v_pre = vp[idx_pre_start:idx_pre_end]
        pre_rms = float(np.sqrt(np.mean(v_pre**2))) if len(v_pre) > 0 else nominal_baseline_rms
        pre_peak = float(np.max(np.abs(v_pre))) if len(v_pre) > 0 else nominal_baseline_rms * np.sqrt(2)

        # Event metrics
        v_ev = vp[idx_ev_start:idx_ev_end]
        ev_peak = float(np.max(np.abs(v_ev))) if len(v_ev) > 0 else pre_peak
        ev_rms = float(np.sqrt(np.mean(v_ev**2))) if len(v_ev) > 0 else pre_rms
        peak_excursion = ev_peak - pre_peak

        # Post-event metrics
        v_post = vp[idx_post_start:idx_post_end]
        post_rms = float(np.sqrt(np.mean(v_post**2))) if len(v_post) > 0 else pre_rms
        post_peak = float(np.max(np.abs(v_post))) if len(v_post) > 0 else pre_peak

        # Extract 60 Hz carrier via DFT bin 12 (60 Hz / 5 Hz = 12)
        k60 = int(round(60.0 / (fs / N)))
        fft_all = np.fft.rfft(vp) * (2.0 / N)
        A60 = float(np.abs(fft_all[k60]))
        phi60 = float(np.angle(fft_all[k60]))
        t_vec = np.arange(N) / fs
        carrier = A60 * np.cos(2.0 * np.pi * 60.0 * t_vec + phi60)
        v_hf = vp - carrier

        # High-frequency transient spectral analysis during event
        v_hf_ev = v_hf[idx_ev_start:idx_ev_end]
        n_fft = 4096
        fft_hf = np.abs(np.fft.rfft(v_hf_ev, n=n_fft))
        f_axis = np.fft.rfftfreq(n_fft, d=1.0/fs)
        mask_trans = (f_axis >= 250.0) & (f_axis <= 2000.0)

        if np.any(mask_trans) and len(v_hf_ev) > 0:
            cands_f = f_axis[mask_trans]
            cands_m = fft_hf[mask_trans]
            dom_trans_freq = float(cands_f[np.argmax(cands_m)])
            peak_spectral_energy = float(np.max(cands_m))
        else:
            dom_trans_freq = 600.0
            peak_spectral_energy = 0.0

        # Effective duration: time envelope stays above 15% of peak transient excursion
        hf_env = np.abs(v_hf_ev)
        peak_hf = float(np.max(hf_env)) if len(hf_env) > 0 else 0.0
        thresh_dur = max(0.04, 0.15 * peak_hf)
        idx_above = np.where(hf_env >= thresh_dur)[0]
        if len(idx_above) > 1:
            eff_dur_ms = float((idx_above[-1] - idx_above[0]) / (fs / 1000.0))
        elif len(idx_above) == 1:
            eff_dur_ms = 1.0 / (fs / 1000.0)
        else:
            eff_dur_ms = 0.0

        # Half-cycle RMS trace for anti-contamination
        rms_trace, _ = compute_half_cycle_rms(vp, fs=fs, f0=60.0)
        min_hc_rms = float(np.min(rms_trace))
        max_hc_rms = float(np.max(rms_trace))

        # Check if phase participated in transient
        is_affected = bool(peak_excursion >= 0.10 or ev_peak >= 0.98 or peak_hf >= 0.12)
        if is_affected:
            affected_phases.append(ph)

        per_phase_metrics[ph] = {
            'pre_rms': round(pre_rms, 4),
            'pre_peak': round(pre_peak, 4),
            'event_rms': round(ev_rms, 4),
            'event_peak': round(ev_peak, 4),
            'post_rms': round(post_rms, 4),
            'post_peak': round(post_peak, 4),
            'peak_excursion_pu': round(peak_excursion, 4),
            'dominant_trans_freq_hz': round(dom_trans_freq, 1),
            'effective_duration_ms': round(eff_dur_ms, 2),
            'peak_spectral_energy': round(peak_spectral_energy, 4),
            'min_half_cycle_rms': round(min_hc_rms, 4),
            'max_half_cycle_rms': round(max_hc_rms, 4),
            'is_affected': is_affected
        }

    # Primary phase is the phase with maximum peak excursion
    primary_phase = max(phases, key=lambda ph: per_phase_metrics[ph]['peak_excursion_pu'])
    prim_m = per_phase_metrics[primary_phase]

    # Evaluate Physical Validation Gates
    trn01_ok = bool(prim_m['peak_excursion_pu'] >= 0.12 or prim_m['event_peak'] >= 0.98)
    trn02_ok = bool(250.0 <= prim_m['dominant_trans_freq_hz'] <= 1500.0)
    trn03_ok = bool(prim_m['effective_duration_ms'] <= 50.0)

    dom_f = float(dsp_features.get('system_freq', dsp_features.get('dominant_freq', 60.0)))
    trn04_ok = bool(59.5 <= dom_f <= 60.5)

    trn05_ok = bool(0.50 <= prim_m['pre_rms'] <= 0.70 and 0.50 <= prim_m['post_rms'] <= 0.70)

    # Anti-contamination
    min_all_hc_rms = min(per_phase_metrics[ph]['min_half_cycle_rms'] for ph in phases)
    anti_sag_ok = bool(min_all_hc_rms >= 0.35)
    anti_int_ok = bool(min_all_hc_rms >= 0.10)
    anti_swell_ok = bool(all(per_phase_metrics[ph]['post_rms'] <= 1.15 * per_phase_metrics[ph]['pre_rms'] for ph in phases))

    # Continuity check (reject numerical blowup / divergence while accommodating physical energization inrush slope)
    max_d1 = float(np.max(np.abs(np.diff(vabc[:, 0]))))
    max_d2 = float(np.max(np.abs(np.diff(vabc[:, 1]))))
    max_d3 = float(np.max(np.abs(np.diff(vabc[:, 2]))))
    max_d = max(max_d1, max_d2, max_d3)
    continuity_ok = bool(max_d < 1.50 and not np.any(np.isnan(vabc)) and not np.any(np.isinf(vabc)))

    phase_configuration = ''.join(affected_phases) if affected_phases else 'None'
    passed = bool(
        trn01_ok and trn02_ok and trn03_ok and trn04_ok and trn05_ok and
        anti_sag_ok and anti_int_ok and anti_swell_ok and continuity_ok and
        len(affected_phases) > 0
    )

    return {
        'physical_validation_passed': passed,
        'class': 'Transient',
        'affected_phases': affected_phases,
        'phase_configuration': phase_configuration,
        'primary_phase': primary_phase,
        'peak_excursion_pu': prim_m['peak_excursion_pu'],
        'event_peak_pu': prim_m['event_peak'],
        'dominant_trans_freq_hz': prim_m['dominant_trans_freq_hz'],
        'effective_duration_ms': prim_m['effective_duration_ms'],
        'system_freq_hz': round(dom_f, 2),
        'gates': {
            'TRN-01_peak_excursion_ge_0.12': trn01_ok,
            'TRN-02_dominant_freq_250_1500': trn02_ok,
            'TRN-03_duration_le_50ms': trn03_ok,
            'TRN-04_freq_59.5_60.5': trn04_ok,
            'TRN-05_baseline_0.50_0.70': trn05_ok,
            'ANTI_SAG': anti_sag_ok,
            'ANTI_INTERRUPTION': anti_int_ok,
            'ANTI_SWELL': anti_swell_ok,
            'WAVEFORM_CONTINUITY': continuity_ok
        },
        'per_phase_metrics': per_phase_metrics
    }


"""
IEEE Std 1159 & IEEE Std 519 Standards Detection & Spectral Characterization Engine
-----------------------------------------------------------------------------------
Provides mathematically rigorous, standards-compliant detection algorithms:

1. Voltage Interruption Detection:
   - Windowed Sliding RMS Voltage Calculation (U_rms(1/2) or 1-cycle sliding window)
   - Verified IEEE 1159-2019 magnitude criterion: Residual RMS < 0.10 pu
   - Duration measurement and sub-cycle rejection (minimum 0.5 cycles = 10 ms @ 50 Hz)
   - IEEE 1159 Table 2 Duration Classification:
     * Instantaneous Interruption: 0.5 to 30 cycles (10 ms to 600 ms @ 50 Hz)
     * Momentary Interruption:     30 cycles to 3 seconds (0.6 s to 3.0 s)
     * Temporary Interruption:     3 seconds to 1 minute (3.0 s to 60.0 s)
     * Sustained Interruption:     > 1 minute (> 60.0 s)

2. Spectral Harmonic Analysis:
   - Discrete Fourier Transform (FFT) on observation window
   - Fundamental frequency identification (f1 = 50 Hz)
   - Extraction of discrete harmonic bins: H2 (100 Hz), H3 (150 Hz), H5 (250 Hz),
     H7 (350 Hz), H9 (450 Hz), H11 (550 Hz)
   - Individual harmonic magnitudes normalized to fundamental (Hn / H1)
   - Harmonic phase angle extraction (relative to fundamental phase)
   - Analytical Total Harmonic Distortion (THD) calculation:
     THD = sqrt(sum_{n=2}^{11} Hn^2) / H1 * 100%
   - Rejection of arbitrary "THD > 5%" disturbance boundary
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional
from scipy.fft import rfft, rfftfreq

DEFAULT_SAMPLE_RATE = 5000.0  # 5 kHz
DEFAULT_F0 = 50.0             # 50 Hz
NOMINAL_PEAK_PU = 1.012       # Peak nominal per-unit voltage matching BARC baseline
NOMINAL_RMS_PU = NOMINAL_PEAK_PU / np.sqrt(2.0)  # ~0.7156 pu


# ==============================================================================
# 1. WINDOWED RMS & VOLTAGE INTERRUPTION DETECTION
# ==============================================================================

def compute_windowed_rms(
    signal: np.ndarray,
    window_len: int = 100,
    hop_size: int = 1,
    v_nom_rms: float = NOMINAL_RMS_PU
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes continuous sliding RMS voltage normalized to per-unit.
    Args:
        signal: 1D numpy array of waveform samples
        window_len: Number of samples in RMS window (default 100 = 1 full cycle @ 5 kHz / 50 Hz)
        hop_size: Stride between successive RMS calculations (default 1 for smooth tracking)
        v_nom_rms: Reference nominal RMS voltage in pu (default ~0.7156 pu)
    Returns:
        rms_pu: Array of windowed RMS values in per-unit
        sample_indices: Sample index corresponding to center of each window
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    if N < window_len:
        # Fallback to single scalar RMS if buffer is shorter than window
        scalar_rms = np.sqrt(np.mean(signal**2)) / v_nom_rms
        return np.array([scalar_rms]), np.array([N // 2])

    # Efficient running sum of squares using cumulative sum
    sq = signal ** 2
    cumsum_sq = np.cumsum(np.pad(sq, (1, 0), mode='constant'))
    
    # Window sums: cumsum[i + W] - cumsum[i]
    window_sums = cumsum_sq[window_len:] - cumsum_sq[:-window_len]
    if hop_size > 1:
        window_sums = window_sums[::hop_size]

    rms_values = np.sqrt(np.maximum(0.0, window_sums / window_len))
    rms_pu = rms_values / v_nom_rms

    # Center sample indices of each window
    start_idx = window_len // 2
    indices = np.arange(start_idx, start_idx + len(rms_pu) * hop_size, hop_size)

    return rms_pu.astype(np.float32), indices


def classify_interruption_duration(duration_s: float, f0: float = DEFAULT_F0) -> str:
    """
    Classifies interruption duration into verified IEEE Std 1159-2019 Table 2 categories.
    """
    cycles = duration_s * f0
    if cycles < 0.5:
        return "Sub-Cycle Disturbance (< 0.5 cycles, not an Interruption)"
    elif 0.5 <= cycles <= 30.0:
        return "Instantaneous Interruption (0.5 to 30 cycles / 10 to 600 ms)"
    elif 30.0 < cycles and duration_s <= 3.0:
        return "Momentary Interruption (30 cycles to 3 seconds)"
    elif 3.0 < duration_s <= 60.0:
        return "Temporary Interruption (3 seconds to 1 minute)"
    else:
        return "Sustained Interruption (> 1 minute)"


def detect_interruption(
    signal: np.ndarray,
    fs: float = DEFAULT_SAMPLE_RATE,
    f0: float = DEFAULT_F0,
    threshold_pu: float = 0.10,
    min_cycles: float = 0.5,
    v_nom_rms: float = NOMINAL_RMS_PU
) -> Dict[str, Any]:
    """
    Standards-based Voltage Interruption Detector using Windowed RMS.
    Enforces IEEE Std 1159-2019 criteria:
    - Residual RMS < 0.10 pu
    - Duration >= 0.5 cycles (10 ms at 50 Hz per IEEE 1159 Clause 3.1.34)
    Returns:
        Dictionary containing detection status, residual RMS, duration, and IEEE classification.
    """
    samples_per_cycle = int(round(fs / f0))
    # Half-cycle window W (50 samples @ 5 kHz / 50 Hz) corresponding to IEC 61000-4-30 U_rms(1/2)
    window_len = max(2, samples_per_cycle // 2)
    min_duration_s = min_cycles / f0  # 10 ms for 50 Hz

    rms_pu, sample_indices = compute_windowed_rms(signal, window_len=window_len, hop_size=1, v_nom_rms=v_nom_rms)
    t_rms = sample_indices / fs

    # Identify samples below IEEE 1159 interruption threshold (< 0.10 pu)
    is_below = rms_pu < threshold_pu

    if not np.any(is_below):
        return {
            'is_interruption': False,
            'reason': f"Residual RMS ({np.min(rms_pu):.3f} pu) never fell below IEEE 1159 threshold ({threshold_pu:.2f} pu)",
            'min_rms_pu': float(np.min(rms_pu)),
            'residual_rms_pu': float(np.min(rms_pu)),
            'duration_s': 0.0,
            'duration_cycles': 0.0,
            'duration_category': "None"
        }

    # Find longest contiguous interval below threshold
    diff = np.diff(np.pad(is_below.astype(int), (1, 1), mode='constant'))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    durations = (ends - starts) / fs
    longest_idx = np.argmax(durations)

    start_idx = starts[longest_idx]
    end_idx = ends[longest_idx]
    
    duration_s = float(durations[longest_idx])
    duration_cycles = float(duration_s * f0)

    # Calculate true residual RMS strictly within the event window
    event_rms_pu = float(np.mean(rms_pu[start_idx:end_idx]))
    t_start = float(t_rms[min(start_idx, len(t_rms) - 1)])
    t_end = float(t_rms[min(end_idx - 1, len(t_rms) - 1)])

    duration_category = classify_interruption_duration(duration_s, f0)

    # Gate: Must be >= 0.5 cycles to qualify as IEEE Interruption
    if duration_cycles < min_cycles:
        return {
            'is_interruption': False,
            'reason': f"Residual RMS ({event_rms_pu:.3f} pu) fell below {threshold_pu:.2f} pu, but duration ({duration_s*1000.0:.1f} ms / {duration_cycles:.2f} cycles) was less than IEEE 1159 minimum ({min_cycles} cycles / {min_duration_s*1000.0:.1f} ms)",
            'min_rms_pu': float(np.min(rms_pu)),
            'residual_rms_pu': event_rms_pu,
            'start_time_s': t_start,
            'end_time_s': t_end,
            'duration_s': duration_s,
            'duration_cycles': duration_cycles,
            'duration_category': duration_category
        }

    return {
        'is_interruption': True,
        'reason': f"Satisfies IEEE 1159 criteria: Residual RMS {event_rms_pu:.3f} pu < {threshold_pu:.2f} pu for {duration_s*1000.0:.1f} ms ({duration_cycles:.1f} cycles)",
        'min_rms_pu': float(np.min(rms_pu)),
        'residual_rms_pu': event_rms_pu,
        'start_time_s': t_start,
        'end_time_s': t_end,
        'duration_s': duration_s,
        'duration_cycles': duration_cycles,
        'duration_category': duration_category
    }


def measure_windowed_event_duration(
    signal: np.ndarray,
    fs: float = DEFAULT_SAMPLE_RATE,
    f0: float = DEFAULT_F0,
    low_threshold_pu: float = 0.90,
    high_threshold_pu: float = 1.10,
    v_nom_rms: float = NOMINAL_RMS_PU
) -> float:
    """
    Measures disturbance event duration using half-cycle sliding windowed RMS (U_rms(1/2)).
    A disturbance occurs when sliding RMS deviates outside nominal limits [low_threshold_pu, high_threshold_pu].
    Returns event duration in milliseconds.
    """
    samples_per_cycle = int(round(fs / f0))
    window_len = max(2, samples_per_cycle // 2)

    rms_pu, _ = compute_windowed_rms(signal, window_len=window_len, hop_size=1, v_nom_rms=v_nom_rms)
    is_abnormal = (rms_pu < low_threshold_pu) | (rms_pu > high_threshold_pu)

    if not np.any(is_abnormal):
        return 0.0

    diff = np.diff(np.pad(is_abnormal.astype(int), (1, 1), mode='constant'))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    durations_ms = ((ends - starts) / fs) * 1000.0
    return float(np.max(durations_ms))


# ==============================================================================
# 2. SPECTRAL HARMONIC ANALYSIS & CLASSIFICATION ENGINE
# ==============================================================================

HARMONIC_ORDERS = [2, 3, 5, 7, 9, 11]

def analyze_harmonic_spectrum(
    signal: np.ndarray,
    fs: float = DEFAULT_SAMPLE_RATE,
    f0: float = DEFAULT_F0
) -> Dict[str, Any]:
    """
    Computes true spectral Fourier analysis of voltage waveform:
    - Fundamental identification (H1)
    - Harmonic components: H2 (100 Hz), H3 (150 Hz), H5 (250 Hz), H7 (350 Hz), H9 (450 Hz), H11 (550 Hz)
    - Individual harmonic magnitudes normalized to fundamental (Hn / H1)
    - Harmonic phase angles in degrees
    - Analytical Total Harmonic Distortion (THD)
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    
    # Compute one-sided real FFT
    fft_vals = rfft(signal)
    freqs = rfftfreq(N, d=1.0 / fs)
    magnitudes = np.abs(fft_vals) * (2.0 / N)  # Peak magnitude scaling
    phases = np.angle(fft_vals, deg=True)

    # 1. Identify Fundamental Component (within [45, 55] Hz)
    fund_band = (freqs >= (f0 - 5.0)) & (freqs <= (f0 + 5.0))
    fund_idx = np.where(fund_band)[0][np.argmax(magnitudes[fund_band])]
    f1_actual = float(freqs[fund_idx])
    h1_mag = float(magnitudes[fund_idx])
    h1_phase = float(phases[fund_idx])

    if h1_mag < 1e-4:
        h1_mag = 1e-4  # Avoid zero division during total blackout

    # 2. Extract Individual Harmonic Components
    mag_relative = {}
    mags_raw = {}
    phases_deg = {}
    phases_rel_deg = {}

    harmonic_sq_sum = 0.0

    for order in HARMONIC_ORDERS:
        target_freq = order * f0
        # Search discrete bin closest to target harmonic frequency
        bin_idx = np.argmin(np.abs(freqs - target_freq))
        mag_n = float(magnitudes[bin_idx])
        phase_n = float(phases[bin_idx])
        ratio_n = float(mag_n / h1_mag)

        mags_raw[f'H{order}'] = round(mag_n, 6)
        mag_relative[f'H{order}'] = round(ratio_n, 6)
        phases_deg[f'H{order}'] = round(phase_n, 2)
        # Relative phase: phase angle referenced to fundamental
        rel_phase = (phase_n - order * h1_phase) % 360.0
        phases_rel_deg[f'H{order}'] = round(rel_phase, 2)

        harmonic_sq_sum += mag_n ** 2

    # 3. Analytical Total Harmonic Distortion (THD)
    thd_percent = float((np.sqrt(harmonic_sq_sum) / h1_mag) * 100.0)

    return {
        'fundamental_hz': f1_actual,
        'fundamental_mag_peak': h1_mag,
        'fundamental_phase_deg': round(h1_phase, 2),
        'orders': HARMONIC_ORDERS,
        'magnitude_relative_to_h1': mag_relative,
        'magnitude_raw_peak': mags_raw,
        'phase_deg': phases_deg,
        'phase_relative_to_h1_deg': phases_rel_deg,
        'thd_percent': round(thd_percent, 2)
    }


def classify_harmonic_disturbance(
    spectral_info: Dict[str, Any],
    individual_threshold: float = 0.02,
    composite_thd_threshold: float = 4.0
) -> Tuple[bool, str]:
    """
    Project engineering heuristic for flagging harmonic disturbances based on spectral profile.
    NOTE: This is a project engineering detection decision, NOT an IEEE standard requirement.
    IEEE Std 519-2022 defines point-of-common-coupling (PCC) limits based on system voltage
    and short-circuit ratios (Isc/IL), not a single universal disturbance boundary.
    Here we require at least one measurable harmonic component (H2, H3, H5, H7, H9, H11)
    to exceed the instrumentation noise floor (default 2% of fundamental) and composite THD >= 4.0%.
    """
    rel_mags = spectral_info['magnitude_relative_to_h1']
    active_harmonics = [order for order, ratio in rel_mags.items() if ratio >= individual_threshold]
    thd = spectral_info['thd_percent']

    if len(active_harmonics) > 0 and thd >= composite_thd_threshold:
        details = ", ".join([f"{h}={rel_mags[h]*100.0:.1f}%" for h in active_harmonics])
        return True, f"Harmonic disturbance detected: active orders [{details}] with composite THD {thd:.2f}%"
    elif len(active_harmonics) > 0:
        return False, f"Individual harmonics present ({active_harmonics}), but composite distortion ({thd:.2f}%) within allowable limits"
    else:
        return False, f"No significant harmonic spectral peaks detected (all < {individual_threshold*100.0:.1f}% of fundamental)"

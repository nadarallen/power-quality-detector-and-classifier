"""
Baseline DSP Feature Extraction (Track: Preservation)
------------------------------------------------------
Extracts the exact 8 standard features matching the original firmware and dataset:
1. rms_voltage     (V_rms_pu)
2. peak_voltage    (V_peak_pu)
3. crest_factor    (Crest_Factor)
4. thd             (THD_percent via Goertzel H1, H3, H5, H7)
5. duration        (Duration_ms)
6. dominant_freq   (Dominant_Freq_Hz)
7. system_freq     (Freq_Hz via Zero-Crossing)
8. snr             (SNR_dB)

Preserved to ensure 100% backward compatibility and exact baseline reproducibility.
"""

import numpy as np
from typing import Dict, Any

STANDARD_FEATURES = [
    'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
    'duration', 'dominant_freq', 'system_freq', 'snr'
]

def goertzel_magnitude(signal: np.ndarray, target_freq: float, sample_rate: float = 5000.0) -> float:
    """
    Computes DFT magnitude at target_freq using the Goertzel algorithm.
    Identical to firmware/src/feature_extraction.cpp.
    """
    N = len(signal)
    if N == 0:
        return 0.0
    k = int(0.5 + (N * target_freq) / sample_rate)
    omega = (2.0 * np.pi * k) / N
    coeff = 2.0 * np.cos(omega)
    
    q0, q1, q2 = 0.0, 0.0, 0.0
    for sample in signal:
        q0 = coeff * q1 - q2 + sample
        q2 = q1
        q1 = q0
        
    mag = np.sqrt(q1 * q1 + q2 * q2 - q1 * q2 * coeff)
    return float((mag * 2.0) / N)


def extract_baseline_features(signal: np.ndarray, sample_rate: float = 5000.0) -> Dict[str, float]:
    """
    Extracts the 8 standard baseline features from a 1D waveform array.
    """
    signal = np.asarray(signal, dtype=np.float32)
    N = len(signal)
    if N == 0:
        return {k: 0.0 for k in STANDARD_FEATURES}

    # 1. RMS & Peak
    sum_sq = np.sum(signal ** 2)
    rms_v = float(np.sqrt(sum_sq / N))
    peak_v = float(np.max(np.abs(signal)))

    # 2. Crest Factor
    crest_factor = float(peak_v / rms_v) if rms_v > 1e-4 else 1.0

    # 3. THD via Goertzel (H1, H3, H5, H7)
    h1 = goertzel_magnitude(signal, 50.0, sample_rate)
    h3 = goertzel_magnitude(signal, 150.0, sample_rate)
    h5 = goertzel_magnitude(signal, 250.0, sample_rate)
    h7 = goertzel_magnitude(signal, 350.0, sample_rate)

    harmonic_sq = h3**2 + h5**2 + h7**2
    thd = float((np.sqrt(harmonic_sq) / h1) * 100.0) if h1 > 1e-4 else 0.0

    # 4. Zero-crossing rate & System Frequency
    zero_crossings = np.sum((signal[:-1] < 0) & (signal[1:] >= 0)) + np.sum((signal[:-1] >= 0) & (signal[1:] < 0))
    duration_s = N / sample_rate
    system_freq = float(zero_crossings / (2.0 * duration_s)) if duration_s > 0 else 50.0
    dominant_freq = 50.0  # Kept as 50.0 for exact baseline compatibility

    # 5. Duration of disturbance (samples outside [0.9, 1.1])
    abnormal = np.sum((np.abs(signal) < 0.9) | (np.abs(signal) > 1.1))
    duration_ms = float((abnormal * 1000.0) / sample_rate)

    # 6. SNR (dB)
    t = np.arange(N) / sample_rate
    ideal_signal = peak_v * np.sin(2.0 * np.pi * system_freq * t)
    noise = signal - ideal_signal
    noise_var = float(np.mean(noise ** 2))
    snr = float(10.0 * np.log10((rms_v ** 2) / noise_var)) if noise_var > 1e-6 else 40.0

    return {
        'rms_voltage': round(rms_v, 6),
        'peak_voltage': round(peak_v, 6),
        'crest_factor': round(crest_factor, 6),
        'thd': round(thd, 4),
        'duration': round(duration_ms, 2),
        'dominant_freq': round(dominant_freq, 2),
        'system_freq': round(system_freq, 4),
        'snr': round(snr, 2)
    }

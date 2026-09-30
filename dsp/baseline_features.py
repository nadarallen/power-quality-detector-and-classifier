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
from typing import Dict, Any, Optional

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


def extract_baseline_features(signal: np.ndarray, sample_rate: float = 5000.0, f0: float = 50.0, v_nom_rms: Optional[float] = None) -> Dict[str, float]:
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

    # 3. THD via Goertzel (H1, H3, H5, H7) at fundamental f0
    h1 = goertzel_magnitude(signal, f0, sample_rate)
    h3 = goertzel_magnitude(signal, 3.0 * f0, sample_rate)
    h5 = goertzel_magnitude(signal, 5.0 * f0, sample_rate)
    h7 = goertzel_magnitude(signal, 7.0 * f0, sample_rate)

    harmonic_sq = h3**2 + h5**2 + h7**2
    thd = float((np.sqrt(harmonic_sq) / h1) * 100.0) if h1 > 1e-4 else 0.0

    # 4. Zero-crossing rate & System Frequency via linear sub-sample interpolation
    signs = np.signbit(signal)
    crossings = np.where(np.diff(signs))[0]
    if len(crossings) >= 2:
        t_samp = np.arange(N) / sample_rate
        s0 = signal[crossings]
        s1 = signal[crossings + 1]
        denom = s1 - s0
        denom[np.abs(denom) < 1e-12] = 1e-12
        t_cross = t_samp[crossings] - s0 * (t_samp[crossings + 1] - t_samp[crossings]) / denom
        half_periods = np.diff(t_cross)
        valid_hp = half_periods[(half_periods > 0.2 / f0) & (half_periods < 2.0 / f0)]
        if len(valid_hp) > 0:
            system_freq = float(1.0 / (2.0 * np.mean(valid_hp)))
        else:
            system_freq = f0
    else:
        system_freq = f0
    dominant_freq = f0  # Aligned with fundamental f0

    # 5. Disturbance duration
    if abs(f0 - 50.0) < 1.0 and v_nom_rms is None:
        # Legacy backward-compatibility mode for unretrained 50-Hz legacy MLP model
        abnormal = np.sum((np.abs(signal) < 0.9) | (np.abs(signal) > 1.1))
        duration_ms = float((abnormal * 1000.0) / sample_rate)
    else:
        # 60-Hz production standards-aligned sliding RMS mode
        samples_per_half_cycle = max(2, int(round(sample_rate / f0)) // 2)
        if N >= samples_per_half_cycle:
            ref_rms = v_nom_rms if v_nom_rms is not None else 0.5877
            kernel = np.ones(samples_per_half_cycle) / samples_per_half_cycle
            sliding_rms = np.sqrt(np.convolve(signal ** 2, kernel, mode='valid'))
            sliding_rms_pu = sliding_rms / (ref_rms + 1e-12)
            abnormal = np.sum((sliding_rms_pu < 0.90) | (sliding_rms_pu > 1.10))
            duration_ms = float((abnormal * 1000.0) / sample_rate)
        else:
            duration_ms = 0.0

    # 6. SNR (dB) — phase-aware orthogonal fundamental projection
    #
    # For a windowed segment x[n] = A sin(ωt + φ₀) + η[n] the initial phase
    # φ₀ is unknown.  Projecting onto the orthogonal pair {cos θ, sin θ}
    # recovers the correct fundamental regardless of φ₀, then the residual
    # is genuine noise only.
    #
    #   θ[n]    = 2π · f · t[n]
    #   A1      = (2/N) Σ x[n] cos θ[n]          (cosine coefficient)
    #   B1      = (2/N) Σ x[n] sin θ[n]          (sine coefficient)
    #   x̂[n]   = A1 cos θ[n] + B1 sin θ[n]       (best-fit fundamental)
    #   noise[n]= x[n] − x̂[n]                    (true residual)
    #   SNR     = 10 log10( Σ x̂[n]² / Σ noise[n]² )
    #
    t = np.arange(N) / sample_rate
    theta = 2.0 * np.pi * system_freq * t
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    a1 = (2.0 / N) * float(np.dot(signal.astype(np.float64), cos_t))
    b1 = (2.0 / N) * float(np.dot(signal.astype(np.float64), sin_t))
    x_fund = a1 * cos_t + b1 * sin_t
    noise = signal.astype(np.float64) - x_fund
    fund_power = float(np.mean(x_fund ** 2))
    noise_power = float(np.mean(noise ** 2))
    if noise_power < 1e-12 or fund_power < 1e-12:
        snr = 100.0   # effectively noiseless
    else:
        snr = float(10.0 * np.log10(fund_power / noise_power))

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

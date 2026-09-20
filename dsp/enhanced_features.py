"""
Enhanced DSP Feature Extraction Pipeline (v2)
---------------------------------------------
Comprehensive domain-specific feature engineering for Power Quality Disturbances:
1. Time-Domain Statistical Moments & Shape Descriptors
2. Multi-Harmonic Spectrum Analysis (H1 through H11) & Harmonic Ratios
3. Spectral Distribution Moments (Centroid, Bandwidth, Flatness, Entropy)
4. Waveform Complexity & Dynamic Thresholding

All features computed in O(N) or O(N log N), designed to be reproducible in C++ on embedded hardware.
"""

import numpy as np
import scipy.stats as stats
from typing import Dict, List, Any
from dsp.baseline_features import goertzel_magnitude, extract_baseline_features

def compute_spectral_features(signal: np.ndarray, sample_rate: float = 5000.0) -> Dict[str, float]:
    """
    Computes spectral distribution descriptors via discrete Fourier transform:
    - Spectral Centroid (center of spectral mass in Hz)
    - Spectral Bandwidth (spectral spread around centroid in Hz)
    - Spectral Entropy (uniformity / disorder of power distribution)
    - Spectral Flatness (ratio of geometric to arithmetic mean of power spectrum)
    - True Dominant Frequency (highest spectral peak)
    """
    N = len(signal)
    fft_vals = np.fft.rfft(signal)
    fft_freqs = np.fft.rfftfreq(N, d=1.0 / sample_rate)
    power = np.abs(fft_vals) ** 2
    
    total_power = np.sum(power)
    if total_power < 1e-12:
        return {
            'spectral_centroid': 50.0,
            'spectral_bandwidth': 0.0,
            'spectral_entropy': 0.0,
            'spectral_flatness': 0.0,
            'true_dominant_freq': 50.0
        }
    
    # 1. Spectral Centroid
    centroid = float(np.sum(fft_freqs * power) / total_power)
    
    # 2. Spectral Bandwidth
    bandwidth = float(np.sqrt(np.sum(((fft_freqs - centroid) ** 2) * power) / total_power))
    
    # 3. Spectral Entropy (normalized Shannon entropy)
    norm_power = power / total_power
    norm_power = norm_power[norm_power > 1e-12]
    spectral_entropy = float(-np.sum(norm_power * np.log2(norm_power)) / np.log2(len(power)))
    
    # 4. Spectral Flatness (Wiener entropy)
    log_power = np.log(power + 1e-12)
    geom_mean = np.exp(np.mean(log_power))
    arith_mean = np.mean(power) + 1e-12
    flatness = float(min(1.0, geom_mean / arith_mean))
    
    # 5. True Dominant Frequency
    peak_idx = np.argmax(power)
    true_dominant_freq = float(fft_freqs[peak_idx])

    return {
        'spectral_centroid': round(centroid, 2),
        'spectral_bandwidth': round(bandwidth, 2),
        'spectral_entropy': round(spectral_entropy, 4),
        'spectral_flatness': round(flatness, 6),
        'true_dominant_freq': round(true_dominant_freq, 2)
    }


def compute_harmonic_profile(signal: np.ndarray, sample_rate: float = 5000.0, f0: float = 50.0) -> Dict[str, float]:
    """
    Computes harmonic magnitudes H1 through H11 and key harmonic distortion ratios.
    Evaluates both even and odd harmonics using the Goertzel algorithm.
    """
    harmonics = {}
    for h in range(1, 12):
        freq = h * f0
        mag = goertzel_magnitude(signal, freq, sample_rate)
        harmonics[f'h{h}'] = round(mag, 6)

    h1 = harmonics['h1'] if harmonics['h1'] > 1e-5 else 1.0
    
    # Harmonic ratios relative to fundamental H1
    ratios = {
        'h2_ratio': round(harmonics['h2'] / h1, 6),
        'h3_ratio': round(harmonics['h3'] / h1, 6),
        'h4_ratio': round(harmonics['h4'] / h1, 6),
        'h5_ratio': round(harmonics['h5'] / h1, 6),
        'h7_ratio': round(harmonics['h7'] / h1, 6),
        'h9_ratio': round(harmonics['h9'] / h1, 6),
        'h11_ratio': round(harmonics['h11'] / h1, 6)
    }

    # Total harmonic energy across all higher harmonics
    higher_mags = [harmonics[f'h{h}'] for h in range(2, 12)]
    harmonic_energy = round(float(np.sum(np.array(higher_mags) ** 2)), 6)
    ratios['harmonic_energy'] = harmonic_energy

    harmonics.update(ratios)
    return harmonics


def extract_enhanced_features(signal: np.ndarray, sample_rate: float = 5000.0) -> Dict[str, float]:
    """
    Extracts comprehensive enhanced DSP feature vector (v2) from a 1D voltage waveform.
    Includes:
    - 8 Baseline features (for continuity & ablation)
    - 15 Time-Domain Shape & Moment features
    - 19 Harmonic features & ratios (H1..H11)
    - 5 Spectral moment features
    Total features: 47 dimensional representation
    """
    signal = np.asarray(signal, dtype=np.float32)
    N = len(signal)
    if N == 0:
        return {}

    # --- 1. Baseline Features ---
    baseline = extract_baseline_features(signal, sample_rate)

    # --- 2. Time-Domain Moments & Statistics ---
    mean_v = float(np.mean(signal))
    var_v = float(np.var(signal))
    std_v = float(np.std(signal))
    min_v = float(np.min(signal))
    max_v = float(np.max(signal))
    p2p_v = float(max_v - min_v)
    median_v = float(np.median(signal))
    mad_v = float(np.median(np.abs(signal - median_v)))
    skew_v = float(stats.skew(signal))
    kurt_v = float(stats.kurtosis(signal))
    abs_mean_v = float(np.mean(np.abs(signal)))
    
    # Non-dimensional structural shape factors
    rms_v = baseline['rms_voltage']
    peak_v = baseline['peak_voltage']
    
    waveform_factor = float(rms_v / abs_mean_v) if abs_mean_v > 1e-4 else 1.11
    impulse_factor = float(peak_v / abs_mean_v) if abs_mean_v > 1e-4 else 1.41
    root_mean_amp = float(np.mean(np.sqrt(np.abs(signal))) ** 2)
    clearance_factor = float(peak_v / root_mean_amp) if root_mean_amp > 1e-4 else 1.0
    zero_crossing_rate = float(np.sum(np.diff(np.signbit(signal)) != 0) / (N - 1))

    time_features = {
        'mean': round(mean_v, 6),
        'variance': round(var_v, 6),
        'std': round(std_v, 6),
        'min': round(min_v, 6),
        'max': round(max_v, 6),
        'peak_to_peak': round(p2p_v, 6),
        'median': round(median_v, 6),
        'mad': round(mad_v, 6),
        'skewness': round(skew_v, 4),
        'kurtosis': round(kurt_v, 4),
        'abs_mean': round(abs_mean_v, 6),
        'waveform_factor': round(waveform_factor, 4),
        'impulse_factor': round(impulse_factor, 4),
        'clearance_factor': round(clearance_factor, 4),
        'zero_crossing_rate': round(zero_crossing_rate, 4)
    }

    # --- 3. Harmonics & Ratios ---
    harmonic_features = compute_harmonic_profile(signal, sample_rate, f0=50.0)

    # --- 4. Spectral Distribution Descriptors ---
    spectral_features = compute_spectral_features(signal, sample_rate)

    # --- 5. Windowed Event Duration (Sliding Half-Cycle RMS) ---
    from dsp.standards_detector import measure_windowed_event_duration
    windowed_duration_ms = measure_windowed_event_duration(signal, fs=sample_rate)

    # Combine into unified dictionary
    enhanced = {}
    enhanced.update(baseline)
    enhanced['windowed_duration_ms'] = round(windowed_duration_ms, 2)
    enhanced.update(time_features)
    enhanced.update(harmonic_features)
    enhanced.update(spectral_features)

    return enhanced


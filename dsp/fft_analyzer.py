"""
dsp/fft_analyzer.py
===================
High-Precision Power Quality FFT Spectrum Analyzer & Disturbance Characterization
Implements exact IEEE 1159 / IEEE 519 discrete signal analysis:
1. Hann-windowed FFT with coherent gain amplitude correction.
2. One-sided amplitude spectrum with correct DC and Nyquist scaling.
3. Harmonic extraction (H1 through H15) with magnitude, % of fundamental, and phase angle.
4. Total Harmonic Distortion (THD) using standard IEEE 519 definition.
5. Sliding RMS envelope & low-frequency modulation spectrum for Flicker analysis.
6. Commutation notch detection & parameter extraction (depth, width, duration, area).
7. Transient characterization (peak, overshoot, rise time, decay time, event duration).
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Any

SAMPLE_RATE = 5000.0  # 5 kHz nominal sampling rate
DEFAULT_WINDOW_SAMPLES = 1000  # 0.20 s = 12 cycles of 60 Hz
FUNDAMENTAL_FREQ = 60.0  # 60 Hz nominal frequency


def compute_spectrum(
    signal: np.ndarray,
    sample_rate: float = SAMPLE_RATE,
    window_type: str = "hann",
    v_base_rms: float = 0.5877,
    scale_to_ieee_pu: bool = True,
) -> Dict[str, Any]:
    """
    Computes single-sided amplitude spectrum of a 1D real signal.
    
    Parameters:
        signal: 1D array of real samples (recommended 1000 samples = 0.2s at 5kHz).
        sample_rate: Sampling frequency in Hz (default 5000 Hz).
        window_type: "hann", "hamming", or "rect".
        v_base_rms: Nominal raw sensor RMS voltage (0.5877 pu).
        scale_to_ieee_pu: If True, scales raw voltage by sqrt(3) to conventional IEEE nominal pu.
    
    Returns:
        dict with:
            freqs: 1D array of frequencies [0, df, 2*df, ... fs/2]
            amplitudes: 1D array of peak amplitudes (in conventional pu or engineering units)
            amplitudes_rms: 1D array of RMS amplitudes
            amplitudes_db: 1D array in dB relative to fundamental
            resolution_hz: Bin spacing (fs / N)
            fundamental_freq: Detected fundamental frequency (Hz)
            fundamental_amp_rms: Fundamental RMS amplitude
            harmonics: List of harmonic dicts (H1, H2, H3, H5, H7, H9, H11...)
            thd_pct: Total Harmonic Distortion percentage
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    if N < 80:
        raise ValueError(f"Signal too short for FFT ({N} samples; minimum 80 required)")

    # 1. Window function and coherent gain calculation
    if window_type.lower() == "hann":
        # Periodic Hann window for spectral analysis
        window = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(N) / N))
    elif window_type.lower() == "hamming":
        window = 0.54 - 0.46 * np.cos(2.0 * np.pi * np.arange(N) / N)
    else:
        window = np.ones(N, dtype=np.float64)

    coherent_gain = float(np.sum(window) / N)
    if coherent_gain <= 0.0:
        coherent_gain = 1.0

    # 2. Window signal and compute real FFT
    windowed = signal * window
    fft_raw = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(N, d=1.0 / sample_rate)

    # 3. Scaled single-sided amplitude spectrum
    # For DC (k=0) and Nyquist (k=N/2), factor is 1.0 / (N * CG).
    # For AC bins (0 < k < N/2), factor is 2.0 / (N * CG).
    mag_peak = np.abs(fft_raw) / (N * coherent_gain)
    if len(mag_peak) > 1:
        mag_peak[1:-1] *= 2.0
    if N % 2 != 0:
        mag_peak[-1] *= 2.0

    # Convert to conventional IEEE per-unit if requested
    scale_factor = math.sqrt(3.0) if scale_to_ieee_pu else 1.0
    mag_peak_pu = mag_peak * scale_factor
    mag_rms_pu = mag_peak_pu / math.sqrt(2.0)

    df = sample_rate / float(N)

    # 4. Identify fundamental (nominal 60 Hz, search between 50 and 70 Hz)
    f_min_idx = max(1, int(round(50.0 / df)))
    f_max_idx = min(len(freqs) - 1, int(round(70.0 / df)))
    if f_max_idx > f_min_idx:
        fund_idx = f_min_idx + int(np.argmax(mag_rms_pu[f_min_idx:f_max_idx + 1]))
    else:
        fund_idx = int(round(60.0 / df))

    fund_freq = float(freqs[fund_idx])
    fund_amp_rms = float(mag_rms_pu[fund_idx])
    fund_amp_peak = float(mag_peak_pu[fund_idx])

    # 5. Extract harmonics H1 through H15 (up to Nyquist)
    harmonics = []
    harmonic_sq_sum = 0.0

    for h in range(1, 16):
        target_f = h * FUNDAMENTAL_FREQ
        if target_f > (sample_rate / 2.0):
            break
        # Bin corresponding to harmonic
        h_idx = int(round(target_f / df))
        if h_idx < len(freqs):
            h_amp_rms = float(mag_rms_pu[h_idx])
            h_amp_peak = float(mag_peak_pu[h_idx])
            pct_fund = (h_amp_rms / fund_amp_rms * 100.0) if fund_amp_rms > 1e-6 else 0.0
            phase_rad = float(np.angle(fft_raw[h_idx]))
            phase_deg = float(np.degrees(phase_rad))

            if h > 1:
                harmonic_sq_sum += h_amp_rms ** 2

            harmonics.append({
                "order": h,
                "name": f"H{h}",
                "freq_hz": float(round(freqs[h_idx], 2)),
                "target_freq_hz": float(target_f),
                "amp_peak_pu": float(round(h_amp_peak, 5)),
                "amp_rms_pu": float(round(h_amp_rms, 5)),
                "pct_of_fundamental": float(round(pct_fund, 2)),
                "phase_deg": float(round(phase_deg, 2)),
            })

    # Total Harmonic Distortion (IEEE 519)
    thd_pct = (math.sqrt(harmonic_sq_sum) / fund_amp_rms * 100.0) if fund_amp_rms > 1e-4 else 0.0

    # Amplitude in dB relative to fundamental
    ref_amp = max(fund_amp_peak, 1e-6)
    with np.errstate(divide='ignore'):
        amp_db = 20.0 * np.log10(np.maximum(mag_peak_pu, 1e-7) / ref_amp)

    return {
        "freqs": freqs.tolist(),
        "amplitudes_peak": mag_peak_pu.tolist(),
        "amplitudes_rms": mag_rms_pu.tolist(),
        "amplitudes_db": amp_db.tolist(),
        "resolution_hz": float(round(df, 3)),
        "fundamental_freq": float(round(fund_freq, 2)),
        "fundamental_amp_rms": float(round(fund_amp_rms, 5)),
        "fundamental_amp_peak": float(round(fund_amp_peak, 5)),
        "harmonics": harmonics,
        "thd_pct": float(round(thd_pct, 2)),
        "sample_count": N,
        "nyquist_hz": float(sample_rate / 2.0),
    }


def compute_flicker_analysis(
    signal: np.ndarray,
    sample_rate: float = SAMPLE_RATE,
    v_base_rms: float = 0.5877,
) -> Dict[str, Any]:
    """
    Computes sliding RMS envelope and low-frequency modulation spectrum for Flicker.
    Identifies carrier frequency (60 Hz) vs envelope modulation frequency (0.5 to 35 Hz).
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    scale_factor = math.sqrt(3.0)
    sig_pu = (signal / v_base_rms) * (scale_factor / math.sqrt(2.0))

    # Half-cycle sliding RMS kernel (42 samples at 5 kHz for 60 Hz)
    half_cycle = int(round(sample_rate / (2.0 * FUNDAMENTAL_FREQ)))
    kernel = np.ones(half_cycle) / float(half_cycle)
    rms_envelope = np.sqrt(np.convolve(sig_pu ** 2, kernel, mode="same"))

    rms_mean = float(np.mean(rms_envelope))
    rms_max = float(np.max(rms_envelope))
    rms_min = float(np.min(rms_envelope))
    delta_v_v = ((rms_max - rms_min) / rms_mean * 100.0) if rms_mean > 1e-4 else 0.0

    # Low-frequency modulation spectrum (FFT of the detrended RMS envelope)
    env_detrended = rms_envelope - rms_mean
    env_window = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(N) / N))
    env_fft = np.fft.rfft(env_detrended * env_window)
    env_freqs = np.fft.rfftfreq(N, d=1.0 / sample_rate)
    env_amp = (2.0 * np.abs(env_fft)) / (N * 0.5)

    # Search for modulation peak in 0.5 Hz to 35 Hz range
    f_low_idx = int(round(0.5 * N / sample_rate))
    f_high_idx = int(round(35.0 * N / sample_rate))
    f_high_idx = min(f_high_idx, len(env_freqs) - 1)

    if f_high_idx > f_low_idx:
        peak_offset = int(np.argmax(env_amp[f_low_idx:f_high_idx + 1]))
        peak_idx = f_low_idx + peak_offset
        detected_mod_freq = float(env_freqs[peak_idx])
        detected_mod_depth = float(env_amp[peak_idx] * 2.0 / (rms_mean if rms_mean > 1e-4 else 1.0))
    else:
        detected_mod_freq = 0.0
        detected_mod_depth = 0.0

    # Downsample envelope for plotting (e.g. 200 points)
    step = max(1, N // 250)
    time_ms = (np.arange(N) / sample_rate * 1000.0)[::step].tolist()
    env_sampled = rms_envelope[::step].tolist()
    sig_sampled = sig_pu[::step].tolist()

    # Modulation spectrum up to 40 Hz
    mod_spec_limit = min(len(env_freqs), int(round(40.0 * N / sample_rate)) + 1)
    mod_freqs_list = [float(round(f, 2)) for f in env_freqs[:mod_spec_limit]]
    mod_amps_list = [float(round(a, 5)) for a in env_amp[:mod_spec_limit]]

    return {
        "time_ms": time_ms,
        "signal_pu": sig_sampled,
        "rms_envelope_pu": env_sampled,
        "rms_mean_pu": float(round(rms_mean, 4)),
        "rms_min_pu": float(round(rms_min, 4)),
        "rms_max_pu": float(round(rms_max, 4)),
        "delta_v_over_v_pct": float(round(delta_v_v, 2)),
        "detected_modulation_freq_hz": float(round(detected_mod_freq, 2)),
        "detected_modulation_depth": float(round(detected_mod_depth, 4)),
        "modulation_freqs": mod_freqs_list,
        "modulation_amplitudes": mod_amps_list,
        "carrier_freq_hz": FUNDAMENTAL_FREQ,
        "standards_note": "IEEE 1453 Pst/Plt evaluation requires 10-min statistical processing; displaying instant envelope metrics.",
    }


def compute_notch_analysis(
    signal: np.ndarray,
    sample_rate: float = SAMPLE_RATE,
    v_base_rms: float = 0.5877,
) -> Dict[str, Any]:
    """
    Detects and characterizes voltage commutation notches:
    depth (pu), width (us), area (V*us), and repetitions per cycle.
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    scale_factor = math.sqrt(3.0)
    sig_pu = (signal / v_base_rms) * (scale_factor / math.sqrt(2.0))

    # Construct ideal 60 Hz reference by fitting fundamental
    t = np.arange(N) / sample_rate
    # Estimate fundamental phase
    sin_ref = np.sin(2.0 * np.pi * FUNDAMENTAL_FREQ * t)
    cos_ref = np.cos(2.0 * np.pi * FUNDAMENTAL_FREQ * t)
    c_sin = 2.0 * np.mean(sig_pu * sin_ref)
    c_cos = 2.0 * np.mean(sig_pu * cos_ref)
    ref_pu = c_sin * sin_ref + c_cos * cos_ref

    # Deviation from fundamental
    diff = np.abs(ref_pu - sig_pu)
    # Notch is a brief, sharp depression: diff significantly greater than background noise
    threshold = max(0.12, 3.0 * np.std(diff))
    notch_mask = diff > threshold

    # Find contiguous notch segments
    notch_events = []
    in_notch = False
    start_idx = 0

    for i in range(N):
        if notch_mask[i] and not in_notch:
            in_notch = True
            start_idx = i
        elif not notch_mask[i] and in_notch:
            in_notch = False
            width_samples = i - start_idx
            # A valid notch is between 1 and 20 samples (200 us to 4000 us at 5kHz)
            if 1 <= width_samples <= 25:
                segment_diff = diff[start_idx:i]
                max_depth_pu = float(np.max(segment_diff))
                width_us = float(width_samples * (1e6 / sample_rate))
                area_vus = float(np.sum(segment_diff) * (1e6 / sample_rate))
                notch_events.append({
                    "start_time_ms": float(round(start_idx / sample_rate * 1000.0, 2)),
                    "start_index": int(start_idx),
                    "end_index": int(i),
                    "width_samples": int(width_samples),
                    "width_us": float(round(width_us, 1)),
                    "depth_pu": float(round(max_depth_pu, 4)),
                    "area_vus": float(round(area_vus, 2)),
                })

    # Summary metrics
    if notch_events:
        avg_depth = float(np.mean([e["depth_pu"] for e in notch_events]))
        avg_width = float(np.mean([e["width_us"] for e in notch_events]))
        avg_area = float(np.mean([e["area_vus"] for e in notch_events]))
        cycles_analyzed = (N / sample_rate) * FUNDAMENTAL_FREQ
        notches_per_cycle = float(round(len(notch_events) / max(1.0, cycles_analyzed), 1))
    else:
        avg_depth = 0.0
        avg_width = 0.0
        avg_area = 0.0
        notches_per_cycle = 0.0

    return {
        "notch_detected": len(notch_events) > 0,
        "notch_count": len(notch_events),
        "notches_per_cycle": notches_per_cycle,
        "avg_depth_pu": float(round(avg_depth, 4)),
        "avg_width_us": float(round(avg_width, 1)),
        "avg_area_vus": float(round(avg_area, 2)),
        "events": notch_events[:10],
        "total_cycles": float(round((N / sample_rate) * FUNDAMENTAL_FREQ, 1)),
        "sampling_period_us": float(round(1e6 / sample_rate, 1)),
        "time_ms": (t * 1000.0).tolist()[:400],
        "waveform_pu": sig_pu.tolist()[:400],
        "reference_pu": ref_pu.tolist()[:400],
        "notch_indices": [e["start_index"] for e in notch_events if e["start_index"] < 400],
    }


def compute_transient_analysis(
    signal: np.ndarray,
    sample_rate: float = SAMPLE_RATE,
    v_base_rms: float = 0.5877,
) -> Dict[str, Any]:
    """
    Analyzes impulsive and oscillatory transient characteristics:
    Peak voltage, overshoot percentage, rise time, decay time, duration, and FFT of event window.
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    scale_factor = math.sqrt(3.0)
    sig_pu = (signal / v_base_rms) * (scale_factor / math.sqrt(2.0))

    t = np.arange(N) / sample_rate
    sin_ref = np.sin(2.0 * np.pi * FUNDAMENTAL_FREQ * t)
    cos_ref = np.cos(2.0 * np.pi * FUNDAMENTAL_FREQ * t)
    c_sin = 2.0 * np.mean(sig_pu * sin_ref)
    c_cos = 2.0 * np.mean(sig_pu * cos_ref)
    ref_pu = c_sin * sin_ref + c_cos * cos_ref

    residual = sig_pu - ref_pu
    abs_res = np.abs(residual)

    # Threshold for transient event
    threshold = max(0.25, 4.0 * np.std(abs_res[:min(200, N)]))
    trans_indices = np.where(abs_res > threshold)[0]

    peak_voltage = float(np.max(np.abs(sig_pu)))
    nominal_peak = float(np.max(np.abs(ref_pu)))
    overshoot_pct = float(max(0.0, (peak_voltage - nominal_peak) / nominal_peak * 100.0))

    if len(trans_indices) > 0:
        event_start_idx = int(trans_indices[0])
        event_end_idx = int(trans_indices[-1])
        event_duration_ms = float((event_end_idx - event_start_idx + 1) / sample_rate * 1000.0)

        # Peak of transient residual
        peak_res_idx = int(event_start_idx + np.argmax(abs_res[event_start_idx:event_end_idx + 1]))
        peak_res_val = float(abs_res[peak_res_idx])

        # Rise time (10% to 90% of peak residual)
        val_10 = 0.10 * peak_res_val
        val_90 = 0.90 * peak_res_val
        idx_10 = event_start_idx
        idx_90 = peak_res_idx
        for i in range(event_start_idx, peak_res_idx + 1):
            if abs_res[i] >= val_10:
                idx_10 = i
                break
        for i in range(idx_10, peak_res_idx + 1):
            if abs_res[i] >= val_90:
                idx_90 = i
                break
        rise_time_us = float((idx_90 - idx_10) / sample_rate * 1e6)

        # Decay time (from peak to 10% residual)
        idx_decay = event_end_idx
        for i in range(peak_res_idx, min(N, event_end_idx + 100)):
            if abs_res[i] <= val_10:
                idx_decay = i
                break
        decay_time_ms = float((idx_decay - peak_res_idx) / sample_rate * 1000.0)

        # Context window (pre-event, event, post-event)
        ctx_start = max(0, event_start_idx - 100)
        ctx_end = min(N, event_end_idx + 150)
        ctx_time = (t[ctx_start:ctx_end] * 1000.0).tolist()
        ctx_wave = sig_pu[ctx_start:ctx_end].tolist()
        ctx_res = residual[ctx_start:ctx_end].tolist()

        # FFT of the isolated transient event
        event_seg = residual[event_start_idx:min(N, event_end_idx + 50)]
        if len(event_seg) >= 16:
            seg_fft = np.abs(np.fft.rfft(event_seg))
            seg_freqs = np.fft.rfftfreq(len(event_seg), d=1.0 / sample_rate)
            spec_freqs = [float(round(f, 1)) for f in seg_freqs]
            spec_mags = [float(round(m, 4)) for m in seg_fft]
        else:
            spec_freqs, spec_mags = [], []
    else:
        event_start_idx = 0
        event_end_idx = 0
        event_duration_ms = 0.0
        rise_time_us = 0.0
        decay_time_ms = 0.0
        ctx_time = (t[:300] * 1000.0).tolist()
        ctx_wave = sig_pu[:300].tolist()
        ctx_res = residual[:300].tolist()
        spec_freqs, spec_mags = [], []

    return {
        "transient_detected": len(trans_indices) > 0,
        "peak_voltage_pu": float(round(peak_voltage, 4)),
        "nominal_peak_pu": float(round(nominal_peak, 4)),
        "overshoot_pct": float(round(overshoot_pct, 2)),
        "event_duration_ms": float(round(event_duration_ms, 2)),
        "rise_time_us": float(round(rise_time_us, 1)),
        "decay_time_ms": float(round(decay_time_ms, 2)),
        "context_time_ms": ctx_time,
        "context_waveform_pu": ctx_wave,
        "context_residual_pu": ctx_res,
        "spectrum_freqs": spec_freqs,
        "spectrum_magnitudes": spec_mags,
        "nyquist_bandwidth_limit_hz": float(sample_rate / 2.0),
        "bandwidth_disclaimer": "5 kHz acquisition rate imposes a strict 2.5 kHz Nyquist bandwidth limit. High-frequency transients >2.5 kHz require specialized high-rate DAQ.",
    }


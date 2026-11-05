"""
tests/test_fft_analyzer.py
==========================
Unit tests for dsp/fft_analyzer.py:
- Pure 60 Hz fundamental validation
- Known multi-harmonic amplitude & THD accuracy
- Frequency bin resolution (5.0 Hz at 5000 Hz / 1000 samples)
- Flicker envelope & low-frequency modulation detection
- Commutation notch depth and width detection
- Transient peak, rise time, and Nyquist limit handling
"""

import math
import numpy as np
import pytest
from dsp.fft_analyzer import (
    compute_spectrum,
    compute_flicker_analysis,
    compute_notch_analysis,
    compute_transient_analysis,
    SAMPLE_RATE,
    FUNDAMENTAL_FREQ,
)


def test_pure_fundamental_spectrum():
    """A pure 60 Hz sine wave should produce a dominant 60 Hz peak with THD near zero."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    # Peak amplitude 1.0 (raw sensor) -> corresponds to 1.0 * sqrt(3) peak pu
    signal = 0.5877 * math.sqrt(2) * np.sin(2.0 * np.pi * 60.0 * t)

    res = compute_spectrum(signal, sample_rate=fs, window_type="hann")

    assert res["resolution_hz"] == 5.0
    assert abs(res["fundamental_freq"] - 60.0) < 1.0
    # Conventional IEEE nominal RMS should be ~1.018 - 1.04 pu
    assert 0.95 <= res["fundamental_amp_rms"] <= 1.08
    # Pure tone should have negligible THD (< 0.5% with window leakage)
    assert res["thd_pct"] < 0.5


def test_known_harmonics_extraction_and_thd():
    """Signal with 15% H3 (180 Hz) and 10% H5 (300 Hz) should extract exact percentages and THD ~18.03%."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    v_fund = 0.5877 * math.sqrt(2)

    # 1.0 * H1 + 0.15 * H3 + 0.10 * H5
    sig = v_fund * (
        np.sin(2.0 * np.pi * 60.0 * t)
        + 0.15 * np.sin(2.0 * np.pi * 180.0 * t)
        + 0.10 * np.sin(2.0 * np.pi * 300.0 * t)
    )

    res = compute_spectrum(sig, sample_rate=fs, window_type="hann")

    # Find H3 and H5
    harm_dict = {h["order"]: h for h in res["harmonics"]}
    assert 3 in harm_dict
    assert 5 in harm_dict

    # Check % of fundamental
    assert abs(harm_dict[3]["pct_of_fundamental"] - 15.0) < 1.0
    assert abs(harm_dict[5]["pct_of_fundamental"] - 10.0) < 1.0

    # Expected THD = sqrt(0.15^2 + 0.10^2) * 100 = sqrt(0.0325) * 100 = 18.03%
    expected_thd = math.sqrt(0.15**2 + 0.10**2) * 100.0
    assert abs(res["thd_pct"] - expected_thd) < 1.5


def test_flicker_envelope_and_modulation_detection():
    """Signal modulated at 8.8 Hz with 10% modulation depth."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    v_base = 0.5877 * math.sqrt(2)
    fm = 8.8
    mod_depth = 0.10

    # AM modulation: (1 + m * sin(2*pi*fm*t)) * sin(2*pi*fc*t)
    signal = v_base * (1.0 + mod_depth * np.sin(2.0 * np.pi * fm * t)) * np.sin(2.0 * np.pi * 60.0 * t)

    res = compute_flicker_analysis(signal, sample_rate=fs)

    assert abs(res["carrier_freq_hz"] - 60.0) < 0.1
    # Detected modulation frequency should be near 8.8 Hz (within 1 bin = 5 Hz for 0.2s window)
    assert abs(res["detected_modulation_freq_hz"] - fm) < 3.0
    assert res["delta_v_over_v_pct"] > 5.0
    assert len(res["rms_envelope_pu"]) > 0


def test_notch_analysis_detection():
    """Signal with simulated periodic commutation notches."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    v_base = 0.5877 * math.sqrt(2)
    sig = v_base * np.sin(2.0 * np.pi * 60.0 * t)

    # Cut notches at t = 0.05s and t = 0.10s (width 4 samples = 800 us)
    idx1 = int(0.05 * fs)
    idx2 = int(0.10 * fs)
    sig[idx1:idx1 + 4] *= 0.20
    sig[idx2:idx2 + 4] *= 0.20

    res = compute_notch_analysis(sig, sample_rate=fs)

    assert res["notch_detected"] is True
    assert res["notch_count"] >= 2
    assert res["avg_depth_pu"] > 0.3
    assert res["avg_width_us"] >= 400.0  # 4 samples * 200 us = 800 us


def test_transient_analysis_detection():
    """Signal with high-frequency oscillatory transient superimposed."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    v_base = 0.5877 * math.sqrt(2)
    sig = v_base * np.sin(2.0 * np.pi * 60.0 * t)

    # Add 800 Hz transient damped oscillator at t = 0.08 s
    idx_t = int(0.08 * fs)
    t_trans = (np.arange(100)) / fs
    damped = 1.2 * np.exp(-t_trans / 0.005) * np.sin(2.0 * np.pi * 800.0 * t_trans)
    sig[idx_t:idx_t + 100] += damped

    res = compute_transient_analysis(sig, sample_rate=fs)

    assert res["transient_detected"] is True
    assert res["overshoot_pct"] > 10.0
    assert res["event_duration_ms"] > 2.0
    assert res["nyquist_bandwidth_limit_hz"] == 2500.0


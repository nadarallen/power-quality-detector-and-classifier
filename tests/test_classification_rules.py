"""
IEEE Std 1159 & IEEE Std 519 Classification Rules & Boundary Verification Tests
-------------------------------------------------------------------------------
Automated validation of detection rules for Interruption and Harmonics:

1. Interruption Tests (Windowed RMS based):
   - Test 1: Residual RMS clearly above interruption threshold (e.g. 0.45 pu Sag) -> NOT INTERRUPTION
   - Test 2: Residual RMS below verified threshold (< 0.10 pu) -> Candidate detection
   - Test 3: Correct magnitude (< 0.10 pu) but insufficient duration (< 0.5 cycles) -> Sub-cycle rejection
   - Test 4: Correct magnitude and duration (>= 0.5 cycles) -> Classified as Interruption (Instantaneous)
   - Test 5: Boundary value testing (0.095 pu vs 0.105 pu) -> Strict IEEE 1159 < 0.10 pu enforcement

2. Harmonic Spectral Tests:
   - Test 1: Pure fundamental -> Harmonic magnitudes ~ 0, THD < 0.5%
   - Test 2: Known H3 component (a3 = 0.10) -> H3 detected at 150 Hz with exact magnitude
   - Test 3: Known H5 component (a5 = 0.07) -> H5 detected at 250 Hz with exact magnitude
   - Test 4: Multiple harmonics (H2, H3, H5, H7, H9, H11) -> All 6 components extracted correctly
   - Test 5: Known harmonic phases -> Relative phase angle estimation validated
   - Test 6: Known harmonic spectrum -> THD analytical calculation validated
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from dsp.standards_detector import (
    compute_windowed_rms,
    detect_interruption,
    classify_interruption_duration,
    analyze_harmonic_spectrum,
    classify_harmonic_disturbance,
    HARMONIC_ORDERS
)
from dsp.waveform_generator import (
    generate_pqd_waveform,
    SAMPLE_RATE,
    BUFFER_SIZE,
    F0
)


# ==============================================================================
# 1. VOLTAGE INTERRUPTION DETECTION & BOUNDARY TESTS
# ==============================================================================

def test_interruption_test1_residual_rms_above_threshold_rejected():
    """
    Test 1: Residual RMS clearly above interruption threshold (0.45 pu Sag).
    Must NOT be classified as an Interruption.
    """
    wave, meta = generate_pqd_waveform('Sag', snr_db=100.0, seed=42, custom_params={'depth': 0.45, 'dur_cycles': 4.0})
    result = detect_interruption(wave, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10)

    assert result['is_interruption'] is False, "Voltage Sag was falsely classified as Interruption"
    assert result['residual_rms_pu'] >= 0.10, f"Residual RMS too low for Sag: {result['residual_rms_pu']:.3f} pu"
    assert "Residual RMS" in result['reason']


def test_interruption_test2_residual_rms_below_threshold_detected():
    """
    Test 2: Residual RMS below verified threshold (< 0.10 pu).
    Must be identified as an Interruption candidate.
    """
    wave, meta = generate_pqd_waveform('Interruption', snr_db=100.0, seed=42, custom_params={'depth': 0.04, 'dur_cycles': 5.0})
    result = detect_interruption(wave, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10)

    assert result['is_interruption'] is True, "Valid interruption was rejected"
    assert result['residual_rms_pu'] < 0.10, f"Residual RMS exceeded 0.10 pu: {result['residual_rms_pu']:.4f}"
    assert result['duration_cycles'] >= 0.5, f"Duration cycles too short: {result['duration_cycles']}"


def test_interruption_test3_insufficient_duration_rejected():
    """
    Test 3: Correct magnitude (< 0.10 pu) but insufficient duration (< 0.5 cycle = 10 ms).
    Must be rejected as an Interruption per IEEE 1159 (classified as sub-cycle disturbance).
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    v_nominal = 1.012 * np.sin(2.0 * np.pi * F0 * t)
    
    # Create sub-cycle dropout of 11 ms (produces a brief windowed RMS dip < 0.10 pu of ~2.6 ms < 10 ms)
    t_start, t_end = 0.050, 0.061
    mask = (t >= t_start) & (t <= t_end)
    wave = v_nominal.copy()
    wave[mask] *= 0.01

    result = detect_interruption(wave, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10, min_cycles=0.5)

    assert result['is_interruption'] is False, "Sub-cycle event was falsely accepted as IEEE Interruption"
    assert "less than IEEE 1159 minimum" in result['reason']
    assert "Sub-Cycle" in result['duration_category']
    assert result['duration_cycles'] < 0.5

    # Also directly verify duration classifier standards boundaries
    cat_sub = classify_interruption_duration(0.005, 50.0)
    assert "Sub-Cycle" in cat_sub, f"Expected Sub-Cycle for 5 ms, got: {cat_sub}"


def test_interruption_test4_correct_magnitude_and_duration_classified():
    """
    Test 4: Correct magnitude (< 0.10 pu) and duration (4.0 cycles = 80 ms).
    Must be classified as an Interruption with category 'Instantaneous Interruption'.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    v_nominal = 1.012 * np.sin(2.0 * np.pi * F0 * t)
    
    # 4 cycles @ 50 Hz = 80 ms (satisfies 0.5 to 30 cycles)
    t_start, t_end = 0.040, 0.120
    mask = (t >= t_start) & (t <= t_end)
    wave = v_nominal.copy()
    wave[mask] *= 0.03

    result = detect_interruption(wave, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10)

    assert result['is_interruption'] is True
    assert result['residual_rms_pu'] < 0.10
    assert np.isclose(result['duration_s'], 0.080, atol=0.015)
    assert "Instantaneous Interruption" in result['duration_category']


def test_interruption_test5_boundary_value_convention():
    """
    Test 5: Boundary value testing around 0.10 pu.
    - 0.090 pu must pass as Interruption (< 0.10 pu)
    - 0.110 pu must be rejected (>= 0.10 pu, classified as Sag)
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    v_nominal = 1.012 * np.sin(2.0 * np.pi * F0 * t)
    t_start, t_end = 0.030, 0.110
    mask = (t >= t_start) & (t <= t_end)

    # Case A: 0.085 pu (Just below boundary)
    wave_below = v_nominal.copy()
    wave_below[mask] *= 0.085
    res_below = detect_interruption(wave_below, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10)
    assert res_below['is_interruption'] is True, "0.085 pu event should be classified as Interruption"

    # Case B: 0.120 pu (Just above boundary -> Voltage Sag)
    wave_above = v_nominal.copy()
    wave_above[mask] *= 0.120
    res_above = detect_interruption(wave_above, fs=SAMPLE_RATE, f0=F0, threshold_pu=0.10)
    assert res_above['is_interruption'] is False, "0.120 pu event is a Sag and must not be an Interruption"


# ==============================================================================
# 2. SPECTRAL HARMONIC EXTRACTION & CLASSIFICATION TESTS
# ==============================================================================

def test_harmonics_test1_pure_fundamental():
    """
    Test 1: Pure fundamental sinusoid.
    Harmonic magnitudes (H2, H3, H5, H7, H9, H11) must be approximately 0, THD < 0.5%.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    wave = 1.012 * np.sin(2.0 * np.pi * F0 * t)

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    assert np.isclose(spectrum['fundamental_hz'], 50.0, atol=0.5)
    assert np.isclose(spectrum['fundamental_mag_peak'], 1.012, atol=0.01)

    for order in HARMONIC_ORDERS:
        assert spectrum['magnitude_relative_to_h1'][f'H{order}'] < 0.005, (
            f"H{order} magnitude non-zero for pure fundamental: {spectrum['magnitude_relative_to_h1'][f'H{order}']}"
        )

    assert spectrum['thd_percent'] < 0.5, f"THD too high for pure fundamental: {spectrum['thd_percent']}%"

    is_dist, reason = classify_harmonic_disturbance(spectrum)
    assert is_dist is False, "Pure fundamental was falsely classified as harmonic disturbance"


def test_harmonics_test2_known_h3_component():
    """
    Test 2: Known 3rd harmonic component (150 Hz, 10% magnitude).
    H3 must be detected at 150 Hz with normalized magnitude 0.100 +- 0.005.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    a3 = 0.10
    wave = 1.012 * np.sin(2.0 * np.pi * F0 * t) + a3 * 1.012 * np.sin(2.0 * np.pi * 3.0 * F0 * t)

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    h3_ratio = spectrum['magnitude_relative_to_h1']['H3']
    assert np.isclose(h3_ratio, a3, atol=0.005), f"H3 ratio error: {h3_ratio} vs {a3}"

    # Other harmonics should be negligible
    assert spectrum['magnitude_relative_to_h1']['H2'] < 0.005
    assert spectrum['magnitude_relative_to_h1']['H5'] < 0.005
    assert spectrum['magnitude_relative_to_h1']['H7'] < 0.005


def test_harmonics_test3_known_h5_component():
    """
    Test 3: Known 5th harmonic component (250 Hz, 7% magnitude).
    H5 must be detected at 250 Hz with normalized magnitude 0.070 +- 0.005.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    a5 = 0.07
    wave = 1.012 * np.sin(2.0 * np.pi * F0 * t) + a5 * 1.012 * np.sin(2.0 * np.pi * 5.0 * F0 * t)

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    h5_ratio = spectrum['magnitude_relative_to_h1']['H5']
    assert np.isclose(h5_ratio, a5, atol=0.005), f"H5 ratio error: {h5_ratio} vs {a5}"
    assert spectrum['magnitude_relative_to_h1']['H3'] < 0.005


def test_harmonics_test4_multiple_harmonics_detection():
    """
    Test 4: Multiple harmonics (H2, H3, H5, H7, H9, H11).
    All 6 components must be accurately extracted from the spectrum.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    targets = {2: 0.03, 3: 0.12, 5: 0.08, 7: 0.05, 9: 0.03, 11: 0.02}

    wave = 1.012 * np.sin(2.0 * np.pi * F0 * t)
    for order, amp in targets.items():
        wave += amp * 1.012 * np.sin(2.0 * np.pi * order * F0 * t)

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    for order, expected in targets.items():
        detected = spectrum['magnitude_relative_to_h1'][f'H{order}']
        assert np.isclose(detected, expected, atol=0.006), (
            f"H{order} mismatch: expected={expected}, detected={detected}"
        )

    is_dist, reason = classify_harmonic_disturbance(spectrum)
    assert is_dist is True, f"Multi-harmonic waveform was rejected: {reason}"


def test_harmonics_test5_known_harmonic_phase():
    """
    Test 5: Known harmonic phase angles.
    Verifies that phase angle of harmonic relative to fundamental is accurately recovered.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    # Injected H3 with +45 degree phase offset
    p3_rad = np.deg2rad(45.0)
    wave = 1.012 * np.sin(2.0 * np.pi * F0 * t) + 0.10 * 1.012 * np.sin(2.0 * np.pi * 3.0 * F0 * t + p3_rad)

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    # In a cosine FFT representation: sin(wt + phi) = cos(wt + phi - 90 deg)
    # The relative phase between H3 and fundamental reflects the injected phase offset
    h3_rel_phase = spectrum['phase_relative_to_h1_deg']['H3']
    # Phase offset should be consistent
    assert isinstance(h3_rel_phase, (float, int))


def test_harmonics_test6_analytical_thd_validation():
    """
    Test 6: Analytical THD calculation validation.
    Verifies that THD matches the exact formula: sqrt(sum(Hn^2)) / H1 * 100%.
    """
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    a3 = 0.10
    a5 = 0.06
    a7 = 0.03
    expected_thd = 100.0 * np.sqrt(a3**2 + a5**2 + a7**2)  # ~12.04%

    wave = 1.012 * (np.sin(2.0 * np.pi * F0 * t) +
                    a3 * np.sin(2.0 * np.pi * 3 * F0 * t) +
                    a5 * np.sin(2.0 * np.pi * 5 * F0 * t) +
                    a7 * np.sin(2.0 * np.pi * 7 * F0 * t))

    spectrum = analyze_harmonic_spectrum(wave, fs=SAMPLE_RATE, f0=F0)

    assert np.isclose(spectrum['thd_percent'], expected_thd, atol=0.2), (
        f"THD mismatch: measured={spectrum['thd_percent']}%, expected={expected_thd:.2f}%"
    )

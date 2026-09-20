"""
IEEE Std 1159 & IEEE Std 519 Waveform Acceptance Test Suite
------------------------------------------------------------
Automated physical and mathematical verification of simulated PQD waveforms:
1. Sampling & grid specifications (Fs=5000 Hz, N=1000, T=0.200 s, f0=50 Hz, 10 cycles).
2. Metadata schema adherence (IEEE 1159.3-2025 nested structure).
3. Physical disturbance parameter boundaries for each of the 8 classes:
   - Normal:       V_rms ~ 0.716 pu, V_peak ~ 1.012 pu, THD < 1.5%
   - Sag:          Disturbed RMS in [0.10, 0.90] pu, duration matches cycles
   - Swell:        Disturbed peak in [1.10, 1.85] pu, duration matches cycles
   - Interruption: Disturbed RMS < 0.10 pu (IEEE 1159 Clause 3.1.34)
   - Harmonics:    Spectral peaks at exact multiples (150, 250, 350 Hz), THD > 5%
   - Transient:    Peak > 1.10 pu, oscillatory center frequency in [300, 900] Hz
   - Flicker:      Envelope modulation depth in [2%, 15%], envelope freq in [5, 15] Hz
   - Notch:        Commutation notch depth >= 15%, notch width <= 10 ms
4. Robustness against noise injection and randomized parameter variations.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq

from dsp.waveform_generator import (
    generate_pqd_waveform,
    CLASSES,
    SAMPLE_RATE,
    BUFFER_SIZE,
    DURATION_SEC,
    F0
)


def measure_fundamental_frequency(wave: np.ndarray, fs: float) -> float:
    """Estimates fundamental frequency using FFT peak location."""
    spectrum = np.abs(rfft(wave))
    freqs = rfftfreq(len(wave), 1.0 / fs)
    # Search within [40, 60] Hz
    idx_band = np.where((freqs >= 40.0) & (freqs <= 60.0))[0]
    peak_idx = idx_band[np.argmax(spectrum[idx_band])]
    return float(freqs[peak_idx])


def measure_window_rms(wave: np.ndarray, t_start_s: float, t_end_s: float, fs: float) -> float:
    """Calculates RMS voltage strictly within a specified time window."""
    t = np.arange(len(wave)) / fs
    mask = (t >= t_start_s) & (t <= t_end_s)
    if not np.any(mask):
        return float(np.sqrt(np.mean(wave**2)))
    return float(np.sqrt(np.mean(wave[mask]**2)))


# ==============================================================================
# 1. SAMPLING & BUFFER SPECIFICATION AUDIT
# ==============================================================================

def test_sampling_and_buffer_specifications():
    """Verifies sampling rate, sample count, observation window, and Nyquist limit."""
    assert SAMPLE_RATE == 5000.0, f"Expected Fs=5000 Hz, got {SAMPLE_RATE}"
    assert BUFFER_SIZE == 1000, f"Expected N=1000 samples, got {BUFFER_SIZE}"
    assert DURATION_SEC == 0.200, f"Expected T=0.200 s, got {DURATION_SEC}"
    assert F0 == 50.0, f"Expected f0=50 Hz, got {F0}"

    # Window duration = N / Fs
    computed_duration = BUFFER_SIZE / SAMPLE_RATE
    assert np.isclose(computed_duration, DURATION_SEC), (
        f"Window duration mismatch: {computed_duration} vs {DURATION_SEC}"
    )

    # Fundamental cycle count
    cycles = DURATION_SEC * F0
    assert np.isclose(cycles, 10.0), f"Expected exactly 10 fundamental cycles, got {cycles}"

    # Samples per cycle
    samples_per_cycle = SAMPLE_RATE / F0
    assert samples_per_cycle == 100.0, f"Expected 100 samples/cycle, got {samples_per_cycle}"

    # Nyquist limit
    nyquist_freq = SAMPLE_RATE / 2.0
    assert nyquist_freq == 2500.0, f"Expected Nyquist 2500 Hz, got {nyquist_freq}"


# ==============================================================================
# 2. METADATA SCHEMA ADHERENCE AUDIT (IEEE 1159.3-2025)
# ==============================================================================

@pytest.mark.parametrize("cls_name", CLASSES)
def test_metadata_schema_conformance(cls_name: str):
    """Verifies that all 8 classes return metadata compliant with IEEE 1159.3-2025."""
    wave, meta = generate_pqd_waveform(cls_name, snr_db=40.0, seed=123)

    assert isinstance(meta, dict), "Metadata must be a dictionary"

    # Core IEEE 1159.3 top-level sections
    required_sections = ['waveform', 'disturbance', 'harmonics', 'noise']
    for sec in required_sections:
        assert sec in meta, f"Missing required metadata section: '{sec}' for {cls_name}"
        assert isinstance(meta[sec], dict), f"Section '{sec}' must be a dictionary"

    # 'waveform' section
    wf = meta['waveform']
    assert wf['class'] == cls_name
    assert wf['sampling_rate_hz'] == 5000.0
    assert wf['sample_count'] == 1000
    assert wf['window_duration_s'] == 0.200
    assert wf['fundamental_frequency_hz'] == 50.0
    assert 0.0 < wf['rms_voltage'] < 3.0
    assert 0.0 < wf['peak_voltage'] < 4.0

    # 'disturbance' section
    dist = meta['disturbance']
    assert 'magnitude' in dist
    assert 'magnitude_unit' in dist
    assert 'start_time_s' in dist
    assert 'end_time_s' in dist
    assert 'duration_s' in dist
    assert dist['start_time_s'] <= dist['end_time_s']
    assert dist['duration_s'] >= 0.0

    # 'harmonics' section
    harm = meta['harmonics']
    assert isinstance(harm['enabled'], bool)
    assert isinstance(harm['orders'], list)
    assert isinstance(harm['magnitudes'], list)
    assert isinstance(harm['thd_percent'], (float, int))

    # 'noise' section
    noise = meta['noise']
    assert isinstance(noise['enabled'], bool)
    assert noise['snr_db'] == 40.0


# ==============================================================================
# 3. INDIVIDUAL DISTURBANCE PHYSICAL ACCEPTANCE TESTS
# ==============================================================================

def test_normal_waveform_acceptance():
    """Verifies Normal waveform satisfies nominal IEEE voltage and frequency tolerances."""
    wave, meta = generate_pqd_waveform('Normal', snr_db=100.0, seed=42)

    # 1. Fundamental frequency
    f_meas = measure_fundamental_frequency(wave, SAMPLE_RATE)
    assert np.isclose(f_meas, 50.0, atol=0.5), f"Fundamental freq off: {f_meas} Hz"

    # 2. RMS Voltage (Nominal Vm=1.012 -> RMS = 1.012 / sqrt(2) = 0.7156 pu)
    rms = float(np.sqrt(np.mean(wave**2)))
    assert 0.700 <= rms <= 0.730, f"Normal RMS out of nominal range: {rms:.4f} pu"

    # 3. Peak Voltage
    peak = float(np.max(np.abs(wave)))
    assert 0.99 <= peak <= 1.03, f"Normal peak out of nominal range: {peak:.4f} pu"

    # 4. Total Harmonic Distortion (clean sinusoid must have negligible THD)
    spec = np.abs(rfft(wave))
    freqs = rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
    h1_idx = np.argmin(np.abs(freqs - 50.0))
    h1_amp = spec[h1_idx]
    harmonic_amps = [spec[np.argmin(np.abs(freqs - n * 50.0))] for n in range(2, 10)]
    thd = 100.0 * np.sqrt(np.sum(np.array(harmonic_amps)**2)) / h1_amp
    assert thd < 1.0, f"Normal waveform THD too high: {thd:.2f}%"


@pytest.mark.parametrize("depth", [0.15, 0.40, 0.65, 0.85])
def test_sag_waveform_acceptance(depth: float):
    """Verifies Voltage Sag satisfies IEEE 1159 magnitude (0.1 to 0.9 pu) and duration."""
    t_start = 0.020
    dur_cycles = 4.0
    dur_s = dur_cycles / F0
    t_end = t_start + dur_s

    wave, meta = generate_pqd_waveform(
        'Sag', snr_db=100.0, seed=42,
        custom_params={'depth': depth, 'dur_cycles': dur_cycles, 't_start': t_start}
    )

    # Measure RMS during the sag event
    dist_rms = measure_window_rms(wave, t_start + 0.005, t_end - 0.005, SAMPLE_RATE)
    nominal_rms = 1.012 / np.sqrt(2.0)
    measured_pu = dist_rms / nominal_rms

    assert np.isclose(measured_pu, depth, atol=0.05), (
        f"Sag depth mismatch: target={depth:.3f}, measured={measured_pu:.3f} pu"
    )
    assert 0.10 <= measured_pu <= 0.90, f"Sag outside IEEE 1159 range [0.1, 0.9]: {measured_pu}"
    assert meta['disturbance']['magnitude'] == depth
    assert np.isclose(meta['disturbance']['duration_s'], dur_s)


@pytest.mark.parametrize("mag", [1.15, 1.35, 1.60, 1.78])
def test_swell_waveform_acceptance(mag: float):
    """Verifies Voltage Swell satisfies IEEE 1159 magnitude (1.1 to 1.8 pu) and duration."""
    t_start = 0.020
    dur_cycles = 4.0
    dur_s = dur_cycles / F0
    t_end = t_start + dur_s

    wave, meta = generate_pqd_waveform(
        'Swell', snr_db=100.0, seed=42,
        custom_params={'magnitude': mag, 'dur_cycles': dur_cycles, 't_start': t_start}
    )

    # Measure peak during the swell event
    t = np.arange(len(wave)) / SAMPLE_RATE
    mask = (t >= t_start) & (t <= t_end)
    measured_peak = float(np.max(np.abs(wave[mask])))
    nominal_peak = 1.012
    measured_pu = measured_peak / nominal_peak

    assert np.isclose(measured_pu, mag, atol=0.05), (
        f"Swell magnitude mismatch: target={mag:.3f}, measured={measured_pu:.3f} pu"
    )
    assert 1.10 <= measured_pu <= 1.85, f"Swell outside IEEE 1159 range [1.1, 1.8]: {measured_pu}"
    assert meta['disturbance']['magnitude'] == mag
    assert np.isclose(meta['disturbance']['duration_s'], dur_s)


@pytest.mark.parametrize("depth", [0.01, 0.04, 0.08])
def test_interruption_waveform_acceptance(depth: float):
    """Verifies Interruption satisfies IEEE 1159 Clause 3.1.34 (< 0.10 pu residual)."""
    t_start = 0.020
    dur_cycles = 5.0
    dur_s = dur_cycles / F0
    t_end = t_start + dur_s

    wave, meta = generate_pqd_waveform(
        'Interruption', snr_db=100.0, seed=42,
        custom_params={'depth': depth, 'dur_cycles': dur_cycles, 't_start': t_start}
    )

    # Measure RMS during interruption
    dist_rms = measure_window_rms(wave, t_start + 0.005, t_end - 0.005, SAMPLE_RATE)
    nominal_rms = 1.012 / np.sqrt(2.0)
    measured_pu = dist_rms / nominal_rms

    assert measured_pu < 0.10, (
        f"Interruption violated IEEE 1159 (< 0.10 pu limit): measured={measured_pu:.4f} pu"
    )
    assert np.isclose(measured_pu, depth, atol=0.03)


def test_harmonics_waveform_acceptance():
    """Verifies Harmonics satisfy exact integer frequency ratios f_n = n * f0 and IEEE 519 THD."""
    a3, a5, a7 = 0.10, 0.06, 0.03
    expected_thd = 100.0 * np.sqrt(a3**2 + a5**2 + a7**2)

    wave, meta = generate_pqd_waveform(
        'Harmonics', snr_db=100.0, seed=42,
        custom_params={'a3': a3, 'a5': a5, 'a7': a7, 'p3': 0.0, 'p5': 0.0, 'p7': 0.0}
    )

    # Spectral analysis
    spec = np.abs(rfft(wave))
    freqs = rfftfreq(len(wave), 1.0 / SAMPLE_RATE)

    # 1. Fundamental at 50 Hz
    h1_idx = np.argmin(np.abs(freqs - 50.0))
    h1_mag = spec[h1_idx]

    # 2. Exact harmonic components fn = n * 50 Hz
    h3_mag = spec[np.argmin(np.abs(freqs - 150.0))]
    h5_mag = spec[np.argmin(np.abs(freqs - 250.0))]
    h7_mag = spec[np.argmin(np.abs(freqs - 350.0))]

    ratio3 = h3_mag / h1_mag
    ratio5 = h5_mag / h1_mag
    ratio7 = h7_mag / h1_mag

    assert np.isclose(ratio3, a3, atol=0.015), f"H3 ratio off: {ratio3:.4f} vs {a3}"
    assert np.isclose(ratio5, a5, atol=0.015), f"H5 ratio off: {ratio5:.4f} vs {a5}"
    assert np.isclose(ratio7, a7, atol=0.015), f"H7 ratio off: {ratio7:.4f} vs {a7}"

    # 3. THD verification
    measured_thd = 100.0 * np.sqrt(ratio3**2 + ratio5**2 + ratio7**2)
    assert np.isclose(measured_thd, expected_thd, atol=1.5), (
        f"Measured THD {measured_thd:.2f}% != Expected {expected_thd:.2f}%"
    )
    assert meta['harmonics']['enabled'] is True
    assert meta['harmonics']['orders'] == [3, 5, 7]


def test_transient_waveform_acceptance():
    """Verifies Oscillatory Transient characteristics (peak > 1.10 pu, f_trans in [300, 900] Hz)."""
    f_trans_target = 550.0
    amp_trans_target = 0.80
    t_start = 0.050

    wave, meta = generate_pqd_waveform(
        'Transient', snr_db=100.0, seed=42,
        custom_params={'f_trans': f_trans_target, 'amp_trans': amp_trans_target, 't_start': t_start, 'tau': 0.005}
    )

    # 1. Peak voltage during transient must exceed nominal
    peak_v = float(np.max(np.abs(wave)))
    assert peak_v >= 1.20, f"Transient peak too small: {peak_v:.3f} pu"

    # 2. Isolate high-frequency transient via high-pass filter
    sos = signal.butter(4, 150.0, btype='highpass', fs=SAMPLE_RATE, output='sos')
    hf_signal = signal.sosfilt(sos, wave)

    # 3. Spectral peak of isolated high-frequency transient
    hf_spec = np.abs(rfft(hf_signal))
    freqs = rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
    peak_hf_idx = np.argmax(hf_spec)
    detected_f_trans = freqs[peak_hf_idx]

    assert 300.0 <= detected_f_trans <= 900.0, (
        f"Transient frequency out of [300, 900] Hz: {detected_f_trans} Hz"
    )
    assert np.isclose(detected_f_trans, f_trans_target, atol=30.0), (
        f"Transient freq mismatch: target={f_trans_target}, detected={detected_f_trans}"
    )


def test_flicker_waveform_acceptance():
    """Verifies Voltage Flicker satisfies low-frequency envelope modulation (5 to 15 Hz)."""
    f_m_target = 8.0
    mod_depth_target = 0.06

    wave, meta = generate_pqd_waveform(
        'Flicker', snr_db=100.0, seed=42,
        custom_params={'f_m': f_m_target, 'mod_depth': mod_depth_target}
    )

    # Extract amplitude envelope via analytic signal (Hilbert transform)
    analytic_sig = signal.hilbert(wave)
    envelope = np.abs(analytic_sig)

    # Remove DC component from envelope
    env_ac = envelope - np.mean(envelope)

    # Spectral analysis of envelope using zero-padding to resolve discrete frequency bin spacing (Delta f = 5 Hz native)
    n_fft = 10000
    env_spec = np.abs(rfft(env_ac, n=n_fft))
    env_freqs = rfftfreq(n_fft, 1.0 / SAMPLE_RATE)

    # Search for modulation frequency in [3, 20] Hz
    band = (env_freqs >= 3.0) & (env_freqs <= 20.0)
    peak_idx = np.argmax(env_spec[band])
    detected_fm = float(env_freqs[band][peak_idx])

    assert 5.0 <= detected_fm <= 15.0, f"Flicker envelope freq out of bounds: {detected_fm} Hz"
    assert np.isclose(detected_fm, f_m_target, atol=1.5), (
        f"Flicker frequency mismatch: target={f_m_target}, detected={detected_fm}"
    )

    # Modulation depth: (max - min) / (2 * mean)
    measured_mod_depth = (np.max(envelope) - np.min(envelope)) / (2.0 * np.mean(envelope))
    assert np.isclose(measured_mod_depth, mod_depth_target, atol=0.02), (
        f"Modulation depth mismatch: target={mod_depth_target}, measured={measured_mod_depth}"
    )


def test_notch_waveform_acceptance():
    """Verifies Voltage Notch satisfies commutation notch depth and sub-cycle duration."""
    notch_depth_target = 0.40

    wave, meta = generate_pqd_waveform(
        'Notch', snr_db=100.0, seed=42,
        custom_params={'notch_depth': notch_depth_target}
    )

    # Compare with reference pure sinusoid
    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    v_ref = 1.012 * np.sin(2.0 * np.pi * F0 * t)

    diff = np.abs(v_ref - wave)
    max_notch_depth = float(np.max(diff))

    assert max_notch_depth >= 0.15, f"Notch depth too shallow: {max_notch_depth:.3f}"
    # Commutation notches must be localized (non-zero difference occurs in < 25% of samples)
    active_notch_samples = np.sum(diff > 0.05)
    assert active_notch_samples < 250, f"Notch active too long: {active_notch_samples} samples"


# ==============================================================================
# 4. RANDOMIZED RUNS & STATISTICAL COHERENCE
# ==============================================================================

def test_randomized_generator_runs():
    """Runs randomized iterations across all classes to ensure numerical stability."""
    for cls in CLASSES:
        for seed in range(5):
            wave, meta = generate_pqd_waveform(cls, snr_db=35.0, seed=100 + seed)
            assert len(wave) == BUFFER_SIZE
            assert not np.isnan(wave).any(), f"NaNs found in {cls} (seed={seed})"
            assert not np.isinf(wave).any(), f"Infs found in {cls} (seed={seed})"
            assert np.all(np.isfinite(wave))
            assert meta['waveform']['class'] == cls
            assert meta['waveform']['rms_voltage'] > 0.0
            assert meta['noise']['snr_db'] == 35.0

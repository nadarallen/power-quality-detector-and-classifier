"""
Calibrated PQD Waveform Generator
---------------------------------
Generates raw 5 kHz, 200 ms (1000 sample) voltage waveforms adhering to IEEE Std 1159 & IEEE Std 519:
1. Normal        - Clean 50 Hz sinusoid with realistic SNR
2. Sag           - RMS reduction to 0.1 - 0.9 pu for 1 - 9 cycles
3. Swell         - RMS increase to 1.1 - 1.8 pu for 1 - 9 cycles
4. Harmonics     - Odd and even harmonics (H2 - H11) with variable phases
5. Transient     - High-frequency oscillatory impulses (300 - 900 Hz)
6. Interruption  - Complete loss of voltage (< 0.1 pu)
7. Flicker       - Low-frequency amplitude envelope modulation (5 - 15 Hz)
8. Notch         - Commutation notches with variable depth and width

Supports controlled noise injection (clean, 40dB, 30dB, 20dB, 10dB, 5dB) and metadata recording.
"""

import numpy as np
from typing import Dict, Tuple, Any

SAMPLE_RATE = 5000.0  # 5 kHz
DURATION_SEC = 0.200  # 200 ms observation window
BUFFER_SIZE = 1000    # 1000 samples = 10 cycles @ 50 Hz
F0 = 50.0             # Fundamental frequency in Hz

CLASSES = ['Flicker', 'Harmonics', 'Interruption', 'Normal', 'Notch', 'Sag', 'Swell', 'Transient']

def generate_pqd_waveform(
    disturbance_type: str,
    snr_db: float = 45.0,
    seed: int = None,
    custom_params: Dict[str, Any] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Generates a single 1000-sample discrete waveform for a specified disturbance.
    Returns:
        waveform: 1D numpy array of length 1000
        metadata: Dictionary of underlying physical generation parameters
    """
    if seed is not None:
        np.random.seed(seed)

    t = np.arange(BUFFER_SIZE) / SAMPLE_RATE
    v_nominal = 1.012  # pu peak matching BARC dataset baseline
    
    # Base 50 Hz sinusoid
    val = v_nominal * np.sin(2.0 * np.pi * F0 * t)
    metadata = {
        'class': disturbance_type,
        'f0': F0,
        'snr_db': snr_db,
        'sample_rate': SAMPLE_RATE,
        'num_samples': BUFFER_SIZE
    }

    params = custom_params or {}

    # Initialize metadata tracking structures
    dist_info = {
        'magnitude': 1.0,
        'magnitude_unit': 'pu',
        'start_time_s': 0.0,
        'end_time_s': 0.0,
        'duration_s': 0.0
    }
    harm_info = {
        'enabled': False,
        'fundamental_hz': F0,
        'orders': [],
        'magnitude_relative_to_h1': {},
        'phase_deg': {},
        'magnitudes': [],
        'thd_percent': 0.0
    }

    if disturbance_type == 'Normal':
        # Pure sinusoid with nominal noise
        dist_info['magnitude'] = 1.0
        dist_info['magnitude_unit'] = 'pu'

    elif disturbance_type == 'Sag':
        # IEEE Std 1159: RMS reduction to 0.1 - 0.9 pu
        depth = params.get('depth', np.random.uniform(0.10, 0.90))
        dur_cycles = params.get('dur_cycles', np.random.uniform(2.0, 8.0))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.04))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= depth
        metadata.update({'depth': depth, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})
        dist_info.update({
            'magnitude': float(depth),
            'magnitude_unit': 'pu',
            'start_time_s': float(t_start),
            'end_time_s': float(t_end),
            'duration_s': float(t_end - t_start)
        })

    elif disturbance_type == 'Swell':
        # IEEE Std 1159: RMS increase to 1.1 - 1.8 pu
        mag = params.get('magnitude', np.random.uniform(1.10, 1.80))
        dur_cycles = params.get('dur_cycles', np.random.uniform(2.0, 8.0))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.04))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= mag
        metadata.update({'magnitude': mag, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})
        dist_info.update({
            'magnitude': float(mag),
            'magnitude_unit': 'pu',
            'start_time_s': float(t_start),
            'end_time_s': float(t_end),
            'duration_s': float(t_end - t_start)
        })

    elif disturbance_type == 'Interruption':
        # IEEE Std 1159: Severe drop to < 0.10 pu
        depth = params.get('depth', np.random.uniform(0.00, 0.095))
        dur_cycles = params.get('dur_cycles', np.random.uniform(3.0, 8.5))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.03))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= depth
        metadata.update({'depth': depth, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})
        dist_info.update({
            'magnitude': float(depth),
            'magnitude_unit': 'pu',
            'start_time_s': float(t_start),
            'end_time_s': float(t_end),
            'duration_s': float(t_end - t_start)
        })

    elif disturbance_type == 'Harmonics':
        # IEEE Std 519 / 1159: Harmonics (H2, H3, H5, H7, H9, H11) with variable phases
        a2 = params.get('a2', 0.0)
        a3 = params.get('a3', np.random.uniform(0.04, 0.15))
        a5 = params.get('a5', np.random.uniform(0.02, 0.10))
        a7 = params.get('a7', np.random.uniform(0.01, 0.06))
        a9 = params.get('a9', 0.0)
        a11 = params.get('a11', 0.0)

        p2 = params.get('p2', 0.0)
        p3 = params.get('p3', np.random.uniform(0, 2 * np.pi))
        p5 = params.get('p5', np.random.uniform(0, 2 * np.pi))
        p7 = params.get('p7', np.random.uniform(0, 2 * np.pi))
        p9 = params.get('p9', 0.0)
        p11 = params.get('p11', 0.0)

        harm_orders = [2, 3, 5, 7, 9, 11]
        harm_amps = [a2, a3, a5, a7, a9, a11]
        harm_phases = [p2, p3, p5, p7, p9, p11]

        for n, an, pn in zip(harm_orders, harm_amps, harm_phases):
            if an > 1e-6:
                val += an * v_nominal * np.sin(2.0 * np.pi * n * F0 * t + pn)

        thd_calc = float(100.0 * np.sqrt(sum(a**2 for a in harm_amps)))
        active_orders = [n for n, a in zip(harm_orders, harm_amps) if a > 1e-6]
        if not active_orders:
            active_orders = [3, 5, 7]

        mags_rel = {f'H{n}': round(float(a), 6) for n, a in zip(harm_orders, harm_amps)}
        phases_dict = {f'H{n}': round(float(np.rad2deg(p)) % 360.0, 2) for n, p in zip(harm_orders, harm_phases)}

        metadata.update({'a2': a2, 'a3': a3, 'a5': a5, 'a7': a7, 'a9': a9, 'a11': a11})
        dist_info.update({
            'magnitude': thd_calc,
            'magnitude_unit': '%',
            'start_time_s': 0.0,
            'end_time_s': DURATION_SEC,
            'duration_s': DURATION_SEC
        })
        harm_info.update({
            'enabled': True,
            'fundamental_hz': F0,
            'orders': active_orders,
            'magnitude_relative_to_h1': mags_rel,
            'phase_deg': phases_dict,
            'magnitudes': [float(a3), float(a5), float(a7)],  # Backwards compatibility
            'thd_percent': thd_calc
        })

    elif disturbance_type == 'Transient':
        # IEEE Std 1159: Oscillatory transient (300 to 900 Hz, sub-cycle decay)
        f_trans = params.get('f_trans', np.random.uniform(350.0, 750.0))
        amp_trans = params.get('amp_trans', np.random.uniform(0.40, 1.20))
        t_start = params.get('t_start', np.random.uniform(0.04, 0.12))
        tau = params.get('tau', np.random.uniform(0.002, 0.008))  # decay constant (2 - 8 ms)
        t_trans_end = min(DURATION_SEC, t_start + 0.02)
        mask = (t >= t_start) & (t <= t_trans_end)
        
        trans_decay = np.exp(-(t[mask] - t_start) / tau)
        trans_osc = np.sin(2.0 * np.pi * f_trans * (t[mask] - t_start))
        val[mask] += amp_trans * v_nominal * trans_decay * trans_osc
        metadata.update({'f_trans': f_trans, 'amp_trans': amp_trans, 't_start': t_start, 'tau': tau})
        dist_info.update({
            'magnitude': float(amp_trans),
            'magnitude_unit': 'pu',
            'start_time_s': float(t_start),
            'end_time_s': float(t_trans_end),
            'duration_s': float(t_trans_end - t_start)
        })

    elif disturbance_type == 'Flicker':
        # IEEE Std 1453 / 1159: Low-frequency amplitude envelope modulation (5 to 15 Hz)
        f_m = params.get('f_m', np.random.uniform(6.0, 12.0))
        mod_depth = params.get('mod_depth', np.random.uniform(0.03, 0.08))
        val = val * (1.0 + mod_depth * np.sin(2.0 * np.pi * f_m * t))
        metadata.update({'f_m': f_m, 'mod_depth': mod_depth})
        dist_info.update({
            'magnitude': float(mod_depth),
            'magnitude_unit': 'fraction',
            'start_time_s': 0.0,
            'end_time_s': DURATION_SEC,
            'duration_s': DURATION_SEC
        })

    elif disturbance_type == 'Notch':
        # IEEE Std 1159 / 519: Periodic commutation notches
        notch_depth = params.get('notch_depth', np.random.uniform(0.20, 0.60))
        notch_width_rad = params.get('notch_width', 0.03 * 2 * np.pi)
        for cycle in range(10):
            t_cycle_start = cycle * (1.0 / F0)
            phase = ((t - t_cycle_start) * F0) % 1.0
            mask = (phase >= 0.25) & (phase <= 0.25 + (notch_width_rad / (2 * np.pi)))
            val[mask] *= (1.0 - notch_depth)
        metadata.update({'notch_depth': notch_depth})
        dist_info.update({
            'magnitude': float(notch_depth),
            'magnitude_unit': 'depth_fraction',
            'start_time_s': 0.0,
            'end_time_s': DURATION_SEC,
            'duration_s': DURATION_SEC
        })

    # Noise Injection
    noise_enabled = snr_db < 100.0
    if noise_enabled:
        sig_power = np.mean(val ** 2)
        noise_power = sig_power / (10.0 ** (snr_db / 10.0))
        noise = np.random.normal(0, np.sqrt(noise_power), size=BUFFER_SIZE)
        val += noise

    # Calculate actual waveform physical characteristics
    rms_v = float(np.sqrt(np.mean(val ** 2)))
    peak_v = float(np.max(np.abs(val)))

    # Assemble IEEE Std 1159.3-2025 compliant metadata structure
    metadata['waveform'] = {
        'class': disturbance_type,
        'sampling_rate_hz': SAMPLE_RATE,
        'sample_count': BUFFER_SIZE,
        'window_duration_s': DURATION_SEC,
        'fundamental_frequency_hz': F0,
        'rms_voltage': rms_v,
        'peak_voltage': peak_v,
        'phase_deg': 0.0
    }
    metadata['disturbance'] = dist_info
    metadata['harmonics'] = harm_info
    metadata['noise'] = {
        'enabled': noise_enabled,
        'snr_db': float(snr_db)
    }

    return val.astype(np.float32), metadata

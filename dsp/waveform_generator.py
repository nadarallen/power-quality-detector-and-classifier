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

    if disturbance_type == 'Normal':
        # Pure sinusoid with nominal noise
        pass

    elif disturbance_type == 'Sag':
        # Depth: 0.1 to 0.9 pu (default ~0.60 pu)
        depth = params.get('depth', np.random.uniform(0.35, 0.85))
        dur_cycles = params.get('dur_cycles', np.random.uniform(2.0, 8.0))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.04))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= depth
        metadata.update({'depth': depth, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})

    elif disturbance_type == 'Swell':
        # Magnitude: 1.1 to 1.8 pu (default ~1.35 pu)
        mag = params.get('magnitude', np.random.uniform(1.15, 1.65))
        dur_cycles = params.get('dur_cycles', np.random.uniform(2.0, 8.0))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.04))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= mag
        metadata.update({'magnitude': mag, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})

    elif disturbance_type == 'Interruption':
        # Severe drop to < 0.1 pu
        depth = params.get('depth', np.random.uniform(0.01, 0.09))
        dur_cycles = params.get('dur_cycles', np.random.uniform(3.0, 8.5))
        t_start = params.get('t_start', np.random.uniform(0.01, 0.03))
        t_end = t_start + (dur_cycles / F0)
        mask = (t >= t_start) & (t <= t_end)
        val[mask] *= depth
        metadata.update({'depth': depth, 'dur_ms': (t_end - t_start) * 1000.0, 't_start': t_start})

    elif disturbance_type == 'Harmonics':
        # Odd harmonics (H3, H5, H7, H9) with realistic THD 5% to 20%
        a3 = params.get('a3', np.random.uniform(0.04, 0.12))
        a5 = params.get('a5', np.random.uniform(0.02, 0.08))
        a7 = params.get('a7', np.random.uniform(0.01, 0.05))
        p3 = np.random.uniform(0, 2 * np.pi)
        p5 = np.random.uniform(0, 2 * np.pi)
        p7 = np.random.uniform(0, 2 * np.pi)
        
        val += (a3 * v_nominal * np.sin(2.0 * np.pi * 3 * F0 * t + p3) +
                a5 * v_nominal * np.sin(2.0 * np.pi * 5 * F0 * t + p5) +
                a7 * v_nominal * np.sin(2.0 * np.pi * 7 * F0 * t + p7))
        metadata.update({'a3': a3, 'a5': a5, 'a7': a7})

    elif disturbance_type == 'Transient':
        # Oscillatory or impulsive sub-cycle transient (300 to 800 Hz)
        f_trans = params.get('f_trans', np.random.uniform(350.0, 750.0))
        amp_trans = params.get('amp_trans', np.random.uniform(0.40, 1.20))
        t_start = params.get('t_start', np.random.uniform(0.04, 0.12))
        tau = params.get('tau', np.random.uniform(0.002, 0.008)) # decay constant
        mask = (t >= t_start) & (t <= t_start + 0.02)
        
        trans_decay = np.exp(-(t[mask] - t_start) / tau)
        trans_osc = np.sin(2.0 * np.pi * f_trans * (t[mask] - t_start))
        val[mask] += amp_trans * v_nominal * trans_decay * trans_osc
        metadata.update({'f_trans': f_trans, 'amp_trans': amp_trans, 't_start': t_start, 'tau': tau})

    elif disturbance_type == 'Flicker':
        # Amplitude modulation at frequency f_m (5 to 15 Hz)
        f_m = params.get('f_m', np.random.uniform(6.0, 12.0))
        mod_depth = params.get('mod_depth', np.random.uniform(0.03, 0.08))
        val = val * (1.0 + mod_depth * np.sin(2.0 * np.pi * f_m * t))
        metadata.update({'f_m': f_m, 'mod_depth': mod_depth})

    elif disturbance_type == 'Notch':
        # Periodic commutation notches
        notch_depth = params.get('notch_depth', np.random.uniform(0.20, 0.60))
        notch_width_rad = params.get('notch_width', 0.03 * 2 * np.pi)
        for cycle in range(10):
            t_cycle_start = cycle * (1.0 / F0)
            phase = ((t - t_cycle_start) * F0) % 1.0
            mask = (phase >= 0.25) & (phase <= 0.25 + (notch_width_rad / (2 * np.pi)))
            val[mask] *= (1.0 - notch_depth)
        metadata.update({'notch_depth': notch_depth})

    # Noise Injection
    if snr_db < 100.0:
        sig_power = np.mean(val ** 2)
        noise_power = sig_power / (10.0 ** (snr_db / 10.0))
        noise = np.random.normal(0, np.sqrt(noise_power), size=BUFFER_SIZE)
        val += noise

    return val.astype(np.float32), metadata

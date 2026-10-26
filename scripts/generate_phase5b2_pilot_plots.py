"""
scripts/generate_phase5b2_pilot_plots.py
----------------------------------------
Generates high-resolution physical validation plots for Phase 5B.2:
1. Dual-Rate Waveform Comparison: 20 kHz vs 5 kHz on Notch (400 us) and Transient (2.2 kHz).
2. Fixed-Reference Sensor Noise: Noise variance invariance across Normal, Sag, Swell, Interruption.
3. ADC Quantization: 12-bit vs 14-bit resolution, LSB staircase, and residual error.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.measurement_pipeline import (
    add_fixed_reference_sensor_noise,
    quantize_adc,
    decimate_to_5khz
)

FIG_DIR = os.path.join(PROJECT_ROOT, 'docs', 'figures', 'phase5b2_pilot')
os.makedirs(FIG_DIR, exist_ok=True)
PROC_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'processed')


def plot_dual_rate_comparison():
    """Compares 20 kHz and 5 kHz resolution on Notch and Transient."""
    notch_file = os.path.join(PROC_DIR, 'P5B2_NOT_0073_abc_c01_mil.npz')
    trans_file = os.path.join(PROC_DIR, 'P5B2_TRA_0127_abc_c01_mil.npz')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=300)

    # 1. Notch Zoom
    if os.path.exists(notch_file):
        d_notch = np.load(notch_file)
        v20k = d_notch['vabc_20k_quant'][:, 0]
        v5k = d_notch['vabc_5k_quant'][:, 0]
        t20k = np.linspace(0, 200, 4000)
        t5k = np.linspace(0, 200, 1000)

        # Zoom into a 5 ms window around a notch (~t = 60 to 65 ms)
        mask20k = (t20k >= 58.0) & (t20k <= 66.0)
        mask5k = (t5k >= 58.0) & (t5k <= 66.0)

        ax1.plot(t20k[mask20k], v20k[mask20k], 'b-', lw=1.5, label='20 kHz Branch (High-Res, 50 $\\mu$s step)')
        ax1.plot(t20k[mask20k], v20k[mask20k], 'bo', ms=4, alpha=0.6, label='20 kHz Samples (8 pts/notch)')
        ax1.plot(t5k[mask5k], v5k[mask5k], 'r--s', lw=1.2, ms=5, label='5 kHz Canonical (200 $\\mu$s step, 2 pts/notch)')
        ax1.set_title('(a) Commutation Notch Representation: 20 kHz High-Res vs 5 kHz Canonical (400 $\\mu$s width)', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Time (ms)', fontsize=10)
        ax1.set_ylabel('Phase A Voltage (pu)', fontsize=10)
        ax1.grid(True, linestyle=':', alpha=0.6)
        ax1.legend(loc='lower right', fontsize=9)

    # 2. Transient Zoom
    if os.path.exists(trans_file):
        d_trans = np.load(trans_file)
        v20k_t = d_trans['vabc_20k_quant'][:, 0]
        v5k_t = d_trans['vabc_5k_quant'][:, 0]
        t20k_t = np.linspace(0, 200, 4000)
        t5k_t = np.linspace(0, 200, 1000)

        # Zoom into transient onset (~t = 38 to 46 ms)
        mask20k_t = (t20k_t >= 38.0) & (t20k_t <= 46.0)
        mask5k_t = (t5k_t >= 38.0) & (t5k_t <= 46.0)

        ax2.plot(t20k_t[mask20k_t], v20k_t[mask20k_t], 'b-', lw=1.5, label='20 kHz High-Res (Captures High-Freq Dynamics)')
        ax2.plot(t20k_t[mask20k_t], v20k_t[mask20k_t], 'bo', ms=3, alpha=0.5)
        ax2.plot(t5k_t[mask5k_t], v5k_t[mask5k_t], 'r--s', lw=1.2, ms=5, label='5 kHz Decimated Branch (Anti-Aliased Chebyshev)')
        ax2.set_title('(b) High-Frequency Transient Inception: 20 kHz vs 5 kHz Canonical (~2.2 kHz Ringing)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Time (ms)', fontsize=10)
        ax2.set_ylabel('Phase A Voltage (pu)', fontsize=10)
        ax2.grid(True, linestyle=':', alpha=0.6)
        ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, 'dual_rate_notch_transient_comparison.png')
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved: {out_path}")


def plot_fixed_reference_noise():
    """Demonstrates noise variance invariance across Normal, Sag, Swell, Interruption."""
    t = np.linspace(0, 0.05, 1000)  # 50 ms
    w0 = 2 * np.pi * 60.0

    v_norm = 0.5887 * np.sqrt(2) * np.sin(w0 * t)
    v_sag = 0.20 * np.sqrt(2) * np.sin(w0 * t)
    v_swl = 0.85 * np.sqrt(2) * np.sin(w0 * t)
    v_int = 0.005 * np.sqrt(2) * np.sin(w0 * t)

    vn_norm, m_norm = add_fixed_reference_sensor_noise(v_norm, target_snr_db=52.0, seed=1)
    vn_sag, m_sag = add_fixed_reference_sensor_noise(v_sag, target_snr_db=52.0, seed=1)
    vn_swl, m_swl = add_fixed_reference_sensor_noise(v_swl, target_snr_db=52.0, seed=1)
    vn_int, m_int = add_fixed_reference_sensor_noise(v_int, target_snr_db=52.0, seed=1)

    fig, axs = plt.subplots(2, 2, figsize=(12, 8), dpi=300)

    cases = [
        ('Normal (Nominal RMS = 0.589 pu)', v_norm, vn_norm, m_norm, axs[0, 0]),
        ('Sag (Deep Fault RMS = 0.200 pu)', v_sag, vn_sag, m_sag, axs[0, 1]),
        ('Swell (Capacitor RMS = 0.850 pu)', v_swl, vn_swl, m_swl, axs[1, 0]),
        ('Interruption (Residual RMS = 0.005 pu)', v_int, vn_int, m_int, axs[1, 1])
    ]

    for title, v_clean, v_noisy, meta, ax in cases:
        noise = v_noisy - v_clean
        t_ms = t * 1000.0
        ax.plot(t_ms, v_noisy, color='#1f77b4', alpha=0.8, lw=1.2, label='Noisy Waveform (52 dB SNR)')
        ax.plot(t_ms, v_clean, color='#ff7f0e', lw=1.8, linestyle='--', label='Clean Signal')
        ax.plot(t_ms, noise, color='#2ca02c', alpha=0.5, lw=0.8, label=f'Noise ($\\sigma$ = {meta["measured_sample_noise_std_pu"]:.6f} pu)')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Time (ms)', fontsize=9)
        ax.set_ylabel('Voltage (pu)', fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper right', fontsize=8)

    plt.suptitle('Fixed-Reference AWGN Sensor Noise Validation (Constant $\\sigma_{noise} \\approx 0.001479$ pu across Disturbances)',
                 fontsize=13, fontweight='bold', y=0.995)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, 'fixed_reference_sensor_noise_comparison.png')
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved: {out_path}")


def plot_adc_quantization():
    """Plots 12-bit vs 14-bit ADC quantization staircase and error."""
    t = np.linspace(0, 0.02, 1000)
    v_clean = 0.5887 * np.sqrt(2) * np.sin(2 * np.pi * 60.0 * t)

    v_q12 = quantize_adc(v_clean, bits=12, v_fs=1.8)
    v_q14 = quantize_adc(v_clean, bits=14, v_fs=1.8)

    err12 = (v_clean - v_q12) * 1e3  # in milli-pu
    err14 = (v_clean - v_q14) * 1e3  # in milli-pu

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=300)

    t_ms = t * 1000.0
    # Zoom around crest: 3.5 to 5.5 ms
    zoom = (t_ms >= 3.5) & (t_ms <= 5.5)

    ax1.plot(t_ms[zoom], v_clean[zoom], 'k-', lw=1.5, label='Analog Signal (Continuous pu)')
    ax1.step(t_ms[zoom], v_q12[zoom], 'r-', lw=1.3, where='mid', label='12-bit ADC ($q = 0.879$ mpu)')
    ax1.step(t_ms[zoom], v_q14[zoom], 'b-', lw=1.3, where='mid', label='14-bit ADC ($q = 0.220$ mpu)')
    ax1.set_title('(a) Bipolar ADC Quantization Staircase Zoom (Crest Window)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Time (ms)', fontsize=10)
    ax1.set_ylabel('Voltage (pu)', fontsize=10)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='lower center', fontsize=9)

    ax2.plot(t_ms, err12, 'r-', alpha=0.7, lw=1.0, label='12-bit Residual Error ($\\pm q/2 = \\pm 0.439$ mpu)')
    ax2.plot(t_ms, err14, 'b-', alpha=0.8, lw=1.0, label='14-bit Residual Error ($\\pm q/2 = \\pm 0.110$ mpu)')
    ax2.axhline(0.8789 / 2.0, color='r', linestyle=':', alpha=0.5)
    ax2.axhline(-0.8789 / 2.0, color='r', linestyle=':', alpha=0.5)
    ax2.axhline(0.2197 / 2.0, color='b', linestyle=':', alpha=0.5)
    ax2.axhline(-0.2197 / 2.0, color='b', linestyle=':', alpha=0.5)
    ax2.set_title('(b) Quantization Residual Error $e(t) = v(t) - v_{quant}(t)$ over Full Cycle', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Time (ms)', fontsize=10)
    ax2.set_ylabel('Residual Error (milli-pu)', fontsize=10)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, 'adc_quantization_12bit_vs_14bit.png')
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[Plot] Saved: {out_path}")


if __name__ == '__main__':
    plot_dual_rate_comparison()
    plot_fixed_reference_noise()
    plot_adc_quantization()
    print("All Phase 5B.2 physical validation figures generated successfully.")

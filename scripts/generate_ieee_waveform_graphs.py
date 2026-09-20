"""
IEEE Std 1159 & IEEE Std 519 Waveform Visualization & Parameter Annotation
---------------------------------------------------------------------------
Generates publication-quality, standards-annotated waveform plots for:
1. Normal
2. Voltage Sag
3. Voltage Swell
4. Voltage Interruption
5. Harmonics (with FFT spectral inset)
6. Oscillatory Transient
7. Voltage Flicker
8. Voltage Notch
9. Consolidated 8-panel comparison overview

Each individual plot features:
- Top panel: Pure nominal reference sinusoid v(t) = Vm * sin(2*pi*f0*t)
- Middle panel: Disturbed waveform synthesized directly by dsp/waveform_generator.py
- Bottom panel: Comparative overlay (Reference vs Disturbed) with shaded disturbance
  regions and parameter annotation callout boxes.
- Physically meaningful engineering units (Time in ms, Voltage in pu, Freq in Hz).
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.fft import rfft, rfftfreq

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dsp.waveform_generator import (
    generate_pqd_waveform,
    CLASSES,
    SAMPLE_RATE,
    BUFFER_SIZE,
    DURATION_SEC,
    F0
)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'figures', 'waveforms')
os.makedirs(OUT_DIR, exist_ok=True)

# Styling palette
COLOR_NOMINAL = '#4A5568'    # Slate Gray
COLOR_DISTURBED = '#E53E3E'  # Vibrant Red
COLOR_OVERLAY = '#3182CE'    # Deep Blue
COLOR_SHADING = '#FEB2B2'    # Soft Red Tint
COLOR_GRID = '#E2E8F0'       # Soft Light Gray
BG_BOX = '#F7FAFC'          # Clean Card White


def get_curated_params(cls_name: str) -> dict:
    """Returns representative, standards-aligned parameters for clean visualization."""
    if cls_name == 'Normal':
        return {}
    elif cls_name == 'Sag':
        return {'depth': 0.45, 'dur_cycles': 4.0, 't_start': 0.030}
    elif cls_name == 'Swell':
        return {'magnitude': 1.45, 'dur_cycles': 4.0, 't_start': 0.030}
    elif cls_name == 'Interruption':
        return {'depth': 0.03, 'dur_cycles': 5.0, 't_start': 0.030}
    elif cls_name == 'Harmonics':
        return {'a3': 0.12, 'a5': 0.07, 'a7': 0.04, 'p3': 0.0, 'p5': 0.0, 'p7': 0.0}
    elif cls_name == 'Transient':
        return {'f_trans': 550.0, 'amp_trans': 0.85, 't_start': 0.065, 'tau': 0.005}
    elif cls_name == 'Flicker':
        return {'f_m': 8.0, 'mod_depth': 0.08}
    elif cls_name == 'Notch':
        return {'notch_depth': 0.45, 'notch_width': 0.035 * 2 * np.pi}
    return {}


def format_callout_text(cls_name: str, meta: dict) -> str:
    """Formats exact, physically grounded parameter annotations for each disturbance."""
    wf = meta['waveform']
    dist = meta['disturbance']
    harm = meta['harmonics']
    
    lines = [
        r"$\bf{Waveform\ Specifications}$",
        f"Fundamental Freq ($f_0$): {wf['fundamental_frequency_hz']:.1f} Hz",
        f"Sampling Rate ($F_s$): {wf['sampling_rate_hz']:.0f} Hz",
        f"Observation Window ($T$): {wf['window_duration_s']*1000.0:.0f} ms ({wf['sample_count']} pts)",
        f"Nominal Peak ($V_m$): {1.012:.3f} pu | RMS: {wf['rms_voltage']:.3f} pu",
        r"$\bf{Disturbance\ Parameters}$"
    ]

    if cls_name == 'Normal':
        lines.append("Class: Nominal Steady-State (IEEE 1159)")
        lines.append("Harmonic Content: THD < 1.0%")
        lines.append(f"SNR: {meta['noise']['snr_db']:.0f} dB")
    elif cls_name == 'Sag':
        lines.append(f"Sag Depth: {dist['magnitude']:.2f} pu (IEEE 1159: [0.1, 0.9])")
        lines.append(f"Start Time ($t_{{start}}$): {dist['start_time_s']*1000.0:.1f} ms")
        lines.append(f"End Time ($t_{{end}}$): {dist['end_time_s']*1000.0:.1f} ms")
        lines.append(f"Duration: {dist['duration_s']*1000.0:.1f} ms ({dist['duration_s']*F0:.1f} cycles)")
    elif cls_name == 'Swell':
        lines.append(f"Swell Magnitude: {dist['magnitude']:.2f} pu (IEEE 1159: [1.1, 1.8])")
        lines.append(f"Start Time ($t_{{start}}$): {dist['start_time_s']*1000.0:.1f} ms")
        lines.append(f"End Time ($t_{{end}}$): {dist['end_time_s']*1000.0:.1f} ms")
        lines.append(f"Duration: {dist['duration_s']*1000.0:.1f} ms ({dist['duration_s']*F0:.1f} cycles)")
    elif cls_name == 'Interruption':
        lines.append(f"Residual Voltage: {dist['magnitude']:.3f} pu (IEEE 1159: < 0.10 pu)")
        lines.append(f"Start Time ($t_{{start}}$): {dist['start_time_s']*1000.0:.1f} ms")
        lines.append(f"End Time ($t_{{end}}$): {dist['end_time_s']*1000.0:.1f} ms")
        lines.append(f"Duration: {dist['duration_s']*1000.0:.1f} ms ({dist['duration_s']*F0:.1f} cycles)")
    elif cls_name == 'Harmonics':
        lines.append(f"Harmonic Orders: {harm['orders']} (Odd integer fn = n*f0)")
        lines.append(f"Magnitudes: H3={harm['magnitudes'][0]:.2f}, H5={harm['magnitudes'][1]:.2f}, H7={harm['magnitudes'][2]:.2f} pu")
        lines.append(f"Total Harmonic Distortion: {harm['thd_percent']:.2f}% (IEEE 519)")
    elif cls_name == 'Transient':
        lines.append(f"Peak Added Magnitude: {dist['magnitude']:.2f} pu")
        lines.append(f"Oscillation Freq ($f_{{trans}}$): {meta['f_trans']:.1f} Hz (IEEE 1159: [300, 900])")
        lines.append(f"Start Time ($t_{{start}}$): {dist['start_time_s']*1000.0:.1f} ms")
        lines.append(f"Decay Constant ($\\tau$): {meta['tau']*1000.0:.1f} ms (sub-cycle decay)")
    elif cls_name == 'Flicker':
        lines.append(f"Envelope Modulation Freq ($f_m$): {meta['f_m']:.1f} Hz (IEEE 1453)")
        lines.append(rf"Modulation Depth ($\Delta V/V$): {meta['mod_depth']*100.0:.1f}%")
        lines.append("Periodic Window: Full 200 ms Window")
    elif cls_name == 'Notch':
        lines.append(f"Notch Commutation Depth: {dist['magnitude']*100.0:.1f}% (IEEE 1159)")
        lines.append("Notch Periodicity: Synchronized (1 notch / cycle)")
        lines.append("Notch Duration: ~0.7 ms (< 0.5 cycle)")

    return "\n".join(lines)


def plot_single_waveform(cls_name: str):
    """Plots standard 3-panel representation with physical overlay and parameters."""
    t_ms = np.arange(BUFFER_SIZE) / SAMPLE_RATE * 1000.0
    t_s = t_ms / 1000.0
    v_nominal = 1.012 * np.sin(2.0 * np.pi * F0 * t_s)

    params = get_curated_params(cls_name)
    wave, meta = generate_pqd_waveform(cls_name, snr_db=50.0, seed=42, custom_params=params)

    fig = plt.figure(figsize=(12, 9), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.0, 1.35])

    # --------------------------------------------------------------------------
    # Panel 1: Pure Nominal Reference Sinusoid
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(t_ms, v_nominal, color=COLOR_NOMINAL, linewidth=1.8, label=r"Nominal $v_{\mathrm{nom}}(t) = V_m \sin(2\pi f_0 t)$")
    ax1.set_title(f"1. Nominal Reference Sinusoid ($f_0 = 50.0$ Hz, $V_m = 1.012$ pu)", fontsize=11, fontweight='bold', loc='left')
    ax1.set_xlim(0, 200)
    ax1.set_ylim(-2.2, 2.2)
    ax1.set_ylabel("Voltage [pu]", fontsize=10)
    ax1.grid(True, linestyle=':', color=COLOR_GRID, alpha=0.8)
    ax1.legend(loc='upper right', framealpha=0.9)

    # --------------------------------------------------------------------------
    # Panel 2: Actual Disturbed PQ Waveform
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.plot(t_ms, wave, color=COLOR_DISTURBED, linewidth=1.8, label=f"Disturbed Signal: {cls_name}")
    ax2.set_title(f"2. Synthesized PQ Disturbance Waveform: {cls_name}", fontsize=11, fontweight='bold', loc='left')
    ax2.set_xlim(0, 200)
    ax2.set_ylim(-2.2, 2.2)
    ax2.set_ylabel("Voltage [pu]", fontsize=10)
    ax2.grid(True, linestyle=':', color=COLOR_GRID, alpha=0.8)
    ax2.legend(loc='upper right', framealpha=0.9)

    # --------------------------------------------------------------------------
    # Panel 3: Overlay (Reference vs Disturbed) + Parameter Annotations
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(t_ms, v_nominal, color=COLOR_NOMINAL, linestyle='--', linewidth=1.4, alpha=0.7, label="Nominal Reference")
    ax3.plot(t_ms, wave, color=COLOR_OVERLAY, linewidth=1.8, label=f"Disturbed ({cls_name})")

    # Shading active disturbance regions where applicable
    dist = meta['disturbance']
    if dist['duration_s'] > 0.0 and cls_name in ['Sag', 'Swell', 'Interruption', 'Transient']:
        t_start_ms = dist['start_time_s'] * 1000.0
        t_end_ms = dist['end_time_s'] * 1000.0
        ax3.axvspan(t_start_ms, t_end_ms, color=COLOR_SHADING, alpha=0.35, label=f"Active Event Window ({t_end_ms - t_start_ms:.1f} ms)")
        ax3.axvline(t_start_ms, color='#C53030', linestyle=':', linewidth=1.2)
        ax3.axvline(t_end_ms, color='#C53030', linestyle=':', linewidth=1.2)

    ax3.set_title(f"3. Synchronized Overlay & Engineering Characterization: {cls_name}", fontsize=11, fontweight='bold', loc='left')
    ax3.set_xlabel("Time [milliseconds]", fontsize=10)
    ax3.set_ylabel("Voltage [pu]", fontsize=10)
    ax3.set_xlim(0, 200)
    ax3.set_ylim(-2.2, 2.2)
    ax3.grid(True, linestyle=':', color=COLOR_GRID, alpha=0.8)
    ax3.legend(loc='lower left', framealpha=0.9)

    # Callout text box
    callout_txt = format_callout_text(cls_name, meta)
    props = dict(boxstyle='round,pad=0.6', facecolor=BG_BOX, edgecolor='#CBD5E0', alpha=0.95)
    ax3.text(0.985, 0.95, callout_txt, transform=ax3.transAxes, fontsize=8.5,
             verticalalignment='top', horizontalalignment='right', bbox=props, family='sans-serif')

    # If Harmonics, add FFT spectral inset
    if cls_name == 'Harmonics':
        inset_ax = ax3.inset_axes([0.05, 0.48, 0.38, 0.45])
        spec = np.abs(rfft(wave))
        freqs = rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
        band = freqs <= 600.0
        inset_ax.plot(freqs[band], spec[band] / spec[np.argmin(np.abs(freqs - 50.0))], color='#805AD5', linewidth=1.6)
        inset_ax.set_title("Discrete FFT Spectrum (H1 - H11)", fontsize=8, fontweight='bold')
        inset_ax.set_xlabel("Frequency [Hz]", fontsize=7)
        inset_ax.set_ylabel("Ratio to H1", fontsize=7)
        inset_ax.tick_params(labelsize=6)
        inset_ax.grid(True, linestyle=':', alpha=0.6)
        for h, n in [(50, 'f0'), (150, 'H3'), (250, 'H5'), (350, 'H7')]:
            inset_ax.annotate(n, xy=(h, spec[np.argmin(np.abs(freqs - h))] / spec[np.argmin(np.abs(freqs - 50.0))]),
                              xytext=(h, 0.25), fontsize=6, fontweight='bold', ha='center',
                              arrowprops=dict(arrowstyle='->', lw=0.6, color='#805AD5'))

    out_path = os.path.join(OUT_DIR, f"{cls_name.lower()}_waveform.png")
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved: {out_path}")
    return out_path


def plot_consolidated_grid():
    """Plots a consolidated 8-panel grid showing all disturbance classes together."""
    t_ms = np.arange(BUFFER_SIZE) / SAMPLE_RATE * 1000.0
    t_s = t_ms / 1000.0
    v_nominal = 1.012 * np.sin(2.0 * np.pi * F0 * t_s)

    fig, axes = plt.subplots(4, 2, figsize=(16, 14), constrained_layout=True, sharex=True, sharey=True)
    axes = axes.flatten()

    for i, cls_name in enumerate(CLASSES):
        ax = axes[i]
        params = get_curated_params(cls_name)
        wave, meta = generate_pqd_waveform(cls_name, snr_db=50.0, seed=42, custom_params=params)

        ax.plot(t_ms, v_nominal, color=COLOR_NOMINAL, linestyle='--', linewidth=1.0, alpha=0.6, label='Nominal')
        ax.plot(t_ms, wave, color=COLOR_OVERLAY, linewidth=1.4, label=cls_name)

        # Highlight event window
        dist = meta['disturbance']
        if dist['duration_s'] > 0.0 and cls_name in ['Sag', 'Swell', 'Interruption', 'Transient']:
            t_start_ms = dist['start_time_s'] * 1000.0
            t_end_ms = dist['end_time_s'] * 1000.0
            ax.axvspan(t_start_ms, t_end_ms, color=COLOR_SHADING, alpha=0.3)

        ax.set_title(f"{i+1}. {cls_name} (RMS={meta['waveform']['rms_voltage']:.3f} pu)", fontsize=11, fontweight='bold', loc='left')
        ax.grid(True, linestyle=':', color=COLOR_GRID, alpha=0.8)
        ax.set_ylabel("Voltage [pu]", fontsize=9)
        if i >= 6:
            ax.set_xlabel("Time [ms]", fontsize=9)
        ax.legend(loc='lower right', fontsize=8, framealpha=0.85)

    out_path = os.path.join(OUT_DIR, "all_waveforms_comparison.png")
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved consolidated grid: {out_path}")


def main():
    print("=" * 70)
    print("      GENERATING IEEE-ALIGNED STANDARDS WAVEFORM FIGURES      ")
    print("=" * 70)

    for cls in CLASSES:
        plot_single_waveform(cls)

    plot_consolidated_grid()
    print("\n[Success] All IEEE waveform figures generated successfully in docs/figures/waveforms/")


if __name__ == '__main__':
    main()

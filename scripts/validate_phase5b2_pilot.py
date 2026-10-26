"""
scripts/validate_phase5b2_pilot.py
----------------------------------
Comprehensive physical validation and artifact generation for the Phase 5B.2 Remediation Pilot.

Resolves Phase 5B.1 Engineering Audit Blockers:
1. Fixed-reference sensor-noise model (independent of disturbance power, V_nom_rms=0.5887 pu, P_nom=0.3466 pu^2).
2. Mathematically defined 12-bit and 14-bit symmetric bipolar ADC quantization with saturation.
3. Dual-rate verification:
   - High-resolution branch: 20 kHz (4,000 samples per 200 ms frame)
   - Canonical branch: 5 kHz (1,000 samples per 200 ms frame) via 8th-order Chebyshev Type I anti-alias filter
4. Evaluates notch width (400 us = 8 samples @ 20 kHz vs 2 samples @ 5 kHz) and transient frequency (~2.2 kHz).
5. Validates electrical physics, generates manifest v2, and computes SHA-256 checksums.
"""

import os
import sys
import json
import hashlib
import numpy as np
import scipy.io
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from pipeline.measurement_pipeline import (
    add_fixed_reference_sensor_noise,
    quantize_adc,
    decimate_to_5khz,
    NOMINAL_REFERENCE_POWER_PU,
    NOMINAL_BUS5_RMS_PU
)
from pipeline.disturbance_validator import (
    compute_half_cycle_rms,
    validate_sag_frame,
    validate_swell_frame,
    validate_interruption_frame,
    validate_harmonics_frame,
    validate_flicker_frame,
    validate_notch_frame,
    validate_transient_frame
)

RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'raw')
PROCESSED_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'processed')
MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'pilot_manifest_v2.json')
CHECKSUMS_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'checksums_sha256.txt')

os.makedirs(PROCESSED_DIR, exist_ok=True)


def validate_normal_physical(vabc: np.ndarray, feats: Dict[str, Any]) -> Dict[str, Any]:
    """Physical validation for Normal steady-state frames."""
    rms_v = feats['rms_voltage']
    peak_v = feats['peak_voltage']
    sys_f = feats['system_freq']
    thd = feats['thd']

    mag_pass = 0.50 <= rms_v <= 0.70
    freq_pass = 59.85 <= sys_f <= 60.15
    thd_pass = thd < 2.5
    overall_pass = mag_pass and freq_pass and thd_pass

    return {
        'status': 'PASS' if overall_pass else 'FAIL',
        'passed': overall_pass,
        'physical_validation_passed': overall_pass,
        'rms_voltage_pu': float(rms_v),
        'peak_voltage_pu': float(peak_v),
        'system_freq_hz': float(sys_f),
        'thd_percent': float(thd),
        'details': {
            'mag_pass': mag_pass,
            'freq_pass': freq_pass,
            'thd_pass': thd_pass
        }
    }


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def evaluate_high_rate_spectral(v_20k: np.ndarray, fs: float = 20000.0) -> Dict[str, Any]:
    """Evaluates high-rate frequency content and transient peak frequency."""
    n_pts = v_20k.shape[0]
    # FFT on phase A
    sig = v_20k[:, 0]
    fft_vals = np.abs(np.fft.rfft(sig)) / (n_pts / 2.0)
    freqs = np.fft.rfftfreq(n_pts, d=1.0 / fs)

    # Find dominant peak outside 60 Hz fundamental (above 150 Hz)
    hf_mask = freqs >= 150.0
    if np.any(hf_mask):
        hf_peak_idx = np.argmax(fft_vals[hf_mask])
        hf_peak_freq = float(freqs[hf_mask][hf_peak_idx])
        hf_peak_mag = float(fft_vals[hf_mask][hf_peak_idx])
    else:
        hf_peak_freq = 0.0
        hf_peak_mag = 0.0

    return {
        'nyquist_limit_hz': fs / 2.0,
        'hf_peak_frequency_hz': hf_peak_freq,
        'hf_peak_magnitude_pu': hf_peak_mag
    }


def run_validation():
    print("=" * 80)
    print("PHASE 5B.2 REMEDIATION PILOT: PHYSICAL VALIDATION & ARTIFACT GENERATION")
    print("=" * 80)

    matrix_file = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b2_simulation_matrix.json')
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matrix not found at {matrix_file}")

    with open(matrix_file, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    matrix_trajectories = {t['trajectory_id']: t for t in catalog['trajectories']}

    raw_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith('.mat')])
    print(f"Discovered {len(raw_files)} raw remediation pilot simulation files in {RAW_DIR}.")

    if len(raw_files) == 0:
        raise RuntimeError("No raw simulation files found! Run run_phase5b2_remediation_pilot.m first.")

    manifest_records = []
    checksum_lines = []

    for fname in raw_files:
        fpath = os.path.join(RAW_DIR, fname)
        traj_id = os.path.splitext(fname)[0]
        meta = matrix_trajectories.get(traj_id, {})
        cls_name = meta.get('class', 'Unknown')
        pilot_id = meta.get('remediation_pilot_id', None)

        print(f"\n[Processing Pilot V2 #{pilot_id}] {traj_id} (Class: {cls_name})")

        mat = scipy.io.loadmat(fpath)
        v_raw_20k = mat['V_frame_20k']  # (4000, 3)
        v_raw_5k_mat = mat['V_frame_5k']  # (1000, 3)
        i_raw_20k = mat['I_frame_20k']  # (4000, 3)
        i_raw_5k = mat['I_frame_5k']  # (1000, 3)
        t_wall = float(mat['t_wall'][0, 0])

        # Extract solver stats
        s_stats = mat['solver_stats']
        solver_stats = {
            'total_solver_steps': int(s_stats['total_solver_steps'][0, 0][0, 0]),
            'min_step_us': float(s_stats['min_step_us'][0, 0][0, 0]),
            'max_step_us': float(s_stats['max_step_us'][0, 0][0, 0]),
            'mean_step_us': float(s_stats['mean_step_us'][0, 0][0, 0]),
            'configured_max_step_us': float(s_stats['configured_max_step_us'][0, 0][0, 0])
        }

        # Assert shapes and integrity
        assert v_raw_20k.shape == (4000, 3), f"Invalid V 20k shape {v_raw_20k.shape}"
        assert v_raw_5k_mat.shape == (1000, 3), f"Invalid V 5k shape {v_raw_5k_mat.shape}"
        assert not np.isnan(v_raw_20k).any(), "NaN in V_frame_20k"
        assert not np.isinf(v_raw_20k).any(), "Inf in V_frame_20k"

        # Decimate 20k to 5k via zero-phase 8th-order Chebyshev anti-alias filter
        v_raw_5k = decimate_to_5khz(v_raw_20k)
        assert v_raw_5k.shape == (1000, 3), f"Decimated shape {v_raw_5k.shape} != (1000, 3)"

        # Settings
        snr_target = float(meta.get('sensor_noise_snr_db', 52.0))
        adc_bits = int(meta.get('adc_resolution_bits', 14))
        seed = int(meta.get('random_seed', 42 + (pilot_id or 0)))
        v_fs = 1.8

        # 1. High-resolution branch processing (20 kHz)
        v_noisy_20k, noise_meta_20k = add_fixed_reference_sensor_noise(v_raw_20k, target_snr_db=snr_target, seed=seed)
        v_quant_20k = quantize_adc(v_noisy_20k, bits=adc_bits, v_fs=v_fs)
        q_lsb = (2.0 * v_fs) / (2 ** adc_bits)
        adc_meta_20k = {
            'lsb_pu': q_lsb,
            'is_saturated': bool(np.any(v_noisy_20k <= -v_fs) or np.any(v_noisy_20k >= (v_fs - q_lsb)))
        }

        # 2. Canonical branch processing (5 kHz)
        # Apply independent noise realization with seed offset for 5 kHz
        v_noisy_5k, noise_meta_5k = add_fixed_reference_sensor_noise(v_raw_5k, target_snr_db=snr_target, seed=seed + 1000)
        v_quant_5k = quantize_adc(v_noisy_5k, bits=adc_bits, v_fs=v_fs)
        adc_meta_5k = {
            'lsb_pu': q_lsb,
            'is_saturated': bool(np.any(v_noisy_5k <= -v_fs) or np.any(v_noisy_5k >= (v_fs - q_lsb)))
        }

        # Spectral analysis of 20 kHz branch
        spectral_meta = evaluate_high_rate_spectral(v_quant_20k, fs=20000.0)

        # Extract authoritative 32 features from 5 kHz quantized signal
        feats_dict = extract_enhanced_features(v_quant_5k[:, 0], sample_rate=5000.0, f0=60.0)

        # Half-cycle RMS profiles on 5 kHz
        rms_traces = []
        for ch in range(3):
            rms_tr, t_tr = compute_half_cycle_rms(v_quant_5k[:, ch], fs=5000.0, f0=60.0)
            rms_traces.append(rms_tr)
        rms_traces = np.array(rms_traces)

        pre_rms = float(np.mean(rms_traces[:, :20]))
        mid_rms = float(np.mean(rms_traces[:, 40:80]))
        post_rms = float(np.mean(rms_traces[:, -20:]))

        # Physical validation on 5 kHz canonical frame
        val_result = {}
        try:
            if cls_name == 'Normal':
                val_result = validate_normal_physical(v_quant_5k, feats_dict)
            elif cls_name == 'Sag':
                val_result = validate_sag_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Swell':
                val_result = validate_swell_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Interruption':
                val_result = validate_interruption_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Harmonics':
                val_result = validate_harmonics_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Flicker':
                val_result = validate_flicker_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Notch':
                val_result = validate_notch_frame(v_quant_5k, feats_dict)
            elif cls_name == 'Transient':
                val_result = validate_transient_frame(v_quant_5k, feats_dict)
            else:
                val_result = {'passed': False, 'status': 'UNKNOWN_CLASS'}
        except Exception as e:
            val_result = {'passed': False, 'status': f'ERROR: {str(e)}'}

        is_passed = bool(val_result.get('physical_validation_passed', val_result.get('passed', False)))
        status_str = 'PASS' if is_passed else 'FAIL'

        print(f" -> Physical Validation: {status_str} | RMS pre={pre_rms:.3f}, mid={mid_rms:.3f}, post={post_rms:.3f} | THD={feats_dict.get('thd', 0):.2f}%")
        print(f"    Noise: sigma={noise_meta_5k['theoretical_noise_std_pu']:.6f} pu (SNR target={snr_target} dB, sample={noise_meta_5k['measured_nominal_snr_db']:.2f} dB)")
        print(f"    ADC: {adc_bits}-bit, q={adc_meta_5k['lsb_pu']:.6f} pu, saturated={adc_meta_5k['is_saturated']}")
        print(f"    Solver: min dt={solver_stats['min_step_us']:.2f} us, max dt={solver_stats['max_step_us']:.2f} us (MaxStep configured=25.0 us)")
        if cls_name == 'Transient':
            print(f"    High-Rate Spectral: Peak Freq={spectral_meta['hf_peak_frequency_hz']:.1f} Hz, Mag={spectral_meta['hf_peak_magnitude_pu']:.4f} pu")

        # Save processed NPZ file with dual-rate data and full provenance
        npz_name = f"{traj_id}.npz"
        npz_path = os.path.join(PROCESSED_DIR, npz_name)
        np.savez_compressed(
            npz_path,
            vabc_20k_quant=v_quant_20k,
            vabc_20k_noisy=v_noisy_20k,
            vabc_20k_raw=v_raw_20k,
            vabc_5k_quant=v_quant_5k,
            vabc_5k_noisy=v_noisy_5k,
            vabc_5k_raw=v_raw_5k,
            iabc_20k=i_raw_20k,
            iabc_5k=i_raw_5k,
            trajectory_id=traj_id,
            remediation_pilot_id=pilot_id,
            class_name=cls_name,
            label_idx=meta.get('label_idx'),
            operating_condition_id=meta.get('operating_condition_id'),
            condition_family=meta.get('condition_family'),
            split=meta.get('split'),
            fs_high=20000.0,
            fs_canonical=5000.0,
            f0=60.0,
            sensor_noise_snr_db=snr_target,
            adc_resolution_bits=adc_bits,
            adc_v_fs_pu=v_fs,
            pre_event_rms=pre_rms,
            event_rms=mid_rms,
            post_event_rms=post_rms,
            feats_32=json.dumps(feats_dict),
            validation_passed=is_passed,
            validation_details=json.dumps(val_result),
            solver_stats=json.dumps(solver_stats),
            spectral_meta=json.dumps(spectral_meta),
            t_wall_sim=t_wall
        )

        raw_sha = compute_sha256(fpath)
        proc_sha = compute_sha256(npz_path)

        checksum_lines.append(f"{raw_sha}  raw/{fname}")
        checksum_lines.append(f"{proc_sha}  processed/{npz_name}")

        rec = {
            'remediation_pilot_id': pilot_id,
            'trajectory_id': traj_id,
            'class': cls_name,
            'label_idx': meta.get('label_idx'),
            'operating_condition_id': meta.get('operating_condition_id'),
            'condition_family': meta.get('condition_family'),
            'split': meta.get('split'),
            'parameters': meta.get('parameters'),
            'sensor_noise_snr_db': snr_target,
            'adc_resolution_bits': adc_bits,
            'adc_v_fs_pu': v_fs,
            'adc_lsb_pu': adc_meta_5k['lsb_pu'],
            'noise_theoretical_std_pu': noise_meta_5k['theoretical_noise_std_pu'],
            'noise_measured_snr_5k_db': noise_meta_5k['measured_nominal_snr_db'],
            'noise_measured_snr_20k_db': noise_meta_20k['measured_nominal_snr_db'],
            'solver_steps': solver_stats['total_solver_steps'],
            'solver_max_step_us': solver_stats['max_step_us'],
            'solver_min_step_us': solver_stats['min_step_us'],
            'physical_validation_passed': is_passed,
            'physical_validation_result': val_result,
            'spectral_evaluation': spectral_meta,
            'features_summary': {
                'rms_voltage': feats_dict.get('rms_voltage'),
                'peak_voltage': feats_dict.get('peak_voltage'),
                'thd': feats_dict.get('thd'),
                'system_freq': feats_dict.get('system_freq'),
                'vuf': feats_dict.get('vuf')
            },
            'raw_mat_sha256': raw_sha,
            'processed_npz_sha256': proc_sha,
            'sim_wall_seconds': t_wall
        }
        manifest_records.append(rec)

    # Save manifest
    manifest_doc = {
        'manifest_version': '2.0.0',
        'phase': 'Phase 5B.2 Remediation Pilot',
        'total_remediation_pilots': len(manifest_records),
        'passed_count': sum(1 for r in manifest_records if r['physical_validation_passed']),
        'failed_count': sum(1 for r in manifest_records if not r['physical_validation_passed']),
        'sampling_configurations': {
            'high_rate': {'fs_hz': 20000, 'samples_per_200ms': 4000, 'processing': 'fixed-reference noise + ADC quant'},
            'canonical': {'fs_hz': 5000, 'samples_per_200ms': 1000, 'filter': '8th-order Chebyshev Type I (fc=2.25 kHz)'}
        },
        'sensor_noise_model': {
            'type': 'fixed_nominal_reference_awgn',
            'v_nom_rms_pu': NOMINAL_BUS5_RMS_PU,
            'p_nominal_pu2': NOMINAL_REFERENCE_POWER_PU
        },
        'adc_model': {
            'type': 'symmetric_bipolar',
            'v_fs_pu': 1.8,
            'supported_bits': [12, 14]
        },
        'records': manifest_records
    }

    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest_doc, f, indent=2)

    with open(CHECKSUMS_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(checksum_lines) + "\n")

    print("\n" + "=" * 80)
    print("REMEDIATION PILOT VALIDATION SUMMARY")
    print(f"Total processed: {len(manifest_records)}")
    print(f"Passed gates:    {manifest_doc['passed_count']} / {len(manifest_records)}")
    print(f"Failed gates:    {manifest_doc['failed_count']} / {len(manifest_records)}")
    print(f"Manifest saved:  {MANIFEST_PATH}")
    print(f"Checksums saved: {CHECKSUMS_PATH}")
    print("=" * 80)


if __name__ == '__main__':
    run_validation()

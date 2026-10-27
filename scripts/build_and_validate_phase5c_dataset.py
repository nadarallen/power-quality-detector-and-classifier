"""
scripts/build_and_validate_phase5c_dataset.py
---------------------------------------------
Comprehensive dataset processing, sliding-window generation, dual-rate anti-aliased
filtering, fixed-reference sensor noise, ADC quantization, 32-feature extraction,
physical validation, and manifest creation for Phase 5C.

Generates:
- 144 trajectories x 32 windows = 4,608 frames
- 20 kHz waveform branch: [4608, 4000, 3] float32
- 5 kHz canonical branch: [4608, 1000, 3] float32 (via 8th-order Chebyshev anti-alias filter)
- 32-feature matrix: [4608, 32] float64
- Zero cross-split leakage:
    - Train: 80 trajectories x 32 = 2,560 frames
    - Val: 32 trajectories x 32 = 1,024 frames
    - Challenge: 32 trajectories x 32 = 1,024 frames (Conditions 33-36 quarantined)
"""

import os
import sys
import json
import hashlib
import time
import numpy as np
import pandas as pd
import scipy.io
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER
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

RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'raw')
PROCESSED_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'processed')
MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'dataset_manifest_v2.json')
CHECKSUMS_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'checksums_sha256.txt')
FAILURES_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5c', 'physical_validation_failures.json')

os.makedirs(PROCESSED_DIR, exist_ok=True)


def validate_normal_physical(vabc: np.ndarray, feats: Dict[str, Any]) -> Dict[str, Any]:
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


def build_and_validate_dataset():
    print("=" * 80)
    print("PHASE 5C EXPANDED DATASET: BULK PROCESSING & PHYSICAL VALIDATION")
    print("=" * 80)

    matrix_file = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b2_simulation_matrix.json')
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matrix not found at {matrix_file}")

    with open(matrix_file, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    trajectories = catalog['trajectories']
    num_trajs = len(trajectories)
    windows_per_traj = 32
    total_frames = num_trajs * windows_per_traj

    print(f"Matrix loaded: {num_trajs} trajectories across 8 classes.")
    print(f"Target dataset: {num_trajs} trajs x {windows_per_traj} windows = {total_frames} frames.")

    # Check available raw files
    raw_files = {os.path.splitext(f)[0]: os.path.join(RAW_DIR, f) 
                 for f in os.listdir(RAW_DIR) if f.endswith('.mat')}
    print(f"Available raw simulation files: {len(raw_files)} / {num_trajs}")

    if len(raw_files) < num_trajs:
        print(f"[Warning] Only {len(raw_files)} / {num_trajs} simulations are available so far.")

    # Storage arrays for pre-allocated bulk data
    all_waveforms_20k = np.zeros((total_frames, 4000, 3), dtype=np.float32)
    all_waveforms_5k = np.zeros((total_frames, 1000, 3), dtype=np.float32)
    all_labels = np.zeros(total_frames, dtype=np.int64)
    all_splits = []
    all_traj_ids = []
    all_frame_ids = []
    feature_rows = []

    trajectory_validation_records = []
    validation_failures = []
    checksum_lines = []

    frame_idx = 0
    start_time = time.time()

    for t_idx, sc in enumerate(trajectories):
        traj_id = sc['trajectory_id']
        cls_name = sc['class']
        label_idx = int(sc['label_idx'])
        split = sc['split']
        cond_id = int(sc['operating_condition_id'])
        cond_family = sc['operating_condition_family']
        snr_target = float(sc.get('sensor_noise_snr_db', 52.0))
        adc_bits = int(sc.get('adc_resolution_bits', 14))
        params = sc.get('parameters', {})
        v_fs = 1.8

        if traj_id not in raw_files:
            raise FileNotFoundError(f"Missing raw simulation for {traj_id}. Ensure bulk simulation has completed!")

        mat_path = raw_files[traj_id]
        mat = scipy.io.loadmat(mat_path)

        V_cont_20k = mat['V_cont_20k']  # (7601, 3)
        V_cont_5k_mat = mat['V_cont_5k']  # (1901, 3)
        s_stats = mat['solver_stats']
        t_wall = float(mat['t_wall'][0, 0])

        solver_stats = {
            'total_solver_steps': int(s_stats['total_solver_steps'][0, 0][0, 0]),
            'min_step_us': float(s_stats['min_step_us'][0, 0][0, 0]),
            'max_step_us': float(s_stats['max_step_us'][0, 0][0, 0]),
            'mean_step_us': float(s_stats['mean_step_us'][0, 0][0, 0])
        }

        # Determine reference onset time for disturbance
        if cls_name in ['Sag', 'Swell', 'Interruption']:
            t0 = 0.12
        elif cls_name == 'Transient':
            t0 = float(params.get('onset_ms', 110.0)) / 1000.0
        elif cls_name in ['Flicker', 'Harmonics', 'Notch']:
            t0 = 0.12
        elif cls_name == 'Normal':
            t0 = 0.12
        else:
            t0 = 0.12

        # Physical validation performed on the representative center window (w=16, onset=36ms)
        traj_val_result = None
        traj_passed = False

        # Slice 32 sliding windows
        for w in range(windows_per_traj):
            if cls_name == 'Normal':
                t_win_start = 0.050 + (w * 0.001)
            else:
                onset_ms = 20.0 + (w * 1.0)  # 20.0 ms to 51.0 ms
                t_win_start = t0 - (onset_ms / 1000.0)

            t_win_end = t_win_start + 0.200

            idx_20k_start = int(round(t_win_start * 20000.0))
            idx_20k_end = idx_20k_start + 4000

            idx_5k_start = int(round(t_win_start * 5000.0))
            idx_5k_end = idx_5k_start + 1000

            assert 0 <= idx_20k_start and idx_20k_end <= V_cont_20k.shape[0], \
                f"Window {w} out of bounds for 20k: [{idx_20k_start}, {idx_20k_end}] vs {V_cont_20k.shape[0]}"

            v_raw_20k = V_cont_20k[idx_20k_start:idx_20k_end, :].astype(np.float64)

            # High-rate 20 kHz branch:
            win_seed = 42 + (t_idx * 1000) + w
            v_noisy_20k, noise_meta_20k = add_fixed_reference_sensor_noise(v_raw_20k, target_snr_db=snr_target, seed=win_seed)
            v_quant_20k = quantize_adc(v_noisy_20k, bits=adc_bits, v_fs=v_fs)

            # Canonical 5 kHz branch:
            # Apply 8th-order Chebyshev Type I anti-alias filter and 4:1 decimation from 20 kHz
            v_raw_5k_filtered = decimate_to_5khz(v_raw_20k)
            v_noisy_5k, noise_meta_5k = add_fixed_reference_sensor_noise(v_raw_5k_filtered, target_snr_db=snr_target, seed=win_seed + 50000)
            v_quant_5k = quantize_adc(v_noisy_5k, bits=adc_bits, v_fs=v_fs)

            # Feature extraction on canonical 5 kHz Phase A signal
            feats_dict = extract_enhanced_features(v_quant_5k[:, 0], sample_rate=5000.0, f0=60.0)

            # Validate physical behavior on center window (w=16)
            if w == 16:
                try:
                    if cls_name == 'Normal':
                        traj_val_result = validate_normal_physical(v_quant_5k, feats_dict)
                    elif cls_name == 'Sag':
                        traj_val_result = validate_sag_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Swell':
                        traj_val_result = validate_swell_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Interruption':
                        traj_val_result = validate_interruption_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Harmonics':
                        traj_val_result = validate_harmonics_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Flicker':
                        traj_val_result = validate_flicker_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Notch':
                        traj_val_result = validate_notch_frame(v_quant_5k, feats_dict)
                    elif cls_name == 'Transient':
                        traj_val_result = validate_transient_frame(v_quant_5k, feats_dict)
                    else:
                        traj_val_result = {'passed': False, 'status': 'UNKNOWN_CLASS'}
                except Exception as e:
                    traj_val_result = {'passed': False, 'status': f'ERROR: {str(e)}'}

                traj_passed = bool(traj_val_result.get('physical_validation_passed', traj_val_result.get('passed', False)))
                if not traj_passed:
                    validation_failures.append({
                        'trajectory_id': traj_id,
                        'class': cls_name,
                        'operating_condition_id': cond_id,
                        'split': split,
                        'validation_result': traj_val_result
                    })

            # Record frame data
            frame_id = f"{traj_id}_w{w:02d}"
            all_waveforms_20k[frame_idx] = v_quant_20k.astype(np.float32)
            all_waveforms_5k[frame_idx] = v_quant_5k.astype(np.float32)
            all_labels[frame_idx] = label_idx
            all_splits.append(split)
            all_traj_ids.append(traj_id)
            all_frame_ids.append(frame_id)

            # Collect feature row
            row = {
                'frame_id': frame_id,
                'trajectory_id': traj_id,
                'window_idx': w,
                'class': cls_name,
                'label_idx': label_idx,
                'split': split,
                'operating_condition_id': cond_id,
                'operating_condition_family': cond_family,
                'snr_db': snr_target,
                'adc_bits': adc_bits
            }
            for feat_name in _MODEL_FEATURE_ORDER:
                row[feat_name] = feats_dict.get(feat_name, 0.0)
            feature_rows.append(row)

            frame_idx += 1

        raw_sha = compute_sha256(mat_path)
        checksum_lines.append(f"{raw_sha}  raw/{os.path.basename(mat_path)}")

        trajectory_validation_records.append({
            'trajectory_id': traj_id,
            'class': cls_name,
            'label_idx': label_idx,
            'operating_condition_id': cond_id,
            'condition_family': cond_family,
            'split': split,
            'sensor_noise_snr_db': snr_target,
            'adc_resolution_bits': adc_bits,
            'solver_steps': solver_stats['total_solver_steps'],
            'max_step_us': solver_stats['max_step_us'],
            'min_step_us': solver_stats['min_step_us'],
            'physical_validation_passed': traj_passed,
            'validation_result': traj_val_result,
            'raw_mat_sha256': raw_sha,
            'sim_wall_seconds': t_wall
        })

        if (t_idx + 1) % 18 == 0 or (t_idx + 1) == num_trajs:
            elapsed = time.time() - start_time
            print(f"[{t_idx+1:03d}/{num_trajs}] Processed {frame_idx:04d} frames | Status: {cls_name:12s} | Pass: {traj_passed} | Elapsed: {elapsed:.1f}s")

    print("\n" + "=" * 80)
    print("SAVING PROCESSED ARRAYS & MANIFEST...")
    print("=" * 80)

    # 1. Save 20 kHz waveforms
    path_20k = os.path.join(PROCESSED_DIR, 'phase5c_waveforms_20k.npz')
    np.savez_compressed(
        path_20k,
        waveforms_20k=all_waveforms_20k,
        labels=all_labels,
        splits=np.array(all_splits),
        trajectory_ids=np.array(all_traj_ids),
        frame_ids=np.array(all_frame_ids),
        fs=20000.0
    )
    sha_20k = compute_sha256(path_20k)
    checksum_lines.append(f"{sha_20k}  processed/phase5c_waveforms_20k.npz")
    print(f"Saved 20 kHz waveforms: {path_20k} (SHA: {sha_20k[:16]}...)")

    # 2. Save 5 kHz waveforms
    path_5k = os.path.join(PROCESSED_DIR, 'phase5c_waveforms_5k.npz')
    np.savez_compressed(
        path_5k,
        waveforms_5k=all_waveforms_5k,
        labels=all_labels,
        splits=np.array(all_splits),
        trajectory_ids=np.array(all_traj_ids),
        frame_ids=np.array(all_frame_ids),
        fs=5000.0
    )
    sha_5k = compute_sha256(path_5k)
    checksum_lines.append(f"{sha_5k}  processed/phase5c_waveforms_5k.npz")
    print(f"Saved 5 kHz waveforms:  {path_5k} (SHA: {sha_5k[:16]}...)")

    # 3. Save feature dataframe
    features_df = pd.DataFrame(feature_rows)
    path_feats_csv = os.path.join(PROCESSED_DIR, 'phase5c_features.csv')
    features_df.to_csv(path_feats_csv, index=False)
    sha_feats = compute_sha256(path_feats_csv)
    checksum_lines.append(f"{sha_feats}  processed/phase5c_features.csv")
    print(f"Saved feature table:    {path_feats_csv} (SHA: {sha_feats[:16]}...)")

    # Save feature NPZ array for fast training load
    feature_matrix = features_df[_MODEL_FEATURE_ORDER].values.astype(np.float64)
    path_feats_npz = os.path.join(PROCESSED_DIR, 'phase5c_features.npz')
    np.savez_compressed(
        path_feats_npz,
        features=feature_matrix,
        labels=all_labels,
        splits=np.array(all_splits),
        trajectory_ids=np.array(all_traj_ids),
        frame_ids=np.array(all_frame_ids),
        feature_names=np.array(_MODEL_FEATURE_ORDER)
    )
    sha_feats_npz = compute_sha256(path_feats_npz)
    checksum_lines.append(f"{sha_feats_npz}  processed/phase5c_features.npz")

    # 4. Save validation failures log
    with open(FAILURES_PATH, 'w', encoding='utf-8') as f:
        json.dump(validation_failures, f, indent=2)

    # 5. Build and save Dataset Manifest v2
    split_counts = {
        'train_trajectories': sum(1 for r in trajectory_validation_records if r['split'] == 'train'),
        'val_trajectories': sum(1 for r in trajectory_validation_records if r['split'] == 'val'),
        'challenge_trajectories': sum(1 for r in trajectory_validation_records if r['split'] == 'challenge'),
        'train_frames': sum(1 for s in all_splits if s == 'train'),
        'val_frames': sum(1 for s in all_splits if s == 'val'),
        'challenge_frames': sum(1 for s in all_splits if s == 'challenge'),
        'total_frames': total_frames
    }

    passed_trajs = sum(1 for r in trajectory_validation_records if r['physical_validation_passed'])
    failed_trajs = sum(1 for r in trajectory_validation_records if not r['physical_validation_passed'])

    manifest_doc = {
        'manifest_version': '2.0.0',
        'phase': 'Phase 5C Expanded Dataset Freeze',
        'study': 'IEEE 9-bus Multi-Model Power Quality Comparative Lab',
        'total_trajectories': num_trajs,
        'frames_per_trajectory': windows_per_traj,
        'total_frames': total_frames,
        'passed_trajectories_count': passed_trajs,
        'failed_trajectories_count': failed_trajs,
        'split_summary': split_counts,
        'feature_contract': {
            'dimension': 32,
            'ordering': _MODEL_FEATURE_ORDER
        },
        'sampling_configurations': {
            'high_rate': {
                'fs_hz': 20000,
                'samples_per_frame': 4000,
                'channel_dimensions': [4000, 3],
                'description': 'Direct simulation output resampled at 20 kHz under 25 us solver constraint'
            },
            'canonical': {
                'fs_hz': 5000,
                'samples_per_frame': 1000,
                'channel_dimensions': [1000, 3],
                'description': 'Decimated from 20 kHz via 8th-order Chebyshev Type I anti-alias filter (fc=2.25 kHz)'
            }
        },
        'sensor_noise_model': {
            'type': 'fixed_nominal_reference_awgn',
            'v_nom_rms_pu': NOMINAL_BUS5_RMS_PU,
            'p_nominal_pu2': NOMINAL_REFERENCE_POWER_PU,
            'target_snr_levels_db': [52.0, 46.0, 40.0]
        },
        'adc_model': {
            'type': 'symmetric_bipolar',
            'v_fs_pu': 1.8,
            'supported_bits': [12, 14]
        },
        'trajectories': trajectory_validation_records
    }

    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest_doc, f, indent=2)
    print(f"Saved dataset manifest: {MANIFEST_PATH}")

    # 6. Save Checksums Registry
    with open(CHECKSUMS_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(checksum_lines) + "\n")
    print(f"Saved checksum registry: {CHECKSUMS_PATH}")

    print("\n" + "=" * 80)
    print("PHASE 5C EXPANDED DATASET GENERATION COMPLETE")
    print(f"Total Trajectories Processed: {num_trajs} ({passed_trajs} PASSED, {failed_trajs} FAILED)")
    print(f"Total Dataset Frames:         {total_frames}")
    print(f"  - Train:     {split_counts['train_frames']} frames ({split_counts['train_trajectories']} trajectories)")
    print(f"  - Val:       {split_counts['val_frames']} frames ({split_counts['val_trajectories']} trajectories)")
    print(f"  - Challenge: {split_counts['challenge_frames']} frames ({split_counts['challenge_trajectories']} trajectories)")
    print("=" * 80)


if __name__ == '__main__':
    build_and_validate_dataset()

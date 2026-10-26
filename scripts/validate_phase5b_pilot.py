"""
scripts/validate_phase5b_pilot.py
---------------------------------
Comprehensive physical validation and artifact generation for the Phase 5B Pilot.

Tasks:
1. Loads raw MAT simulation files from data/ieee9bus_60hz_phase5b_pilot/raw/.
2. Applies sensor noise at 52 dB SNR (AWGN per phase channel).
3. Computes physical metrics:
   - Half-cycle windowed RMS trace (pre-event, event, post-event)
   - Fundamental frequency, THD, peak voltage, crest factor, VUF
4. Runs independent class-specific physical validation gates from pipeline.disturbance_validator.
5. Saves processed 1000-sample frames to data/ieee9bus_60hz_phase5b_pilot/processed/.
6. Generates canonical pilot manifest: data/ieee9bus_60hz_phase5b_pilot/pilot_manifest_v1.json.
7. Computes SHA-256 checksums: data/ieee9bus_60hz_phase5b_pilot/checksums_sha256.txt.
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

RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot', 'raw')
PROCESSED_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot', 'processed')
MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot', 'pilot_manifest_v1.json')
CHECKSUMS_PATH = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz_phase5b_pilot', 'checksums_sha256.txt')

os.makedirs(PROCESSED_DIR, exist_ok=True)


def add_sensor_noise(vabc: np.ndarray, target_snr_db: float = 52.0, seed: int = 42) -> np.ndarray:
    """Adds additive white Gaussian noise at target SNR per channel."""
    rng = np.random.RandomState(seed)
    noisy_vabc = np.zeros_like(vabc)
    for ch in range(3):
        sig = vabc[:, ch]
        p_sig = np.mean(sig**2)
        p_noise = p_sig / (10.0 ** (target_snr_db / 10.0))
        noise = rng.normal(0.0, np.sqrt(p_noise), size=sig.shape)
        noisy_vabc[:, ch] = sig + noise
    return noisy_vabc


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


def run_validation():
    print("=" * 70)
    print("PHASE 5B PILOT PHYSICAL VALIDATION & ARTIFACT GENERATION")
    print("=" * 70)

    matrix_file = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b_simulation_matrix.json')
    with open(matrix_file, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    matrix_scenarios = {s['scenario_id']: s for s in catalog['scenarios']}

    raw_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith('.mat')])
    print(f"Discovered {len(raw_files)} raw pilot simulation files in {RAW_DIR}.")

    if len(raw_files) == 0:
        raise RuntimeError("No raw simulation files found! Run run_phase5b_pilot_simulation.m first.")

    manifest_records = []
    checksum_lines = []

    for fname in raw_files:
        fpath = os.path.join(RAW_DIR, fname)
        scen_id = os.path.splitext(fname)[0]
        meta = matrix_scenarios.get(scen_id, {})
        cls_name = meta.get('class', 'Unknown')
        pilot_id = meta.get('pilot_id', None)

        print(f"\n[Processing Pilot #{pilot_id}] {scen_id} (Class: {cls_name})")

        mat = scipy.io.loadmat(fpath)
        v_raw = mat['V_frame'] # (1000, 3)
        i_raw = mat['I_frame'] # (1000, 3)
        t_wall = float(mat['t_wall'][0, 0])

        # Assert shapes and integrity
        assert v_raw.shape == (1000, 3), f"Invalid V shape {v_raw.shape}"
        assert i_raw.shape == (1000, 3), f"Invalid I shape {i_raw.shape}"
        assert not np.isnan(v_raw).any(), "NaN in V_frame"
        assert not np.isinf(v_raw).any(), "Inf in V_frame"

        # Apply canonical 52 dB SNR sensor noise
        snr_target = meta.get('sensor_noise_snr_db', 52.0)
        v_noisy = add_sensor_noise(v_raw, target_snr_db=snr_target, seed=42 + (pilot_id or 0))

        # Extract authoritative 32 features
        feats_dict = extract_enhanced_features(v_noisy[:, 0], sample_rate=5000.0, f0=60.0)

        # Per-phase half cycle RMS profiles
        rms_traces = []
        for ch in range(3):
            rms_tr, t_tr = compute_half_cycle_rms(v_noisy[:, ch], fs=5000.0, f0=60.0)
            rms_traces.append(rms_tr)
        rms_traces = np.array(rms_traces) # (3, n_steps)

        # Pre, Event, Post RMS
        pre_rms = float(np.mean(rms_traces[:, :20])) # First 20 half-cycle windows (~33 ms)
        mid_rms = float(np.mean(rms_traces[:, 40:80])) # Middle windows
        post_rms = float(np.mean(rms_traces[:, -20:])) # Last 20 windows

        # Execute physical validation
        val_result = {}
        try:
            if cls_name == 'Normal':
                val_result = validate_normal_physical(v_noisy, feats_dict)
            elif cls_name == 'Sag':
                val_result = validate_sag_frame(v_noisy, feats_dict)
            elif cls_name == 'Swell':
                val_result = validate_swell_frame(v_noisy, feats_dict)
            elif cls_name == 'Interruption':
                val_result = validate_interruption_frame(v_noisy, feats_dict)
            elif cls_name == 'Harmonics':
                val_result = validate_harmonics_frame(v_noisy, feats_dict)
            elif cls_name == 'Flicker':
                val_result = validate_flicker_frame(v_noisy, feats_dict)
            elif cls_name == 'Notch':
                val_result = validate_notch_frame(v_noisy, feats_dict)
            elif cls_name == 'Transient':
                val_result = validate_transient_frame(v_noisy, feats_dict)
            else:
                val_result = {'passed': False, 'status': 'UNKNOWN_CLASS'}
        except Exception as e:
            val_result = {'passed': False, 'status': f'ERROR: {str(e)}'}

        is_passed = bool(val_result.get('physical_validation_passed', val_result.get('passed', False)))
        status_str = 'PASS' if is_passed else 'FAIL'
        print(f" -> Physical Validation: {status_str} | RMS pre={pre_rms:.3f}, mid={mid_rms:.3f}, post={post_rms:.3f} | THD={feats_dict.get('thd', 0):.2f}%")

        # Save processed NPZ frame
        npz_name = f"{scen_id}.npz"
        npz_path = os.path.join(PROCESSED_DIR, npz_name)
        np.savez_compressed(
            npz_path,
            vabc=v_noisy,
            vabc_raw=v_raw,
            iabc=i_raw,
            scenario_id=scen_id,
            pilot_id=pilot_id,
            class_name=cls_name,
            label_idx=meta.get('label_idx'),
            operating_condition_id=meta.get('operating_condition_id'),
            split=meta.get('split'),
            fs=5000.0,
            f0=60.0,
            pre_event_rms=pre_rms,
            event_mid_rms=mid_rms,
            post_event_rms=post_rms,
            thd=float(feats_dict.get('thd', 0.0)),
            system_freq=float(feats_dict.get('system_freq', 60.0)),
            crest_factor=float(feats_dict.get('crest_factor', 1.414)),
            validation_passed=is_passed,
            validation_status=val_result.get('status', 'N/A')
        )

        # Checksums
        raw_sha = compute_sha256(fpath)
        proc_sha = compute_sha256(npz_path)
        checksum_lines.append(f"{raw_sha}  raw/{fname}")
        checksum_lines.append(f"{proc_sha}  processed/{npz_name}")

        record = {
            "scenario_id": scen_id,
            "pilot_id": pilot_id,
            "class": cls_name,
            "label_idx": meta.get('label_idx'),
            "phase": meta.get('phase'),
            "severity": meta.get('severity'),
            "split": meta.get('split'),
            "operating_condition_id": meta.get('operating_condition_id'),
            "operating_condition_name": meta.get('operating_condition_name'),
            "operating_condition_family": meta.get('operating_condition_family'),
            "simulation_wall_time_s": t_wall,
            "samples": 1000,
            "duration_ms": 200.0,
            "fs_hz": 5000.0,
            "snr_db": snr_target,
            "pre_event_rms_pu": pre_rms,
            "event_mid_rms_pu": mid_rms,
            "post_event_rms_pu": post_rms,
            "thd_pct": float(feats_dict.get('thd', 0.0)),
            "frequency_hz": float(feats_dict.get('system_freq', 60.0)),
            "physical_validation_passed": is_passed,
            "physical_validation_status": val_result.get('status', 'PASS' if is_passed else 'FAIL'),
            "raw_sha256": raw_sha,
            "processed_sha256": proc_sha
        }
        manifest_records.append(record)

    # Save Manifest
    pilot_manifest = {
        "manifest_version": "1.0",
        "phase": "Phase 5B Bounded Pilot Generation & Validation",
        "timestamp": "2026-10-11T23:52:00Z",
        "repository": "https://github.com/nadarallen/power-quality-detector-and-classifier",
        "source_reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
        "working_disturbance_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx",
        "total_pilot_trajectories": len(manifest_records),
        "classes_represented": len(set(r['class'] for r in manifest_records)),
        "class_counts": {c: sum(1 for r in manifest_records if r['class'] == c) for c in sorted(list(set(r['class'] for r in manifest_records)))},
        "split_counts": {s: sum(1 for r in manifest_records if r['split'] == s) for s in ['train', 'val', 'challenge']},
        "all_passed": all(r['physical_validation_passed'] for r in manifest_records),
        "records": manifest_records
    }

    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(pilot_manifest, f, indent=2)
    print(f"\n[Success] Saved Pilot Manifest to {MANIFEST_PATH}")

    # Save Checksums file
    with open(CHECKSUMS_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(checksum_lines) + "\n")
    print(f"[Success] Saved SHA-256 Checksums to {CHECKSUMS_PATH}")
    print("\nPhysical validation and artifact processing complete!")


if __name__ == '__main__':
    run_validation()

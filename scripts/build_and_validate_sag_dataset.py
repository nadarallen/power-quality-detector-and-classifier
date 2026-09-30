"""
scripts/build_and_validate_sag_dataset.py
-----------------------------------------
Authoritative pipeline to build, extract, independently validate, and partition
the IEEE 9-bus 60-Hz Voltage Sag dataset (Gate 3E).

Target:
- 1,152 unique Sag frames across 36 continuous simulation scenarios
- 32 diverse grid operating conditions
- Multiple fault types: 3-phase symmetrical, single-phase-to-ground, phase-to-phase
- 100% independent physical validation (GATE3C_VALIDATION_PLAN.md §3.2)
- Zero cross-split simulation trajectory leakage (group-partitioned by simulation_id)
- Decoupled from ML inference (ground_truth = "Sag", label_idx = 5)
- Full feature distribution audit vs. 1,120 Normal baseline frames
"""

import os
import sys
import json
import hashlib
import numpy as np
import pandas as pd
import scipy.io

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity
from pipeline.disturbance_validator import validate_sag_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, MLPClassifier

SAG_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag')
NORMAL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
WEIGHTS_PATH = os.path.join(PROJECT_ROOT, 'ml', 'models', 'model_weights_32.json')


def extract_scalar(item):
    """Recursively unwraps MATLAB struct array nesting to a Python primitive."""
    while isinstance(item, (np.ndarray, list)):
        if len(item) == 0:
            return None
        item = item[0]
    return item


def add_sensor_noise(vabc: np.ndarray, target_snr_db: float = 52.0, seed: int = 42) -> np.ndarray:
    """Adds sensor noise at target SNR level per DAQ model."""
    rng = np.random.RandomState(seed)
    noisy_vabc = np.zeros_like(vabc)
    for ch in range(3):
        sig = vabc[:, ch]
        p_sig = np.mean(sig**2)
        p_noise = p_sig / (10.0 ** (target_snr_db / 10.0))
        noise = rng.normal(0.0, np.sqrt(p_noise), size=sig.shape)
        noisy_vabc[:, ch] = sig + noise
    return noisy_vabc


def build_and_validate_sag_dataset():
    print("=" * 70)
    print("GATE 3E — VOLTAGE SAG DATASET GENERATION & VALIDATION")
    print("=" * 70)

    # 1. Assert Pristine Model Integrity
    verify_pristine_model_integrity()
    print("[Step 1] Pristine reference model integrity verified (SHA256 untouched).")

    # 2. Load Raw Simulation Trajectories
    mat_path = os.path.join(SAG_DIR, 'raw_sag_simulations.mat')
    if not os.path.exists(mat_path):
        raise FileNotFoundError(f"Raw simulation MAT file not found at {mat_path}")

    print(f"[Step 2] Loading raw simulations: {mat_path}...")
    mat = scipy.io.loadmat(mat_path)
    sim_records = mat['sim_records']
    num_sims = sim_records.shape[0] # 36
    windows_per_sim = 32
    target_total_frames = num_sims * windows_per_sim # 1,152

    print(f" -> Loaded {num_sims} simulation trajectories.")
    print(f" -> Target extraction: {num_sims} sims x {windows_per_sim} windows = {target_total_frames} frames.")

    # Load operating conditions metadata
    cond_path = os.path.join(NORMAL_DIR, 'operating_conditions.json')
    with open(cond_path, 'r', encoding='utf-8') as f:
        cond_list = json.load(f)
    cond_map = {c['id']: c for c in cond_list}

    # 3. Partition Assignment (Leakage Prevention)
    # 36 simulation groups:
    # Test groups: diverse coverage across 3P, 1P, 2P (sim 02, 06, 11, 21, 30) = 5 groups (160 frames, 13.9%)
    # Val groups: diverse coverage (sim 03, 09, 14, 22, 28) = 5 groups (160 frames, 13.9%)
    # Train groups: remaining 26 groups (832 frames, 72.2%)
    test_sim_ids = {'sag_sim_02', 'sag_sim_06', 'sag_sim_11', 'sag_sim_21', 'sag_sim_30'}
    val_sim_ids  = {'sag_sim_03', 'sag_sim_09', 'sag_sim_14', 'sag_sim_22', 'sag_sim_28'}

    # 4. Scenario Metadata Generation conforming to GATE3C_SCENARIO_SCHEMA
    scenario_catalog = []
    for s_idx in range(num_sims):
        rec = sim_records[s_idx]
        scen_id = str(extract_scalar(rec['scenario_id']))
        sim_id = str(extract_scalar(rec['sim_id']))
        cond_id = int(extract_scalar(rec['cond_id']))
        phase_str = str(extract_scalar(rec['phase']))
        rf = float(extract_scalar(rec['rf']))
        rg = float(extract_scalar(rec['rg']))
        dur_cycles = float(extract_scalar(rec['duration_cycles']))
        dur_ms = float(extract_scalar(rec['duration_ms']))

        split = 'train'
        if sim_id in test_sim_ids:
            split = 'test'
        elif sim_id in val_sim_ids:
            split = 'val'

        scen_dict = {
            "schema_version": "1.0",
            "scenario_id": scen_id,
            "class": "Sag",
            "label_idx": 5,
            "label_source": "SCENARIO_CONTROLLER",
            "electrical_model": {
                "reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
                "working_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx",
                "model_unchanged": True
            },
            "injection_location": {
                "bus": "Bus4",
                "measurement_point": "Vabc_5",
                "mechanism": "FAULT_IMPEDANCE",
                "phase": phase_str
            },
            "nominal_frequency_hz": 60.0,
            "sampling_rate_hz": 5000.0,
            "window_samples": 1000,
            "window_ms": 200.0,
            "seed": 42 + s_idx,
            "operating_condition_id": cond_id,
            "simulation_id": sim_id,
            "parameters": {
                "fault_resistance_ohms": rf,
                "ground_resistance_ohms": rg,
                "duration_cycles": dur_cycles,
                "duration_ms": dur_ms,
                "onset_range_ms": [20.0, 51.0],
                "transition_type": "POINT_ON_WAVE",
                "sensor_noise_snr_db": 52.0
            },
            "parameter_provenance": {
                "magnitude_pu": "STANDARD-SUPPORTED",
                "duration_cycles": "STANDARD-SUPPORTED",
                "duration_ms": "PROJECT-DESIGN-CHOICE",
                "onset_range_ms": "PROJECT-DESIGN-CHOICE",
                "transition_type": "ENGINEERING-INTERPRETATION",
                "fault_resistance_ohms": "SIMULATION-PARAMETER",
                "ground_resistance_ohms": "SIMULATION-PARAMETER",
                "sensor_noise_snr_db": "SIMULATION-PARAMETER"
            },
            "standard_references": [
                {
                    "standard": "IEEE Std 1159-2019",
                    "clause": "Table 2 / Clause 3.1.58",
                    "applies_to": "Sag magnitude [0.10, 0.90] pu, duration 0.5 cycle to 1 min"
                },
                {
                    "standard": "IEC 61000-4-30:2015",
                    "clause": "Clause 5.2",
                    "applies_to": "Half-cycle RMS U_rms(1/2) aggregation"
                }
            ],
            "dataset_partition": {
                "group_id": sim_id,
                "split": split
            }
        }
        scenario_catalog.append(scen_dict)

    # Save scenarios JSON
    scenarios_json_path = os.path.join(SAG_DIR, 'sag_scenarios.json')
    with open(scenarios_json_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_catalog, f, indent=2)
    print(f"[Step 3] Scenario catalog generated and saved ({len(scenario_catalog)} scenarios).")

    # 5. Extract, Process, Validate, and Collect Frames
    print("\n[Step 4] Slicing, Extracting 32 Features, and Physically Validating Frames...")

    all_waveforms = np.zeros((target_total_frames, 1000, 3), dtype=np.float32)
    all_currents  = np.zeros((target_total_frames, 1000, 3), dtype=np.float32)
    feature_rows = []
    validation_records = []
    rejected_records = []

    frame_counter = 0
    t_fault_nominal = 0.12 # fault inception in simulation

    for s_idx in range(num_sims):
        rec = sim_records[s_idx]
        scen_id = str(extract_scalar(rec['scenario_id']))
        sim_id = str(extract_scalar(rec['sim_id']))
        cond_id = int(extract_scalar(rec['cond_id']))
        dur_ms = float(extract_scalar(rec['duration_ms']))
        ph_str = str(extract_scalar(rec['phase']))

        split = 'train'
        if sim_id in test_sim_ids:
            split = 'test'
        elif sim_id in val_sim_ids:
            split = 'val'

        tres = rec['t_resampled'][0].flatten()
        vres = rec['Vabc_resampled'][0]
        ires = rec['Iabc_resampled'][0]

        # Add calibrated sensor noise (52 dB SNR)
        vres_noisy = add_sensor_noise(vres, target_snr_db=52.0, seed=42 + s_idx)
        ires_noisy = add_sensor_noise(ires, target_snr_db=52.0, seed=142 + s_idx)

        # Slice 32 windows: onset varies from 20.0 ms to 51.0 ms by 1.0 ms (5 samples)
        for w_idx in range(windows_per_sim):
            onset_ms = 20.0 + (w_idx * 1.0) # ms into 200 ms frame
            onset_s = onset_ms / 1000.0
            t_win_start = t_fault_nominal - onset_s
            t_win_end = t_win_start + 0.200

            # Find nearest 1000 samples
            idx_start = int(round(t_win_start * 5000.0))
            idx_end = idx_start + 1000

            v_win = vres_noisy[idx_start:idx_end, :].astype(np.float32)
            i_win = ires_noisy[idx_start:idx_end, :].astype(np.float32)

            frame_id = f"sag_{s_idx+1:02d}_{w_idx+1:02d}"

            # 5a. Feature Extraction (Authoritative Production Contract)
            feats_a = extract_enhanced_features(v_win[:, 0], sample_rate=5000.0, f0=60.0)

            # 5b. Independent Physical Validation
            # Look up authoritative steady-state baseline RMS for this operating condition
            cond_baseline_rms = float(cond_map.get(cond_id, {}).get('bus5_v_rms_pu', 0.5887))
            if cond_baseline_rms < 0.50 or cond_baseline_rms > 0.70:
                cond_baseline_rms = 0.5887

            val_res = validate_sag_frame(v_win, feats_a, nominal_baseline_rms=cond_baseline_rms)

            if not val_res['physical_validation_passed']:
                rejected_records.append({
                    'frame_id': frame_id,
                    'sim_id': sim_id,
                    'scenario_id': scen_id,
                    'reason': [k for k, v in val_res['gates'].items() if not v],
                    'metrics': val_res
                })
                continue # Reject frame

            # Accepted Frame
            all_waveforms[frame_counter] = v_win
            all_currents[frame_counter]  = i_win

            # Compile feature dictionary row
            row = {
                'frame_id': frame_id,
                'simulation_id': sim_id,
                'scenario_id': scen_id,
                'operating_condition_id': cond_id,
                'split': split,
                'class': 'Sag',
                'label_idx': 5,
                'label_source': 'SCENARIO_CONTROLLER',
                'phase_config': val_res['phase_configuration'],
                'affected_phases': ','.join(val_res['affected_phases']),
                'residual_voltage_pu': val_res['residual_voltage_pu'],
                'duration_ms': val_res['duration_ms'],
                'start_time_s': val_res['start_time_s'],
                'end_time_s': val_res['end_time_s'],
                'event_start_idx': int(round(val_res['start_time_s'] * 5000.0)) if val_res['start_time_s'] else 0,
                'event_end_idx': int(round(val_res['end_time_s'] * 5000.0)) if val_res['end_time_s'] else 0,
            }
            # Append all 32 model features
            for fn in _MODEL_FEATURE_ORDER:
                row[fn] = float(feats_a[fn])

            feature_rows.append(row)
            validation_records.append(val_res)
            frame_counter += 1

    accepted_count = frame_counter
    print(f"\n -> Total candidate windows: {target_total_frames}")
    print(f" -> Accepted Sag frames:     {accepted_count} (100% physically validated)")
    print(f" -> Rejected Sag frames:     {len(rejected_records)}")

    # Trim arrays to actual accepted count
    all_waveforms = all_waveforms[:accepted_count]
    all_currents = all_currents[:accepted_count]
    df_features = pd.DataFrame(feature_rows)

    # 6. Quality Control Checks
    print("\n[Step 5] Quality Control Audits...")
    # Check 1: Zero exact duplicates via MD5 byte hash
    frame_hashes = [hashlib.md5(all_waveforms[i].tobytes()).hexdigest() for i in range(accepted_count)]
    unique_hashes = len(set(frame_hashes))
    print(f" -> Duplicate check: {unique_hashes} unique waveforms out of {accepted_count} (Zero duplicates).")
    assert unique_hashes == accepted_count, f"Found duplicate waveform frames: {accepted_count - unique_hashes}"

    # Check 2: No NaN or Inf
    assert not np.any(np.isnan(all_waveforms)), "Found NaN in waveforms!"
    assert not np.any(np.isinf(all_waveforms)), "Found Inf in waveforms!"
    for col in _MODEL_FEATURE_ORDER:
        assert not df_features[col].isnull().any(), f"NaN in feature {col}"
        assert not np.isinf(df_features[col]).any(), f"Inf in feature {col}"
    print(" -> Numerical validity: Zero NaN, Zero Inf across all waveforms and features.")

    # Check 3: Zero cross-split simulation trajectory leakage
    train_sims = set(df_features[df_features['split'] == 'train']['simulation_id'].unique())
    val_sims   = set(df_features[df_features['split'] == 'val']['simulation_id'].unique())
    test_sims  = set(df_features[df_features['split'] == 'test']['simulation_id'].unique())

    leakage_train_val = train_sims.intersection(val_sims)
    leakage_train_test = train_sims.intersection(test_sims)
    leakage_val_test = val_sims.intersection(test_sims)

    assert len(leakage_train_val) == 0, f"Leakage Train/Val: {leakage_train_val}"
    assert len(leakage_train_test) == 0, f"Leakage Train/Test: {leakage_train_test}"
    assert len(leakage_val_test) == 0, f"Leakage Val/Test: {leakage_val_test}"
    print(f" -> Leakage Prevention: Verified! Train: {len(train_sims)} sims, Val: {len(val_sims)} sims, Test: {len(test_sims)} sims. Zero overlap.")

    # 7. Comparison with Normal Dataset (Feature Distribution Audit)
    print("\n[Step 6] Comparing Feature Distributions: Normal Baseline vs Voltage Sag...")
    normal_csv_path = os.path.join(NORMAL_DIR, 'normal_features.csv')
    df_normal = pd.read_csv(normal_csv_path)

    comparison_metrics = {}
    audit_features = ['rms_voltage', 'peak_voltage', 'crest_factor', 'thd', 'duration', 'dominant_freq', 'system_freq', 'snr']

    print(f"{'Feature':<18s} | {'Normal Mean ± Std':<22s} | {'Sag Mean ± Std':<22s} | {'Separation / Overlap':<22s}")
    print("-" * 90)

    for feat in audit_features:
        norm_vals = df_normal[feat]
        sag_vals = df_features[feat]

        norm_mean, norm_std = float(norm_vals.mean()), float(norm_vals.std())
        sag_mean, sag_std   = float(sag_vals.mean()), float(sag_vals.std())

        norm_range = (float(norm_vals.min()), float(norm_vals.max()))
        sag_range  = (float(sag_vals.min()), float(sag_vals.max()))

        # Calculate range overlap
        overlap_min = max(norm_range[0], sag_range[0])
        overlap_max = min(norm_range[1], sag_range[1])
        has_overlap = bool(overlap_max >= overlap_min)

        comparison_metrics[feat] = {
            'normal_mean': norm_mean,
            'normal_std': norm_std,
            'normal_range': norm_range,
            'sag_mean': sag_mean,
            'sag_std': sag_std,
            'sag_range': sag_range,
            'has_overlap': has_overlap
        }

        norm_str = f"{norm_mean:.4f} ± {norm_std:.4f}"
        sag_str  = f"{sag_mean:.4f} ± {sag_std:.4f}"
        status_str = "Overlapped" if has_overlap else "Fully Separated"
        print(f"{feat:<18s} | {norm_str:<22s} | {sag_str:<22s} | {status_str:<22s}")

    # 8. Export Authoritative Datasets
    print("\n[Step 7] Exporting Datasets and Computing Checksums...")

    # 8a. Waveforms NPZ
    npz_path = os.path.join(SAG_DIR, 'sag_waveforms.npz')
    np.savez_compressed(
        npz_path,
        waveforms=all_waveforms,
        currents=all_currents,
        frame_ids=df_features['frame_id'].values,
        simulation_ids=df_features['simulation_id'].values,
        operating_condition_ids=df_features['operating_condition_id'].values,
        scenario_ids=df_features['scenario_id'].values,
        splits=df_features['split'].values,
        ground_truth=df_features['class'].values,
        label_idx=df_features['label_idx'].values
    )
    sha_npz = compute_sha256(npz_path)
    print(f" -> Saved: {npz_path} (SHA256: {sha_npz})")

    # 8b. Features CSV
    csv_path = os.path.join(SAG_DIR, 'sag_features.csv')
    df_features.to_csv(csv_path, index=False)
    sha_csv = compute_sha256(csv_path)
    print(f" -> Saved: {csv_path} (SHA256: {sha_csv})")

    # 8c. Metadata JSON
    metadata = {
        'dataset_name': 'IEEE 9-Bus 60-Hz Voltage Sag Dataset',
        'gate': 'GATE 3E',
        'creation_date': '2026-09-30',
        'electrical_system': {
            'benchmark': 'IEEE 9-bus WSCC 3-machine system',
            'nominal_frequency_hz': 60.0,
            'measurement_bus': 'Bus 5',
            'base_voltage_kv': 230.0,
            'sampling_rate_hz': 5000.0,
            'window_samples': 1000,
            'window_duration_ms': 200.0,
            'cycles_per_window': 12.0
        },
        'counts': {
            'total_simulations': num_sims,
            'windows_per_simulation': windows_per_sim,
            'total_accepted_frames': accepted_count,
            'total_rejected_frames': len(rejected_records),
            'train_frames': int((df_features['split'] == 'train').sum()),
            'val_frames': int((df_features['split'] == 'val').sum()),
            'test_frames': int((df_features['split'] == 'test').sum())
        },
        'phase_coverage': {
            'three_phase': int((df_features['phase_config'] == 'three-phase').sum()),
            'single_phase_to_ground': int((df_features['phase_config'] == 'phase-to-ground').sum()),
            'phase_to_phase': int((df_features['phase_config'] == 'phase-to-phase').sum())
        },
        'operating_condition_coverage': {
            'unique_operating_conditions': int(df_features['operating_condition_id'].nunique()),
            'condition_ids': sorted([int(x) for x in df_features['operating_condition_id'].unique()])
        },
        'parameter_distributions': {
            'residual_voltage_pu': {
                'min': float(df_features['residual_voltage_pu'].min()),
                'max': float(df_features['residual_voltage_pu'].max()),
                'mean': float(df_features['residual_voltage_pu'].mean()),
                'median': float(df_features['residual_voltage_pu'].median())
            },
            'duration_ms': {
                'min': float(df_features['duration_ms'].min()),
                'max': float(df_features['duration_ms'].max()),
                'mean': float(df_features['duration_ms'].mean()),
                'median': float(df_features['duration_ms'].median())
            }
        },
        'feature_comparison_vs_normal': comparison_metrics,
        'pristine_reference_model': {
            'path': 'IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx',
            'sha256': compute_sha256(os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')),
            'status': 'UNTOUCHED'
        },
        'checksums': {
            'sag_waveforms_npz': sha_npz,
            'sag_features_csv': sha_csv,
            'sag_scenarios_json': compute_sha256(scenarios_json_path)
        }
    }

    meta_json_path = os.path.join(SAG_DIR, 'sag_dataset_metadata.json')
    with open(meta_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f" -> Saved: {meta_json_path}")

    # Re-verify pristine model integrity
    verify_pristine_model_integrity()
    print("[Step 8] Pristine model re-verified untouched after full generation.")

    print("\n" + "=" * 70)
    print(f"GATE3E_SAG_DATASET = PASS")
    print(f"Accepted Frames: {accepted_count} | Rejected: {len(rejected_records)}")
    print("=" * 70)

    return True


def mean_square_pre(signal: np.ndarray, onset_samples: int) -> float:
    """Computes mean square of pre-event region."""
    if onset_samples <= 10:
        return float(np.mean(signal**2))
    return float(np.mean(signal[:onset_samples]**2))


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


if __name__ == '__main__':
    success = build_and_validate_sag_dataset()
    sys.exit(0 if success else 1)

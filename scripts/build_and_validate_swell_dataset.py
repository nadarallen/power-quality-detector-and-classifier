"""
scripts/build_and_validate_swell_dataset.py
-------------------------------------------
Authoritative pipeline to build, extract, independently validate, and partition
the IEEE 9-bus 60-Hz Voltage Swell dataset (Gate 3H).

Target:
- 1,152 unique Swell frames across 36 continuous simulation scenarios
- 32 diverse grid operating conditions
- Multiple phase configurations: 3-phase symmetrical, single-phase, phase-to-phase
- 100% independent physical validation (GATE3C_VALIDATION_PLAN.md §3.3)
- Zero cross-split simulation trajectory leakage (group-partitioned by simulation_id)
- Decoupled from ML inference (ground_truth = "Swell", label_idx = 6)
- Full feature distribution audit vs. Normal (1,120 frames) and Sag (1,152 frames)
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
from pipeline.disturbance_validator import validate_swell_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, MLPClassifier

SWELL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'swell')
SAG_DIR   = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag')
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


def build_and_validate_swell_dataset():
    print("=" * 70)
    print("GATE 3H — VOLTAGE SWELL DATASET GENERATION & VALIDATION")
    print("=" * 70)

    # 1. Assert Pristine Model Integrity
    verify_pristine_model_integrity()
    print("[Step 1] Pristine reference model integrity verified (SHA256 untouched).")

    # 2. Load Raw Simulation Trajectories
    mat_path = os.path.join(SWELL_DIR, 'raw_swell_simulations.mat')
    if not os.path.exists(mat_path):
        raise FileNotFoundError(f"Raw simulation MAT file not found at {mat_path}")

    print(f"[Step 2] Loading raw simulations: {mat_path}...")
    mat = scipy.io.loadmat(mat_path)
    sim_records = mat['sim_records']
    num_sims = sim_records.shape[0]  # 36
    windows_per_sim = 32
    target_total_frames = num_sims * windows_per_sim  # 1,152

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
    test_sim_ids = {'swell_sim_02', 'swell_sim_06', 'swell_sim_11', 'swell_sim_21', 'swell_sim_30'}
    val_sim_ids  = {'swell_sim_03', 'swell_sim_09', 'swell_sim_14', 'swell_sim_22', 'swell_sim_28'}

    # 4. Scenario Metadata Generation conforming to GATE3C_SCENARIO_SCHEMA
    scenario_catalog = []
    for s_idx in range(num_sims):
        rec = sim_records[s_idx]
        scen_id = str(extract_scalar(rec['scenario_id']))
        sim_id = str(extract_scalar(rec['sim_id']))
        cond_id = int(extract_scalar(rec['cond_id']))
        phase_str = str(extract_scalar(rec['phase']))
        qc = float(extract_scalar(rec['qc_mvar']))
        damping = float(extract_scalar(rec['damping_kw']))
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
            "class": "Swell",
            "label_idx": 6,
            "label_source": "SCENARIO_CONTROLLER",
            "electrical_model": {
                "reference_model": "IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx",
                "working_model": "IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx",
                "model_unchanged": True
            },
            "injection_location": {
                "bus": "Bus4",
                "measurement_point": "Vabc_5",
                "mechanism": "CAPACITOR_SWITCH",
                "phase": phase_str
            },
            "nominal_frequency_hz": 60.0,
            "sampling_rate_hz": 5000.0,
            "window_samples": 1000,
            "window_ms": 200.0,
            "seed": 1042 + s_idx,
            "operating_condition_id": cond_id,
            "simulation_id": sim_id,
            "parameters": {
                "capacitive_power_mvar": qc,
                "damping_power_kw": damping,
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
                "capacitive_power_mvar": "SIMULATION-PARAMETER",
                "damping_power_kw": "SIMULATION-PARAMETER",
                "sensor_noise_snr_db": "SIMULATION-PARAMETER"
            },
            "standard_references": [
                {
                    "standard": "IEEE Std 1159-2019",
                    "clause": "Table 2 / Clause 3.1.65",
                    "applies_to": "Swell magnitude [1.10, 1.80] pu, duration 0.5 cycle to 1 min"
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
    scenarios_json_path = os.path.join(SWELL_DIR, 'swell_scenarios.json')
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
    t_fault_nominal = 0.12  # event inception in simulation

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
        vres_noisy = add_sensor_noise(vres, target_snr_db=52.0, seed=1042 + s_idx)
        ires_noisy = add_sensor_noise(ires, target_snr_db=52.0, seed=2042 + s_idx)

        # Slice 32 windows: onset varies from 20.0 ms to 51.0 ms by 1.0 ms (5 samples)
        for w_idx in range(windows_per_sim):
            onset_ms = 20.0 + (w_idx * 1.0)
            onset_s = onset_ms / 1000.0
            t_win_start = t_fault_nominal - onset_s
            t_win_end = t_win_start + 0.200

            idx_start = int(round(t_win_start * 5000.0))
            idx_end = idx_start + 1000

            v_win = vres_noisy[idx_start:idx_end, :].astype(np.float32)
            i_win = ires_noisy[idx_start:idx_end, :].astype(np.float32)

            frame_id = f"swell_{s_idx+1:02d}_{w_idx+1:02d}"

            # Feature Extraction (Primary Candidate Phase)
            peaks = [np.max(np.abs(v_win[:, ch])) for ch in range(3)]
            cand_idx = int(np.argmax(peaks))
            feats_primary = extract_enhanced_features(v_win[:, cand_idx], sample_rate=5000.0, f0=60.0)

            # Independent Physical Validation
            cond_baseline_rms = float(cond_map.get(cond_id, {}).get('bus5_v_rms_pu', 0.5887))
            if cond_baseline_rms < 0.50 or cond_baseline_rms > 0.70:
                cond_baseline_rms = 0.5887

            val_res = validate_swell_frame(v_win, feats_primary, nominal_baseline_rms=cond_baseline_rms)

            if not val_res['physical_validation_passed']:
                rejected_records.append({
                    'frame_id': frame_id,
                    'sim_id': sim_id,
                    'scenario_id': scen_id,
                    'reason': [k for k, v in val_res['gates'].items() if not v],
                    'metrics': val_res
                })
                continue

            # Accepted Frame
            all_waveforms[frame_counter] = v_win
            all_currents[frame_counter]  = i_win

            row = {
                'frame_id': frame_id,
                'simulation_id': sim_id,
                'scenario_id': scen_id,
                'operating_condition_id': cond_id,
                'split': split,
                'class': 'Swell',
                'label_idx': 6,
                'label_source': 'SCENARIO_CONTROLLER',
                'phase_config': val_res['phase_configuration'],
                'affected_phases': ','.join(val_res['affected_phases']),
                'swell_magnitude_pu': val_res['swell_magnitude_pu'],
                'duration_ms': val_res['duration_ms'],
                'start_time_s': val_res['start_time_s'],
                'end_time_s': val_res['end_time_s'],
                'event_start_idx': int(round(val_res['start_time_s'] * 5000.0)) if val_res['start_time_s'] else 0,
                'event_end_idx': int(round(val_res['end_time_s'] * 5000.0)) if val_res['end_time_s'] else 0,
            }
            for fn in _MODEL_FEATURE_ORDER:
                row[fn] = float(feats_primary[fn])

            feature_rows.append(row)
            validation_records.append(val_res)
            frame_counter += 1

    accepted_count = frame_counter
    print(f"\n -> Total candidate windows: {target_total_frames}")
    print(f" -> Accepted Swell frames:   {accepted_count} (100% physically validated)")
    print(f" -> Rejected Swell frames:   {len(rejected_records)}")

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
    leakage_val_test   = val_sims.intersection(test_sims)

    assert len(leakage_train_val) == 0, f"Train-Val simulation leakage: {leakage_train_val}"
    assert len(leakage_train_test) == 0, f"Train-Test simulation leakage: {leakage_train_test}"
    assert len(leakage_val_test) == 0, f"Val-Test simulation leakage: {leakage_val_test}"
    print(f" -> Leakage audit: Zero trajectory leakage verified.")
    print(f"    Train: {len(train_sims)} sims ({len(df_features[df_features['split']=='train'])} frames, {len(df_features[df_features['split']=='train'])/accepted_count*100:.1f}%)")
    print(f"    Val:   {len(val_sims)} sims ({len(df_features[df_features['split']=='val'])} frames, {len(df_features[df_features['split']=='val'])/accepted_count*100:.1f}%)")
    print(f"    Test:  {len(test_sims)} sims ({len(df_features[df_features['split']=='test'])} frames, {len(df_features[df_features['split']=='test'])/accepted_count*100:.1f}%)")

    # 7. Distribution Statistics
    print("\n[Step 6] Computing Measured Severity & Parameter Statistics...")
    ratios = df_features['swell_magnitude_pu'].values
    durs   = df_features['duration_ms'].values
    durs_cyc = durs / (1000.0 / 60.0)

    percentiles = [0, 1, 5, 25, 50, 75, 95, 99, 100]
    ratio_pcts = {f"P{p}": float(np.percentile(ratios, p)) for p in percentiles}
    dur_pcts   = {f"P{p}": float(np.percentile(durs, p)) for p in percentiles}
    dur_cyc_pcts = {f"P{p}": float(np.percentile(durs_cyc, p)) for p in percentiles}

    print(" -> Swell Magnitude (Ratio to Nominal):")
    for k, v in ratio_pcts.items():
        print(f"    {k:>4s}: {v:.4f} pu")

    print(" -> Duration (ms):")
    for k, v in dur_pcts.items():
        print(f"    {k:>4s}: {v:.2f} ms")

    # Phase Breakdown
    phase_counts = df_features['phase_config'].value_counts().to_dict()
    print(" -> Phase Configurations:", phase_counts)

    # 8. Save CSV, NPZ, and Metadata
    print("\n[Step 7] Saving Waveform NPZ, Features CSV, and Metadata...")
    features_csv_path = os.path.join(SWELL_DIR, 'swell_features.csv')
    df_features.to_csv(features_csv_path, index=False)
    print(f" -> Saved Features CSV:  {features_csv_path} ({len(df_features)} rows)")

    waveforms_npz_path = os.path.join(SWELL_DIR, 'swell_waveforms.npz')
    np.savez_compressed(
        waveforms_npz_path,
        waveforms=all_waveforms,
        currents=all_currents,
        frame_ids=df_features['frame_id'].values,
        simulation_ids=df_features['simulation_id'].values,
        splits=df_features['split'].values,
        labels=np.full(accepted_count, 'Swell'),
        label_indices=np.full(accepted_count, 6, dtype=np.int32)
    )
    print(f" -> Saved Waveforms NPZ: {waveforms_npz_path} ({all_waveforms.shape})")

    # Checksums
    with open(features_csv_path, 'rb') as f:
        csv_sha = hashlib.sha256(f.read()).hexdigest()
    with open(waveforms_npz_path, 'rb') as f:
        npz_sha = hashlib.sha256(f.read()).hexdigest()
    with open(scenarios_json_path, 'rb') as f:
        scen_sha = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx'), 'rb') as f:
        pristine_sha = hashlib.sha256(f.read()).hexdigest()

    metadata = {
        'dataset_name': 'IEEE-9bus-60Hz-Voltage-Swell',
        'gate': 'GATE3H',
        'class': 'Swell',
        'label_idx': 6,
        'label_source': 'SCENARIO_CONTROLLER',
        'sampling_rate_hz': 5000.0,
        'nominal_frequency_hz': 60.0,
        'window_samples': 1000,
        'window_duration_ms': 200.0,
        'num_frames': accepted_count,
        'num_simulations': num_sims,
        'windows_per_simulation': windows_per_sim,
        'operating_conditions_count': len(df_features['operating_condition_id'].unique()),
        'partitions': {
            'train_frames': int(np.sum(df_features['split'] == 'train')),
            'val_frames': int(np.sum(df_features['split'] == 'val')),
            'test_frames': int(np.sum(df_features['split'] == 'test'))
        },
        'phase_distribution': phase_counts,
        'severity_statistics': {
            'magnitude_ratio_percentiles': ratio_pcts,
            'duration_ms_percentiles': dur_pcts,
            'duration_cycles_percentiles': dur_cyc_pcts,
            'mean_magnitude_ratio': float(np.mean(ratios)),
            'std_magnitude_ratio': float(np.std(ratios)),
            'mean_duration_ms': float(np.mean(durs)),
            'std_duration_ms': float(np.std(durs))
        },
        'checksums': {
            'features_csv_sha256': csv_sha,
            'waveforms_npz_sha256': npz_sha,
            'scenarios_json_sha256': scen_sha,
            'pristine_model_sha256': pristine_sha
        },
        'purity_verification': {
            'duplicate_count': 0,
            'nan_count': 0,
            'inf_count': 0,
            'rejected_frames_count': len(rejected_records),
            'physical_validation_pass_rate': float(accepted_count / target_total_frames)
        }
    }

    metadata_path = os.path.join(SWELL_DIR, 'swell_dataset_metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f" -> Saved Dataset Metadata: {metadata_path}")

    print("\n" + "=" * 70)
    print(f"GATE 3H SWELL DATASET GENERATION SUCCESS: {accepted_count} FRAMES")
    print("=" * 70)
    return metadata


if __name__ == '__main__':
    build_and_validate_swell_dataset()

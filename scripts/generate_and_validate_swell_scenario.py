"""
scripts/generate_and_validate_swell_scenario.py
-----------------------------------------------
Generates, processes, validates, and records the first deterministic Voltage Swell
scenario for Gate 3G / Gate 3H baseline.

Execution Pipeline:
1. ScenarioController selects and validates scenario definition SWELL_0001.
2. Asserts pristine reference model (IEEE_9bus_PQD_HIL_R2025a.slx) integrity.
3. Invokes MATLAB simulation runner on the working model (IEEE_9bus_PQD_DISTURBANCES.slx).
4. Slices 1000-sample (200 ms @ 5 kHz) three-phase waveform.
5. Computes authoritative 32-feature contract using production Python DSP.
6. Evaluates independent physical validation gates (GATE3C_VALIDATION_PLAN.md §3.3).
7. Performs multi-phase analysis (Va, Vb, Vc independent half-cycle RMS tracking).
8. Evaluates raw ML prediction and flags model domain mismatch without contaminating labels.
9. Exports waveform NPZ, features JSON, validation JSON, and complete metadata.
"""

import os
import sys
import json
import subprocess
import hashlib
import numpy as np
import scipy.io

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scenarios.scenario_controller import ScenarioController, verify_pristine_model_integrity
from pipeline.disturbance_validator import validate_swell_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import MLPClassifier, _MODEL_FEATURE_ORDER

DATA_SWELL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'swell')
DATA_NORMAL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
WEIGHTS_PATH = os.path.join(PROJECT_ROOT, 'ml', 'models', 'model_weights_32.json')

os.makedirs(DATA_SWELL_DIR, exist_ok=True)


def run_matlab_simulation(scenario_json_path: str, output_mat_path: str) -> None:
    """Executes MATLAB simulation runner via CLI."""
    scen_p = scenario_json_path.replace(os.sep, '/')
    out_p = output_mat_path.replace(os.sep, '/')
    matlab_cmd = (
        f"addpath('scripts'); addpath('IEEE_9bus'); "
        f"run_disturbance_simulation('{scen_p}', '{out_p}')"
    )
    cmd = ["matlab", "-batch", matlab_cmd]
    print(f"[MATLAB] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print("[MATLAB Stdout]:", res.stdout)
        print("[MATLAB Stderr]:", res.stderr)
        raise RuntimeError(f"MATLAB simulation failed with exit code {res.returncode}")
    print("[MATLAB] Finished successfully.")


def main():
    print("=" * 70)
    print("GATE 3G — VOLTAGE SWELL IMPLEMENTATION & VALIDATION")
    print("=" * 70)

    # 1. Initialize Scenario Controller & Verify Pristine Model Integrity
    print("\n[Step 1] Initializing Scenario Controller & Integrity Verification...")
    controller = ScenarioController()
    scenario_id = 'SWELL_0001_three_phase_symmetric'
    scen = controller.select_scenario(scenario_id)
    verify_pristine_model_integrity()
    print(f" -> Selected Scenario: {scenario_id}")
    print(f" -> Class:            {scen['class']}")
    print(f" -> Ground Truth:     {controller.ground_truth_label} (Label Index: {controller.ground_truth_label_idx})")
    print(f" -> Pristine Model:   UNTOUCHED (SHA256 verified)")

    # 2. Execute Electrical Simulation in MATLAB
    print("\n[Step 2] Executing Electrical Simulation on Working Model...")
    scenario_json_path = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', f"{scenario_id}.json")
    output_mat_path = os.path.join(DATA_SWELL_DIR, 'raw_sim_swell_0001.mat')
    if not os.path.exists(output_mat_path):
        run_matlab_simulation(scenario_json_path, output_mat_path)
    else:
        print(f" -> Found existing raw simulation file: {output_mat_path}")

    # Verify pristine model was NOT modified during simulation
    verify_pristine_model_integrity()
    print(" -> Pristine reference model re-verified untouched after simulation.")

    # 3. Load Resampled Waveform Frame
    print("\n[Step 3] Loading & Inspecting Waveform Frame...")
    mat = scipy.io.loadmat(output_mat_path)
    v_frame = mat['V_frame']  # (1000, 3)
    i_frame = mat['I_frame']  # (1000, 3)
    t_frame = mat['t_frame'].flatten()  # (1000,)

    n_samples, n_channels = v_frame.shape
    print(f" -> Waveform shape:  {v_frame.shape} ({n_samples} samples, {n_channels} channels)")
    print(f" -> Time span:       {t_frame[0]:.4f} s to {t_frame[-1]:.4f} s ({(t_frame[-1]-t_frame[0])*1000:.1f} ms)")

    # 4. Authoritative Feature Extraction (Phase A, B, C)
    print("\n[Step 4] Extracting Authoritative 32-Feature Contract...")
    feats_a = extract_enhanced_features(v_frame[:, 0], sample_rate=5000.0, f0=60.0)
    feats_b = extract_enhanced_features(v_frame[:, 1], sample_rate=5000.0, f0=60.0)
    feats_c = extract_enhanced_features(v_frame[:, 2], sample_rate=5000.0, f0=60.0)

    print(" -> Features Extracted:")
    print(f"    Phase A: RMS={feats_a['rms_voltage']:.4f} pu, Peak={feats_a['peak_voltage']:.4f}, Crest={feats_a['crest_factor']:.4f}, THD={feats_a['thd']:.2f}%, Freq={feats_a['system_freq']:.2f} Hz, SNR={feats_a['snr']:.1f} dB")
    print(f"    Phase B: RMS={feats_b['rms_voltage']:.4f} pu, Peak={feats_b['peak_voltage']:.4f}, Crest={feats_b['crest_factor']:.4f}, THD={feats_b['thd']:.2f}%, Freq={feats_b['system_freq']:.2f} Hz, SNR={feats_b['snr']:.1f} dB")
    print(f"    Phase C: RMS={feats_c['rms_voltage']:.4f} pu, Peak={feats_c['peak_voltage']:.4f}, Crest={feats_c['crest_factor']:.4f}, THD={feats_c['thd']:.2f}%, Freq={feats_c['system_freq']:.2f} Hz, SNR={feats_c['snr']:.1f} dB")

    # 5. Independent Physical Validation
    print("\n[Step 5] Evaluating Independent Physical Validation Gates (GATE3C_VALIDATION_PLAN §3.3)...")
    val_res = validate_swell_frame(v_frame, feats_a, nominal_baseline_rms=0.5887, fs=5000.0, f0=60.0)
    
    print(f" -> Validation Passed:     {val_res['physical_validation_passed']}")
    print(f" -> Class:                 {val_res['class']}")
    print(f" -> Phase Configuration:   {val_res['phase_configuration']}")
    print(f" -> Affected Phases:       {val_res['affected_phases']}")
    print(f" -> Primary Affected Phase:{val_res['primary_phase']}")
    print(f" -> Pre-event Nominal RMS: {val_res['pre_event_nominal_rms']:.4f} pu")
    print(f" -> Max Event RMS:         {val_res['max_event_rms']:.4f} pu")
    print(f" -> Swell Magnitude Ratio: {val_res['swell_magnitude_pu']:.4f} pu (IEEE 1159 target: [1.10, 1.80])")
    print(f" -> Measured Duration:     {val_res['duration_ms']:.2f} ms")
    print(f" -> Event Window:          t=[{val_res['start_time_s']}, {val_res['end_time_s']}] s")

    print("\n -> Individual Gate Results:")
    for gate_name, gate_pass in val_res['gates'].items():
        status_str = "PASS" if gate_pass else "FAIL"
        print(f"    [{status_str}] {gate_name}")

    if not val_res['physical_validation_passed']:
        raise RuntimeError("Deterministic Swell scenario failed independent physical validation!")

    # 6. ML Model Inference & Decoupling Audit
    print("\n[Step 6] Auditing Raw ML Model Response (Confirming Label Decoupling)...")
    mlp = MLPClassifier.from_json(WEIGHTS_PATH)
    clean_feats_a = {k: (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer, int)) else v)) for k, v in feats_a.items()}
    vec_a = np.array([clean_feats_a[k] for k in _MODEL_FEATURE_ORDER], dtype=np.float32)
    pred_class_a, pred_conf_a, probs_a = mlp.predict(vec_a)

    print(f" -> Raw Model Prediction: {pred_class_a} ({pred_conf_a * 100:.2f}%)")
    print(f" -> Ground Truth Label:   {controller.ground_truth_label} (Derived from Scenario Controller)")
    print(f" -> Decoupling Verified:  True (ML inference NEVER overwrites scenario ground truth)")
    model_domain_status = "MODEL_DOMAIN_MISMATCH" if pred_class_a != controller.ground_truth_label else "MODEL_DOMAIN_MATCH"
    print(f" -> Model Domain Status:  {model_domain_status}")

    # 7. Export Artifacts
    print("\n[Step 7] Exporting Waveform, Features, Validation, and Scenario Metadata...")
    # NPZ Waveform
    npz_path = os.path.join(DATA_SWELL_DIR, 'swell_scenario_0001_waveform.npz')
    clean_feats_a = {k: (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer, int)) else v)) for k, v in feats_a.items()}
    clean_feats_b = {k: (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer, int)) else v)) for k, v in feats_b.items()}
    clean_feats_c = {k: (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer, int)) else v)) for k, v in feats_c.items()}
    np.savez_compressed(
        npz_path,
        waveforms=v_frame[np.newaxis, :, :],
        currents=i_frame[np.newaxis, :, :],
        time=t_frame,
        fs=5000.0,
        f0=60.0,
        scenario_id=np.array([scenario_id]),
        ground_truth=np.array([controller.ground_truth_label]),
        label_idx=np.array([controller.ground_truth_label_idx])
    )
    print(f" -> Saved Waveform NPZ: {npz_path}")

    # Features JSON
    feats_json_path = os.path.join(DATA_SWELL_DIR, 'swell_scenario_0001_features.json')
    with open(feats_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'scenario_id': scenario_id,
            'ground_truth': controller.ground_truth_label,
            'label_idx': controller.ground_truth_label_idx,
            'phase_A': clean_feats_a,
            'phase_B': clean_feats_b,
            'phase_C': clean_feats_c
        }, f, indent=2)
    print(f" -> Saved Features JSON: {feats_json_path}")

    # Validation JSON
    val_json_path = os.path.join(DATA_SWELL_DIR, 'swell_scenario_0001_validation.json')
    with open(val_json_path, 'w', encoding='utf-8') as f:
        json.dump(val_res, f, indent=2)
    print(f" -> Saved Validation JSON: {val_json_path}")

    # Metadata JSON
    with open(os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx'), 'rb') as f:
        pristine_sha = hashlib.sha256(f.read()).hexdigest()
    with open(npz_path, 'rb') as f:
        npz_sha = hashlib.sha256(f.read()).hexdigest()

    meta_json_path = os.path.join(DATA_SWELL_DIR, 'swell_scenario_0001_metadata.json')
    with open(meta_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'scenario': scen,
            'physical_validation': val_res,
            'raw_ml_prediction': {
                'predicted_class': pred_class_a,
                'confidence': pred_conf_a,
                'model_domain_status': model_domain_status
            },
            'checksums': {
                'pristine_model_sha256': pristine_sha,
                'waveform_npz_sha256': npz_sha
            }
        }, f, indent=2)
    print(f" -> Saved Metadata JSON: {meta_json_path}")

    print("\n" + "=" * 70)
    print("GATE 3G DETERMINISTIC SCENARIO COMPLETED & VALIDATED: PASS")
    print("=" * 70)


if __name__ == '__main__':
    main()

"""
scripts/generate_and_validate_sag_scenario.py
---------------------------------------------
Generates, processes, validates, and records the first deterministic Voltage Sag
scenario for Gate 3D.

Execution Pipeline:
1. ScenarioController selects and validates scenario definition SAG_0001.
2. Asserts pristine reference model (IEEE_9bus_PQD_HIL_R2025a.slx) integrity.
3. Invokes MATLAB simulation runner on the working model (IEEE_9bus_PQD_DISTURBANCES.slx).
4. Slices 1000-sample (200 ms @ 5 kHz) three-phase waveform.
5. Computes authoritative 32-feature contract using production Python DSP.
6. Evaluates independent physical validation gates (GATE3C_VALIDATION_PLAN.md §3.2).
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
from pipeline.disturbance_validator import validate_sag_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import MLPClassifier, _MODEL_FEATURE_ORDER

DATA_SAG_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'sag')
DATA_NORMAL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
WEIGHTS_PATH = os.path.join(PROJECT_ROOT, 'ml', 'models', 'model_weights_32.json')

os.makedirs(DATA_SAG_DIR, exist_ok=True)


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
    print("GATE 3D — VOLTAGE SAG IMPLEMENTATION & VALIDATION")
    print("=" * 70)

    # 1. Initialize Scenario Controller & Verify Pristine Model Integrity
    print("\n[Step 1] Initializing Scenario Controller & Integrity Verification...")
    controller = ScenarioController()
    scenario_id = 'SAG_0001_three_phase_symmetric'
    scen = controller.select_scenario(scenario_id)
    verify_pristine_model_integrity()
    print(f" -> Selected Scenario: {scenario_id}")
    print(f" -> Class:            {scen['class']}")
    print(f" -> Ground Truth:     {controller.ground_truth_label} (Label Index: {controller.ground_truth_label_idx})")
    print(f" -> Pristine Model:   UNTOUCHED (SHA256 verified)")

    # 2. Execute Electrical Simulation in MATLAB
    print("\n[Step 2] Executing Electrical Simulation on Working Model...")
    scenario_json_path = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', f"{scenario_id}.json")
    output_mat_path = os.path.join(DATA_SAG_DIR, 'raw_sim_sag_0001.mat')
    run_matlab_simulation(scenario_json_path, output_mat_path)

    # Verify pristine model was NOT modified during simulation
    verify_pristine_model_integrity()
    print(" -> Pristine reference model re-verified untouched after simulation.")

    # 3. Load Resampled Waveform Frame
    print("\n[Step 3] Loading & Inspecting Waveform Frame...")
    mat = scipy.io.loadmat(output_mat_path)
    v_frame = mat['V_frame'] # (1000, 3)
    i_frame = mat['I_frame'] # (1000, 3)
    t_frame = mat['t_frame'].flatten() # (1000,)

    n_samples, n_channels = v_frame.shape
    print(f" -> Waveform shape:  {v_frame.shape} ({n_samples} samples, {n_channels} channels)")
    print(f" -> Time span:       {t_frame[0]:.4f} s to {t_frame[-1]:.4f} s ({(t_frame[-1]-t_frame[0])*1000:.1f} ms)")

    # 4. Authoritative Feature Extraction (Phase A, B, C)
    print("\n[Step 4] Extracting Authoritative 32-Feature Contract...")
    feats_a = extract_enhanced_features(v_frame[:, 0], sample_rate=5000.0, f0=60.0)
    feats_b = extract_enhanced_features(v_frame[:, 1], sample_rate=5000.0, f0=60.0)
    feats_c = extract_enhanced_features(v_frame[:, 2], sample_rate=5000.0, f0=60.0)

    # Convert np.float64 to float for serialization
    def clean_dict(d):
        return {k: float(v) if isinstance(v, (np.floating, float, int)) else v for k, v in d.items()}

    clean_feats_a = clean_dict(feats_a)
    clean_feats_b = clean_dict(feats_b)
    clean_feats_c = clean_dict(feats_c)

    print(" -> Phase A key features:")
    for k in ['rms_voltage', 'peak_voltage', 'crest_factor', 'duration', 'system_freq', 'dominant_freq', 'thd', 'snr']:
        print(f"    {k:15s}: {clean_feats_a[k]:.4f}")

    # 5. Independent Physical Validation
    print("\n[Step 5] Performing Independent Physical Validation...")
    # Normal baseline reference from Gate 3B1
    normal_baseline_rms = 0.5887
    val_result = validate_sag_frame(v_frame, clean_feats_a, nominal_baseline_rms=normal_baseline_rms)

    print(f" -> Physical Validation Result: {'PASS' if val_result['physical_validation_passed'] else 'FAIL'}")
    print(f" -> Affected Phases:           {val_result['affected_phases']}")
    print(f" -> Phase Configuration:       {val_result['phase_configuration']}")
    print(f" -> Pre-event Nominal RMS:     {val_result['pre_event_nominal_rms']:.4f} pu")
    print(f" -> Min Event RMS:             {val_result['min_event_rms']:.4f} pu")
    print(f" -> Measured Residual Voltage: {val_result['residual_voltage_pu']:.4f} pu ({val_result['residual_voltage_pu']*100:.1f}%)")
    print(f" -> Measured Duration:         {val_result['duration_ms']:.2f} ms")
    print(f" -> Event Window:              t = {val_result['start_time_s']} s to {val_result['end_time_s']} s")
    print(" -> Gate Evaluations:")
    for gname, gval in val_result['gates'].items():
        print(f"    {gname:30s}: {'PASS' if gval else 'FAIL'}")

    # 6. ML Model Inference & Domain Status Separation
    print("\n[Step 6] Evaluating Raw ML Model Prediction (Domain Isolation)...")
    mlp = MLPClassifier.from_json(WEIGHTS_PATH)
    vec_a = np.array([clean_feats_a[f] for f in _MODEL_FEATURE_ORDER], dtype=np.float32)
    pred_cls, conf, probs = mlp.predict(vec_a)

    print(f" -> Ground Truth (Scenario):   {controller.ground_truth_label} (Label Index: {controller.ground_truth_label_idx})")
    print(f" -> Raw ML Prediction:         {pred_cls} (Confidence: {conf:.4f})")
    print(f" -> Model Domain Status:       MODEL_DOMAIN_MISMATCH")
    print("    (Note: Existing MLP weights trained on legacy 50-Hz synthetic dataset. "
          "Ground truth is decoupled from model output per Gate 3D requirements.)")

    # 7. Comparison with Normal Baseline
    print("\n[Step 7] Comparison: Normal Baseline vs Sag Event...")
    print(f"{'Feature':<20s} | {'Normal Baseline':<16s} | {'Sag Waveform':<16s} | {'Difference / Status':<20s}")
    print("-" * 80)
    normal_ref = {
        'rms_voltage': 0.5887,
        'peak_voltage': 0.8327,
        'crest_factor': 1.4144,
        'duration': 0.0,
        'system_freq': 60.00,
        'thd': 0.08,
        'snr': 51.7
    }
    for feat_k, norm_v in normal_ref.items():
        sag_v = clean_feats_a[feat_k]
        diff_str = f"{sag_v - norm_v:+.4f}"
        print(f"{feat_k:<20s} | {norm_v:<16.4f} | {sag_v:<16.4f} | {diff_str:<20s}")

    # 8. Export Artifacts
    print("\n[Step 8] Exporting Datasets & Metadata...")
    npz_path = os.path.join(DATA_SAG_DIR, 'sag_scenario_0001_waveform.npz')
    np.savez_compressed(
        npz_path,
        waveforms=v_frame[np.newaxis, :, :], # (1, 1000, 3)
        currents=i_frame[np.newaxis, :, :],  # (1, 1000, 3)
        time=t_frame,
        scenario_id=np.array([scenario_id]),
        ground_truth=np.array([controller.ground_truth_label]),
        label_idx=np.array([controller.ground_truth_label_idx])
    )
    print(f" -> Saved Waveform NPZ:   {npz_path}")

    feats_path = os.path.join(DATA_SAG_DIR, 'sag_scenario_0001_features.json')
    with open(feats_path, 'w', encoding='utf-8') as f:
        json.dump({
            'scenario_id': scenario_id,
            'ground_truth': controller.ground_truth_label,
            'label_idx': controller.ground_truth_label_idx,
            'phase_A': clean_feats_a,
            'phase_B': clean_feats_b,
            'phase_C': clean_feats_c
        }, f, indent=2)
    print(f" -> Saved Features JSON:   {feats_path}")

    val_path = os.path.join(DATA_SAG_DIR, 'sag_scenario_0001_validation.json')
    with open(val_path, 'w', encoding='utf-8') as f:
        json.dump(val_result, f, indent=2)
    print(f" -> Saved Validation JSON: {val_path}")

    meta_path = os.path.join(DATA_SAG_DIR, 'sag_scenario_0001_metadata.json')
    meta = {
        'scenario': scen,
        'ground_truth': controller.ground_truth_label,
        'ground_truth_label_idx': controller.ground_truth_label_idx,
        'label_source': 'SCENARIO_CONTROLLER',
        'raw_model_prediction': pred_cls,
        'raw_model_confidence': float(conf),
        'model_domain_status': 'MODEL_DOMAIN_MISMATCH',
        'physical_validation': val_result,
        'pristine_model_sha256': hashlib.sha256(open(os.path.join(PROJECT_ROOT, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx'), 'rb').read()).hexdigest(),
        'working_model': 'IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx',
        'key_metrics': {
            'measured_pre_event_rms': val_result['pre_event_nominal_rms'],
            'measured_event_rms': val_result['min_event_rms'],
            'measured_residual_pu': val_result['residual_voltage_pu'],
            'measured_duration_ms': val_result['duration_ms'],
            'affected_phases': val_result['affected_phases'],
            'phase_configuration': val_result['phase_configuration']
        }
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f" -> Saved Metadata JSON:   {meta_path}")

    # Summary
    print("\n" + "=" * 70)
    print(f"GATE3D_SAG = {'PASS' if val_result['physical_validation_passed'] else 'FAIL'}")
    print("=" * 70)

    return val_result['physical_validation_passed']


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

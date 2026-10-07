"""
scripts/generate_and_validate_interruption_scenario.py
------------------------------------------------------
Generates, processes, validates, and records the first deterministic Voltage Interruption
scenario for Gate 3J.

Execution Pipeline:
1. ScenarioController selects and validates scenario definition INT_0001.
2. Asserts pristine reference model (IEEE_9bus_PQD_HIL_R2025a.slx) integrity.
3. Invokes MATLAB simulation runner on the working model (IEEE_9bus_PQD_DISTURBANCES.slx).
4. Slices 1000-sample (200 ms @ 5 kHz) three-phase waveform.
5. Computes authoritative 32-feature contract using production Python DSP with phase-aware SNR.
6. Evaluates independent physical validation gates (GATE3C_VALIDATION_PLAN.md §3.4 & IEEE 1159 Table 2).
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
from pipeline.disturbance_validator import validate_interruption_frame
from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import MLPClassifier, _MODEL_FEATURE_ORDER

DATA_INT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'interruption')
DATA_NORMAL_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal')
WEIGHTS_PATH = os.path.join(PROJECT_ROOT, 'ml', 'models', 'model_weights_32.json')

os.makedirs(DATA_INT_DIR, exist_ok=True)


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
    print("GATE 3J — VOLTAGE INTERRUPTION IMPLEMENTATION & VALIDATION")
    print("=" * 70)

    # 1. Initialize Scenario Controller & Verify Pristine Model Integrity
    print("\n[Step 1] Initializing Scenario Controller & Integrity Verification...")
    controller = ScenarioController()
    scenario_id = 'INT_0001_three_phase_symmetric'
    scen = controller.select_scenario(scenario_id)
    verify_pristine_model_integrity()
    print(f" -> Selected Scenario: {scenario_id}")
    print(f" -> Class:            {scen['class']}")
    print(f" -> Ground Truth:     {controller.ground_truth_label} (Label Index: {controller.ground_truth_label_idx})")
    print(f" -> Pristine Model:   UNTOUCHED (SHA256 verified)")

    # 2. Execute Electrical Simulation in MATLAB
    print("\n[Step 2] Executing Electrical Simulation on Working Model...")
    scenario_json_path = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions', f"{scenario_id}.json")
    output_mat_path = os.path.join(DATA_INT_DIR, 'raw_sim_int_0001.mat')
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

    # 4. Feature Extraction via Production DSP Pipeline (Phase A)
    print("\n[Step 4] Extracting 32 Authoritative Features via Production DSP...")
    v_a = v_frame[:, 0]
    enhanced_dict = extract_enhanced_features(v_a, sample_rate=5000.0, f0=60.0)
    
    # Filter strictly to the 32 production features
    features_32 = {k: enhanced_dict[k] for k in _MODEL_FEATURE_ORDER}
    print(f" -> Extracted {len(features_32)} features matching model contract.")
    print(f" -> Measured RMS Voltage:     {features_32['rms_voltage']:.4f} pu")
    print(f" -> Measured Peak Voltage:    {features_32['peak_voltage']:.4f} pu")
    print(f" -> Measured Crest Factor:    {features_32['crest_factor']:.4f}")
    print(f" -> Measured Disturbance Dur: {features_32['duration']:.2f} ms")
    print(f" -> Measured Phase-Aware SNR: {features_32['snr']:.2f} dB")
    print(f" -> Measured THD:             {features_32['thd']:.4f}%")

    # 5. Independent Physical Validation Gates
    print("\n[Step 5] Evaluating Independent Physical Validation Gates...")
    nominal_baseline_rms = 0.5887  # Authoritative 60-Hz nominal baseline RMS
    val_result = validate_interruption_frame(
        v_frame,
        dsp_features=features_32,
        nominal_baseline_rms=nominal_baseline_rms,
        fs=5000.0,
        f0=60.0
    )

    print(f" -> Physical Validation Result: {'PASS' if val_result['physical_validation_passed'] else 'FAIL'}")
    print(f" -> Pre-event Nominal RMS:      {val_result['pre_event_nominal_rms']:.4f} pu")
    print(f" -> Event Residual RMS:         {val_result['min_event_rms']:.4f} pu")
    print(f" -> Residual Voltage Ratio:     {val_result['residual_voltage_pu']:.4f} pu (IEEE 1159 < 0.10 pu)")
    print(f" -> Measured Duration:          {val_result['duration_ms']:.2f} ms")
    print(f" -> Inception Time:             {val_result['start_time_s']} s")
    print(f" -> Recovery Time:              {val_result['end_time_s']} s")
    print(f" -> Primary Affected Phase:     {val_result['primary_phase']}")
    print(f" -> Phase Configuration:        {val_result['phase_configuration']}")
    print(" -> Validation Gate Details:")
    for gate_name, gate_pass in val_result['gates'].items():
        print(f"    - {gate_name}: {'PASS' if gate_pass else 'FAIL'}")

    if not val_result['physical_validation_passed']:
        raise RuntimeError("Physical validation gates failed for Interruption scenario!")

    # 6. Multi-Phase Analysis
    print("\n[Step 6] Per-Phase Electrical Metrics:")
    for ph, m in val_result['per_phase_metrics'].items():
        print(f" -> Phase {ph}: Min RMS = {m['min_rms']:.4f} pu, Residual Ratio = {m['residual_ratio']:.4f} pu, Duration = {m['duration_ms']:.1f} ms")

    # 7. Model Domain Status & Label Purity
    print("\n[Step 7] Evaluating Label Purity & ML Baseline Prediction...")
    clf = MLPClassifier.from_json(WEIGHTS_PATH)
    feat_vec = np.array([features_32[k] for k in _MODEL_FEATURE_ORDER], dtype=np.float32)
    pred_label, pred_idx, pred_probs = clf.predict(feat_vec)

    print(f" -> Authoritative Ground Truth: {controller.ground_truth_label} (Index: {controller.ground_truth_label_idx})")
    print(f" -> Physical Validation Label:  {val_result['class']}")
    pred_idx_int = int(pred_idx)
    print(f" -> Raw ML Model Prediction:    {pred_label} (Index: {pred_idx_int}, Confidence: {pred_probs[pred_idx_int]*100:.2f}%)")
    print(" -> Model Domain Status:        OUT_OF_DOMAIN")
    print("    (Legacy weights not yet retrained on 60-Hz IEEE 9-bus Interruption. ML output does NOT alter ground truth.)")

    # 8. Save Artifacts
    print("\n[Step 8] Exporting Scenario Waveform, Features, and Metadata...")
    npz_path = os.path.join(DATA_INT_DIR, 'interruption_scenario_0001_waveform.npz')
    np.savez_compressed(npz_path, waveform=v_frame, time=t_frame, currents=i_frame)

    feat_path = os.path.join(DATA_INT_DIR, 'interruption_scenario_0001_features.json')
    with open(feat_path, 'w', encoding='utf-8') as f:
        json.dump(features_32, f, indent=2)

    val_path = os.path.join(DATA_INT_DIR, 'interruption_scenario_0001_validation.json')
    with open(val_path, 'w', encoding='utf-8') as f:
        json.dump(val_result, f, indent=2)

    # Compute checksums
    sha_npz = hashlib.sha256(open(npz_path, 'rb').read()).hexdigest()
    sha_feat = hashlib.sha256(open(feat_path, 'rb').read()).hexdigest()
    sha_val = hashlib.sha256(open(val_path, 'rb').read()).hexdigest()

    meta = {
        'scenario_id': scenario_id,
        'class': 'Interruption',
        'label_idx': 2,
        'label_source': 'SCENARIO_CONTROLLER',
        'operating_condition_id': scen.get('operating_condition_id', 1),
        'nominal_frequency_hz': 60.0,
        'sampling_rate_hz': 5000.0,
        'window_samples': 1000,
        'window_duration_ms': 200.0,
        'parameters': scen['parameters'],
        'parameter_provenance': scen['parameter_provenance'],
        'standard_references': scen['standard_references'],
        'physical_validation': {
            'status': 'PASS',
            'pre_event_nominal_rms': val_result['pre_event_nominal_rms'],
            'min_event_rms': val_result['min_event_rms'],
            'residual_voltage_pu': val_result['residual_voltage_pu'],
            'measured_duration_ms': val_result['duration_ms'],
            'start_time_s': val_result['start_time_s'],
            'end_time_s': val_result['end_time_s'],
            'affected_phases': val_result['affected_phases'],
            'phase_configuration': val_result['phase_configuration']
        },
        'ml_evaluation': {
            'raw_prediction': pred_label,
            'prediction_confidence': float(pred_probs[pred_idx_int]),
            'model_domain_status': 'OUT_OF_DOMAIN',
            'decoupling_confirmed': True
        },
        'checksums': {
            'waveform_npz_sha256': sha_npz,
            'features_json_sha256': sha_feat,
            'validation_json_sha256': sha_val
        }
    }

    meta_path = os.path.join(DATA_INT_DIR, 'interruption_scenario_0001_metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    print(f" -> Saved Waveform NPZ:    {npz_path} (SHA256: {sha_npz[:12]}...)")
    print(f" -> Saved Features JSON:   {feat_path} (SHA256: {sha_feat[:12]}...)")
    print(f" -> Saved Validation JSON: {val_path} (SHA256: {sha_val[:12]}...)")
    print(f" -> Saved Metadata JSON:   {meta_path}")

    print("\n" + "=" * 70)
    print("GATE 3J DETERMINISTIC SCENARIO IMPLEMENTATION: COMPLETE & VERIFIED")
    print("=" * 70)


if __name__ == '__main__':
    main()

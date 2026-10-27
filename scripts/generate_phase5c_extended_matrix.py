"""
scripts/generate_phase5c_extended_matrix.py
-------------------------------------------
Constructs the versioned Phase 5C Extended Simulation Matrix specification
per Master Prompt Part II Section 4:
- Target: 368 independent trajectories across 8 classes:
    - 30 Train trajectories per class (240 trajectories, 7,680 frames)
    - 8 Val trajectories per class (64 trajectories, 2,048 frames)
    - 8 Challenge trajectories per class (64 trajectories, 2,048 frames)
- 8 distinct held-out challenge operating conditions (Conditions 33 to 40)
- Preserves the 144-trajectory core matrix as the primary executed baseline
- Full machine-readable documentation with exact counts, parameter grids, and split assignments.
"""

import os
import json
import csv
import copy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_MATRIX_PATH = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5b2_simulation_matrix.json')
EXTENDED_JSON_PATH = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5c_extended_matrix.json')
EXTENDED_CSV_PATH = os.path.join(PROJECT_ROOT, 'scenarios', 'phase5c_extended_matrix.csv')

CLASS_NAMES = ["Flicker", "Harmonics", "Interruption", "Normal", "Notch", "Sag", "Swell", "Transient"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

ADDITIONAL_CHALLENGE_CONDITIONS = {
    "37": {
        "name": "High Wind Intermittent Fluctuation",
        "family": "Family J (Renewable Intermittency [CHALLENGE])",
        "split_default": "challenge",
        "pA": 1.05, "qA": 1.02, "pB": 0.88, "qB": 0.90, "pC": 1.00, "qC": 0.98,
        "v1": 1.01, "f": 60.05, "v2": 1.00, "p2": 150000000.0, "v3": 0.98, "p3": 95000000.0
    },
    "38": {
        "name": "Stressed Industrial Induction Dynamic Load",
        "family": "Family K (Dynamic Industrial Impedance [CHALLENGE])",
        "split_default": "challenge",
        "pA": 1.20, "qA": 1.30, "pB": 1.00, "qB": 1.00, "pC": 0.95, "qC": 0.95,
        "v1": 0.99, "f": 59.92, "v2": 0.98, "p2": 170000000.0, "v3": 0.99, "p3": 85000000.0
    },
    "39": {
        "name": "High Solar Reverse Feeder Injection",
        "family": "Family L (Reverse Active Flow [CHALLENGE])",
        "split_default": "challenge",
        "pA": 0.70, "qA": 0.80, "pB": 0.75, "qB": 0.85, "pC": 0.80, "qC": 0.80,
        "v1": 1.02, "f": 60.08, "v2": 1.01, "p2": 120000000.0, "v3": 1.00, "p3": 70000000.0
    },
    "40": {
        "name": "Extreme Substation Reactive Deficit",
        "family": "Family M (Severe Reactive Deficit [CHALLENGE])",
        "split_default": "challenge",
        "pA": 1.10, "qA": 1.35, "pB": 1.10, "qB": 1.35, "pC": 1.10, "qC": 1.35,
        "v1": 0.98, "f": 59.90, "v2": 0.97, "p2": 165000000.0, "v3": 0.97, "p3": 88000000.0
    }
}

def generate_extended_matrix():
    with open(CORE_MATRIX_PATH, 'r', encoding='utf-8') as f:
        core = json.load(f)
    
    op_catalog = copy.deepcopy(core['operating_condition_catalog'])
    op_catalog.update(ADDITIONAL_CHALLENGE_CONDITIONS)
    
    core_trajectories = core['trajectories']
    
    # We preserve the 144 core trajectories exactly
    extended_trajectories = []
    for t in core_trajectories:
        t_copy = copy.deepcopy(t)
        t_copy['core_or_supplementary'] = 'core'
        extended_trajectories.append(t_copy)
    
    # Generate supplementary trajectories to reach 30 Train, 8 Val, 8 Challenge per class (368 total)
    # Core has per class: 10 Train, 4 Val, 4 Challenge (18 total)
    # Supplementary needs per class: 20 Train, 4 Val, 4 Challenge (28 total per class * 8 = 224 supplementary)
    
    supp_idx = 145
    for cls in CLASS_NAMES:
        cls_prefix = cls[:3].upper()
        lbl_idx = CLASS_TO_IDX[cls]
        
        # 20 supplementary train trajectories
        for i in range(1, 21):
            cond_id = ((i - 1) % 24) + 1  # Train conditions 1..24
            cond_meta = op_catalog[str(cond_id)]
            traj_id = f"P5C_{cls_prefix}_{supp_idx:04d}_s{i:02d}_tr_c{cond_id:02d}"
            snr = 52.0 if i % 3 != 0 else (46.0 if i % 2 == 0 else 40.0)
            adc = 14 if i % 2 == 1 else 12
            
            # Base parameter from core template
            template = [t for t in core_trajectories if t['class'] == cls][i % 10]
            params = copy.deepcopy(template['parameters'])
            
            extended_trajectories.append({
                "trajectory_id": traj_id,
                "matrix_index": supp_idx,
                "core_or_supplementary": "supplementary",
                "class": cls,
                "label_idx": lbl_idx,
                "operating_condition_id": cond_id,
                "operating_condition_name": cond_meta['name'],
                "operating_condition_family": cond_meta['family'],
                "phase": template['phase'],
                "severity": template['severity'],
                "split": "train",
                "sensor_noise_snr_db": snr,
                "adc_bits": adc,
                "expected_windows_count": 32,
                "parameters": params
            })
            supp_idx += 1
            
        # 4 supplementary val trajectories (using Val conditions 25..32)
        for i in range(1, 5):
            cond_id = 24 + i  # Conditions 25..28
            cond_meta = op_catalog[str(cond_id)]
            traj_id = f"P5C_{cls_prefix}_{supp_idx:04d}_s{i:02d}_va_c{cond_id:02d}"
            snr = 52.0 if i % 2 == 1 else 46.0
            adc = 14 if i % 2 == 1 else 12
            template = [t for t in core_trajectories if t['class'] == cls][10 + (i % 4)]
            params = copy.deepcopy(template['parameters'])
            
            extended_trajectories.append({
                "trajectory_id": traj_id,
                "matrix_index": supp_idx,
                "core_or_supplementary": "supplementary",
                "class": cls,
                "label_idx": lbl_idx,
                "operating_condition_id": cond_id,
                "operating_condition_name": cond_meta['name'],
                "operating_condition_family": cond_meta['family'],
                "phase": template['phase'],
                "severity": template['severity'],
                "split": "val",
                "sensor_noise_snr_db": snr,
                "adc_bits": adc,
                "expected_windows_count": 32,
                "parameters": params
            })
            supp_idx += 1
            
        # 4 supplementary challenge trajectories (using NEW Challenge conditions 37..40)
        for i in range(1, 5):
            cond_id = 36 + i  # Conditions 37..40
            cond_meta = op_catalog[str(cond_id)]
            traj_id = f"P5C_{cls_prefix}_{supp_idx:04d}_s{i:02d}_ch_c{cond_id:02d}"
            snr = 52.0 if i % 2 == 1 else 40.0
            adc = 14 if i % 2 == 1 else 12
            template = [t for t in core_trajectories if t['class'] == cls][14 + (i % 4)]
            params = copy.deepcopy(template['parameters'])
            
            extended_trajectories.append({
                "trajectory_id": traj_id,
                "matrix_index": supp_idx,
                "core_or_supplementary": "supplementary",
                "class": cls,
                "label_idx": lbl_idx,
                "operating_condition_id": cond_id,
                "operating_condition_name": cond_meta['name'],
                "operating_condition_family": cond_meta['family'],
                "phase": template['phase'],
                "severity": template['severity'],
                "split": "challenge",
                "sensor_noise_snr_db": snr,
                "adc_bits": adc,
                "expected_windows_count": 32,
                "parameters": params
            })
            supp_idx += 1

    total_trajs = len(extended_trajectories)
    assert total_trajs == 368, f"Total trajectories {total_trajs} != 368"
    
    split_summary = {
        "train_trajectories": sum(1 for t in extended_trajectories if t['split'] == 'train'),
        "val_trajectories": sum(1 for t in extended_trajectories if t['split'] == 'val'),
        "challenge_trajectories": sum(1 for t in extended_trajectories if t['split'] == 'challenge'),
        "train_frames": sum(1 for t in extended_trajectories if t['split'] == 'train') * 32,
        "val_frames": sum(1 for t in extended_trajectories if t['split'] == 'val') * 32,
        "challenge_frames": sum(1 for t in extended_trajectories if t['split'] == 'challenge') * 32,
        "total_frames": 368 * 32
    }
    
    assert split_summary['train_trajectories'] == 240
    assert split_summary['val_trajectories'] == 64
    assert split_summary['challenge_trajectories'] == 64
    assert split_summary['total_frames'] == 11776
    
    doc = {
        "schema_version": "3.0",
        "phase": "Phase 5C Extended Simulation Matrix (Core + Supplementary)",
        "study": "IEEE 9-bus Multi-Model Power Quality Comparative Lab",
        "total_trajectories": 368,
        "core_trajectories_count": 144,
        "supplementary_trajectories_count": 224,
        "frames_per_trajectory": 32,
        "total_dataset_frames": 11776,
        "classes_count": 8,
        "class_mapping": CLASS_TO_IDX,
        "operating_conditions_count": len(op_catalog),
        "challenge_conditions": [33, 34, 35, 36, 37, 38, 39, 40],
        "split_summary": split_summary,
        "operating_condition_catalog": op_catalog,
        "trajectories": extended_trajectories
    }
    
    with open(EXTENDED_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
    print(f"[Success] Saved Phase 5C Extended Matrix to {EXTENDED_JSON_PATH}")
    
    fieldnames = [
        "trajectory_id", "matrix_index", "core_or_supplementary", "class", "label_idx",
        "operating_condition_id", "operating_condition_name", "operating_condition_family",
        "phase", "severity", "split", "sensor_noise_snr_db", "adc_bits", "expected_windows_count"
    ]
    with open(EXTENDED_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in extended_trajectories:
            row = {k: t.get(k, '') for k in fieldnames}
            writer.writerow(row)
    print(f"[Success] Saved Phase 5C Extended Matrix CSV to {EXTENDED_CSV_PATH}")

if __name__ == '__main__':
    generate_extended_matrix()

"""
scenarios/scenario_controller.py
--------------------------------
Authoritative modular scenario architecture for PQ disturbance injection
in the IEEE 9-bus 60-Hz Power Quality system.

Key Principles:
1. Declarative, schema-validated scenario definitions (GATE3C_SCENARIO_SCHEMA.json).
2. Ground truth originates EXCLUSIVELY from the scenario controller (label_source = "SCENARIO_CONTROLLER").
   The ML model is NEVER consulted to determine ground truth.
3. Pristine model (IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) is asserted unchanged.
4. Disturbances are modular and independently selectable (enabled=True/False, scenario_id).
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
import jsonschema

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'docs', 'GATE3C_SCENARIO_SCHEMA.json')
DEFINITIONS_DIR = os.path.join(PROJECT_ROOT, 'scenarios', 'definitions')
PRISTINE_MODEL_REL = os.path.join('IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx')
PRISTINE_MODEL_FULL = os.path.join(PROJECT_ROOT, PRISTINE_MODEL_REL)
PRISTINE_SHA256 = '5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d'

# Authoritative class labels matching dsp/phase_processor.py
CLASS_LABELS = [
    'Flicker', 'Harmonics', 'Interruption', 'Normal',
    'Notch', 'Sag', 'Swell', 'Transient'
]
CLASS_TO_IDX = {cls: idx for idx, cls in enumerate(CLASS_LABELS)}


def verify_pristine_model_integrity() -> bool:
    """Verifies that the reference Simulink model has not been altered."""
    if not os.path.exists(PRISTINE_MODEL_FULL):
        raise FileNotFoundError(f"Pristine model not found at {PRISTINE_MODEL_FULL}")
    with open(PRISTINE_MODEL_FULL, 'rb') as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()
    if actual_sha != PRISTINE_SHA256:
        raise RuntimeError(
            f"PRISTINE MODEL INTEGRITY VIOLATION!\n"
            f"Expected SHA256: {PRISTINE_SHA256}\n"
            f"Actual SHA256:   {actual_sha}"
        )
    return True


class ScenarioController:
    """
    Manages loading, validation, and activation of disturbance scenarios.
    """

    def __init__(self, schema_path: str = SCHEMA_PATH, definitions_dir: str = DEFINITIONS_DIR):
        self.schema_path = schema_path
        self.definitions_dir = definitions_dir
        os.makedirs(self.definitions_dir, exist_ok=True)
        
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
            
        self.active_scenario: Optional[Dict[str, Any]] = None
        self.enabled: bool = False
        self.loaded_scenarios: Dict[str, Dict[str, Any]] = {}
        self.load_all_definitions()

    def validate_scenario(self, scenario_dict: Dict[str, Any]) -> None:
        """Validates a scenario dictionary against GATE3C_SCENARIO_SCHEMA.json."""
        jsonschema.validate(instance=scenario_dict, schema=self.schema)
        # Verify label_idx consistency with class
        expected_idx = CLASS_TO_IDX.get(scenario_dict['class'])
        if scenario_dict['label_idx'] != expected_idx:
            raise ValueError(
                f"Label index mismatch: class '{scenario_dict['class']}' has index "
                f"{scenario_dict['label_idx']}, expected {expected_idx} based on phase_processor contract."
            )
        # Verify pristine reference model declaration
        ref_model = scenario_dict.get('electrical_model', {}).get('reference_model', '')
        if 'IEEE_9bus_PQD_HIL_R2025a.slx' not in ref_model:
            raise ValueError(f"reference_model must point to pristine IEEE_9bus_PQD_HIL_R2025a.slx, got {ref_model}")
        if not scenario_dict.get('electrical_model', {}).get('model_unchanged', False):
            raise ValueError("model_unchanged must be true.")

    def load_all_definitions(self) -> None:
        """Loads all scenario JSON files in definitions_dir."""
        self.loaded_scenarios.clear()
        for fname in os.listdir(self.definitions_dir):
            if fname.endswith('.json'):
                path = os.path.join(self.definitions_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        scen = json.load(f)
                    self.validate_scenario(scen)
                    self.loaded_scenarios[scen['scenario_id']] = scen
                except Exception as e:
                    print(f"[Warning] Failed to load scenario from {fname}: {e}")

    def register_scenario(self, scenario_dict: Dict[str, Any], save_to_disk: bool = True) -> None:
        """Registers a new scenario, validates it, and optionally saves to disk."""
        self.validate_scenario(scenario_dict)
        scen_id = scenario_dict['scenario_id']
        self.loaded_scenarios[scen_id] = scenario_dict
        if save_to_disk:
            fpath = os.path.join(self.definitions_dir, f"{scen_id}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(scenario_dict, f, indent=2)

    def select_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Selects and activates a scenario by its unique identifier."""
        if scenario_id not in self.loaded_scenarios:
            raise KeyError(f"Scenario '{scenario_id}' not found in loaded definitions.")
        verify_pristine_model_integrity()
        self.active_scenario = self.loaded_scenarios[scenario_id]
        self.enabled = True
        return self.active_scenario

    def disable(self) -> None:
        """Disables disturbance injection, returning to normal operation."""
        self.enabled = False
        self.active_scenario = None

    def get_active_scenario(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active scenario if enabled."""
        if not self.enabled:
            return None
        return self.active_scenario

    @property
    def ground_truth_label(self) -> str:
        """
        Ground-truth class label. Exclusively originates from active scenario.
        Defaults to 'Normal' when disabled.
        """
        if not self.enabled or self.active_scenario is None:
            return 'Normal'
        return self.active_scenario['class']

    @property
    def ground_truth_label_idx(self) -> int:
        """
        Ground-truth label index.
        """
        if not self.enabled or self.active_scenario is None:
            return CLASS_TO_IDX['Normal']
        return self.active_scenario['label_idx']

    def list_scenarios(self, class_filter: Optional[str] = None) -> List[str]:
        """Lists available scenario IDs, optionally filtered by class."""
        if class_filter is None:
            return list(self.loaded_scenarios.keys())
        return [
            s_id for s_id, s in self.loaded_scenarios.items()
            if s.get('class') == class_filter
        ]

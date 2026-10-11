# REPRODUCING PHASE 4: 60 Hz IEEE 9-BUS ML TRAINING & EVALUATION

**Document Reference**: `docs/REPRODUCING_PHASE4.md`
**Applicability**: Phase 4A (Dataset Freeze), Phase 4B (Model Comparison), Phase 4C (MLP Tuning), Phase 4D (Locked Test Evaluation)
**Last Verified**: October 11, 2026

---

## 1. Overview

This guide documents the exact, verified steps required to replicate and audit all Phase 4 machine learning results on a clean computer using the artifacts committed to this repository.

All datasets, feature vectors, scalers, and trained models are committed directly to the repository. **MATLAB / Simulink is NOT required to reproduce ML training, baseline comparisons, tuning, or test evaluations.** MATLAB is only required if regenerating raw physical waveforms from scratch.

---

## 2. Software Environment & Dependencies

### 2.1 Verified Python Environment
- **Python Version**: Python 3.10+ (Verified on Python 3.14.2 64-bit on Windows; compatible with Linux / macOS)
- **Verified Package Versions**:
  - `numpy >= 2.0.0` (verified with `2.4.6` / `2.5.4`)
  - `scipy >= 1.14.0` (verified with `1.17.1` / `1.18.1`)
  - `pandas >= 2.2.0` (verified with `3.0.3` / `3.0.6`)
  - `scikit-learn >= 1.5.0` (verified with `1.9.0` / `1.9.1`)
  - `pytest >= 8.0.0` (verified with `8.2.2` / `9.1.1`)
  - `jsonschema >= 4.20.0` (verified with `4.26.0`, required for scenario schemas)
  - `requests >= 2.31.0` (verified with `2.34.2`, required for server telemetry)
  - `matplotlib >= 3.8.0` (verified with `3.11.2`, required for waveform plotting)

### 2.2 Installation
In a standard Python environment or virtual environment:

```bash
pip install numpy scipy pandas scikit-learn pytest jsonschema requests matplotlib
```

---

## 3. Cryptographic Baseline & Integrity Verification

To verify that the dataset manifest, reference Simulink model, and legacy models have not been modified or corrupted:

```bash
python scripts/verify_dataset_freeze.py
```

### Expected Output
```
================================================================================
PHASE 4A — DATASET FREEZE & INTEGRITY VERIFICATION AUDIT
================================================================================
[PASS] Pristine Simulink model verified intact (5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D)
...
[PASS] Zero trajectory leakage across all 8 classes
================================================================================
[SUCCESS] ALL PHASE 4A INTEGRITY & LEAKAGE AUDITS PASSED — DATASET IS FROZEN
```

### Key Reference Hashes (SHA-256)
- **Dataset Manifest (`data/ieee9bus_60hz/dataset_manifest_v1.json`)**:
  `B4C7CCA746B69EE895BC6E7C68F2BE2F56700F3B9C1976BF0B674C4D292548F5`
- **Pristine Reference Simulink (`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`)**:
  `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D`
- **Legacy 50 Hz Model (`ml/models/model_weights_32.json`)**:
  `BE9BDBC3641F6C2F667F65D32BA2DA90B244F0912F78A253221503E70BBAAB72`

---

## 4. Reproducing Machine Learning Experiments

### 4.1 Phase 4B: Baseline Model Comparison
To benchmark the five baseline classifiers (Logistic Regression, MLP, SVM-RBF, Random Forest, Gradient Boosting) on the training/validation splits:

```bash
python experiments/phase4b/run_comparison.py
```
- **Outputs generated**: `experiments/phase4b/baseline_comparison_summary.json`, `experiments/phase4b/models/*.pkl`
- **Primary Report**: [`docs/GATE4B_BASELINE_MODEL_COMPARISON.md`](GATE4B_BASELINE_MODEL_COMPARISON.md)

### 4.2 Phase 4C: MLP Hyperparameter Tuning & Boundary Optimization
To re-run the 54-experiment matrix (3 architectures $\times$ 2 solvers $\times$ 3 regularizers $\times$ 3 random seeds):

```bash
python experiments/phase4c/run_phase4c_experiments.py
```
- **Outputs generated**: `experiments/phase4c/models/candidate_mlp_weights.json`, `experiments/phase4c/phase4c_tuning_results.json`
- **Primary Report**: [`docs/GATE4C_MLP_TUNING_AUDIT.md`](GATE4C_MLP_TUNING_AUDIT.md)

### 4.3 Phase 4D: Locked Test Partition Evaluation
To execute the one-time evaluation of the frozen candidate model on the 1,295-frame test partition:

```bash
python experiments/phase4d/run_phase4d_evaluation.py
```
- **Outputs generated**: `experiments/phase4d/test_metrics.json`, `experiments/phase4d/test_predictions.csv`, `experiments/phase4d/confusion_matrix.csv`, `experiments/phase4d/trajectory_metrics.json`
- **Primary Report**: [`docs/GATE4D_LOCKED_TEST_EVALUATION.md`](GATE4D_LOCKED_TEST_EVALUATION.md)

---

## 5. Running the Complete Automated Test Suite

To run all unit, integration, physical validation, and Phase 4 gate tests:

```bash
pytest -q
```

### Expected Result
```
316 passed, 2 skipped, 2 warnings in ~8.5s
```
*(2 skipped tests correspond to optional CUDA acceleration checks on CPU machines).*

To run specifically the Phase 4 gate verification tests:

```bash
pytest tests/test_phase4c_mlp.py tests/test_phase4d_test_eval.py -v
```

---

## 6. Simulation Workflows (Optional — MATLAB / Simulink)

If modifying electrical disturbance physics or regenerating continuous simulation trajectories:
- **Required Version**: MATLAB R2024b or R2025a
- **Required Toolboxes**: Simulink, Simscape, Simscape Electrical (Specialized Power Systems)
- **Primary Model**: `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`
- **Generation Script**: `scripts/generate_ieee9bus_transient_dataset.m`

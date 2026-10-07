# Machine Learning Readiness & Phase 4 Preparation

**Document Reference**: `docs/ML_READINESS.md`  
**Date**: October 7, 2026  
**Status**: ACTIVE / MANDATORY PROTOCOL  
**Current State**: Phase 3 Complete / Phase 4 Machine Learning Training **PENDING**  
**Prohibition**: **DO NOT TRAIN OR RETRAIN ANY MACHINE LEARNING MODEL IN THIS TASK**  

---

## 1. Current Legacy Model Status

The repository currently maintains a legacy neural network model located at:
`ml/models/model_weights_32.json`

### Legacy Model Specifications:
- **Architecture**: Multi-Layer Perceptron (MLP: 32 $\rightarrow$ 64 $\rightarrow$ 32 $\rightarrow$ 8, FP32).
- **Historical Origin**: EXP-003 trained on early 50-Hz synthetic single-phase datasets.
- **Current Operating Domain**: **`OUT_OF_DOMAIN`** when evaluated on native 60-Hz IEEE 9-bus WSCC transmission waveforms.
- **Frozen Status**: **STRICTLY IMMUTABLE**. Model weights, layer biases, and scaler parameters are byte-frozen.

### Ground-Truth Decoupling Rule:
Under no circumstances may the predictions, output probabilities, or uncertainty flags of the legacy model be used as dataset ground truth or validation criteria:
- **Ground truth source**: Strictly `SCENARIO_CONTROLLER`.
- **Legacy model role**: Informational diagnostic observer only.

---

## 2. Phase 4 Machine Learning Execution Plan

When Phase 4 commences, neural network training will proceed through a strict 10-step protocol:

```
┌────────────────────────────────────────────────────────┐
│  Step 1: Final Dataset Freeze & Checksum Lock          │
│  • Verify SHA-256 hashes across all 8 classes          │
│  • Lock 9,216 total frames (1,152 per class)           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 2: Trajectory-Grouped Partitioning               │
│  • Train: 6,656 frames (26 trajectories x 8 classes)   │
│  • Validation: 1,280 frames (5 trajectories x 8 classes)│
│  • Test: 1,280 frames (5 trajectories x 8 classes)     │
│  • Assert zero trajectory overlap across splits        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 3: Train-Only Scaler Fitting                     │
│  • Fit StandardScaler strictly on the 6,656 train rows │
│  • Apply learned transform to Val and Test (0 leakage) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 4: Multi-Model Baseline Comparison               │
│  • Baseline 1: Logistic Regression / Ridge             │
│  • Baseline 2: Random Forest (100 estimators)          │
│  • Candidate 1: Compact MLP (32->64->32->8)            │
│  • Candidate 2: 1D-CNN (raw waveform input)            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 5: Native 60-Hz MLP Training                     │
│  • PyTorch training with cross-entropy loss            │
│  • Adam optimizer with cosine annealing learning rate  │
│  • Early stopping based on validation loss             │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 6: Hyperparameter Selection & Validation Tuning  │
│  • Tune learning rate, batch size, L2 weight decay     │
│  • Evaluate validation accuracy, macro F1, and loss    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 7: Model Calibration & Uncertainty Tuning        │
│  • Platt scaling / temperature scaling optimization    │
│  • Tune UNCERTAIN confidence threshold (default: 60%)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 8: Independent Held-Out Test Evaluation          │
│  • Final inference on isolated 1,280 test frames       │
│  • Per-class precision, recall, F1, confusion matrix   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 9: Model Artifact Generation & Export            │
│  • Export model_weights_32.json (JSON format)          │
│  • Export firmware/src/model_weights_32.h (C++ arrays) │
│  • Export TFLite Micro flatbuffer (if required)        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Step 10: Regression Verification & Firmware Parity    │
│  • Validate numerical output parity between Python,    │
│    C++ firmware simulation, and REST server endpoints  │
└────────────────────────────────────────────────────────┘
```

---

## 3. Mandatory Phase 4 Success Criteria

1. **Test Set Accuracy**: Overall accuracy $\ge 98.0\%$ across all 8 classes on the held-out test split.
2. **Per-Class Recall**: Minimum recall $\ge 95.0\%$ for every individual disturbance class (Normal, Sag, Swell, Interruption, Harmonics, Flicker, Notch, Transient).
3. **Confusion Matrix Isolation**: Zero confusion between Interruption and Sag, and zero confusion between Harmonics and Transient.
4. **Firmware Parity**: Absolute difference between Python forward pass and C++ embedded forward pass $< 10^{-5}$ across all test vectors.
5. **Inference Latency**: Embedded execution time on ESP32 $\le 35\,\text{ms}$ per 3-phase frame.

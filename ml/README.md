# Machine Learning (ML) Subsystem Guide

**Subsystem:** Machine Learning Classification & Model Artifacts  
**Current Phase:** Pre-Phase 4 Maintenance (Legacy Weights Frozen)  
**Next Engineering Phase:** Phase 4 — Proper 60-Hz Machine Learning Training  
**Authoritative Protocol:** [docs/ML_READINESS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ML_READINESS.md)  

---

## 1. Current Machine Learning Status

> [!IMPORTANT]
> **Model Freeze & Domain Mismatch Notice:** The current weights in `ml/models/model_weights_32.json` were trained on an early 50-Hz synthetic dataset and remain **globally frozen**. When presented with 60-Hz IEEE 9-bus transmission data, the runtime pipeline correctly reports `model_domain_status: 'MODEL_DOMAIN_MISMATCH'`, allowing the independent physical rule engine (`dsp/standards_detector.py`) to maintain 100% classification integrity.
> 
> **No machine learning models will be retrained during Phase 3 maintenance.** Retraining is scheduled for Phase 4.

---

## 2. Model Directory & Artifact Structure

```
ml/
├── README.md                      # Machine Learning subsystem overview
├── compare_models.py              # Legacy multi-model benchmark script (MLP, RF, SVM, KNN)
├── convert_tflite.py              # TFLite quantization & C-header exporter
├── generate_dataset.py            # Historical synthetic feature generator
├── run_diagnostics.py             # Historical 12-phase diagnostic evaluation
│
└── models/
    ├── model_weights_32.json      # CURRENT 32-feature weights (FROZEN pending Phase 4)
    │                              # SHA-256: BE9BDBC3641F6C2F667F65D32BA2DA90B244F0912F78A253221503E70BBAAB72
    ├── mlp_deployed.h5            # Historical 8-feature Keras model
    ├── mlp_deployed.tflite        # Historical 8-feature Int8 quantized model
    ├── scaler.pkl                 # Historical 8-feature StandardScaler
    ├── label_encoder.pkl          # Historical 8-class LabelEncoder
    └── model_weights.json         # Historical 8-feature browser JS weights
```

---

## 3. Phase 4 Retraining Protocol (Upcoming)

When Phase 4 commences, retraining will follow the strict 10-step protocol specified in [docs/ML_READINESS.md](file:///d:/my%20study/Project/power-quality-detector-and-classifier/docs/ML_READINESS.md):

1. **Dataset Freeze:** Lock all 8 audited datasets in `data/ieee9bus_60hz/` (9,216 total multi-phase frames across 256 trajectories).
2. **Trajectory-Grouped Splitting:** Partition by operating condition trajectory ($70\%\text{ train} / 15\%\text{ val} / 15\%\text{ test}$) with **zero inter-trajectory leakage**.
3. **Train-Only Scaler Fitting:** Compute `StandardScaler` ($\mu, \sigma$) strictly on training folds.
4. **Baseline Classical Benchmarking:** Train Random Forest, Extra Trees, and XGBoost baselines.
5. **60-Hz Neural Network (MLP) Training:** Train compact MLP architecture with early stopping and learning rate scheduling.
6. **Hyperparameter Selection:** Optimize hidden dimensions, dropout rates, and L2 regularization against validation F1-score.
7. **Independent Test Evaluation:** Evaluate on unseen test trajectories across all 8 disturbance classes.
8. **Reliability & Confidence Calibration:** Verify expected calibration error (ECE) and temperature scaling.
9. **Physical Decoupling Verification:** Verify that ML output remains isolated from physical protection trips.
10. **Deployment Export:** Export retrained weights to `ml/models/model_weights_32.json` and ONNX formats.

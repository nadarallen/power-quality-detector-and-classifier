# Data Leakage & Evaluation Integrity Audit
**Document Version:** 1.0.0  
**Audit Date:** 2026-09-19  
**Target:** Data Pipeline, Preprocessing, Splitting, and Feature Extraction

---

## 1. Executive Summary

This audit assesses the PQD classification pipeline for data leakage across four key vectors:
1. **Preprocessing & Scaling Leakage** (fitting scalers on test data)
2. **Instance / Duplicate Leakage** (identical or near-identical instances crossing splits)
3. **Target / Feature Leakage** (features inadvertently containing the ground truth label)
4. **Validation Strategy Leakage** (test set overfitting / multi-testing bias)

---

## 2. Preprocessing & Scaling Isolation Check

### Current Implementation in `ml/compare_models.py`:
```python
# 1. 80/20 Stratified Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=SEED, stratify=y
)

# 2. Feature Standardization
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

### Audit Findings:
- ✅ **Properly Isolated:** `scaler.fit_transform()` is invoked **strictly on `X_train`**. `X_test` is transformed using `scaler.transform()` without recomputing $\mu$ or $\sigma$.
- ✅ **No Global Scaling:** `data/pqd_features.csv` stores unscaled raw physical units (pu, %, ms, Hz, dB). Preprocessing parameters were not leaked prior to splitting.
- ✅ **Label Encoder:** `LabelEncoder` maps string class names to integer indices $(0..7)$ deterministically without target value leakage.

---

## 3. Instance & Duplicate Leakage Check

### Audit Findings:
- **Full Row Duplicates:** Exactly **0** duplicate rows exist in `Dataset/BARC DATA.csv`.
- **Feature Vector Duplicates:** Exactly **0** duplicate 8D feature vectors exist.
- **Train/Test Overlap:** Across the 8,000 train instances and 2,000 test instances, the intersection of feature vectors is **0**.
- **Near-Duplicate Cross-Contamination:** Out of 2 million pairwise comparisons among random samples, only 18 pairs had normalized Euclidean distance $< 0.05$. Cross-split near-duplicate leakage is negligible ($< 0.001\%$).

---

## 4. Target & Feature Leakage Check

### Audit Findings:
- **`Duration_ms = 5.0 ms` for Transients:**
  - In `Dataset/BARC DATA.csv`, all 985 Transient instances have an exact duration of `5.0 ms`.
  - No other class has a duration of `5.0 ms` (other classes have either `0.0 ms` or $\ge 20.0\text{ ms}$).
  - *Risk:* This represents synthetic generation leakage. While not a direct copy of the label string, it functions as a near-perfect surrogate indicator for the `Transient` class.
- **`Dominant_Freq_Hz = 50.0 Hz`:**
  - Constant for all samples. Zero variance. No leakage, but completely uninformative.

---

## 5. Evaluation Protocol & Split Vulnerability

### Current Vulnerability:
The current repository relies on a **single 80/20 train/test split**:
- **No Locked Final Test Set:** All 5 models in `ml/compare_models.py` were evaluated against the same 20% test set (`2,000 samples`).
- **Absence of a Validation Split:** Hyperparameter decisions (such as MLP layer sizes 64 and 32, epochs = 40, batch size = 32) and model selection decisions were judged directly on the test set.
- **Optimistic Bias:** When the test set is repeatedly used to select the "best" model or tune thresholds, its performance estimate becomes optimistically biased.

### Corrective Action for Phase 5:
Lock a permanent, untouched **3-way split**:
- **70% Training (`7,000 samples`)** — for fitting models and estimators.
- **15% Validation (`1,500 samples`)** — for hyperparameter optimization, threshold tuning, and architecture comparisons.
- **15% Final Test (`1,500 samples`)** — completely locked and evaluated **only once** for the final report.

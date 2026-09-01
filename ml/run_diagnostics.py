"""
Power Quality Disturbance (PQD) Classifier — Comprehensive ML & Dataset Diagnostic Suite
-----------------------------------------------------------------------------------------
Executes deep diagnostic analysis across dataset quality, feature distributions,
separability, model benchmarking, and simulation feature compatibility.
"""

import os
import sys
import pickle
import json
import numpy as np
import pandas as pd

# Load sklearn & tensorflow
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.decomposition import PCA

import tensorflow as tf

SEED = 42
np.random.seed(SEED)

STANDARD_FEATURES = [
    'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
    'duration', 'dominant_freq', 'system_freq', 'snr'
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARC_PATH = os.path.join(BASE_DIR, 'Dataset', 'BARC DATA.csv')
FEATURES_PATH = os.path.join(BASE_DIR, 'data', 'pqd_features.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'ml', 'models')

def run_diagnostics():
    print("=" * 80)
    print("      PQD CLASSIFIER & DATASET SCIENTIFIC DIAGNOSTIC SUITE      ")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. DATASET ANALYSIS & QUALITY CHECK
    # -------------------------------------------------------------------------
    print("\n--- 1. DATASET ANALYSIS & QUALITY CHECK ---")
    if not os.path.exists(BARC_PATH):
        print(f"Error: BARC DATA.csv not found at {BARC_PATH}")
        return

    df_raw = pd.read_csv(BARC_PATH)
    print(f"Total Recorded Samples in BARC DATA.csv : {len(df_raw)}")
    print(f"Columns present                         : {list(df_raw.columns)}")
    print(f"Null values count                       : {df_raw.isnull().sum().sum()}")
    print(f"Duplicate rows count                    : {df_raw.duplicated().sum()}")

    # Normalize column names & label column
    column_map = {
        'V_rms_pu': 'rms_voltage', 'V_peak_pu': 'peak_voltage',
        'Crest_Factor': 'crest_factor', 'THD_percent': 'thd',
        'Duration_ms': 'duration', 'Dominant_Freq_Hz': 'dominant_freq',
        'Freq_Hz': 'system_freq', 'SNR_dB': 'snr', 'Label': 'label'
    }
    df = df_raw.rename(columns=column_map)
    df['label'] = df['label'].astype(str).str.strip()

    class_counts = df['label'].value_counts()
    print("\n[Class Distribution]")
    for cls, cnt in class_counts.items():
        pct = (cnt / len(df)) * 100.0
        print(f"  - {cls:<15}: {cnt:>5} samples ({pct:>5.2f}%)")

    # -------------------------------------------------------------------------
    # 2. FEATURE ORDER, SCALER, AND LABEL ENCODER VERIFICATION
    # -------------------------------------------------------------------------
    print("\n--- 2. ML PIPELINE & PREPROCESSING VERIFICATION ---")
    le_path = os.path.join(MODEL_DIR, 'label_encoder.pkl')
    sc_path = os.path.join(MODEL_DIR, 'scaler.pkl')

    with open(le_path, 'rb') as f:
        label_encoder = pickle.load(f)
    with open(sc_path, 'rb') as f:
        scaler = pickle.load(f)

    print(f"LabelEncoder Trained Classes ({len(label_encoder.classes_)}): {list(label_encoder.classes_)}")
    print("StandardScaler Feature Means:")
    for feat, m, s in zip(STANDARD_FEATURES, scaler.mean_, scaler.scale_):
        print(f"  - {feat:<15}: mean = {m:>10.6f}, scale = {s:>10.6f}")

    # -------------------------------------------------------------------------
    # 3. FEATURE SEPARABILITY & CORRELATION ANALYSIS
    # -------------------------------------------------------------------------
    print("\n--- 3. FEATURE SEPARABILITY & IMPORTANCE ---")
    X = df[STANDARD_FEATURES].values
    y = label_encoder.transform(df['label'].values)

    # Feature Importance via Random Forest
    rf_temp = RandomForestClassifier(n_estimators=100, random_state=SEED)
    rf_temp.fit(X, y)
    print("[Random Forest Feature Importances]")
    for feat, imp in zip(STANDARD_FEATURES, rf_temp.feature_importances_):
        print(f"  - {feat:<15}: {imp * 100:>6.2f}%")

    # PCA Analysis
    pca = PCA(n_components=4)
    pca.fit(scaler.transform(X))
    exp_var = pca.explained_variance_ratio_
    print(f"PCA Variance Explained (Top 4 components): {np.round(exp_var * 100, 2)}% | Total 4-comp: {np.sum(exp_var)*100:.2f}%")

    # -------------------------------------------------------------------------
    # 4. STATISTICAL PROFILES PER CLASS (BARC REAL DATASET)
    # -------------------------------------------------------------------------
    print("\n--- 4. REAL BARC DATASET FEATURE STATISTICAL PROFILES PER CLASS ---")
    class_stats = {}
    for cls in label_encoder.classes_:
        sub_df = df[df['label'] == cls][STANDARD_FEATURES]
        class_stats[cls] = {
            'mean': sub_df.mean().to_dict(),
            'std': sub_df.std().to_dict(),
            'min': sub_df.min().to_dict(),
            'max': sub_df.max().to_dict()
        }
        print(f"\n[Class: {cls.upper()}] (n={len(sub_df)})")
        print(f"  Feature          Mean        Std         Min         Max")
        for feat in STANDARD_FEATURES:
            m = sub_df[feat].mean()
            s = sub_df[feat].std()
            mn = sub_df[feat].min()
            mx = sub_df[feat].max()
            print(f"  {feat:<15} {m:>10.3f}  {s:>10.3f}  {mn:>10.3f}  {mx:>10.3f}")

    # -------------------------------------------------------------------------
    # 5. REAL DATASET MODEL BENCHMARKING (80/20 STRATIFIED TEST SET)
    # -------------------------------------------------------------------------
    print("\n--- 5. EVALUATION OF DEPLOYED MODEL ON REAL TEST DATASET ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )
    X_test_scaled = scaler.transform(X_test)

    model_h5_path = os.path.join(MODEL_DIR, 'mlp_deployed.h5')
    keras_model = tf.keras.models.load_model(model_h5_path)
    
    y_probs = keras_model.predict(X_test_scaled, verbose=0)
    y_pred = np.argmax(y_probs, axis=1)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)

    print(f"\n[REAL TEST SET RESULTS — Compact Keras MLP]")
    print(f"Overall Accuracy : {acc * 100:.2f}%")
    print(f"Macro F1 Score   : {macro_f1:.4f}")
    print("\nPer-Class Detailed Metrics:")
    print(f"  {'Class':<15} {'Precision':<10} {'Recall':<10} {'F1-Score':<10}")
    for idx, cls in enumerate(label_encoder.classes_):
        print(f"  {cls:<15} {prec[idx]:<10.4f} {rec[idx]:<10.4f} {f1[idx]:<10.4f}")

    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix on Real Test Set:")
    print(f"{'True \\ Pred':<12}", end="")
    for cls in label_encoder.classes_:
        print(f"{cls[:4]:>6}", end="")
    print()
    for i, true_cls in enumerate(label_encoder.classes_):
        print(f"{true_cls:<12}", end="")
        for j in range(len(label_encoder.classes_)):
            print(f"{cm[i, j]:>6}", end="")
        print()

    # -------------------------------------------------------------------------
    # 6. SIMULATION-GENERATED WAVEFORM VS BARC TRAINING FEATURE COMPARISON
    # -------------------------------------------------------------------------
    print("\n--- 6. SIMULATION FEATURE VECTOR VS BARC DATASET DISTRIBUTION COMPARISON ---")

    # Define the exact simulated feature vectors generated by waveform / web app DSP
    simulated_cases = {
        'Normal': [0.998, 1.412, 1.415, 0.82, 0.0, 50.0, 50.0, 44.8],
        'Sag': [0.354, 0.507, 1.432, 0.06, 200.0, 50.0, 50.0, 42.1],
        'Swell': [1.025, 1.457, 1.421, 0.03, 200.0, 50.0, 50.0, 40.5],
        'Harmonics': [0.745, 0.841, 1.129, 33.20, 200.0, 150.0, 50.0, 32.4],
        'Interruption': [0.029, 0.047, 1.620, 0.88, 200.0, 50.0, 50.0, 15.2],
        'Transient': [1.120, 2.350, 2.098, 4.20, 5.0, 500.0, 50.0, 36.8],
        'Flicker': [0.985, 1.460, 1.482, 2.10, 120.0, 50.0, 50.0, 38.5],
        'Notch': [0.970, 1.420, 1.464, 6.80, 15.0, 50.0, 50.0, 34.1]
    }

    print("\nComparing Simulated Injection Feature Vectors against BARC Dataset Distribution Bounds:")
    for sim_cls, sim_vec in simulated_cases.items():
        if sim_cls not in class_stats:
            continue
        print(f"\n[INJECTED CLASS: {sim_cls.upper()}]")
        
        # Run ML model on this simulated vector
        sim_vec_scaled = scaler.transform([sim_vec])
        probs = keras_model.predict(sim_vec_scaled, verbose=0)[0]
        pred_idx = np.argmax(probs)
        pred_cls = label_encoder.classes_[pred_idx]
        conf = probs[pred_idx]

        print(f"  --> ML Model Prediction : {pred_cls.upper()} (Confidence: {conf*100:.1f}%)")
        print(f"  --> Result              : {'CORRECT' if pred_cls == sim_cls else 'MISCLASSIFIED'}")
        
        print(f"  Feature-by-Feature Distribution Audit vs BARC Real Training Data:")
        print(f"  {'Feature':<15} {'Sim Value':<10} {'BARC Mean':<10} {'BARC [Min, Max]':<20} {'Z-Score':<10} {'Status':<15}")
        
        stats = class_stats[sim_cls]
        for idx, feat in enumerate(STANDARD_FEATURES):
            val = sim_vec[idx]
            m = stats['mean'][feat]
            s = stats['std'][feat] if stats['std'][feat] > 1e-6 else 1.0
            mn = stats['min'][feat]
            mx = stats['max'][feat]
            z_score = (val - m) / s

            status = "IN RANGE"
            if val < mn or val > mx:
                status = "OUT OF BOUNDS"
            elif abs(z_score) > 2.5:
                status = "OUT OF DIST"

            print(f"  {feat:<15} {val:<10.3f} {m:<10.3f} [{mn:>7.3f}, {mx:>7.3f}] {z_score:<10.2f} {status:<15}")

    print("\n" + "=" * 80)
    print("                      DIAGNOSTIC SUITE COMPLETE                         ")
    print("=" * 80)

if __name__ == '__main__':
    run_diagnostics()

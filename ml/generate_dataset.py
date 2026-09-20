"""
Power Quality Disturbance (PQD) Dataset Loader & Standardizer
--------------------------------------------------------------
Processes the dataset BARC DATA.csv (D:\\Major proj\\Dataset\\BARC DATA.csv)
without any synthetic data generation.

Feature Extraction Vector (8 Features):
1. rms_voltage     (V_rms_pu)       - Root Mean Square voltage in per-unit
2. peak_voltage    (V_peak_pu)      - Peak voltage magnitude in per-unit
3. crest_factor    (Crest_Factor)   - Ratio of peak to RMS voltage
4. thd             (THD_percent)    - Total Harmonic Distortion (%)
5. duration        (Duration_ms)    - Duration of disturbance in milliseconds
6. dominant_freq   (Dominant_Freq_Hz)- Dominant spectral frequency (Hz)
7. system_freq     (Freq_Hz)        - System fundamental frequency (Hz)
8. snr             (SNR_dB)         - Signal-to-Noise Ratio in dB
"""

import os
import argparse
import pandas as pd

# Standard feature column names
STANDARD_FEATURES = [
    'rms_voltage',
    'peak_voltage',
    'crest_factor',
    'thd',
    'duration',
    'dominant_freq',
    'system_freq',
    'snr'
]

# Column mapping from BARC DATA.csv schema to standard names
BARC_COLUMN_MAP = {
    'V_rms_pu': 'rms_voltage',
    'V_peak_pu': 'peak_voltage',
    'Crest_Factor': 'crest_factor',
    'THD_percent': 'thd',
    'Duration_ms': 'duration',
    'Dominant_Freq_Hz': 'dominant_freq',
    'Freq_Hz': 'system_freq',
    'SNR_dB': 'snr',
    'Label': 'label'
}


def load_and_prepare_barc_dataset(csv_path: str) -> pd.DataFrame:
    """
    Loads BARC DATA.csv, validates columns, maps headers to standardized names,
    and returns a cleaned DataFrame.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Real dataset file not found at: {csv_path}")

    print(f"[BARC Dataset Loader] Reading real dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Validate BARC columns
    for barc_col in BARC_COLUMN_MAP.keys():
        if barc_col not in df.columns:
            raise ValueError(f"Missing expected column '{barc_col}' in BARC DATA dataset.")

    # Select and rename columns to standard schema
    df_clean = df[list(BARC_COLUMN_MAP.keys())].rename(columns=BARC_COLUMN_MAP)
    
    # Clean label string formatting
    df_clean['label'] = df_clean['label'].astype(str).str.strip()

    print(f"[BARC Dataset Loader] Successfully loaded {len(df_clean)} real dataset rows.")
    print(f"[BARC Dataset Loader] Disturbance Class Distribution:\n{df_clean['label'].value_counts()}")
    return df_clean


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_input = os.path.join(base_dir, "Dataset", "BARC DATA.csv")
    default_output = os.path.join(base_dir, "data", "pqd_features.csv")

    parser = argparse.ArgumentParser(description="BARC PQD Dataset Loader")
    parser.add_argument("--input", type=str, default=default_input,
                        help="Path to input BARC DATA.csv dataset")
    parser.add_argument("--output", type=str, default=default_output,
                        help="Path to output standardized feature CSV")
    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    df = load_and_prepare_barc_dataset(args.input)
    df.to_csv(args.output, index=False)
    print(f"[Success] Real BARC dataset standardized and saved to: {args.output}")


if __name__ == "__main__":
    main()

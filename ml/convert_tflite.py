"""
TFLite Micro Model Conversion Script (Track A -> Track B Bridge)
----------------------------------------------------------------
Converts the trained compact MLP deployment model (ml/models/mlp_deployed.h5 or mlp_deployed.pkl)
to an int8 / float32 quantized TFLite flatbuffer and exports it as a C byte array header
file for ESP32 TFLite Micro runtime deployment (firmware/src/model_data.h).
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd

STANDARD_FEATURES = [
    'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
    'duration', 'dominant_freq', 'system_freq', 'snr'
]

# Check TensorFlow availability
HAS_TF = False
try:
    import tensorflow as tf
    HAS_TF = True
except ImportError:
    HAS_TF = False


def export_c_header(tflite_bytes: bytes, output_header_path: str):
    """
    Converts raw tflite model bytes into a C array header file.
    """
    os.makedirs(os.path.dirname(output_header_path), exist_ok=True)
    
    array_name = "g_model"
    len_name = "g_model_len"

    bytes_per_line = 12
    hex_bytes = [f"0x{b:02x}" for b in tflite_bytes]
    lines = []
    for i in range(0, len(hex_bytes), bytes_per_line):
        lines.append("  " + ", ".join(hex_bytes[i:i + bytes_per_line]))

    c_content = f"""// Auto-generated TFLite Micro model header for ESP32 firmware.
// DO NOT HAND-EDIT THIS FILE. Regenerate using ml/convert_tflite.py.

#ifndef MODEL_DATA_H_
#define MODEL_DATA_H_

#include <cstdint>

alignas(16) const unsigned char {array_name}[] = {{
{",\n".join(lines)}
}};

const unsigned int {len_name} = {len(tflite_bytes)};

#endif  // MODEL_DATA_H_
"""
    with open(output_header_path, "w") as f:
        f.write(c_content)
    
    print(f"[C Header Exporter] Successfully generated C header: {output_header_path}")


def convert_keras_to_tflite(h5_path: str, data_path: str, header_out: str, tflite_out: str):
    """
    Converts Keras H5 MLP model to quantized TFLite model and C header.
    """
    print(f"[TFLite Converter] Loading Keras model from: {h5_path}")
    model = tf.keras.models.load_model(h5_path)

    # Load representative dataset for int8 quantization
    df = pd.read_csv(data_path)
    X = df[STANDARD_FEATURES].values.astype(np.float32)

    scaler_path = os.path.join(os.path.dirname(h5_path), "scaler.pkl")
    if os.path.exists(scaler_path):
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
            X = scaler.transform(X).astype(np.float32)

    def representative_dataset_gen():
        for i in range(min(500, len(X))):
            yield [X[i:i+1]]

    # Converter setup
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset_gen
    
    try:
        tflite_model_bytes = converter.convert()
    except Exception as e:
        print(f"[Warning] Full int8 quantization fallback to standard float conversion: {e}")
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        tflite_model_bytes = converter.convert()

    # Save .tflite file
    with open(tflite_out, "wb") as f:
        f.write(tflite_model_bytes)

    tflite_size_kb = len(tflite_model_bytes) / 1024.0
    h5_size_kb = os.path.getsize(h5_path) / 1024.0

    print(f"\n==========================================================")
    print(f"       TFLITE CONVERSION REPORT       ")
    print(f"==========================================================")
    print(f"Original Keras H5 Size : {h5_size_kb:.2f} KB")
    print(f"Quantized TFLite Size  : {tflite_size_kb:.2f} KB")
    print(f"Footprint Reduction    : {(1 - tflite_size_kb/h5_size_kb)*100:.1f}%")
    print(f"TFLite Output Path     : {tflite_out}")
    print(f"==========================================================\n")

    # Export C Header
    export_c_header(tflite_model_bytes, header_out)


def convert_pickle_mlp_to_header(pkl_path: str, header_out: str):
    """
    Fallback C header exporter for Sklearn MLP model weights when TF/Keras is unavailable.
    """
    print(f"[MLP Weights Exporter] Exporting Sklearn MLP weights from: {pkl_path}")
    with open(pkl_path, "rb") as f:
        clf = pickle.load(f)

    # Flatten weights & biases into bytes
    weights_bytes = bytearray()
    for w in clf.coefs_:
        weights_bytes.extend(w.astype(np.float32).tobytes())
    for b in clf.intercepts_:
        weights_bytes.extend(b.astype(np.float32).tobytes())

    export_c_header(bytes(weights_bytes), header_out)


def main():
    h5_model = r"D:\Major proj\ml\models\mlp_deployed.h5"
    pkl_model = r"D:\Major proj\ml\models\mlp_deployed.pkl"
    features_csv = r"D:\Major proj\data\pqd_features.csv"
    header_path = r"D:\Major proj\firmware\src\model_data.h"
    tflite_path = r"D:\Major proj\ml\models\mlp_deployed.tflite"

    if HAS_TF and os.path.exists(h5_model):
        convert_keras_to_tflite(h5_model, features_csv, header_path, tflite_path)
    elif os.path.exists(pkl_model):
        convert_pickle_mlp_to_header(pkl_model, header_path)
    else:
        print(f"[Error] Neither '{h5_model}' nor '{pkl_model}' exists. Run ml/compare_models.py first.")
        sys.exit(1)


if __name__ == "__main__":
    main()

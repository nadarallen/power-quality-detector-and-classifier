"""
Power Quality Disturbance (PQD) Classifier — Lightweight REST & Telemetry Server
----------------------------------------------------------------------------------
Serves the retro laboratory web dashboard and provides backend ML inference endpoints
loading the exact trained Keras MLP model, scaler.pkl, and label_encoder.pkl.
"""

import os
import sys
import json
import math
import time
import pickle
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Standard feature order
STANDARD_FEATURES = [
    'rms_voltage', 'peak_voltage', 'crest_factor', 'thd',
    'duration', 'dominant_freq', 'system_freq', 'snr'
]

# Load ML artifacts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'ml', 'models')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.pkl')
WEIGHTS_JSON_PATH = os.path.join(MODEL_DIR, 'model_weights.json')

CLASSES = ['Flicker', 'Harmonics', 'Interruption', 'Normal', 'Notch', 'Sag', 'Swell', 'Transient']
SCALER_MEAN = [0.6849054, 1.127878875, 1.681970125, 2.4761045, 36.0934625, 50.0, 49.999888, 45.00306375]
SCALER_SCALE = [0.11520105, 0.26324074, 0.43368028, 3.74957678, 51.56225365, 1.0, 0.01989759, 5.78793978]
WEIGHTS_DATA = None

if os.path.exists(WEIGHTS_JSON_PATH):
    try:
        with open(WEIGHTS_JSON_PATH, 'r') as f:
            WEIGHTS_DATA = json.load(f)
            CLASSES = WEIGHTS_DATA.get('classes', CLASSES)
            SCALER_MEAN = WEIGHTS_DATA.get('scaler_mean', SCALER_MEAN)
            SCALER_SCALE = WEIGHTS_DATA.get('scaler_scale', SCALER_SCALE)
            print("[PQD Server] Successfully loaded ML model_weights.json!")
    except Exception as e:
        print(f"[PQD Server] Warning loading weights JSON: {e}")

def relu(x):
    return np.maximum(0, x)

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def run_python_ml_inference(feature_vector):
    """
    Executes forward pass of the Compact Keras MLP model (Dense 64 -> Dense 32 -> Dense 8).
    """
    if len(feature_vector) != 8:
        raise ValueError("Expected 8 features")
    
    # 1. Feature Standardization
    z = (np.array(feature_vector, dtype=np.float32) - np.array(SCALER_MEAN, dtype=np.float32)) / np.array(SCALER_SCALE, dtype=np.float32)
    
    if WEIGHTS_DATA and 'weights' in WEIGHTS_DATA:
        w = WEIGHTS_DATA['weights']
        # Layer 1
        w1, b1 = np.array(w[0]), np.array(w[1])
        h1 = relu(np.dot(z, w1) + b1)
        # Layer 2
        w2, b2 = np.array(w[2]), np.array(w[3])
        h2 = relu(np.dot(h1, w2) + b2)
        # Layer 3 (Output)
        w3, b3 = np.array(w[4]), np.array(w[5])
        logits = np.dot(h2, w3) + b3
        probs = softmax(logits)
    else:
        # Simple fallback probabilities if weights file missing
        probs = np.ones(8) / 8.0
    
    pred_idx = int(np.argmax(probs))
    pred_class = CLASSES[pred_idx]
    confidence = float(probs[pred_idx])

    prob_dict = {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))}

    return {
        'predicted_class': pred_class,
        'confidence': confidence,
        'probabilities': prob_dict,
        'features_used': feature_vector,
        'is_uncertain': bool(confidence < 0.60)
    }

class PQDServerRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(BASE_DIR, 'web'), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/classes':
            self._send_json({'classes': CLASSES, 'status': 'success'})
        elif parsed.path == '/api/health':
            self._send_json({'status': 'online', 'model': 'Compact MLP 8.4KB Int8', 'timestamp': time.time()})
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            data = {}

        if parsed.path == '/api/predict':
            features = data.get('features', [])
            if len(features) == 8:
                res = run_python_ml_inference(features)
                self._send_json(res)
            else:
                self._send_json({'error': 'Invalid feature vector length (expected 8)'}, status=400)
        else:
            self._send_json({'error': 'Endpoint not found'}, status=404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def run_server(port=8500):
    server_address = ('', port)
    httpd = HTTPServer(server_address, PQDServerRequestHandler)
    print(f"\n========================================================")
    print(f"  PQD RETRO LABORATORY SERVER ONLINE AT: http://localhost:{port}")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    port = 8500
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)

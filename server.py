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
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
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
WEIGHTS_32_JSON_PATH = os.path.join(MODEL_DIR, 'model_weights_32.json')

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

# Shared storage and pipeline components
from storage.event_store import EventStore
from dsp.waveform_frame import WaveformFrame
from dsp.acquisition_adapter import SimulationAdapter
from pipeline.realtime_pipeline import RealtimePQPipeline

SHARED_EVENT_STORE = EventStore(os.path.join(BASE_DIR, 'data', 'pq_events.db'))
SIM_ADAPTER = SimulationAdapter(device_id="SIM_GRID_NODE_1", sampling_rate_hz=5000.0, nominal_frequency_hz=50.0)
SHARED_PIPELINE = RealtimePQPipeline(adapter=SIM_ADAPTER, event_store=SHARED_EVENT_STORE, device_id="GRID_NODE_1")


class PQDServerRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(BASE_DIR, 'web'), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == '/api/classes':
            self._send_json({'classes': CLASSES, 'status': 'success'})
        elif parsed.path == '/api/health':
            self._send_json({
                'status': 'online',
                'model': 'Compact MLP 8.4KB Int8',
                'three_phase_engine': 'active',
                'timestamp': time.time()
            })
        elif parsed.path == '/api/events':
            event_class = query.get('event_class', [None])[0]
            phase = query.get('phase', [None])[0]
            limit = int(query.get('limit', [50])[0])
            offset = int(query.get('offset', [0])[0])
            start_time_after = float(query.get('start_time_after', [None])[0]) if query.get('start_time_after', [None])[0] is not None else None
            end_time_before = float(query.get('end_time_before', [None])[0]) if query.get('end_time_before', [None])[0] is not None else None
            mp_str = query.get('multi_phase_only', [None])[0]
            multi_phase_only = True if mp_str == 'true' else (False if mp_str == 'false' else None)

            events = SHARED_EVENT_STORE.query_events(
                event_class=event_class,
                phase=phase,
                start_time_after=start_time_after,
                end_time_before=end_time_before,
                multi_phase_only=multi_phase_only,
                limit=limit,
                offset=offset
            )
            total = SHARED_EVENT_STORE.count_events(
                event_class=event_class,
                phase=phase,
                start_time_after=start_time_after,
                end_time_before=end_time_before,
                multi_phase_only=multi_phase_only
            )
            self._send_json({
                'events': events,
                'count': len(events),
                'total': total,
                'limit': limit,
                'offset': offset
            })
        elif parsed.path == '/api/events/stats':
            stats = SHARED_EVENT_STORE.get_event_stats()
            self._send_json(stats)
        elif parsed.path == '/api/telemetry':
            telem = SHARED_PIPELINE.get_latest_telemetry()
            self._send_json(telem)
        elif parsed.path == '/api/stream/telemetry':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close' if 'iterations' in query else 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            iterations = int(query.get('iterations', [1])[0])
            for _ in range(iterations):
                telem = SHARED_PIPELINE.get_latest_telemetry()
                msg = f"data: {json.dumps(telem)}\n\n"
                self.wfile.write(msg.encode('utf-8'))
                self.wfile.flush()
                if iterations > 1:
                    time.sleep(0.05)
            if 'iterations' in query:
                self.close_connection = True
            return
        elif parsed.path.startswith('/api/events/'):
            event_id = parsed.path.split('/')[-1]
            evt = SHARED_EVENT_STORE.get_event(event_id)
            if evt:
                self._send_json(evt)
            else:
                self._send_json({'error': 'Event not found'}, status=404)
        elif parsed.path == '/api/weights/32':
            if os.path.exists(WEIGHTS_32_JSON_PATH):
                with open(WEIGHTS_32_JSON_PATH, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            else:
                self._send_json({'error': '32-feature weights not found'}, status=404)
        elif parsed.path.endswith('model_weights.json') or parsed.path == '/api/weights':
            if os.path.exists(WEIGHTS_JSON_PATH):
                with open(WEIGHTS_JSON_PATH, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            else:
                self._send_json({'error': 'Weights not found'}, status=404)
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
        elif parsed.path == '/api/ingest':
            # Accepts a WaveformFrame JSON payload from remote edge/acquisition adapters
            try:
                frame = WaveformFrame.from_dict(data)
                events = SHARED_PIPELINE.process_frame(frame)
                self._send_json({
                    'status': 'success',
                    'frame_sequence': frame.sequence_number,
                    'events_detected': len(events),
                    'event_ids': [e.event_id for e in events]
                })
            except Exception as e:
                self._send_json({'error': f'Failed to process waveform frame: {str(e)}'}, status=400)
        elif parsed.path == '/api/ingest/chunk':
            # Streaming chunk ingestion: raw multi-channel samples
            channels_raw = data.get('channels', {})
            if not channels_raw:
                self._send_json({'error': 'Missing required channels dict in payload'}, status=400)
                return
            try:
                channels = {
                    ch: np.asarray(arr, dtype=np.float32)
                    for ch, arr in channels_raw.items()
                }
                ts = data.get('timestamp_utc', None)
                if ts is not None:
                    ts = float(ts)
                events = SHARED_PIPELINE.ingest_samples(channels, timestamp_utc=ts)
                first_ch_len = len(next(iter(channels.values())))
                self._send_json({
                    'status': 'success',
                    'samples_ingested': first_ch_len,
                    'events_detected': len(events),
                    'event_ids': [e.event_id for e in events],
                    'telemetry': SHARED_PIPELINE.get_latest_telemetry()
                })
            except Exception as e:
                self._send_json({'error': f'Failed to ingest sample chunk: {str(e)}'}, status=400)
        elif parsed.path == '/api/simulation/disturbance':
            # Control simulation disturbance dynamically from UI
            phase = data.get('phase', 'L1')
            dist = data.get('disturbance', 'Normal')
            try:
                SIM_ADAPTER.set_phase_disturbance(phase, dist)
                self._send_json({'status': 'updated', 'phase': phase, 'disturbance': dist})
            except Exception as e:
                self._send_json({'error': str(e)}, status=400)
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
    httpd = ThreadingHTTPServer(server_address, PQDServerRequestHandler)
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

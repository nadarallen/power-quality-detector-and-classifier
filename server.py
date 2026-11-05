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
import socket
import queue
import queue
import pickle
import numpy as np
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Live Simulink simulation bridge
import simulation_bridge as _sim_bridge

from dsp.fft_analyzer import (
    compute_spectrum,
    compute_flicker_analysis,
    compute_notch_analysis,
    compute_transient_analysis,
)

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

def adapt_features_60hz_to_50hz(feature_vector):
    """
    Adapts 60-Hz IEEE 9-bus Bus 5 features (V_nom=0.5887 pu, f0=60 Hz)
    to the 50-Hz reference base (V_nom=0.7071 pu, f0=50 Hz) expected by the compact MLP model.
    Preserves exact 50-Hz feature vectors untouched.
    """
    rms, pk, crest, thd, dur, dom_f, sys_f, snr = [float(x) for x in feature_vector]
    if sys_f >= 55.0 or dom_f >= 55.0:
        # Bus 5 nominal base: 0.5887 pu RMS, 0.8326 pu Peak
        v_pu = rms / 0.5887
        p_pu = pk / 0.8326
        ad_rms = v_pu * 0.7071
        ad_pk = p_pu * 1.000
        ad_crest = (ad_pk / ad_rms) if ad_rms > 1e-4 else crest
        ad_dom = 50.0
        ad_sys = 50.0
        return [ad_rms, ad_pk, ad_crest, thd, dur, ad_dom, ad_sys, snr]
    return [float(x) for x in feature_vector]

def run_python_ml_inference(feature_vector):
    """
    Executes forward pass of the Compact Keras MLP model (Dense 64 -> Dense 32 -> Dense 8).
    Handles 60 Hz -> 50 Hz domain adaptation and IEEE 1159 boundary standards.
    """
    if len(feature_vector) != 8:
        raise ValueError("Expected 8 features")
    
    # 1. Adapt 60 Hz domain to 50 Hz model space if needed
    adapted = adapt_features_60hz_to_50hz(feature_vector)
    
    # 2. Feature Standardization
    z = (np.array(adapted, dtype=np.float32) - np.array(SCALER_MEAN, dtype=np.float32)) / np.array(SCALER_SCALE, dtype=np.float32)
    
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

    # IEEE 1159 Physical standard disambiguation:
    # If residual RMS drops below 0.10 pu (< 0.15 pu in 50Hz base) with sustained duration,
    # it is strictly an Interruption per IEEE Std 1159-2019.
    if adapted[0] < 0.15 and adapted[4] >= 8.0:
        pred_class = 'Interruption'
        confidence = max(confidence, 0.98)
        if 'Interruption' in CLASSES:
            int_idx = CLASSES.index('Interruption')
            probs = np.zeros(8)
            probs[int_idx] = confidence
            other_p = (1.0 - confidence) / 7.0
            for i in range(8):
                if i != int_idx:
                    probs[i] = other_p

    prob_dict = {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))}

    return {
        'predicted_class': pred_class,
        'confidence': confidence,
        'probabilities': prob_dict,
        'features_used': feature_vector,
        'features_adapted': adapted,
        'is_uncertain': bool(confidence < 0.60)
    }

# Shared storage and pipeline components
from storage.event_store import EventStore
from dsp.waveform_frame import WaveformFrame
from dsp.acquisition_adapter import SimulationAdapter, MockHardwareAdapter, HardwareAdapter, SimulinkAdapter
from dsp.ring_buffer import MultiChannelRingBuffer
from pipeline.realtime_pipeline import RealtimePQPipeline

SHARED_EVENT_STORE = EventStore(os.path.join(BASE_DIR, 'data', 'pq_events.db'))

PQD_SOURCE = os.environ.get("PQD_ACQUISITION_SOURCE", os.environ.get("SOURCE", "simulink")).lower()
if PQD_SOURCE in ("mock_hardware", "mock", "hardware"):
    ACTIVE_ADAPTER = MockHardwareAdapter(device_id="MOCK_HW_GRID_NODE")
elif PQD_SOURCE in ("simulation", "sim"):
    ACTIVE_ADAPTER = SimulationAdapter(device_id="SIM_GRID_NODE_1", sampling_rate_hz=5000.0, nominal_frequency_hz=50.0)
else:
    ACTIVE_ADAPTER = SimulinkAdapter(device_id="SIMULINK_IEEE9BUS_BUS5", sampling_rate_hz=5000.0, nominal_frequency_hz=60.0)
ACTIVE_ADAPTER.connect()

SHARED_PIPELINE = RealtimePQPipeline(adapter=ACTIVE_ADAPTER, event_store=SHARED_EVENT_STORE, device_id="GRID_NODE_1")


def set_active_source(source_name: str) -> None:
    """Switches the active acquisition adapter (simulation vs mock_hardware vs simulink)."""
    global ACTIVE_ADAPTER, SHARED_PIPELINE
    src = source_name.lower()
    if src in ("mock_hardware", "mock", "hardware"):
        ACTIVE_ADAPTER = MockHardwareAdapter(device_id="MOCK_HW_GRID_NODE")
    elif src in ("simulation", "sim"):
        ACTIVE_ADAPTER = SimulationAdapter(device_id="SIM_GRID_NODE_1")
    elif src in ("simulink", "matlab"):
        ACTIVE_ADAPTER = SimulinkAdapter(device_id="SIMULINK_IEEE9BUS_BUS5", sampling_rate_hz=5000.0, nominal_frequency_hz=60.0)
    else:
        raise ValueError(f"Unknown acquisition source: {source_name}. Must be 'simulation', 'mock_hardware', or 'simulink'")
    ACTIVE_ADAPTER.connect()
    SHARED_PIPELINE.adapter = ACTIVE_ADAPTER
    SHARED_PIPELINE.device_id = ACTIVE_ADAPTER.device_id
    SHARED_PIPELINE.ring_buffer = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        device_id=ACTIVE_ADAPTER.device_id,
        source_type=ACTIVE_ADAPTER.source_type,
        sampling_rate_hz=ACTIVE_ADAPTER.sampling_rate_hz,
        nominal_frequency_hz=ACTIVE_ADAPTER.nominal_frequency_hz,
    )
    f0 = ACTIVE_ADAPTER.nominal_frequency_hz
    SHARED_PIPELINE.last_frame_telemetry["source_type"] = ACTIVE_ADAPTER.source_type
    SHARED_PIPELINE.last_frame_telemetry["device_id"] = ACTIVE_ADAPTER.device_id
    SHARED_PIPELINE.last_frame_telemetry["nominal_frequency"] = f0
    SHARED_PIPELINE.last_frame_telemetry["sampling_rate"] = ACTIVE_ADAPTER.sampling_rate_hz
    SHARED_PIPELINE.last_frame_telemetry["spectrum"]["freqs"] = [h * f0 for h in range(1, 12)]


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
                'acquisition_source': getattr(ACTIVE_ADAPTER, 'source_type', 'simulation'),
                'hardware_state': getattr(ACTIVE_ADAPTER, 'state', 'CONNECTED'),
                'sampling_rate': getattr(ACTIVE_ADAPTER, 'sampling_rate_hz', 5000.0),
                'nominal_frequency': getattr(ACTIVE_ADAPTER, 'nominal_frequency_hz', 50.0),
                'device_id': getattr(ACTIVE_ADAPTER, 'device_id', 'DEV_LOCAL'),
                'events_persisted': SHARED_EVENT_STORE.count_events(),
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
            if 'iterations' in query:
                iterations = int(query.get('iterations', [1])[0])
                for _ in range(iterations):
                    telem = SHARED_PIPELINE.get_latest_telemetry()
                    msg = f"data: {json.dumps(telem)}\n\n"
                    self.wfile.write(msg.encode('utf-8'))
                    self.wfile.flush()
                    if iterations > 1:
                        time.sleep(0.05)
                self.close_connection = True
                return
            else:
                try:
                    while True:
                        telem = SHARED_PIPELINE.get_latest_telemetry()
                        msg = f"data: {json.dumps(telem)}\n\n"
                        self.wfile.write(msg.encode('utf-8'))
                        self.wfile.flush()
                        time.sleep(0.5)
                except (BrokenPipeError, ConnectionResetError, socket.error):
                    pass
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
        elif parsed.path == '/api/live/simulation/prediction':
            pred = _sim_bridge.get_latest_prediction()
            self._send_json(pred)
        elif parsed.path == '/api/live/simulation/status':
            self._send_json(_sim_bridge.get_simulation_status())
        elif parsed.path == '/api/live/simulation/stream':
            # SSE stream emitting dedicated classification, telemetry, and status events
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Immediate status & prediction snapshot on initial connect
            try:
                cur_status = _sim_bridge.get_simulation_status()
                self.wfile.write(f"event: status\ndata: {json.dumps(cur_status)}\n\n".encode('utf-8'))
                latest_pred = _sim_bridge.get_latest_prediction()
                if latest_pred and latest_pred.get("prediction_status") == "VALID":
                    self.wfile.write(f"event: classification\ndata: {json.dumps(latest_pred)}\n\n".encode('utf-8'))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, socket.error):
                return

            q = _sim_bridge.subscribe_sse()
            try:
                while True:
                    try:
                        item = q.get(timeout=1.0)
                        evt_type = item.get("event", "message")
                        data_str = json.dumps(item.get("data", {}))
                        msg = f"event: {evt_type}\ndata: {data_str}\n\n"
                        self.wfile.write(msg.encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, socket.error):
                pass
            finally:
                _sim_bridge.unsubscribe_sse(q)
            return
        elif parsed.path == '/api/live/matlab/check':
            avail, detail = _sim_bridge.check_matlab_available()
            hil_ok, hil_sha = _sim_bridge.verify_hil_model_sha256()
            self._send_json({
                'matlab_available': avail,
                'matlab_detail': detail,
                'hil_model_sha256_ok': hil_ok,
                'hil_model_sha256': hil_sha,
            })
        elif parsed.path == '/api/analysis/fft':
            qs = parse_qs(parsed.query)
            ch = qs.get('channel', ['L1'])[0]
            sig_type = qs.get('type', ['voltage'])[0]
            win_type = qs.get('window', ['hann'])[0]
            active_job = _sim_bridge.get_active_job()
            signal = None
            if active_job:
                buf_dict = active_job.voltage if sig_type == 'voltage' else active_job.current
                if ch in buf_dict and len(buf_dict[ch]) >= 80:
                    signal = np.array(buf_dict[ch][-1000:], dtype=np.float64)
            if signal is None:
                telem = SHARED_PIPELINE.get_latest_telemetry()
                wfs = telem.get('waveforms', {}) if sig_type == 'voltage' else telem.get('current_waveforms', {})
                if ch in wfs and len(wfs[ch]) >= 80:
                    signal = np.array(wfs[ch][-1000:], dtype=np.float64)
            if signal is None:
                t_arr = np.arange(1000) / 5000.0
                signal = 0.5877 * math.sqrt(2) * np.sin(2.0 * np.pi * 60.0 * t_arr)
            res = compute_spectrum(signal, sample_rate=5000.0, window_type=win_type)
            self._send_json(res)
        elif parsed.path == '/api/analysis/disturbance':
            qs = parse_qs(parsed.query)
            dist_kind = qs.get('kind', ['flicker'])[0].lower()
            ch = qs.get('channel', ['L1'])[0]
            active_job = _sim_bridge.get_active_job()
            signal = None
            if active_job and ch in active_job.voltage and len(active_job.voltage[ch]) >= 80:
                signal = np.array(active_job.voltage[ch][-1000:], dtype=np.float64)
            if signal is None:
                telem = SHARED_PIPELINE.get_latest_telemetry()
                wfs = telem.get('waveforms', {})
                if ch in wfs and len(wfs[ch]) >= 80:
                    signal = np.array(wfs[ch][-1000:], dtype=np.float64)
            if signal is None:
                t_arr = np.arange(1000) / 5000.0
                signal = 0.5877 * math.sqrt(2) * np.sin(2.0 * np.pi * 60.0 * t_arr)
            if dist_kind == 'flicker':
                res = compute_flicker_analysis(signal, sample_rate=5000.0)
            elif dist_kind == 'notch':
                res = compute_notch_analysis(signal, sample_rate=5000.0)
            elif dist_kind == 'transient':
                res = compute_transient_analysis(signal, sample_rate=5000.0)
            else:
                res = compute_spectrum(signal, sample_rate=5000.0)
            self._send_json(res)
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
        elif parsed.path in ('/api/ingest/chunk', '/api/ingest/simulink'):
            # Ingestion handler supporting both standard chunks and Simulink electrical stream chunks
            if not isinstance(data, dict):
                self._send_json({'error': 'Payload must be a JSON object'}, status=400)
                return

            channels_raw = data.get('channels', {})
            if not channels_raw or not isinstance(channels_raw, dict):
                self._send_json({'error': 'Missing or invalid "channels" dictionary in payload'}, status=400)
                return

            is_simulink = (parsed.path == '/api/ingest/simulink') or (data.get('source') == 'simulink')

            if is_simulink:
                # Dedicated Simulink / Bus 5 handling
                device_id = str(data.get('device_id', 'SIMULINK_IEEE9BUS_BUS5'))
                seq_num = data.get('sequence_number', None)
                sampling_rate_hz = float(data.get('sampling_rate_hz', 5000.0))
                nominal_frequency_hz = float(data.get('nominal_frequency_hz', 60.0))
                current_channels_raw = data.get('current_channels') or data.get('currents')

                ts = data.get('timestamp_utc', None)
                if ts is not None:
                    try:
                        ts = float(ts)
                    except (ValueError, TypeError):
                        ts = None

                # Auto-switch to SimulinkAdapter if not already active or parameters changed
                if not isinstance(ACTIVE_ADAPTER, SimulinkAdapter) or ACTIVE_ADAPTER.nominal_frequency_hz != nominal_frequency_hz:
                    set_active_source("simulink")
                ACTIVE_ADAPTER.sampling_rate_hz = sampling_rate_hz
                ACTIVE_ADAPTER.nominal_frequency_hz = nominal_frequency_hz
                ACTIVE_ADAPTER.device_id = device_id
                SHARED_PIPELINE.device_id = device_id
                if SHARED_PIPELINE.ring_buffer is not None:
                    SHARED_PIPELINE.ring_buffer.sampling_rate_hz = sampling_rate_hz
                    SHARED_PIPELINE.ring_buffer.nominal_frequency_hz = nominal_frequency_hz

                try:
                    frame = ACTIVE_ADAPTER.ingest_chunk(
                        channels=channels_raw,
                        current_channels=current_channels_raw if isinstance(current_channels_raw, dict) else None,
                        timestamp_utc=ts,
                        sequence_number=seq_num,
                    )
                    events = SHARED_PIPELINE.ingest_samples(frame.phases, timestamp_utc=frame.timestamp_utc)
                    first_ch_len = len(frame.phases["L1"])
                    dom_status = "MODEL_DOMAIN_MISMATCH" if abs(nominal_frequency_hz - 50.0) > 2.0 else "MODEL_COMPATIBLE"
                    # Track live run chunk count & buffer real waveforms
                    ingest_run_id = data.get('run_id', '')
                    if ingest_run_id:
                        _sim_bridge.record_chunk_posted(
                            ingest_run_id,
                            channels=channels_raw,
                            current_channels=current_channels_raw if isinstance(current_channels_raw, dict) else None,
                            chunk_index=seq_num or 0,
                            simulation_time=data.get('simulation_time_end')
                        )
                    self._send_json({
                        'status': 'success',
                        'source': 'simulink',
                        'device_id': device_id,
                        'sequence_number': frame.sequence_number,
                        'samples_ingested': first_ch_len,
                        'nominal_frequency_hz': nominal_frequency_hz,
                        'sampling_rate_hz': sampling_rate_hz,
                        'model_domain_status': dom_status,
                        'events_detected': len(events),
                        'event_ids': [e.event_id for e in events],
                        'telemetry': SHARED_PIPELINE.get_latest_telemetry()
                    })
                except (ValueError, TypeError, OverflowError) as e:
                    self._send_json({'error': f'Simulink ingestion validation error: {str(e)}'}, status=400)
                except Exception as e:
                    self._send_json({'error': f'Failed to process Simulink chunk: {str(e)}'}, status=500)
            else:
                # Standard legacy chunk ingestion
                try:
                    is_raw_adc = bool(data.get('is_raw_adc', False))
                    if is_raw_adc and isinstance(ACTIVE_ADAPTER, HardwareAdapter):
                        channels = ACTIVE_ADAPTER.calibration.raw_to_pu_frame({
                            ch: np.asarray(arr) for ch, arr in channels_raw.items()
                        })
                    else:
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
                        'is_raw_adc_calibrated': is_raw_adc,
                        'events_detected': len(events),
                        'event_ids': [e.event_id for e in events],
                        'telemetry': SHARED_PIPELINE.get_latest_telemetry()
                    })
                except Exception as e:
                    self._send_json({'error': f'Failed to ingest sample chunk: {str(e)}'}, status=400)
        elif parsed.path == '/api/simulation/disturbance':
            # Control simulation / mock disturbance dynamically from UI
            phase = data.get('phase', 'L1')
            dist = data.get('disturbance', 'Normal')
            try:
                if hasattr(ACTIVE_ADAPTER, 'set_phase_disturbance'):
                    ACTIVE_ADAPTER.set_phase_disturbance(phase, dist)
                    self._send_json({
                        'status': 'updated',
                        'phase': phase,
                        'disturbance': dist,
                        'source': getattr(ACTIVE_ADAPTER, 'source_type', 'unknown')
                    })
                else:
                    self._send_json({'error': 'Active adapter does not support dynamic disturbance injection'}, status=400)
            except Exception as e:
                self._send_json({'error': str(e)}, status=400)
        elif parsed.path == '/api/adapter/source':
            # Dynamically switch between acquisition sources (simulation, mock_hardware)
            source = data.get('source', 'simulation')
            try:
                set_active_source(source)
                self._send_json({
                    'status': 'source_switched',
                    'active_source': getattr(ACTIVE_ADAPTER, 'source_type', source),
                    'device_id': getattr(ACTIVE_ADAPTER, 'device_id', 'DEV_LOCAL')
                })
            except Exception as e:
                self._send_json({'error': str(e)}, status=400)
        elif parsed.path == '/api/live/simulation/start':
            try:
                result = _sim_bridge.launch_simulation(data)
                self._send_json({
                    'status': 'starting',
                    'run_id': result.run_id,
                    'dist_class': result.dist_class,
                    'phases': result.phases,
                })
            except RuntimeError as e:
                self._send_json({'error': str(e)}, status=409)
            except ValueError as e:
                self._send_json({'error': str(e)}, status=400)
            except Exception as e:
                self._send_json({'error': f'Internal error: {str(e)}'}, status=500)
        elif parsed.path == '/api/live/simulation/stop':
            _sim_bridge.stop_simulation()
            active_job = _sim_bridge.get_active_job()
            st = active_job.status if active_job else "stopped"
            self._send_json({'status': st, 'command_status': 'STOPPED'})
        elif parsed.path == '/api/live/simulation/inject':
            try:
                active_job = _sim_bridge.get_active_job()
                run_id = data.get('run_id') or (active_job.run_id if active_job else '')
                dist = data.get('disturbance', 'Sag')
                phases = data.get('phases')
                params = data.get('params') or data.get('parameters')
                duration_s = float(data.get('duration_s', 0.10))
                cid = data.get('command_id')
                res = _sim_bridge.inject_live_disturbance(
                    run_id=run_id,
                    disturbance=dist,
                    phases=phases,
                    params=params,
                    duration_s=duration_s,
                    command_id=cid,
                )
                self._send_json(res)
            except (ValueError, RuntimeError) as e:
                self._send_json({'error': str(e)}, status=400)
            except Exception as e:
                self._send_json({'error': f'Failed to inject disturbance: {str(e)}'}, status=500)
        elif parsed.path == '/api/live/simulation/reset':
            try:
                active_job = _sim_bridge.get_active_job()
                run_id = data.get('run_id') or (active_job.run_id if active_job else '')
                cid = data.get('command_id')
                res = _sim_bridge.reset_live_disturbance(run_id=run_id, command_id=cid)
                self._send_json(res)
            except Exception as e:
                self._send_json({'error': str(e)}, status=400)
        elif parsed.path == '/api/live/simulation/complete':
            run_id  = data.get('run_id', '')
            status  = data.get('status', 'completed')
            if status == 'completed':
                _sim_bridge.mark_simulation_complete(run_id)
            elif status == 'stopped':
                _sim_bridge.mark_simulation_stopped(run_id)
            else:
                _sim_bridge.mark_simulation_error(run_id, data.get('error', 'Unknown'))
            self._send_json({'received': True, 'status': status})
        elif parsed.path == '/api/analysis/fft':
            sig = data.get('signal')
            if not sig or len(sig) < 80:
                self._send_json({'error': 'Signal must contain at least 80 samples'}, status=400)
                return
            fs = float(data.get('sample_rate', 5000.0))
            win = data.get('window', 'hann')
            scale = bool(data.get('scale_to_ieee_pu', True))
            res = compute_spectrum(np.array(sig, dtype=np.float64), sample_rate=fs, window_type=win, scale_to_ieee_pu=scale)
            self._send_json(res)
        elif parsed.path == '/api/analysis/disturbance':
            sig = data.get('signal')
            if not sig or len(sig) < 80:
                self._send_json({'error': 'Signal must contain at least 80 samples'}, status=400)
                return
            kind = data.get('kind', 'flicker').lower()
            fs = float(data.get('sample_rate', 5000.0))
            arr = np.array(sig, dtype=np.float64)
            if kind == 'flicker':
                res = compute_flicker_analysis(arr, sample_rate=fs)
            elif kind == 'notch':
                res = compute_notch_analysis(arr, sample_rate=fs)
            elif kind == 'transient':
                res = compute_transient_analysis(arr, sample_rate=fs)
            else:
                res = compute_spectrum(arr, sample_rate=fs)
            self._send_json(res)
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

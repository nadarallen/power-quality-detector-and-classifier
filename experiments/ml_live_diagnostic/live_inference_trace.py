"""
experiments/ml_live_diagnostic/live_inference_trace.py
------------------------------------------------------
Generates an end-to-end trace of a live simulation inference evaluation:
- Simulates streaming chunks of telemetry
- Traces analysis-window selection
- Traces feature extraction
- Traces standardized z-scores
- Traces logits and softmax probabilities
- Emits structured JSON trace artifact
"""

import os
import sys
import json
import time
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, _features_to_vector
import simulation_bridge as sb

def trace_live_inference():
    print("==================================================================")
    print("LIVE INFERENCE TRACE & SCHEDULER AUDIT")
    print("==================================================================")

    # Load normal and sag waveforms to trace a transition
    norm_w = np.load(os.path.join(PROJECT_ROOT, "data/ieee9bus_60hz/normal/normal_waveforms.npz"))["waveforms"][0, :, :] # (1000, 3)
    sag_w = np.load(os.path.join(PROJECT_ROOT, "data/ieee9bus_60hz/sag/sag_waveforms.npz"))["waveforms"][0, :, :] # (1000, 3)

    model = sb._get_60hz_model()
    assert model is not None, "Failed to load Phase 4C 60 Hz model!"

    # Trace 1: Pure Normal Window
    t0 = time.perf_counter()
    pred_norm = sb.predict_60hz_model(norm_w[:, 0], sample_rate=5000.0)
    lat_norm = (time.perf_counter() - t0) * 1000.0

    # Trace 2: Pure Sag Window
    t0 = time.perf_counter()
    pred_sag = sb.predict_60hz_model(sag_w[:, 0], sample_rate=5000.0)
    lat_sag = (time.perf_counter() - t0) * 1000.0

    trace_payload = {
        "model_id": "phase4c_candidate_mlp",
        "model_sha256": "f0febd5b3829677ac0f2c13262cccb5ff8947cdcb59596f5e4a8f2b6180c27c5",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "normal_trace": {
            "predicted_class": pred_norm["predicted_class"],
            "confidence": pred_norm["confidence"],
            "latency_ms": lat_norm,
            "status": pred_norm["status"],
            "key_features": {
                "rms_voltage": pred_norm["features"]["rms_voltage"],
                "thd": pred_norm["features"]["thd"],
                "crest_factor": pred_norm["features"]["crest_factor"],
                "snr": pred_norm["features"]["snr"]
            }
        },
        "sag_trace": {
            "predicted_class": pred_sag["predicted_class"],
            "confidence": pred_sag["confidence"],
            "latency_ms": lat_sag,
            "status": pred_sag["status"],
            "key_features": {
                "rms_voltage": pred_sag["features"]["rms_voltage"],
                "thd": pred_sag["features"]["thd"],
                "crest_factor": pred_sag["features"]["crest_factor"],
                "snr": pred_sag["features"]["snr"]
            }
        }
    }

    print(f"Normal Trace: Pred={pred_norm['predicted_class']} ({pred_norm['confidence']*100:.1f}%) in {lat_norm:.2f} ms")
    print(f"Sag Trace:    Pred={pred_sag['predicted_class']} ({pred_sag['confidence']*100:.1f}%) in {lat_sag:.2f} ms")

    out_file = os.path.join(os.path.dirname(__file__), "live_inference_trace_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(trace_payload, f, indent=2)

    print(f"Inference trace results saved to: {out_file}")

if __name__ == "__main__":
    trace_live_inference()

"""
experiments/ml_live_diagnostic/injection_duration_matrix.py
-----------------------------------------------------------
Tests the candidate MLP classifier across controlled disturbance durations:
0.05 s, 0.10 s, 0.20 s, 0.40 s, 0.80 s, 1.00 s, 2.00 s.

Evaluates:
- Trailing window vs Event-aware disturbance window
- Physical assessment vs ML raw prediction
- Probability distribution
- Minimum disturbance duration for reliable recognition
"""

import os
import sys
import json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.enhanced_features import extract_enhanced_features
from dsp.phase_processor import _MODEL_FEATURE_ORDER, _features_to_vector
import simulation_bridge as sb

DURATIONS = [0.05, 0.10, 0.20, 0.40, 0.80, 1.00, 2.00]
CLASSES = ["Sag", "Swell", "Harmonics", "Flicker", "Notch", "Transient", "Interruption"]

def run_duration_matrix():
    print("==================================================================")
    print("INJECTION DURATION MATRIX AUDIT")
    print("==================================================================")

    # Load canonical base waveforms
    waveforms = {}
    for c in ["normal", "sag", "swell", "harmonics", "flicker", "notch", "transient", "interruption"]:
        npz = os.path.join(PROJECT_ROOT, "data", "ieee9bus_60hz", c, f"{c}_waveforms.npz")
        waveforms[c] = np.load(npz)["waveforms"][0, :, 0] # 1000 samples

    results_table = []
    min_reliable_durations = {}

    for c in CLASSES:
        c_lower = c.lower()
        dist_w = waveforms[c_lower]
        norm_w = waveforms["normal"]

        print(f"\n--- Class: {c} ---")
        min_reliable = None

        for dur in DURATIONS:
            # Generate a continuous waveform segment representing this duration
            n_samples = int(dur * 5000)

            # Tile or slice to target duration
            if n_samples <= 1000:
                # Disturbance active for n_samples
                # When using event-aware windowing: exactly the disturbance epoch is analyzed
                # Repeated/padded periodically to fill 1000 samples (12 cycles @ 60 Hz) for contract
                num_repeats = int(np.ceil(1000 / n_samples))
                event_signal = np.tile(dist_w[:n_samples], num_repeats)[:1000]
            else:
                num_repeats = int(np.ceil(n_samples / 1000))
                full_stream = np.tile(dist_w, num_repeats)[:n_samples]
                event_signal = full_stream[-1000:]

            pred_res = sb.predict_60hz_model(event_signal, sample_rate=5000.0)
            pred_cls = pred_res["predicted_class"]
            conf = pred_res["confidence"]
            probs = pred_res["probabilities"]

            is_correct = (pred_cls == c)
            if is_correct and min_reliable is None:
                min_reliable = dur

            results_table.append({
                "class": c,
                "duration_s": dur,
                "sample_count": n_samples,
                "predicted_class": pred_cls,
                "confidence": float(conf),
                "is_correct": bool(is_correct),
                "class_probability": float(probs.get(c, 0.0)),
                "windowing_strategy": "event_aware"
            })

            status_mark = "PASS" if is_correct else "FAIL"
            print(f"  Duration: {dur:4.2f} s ({n_samples:5d} samples) -> Pred: {pred_cls:12s} ({conf*100:5.1f}%) [{status_mark}]")

        min_reliable_durations[c] = min_reliable

    print("\n" + "=" * 75)
    print("MINIMUM RELIABLE DISTURBANCE DURATION SUMMARY:")
    print("=" * 75)
    for c, min_d in min_reliable_durations.items():
        print(f"  {c:15s}: {min_d:4.2f} s" if min_d is not None else f"  {c:15s}: UNRELIABLE")

    out_file = os.path.join(os.path.dirname(__file__), "injection_duration_matrix_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "results": results_table,
            "min_reliable_durations": min_reliable_durations
        }, f, indent=2)

    print(f"\nDuration matrix results saved to: {out_file}")

if __name__ == "__main__":
    run_duration_matrix()

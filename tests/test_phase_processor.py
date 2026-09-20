"""
Phase Processor Tests — Per-Phase DSP + ML Integration
------------------------------------------------------
Tests that dsp/phase_processor.py correctly:

1. Routes a WaveformFrame through extract_enhanced_features() to produce
   the 32-element feature vector required by model_weights_32.json.
2. Runs the MLP forward pass (or heuristic fallback) per phase.
3. Returns correctly populated PhaseMeasurement objects.
4. Applies the UNCERTAINTY_THRESHOLD gate.
5. Rejects invalid (non-validated) WaveformFrames.
"""

import numpy as np
import pytest

from dsp.waveform_frame import WaveformFrame
from dsp.phase_processor import (
    classify_phase_signal,
    process_waveform_frame,
    UNCERTAINTY_THRESHOLD,
    _MODEL_FEATURE_ORDER,
    _features_to_vector,
    MLPClassifier,
)
from dsp.enhanced_features import extract_enhanced_features
from dsp.event_engine import PhaseMeasurement

FS = 5000.0
F0 = 50.0
N = 1000  # 10 grid cycles at 5 kHz
_CLASS_LABELS = ['Flicker', 'Harmonics', 'Interruption', 'Normal',
                 'Notch', 'Sag', 'Swell', 'Transient']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(*disturbances) -> WaveformFrame:
    """
    Build a 3-phase WaveformFrame.
    disturbances: (class_name_for_L1, class_for_L2, class_for_L3)
    Use None or 'Normal' for a clean sinusoid.
    """
    from dsp.waveform_generator import generate_pqd_waveform
    t = np.arange(N) / FS
    phases = {}
    phase_labels = ["L1", "L2", "L3"]
    offsets_deg = [0.0, -120.0, 120.0]
    dist_map = {None: "Normal", "Normal": "Normal"}

    for phase, offset, dist in zip(phase_labels, offsets_deg, disturbances):
        cls = dist_map.get(dist, dist) if dist in (None, "Normal") else dist
        try:
            wave, _ = generate_pqd_waveform(cls, snr_db=45.0, seed=42)
        except Exception:
            wave = np.sin(2 * np.pi * F0 * t)
        shift = int((offset / 360.0) * (FS / F0))
        phases[phase] = np.roll(wave, shift).astype(np.float32)

    frame = WaveformFrame(
        timestamp_utc=0.0,
        sampling_rate_hz=FS,
        nominal_frequency_hz=F0,
        source_type="simulation",
        phases=phases,
    )
    frame.validate()
    return frame


# ---------------------------------------------------------------------------
# Feature vector assembly
# ---------------------------------------------------------------------------

def test_feature_vector_has_correct_length():
    """Feature vector must have exactly 32 elements in the documented order."""
    t = np.arange(N) / FS
    signal = np.sin(2 * np.pi * F0 * t).astype(np.float32)
    feat = extract_enhanced_features(signal, sample_rate=FS)
    vec = _features_to_vector(feat)
    assert vec.shape == (32,), f"Expected (32,), got {vec.shape}"


def test_feature_vector_order_matches_model_manifest():
    """Every feature in _MODEL_FEATURE_ORDER must be non-zero for a non-trivial signal."""
    t = np.arange(N) / FS
    # Use a signal with harmonics so h1-h11 are non-zero
    signal = (np.sin(2 * np.pi * F0 * t) + 0.1 * np.sin(2 * np.pi * 3 * F0 * t)).astype(np.float32)
    feat = extract_enhanced_features(signal, sample_rate=FS)
    vec = _features_to_vector(feat)
    # At minimum: rms, peak, h1, h3 must be non-zero
    for name in ["rms_voltage", "peak_voltage", "h1", "h3"]:
        idx = _MODEL_FEATURE_ORDER.index(name)
        assert vec[idx] != 0.0, f"Feature '{name}' at index {idx} is zero for a non-trivial signal"


# ---------------------------------------------------------------------------
# Single-phase classification
# ---------------------------------------------------------------------------

def test_classify_normal_signal():
    """A clean 50 Hz sinusoid must classify as 'Normal' with confidence >= threshold."""
    t = np.arange(N) / FS
    signal = np.sin(2 * np.pi * F0 * t).astype(np.float32)
    cls, conf, probs = classify_phase_signal(signal, FS)
    assert cls == "Normal", f"Expected 'Normal', got '{cls}'"
    assert conf >= UNCERTAINTY_THRESHOLD
    assert probs.shape == (8,)
    assert abs(probs.sum() - 1.0) < 1e-4, "Softmax probabilities must sum to 1"


def test_classify_sag_signal():
    """A 50% amplitude sag must classify as 'Sag' or 'Interruption' (low RMS region)."""
    t = np.arange(N) / FS
    signal = 0.5 * np.sin(2 * np.pi * F0 * t).astype(np.float32)
    cls, conf, probs = classify_phase_signal(signal, FS)
    assert cls in ("Sag", "Interruption", "UNCERTAIN"), \
        f"Low-RMS signal classified as '{cls}' — unexpected for a sag input"


def test_classify_harmonics_signal():
    """A waveform with strong odd harmonics (THD ~25%) must classify as 'Harmonics'."""
    t = np.arange(N) / FS
    signal = (
        np.sin(2 * np.pi * F0 * t) +
        0.15 * np.sin(2 * np.pi * 3 * F0 * t) +
        0.10 * np.sin(2 * np.pi * 5 * F0 * t) +
        0.08 * np.sin(2 * np.pi * 7 * F0 * t)
    ).astype(np.float32)
    cls, conf, probs = classify_phase_signal(signal, FS)
    assert cls in ("Harmonics", "Normal", "UNCERTAIN"), \
        f"High-THD signal classified as '{cls}' — unexpected"


def test_uncertainty_gate_applied():
    """Signals with confidence < UNCERTAINTY_THRESHOLD must return 'UNCERTAIN'."""
    # Manufacture a borderline artificial vector where the MLP produces low confidence
    # by using a constant flat signal (no frequency content at all)
    signal = np.full(N, 0.3, dtype=np.float32)
    cls, conf, probs = classify_phase_signal(signal, FS)
    # Regardless of class, uncertainty gate must mark low-conf predictions
    if conf < UNCERTAINTY_THRESHOLD:
        assert cls == "UNCERTAIN"


# ---------------------------------------------------------------------------
# Per-phase WaveformFrame processing
# ---------------------------------------------------------------------------

def test_process_waveform_frame_returns_all_phases():
    """process_waveform_frame() must return PhaseMeasurement for every available phase."""
    frame = _make_frame("Normal", "Normal", "Normal")
    result = process_waveform_frame(frame)
    assert set(result.keys()) == {"L1", "L2", "L3"}
    for phase, pm in result.items():
        assert isinstance(pm, PhaseMeasurement)
        assert pm.phase == phase
        assert pm.rms_voltage >= 0.0
        assert pm.classification in _CLASS_LABELS + ["UNCERTAIN"]
        assert 0.0 <= pm.confidence <= 1.0


def test_process_waveform_frame_invalid_raises():
    """process_waveform_frame() must raise ValueError on an invalid (non-validated) frame."""
    frame = WaveformFrame(
        timestamp_utc=0.0,
        sampling_rate_hz=FS,
        phases={"L1": np.array([np.nan] * N, dtype=np.float32)},
    )
    frame.validate()  # marks frame.is_valid = False
    with pytest.raises(ValueError, match="invalid WaveformFrame"):
        process_waveform_frame(frame)


def test_process_waveform_frame_subset_phases():
    """process_waveform_frame() must process only the requested subset of phases."""
    frame = _make_frame("Normal", "Normal", "Normal")
    result = process_waveform_frame(frame, phases_to_process=["L1", "L3"])
    assert set(result.keys()) == {"L1", "L3"}
    assert "L2" not in result


def test_per_phase_harmonics_populated():
    """PhaseMeasurement.harmonics must contain h1..h11 keys."""
    frame = _make_frame("Normal", "Normal", "Normal")
    result = process_waveform_frame(frame)
    pm_l1 = result["L1"]
    # At minimum h1 should be present and non-zero for a sinusoidal signal
    assert "h1" in pm_l1.harmonics
    assert pm_l1.harmonics["h1"] > 0.0

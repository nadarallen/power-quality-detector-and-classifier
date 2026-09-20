"""
Unit Tests for ThreePhaseEventEngine & Multi-Phase Correlator
------------------------------------------------------------
Tests the ENGINE STATE MACHINE mechanics (open/close/merge/correlate).

These tests use use_mlp=False (heuristic classifier) so they are isolated
from model weight availability and remain fast, deterministic, and independent
of the trained MLP.

The trained MLP integration is tested in test_end_to_end_pipeline.py, which
verifies classification accuracy using waveform_generator-produced signals.
"""

import numpy as np
import pytest

from dsp.waveform_frame import WaveformFrame
from dsp.event_engine import ThreePhaseEventEngine, PQEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(timestamp_utc: float, l1_amp: float, l2_amp: float, l3_amp: float,
                fs: float = 5000.0, N: int = 1000) -> WaveformFrame:
    """
    Builds a raw sinusoidal 3-phase frame for state machine testing.
    Amplitude < 0.90 * 0.7156 triggers Sag in heuristic.
    Amplitude 0.0..0.10 * 0.7156 triggers Interruption.
    """
    t = np.arange(N) / fs
    frame = WaveformFrame(
        timestamp_utc=timestamp_utc,
        sampling_rate_hz=fs,
        phases={
            "L1": (l1_amp * np.sin(2.0 * np.pi * 50.0 * t)).astype(np.float32),
            "L2": (l2_amp * np.sin(2.0 * np.pi * 50.0 * t - 2.094)).astype(np.float32),
            "L3": (l3_amp * np.sin(2.0 * np.pi * 50.0 * t + 2.094)).astype(np.float32),
        },
    )
    frame.validate()
    return frame


# Normal amplitude: amplitude * sin → RMS = amplitude / sqrt(2) ≈ amplitude * 0.707
# Heuristic checks rms_pu = rms_raw / 0.7156
# So: nominal_amplitude = 1.0 → rms_raw ≈ 0.707 → rms_pu ≈ 0.988 → Normal
# Sag amplitude = 0.5 → rms_raw ≈ 0.354 → rms_pu ≈ 0.494 → Sag [0.10, 0.90)

NORMAL_AMP = 1.0
SAG_AMP = 0.5  # rms_pu ≈ 0.494


def test_event_engine_single_phase_event():
    """State machine: single-phase sag on L2 → open → extend → close, correct metadata."""
    engine = ThreePhaseEventEngine(use_mlp=False)

    # Frame 1: All Normal
    closed = engine.process_frame(_make_frame(100.0, NORMAL_AMP, NORMAL_AMP, NORMAL_AMP))
    assert len(closed) == 0

    # Frame 2: Sag on L2
    closed = engine.process_frame(_make_frame(100.200, NORMAL_AMP, SAG_AMP, NORMAL_AMP))
    assert len(closed) == 0                                  # event is active, not closed
    assert engine.active_events_by_phase["L2"] is not None
    assert engine.active_events_by_phase["L2"].affected_phases == ["L2"]
    assert engine.active_events_by_phase["L2"].event_class == "Sag"

    # Frame 3: Sag continues
    closed = engine.process_frame(_make_frame(100.400, NORMAL_AMP, SAG_AMP, NORMAL_AMP))
    assert len(closed) == 0                                  # merged with Frame 2 event

    # Frame 4: Grid recovers
    closed = engine.process_frame(_make_frame(100.600, NORMAL_AMP, NORMAL_AMP, NORMAL_AMP))
    assert len(closed) == 1
    ev = closed[0]
    assert ev.event_class == "Sag"
    assert ev.affected_phases == ["L2"]
    assert ev.duration_ms >= 399.0          # spanned Frame 2 (100.200) → Frame 4 (100.600)
    assert ev.phase_metrics["L2"].min_rms < 0.60


def test_event_engine_multi_phase_correlation():
    """State machine: simultaneous sag on L1+L2 merges into one correlated event."""
    engine = ThreePhaseEventEngine(use_mlp=False)

    # Simultaneous sag on L1 and L2
    engine.process_frame(_make_frame(200.0, SAG_AMP, SAG_AMP, NORMAL_AMP))

    # Return to normal
    closed = engine.process_frame(_make_frame(200.200, NORMAL_AMP, NORMAL_AMP, NORMAL_AMP))
    assert len(closed) == 1
    ev = closed[0]
    assert ev.event_class == "Sag"
    assert set(ev.affected_phases) == {"L1", "L2"}
    assert "L1" in ev.phase_metrics
    assert "L2" in ev.phase_metrics

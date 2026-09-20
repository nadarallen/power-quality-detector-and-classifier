"""
Unit Tests for ThreePhaseEventEngine & Multi-Phase Correlator
------------------------------------------------------------
Verifies:
1. Per-phase disturbance identification.
2. Cross-phase correlation (e.g. concurrent L1 and L2 sag merged into a single event with affected_phases=['L1', 'L2']).
3. Multi-window event merging (consecutive sag windows do not create duplicate events).
4. Clean event closure and duration accumulation when grid returns to Normal.
"""

import numpy as np
import pytest

from dsp.waveform_frame import WaveformFrame
from dsp.event_engine import ThreePhaseEventEngine, PQEvent


def test_event_engine_single_phase_event():
    """Verify single-phase sag detection on L2."""
    engine = ThreePhaseEventEngine()
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs

    # Frame 1: Normal grid baseline
    f1 = WaveformFrame(
        timestamp_utc=100.0,
        sampling_rate_hz=fs,
        phases={
            "L1": 1.0 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 1.0 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    closed = engine.process_frame(f1)
    assert len(closed) == 0

    # Frame 2: Sag on L2 (0.5 pu)
    f2 = WaveformFrame(
        timestamp_utc=100.200,
        sampling_rate_hz=fs,
        phases={
            "L1": 1.0 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 0.5 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    closed = engine.process_frame(f2)
    assert len(closed) == 0  # Event is active, not closed yet
    assert engine.active_events_by_phase["L2"] is not None
    assert engine.active_events_by_phase["L2"].affected_phases == ["L2"]
    assert engine.active_events_by_phase["L2"].event_class == "Sag"

    # Frame 3: Sag on L2 continues
    f3 = WaveformFrame(
        timestamp_utc=100.400,
        sampling_rate_hz=fs,
        phases={
            "L1": 1.0 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 0.5 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    closed = engine.process_frame(f3)
    assert len(closed) == 0  # Still open, merged with Frame 2

    # Frame 4: Grid recovers to Normal
    f4 = WaveformFrame(
        timestamp_utc=100.600,
        sampling_rate_hz=fs,
        phases={
            "L1": 1.0 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 1.0 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    closed = engine.process_frame(f4)
    assert len(closed) == 1
    ev = closed[0]
    assert ev.event_class == "Sag"
    assert ev.affected_phases == ["L2"]
    assert ev.duration_ms >= 399.0  # Spanned Frame 2 and Frame 3 (~400 ms)
    assert ev.phase_metrics["L2"].min_rms < 0.60


def test_event_engine_multi_phase_correlation():
    """Verify simultaneous sag on L1 and L2 merges into a single correlated event."""
    engine = ThreePhaseEventEngine()
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs

    # Sag on L1 and L2 simultaneously
    f1 = WaveformFrame(
        timestamp_utc=200.0,
        sampling_rate_hz=fs,
        phases={
            "L1": 0.4 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 0.4 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    engine.process_frame(f1)
    
    # Return to normal
    f2 = WaveformFrame(
        timestamp_utc=200.200,
        sampling_rate_hz=fs,
        phases={
            "L1": 1.0 * np.sin(2.0 * np.pi * 50.0 * t),
            "L2": 1.0 * np.sin(2.0 * np.pi * 50.0 * t - 2.094),
            "L3": 1.0 * np.sin(2.0 * np.pi * 50.0 * t + 2.094)
        }
    )
    closed = engine.process_frame(f2)
    assert len(closed) == 1
    ev = closed[0]
    assert ev.event_class == "Sag"
    assert set(ev.affected_phases) == {"L1", "L2"}
    assert "L1" in ev.phase_metrics
    assert "L2" in ev.phase_metrics

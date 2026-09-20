"""
Integration Tests for Multi-Window Disturbance Merging & Lifecycle
-----------------------------------------------------------------
Validates IEEE 1159 / Master Spec requirements:
- Section 16: Contiguous & overlapping analysis windows merge into ONE event
- Section 17: Multi-phase simultaneous disturbance correlation & dynamic expansion
- Monotonic envelope tracking (Vmin nadir, Vmax peak, maximum THD)
- Clean event splitting across disturbance type transitions
- Integration with RealtimePQPipeline and MultiChannelRingBuffer
"""

import pytest
import numpy as np
import tempfile
import os

from dsp.waveform_frame import WaveformFrame
from dsp.event_engine import ThreePhaseEventEngine, PQEvent
from dsp.ring_buffer import MultiChannelRingBuffer
from pipeline.realtime_pipeline import RealtimePQPipeline
from storage.event_store import EventStore


def _make_sinusoid(v_peak_pu: float, duration_samples: int = 1000, fs: float = 5000.0, f0: float = 50.0):
    """Generates a pure sinusoid with calibrated per-unit peak amplitude."""
    t = np.arange(duration_samples) / fs
    return (v_peak_pu * np.sin(2.0 * np.pi * f0 * t)).astype(np.float32)


def test_three_contiguous_sag_windows_merge_into_one_event():
    """
    IEEE 1159 Section 16:
    Three consecutive 200 ms Sag windows (total 600 ms) must merge into ONE event
    with start=0.0, end=0.6, duration=600 ms, and single event_id.
    """
    engine = ThreePhaseEventEngine(use_mlp=False)

    fs = 5000.0
    sig_norm = _make_sinusoid(1.0, 1000, fs)
    sig_sag = _make_sinusoid(0.5, 1000, fs)  # 0.5 pu Sag

    # Window 1: t=0.0 to 0.2
    f1 = WaveformFrame(timestamp_utc=0.0, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_sag, "L3": sig_norm})
    ev1 = engine.process_frame(f1)
    assert len(ev1) == 0  # Event is active, not closed
    assert len(engine.get_active_events()) == 1
    active_id = engine.get_active_events()[0].event_id

    # Window 2: t=0.2 to 0.4
    f2 = WaveformFrame(timestamp_utc=0.2, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_sag, "L3": sig_norm})
    ev2 = engine.process_frame(f2)
    assert len(ev2) == 0
    assert len(engine.get_active_events()) == 1
    assert engine.get_active_events()[0].event_id == active_id  # Same event

    # Window 3: t=0.4 to 0.6
    f3 = WaveformFrame(timestamp_utc=0.4, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_sag, "L3": sig_norm})
    ev3 = engine.process_frame(f3)
    assert len(ev3) == 0
    assert len(engine.get_active_events()) == 1

    # Window 4: Normal frame at t=0.6 -> Closes the Sag event
    f4 = WaveformFrame(timestamp_utc=0.6, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_norm, "L3": sig_norm})
    closed_events = engine.process_frame(f4)
    assert len(closed_events) == 1
    assert len(engine.get_active_events()) == 0

    event = closed_events[0]
    assert event.event_id == active_id
    assert event.event_class == "Sag"
    assert event.affected_phases == ["L2"]
    assert event.is_multi_phase is False
    assert event.start_time_utc == pytest.approx(0.0)
    assert event.end_time_utc == pytest.approx(0.6)
    assert event.duration_ms == pytest.approx(600.0)
    assert event.max_severity > 0.4  # ~0.5 pu deviation


def test_overlapping_sliding_windows_do_not_duplicate_events():
    """
    When processing via ring buffer with 50% hop size (100 ms hop, 200 ms window),
    overlapping windows spanning a disturbance must not produce duplicate events.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        store = EventStore(db_path=db_path)
        rb = MultiChannelRingBuffer(
            channels=["L1", "L2", "L3"],
            window_size=1000,
            hop_size=500,  # 50% overlap = 100 ms hop
            sampling_rate_hz=5000.0
        )
        pipeline = RealtimePQPipeline(ring_buffer=rb, event_store=store)
        pipeline.engine.use_mlp = False

        fs = 5000.0
        # 1. 200 ms normal (1000 samples)
        norm_chunk = {"L1": _make_sinusoid(1.0, 1000, fs),
                      "L2": _make_sinusoid(1.0, 1000, fs),
                      "L3": _make_sinusoid(1.0, 1000, fs)}
        pipeline.ingest_samples(norm_chunk, timestamp_utc=0.0)

        # 2. 400 ms sag on L2 (2000 samples)
        sag_chunk = {"L1": _make_sinusoid(1.0, 2000, fs),
                     "L2": _make_sinusoid(0.5, 2000, fs),
                     "L3": _make_sinusoid(1.0, 2000, fs)}
        pipeline.ingest_samples(sag_chunk, timestamp_utc=0.2)

        # 3. 400 ms normal to close (2000 samples)
        rec_chunk = {"L1": _make_sinusoid(1.0, 2000, fs),
                     "L2": _make_sinusoid(1.0, 2000, fs),
                     "L3": _make_sinusoid(1.0, 2000, fs)}
        closed = pipeline.ingest_samples(rec_chunk, timestamp_utc=0.6)

        # There should be exactly ONE Sag event detected and persisted
        events_in_db = store.query_events(limit=10)
        assert len(events_in_db) == 1
        assert events_in_db[0]["event_class"] == "Sag"
        assert "L2" in events_in_db[0]["affected_phases"]
        assert events_in_db[0]["duration_ms"] >= 300.0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_disturbance_class_transition_event_splitting():
    """
    If disturbance class changes (e.g. Sag transitioning directly into Swell),
    the Sag event must cleanly close and the Swell event must open without leaking metrics.
    """
    engine = ThreePhaseEventEngine(use_mlp=False)

    fs = 5000.0
    sig_norm = _make_sinusoid(1.0, 1000, fs)
    sig_sag = _make_sinusoid(0.5, 1000, fs)
    sig_swell = _make_sinusoid(1.4, 1000, fs)

    # Window 1: Sag on L1
    f1 = WaveformFrame(timestamp_utc=0.0, sampling_rate_hz=fs,
                       phases={"L1": sig_sag, "L2": sig_norm, "L3": sig_norm})
    engine.process_frame(f1)
    assert len(engine.get_active_events()) == 1
    assert engine.get_active_events()[0].event_class == "Sag"

    # Window 2: Swell on L1 -> Sag closes, Swell opens
    f2 = WaveformFrame(timestamp_utc=0.2, sampling_rate_hz=fs,
                       phases={"L1": sig_swell, "L2": sig_norm, "L3": sig_norm})
    closed_from_f2 = engine.process_frame(f2)
    assert len(closed_from_f2) == 1
    assert closed_from_f2[0].event_class == "Sag"
    assert closed_from_f2[0].end_time_utc == pytest.approx(0.2)

    # Verify Swell is now the active event
    active = engine.get_active_events()
    assert len(active) == 1
    assert active[0].event_class == "Swell"

    # Window 3: Normal -> Swell closes
    f3 = WaveformFrame(timestamp_utc=0.4, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_norm, "L3": sig_norm})
    closed_from_f3 = engine.process_frame(f3)
    assert len(closed_from_f3) == 1
    assert closed_from_f3[0].event_class == "Swell"


def test_dynamic_multi_phase_expansion():
    """
    Section 17: Disturbance starts on L1, then spreads to L2 in the next window.
    Both phases must be correlated under the same unified PQEvent.
    """
    engine = ThreePhaseEventEngine(use_mlp=False)

    fs = 5000.0
    sig_norm = _make_sinusoid(1.0, 1000, fs)
    sig_sag = _make_sinusoid(0.5, 1000, fs)

    # Window 1: Sag only on L1
    f1 = WaveformFrame(timestamp_utc=0.0, sampling_rate_hz=fs,
                       phases={"L1": sig_sag, "L2": sig_norm, "L3": sig_norm})
    engine.process_frame(f1)
    active1 = engine.get_active_events()[0]
    assert active1.affected_phases == ["L1"]
    assert active1.is_multi_phase is False

    # Window 2: Sag on BOTH L1 and L2
    f2 = WaveformFrame(timestamp_utc=0.2, sampling_rate_hz=fs,
                       phases={"L1": sig_sag, "L2": sig_sag, "L3": sig_norm})
    engine.process_frame(f2)
    active2 = engine.get_active_events()[0]
    assert sorted(active2.affected_phases) == ["L1", "L2"]
    assert active2.is_multi_phase is True
    assert "L1" in active2.phase_metrics
    assert "L2" in active2.phase_metrics

    # Window 3: Normal on all phases
    f3 = WaveformFrame(timestamp_utc=0.4, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_norm, "L3": sig_norm})
    closed = engine.process_frame(f3)
    assert len(closed) == 1
    assert sorted(closed[0].affected_phases) == ["L1", "L2"]
    assert closed[0].is_multi_phase is True
    assert closed[0].duration_ms == pytest.approx(400.0)


def test_monotonic_envelope_nadir_aggregation():
    """
    Verify that min_rms across multiple windows records the global nadir
    (deepest sag), not just the value of the last window.
    """
    engine = ThreePhaseEventEngine(use_mlp=False)

    fs = 5000.0
    sig_norm = _make_sinusoid(1.0, 1000, fs)
    sig_sag_mild = _make_sinusoid(0.70, 1000, fs)
    sig_sag_deep = _make_sinusoid(0.35, 1000, fs)
    sig_sag_recovery = _make_sinusoid(0.80, 1000, fs)

    # Window 1: Mild sag (0.70 pu)
    f1 = WaveformFrame(timestamp_utc=0.0, sampling_rate_hz=fs,
                       phases={"L1": sig_sag_mild, "L2": sig_norm, "L3": sig_norm})
    engine.process_frame(f1)

    # Window 2: Deep sag (0.35 pu)
    f2 = WaveformFrame(timestamp_utc=0.2, sampling_rate_hz=fs,
                       phases={"L1": sig_sag_deep, "L2": sig_norm, "L3": sig_norm})
    engine.process_frame(f2)

    # Window 3: Recovering sag (0.80 pu)
    f3 = WaveformFrame(timestamp_utc=0.4, sampling_rate_hz=fs,
                       phases={"L1": sig_sag_recovery, "L2": sig_norm, "L3": sig_norm})
    engine.process_frame(f3)

    # Window 4: Fully recovered normal
    f4 = WaveformFrame(timestamp_utc=0.6, sampling_rate_hz=fs,
                       phases={"L1": sig_norm, "L2": sig_norm, "L3": sig_norm})
    closed = engine.process_frame(f4)

    assert len(closed) == 1
    event = closed[0]
    l1_metrics = event.phase_metrics["L1"]
    # Global min_rms must be ~0.35 / sqrt(2) pu (the nadir), NOT the recovery value ~0.80 / sqrt(2)
    assert l1_metrics.min_rms == pytest.approx(0.35 / np.sqrt(2.0), abs=0.02)
    assert l1_metrics.max_rms >= 0.70 / np.sqrt(2.0)
    assert l1_metrics.min_rms < 0.50  # Must be strictly lower than recovery level

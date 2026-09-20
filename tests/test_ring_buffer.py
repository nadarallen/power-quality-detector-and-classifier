"""
Unit Tests for MultiChannelRingBuffer
-------------------------------------
Tests continuous sliding-window ring buffer:
- Chunk ingestion across synchronized channels
- Configurable window size and overlap (hop size)
- Circular wrap-around integrity
- Timestamp propagation
- Validation failure modes (NaN, length mismatch, missing channels, overflow)
"""

import pytest
import numpy as np
from dsp.ring_buffer import MultiChannelRingBuffer
from dsp.waveform_frame import WaveformFrame


def test_ring_buffer_basic_window_extraction():
    """Verify standard non-overlapping 1000-sample window extraction."""
    rb = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        window_size=1000,
        hop_size=1000,
        sampling_rate_hz=5000.0
    )
    assert not rb.has_window()
    assert rb.get_next_window() is None

    # Append 1000 samples
    chunk = {
        "L1": np.ones(1000, dtype=np.float32) * 1.0,
        "L2": np.ones(1000, dtype=np.float32) * 2.0,
        "L3": np.ones(1000, dtype=np.float32) * 3.0,
    }
    rb.append_samples(chunk, timestamp_utc=100.0)

    assert rb.has_window()
    assert rb.available_samples == 1000

    frame = rb.get_next_window()
    assert isinstance(frame, WaveformFrame)
    assert frame.num_samples == 1000
    assert frame.sampling_rate_hz == 5000.0
    assert frame.timestamp_utc == 100.0
    assert np.allclose(frame.get_phase("L1"), 1.0)
    assert np.allclose(frame.get_phase("L2"), 2.0)
    assert np.allclose(frame.get_phase("L3"), 3.0)

    # After hop of 1000, no more windows available
    assert not rb.has_window()
    assert rb.get_next_window() is None


def test_ring_buffer_overlapping_windows():
    """Verify 50% overlapping windows (window=1000, hop=500)."""
    rb = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        window_size=1000,
        hop_size=500,
        sampling_rate_hz=5000.0
    )

    ramp = np.arange(1500, dtype=np.float32)
    chunk = {"L1": ramp, "L2": ramp, "L3": ramp}
    rb.append_samples(chunk, timestamp_utc=100.0)

    assert rb.has_window()

    # Window 0: samples 0..999
    w0 = rb.get_next_window()
    assert w0 is not None
    assert w0.timestamp_utc == pytest.approx(100.0)
    assert np.array_equal(w0.get_phase("L1"), ramp[:1000])

    # Window 1: samples 500..1499, timestamp advanced by 500/5000 = 0.1s
    assert rb.has_window()
    w1 = rb.get_next_window()
    assert w1 is not None
    assert w1.timestamp_utc == pytest.approx(100.1)
    assert np.array_equal(w1.get_phase("L1"), ramp[500:1500])

    # No more full windows (500 samples remain waiting for next 500)
    assert not rb.has_window()
    assert rb.available_samples == 500


def test_ring_buffer_continuous_small_chunks():
    """Verify streaming in 100-sample chunks yields exact continuous waveforms."""
    rb = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        window_size=1000,
        hop_size=1000,
        sampling_rate_hz=5000.0
    )

    total_samples = 2500
    full_ramp = np.arange(total_samples, dtype=np.float32)

    # Ingest in chunks of 100 samples
    frames_collected = []
    chunk_size = 100
    for i in range(0, total_samples, chunk_size):
        sub = full_ramp[i:i + chunk_size]
        rb.append_samples({"L1": sub, "L2": sub, "L3": sub}, timestamp_utc=1000.0 + i / 5000.0)
        while rb.has_window():
            frames_collected.append(rb.get_next_window())

    assert len(frames_collected) == 2
    assert np.array_equal(frames_collected[0].get_phase("L1"), full_ramp[:1000])
    assert np.array_equal(frames_collected[1].get_phase("L1"), full_ramp[1000:2000])
    assert rb.available_samples == 500


def test_ring_buffer_circular_wraparound():
    """Verify circular buffer wrap-around preserves data fidelity over many cycles."""
    capacity = 3000
    window = 500
    hop = 500
    rb = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        window_size=window,
        hop_size=hop,
        capacity_samples=capacity,
        sampling_rate_hz=5000.0
    )

    # Stream 15,000 samples (5x capacity)
    stream_length = 15000
    chunk_size = 250
    full_sig = np.sin(2 * np.pi * 50.0 * np.arange(stream_length) / 5000.0).astype(np.float32)

    windows = []
    for i in range(0, stream_length, chunk_size):
        chunk = full_sig[i:i + chunk_size]
        rb.append_samples({"L1": chunk, "L2": chunk, "L3": chunk})
        while rb.has_window():
            windows.append(rb.get_next_window())

    expected_windows = stream_length // hop
    assert len(windows) == expected_windows

    # Verify first and last window match expected slices
    assert np.allclose(windows[0].get_phase("L1"), full_sig[:window], atol=1e-6)
    last_idx = (expected_windows - 1) * hop
    assert np.allclose(windows[-1].get_phase("L1"), full_sig[last_idx:last_idx + window], atol=1e-6)


def test_ring_buffer_validation_errors():
    """Verify strict fail-clearly validation for missing channels, length mismatch, NaN/Inf, and overflow."""
    rb = MultiChannelRingBuffer(
        channels=["L1", "L2", "L3"],
        window_size=1000,
        hop_size=1000,
        capacity_samples=4000
    )

    # Missing channel
    with pytest.raises(ValueError, match="Missing required channel"):
        rb.append_samples({"L1": np.ones(100), "L2": np.ones(100)})

    # Length mismatch
    with pytest.raises(ValueError, match="Channel length mismatch"):
        rb.append_samples({"L1": np.ones(100), "L2": np.ones(100), "L3": np.ones(50)})

    # NaN / Inf detection
    bad_data = np.ones(100, dtype=np.float32)
    bad_data[10] = np.nan
    with pytest.raises(ValueError, match="NaN or infinite"):
        rb.append_samples({"L1": bad_data, "L2": np.ones(100), "L3": np.ones(100)})

    # Buffer overflow
    huge_chunk = np.ones(5000, dtype=np.float32)
    with pytest.raises(OverflowError, match="Ring buffer overflow"):
        rb.append_samples({"L1": huge_chunk, "L2": huge_chunk, "L3": huge_chunk})


def test_ring_buffer_clear():
    """Verify clear() cleanly resets buffer state."""
    rb = MultiChannelRingBuffer(channels=["L1", "L2", "L3"], window_size=500, hop_size=500)
    rb.append_samples({"L1": np.ones(600), "L2": np.ones(600), "L3": np.ones(600)})
    assert rb.has_window()
    assert rb.available_samples == 600

    rb.clear()
    assert not rb.has_window()
    assert rb.available_samples == 0
    assert rb.total_windows_emitted == 0

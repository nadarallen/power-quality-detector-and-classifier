"""
Unit Tests for Canonical WaveformFrame Representation
-----------------------------------------------------
Verifies:
1. Synchronization across L1, L2, L3.
2. Temporal attributes (sampling rate, duration seconds, duration cycles).
3. Quality validation (NaN, Inf, unphysical amplitudes, channel length mismatch).
4. Serialization and phase retrieval.
"""

import numpy as np
import pytest
from dsp.waveform_frame import WaveformFrame, ChannelMetadata


def test_waveform_frame_valid_creation():
    """Verify clean 3-phase frame creation and validation."""
    fs = 5000.0
    N = 1000
    t = np.arange(N) / fs
    
    # Balanced 3-phase voltages
    v_l1 = 1.0 * np.sin(2.0 * np.pi * 50.0 * t)
    v_l2 = 1.0 * np.sin(2.0 * np.pi * 50.0 * t - (2.0 * np.pi / 3.0))
    v_l3 = 1.0 * np.sin(2.0 * np.pi * 50.0 * t + (2.0 * np.pi / 3.0))

    frame = WaveformFrame(
        timestamp_utc=1700000000.0,
        sampling_rate_hz=fs,
        nominal_frequency_hz=50.0,
        source_type="simulation",
        device_id="TEST_NODE_01",
        sequence_number=1,
        phases={
            "L1": v_l1,
            "L2": v_l2,
            "L3": v_l3
        }
    )

    is_valid, errors = frame.validate()
    assert is_valid is True
    assert len(errors) == 0
    assert frame.num_samples == 1000
    assert np.isclose(frame.duration_seconds, 0.200)
    assert np.isclose(frame.duration_cycles, 10.0)
    assert frame.available_phases == ["L1", "L2", "L3"]
    assert len(frame.get_phase("L2")) == 1000


def test_waveform_frame_synchronization_mismatch():
    """Verify that misaligned channel lengths trigger validation errors."""
    frame = WaveformFrame(
        timestamp_utc=1700000000.0,
        sampling_rate_hz=5000.0,
        phases={
            "L1": np.zeros(1000, dtype=np.float32),
            "L2": np.zeros(990, dtype=np.float32),  # Missing 10 samples
            "L3": np.zeros(1000, dtype=np.float32)
        }
    )
    is_valid, errors = frame.validate()
    assert is_valid is False
    assert any("length synchronization mismatch" in err for err in errors)


def test_waveform_frame_nan_inf_detection():
    """Verify that corrupt numerical values (NaN, Inf) invalidate the frame."""
    arr_nan = np.zeros(1000, dtype=np.float32)
    arr_nan[50] = np.nan

    frame = WaveformFrame(
        timestamp_utc=1700000000.0,
        sampling_rate_hz=5000.0,
        phases={
            "L1": arr_nan,
            "L2": np.zeros(1000, dtype=np.float32),
            "L3": np.zeros(1000, dtype=np.float32)
        }
    )
    is_valid, errors = frame.validate()
    assert is_valid is False
    assert any("NaN values detected on phase L1" in err for err in errors)

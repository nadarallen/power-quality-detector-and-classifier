"""
Unit Tests for Acquisition Adapters (Simulation & CSV Replay)
------------------------------------------------------------
1. Verifies SimulationAdapter connects, generates synchronized 3-phase frames,
   and respects per-phase disturbance injections.
2. Verifies CSVReplayAdapter reads multi-phase CSVs and streams frames
   with monotonic sequence numbers without dropping channels.
3. Verifies CSVReplayAdapter FAILS CLEARLY on bad input:
   - missing L1/L2/L3 columns
   - invalid (<=0) sampling rate
   - NaN values in data slice
   - acquire_frame() called before connect()
"""

import numpy as np
import pandas as pd
import pytest

from dsp.acquisition_adapter import SimulationAdapter, CSVReplayAdapter
from dsp.waveform_frame import WaveformFrame


# ---------------------------------------------------------------------------
# SimulationAdapter
# ---------------------------------------------------------------------------

def test_simulation_adapter_basic_stream():
    """Verify SimulationAdapter connects and streams valid 3-phase frames."""
    sim = SimulationAdapter(sampling_rate_hz=5000.0, nominal_frequency_hz=50.0, window_samples=1000)
    assert sim.connect() is True

    frame = sim.acquire_frame()
    assert frame is not None
    assert frame.is_valid is True
    assert frame.num_samples == 1000
    assert frame.available_phases == ["L1", "L2", "L3"]
    assert frame.sequence_number == 1

    # Inject Sag on L2
    sim.set_phase_disturbance("L2", "Sag")
    frame2 = sim.acquire_frame()
    assert frame2 is not None
    assert frame2.sequence_number == 2
    # Verify L2 RMS is reduced relative to L1
    rms_l1 = float(np.sqrt(np.mean(frame2.get_phase("L1") ** 2)))
    rms_l2 = float(np.sqrt(np.mean(frame2.get_phase("L2") ** 2)))
    assert rms_l2 < rms_l1

    sim.disconnect()
    assert sim.acquire_frame() is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_normal_csv(tmp_path, n_rows: int = 2500) -> str:
    """Write a valid 3-phase balanced sinusoidal CSV."""
    path = str(tmp_path / "test_3phase.csv")
    t = np.arange(n_rows) / 5000.0
    pd.DataFrame({
        "L1": np.sin(2.0 * np.pi * 50.0 * t),
        "L2": np.sin(2.0 * np.pi * 50.0 * t - 2.094),
        "L3": np.sin(2.0 * np.pi * 50.0 * t + 2.094),
    }).to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# CSVReplayAdapter — happy path
# ---------------------------------------------------------------------------

def test_csv_replay_adapter(tmp_path):
    """Verify CSVReplayAdapter streams continuous multi-phase records accurately."""
    csv_file = _make_normal_csv(tmp_path, n_rows=2500)

    replay = CSVReplayAdapter(csv_path=csv_file, sampling_rate_hz=5000.0, window_samples=1000)
    assert replay.connect() is True

    frame1 = replay.acquire_frame()
    assert frame1 is not None
    assert frame1.num_samples == 1000
    assert frame1.sequence_number == 1

    frame2 = replay.acquire_frame()
    assert frame2 is not None
    assert frame2.num_samples == 1000
    assert frame2.sequence_number == 2

    # Remaining 500 samples < window_samples (1000) -> returns None (end-of-stream)
    frame3 = replay.acquire_frame()
    assert frame3 is None

    replay.disconnect()


# ---------------------------------------------------------------------------
# CSVReplayAdapter — strict validation (fail-clearly semantics)
# ---------------------------------------------------------------------------

def test_csv_replay_adapter_missing_columns_raises(tmp_path):
    """connect() must raise ValueError if L1/L2/L3 columns are absent."""
    path = str(tmp_path / "bad.csv")
    pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]}).to_csv(path, index=False)
    adapter = CSVReplayAdapter(csv_path=path, sampling_rate_hz=5000.0)
    with pytest.raises(ValueError, match="missing required phase column"):
        adapter.connect()


def test_csv_replay_adapter_invalid_sampling_rate_raises(tmp_path):
    """connect() must raise ValueError if sampling_rate_hz <= 0."""
    csv_file = _make_normal_csv(tmp_path)
    adapter = CSVReplayAdapter(csv_path=csv_file, sampling_rate_hz=-1.0)
    with pytest.raises(ValueError, match="invalid sampling_rate_hz"):
        adapter.connect()


def test_csv_replay_adapter_nan_data_raises(tmp_path):
    """acquire_frame() must raise ValueError on NaN data in a slice."""
    path = str(tmp_path / "nan.csv")
    t = np.arange(1000) / 5000.0
    df = pd.DataFrame({
        "L1": np.sin(2 * np.pi * 50 * t),
        "L2": np.where(t < 0.05, np.nan, np.sin(2 * np.pi * 50 * t)),
        "L3": np.sin(2 * np.pi * 50 * t),
    })
    df.to_csv(path, index=False)
    adapter = CSVReplayAdapter(csv_path=path, sampling_rate_hz=5000.0, window_samples=1000)
    adapter.connect()
    with pytest.raises(ValueError, match="NaN values"):
        adapter.acquire_frame()


def test_csv_replay_adapter_acquire_before_connect_raises(tmp_path):
    """acquire_frame() must raise RuntimeError if called before connect()."""
    csv_file = _make_normal_csv(tmp_path)
    adapter = CSVReplayAdapter(csv_path=csv_file, sampling_rate_hz=5000.0)
    with pytest.raises(RuntimeError, match="before connect"):
        adapter.acquire_frame()

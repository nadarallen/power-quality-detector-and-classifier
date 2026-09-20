"""
Unit Tests for Acquisition Adapters (Simulation & CSV Replay)
------------------------------------------------------------
1. Verifies SimulationAdapter connects, generates synchronized 3-phase frames,
   and respects per-phase disturbance injections.
2. Verifies CSVReplayAdapter reads multi-phase CSVs and streams frames
   with monotonic sequence numbers without dropping channels.
"""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest

from dsp.acquisition_adapter import SimulationAdapter, CSVReplayAdapter
from dsp.waveform_frame import WaveformFrame


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
    rms_l1 = np.sqrt(np.mean(frame2.get_phase("L1") ** 2))
    rms_l2 = np.sqrt(np.mean(frame2.get_phase("L2") ** 2))
    assert rms_l2 < rms_l1

    sim.disconnect()
    assert sim.acquire_frame() is None


def test_csv_replay_adapter(tmp_path):
    """Verify CSVReplayAdapter streams continuous multi-phase records accurately."""
    csv_file = tmp_path / "test_3phase.csv"
    N = 2500
    t = np.arange(N) / 5000.0
    df = pd.DataFrame({
        "L1": np.sin(2.0 * np.pi * 50.0 * t),
        "L2": np.sin(2.0 * np.pi * 50.0 * t - 2.094),
        "L3": np.sin(2.0 * np.pi * 50.0 * t + 2.094)
    })
    df.to_csv(csv_file, index=False)

    replay = CSVReplayAdapter(
        csv_path=str(csv_file),
        sampling_rate_hz=5000.0,
        window_samples=1000
    )
    assert replay.connect() is True

    frame1 = replay.acquire_frame()
    assert frame1 is not None
    assert frame1.num_samples == 1000
    assert frame1.sequence_number == 1

    frame2 = replay.acquire_frame()
    assert frame2 is not None
    assert frame2.num_samples == 1000
    assert frame2.sequence_number == 2

    # Remaining 500 samples is less than window_samples (1000) -> returns None
    frame3 = replay.acquire_frame()
    assert frame3 is None

    replay.disconnect()

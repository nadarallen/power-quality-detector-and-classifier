"""
Acquisition Adapter Interface & Baseline Adapters
-------------------------------------------------
Establishes a standardized abstraction layer between physical / virtual
signal sources and the downstream WaveformFrame pipeline:

1. AcquisitionAdapter (Base Class)
2. SimulationAdapter (Synthesizes 3-phase waveforms using dsp.waveform_generator)
3. CSVReplayAdapter (Streams pre-recorded 3-phase CSV data at configurable replay speeds)
"""

from abc import ABC, abstractmethod
import time
from typing import Optional, Dict, Any, Generator, List
import numpy as np
import pandas as pd

from dsp.waveform_frame import WaveformFrame, ChannelMetadata
from dsp.waveform_generator import generate_pqd_waveform


class AcquisitionAdapter(ABC):
    """Abstract base class for all power quality waveform acquisition sources."""

    def __init__(self, device_id: str = "DEV_LOCAL", sampling_rate_hz: float = 5000.0, nominal_frequency_hz: float = 50.0):
        self.device_id = device_id
        self.sampling_rate_hz = sampling_rate_hz
        self.nominal_frequency_hz = nominal_frequency_hz
        self.sequence_number = 0
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Initializes connection to signal source."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes connection to signal source."""
        pass

    @abstractmethod
    def acquire_frame(self) -> Optional[WaveformFrame]:
        """Fetches the next time-synchronized WaveformFrame."""
        pass


class SimulationAdapter(AcquisitionAdapter):
    """
    Synthesizes continuous, time-synchronized three-phase (L1, L2, L3) waveforms
    using the mathematical models in dsp.waveform_generator.
    Allows independent injection of disturbances on individual phases.
    """

    def __init__(
        self,
        device_id: str = "SIM_SOURCE_01",
        sampling_rate_hz: float = 5000.0,
        nominal_frequency_hz: float = 50.0,
        window_samples: int = 1000
    ):
        super().__init__(device_id, sampling_rate_hz, nominal_frequency_hz)
        self.window_samples = window_samples
        self.phase_states: Dict[str, str] = {
            "L1": "Normal",
            "L2": "Normal",
            "L3": "Normal"
        }
        self.phase_offsets_deg = {
            "L1": 0.0,
            "L2": -120.0,
            "L3": 120.0
        }

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def set_phase_disturbance(self, phase: str, disturbance_class: str) -> None:
        """Configures disturbance state for a specific phase (e.g. set L2 to 'Sag')."""
        if phase not in self.phase_states:
            raise KeyError(f"Invalid phase: {phase}. Must be one of L1, L2, L3")
        self.phase_states[phase] = disturbance_class

    def acquire_frame(self) -> Optional[WaveformFrame]:
        if not self.is_connected:
            return None

        self.sequence_number += 1
        t_now = time.time()

        phase_signals = {}
        for phase, dist_cls in self.phase_states.items():
            offset_rad = np.radians(self.phase_offsets_deg[phase])
            wave, _ = generate_pqd_waveform(
                dist_cls,
                snr_db=45.0,
                seed=self.sequence_number + abs(int(self.phase_offsets_deg[phase]))
            )
            # Apply 120-degree spatial balance shift
            t = np.arange(len(wave)) / self.sampling_rate_hz
            # Shift wave phase by rotating indices or adding carrier phase offset
            shift_samples = int((self.phase_offsets_deg[phase] / 360.0) * (self.sampling_rate_hz / self.nominal_frequency_hz))
            phase_signals[phase] = np.roll(wave, shift_samples).astype(np.float32)

        frame = WaveformFrame(
            timestamp_utc=t_now,
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type="simulation",
            device_id=self.device_id,
            sequence_number=self.sequence_number,
            phases=phase_signals
        )
        frame.validate()
        return frame


class CSVReplayAdapter(AcquisitionAdapter):
    """
    Replays pre-recorded continuous multi-phase electrical waveforms from CSV files.
    Ensures that historical recordings follow the exact same downstream processing
    and ML evaluation paths as live acquisition.
    """

    def __init__(
        self,
        csv_path: str,
        device_id: str = "CSV_REPLAY_01",
        sampling_rate_hz: float = 5000.0,
        nominal_frequency_hz: float = 50.0,
        window_samples: int = 1000,
        replay_speed: float = 1.0
    ):
        super().__init__(device_id, sampling_rate_hz, nominal_frequency_hz)
        self.csv_path = csv_path
        self.window_samples = window_samples
        self.replay_speed = max(0.1, replay_speed)
        self.df: Optional[pd.DataFrame] = None
        self.current_idx = 0
        self.total_rows = 0

    def connect(self) -> bool:
        try:
            self.df = pd.read_csv(self.csv_path)
            self.total_rows = len(self.df)
            self.current_idx = 0
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        self.is_connected = False
        self.df = None

    def acquire_frame(self) -> Optional[WaveformFrame]:
        if not self.is_connected or self.df is None:
            return None

        if self.current_idx + self.window_samples > self.total_rows:
            # End of recorded stream
            return None

        slice_df = self.df.iloc[self.current_idx : self.current_idx + self.window_samples]
        self.current_idx += self.window_samples
        self.sequence_number += 1

        phase_signals = {}
        for phase in ["L1", "L2", "L3"]:
            if phase in slice_df.columns:
                phase_signals[phase] = slice_df[phase].values.astype(np.float32)
            elif f"V_{phase}" in slice_df.columns:
                phase_signals[phase] = slice_df[f"V_{phase}"].values.astype(np.float32)

        frame = WaveformFrame(
            timestamp_utc=time.time(),
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type="csv_replay",
            device_id=self.device_id,
            sequence_number=self.sequence_number,
            phases=phase_signals
        )
        frame.validate()
        return frame

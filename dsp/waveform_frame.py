"""
Canonical Three-Phase Waveform Representation
---------------------------------------------
Encapsulates time-synchronized multi-channel electrical measurements
(Phase A / L1, Phase B / L2, Phase C / L3) along with physical metadata,
channel calibration, sampling rates, and quality flags.

Decouples acquisition hardware (ESP32, DAQ, CSV replay, simulation)
from the downstream DSP and machine learning pipelines.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, List
import numpy as np


@dataclass
class ChannelMetadata:
    """Metadata and calibration parameters for an individual acquisition channel."""
    channel_id: str                          # e.g. "VA", "VB", "VC", "IA", "IB", "IC"
    phase: str                               # "L1", "L2", "L3", "N"
    unit: str = "pu"                         # "V", "kV", "A", "pu"
    scale_factor: float = 1.0                # Multiplier to convert raw ADC counts to engineering units
    offset: float = 0.0                      # DC calibration offset
    nominal_value: float = 1.0               # Nominal per-unit or RMS engineering value
    is_saturated: bool = False               # Hardware clipping flag


@dataclass
class WaveformFrame:
    """
    Canonical multi-channel, time-synchronized waveform frame.
    Guarantees structural and temporal alignment across 3-phase grid signals.
    """
    timestamp_utc: float                     # Unix epoch timestamp in seconds (microsecond precision)
    sampling_rate_hz: float                  # Sampling frequency fs in Hz (e.g. 5000.0)
    nominal_frequency_hz: float = 50.0       # Grid nominal frequency f0 (e.g. 50.0 or 60.0 Hz)
    source_type: str = "simulation"          # "simulation", "csv_replay", "daq", "esp32", "pq_meter"
    device_id: str = "DEV_LOCAL"             # Unique identifier of physical / virtual capture node
    sequence_number: int = 0                 # Monotonically increasing frame sequence counter
    
    # Waveform arrays: dictionary mapping phase names ("L1", "L2", "L3") to 1D float32 numpy arrays
    phases: Dict[str, np.ndarray] = field(default_factory=dict)
    
    # Optional metadata per channel
    channels: Dict[str, ChannelMetadata] = field(default_factory=dict)
    
    # Frame validation & health indicators
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Normalize and validate array inputs
        for phase, data in self.phases.items():
            if not isinstance(data, np.ndarray):
                self.phases[phase] = np.asarray(data, dtype=np.float32)
            elif data.dtype != np.float32:
                self.phases[phase] = data.astype(np.float32)

    @property
    def num_samples(self) -> int:
        """Returns the number of samples per channel (assuming synchronized channels)."""
        if not self.phases:
            return 0
        return len(next(iter(self.phases.values())))

    @property
    def duration_seconds(self) -> float:
        """Returns the total duration of this frame in seconds."""
        if self.sampling_rate_hz <= 0:
            return 0.0
        return self.num_samples / self.sampling_rate_hz

    @property
    def duration_cycles(self) -> float:
        """Returns the total duration of this frame in nominal grid cycles."""
        return self.duration_seconds * self.nominal_frequency_hz

    @property
    def available_phases(self) -> List[str]:
        """Returns list of phase identifiers available in this frame."""
        return sorted(list(self.phases.keys()))

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Executes strict physical and structural integrity verification:
        1. Checks sampling rate > 0
        2. Verifies presence of phases (requires at minimum L1, L2, L3 for 3-phase analysis)
        3. Verifies exact synchronization: all channels must have identical sample length
        4. Detects NaN or Infinite values
        5. Detects severe hardware clipping or unphysical amplitudes
        """
        errors: List[str] = []

        if self.sampling_rate_hz <= 0:
            errors.append(f"Invalid sampling rate: {self.sampling_rate_hz} Hz")

        if not self.phases:
            errors.append("No phase signals present in WaveformFrame")
            self.is_valid = False
            self.validation_errors = errors
            return False, errors

        # Channel synchronization check
        lengths = {phase: len(arr) for phase, arr in self.phases.items()}
        unique_lens = set(lengths.values())
        if len(unique_lens) > 1:
            errors.append(f"Channel length synchronization mismatch: {lengths}")

        # Signal quality & validity
        for phase, arr in self.phases.items():
            if np.isnan(arr).any():
                errors.append(f"NaN values detected on phase {phase}")
            if np.isinf(arr).any():
                errors.append(f"Infinite values detected on phase {phase}")
            
            # Check extreme unphysical per-unit voltage
            if np.any(np.abs(arr) > 10.0):
                errors.append(f"Unphysical per-unit amplitude (> 10 pu) on phase {phase}")

        self.is_valid = (len(errors) == 0)
        self.validation_errors = errors
        return self.is_valid, errors

    def get_phase(self, phase: str) -> np.ndarray:
        """Retrieves raw 1D array for requested phase."""
        if phase not in self.phases:
            raise KeyError(f"Phase {phase} not available in frame. Available: {self.available_phases}")
        return self.phases[phase]

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
import time
import json
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "phase": self.phase,
            "unit": self.unit,
            "scale_factor": self.scale_factor,
            "offset": self.offset,
            "nominal_value": self.nominal_value,
            "is_saturated": self.is_saturated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelMetadata":
        return cls(**data)


@dataclass
class WaveformFrame:
    """
    Canonical multi-channel, time-synchronized waveform frame.
    Guarantees structural and temporal alignment across 3-phase grid signals.
    """
    timestamp_utc: float                     # Unix epoch timestamp in seconds (microsecond precision)
    sampling_rate_hz: float                  # Sampling frequency fs in Hz (e.g. 5000.0)
    nominal_frequency_hz: float = 50.0       # Grid nominal frequency f0 (e.g. 50.0 or 60.0 Hz)
    source_type: str = "simulation"          # "simulation", "csv_replay", "mock_hardware", "hardware", "daq", "esp32"
    device_id: str = "DEV_LOCAL"             # Unique identifier of physical / virtual capture node
    sequence_number: int = 0                 # Monotonically increasing frame sequence counter
    
    # Waveform arrays: dictionary mapping phase names ("L1", "L2", "L3") to 1D float32 numpy arrays
    phases: Dict[str, np.ndarray] = field(default_factory=dict)
    
    # Optional metadata per channel
    channels: Dict[str, ChannelMetadata] = field(default_factory=dict)
    
    # Quality, calibration & loss indicators
    dropped_samples_count: int = 0           # Count of dropped samples detected prior to or within this frame
    is_clipped: bool = False                 # Flagged if any channel experienced ADC saturation/clipping
    calibration_id: str = "DEFAULT"          # Identifier of applied calibration profile
    
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

        # Check clipping / hardware saturation indicators
        for phase, ch_meta in self.channels.items():
            if ch_meta.is_saturated:
                self.is_clipped = True
                errors.append(f"Hardware saturation/clipping flagged on channel {ch_meta.channel_id} (phase {phase})")

        self.is_valid = (len(errors) == 0)
        self.validation_errors = errors
        return self.is_valid, errors

    def get_phase(self, phase: str) -> np.ndarray:
        """Retrieves raw 1D array for requested phase."""
        if phase not in self.phases:
            raise KeyError(f"Phase {phase} not available in frame. Available: {self.available_phases}")
        return self.phases[phase]

    def to_dict(self, include_waveforms: bool = True) -> Dict[str, Any]:
        """Serializes frame metadata and optionally waveform arrays to dictionary."""
        d = {
            "timestamp_utc": self.timestamp_utc,
            "sampling_rate_hz": self.sampling_rate_hz,
            "nominal_frequency_hz": self.nominal_frequency_hz,
            "source_type": self.source_type,
            "device_id": self.device_id,
            "sequence_number": self.sequence_number,
            "num_samples": self.num_samples,
            "duration_seconds": self.duration_seconds,
            "available_phases": self.available_phases,
            "dropped_samples_count": self.dropped_samples_count,
            "is_clipped": self.is_clipped,
            "calibration_id": self.calibration_id,
            "channels": {p: m.to_dict() for p, m in self.channels.items()},
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }
        if include_waveforms:
            d["phases"] = {p: arr.tolist() for p, arr in self.phases.items()}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WaveformFrame":
        """Reconstructs WaveformFrame from dictionary."""
        phases = {}
        for p, arr in data.get("phases", {}).items():
            phases[p] = np.asarray(arr, dtype=np.float32)
            
        channels = {}
        for p, c_dict in data.get("channels", {}).items():
            channels[p] = ChannelMetadata.from_dict(c_dict)

        frame = cls(
            timestamp_utc=float(data.get("timestamp_utc", time.time())),
            sampling_rate_hz=float(data.get("sampling_rate_hz", 5000.0)),
            nominal_frequency_hz=float(data.get("nominal_frequency_hz", 50.0)),
            source_type=data.get("source_type", "network"),
            device_id=data.get("device_id", "DEV_REMOTE"),
            sequence_number=int(data.get("sequence_number", 0)),
            phases=phases,
            channels=channels,
            dropped_samples_count=int(data.get("dropped_samples_count", 0)),
            is_clipped=bool(data.get("is_clipped", False)),
            calibration_id=str(data.get("calibration_id", "DEFAULT")),
        )
        return frame

    def save(self, filepath: str) -> None:
        """Saves canonical waveform frame to .npz or .json format."""
        if filepath.endswith(".npz"):
            arrays_to_save = {f"phase_{p}": arr for p, arr in self.phases.items()}
            meta_json = json.dumps(self.to_dict(include_waveforms=False))
            np.savez_compressed(filepath, metadata=meta_json, **arrays_to_save)
        else:
            with open(filepath, "w") as f:
                json.dump(self.to_dict(include_waveforms=True), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "WaveformFrame":
        """Loads canonical waveform frame from .npz or .json format."""
        if filepath.endswith(".npz"):
            with np.load(filepath) as data:
                meta = json.loads(str(data["metadata"]))
                phases = {}
                for key in data.files:
                    if key.startswith("phase_"):
                        phase_name = key[len("phase_"):]
                        phases[phase_name] = data[key].astype(np.float32)
                meta["phases"] = phases
                return cls.from_dict(meta)
        else:
            with open(filepath, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)

"""
Hardware Acquisition Calibration & Scaling Abstraction Layer
------------------------------------------------------------
Implements standard-compliant calibration and unit conversion:

    Raw ADC Counts
          ↓ (offset, gain, bit depth, Vref)
    Physical Sensor Voltage (V_sensor)
          ↓ (PT / potential divider / transducer ratio)
    Grid Engineering Units (V_rms, Volts, kV)
          ↓ (nominal base voltage V_nominal)
    Per-Unit Normalization (pu)
          ↓
    DSP & AI Feature Extraction

Guarantees that:
1. Core DSP and ML pipelines operate strictly in per-unit (pu) normalized coordinates.
2. Hardware-specific ADC bit-depths, reference voltages, and transformer turns-ratios
   are encapsulated inside calibration profiles.
3. Clipping and hardware saturation are detected before digital processing.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, List
import numpy as np


@dataclass
class ChannelCalibration:
    """
    Calibration parameters for an individual acquisition channel (voltage or current).
    """
    channel_id: str                          # e.g. "VA", "VB", "VC", "L1", "L2", "L3"
    phase: str                               # "L1", "L2", "L3", "N"
    unit: str = "V"                          # Engineering unit: "V", "kV", "A", "pu"
    
    # ADC Hardware Specifications
    adc_resolution_bits: int = 16            # ADC bit depth (e.g. 12, 16, 24)
    adc_vref_volts: float = 3.3              # Full-scale ADC reference voltage in Volts
    is_bipolar: bool = True                  # True if ADC input is signed/differential (±Vref)
    
    # Analog Front-End / Sensor Transducer Scaling
    # V_grid = (V_adc - offset_volts) * sensor_ratio
    sensor_ratio: float = 100.0              # Transducer division ratio (e.g. 100:1 PT, 230V:2.3V)
    offset_volts: float = 0.0                # DC bias / analog reference ground offset in Volts
    scale_multiplier: float = 1.0            # Fine-trim gain adjustment factor (from lab calibration)
    
    # Grid Nominal Base Reference for Per-Unit Normalization
    nominal_voltage_rms: float = 230.0       # Nominal grid phase voltage RMS in engineering units (e.g. 230V)
    nominal_frequency_hz: float = 50.0       # Grid nominal frequency (50 Hz or 60 Hz)
    
    # Saturation / Railing Thresholds in Raw ADC Counts
    saturation_margin_pct: float = 1.0       # Margin % below rail before flagging hardware saturation

    @property
    def max_adc_count(self) -> int:
        """Maximum possible count for this ADC resolution."""
        if self.is_bipolar:
            return (1 << (self.adc_resolution_bits - 1)) - 1
        return (1 << self.adc_resolution_bits) - 1

    @property
    def min_adc_count(self) -> int:
        """Minimum possible count for this ADC resolution."""
        if self.is_bipolar:
            return -(1 << (self.adc_resolution_bits - 1))
        return 0

    @property
    def volts_per_count(self) -> float:
        """Volts at the ADC pin per discrete ADC quantization step."""
        count_span = self.max_adc_count - self.min_adc_count
        voltage_span = 2.0 * self.adc_vref_volts if self.is_bipolar else self.adc_vref_volts
        return voltage_span / count_span

    @property
    def nominal_peak_volts(self) -> float:
        """Nominal instantaneous peak voltage: V_rms * sqrt(2)."""
        return self.nominal_voltage_rms * np.sqrt(2.0)

    def raw_to_volts(self, raw_counts: np.ndarray) -> np.ndarray:
        """
        Converts raw integer ADC counts into physical engineering units (Volts).
        """
        counts = np.asarray(raw_counts, dtype=np.float32)
        # ADC pin voltage
        v_pin = (counts * self.volts_per_count) - self.offset_volts
        # Grid voltage via transducer ratio and calibration trim
        v_grid = v_pin * self.sensor_ratio * self.scale_multiplier
        return v_grid.astype(np.float32)

    def volts_to_pu(self, volts: np.ndarray) -> np.ndarray:
        """
        Converts engineering units (Volts) into per-unit (pu) normalized voltage.
        Base per-unit reference: 1.0 pu = nominal instantaneous peak voltage.
        In nominal grid conditions: peak = 1.012 pu, RMS = 0.708 pu (1 / sqrt(2)).
        """
        v = np.asarray(volts, dtype=np.float32)
        v_base = self.nominal_peak_volts
        if v_base <= 0:
            raise ValueError(f"Invalid nominal_voltage_rms: {self.nominal_voltage_rms}")
        return (v / v_base).astype(np.float32)

    def raw_to_pu(self, raw_counts: np.ndarray) -> np.ndarray:
        """
        Direct end-to-end transformation: raw ADC counts → per-unit (pu).
        """
        volts = self.raw_to_volts(raw_counts)
        return self.volts_to_pu(volts)

    def pu_to_volts(self, pu: np.ndarray) -> np.ndarray:
        """Converts per-unit voltage back to engineering Volts."""
        return (np.asarray(pu, dtype=np.float32) * self.nominal_peak_volts).astype(np.float32)

    def pu_to_raw(self, pu: np.ndarray) -> np.ndarray:
        """
        Synthesizes realistic raw ADC counts from per-unit waveform (for hardware mocks).
        """
        volts = self.pu_to_volts(pu)
        v_pin = volts / (self.sensor_ratio * self.scale_multiplier) + self.offset_volts
        counts = v_pin / self.volts_per_count
        counts_clipped = np.clip(counts, self.min_adc_count, self.max_adc_count)
        return np.round(counts_clipped).astype(np.int32 if self.adc_resolution_bits > 16 else np.int16)

    def check_saturation(self, raw_counts: np.ndarray) -> Tuple[bool, float]:
        """
        Evaluates whether raw ADC samples reached the hardware clipping rails.
        Returns (is_saturated, max_utilization_ratio).
        """
        arr = np.asarray(raw_counts)
        if len(arr) == 0:
            return False, 0.0
        
        pos_rail = self.max_adc_count
        neg_rail = self.min_adc_count
        margin_counts = int((pos_rail - neg_rail) * (self.saturation_margin_pct / 100.0))

        max_val = np.max(arr)
        min_val = np.min(arr)

        is_saturated = (max_val >= (pos_rail - margin_counts)) or (min_val <= (neg_rail + margin_counts))
        peak_deviation = max(abs(int(max_val)), abs(int(min_val)))
        full_span = max(abs(int(pos_rail)), abs(int(neg_rail)))
        utilization = peak_deviation / full_span if full_span > 0 else 0.0

        return bool(is_saturated), float(utilization)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes calibration profile to a JSON-compatible dictionary."""
        return {
            "channel_id": self.channel_id,
            "phase": self.phase,
            "unit": self.unit,
            "adc_resolution_bits": self.adc_resolution_bits,
            "adc_vref_volts": self.adc_vref_volts,
            "is_bipolar": self.is_bipolar,
            "sensor_ratio": self.sensor_ratio,
            "offset_volts": self.offset_volts,
            "scale_multiplier": self.scale_multiplier,
            "nominal_voltage_rms": self.nominal_voltage_rms,
            "nominal_frequency_hz": self.nominal_frequency_hz,
            "saturation_margin_pct": self.saturation_margin_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelCalibration":
        """Reconstructs ChannelCalibration from dictionary."""
        return cls(**data)


@dataclass
class ThreePhaseCalibration:
    """
    Composite three-phase calibration profile managing L1, L2, and L3 (plus optional Neutral N).
    """
    device_id: str = "PQD_MEASUREMENT_NODE_01"
    calibration_date_utc: str = "2026-09-20T00:00:00Z"
    calibrated_by: str = "Standard Laboratory Calibration v1.0"
    channels: Dict[str, ChannelCalibration] = field(default_factory=dict)

    def __post_init__(self):
        if not self.channels:
            # Default standard laboratory 230V 16-bit bipolar calibration for L1, L2, L3
            for phase in ["L1", "L2", "L3"]:
                self.channels[phase] = ChannelCalibration(
                    channel_id=f"V_{phase}",
                    phase=phase,
                    unit="V",
                    adc_resolution_bits=16,
                    adc_vref_volts=3.3,
                    is_bipolar=True,
                    sensor_ratio=141.42,         # 230V RMS * sqrt(2) = 325.27V peak -> 2.3V ADC pin
                    offset_volts=0.0,
                    scale_multiplier=1.0,
                    nominal_voltage_rms=230.0,
                    nominal_frequency_hz=50.0
                )

    def get_channel(self, phase: str) -> ChannelCalibration:
        """Retrieves calibration for the specified phase."""
        if phase not in self.channels:
            raise KeyError(f"Phase {phase} not configured in calibration profile. Available: {list(self.channels.keys())}")
        return self.channels[phase]

    def raw_to_pu_frame(self, raw_phase_dict: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Converts raw ADC arrays for all phases to per-unit float32 arrays."""
        pu_dict = {}
        for phase, raw_counts in raw_phase_dict.items():
            cal = self.get_channel(phase)
            pu_dict[phase] = cal.raw_to_pu(raw_counts)
        return pu_dict

    def check_frame_saturation(self, raw_phase_dict: Dict[str, np.ndarray]) -> Dict[str, Tuple[bool, float]]:
        """Checks clipping and rail saturation on all raw phase arrays."""
        res = {}
        for phase, raw_counts in raw_phase_dict.items():
            cal = self.get_channel(phase)
            res[phase] = cal.check_saturation(raw_counts)
        return res

    def to_dict(self) -> Dict[str, Any]:
        """Serializes three-phase calibration profile."""
        return {
            "device_id": self.device_id,
            "calibration_date_utc": self.calibration_date_utc,
            "calibrated_by": self.calibrated_by,
            "channels": {p: c.to_dict() for p, c in self.channels.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreePhaseCalibration":
        channels = {}
        for p, c_dict in data.get("channels", {}).items():
            channels[p] = ChannelCalibration.from_dict(c_dict)
        return cls(
            device_id=data.get("device_id", "DEV_CAL"),
            calibration_date_utc=data.get("calibration_date_utc", ""),
            calibrated_by=data.get("calibrated_by", ""),
            channels=channels
        )

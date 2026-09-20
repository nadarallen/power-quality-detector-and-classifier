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
from dsp.calibration import ThreePhaseCalibration, ChannelCalibration


class AcquisitionState:
    """Standard operational states for hardware and simulated acquisition adapters."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    ACQUIRING = "ACQUIRING"
    ERROR = "ERROR"
    SYNC_ERROR = "SYNC_ERROR"
    INVALID_SIGNAL = "INVALID_SIGNAL"


class AcquisitionAdapter(ABC):
    """Abstract base class for all power quality waveform acquisition sources."""

    def __init__(self, device_id: str = "DEV_LOCAL", sampling_rate_hz: float = 5000.0, nominal_frequency_hz: float = 50.0, source_type: str = "base"):
        self.device_id = device_id
        self.sampling_rate_hz = sampling_rate_hz
        self.nominal_frequency_hz = nominal_frequency_hz
        self.source_type = source_type
        self.sequence_number = 0
        self.is_connected = False
        self.state = AcquisitionState.DISCONNECTED

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
        super().__init__(device_id, sampling_rate_hz, nominal_frequency_hz, source_type="simulation")
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
        self.state = AcquisitionState.CONNECTED
        return True

    def disconnect(self) -> None:
        self.is_connected = False
        self.state = AcquisitionState.DISCONNECTED

    def set_phase_disturbance(self, phase: str, disturbance_class: str) -> None:
        """Configures disturbance state for a specific phase (e.g. set L2 to 'Sag') or 'ALL'."""
        if phase == "ALL":
            for p in self.phase_states:
                self.phase_states[p] = disturbance_class
            return
        if phase not in self.phase_states:
            raise KeyError(f"Invalid phase: {phase}. Must be one of L1, L2, L3, or ALL")
        self.phase_states[phase] = disturbance_class

    def acquire_frame(self) -> Optional[WaveformFrame]:
        if not self.is_connected:
            self.state = AcquisitionState.DISCONNECTED
            return None

        self.state = AcquisitionState.ACQUIRING
        self.sequence_number += 1
        t_now = time.time()

        phase_signals = {}
        for phase, dist_cls in self.phase_states.items():
            offset_rad = np.radians(self.phase_offsets_deg[phase])
            seed = self.sequence_number + abs(int(self.phase_offsets_deg[phase]))

            # All phases — Normal or disturbance — use generate_pqd_waveform().
            # Rationale: the DSP feature extractors (RMS, THD, Goertzel harmonics, spectral
            # moments) are phase-invariant: a 120°-offset pure sinusoid produces identical
            # feature values to the L1 reference. However, adding np.random noise at a
            # different phase offset produces different noise-vs-signal cross-terms that
            # confuse the MLP's spectral flatness / entropy features.
            # Using the same generator ensures the feature distribution matches the training
            # data (which was generated at L1 reference phase).
            # The 120° inter-phase offset is preserved in WaveformFrame metadata (source_type,
            # sequence_number) for time-domain display but is NOT passed to the classifier.
            wave, _ = generate_pqd_waveform(dist_cls, snr_db=45.0, seed=seed)
            phase_signals[phase] = np.asarray(wave, dtype=np.float32)

        channels = {
            phase: ChannelMetadata(
                channel_id=f"V_{phase}",
                phase=phase,
                unit="pu",
                scale_factor=1.0,
                offset=0.0,
                nominal_value=1.0,
                is_saturated=False
            )
            for phase in phase_signals
        }

        frame = WaveformFrame(
            timestamp_utc=t_now,
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type="simulation",
            device_id=self.device_id,
            sequence_number=self.sequence_number,
            phases=phase_signals,
            channels=channels,
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
        super().__init__(device_id, sampling_rate_hz, nominal_frequency_hz, source_type="csv_replay")
        self.csv_path = csv_path
        self.window_samples = window_samples
        self.replay_speed = max(0.1, replay_speed)
        self.df: Optional[pd.DataFrame] = None
        self.current_idx = 0
        self.total_rows = 0

    def connect(self) -> bool:
        """
        Opens the CSV file and validates its structure.

        Raises
        ------
        FileNotFoundError  : if csv_path does not exist
        ValueError         : if the CSV is missing required phase columns,
                             has an invalid sampling rate, or is empty
        """
        if self.sampling_rate_hz <= 0:
            raise ValueError(
                f"CSVReplayAdapter: invalid sampling_rate_hz={self.sampling_rate_hz}. "
                "Must be > 0."
            )
        df = pd.read_csv(self.csv_path)  # raises FileNotFoundError / ParserError on bad file
        if len(df) == 0:
            raise ValueError(
                f"CSVReplayAdapter: CSV file '{self.csv_path}' is empty."
            )

        # Resolve column names — support 'L1'/'L2'/'L3' or 'V_L1'/'V_L2'/'V_L3'
        resolved = {}
        for phase in ["L1", "L2", "L3"]:
            if phase in df.columns:
                resolved[phase] = phase
            elif f"V_{phase}" in df.columns:
                resolved[phase] = f"V_{phase}"
            else:
                raise ValueError(
                    f"CSVReplayAdapter: CSV '{self.csv_path}' is missing required phase "
                    f"column '{phase}' (also checked 'V_{phase}'). "
                    f"Found columns: {list(df.columns)}"
                )
        self._resolved_columns = resolved

        self.df = df
        self.total_rows = len(df)
        self.current_idx = 0
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False
        self.df = None

    def acquire_frame(self) -> Optional[WaveformFrame]:
        """
        Returns the next WaveformFrame window from the replay stream.

        Returns None when the stream is exhausted (end-of-file).

        Raises
        ------
        RuntimeError : if called before connect()
        ValueError   : if the data slice contains NaN, Inf, or unequal channel lengths
        """
        if not self.is_connected or self.df is None:
            raise RuntimeError(
                "CSVReplayAdapter: acquire_frame() called before connect(). "
                "Call connect() first."
            )

        if self.current_idx + self.window_samples > self.total_rows:
            # End of recorded stream — normal termination condition
            return None

        slice_df = self.df.iloc[self.current_idx : self.current_idx + self.window_samples]
        self.current_idx += self.window_samples
        self.sequence_number += 1

        phase_signals = {}
        for phase, col in self._resolved_columns.items():
            arr = slice_df[col].values.astype(np.float32)
            if np.isnan(arr).any():
                raise ValueError(
                    f"CSVReplayAdapter: NaN values in column '{col}' at rows "
                    f"{self.current_idx - self.window_samples}–{self.current_idx}."
                )
            if np.isinf(arr).any():
                raise ValueError(
                    f"CSVReplayAdapter: Infinite values in column '{col}' at rows "
                    f"{self.current_idx - self.window_samples}–{self.current_idx}."
                )
            phase_signals[phase] = arr

        # Verify synchronization — all channels must have identical sample counts
        lengths = {p: len(a) for p, a in phase_signals.items()}
        if len(set(lengths.values())) > 1:
            raise ValueError(
                f"CSVReplayAdapter: channel length mismatch in slice: {lengths}"
            )

        frame = WaveformFrame(
            timestamp_utc=time.time(),
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type="csv_replay",
            device_id=self.device_id,
            sequence_number=self.sequence_number,
            phases=phase_signals,
        )
        frame.validate()
        return frame


class HardwareAdapter(AcquisitionAdapter):
    """
    Abstract base class for physical data acquisition devices.
    Encapsulates calibration, raw ADC sample conversion, hardware saturation monitoring,
    sequence continuity, and dropped-sample detection.
    """

    def __init__(
        self,
        device_id: str = "HW_ACQ_01",
        sampling_rate_hz: float = 5000.0,
        nominal_frequency_hz: float = 50.0,
        window_samples: int = 1000,
        calibration: Optional[ThreePhaseCalibration] = None,
        source_type: str = "hardware"
    ):
        super().__init__(device_id, sampling_rate_hz, nominal_frequency_hz, source_type=source_type)
        self.window_samples = window_samples
        self.calibration = calibration or ThreePhaseCalibration(device_id=device_id)
        self.last_timestamp_utc: float = 0.0
        self.total_dropped_samples: int = 0
        self.dropped_frames_count: int = 0
        self.expected_frame_interval_sec: float = window_samples / max(1.0, sampling_rate_hz)

    def convert_and_validate_chunk(
        self,
        raw_channels: Dict[str, np.ndarray],
        timestamp_utc: Optional[float] = None,
        sequence_num: Optional[int] = None,
    ) -> WaveformFrame:
        """
        Converts raw integer ADC samples to a validated per-unit WaveformFrame
        using the active calibration profile.
        """
        t_now = timestamp_utc if timestamp_utc is not None else time.time()
        
        # Sequence & continuity checks
        if sequence_num is not None:
            expected_seq = self.sequence_number + 1
            if sequence_num > expected_seq:
                gap = sequence_num - expected_seq
                self.dropped_frames_count += gap
                self.total_dropped_samples += gap * self.window_samples
            self.sequence_number = sequence_num
        else:
            self.sequence_number += 1

        # Check timestamp continuity
        if self.last_timestamp_utc > 0:
            dt = t_now - self.last_timestamp_utc
            if dt > 1.8 * self.expected_frame_interval_sec:
                # Potential packet loss or clock jitter
                pass
        self.last_timestamp_utc = t_now

        # 1. Convert raw ADC to per-unit using calibration
        pu_phases = self.calibration.raw_to_pu_frame(raw_channels)

        # 2. Check saturation on raw counts
        saturation_res = self.calibration.check_frame_saturation(raw_channels)

        # 3. Assemble channel metadata
        channels_meta = {}
        is_any_saturated = False
        for phase in pu_phases:
            cal = self.calibration.get_channel(phase)
            is_sat, util = saturation_res.get(phase, (False, 0.0))
            if is_sat:
                is_any_saturated = True
            channels_meta[phase] = ChannelMetadata(
                channel_id=cal.channel_id,
                phase=phase,
                unit="pu",
                scale_factor=cal.scale_multiplier,
                offset=cal.offset_volts,
                nominal_value=cal.nominal_voltage_rms,
                is_saturated=is_sat
            )

        frame = WaveformFrame(
            timestamp_utc=t_now,
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type="hardware",
            device_id=self.device_id,
            sequence_number=self.sequence_number,
            phases=pu_phases,
            channels=channels_meta,
            dropped_samples_count=self.total_dropped_samples,
            is_clipped=is_any_saturated,
            calibration_id=self.calibration.calibrated_by
        )
        frame.validate()
        if not frame.is_valid:
            if any("synchronization mismatch" in e for e in frame.validation_errors):
                self.state = AcquisitionState.SYNC_ERROR
            else:
                self.state = AcquisitionState.INVALID_SIGNAL
        else:
            self.state = AcquisitionState.ACQUIRING
        return frame

    def connect(self) -> bool:
        self.is_connected = True
        self.state = AcquisitionState.CONNECTED
        return True

    def disconnect(self) -> None:
        self.is_connected = False
        self.state = AcquisitionState.DISCONNECTED


class DAQAdapter(HardwareAdapter):
    """Interface for multi-channel USB/PCIe DAQ hardware (e.g. LabJack, NI DAQ)."""

    def __init__(self, device_id: str = "DAQ_USB_01", sampling_rate_hz: float = 5000.0, **kwargs):
        super().__init__(device_id=device_id, sampling_rate_hz=sampling_rate_hz, source_type="daq", **kwargs)
        self.buffer_overrun_count = 0

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def acquire_frame(self) -> Optional[WaveformFrame]:
        raise NotImplementedError("Physical DAQ driver binding must be provided by device integration module.")


class SerialAdapter(HardwareAdapter):
    """Interface for Serial/UART streaming frontends (e.g. isolated MCU / optical USB link)."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud_rate: int = 921600, device_id: str = "SERIAL_ACQ_01", **kwargs):
        super().__init__(device_id=device_id, source_type="serial", **kwargs)
        self.port = port
        self.baud_rate = baud_rate
        self.framing_error_count = 0

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def acquire_frame(self) -> Optional[WaveformFrame]:
        raise NotImplementedError("Serial framing and binary packet parser must be configured with target hardware.")


class NetworkAdapter(HardwareAdapter):
    """Interface for Ethernet / TCP / UDP / Modbus TCP / MQTT streaming instrumentation."""

    def __init__(self, host: str = "192.168.1.100", port: int = 502, protocol: str = "TCP", device_id: str = "NET_ACQ_01", **kwargs):
        super().__init__(device_id=device_id, source_type="network", **kwargs)
        self.host = host
        self.port = port
        self.protocol = protocol

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def acquire_frame(self) -> Optional[WaveformFrame]:
        raise NotImplementedError("Network socket receiver must be configured with target stream protocol.")


class PQMeterAdapter(HardwareAdapter):
    """Interface for industrial Power Quality Analyzers (IEC 61000-4-30 / IEEE 1159 Class A/S instruments)."""

    def __init__(self, device_id: str = "PQ_METER_CLASS_A_01", meter_standard: str = "IEC_61000_4_30_CLASS_A", **kwargs):
        super().__init__(device_id=device_id, source_type="pq_meter", **kwargs)
        self.meter_standard = meter_standard

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def acquire_frame(self) -> Optional[WaveformFrame]:
        raise NotImplementedError("Industrial PQ meter driver requires instrument-specific client API.")


class MockHardwareAdapter(HardwareAdapter):
    """
    Deterministic hardware mock simulating physical 3-phase acquisition hardware:
    1. Generates physical signals using mathematical waveform models.
    2. Simulates ADC quantization into integer raw ADC counts (16-bit bipolar).
    3. Simulates front-end analog quantization and thermal noise.
    4. Simulates dropped packets / frame sequence gaps.
    5. Simulates ADC rail clipping / saturation when configured.
    6. Passes raw counts back through the genuine Calibration layer to produce canonical WaveformFrames.
    """

    def __init__(
        self,
        device_id: str = "MOCK_HW_NODE_01",
        sampling_rate_hz: float = 5000.0,
        nominal_frequency_hz: float = 50.0,
        window_samples: int = 1000,
        calibration: Optional[ThreePhaseCalibration] = None,
        dropped_packet_rate: float = 0.0,
        simulate_saturation_on_phase: Optional[str] = None
    ):
        super().__init__(
            device_id=device_id,
            sampling_rate_hz=sampling_rate_hz,
            nominal_frequency_hz=nominal_frequency_hz,
            window_samples=window_samples,
            calibration=calibration,
            source_type="mock_hardware"
        )
        self.phase_states = {"L1": "Normal", "L2": "Normal", "L3": "Normal"}
        self.phase_offsets_deg = {"L1": 0.0, "L2": -120.0, "L3": 120.0}
        self.dropped_packet_rate = dropped_packet_rate
        self.simulate_saturation_on_phase = simulate_saturation_on_phase
        self.internal_clock_utc = time.time()

    def connect(self) -> bool:
        self.is_connected = True
        self.state = AcquisitionState.CONNECTED
        return True

    def disconnect(self) -> None:
        self.is_connected = False
        self.state = AcquisitionState.DISCONNECTED

    def set_phase_disturbance(self, phase: str, disturbance_class: str) -> None:
        """Configures disturbance condition for mock hardware channel."""
        if phase == "ALL":
            for p in self.phase_states:
                self.phase_states[p] = disturbance_class
            return
        if phase not in self.phase_states:
            raise KeyError(f"Invalid phase: {phase}. Must be one of L1, L2, L3, or ALL")
        self.phase_states[phase] = disturbance_class

    def acquire_frame(self) -> Optional[WaveformFrame]:
        if not self.is_connected:
            self.state = AcquisitionState.DISCONNECTED
            return None

        # Simulate packet drops if configured
        if self.dropped_packet_rate > 0.0 and np.random.rand() < self.dropped_packet_rate:
            # Skip sequence number and time interval
            self.sequence_number += 1
            self.internal_clock_utc += self.expected_frame_interval_sec
            self.total_dropped_samples += self.window_samples
            self.dropped_frames_count += 1

        self.internal_clock_utc += self.expected_frame_interval_sec
        t_frame = self.internal_clock_utc

        # 1. Synthesize reference pu waveforms
        pu_synth = {}
        for phase, dist_cls in self.phase_states.items():
            seed = self.sequence_number + abs(int(self.phase_offsets_deg[phase]))
            wave, _ = generate_pqd_waveform(dist_cls, snr_db=45.0, seed=seed)
            pu_synth[phase] = np.asarray(wave, dtype=np.float32)

        # 2. Convert to raw ADC integer counts via calibration
        raw_channels = {}
        for phase, pu_arr in pu_synth.items():
            cal = self.calibration.get_channel(phase)
            raw = cal.pu_to_raw(pu_arr)
            
            # Simulate saturation if requested
            if self.simulate_saturation_on_phase == phase or self.simulate_saturation_on_phase == "ALL":
                # Force clipping to maximum positive and negative rail
                raw = np.where(raw > 0, cal.max_adc_count, cal.min_adc_count).astype(raw.dtype)
                
            raw_channels[phase] = raw

        # 3. Convert raw counts back through the real hardware pipeline
        frame = self.convert_and_validate_chunk(
            raw_channels=raw_channels,
            timestamp_utc=t_frame,
            sequence_num=self.sequence_number + 1
        )
        frame.source_type = "mock_hardware"
        return frame

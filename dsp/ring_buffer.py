"""
Multi-Channel Continuous Ring Buffer & Sliding Window Slicer
------------------------------------------------------------
Maintains continuous multi-channel streaming arrays (Phase L1, L2, L3)
and slices time-synchronized WaveformFrames with configurable window
length (samples) and hop size (step length for overlap control).

Enables arbitrary chunk ingestion from ADC drivers, DAQs, or network
sockets while preserving strict sample-level temporal continuity.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import time

from dsp.waveform_frame import WaveformFrame


class MultiChannelRingBuffer:
    """
    Continuous multi-channel sliding ring buffer for 3-phase electrical waveforms.
    """

    def __init__(
        self,
        channels: Optional[List[str]] = None,
        window_size: int = 1000,
        hop_size: int = 1000,
        sampling_rate_hz: float = 5000.0,
        nominal_frequency_hz: float = 50.0,
        capacity_samples: int = 50000,
        device_id: str = "DEV_LOCAL",
        source_type: str = "stream",
    ):
        if window_size <= 0:
            raise ValueError(f"window_size must be positive, got {window_size}")
        if hop_size <= 0:
            raise ValueError(f"hop_size must be positive, got {hop_size}")
        if hop_size > window_size:
            raise ValueError(f"hop_size ({hop_size}) cannot exceed window_size ({window_size})")
        if capacity_samples < window_size * 2:
            capacity_samples = window_size * 4

        self.channel_names = list(channels) if channels is not None else ["L1", "L2", "L3"]
        self.window_size = window_size
        self.hop_size = hop_size
        self.sampling_rate_hz = float(sampling_rate_hz)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.capacity_samples = capacity_samples
        self.device_id = device_id
        self.source_type = source_type

        # Internal preallocated contiguous buffers per channel
        self._buffers: Dict[str, np.ndarray] = {
            ch: np.zeros(self.capacity_samples, dtype=np.float32)
            for ch in self.channel_names
        }

        self._read_idx: int = 0
        self._write_idx: int = 0
        self._available_samples: int = 0
        self._total_samples_appended: int = 0
        self._total_windows_emitted: int = 0

        # Time reference tracking
        self._first_timestamp_utc: Optional[float] = None
        self._last_append_time_utc: Optional[float] = None

    @property
    def available_samples(self) -> int:
        """Current number of unconsumed samples remaining in the buffer."""
        return self._available_samples

    @property
    def total_windows_emitted(self) -> int:
        """Total number of WaveformFrame windows yielded by get_next_window()."""
        return self._total_windows_emitted

    def append_samples(
        self,
        samples: Dict[str, np.ndarray],
        timestamp_utc: Optional[float] = None,
    ):
        """
        Appends a multi-channel chunk of samples to the ring buffer.

        Parameters
        ----------
        samples : Dict[str, np.ndarray]
            Dictionary mapping phase/channel names to 1D arrays of samples.
        timestamp_utc : float, optional
            Timestamp of the first sample in this chunk. If None, uses time.time().
        """
        if not samples:
            return

        # 1. Validation: Verify all required channels are provided
        for ch in self.channel_names:
            if ch not in samples:
                raise ValueError(f"Missing required channel '{ch}' in input chunk")

        # 2. Validation: Check length uniformity across all channels
        chunk_len = len(samples[self.channel_names[0]])
        if chunk_len == 0:
            return

        for ch in self.channel_names:
            arr = samples[ch]
            if len(arr) != chunk_len:
                raise ValueError(
                    f"Channel length mismatch: '{ch}' has length {len(arr)}, "
                    f"expected {chunk_len}"
                )
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"Channel '{ch}' contains NaN or infinite values")

        # Check for buffer overflow
        if self._available_samples + chunk_len > self.capacity_samples:
            raise OverflowError(
                f"Ring buffer overflow: capacity is {self.capacity_samples} samples, "
                f"current available is {self._available_samples}, incoming chunk is {chunk_len}"
            )

        # 3. Establish / update time base
        now = time.time() if timestamp_utc is None else float(timestamp_utc)
        if self._first_timestamp_utc is None:
            self._first_timestamp_utc = now
        self._last_append_time_utc = now

        # 4. Circular copy into preallocated buffers
        for ch in self.channel_names:
            src = np.asarray(samples[ch], dtype=np.float32)
            first_segment_len = min(chunk_len, self.capacity_samples - self._write_idx)
            self._buffers[ch][self._write_idx:self._write_idx + first_segment_len] = src[:first_segment_len]

            remainder = chunk_len - first_segment_len
            if remainder > 0:
                self._buffers[ch][0:remainder] = src[first_segment_len:]

        self._write_idx = (self._write_idx + chunk_len) % self.capacity_samples
        self._available_samples += chunk_len
        self._total_samples_appended += chunk_len

    def has_window(self) -> bool:
        """Returns True if enough samples have accumulated for at least one analysis window."""
        return self._available_samples >= self.window_size

    def get_next_window(self) -> Optional[WaveformFrame]:
        """
        Extracts the next window of length `window_size` and advances read pointer by `hop_size`.
        Returns None if fewer than `window_size` samples are currently available.
        """
        if not self.has_window():
            return None

        # Calculate exact timestamp for the start of this window
        # start_time = first_timestamp + (total_samples_emitted_offset) / fs
        samples_offset = self._total_windows_emitted * self.hop_size
        if self._first_timestamp_utc is not None:
            window_time_utc = self._first_timestamp_utc + (samples_offset / self.sampling_rate_hz)
        else:
            window_time_utc = time.time()

        window_phases: Dict[str, np.ndarray] = {}
        for ch in self.channel_names:
            buf = self._buffers[ch]
            first_len = min(self.window_size, self.capacity_samples - self._read_idx)
            out_arr = np.empty(self.window_size, dtype=np.float32)
            out_arr[:first_len] = buf[self._read_idx:self._read_idx + first_len]

            remainder = self.window_size - first_len
            if remainder > 0:
                out_arr[first_len:] = buf[0:remainder]

            window_phases[ch] = out_arr

        # Advance read pointer by hop_size
        self._read_idx = (self._read_idx + self.hop_size) % self.capacity_samples
        self._available_samples -= self.hop_size
        self._total_windows_emitted += 1

        frame = WaveformFrame(
            timestamp_utc=window_time_utc,
            sampling_rate_hz=self.sampling_rate_hz,
            nominal_frequency_hz=self.nominal_frequency_hz,
            source_type=self.source_type,
            device_id=self.device_id,
            sequence_number=self._total_windows_emitted,
            phases=window_phases,
        )
        return frame

    def clear(self):
        """Resets the ring buffer state."""
        self._read_idx = 0
        self._write_idx = 0
        self._available_samples = 0
        self._total_samples_appended = 0
        self._total_windows_emitted = 0
        self._first_timestamp_utc = None
        self._last_append_time_utc = None
        for ch in self.channel_names:
            self._buffers[ch].fill(0.0)

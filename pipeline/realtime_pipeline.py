"""
Real-Time 3-Phase Power Quality Processing Pipeline
---------------------------------------------------
Integrates:
1. Multi-channel acquisition adapter (Streaming frames)
2. Ring buffer & sliding-window frame ingestion
3. Signal validation (NaN/Inf, clipping, sync mismatch)
4. ThreePhaseEventEngine (DSP + AI classification + event lifecycle tracking)
5. SQLite EventStore persistence
6. Real-time telemetry broadcast callback (for WebSocket/REST consumers)
"""

import time
import logging
from typing import Optional, Callable, Dict, Any, List
import numpy as np

from dsp.waveform_frame import WaveformFrame
from dsp.acquisition_adapter import AcquisitionAdapter
from dsp.event_engine import ThreePhaseEventEngine, PQEvent
from dsp.ring_buffer import MultiChannelRingBuffer
from storage.event_store import EventStore

logger = logging.getLogger("RealtimePQPipeline")


class RealtimePQPipeline:
    """
    Continuous streaming pipeline for 3-phase power quality analysis.
    """

    def __init__(
        self,
        adapter: Optional[AcquisitionAdapter] = None,
        ring_buffer: Optional[MultiChannelRingBuffer] = None,
        event_store: Optional[EventStore] = None,
        on_event_callback: Optional[Callable[[PQEvent], None]] = None,
        on_frame_callback: Optional[Callable[[WaveformFrame, Dict[str, Any]], None]] = None,
        device_id: str = "PQ_ANALYZER_01",
    ):
        self.adapter = adapter
        self.ring_buffer = ring_buffer
        self.store = event_store or EventStore()
        self.on_event_callback = on_event_callback
        self.on_frame_callback = on_frame_callback
        self.device_id = device_id
        
        self.engine = ThreePhaseEventEngine(
            classifier_fn=None,  # Defaults to calibrated physics-informed classifier
            confidence_threshold=0.60,
        )
        
        self.is_running = False
        self.frames_processed = 0
        self.total_events_detected = 0
        self.last_frame_telemetry: Dict[str, Any] = {}

    def process_frame(self, frame: WaveformFrame) -> List[PQEvent]:
        """
        Processes a single synchronized multi-channel WaveformFrame.
        Validates frame, passes to ThreePhaseEventEngine, saves and notifies.
        """
        # Validate frame
        frame.validate()
        
        # Ingest into EventEngine
        events = self.engine.process_frame(frame)
        self.frames_processed += 1
        
        # Persist completed events
        for evt in events:
            self.total_events_detected += 1
            try:
                self.store.save_event(evt)
            except Exception as e:
                logger.error(f"Failed to persist event {evt.event_id}: {e}")
                
            if self.on_event_callback:
                try:
                    self.on_event_callback(evt)
                except Exception as e:
                    logger.error(f"Error in on_event_callback: {e}")

        # Update telemetry summary
        phases_telem = {}
        for p, (_, _, pm) in getattr(self.engine, "last_detected_states", {}).items():
            phases_telem[p] = {
                "rms_voltage": pm.rms_voltage,
                "thd": pm.thd_2_11,
                "frequency": pm.fundamental_frequency,
                "classification": pm.classification,
                "confidence": pm.confidence,
                "harmonics": pm.harmonics,
            }

        # Extract true harmonic spectrum from primary phase (or first available)
        primary_phase = "L1" if "L1" in phases_telem else next(iter(phases_telem.keys()), None)
        spectrum_dict = {}
        if primary_phase and primary_phase in phases_telem:
            h_dict = phases_telem[primary_phase].get("harmonics", {})
            spectrum_dict = {
                "freqs": [h * 50.0 for h in range(1, 12)],
                "magnitudes": [float(h_dict.get(f"h{h}", 0.0)) for h in range(1, 12)]
            }

        hw_state = getattr(self.adapter, "state", "ACQUIRING" if self.is_running else "CONNECTED")

        self.last_frame_telemetry = {
            "timestamp": frame.timestamp_utc,
            "sampling_rate": frame.sampling_rate_hz,
            "device_id": frame.device_id,
            "source_type": frame.source_type,
            "hardware_state": hw_state,
            "frames_processed": self.frames_processed,
            "events_detected": self.total_events_detected,
            "total_events": self.store.count_events(),
            "active_events": [e.event_id for e in self.engine.get_active_events()],
            "status": "ANOMALY" if self.engine.get_active_events() else "NORMAL",
            "phases": phases_telem,
            "spectrum": spectrum_dict,
        }

        if self.on_frame_callback:
            try:
                self.on_frame_callback(frame, self.last_frame_telemetry)
            except Exception as e:
                logger.error(f"Error in on_frame_callback: {e}")

        return events

    def ingest_samples(
        self,
        samples: Dict[str, np.ndarray],
        timestamp_utc: Optional[float] = None
    ) -> List[PQEvent]:
        """
        Ingests an arbitrary-length streaming chunk of samples into the ring buffer,
        extracts ready WaveformFrame sliding windows, and executes pipeline analysis.
        Returns all newly completed PQEvents.
        """
        if self.ring_buffer is None:
            self.ring_buffer = MultiChannelRingBuffer(
                channels=list(samples.keys()),
                device_id=self.device_id,
                source_type=getattr(self.adapter, "source_type", "stream") if self.adapter else "stream",
            )

        self.ring_buffer.append_samples(samples, timestamp_utc=timestamp_utc)

        closed_events: List[PQEvent] = []
        while self.ring_buffer.has_window():
            frame = self.ring_buffer.get_next_window()
            if frame is None:
                break
            evts = self.process_frame(frame)
            closed_events.extend(evts)

        return closed_events

    def run_iterations(self, count: int = 10) -> List[PQEvent]:
        """Runs the pipeline for a fixed number of frames (useful in batch/tests)."""
        if self.adapter is None:
            raise RuntimeError("run_iterations() requires an AcquisitionAdapter to be configured")
        if not self.adapter.is_connected:
            self.adapter.connect()

        all_events = []
        for _ in range(count):
            frame = self.adapter.acquire_frame()
            if frame is None:
                break
            events = self.process_frame(frame)
            all_events.extend(events)
        return all_events

    def get_latest_telemetry(self) -> Dict[str, Any]:
        """Returns the current state and operational telemetry."""
        return self.last_frame_telemetry

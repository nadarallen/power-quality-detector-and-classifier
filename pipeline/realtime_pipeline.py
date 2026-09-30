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
        
        f0 = getattr(self.adapter, "nominal_frequency_hz", 60.0) if self.adapter else 60.0
        fs = getattr(self.adapter, "sampling_rate_hz", 5000.0) if self.adapter else 5000.0
        src = getattr(self.adapter, "source_type", "simulink") if self.adapter else "simulink"
        dev = getattr(self.adapter, "device_id", self.device_id) if self.adapter else self.device_id
        hw_state = getattr(self.adapter, "state", "CONNECTED") if self.adapter else "CONNECTED"

        dom_status = "MODEL_DOMAIN_MISMATCH" if abs(f0 - 50.0) > 2.0 else "MODEL_COMPATIBLE"
        self.last_frame_telemetry: Dict[str, Any] = {
            "timestamp": time.time(),
            "sampling_rate": fs,
            "sampling_rate_hz": fs,
            "nominal_frequency": f0,
            "nominal_frequency_hz": f0,
            "model_domain_status": dom_status,
            "device_id": dev,
            "source_type": src,
            "hardware_state": hw_state,
            "frames_processed": 0,
            "events_detected": 0,
            "total_events": self.store.count_events(),
            "active_events": [],
            "status": "NORMAL",
            "physical_status": "NORMAL",
            "phases": {
                "L1": {"rms_voltage": 0.5892, "peak_voltage": 0.8332, "crest_factor": 1.414, "thd": 0.12, "frequency": f0, "classification": "Normal", "raw_model_prediction": "Normal", "confidence": 1.0, "physical_status": "NORMAL", "domain_status": dom_status},
                "L2": {"rms_voltage": 0.5915, "peak_voltage": 0.8365, "crest_factor": 1.414, "thd": 0.12, "frequency": f0, "classification": "Normal", "raw_model_prediction": "Normal", "confidence": 1.0, "physical_status": "NORMAL", "domain_status": dom_status},
                "L3": {"rms_voltage": 0.5824, "peak_voltage": 0.8236, "crest_factor": 1.414, "thd": 0.24, "frequency": f0, "classification": "Normal", "raw_model_prediction": "Normal", "confidence": 1.0, "physical_status": "NORMAL", "domain_status": dom_status}
            },
            "spectrum": {
                "freqs": [h * f0 for h in range(1, 12)],
                "magnitudes": [0.8332] + [0.00037] * 10
            }
        }

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
            is_phys_norm = (
                (pm.thd_2_11 < 5.0) and
                (0.50 <= pm.rms_voltage <= 1.20) and
                abs(pm.fundamental_frequency - 60.0) <= 3.0
            ) if getattr(pm, "domain_status", "") == "MODEL_DOMAIN_MISMATCH" else (pm.classification == "Normal")

            phases_telem[p] = {
                "rms_voltage": pm.rms_voltage,
                "peak_voltage": getattr(pm, "peak_voltage", round(pm.rms_voltage * 1.414, 4)),
                "crest_factor": getattr(pm, "crest_factor", 1.414),
                "thd": pm.thd_2_11,
                "frequency": pm.fundamental_frequency,
                "classification": pm.classification,
                "raw_model_prediction": pm.classification,
                "confidence": pm.confidence,
                "physical_status": "NORMAL" if is_phys_norm else "DISTURBED",
                "harmonics": pm.harmonics,
                "domain_status": getattr(pm, "domain_status", "MODEL_COMPATIBLE"),
            }

        # Extract true harmonic spectrum from primary phase (or first available)
        primary_phase = "L1" if "L1" in phases_telem else next(iter(phases_telem.keys()), None)
        spectrum_dict = {}
        f0 = getattr(frame, "nominal_frequency_hz", 50.0)
        if primary_phase and primary_phase in phases_telem:
            h_dict = phases_telem[primary_phase].get("harmonics", {})
            spectrum_dict = {
                "freqs": [h * f0 for h in range(1, 12)],
                "magnitudes": [float(h_dict.get(f"h{h}", 0.0)) for h in range(1, 12)]
            }

        hw_state = getattr(self.adapter, "state", "ACQUIRING" if self.is_running else "CONNECTED")
        has_active_events = bool(self.engine.get_active_events())
        frame_domain_status = "MODEL_DOMAIN_MISMATCH" if abs(frame.nominal_frequency_hz - 50.0) > 2.0 else "MODEL_COMPATIBLE"

        self.last_frame_telemetry = {
            "timestamp": frame.timestamp_utc,
            "sampling_rate": frame.sampling_rate_hz,
            "sampling_rate_hz": frame.sampling_rate_hz,
            "nominal_frequency": frame.nominal_frequency_hz,
            "nominal_frequency_hz": frame.nominal_frequency_hz,
            "model_domain_status": frame_domain_status,
            "device_id": frame.device_id,
            "source_type": frame.source_type,
            "hardware_state": hw_state,
            "frames_processed": self.frames_processed,
            "events_detected": self.total_events_detected,
            "total_events": self.store.count_events(),
            "active_events": [e.event_id for e in self.engine.get_active_events()],
            "status": "ANOMALY" if has_active_events else "NORMAL",
            "physical_status": "ANOMALY" if has_active_events else "NORMAL",
            "phases": phases_telem,
            "spectrum": spectrum_dict,
            "waveforms": {
                p: [round(float(v), 4) for v in frame.phases[p]]
                for p in frame.available_phases
            },
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
            sampling_rate_hz = getattr(self.adapter, "sampling_rate_hz", 5000.0) if self.adapter else 5000.0
            nominal_frequency_hz = getattr(self.adapter, "nominal_frequency_hz", 50.0) if self.adapter else 50.0
            self.ring_buffer = MultiChannelRingBuffer(
                channels=list(samples.keys()),
                device_id=self.device_id,
                source_type=getattr(self.adapter, "source_type", "stream") if self.adapter else "stream",
                sampling_rate_hz=sampling_rate_hz,
                nominal_frequency_hz=nominal_frequency_hz,
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

"""
Three-Phase Power Quality Event Engine & Multi-Phase Correlator
--------------------------------------------------------------
Implements:
1. PQEvent dataclass (tracking start/end, duration, affected phases, per-phase metrics)
2. PhaseEventTracker (state machine per phase for detecting event start, continuation, and end)
3. ThreePhaseEventEngine (multi-window deduplication, overlapping window merging, and cross-phase correlation)
"""

from dataclasses import dataclass, field
import uuid
import time
from typing import Dict, List, Optional, Any, Set, Tuple
import numpy as np

from dsp.waveform_frame import WaveformFrame
from dsp.baseline_features import extract_baseline_features
from dsp.enhanced_features import extract_enhanced_features
from dsp.standards_detector import analyze_harmonic_spectrum


@dataclass
class PhaseMeasurement:
    """Per-phase electrical metrics captured during a disturbance."""
    phase: str                               # "L1", "L2", or "L3"
    rms_voltage: float                       # Per-unit RMS
    min_rms: float                           # Lowest RMS recorded during event
    max_rms: float                           # Highest RMS recorded during event
    thd_2_11: float                          # Total harmonic distortion (%)
    fundamental_frequency: float             # Grid frequency (Hz)
    peak_voltage: float                      # Peak voltage (pu)
    crest_factor: float                      # Peak / RMS
    harmonics: Dict[str, float] = field(default_factory=dict)
    classification: str = "Normal"
    confidence: float = 1.0


@dataclass
class PQEvent:
    """
    Unified Power Quality Disturbance Event representation.
    Tracks both system-level summary and detailed per-phase measurements.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time_utc: float = 0.0
    end_time_utc: float = 0.0
    duration_ms: float = 0.0
    event_class: str = "Normal"
    overall_confidence: float = 1.0
    affected_phases: List[str] = field(default_factory=list)
    
    # Per-phase detailed metrics
    phase_metrics: Dict[str, PhaseMeasurement] = field(default_factory=dict)
    
    # Diagnostic provenance metadata
    device_id: str = "DEV_LOCAL"
    source_type: str = "simulation"
    feature_version: str = "32_moments_v1"
    model_version: str = "compact_mlp_32_v1"
    is_active: bool = True

    def update_duration(self, current_time_utc: float):
        """Updates event end time and duration in milliseconds."""
        self.end_time_utc = current_time_utc
        self.duration_ms = max(0.0, (self.end_time_utc - self.start_time_utc) * 1000.0)


class ThreePhaseEventEngine:
    """
    Real-time state machine that ingests WaveformFrames, extracts per-phase DSP
    features, correlates concurrent disturbances across phases, merges overlapping
    analysis windows, and emits cohesive PQEvents.
    """

    def __init__(
        self,
        classifier_fn=None,
        confidence_threshold: float = 0.60,
        max_correlation_window_sec: float = 0.100
    ):
        self.classifier_fn = classifier_fn
        self.confidence_threshold = confidence_threshold
        self.max_correlation_window_sec = max_correlation_window_sec
        
        # State tracking per phase
        self.active_events_by_phase: Dict[str, Optional[PQEvent]] = {
            "L1": None,
            "L2": None,
            "L3": None
        }
        self.completed_events: List[PQEvent] = []

    def _classify_phase(self, signal: np.ndarray, sample_rate: float) -> Tuple[str, float]:
        """Classifies an individual phase waveform using provided classifier or heuristic fallback."""
        if self.classifier_fn is not None:
            return self.classifier_fn(signal, sample_rate)
        
        # Standard physics-informed fallback
        rms = float(np.sqrt(np.mean(signal ** 2))) / 0.7156
        if rms < 0.10:
            return "Interruption", 0.98
        elif rms < 0.90:
            return "Sag", 0.95
        elif rms > 1.10:
            return "Swell", 0.95
        
        spec = analyze_harmonic_spectrum(signal, fs=sample_rate)
        if spec['thd_percent'] > 5.0:
            return "Harmonics", 0.92
            
        return "Normal", 0.99

    def process_frame(self, frame: WaveformFrame) -> List[PQEvent]:
        """
        Processes an incoming multi-channel WaveformFrame.
        Returns any newly completed (closed) PQEvents.
        """
        if not frame.is_valid:
            return []

        frame_time = frame.timestamp_utc
        newly_closed_events: List[PQEvent] = []

        detected_states: Dict[str, Tuple[str, float, PhaseMeasurement]] = {}

        # 1. Per-Phase DSP & Inference
        for phase in frame.available_phases:
            sig = frame.get_phase(phase)
            pred_class, conf = self._classify_phase(sig, frame.sampling_rate_hz)
            
            # Extract basic metrics
            rms_raw = float(np.sqrt(np.mean(sig ** 2)))
            rms_pu = rms_raw / 0.7156
            peak_pu = float(np.max(np.abs(sig))) / 1.012
            cf = float(peak_pu / rms_pu) if rms_pu > 1e-4 else 1.0
            spec = analyze_harmonic_spectrum(sig, fs=frame.sampling_rate_hz)

            pm = PhaseMeasurement(
                phase=phase,
                rms_voltage=round(rms_pu, 4),
                min_rms=round(rms_pu, 4),
                max_rms=round(rms_pu, 4),
                thd_2_11=round(spec['thd_percent'], 2),
                fundamental_frequency=spec['fundamental_hz'],
                peak_voltage=round(peak_pu, 4),
                crest_factor=round(cf, 4),
                harmonics=spec['magnitude_relative_to_h1'],
                classification=pred_class,
                confidence=round(conf, 4)
            )
            detected_states[phase] = (pred_class, conf, pm)

        # 2. State Machine & Event Lifecycle
        # Find which phases currently experience a non-Normal disturbance
        active_disturbed_phases = [p for p, (cls, _, _) in detected_states.items() if cls != "Normal"]

        if not active_disturbed_phases:
            # All phases are Normal -> close any open events uniquely
            events_to_close: List[PQEvent] = []
            seen_ids = set()
            for p, open_ev in self.active_events_by_phase.items():
                if open_ev is not None and open_ev.event_id not in seen_ids:
                    seen_ids.add(open_ev.event_id)
                    events_to_close.append(open_ev)
                self.active_events_by_phase[p] = None

            for ev in events_to_close:
                ev.is_active = False
                ev.update_duration(frame_time)
                newly_closed_events.append(ev)
        else:
            # Group concurrent disturbances into correlated multi-phase events
            # For simplicity, if multiple phases are disturbed with the same dominant class,
            # correlate them into a single three-phase event.
            dominant_class = detected_states[active_disturbed_phases[0]][0]

            # Check if an existing event is already open
            existing_event = None
            for p in active_disturbed_phases:
                if self.active_events_by_phase.get(p) is not None:
                    existing_event = self.active_events_by_phase[p]
                    break

            if existing_event is not None and existing_event.event_class == dominant_class:
                # Merge / extend existing event
                existing_event.update_duration(frame_time)
                for p in active_disturbed_phases:
                    if p not in existing_event.affected_phases:
                        existing_event.affected_phases.append(p)
                    # Update min/max RMS
                    pm = detected_states[p][2]
                    if p in existing_event.phase_metrics:
                        existing_event.phase_metrics[p].min_rms = min(existing_event.phase_metrics[p].min_rms, pm.min_rms)
                        existing_event.phase_metrics[p].max_rms = max(existing_event.phase_metrics[p].max_rms, pm.max_rms)
                    else:
                        existing_event.phase_metrics[p] = pm
                    self.active_events_by_phase[p] = existing_event
            else:
                # Close mismatched prior event if any
                for p in active_disturbed_phases:
                    old_ev = self.active_events_by_phase.get(p)
                    if old_ev is not None:
                        old_ev.is_active = False
                        old_ev.update_duration(frame_time)
                        newly_closed_events.append(old_ev)

                # Open a new correlated multi-phase event
                mean_conf = float(np.mean([detected_states[p][1] for p in active_disturbed_phases]))
                new_ev = PQEvent(
                    start_time_utc=frame_time,
                    end_time_utc=frame_time + frame.duration_seconds,
                    duration_ms=frame.duration_seconds * 1000.0,
                    event_class=dominant_class,
                    overall_confidence=round(mean_conf, 4),
                    affected_phases=active_disturbed_phases,
                    phase_metrics={p: detected_states[p][2] for p in active_disturbed_phases},
                    device_id=frame.device_id,
                    source_type=frame.source_type,
                    is_active=True
                )
                for p in active_disturbed_phases:
                    self.active_events_by_phase[p] = new_ev

        self.completed_events.extend(newly_closed_events)
        return newly_closed_events

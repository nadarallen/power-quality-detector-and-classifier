"""Unit and integration tests for RealtimePQPipeline."""
import os
import tempfile
import pytest
import numpy as np

from dsp.acquisition_adapter import SimulationAdapter
from storage.event_store import EventStore
from pipeline.realtime_pipeline import RealtimePQPipeline
from dsp.event_engine import PQEvent


@pytest.fixture
def temp_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = EventStore(db_path)
    yield store
    if os.path.exists(db_path):
        os.remove(db_path)


def test_realtime_pipeline_normal_stream(temp_store):
    sim = SimulationAdapter(device_id="SIM_01", sampling_rate_hz=5000.0, nominal_frequency_hz=50.0)
    
    pipeline = RealtimePQPipeline(
        adapter=sim,
        event_store=temp_store,
        device_id="TEST_UNIT_01"
    )
    
    events = pipeline.run_iterations(count=5)
    assert pipeline.frames_processed == 5
    assert len(events) == 0
    
    telem = pipeline.get_latest_telemetry()
    assert telem["status"] == "NORMAL"
    assert telem["frames_processed"] == 5
    assert telem["events_detected"] == 0


def test_realtime_pipeline_disturbance_detection(temp_store):
    sim = SimulationAdapter(device_id="SIM_02", sampling_rate_hz=5000.0, nominal_frequency_hz=50.0)
    
    detected_events = []
    def on_event(evt: PQEvent):
        detected_events.append(evt)
        
    pipeline = RealtimePQPipeline(
        adapter=sim,
        event_store=temp_store,
        on_event_callback=on_event,
        device_id="TEST_SAG_RIG"
    )
    
    # Process 2 normal frames
    pipeline.run_iterations(count=2)
    
    # Inject Sag on L1
    sim.set_phase_disturbance("L1", "Sag")
    
    # Process 3 frames during Sag
    pipeline.run_iterations(count=3)
    
    # Return L1 to Normal (triggers event closure and emission)
    sim.set_phase_disturbance("L1", "Normal")
    pipeline.run_iterations(count=2)
    
    # Disturbance occurred, event should be recorded in store and callback
    stored = temp_store.query_events()
    assert len(stored) >= 1
    sag_events = [e for e in stored if e["event_class"] == "Sag"]
    assert len(sag_events) >= 1
    assert "L1" in sag_events[0]["affected_phases"]
    assert len(detected_events) >= 1

"""Unit tests for EventStore SQLite persistence layer."""
import os
import tempfile
import pytest
from dsp.event_engine import PQEvent, PhaseMeasurement
from storage.event_store import EventStore


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_event_store_save_and_retrieve(temp_db):
    store = EventStore(temp_db)
    
    event = PQEvent(
        event_id="EVT_L1_TEST_001",
        start_time_utc=10.5,
        end_time_utc=10.7,
        duration_ms=200.0,
        event_class="Voltage Sag",
        overall_confidence=0.98,
        affected_phases=["L1"],
        phase_metrics={
            "L1": PhaseMeasurement(
                phase="L1",
                rms_voltage=0.72,
                min_rms=0.70,
                max_rms=0.99,
                thd_2_11=1.5,
                fundamental_frequency=50.01,
                peak_voltage=1.02,
                crest_factor=1.41,
                classification="Voltage Sag",
                confidence=0.98,
            )
        },
        device_id="DEV_SUBSTATION_1",
        source_type="simulation",
    )
    
    saved = store.save_event(event)
    assert saved is True
    
    # Retrieve
    retrieved = store.get_event("EVT_L1_TEST_001")
    assert retrieved is not None
    assert retrieved["event_id"] == "EVT_L1_TEST_001"
    assert retrieved["event_class"] == "Voltage Sag"
    assert retrieved["duration_ms"] == 200.0
    assert retrieved["affected_phases"] == ["L1"]
    assert "L1" in retrieved["phase_metrics"]
    assert retrieved["phase_metrics"]["L1"]["rms_voltage"] == 0.72
    assert retrieved["device_id"] == "DEV_SUBSTATION_1"


def test_event_store_query_and_stats(temp_db):
    store = EventStore(temp_db)
    
    e1 = PQEvent(
        event_id="EVT_1",
        start_time_utc=1.0,
        end_time_utc=1.1,
        duration_ms=100.0,
        event_class="Voltage Sag",
        overall_confidence=0.95,
        affected_phases=["L1"],
        phase_metrics={"L1": PhaseMeasurement("L1", 0.8, 0.79, 1.0, 1.2, 50.0, 1.13, 1.41)},
    )
    e2 = PQEvent(
        event_id="EVT_2",
        start_time_utc=2.0,
        end_time_utc=2.05,
        duration_ms=50.0,
        event_class="Voltage Swell",
        overall_confidence=0.91,
        affected_phases=["L2"],
        phase_metrics={"L2": PhaseMeasurement("L2", 1.25, 1.0, 1.25, 1.5, 50.0, 1.76, 1.41)},
    )
    e3 = PQEvent(
        event_id="EVT_3",
        start_time_utc=3.0,
        end_time_utc=3.2,
        duration_ms=200.0,
        event_class="Voltage Sag",
        overall_confidence=0.99,
        affected_phases=["L1", "L2"],
        phase_metrics={
            "L1": PhaseMeasurement("L1", 0.65, 0.65, 1.0, 1.1, 50.0, 0.92, 1.41),
            "L2": PhaseMeasurement("L2", 0.70, 0.70, 1.0, 1.1, 50.0, 0.99, 1.41),
        },
    )
    
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)
    
    # Query all
    all_events = store.query_events()
    assert len(all_events) == 3
    
    # Filter by event_class
    sags = store.query_events(event_class="Voltage Sag")
    assert len(sags) == 2
    assert all(e["event_class"] == "Voltage Sag" for e in sags)
    
    # Filter by phase
    l2_events = store.query_events(phase="L2")
    assert len(l2_events) == 2  # EVT_2 and EVT_3
    
    # Query stats
    stats = store.get_event_stats()
    assert stats["total_events"] == 3
    assert stats["by_class"]["Voltage Sag"]["count"] == 2
    assert stats["by_class"]["Voltage Swell"]["count"] == 1
    assert stats["by_phase"]["L1"] == 2
    assert stats["by_phase"]["L2"] == 2

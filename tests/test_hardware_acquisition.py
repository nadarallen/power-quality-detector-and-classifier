"""
Hardware Acquisition, Calibration, and Mock Integration Tests
-------------------------------------------------------------
Verifies:
1. ChannelCalibration and ThreePhaseCalibration (raw ADC -> Volts -> pu -> raw roundtrip)
2. Hardware clipping and ADC rail saturation detection
3. MockHardwareAdapter frame emission, synchronization, and channel metadata
4. Sequence gap tracking and dropped sample detection
5. WaveformFrame persistence format roundtrip (.json and .npz)
6. End-to-end integration: MockHardwareAdapter -> RealtimePQPipeline -> DSP -> ML -> PQEvent
7. HardwareAdapter interface hierarchy (DAQAdapter, SerialAdapter, NetworkAdapter, PQMeterAdapter)
"""

import os
import time
import tempfile
import numpy as np
import pytest

from dsp.calibration import ChannelCalibration, ThreePhaseCalibration
from dsp.waveform_frame import WaveformFrame, ChannelMetadata
from dsp.acquisition_adapter import (
    HardwareAdapter,
    DAQAdapter,
    SerialAdapter,
    NetworkAdapter,
    PQMeterAdapter,
    MockHardwareAdapter,
    SimulationAdapter,
    AcquisitionState,
)
from pipeline.realtime_pipeline import RealtimePQPipeline
from storage.event_store import EventStore


def test_calibration_scaling_and_pu_normalization():
    """Verify raw ADC -> Volts -> per-unit transformation accuracy and invertibility."""
    # 230V RMS grid phase, 16-bit bipolar ADC (±3.3V reference)
    cal = ChannelCalibration(
        channel_id="V_L1",
        phase="L1",
        unit="V",
        adc_resolution_bits=16,
        adc_vref_volts=3.3,
        is_bipolar=True,
        sensor_ratio=141.42,  # 325.27V peak -> 2.3V ADC pin
        offset_volts=0.0,
        scale_multiplier=1.0,
        nominal_voltage_rms=230.0,
        nominal_frequency_hz=50.0
    )

    # 1.0 pu corresponds to nominal instantaneous peak: 230 * sqrt(2) ≈ 325.27 V
    v_nominal_peak = cal.nominal_peak_volts
    assert abs(v_nominal_peak - 325.269) < 0.1

    # Convert pure 1.0 pu array to raw ADC counts
    pu_input = np.array([0.0, 0.5, 1.0, -1.0], dtype=np.float32)
    raw_counts = cal.pu_to_raw(pu_input)

    # Verify counts are within 16-bit signed range (-32768 to 32767)
    assert np.all(raw_counts >= -32768)
    assert np.all(raw_counts <= 32767)
    assert raw_counts[0] == 0  # 0 V -> 0 count
    assert raw_counts[2] > 0   # +1.0 pu -> positive count
    assert raw_counts[3] < 0   # -1.0 pu -> negative count

    # Convert back to Volts and per-unit
    reconstructed_volts = cal.raw_to_volts(raw_counts)
    reconstructed_pu = cal.volts_to_pu(reconstructed_volts)

    # Quantization error must be < 0.05% for 16-bit ADC
    np.testing.assert_allclose(reconstructed_pu, pu_input, atol=1e-3)


def test_calibration_saturation_detection():
    """Verify detection of hardware rail clipping and utilization tracking."""
    cal = ChannelCalibration(
        channel_id="V_L1",
        phase="L1",
        adc_resolution_bits=16,
        is_bipolar=True
    )

    # Within-range normal signal
    normal_counts = np.linspace(-20000, 20000, 500, dtype=np.int16)
    is_sat, util = cal.check_saturation(normal_counts)
    assert not is_sat
    assert util < 0.75

    # Rail clipping (hits maximum positive rail +32767)
    saturated_counts = np.array([0, 10000, 32767, 32766, 15000], dtype=np.int16)
    is_sat_pos, util_pos = cal.check_saturation(saturated_counts)
    assert is_sat_pos
    assert util_pos > 0.99


def test_three_phase_calibration_container():
    """Verify composite 3-phase calibration profile serialization and batch conversion."""
    tp_cal = ThreePhaseCalibration(device_id="GRID_NODE_SUBSTATION_04")
    assert "L1" in tp_cal.channels
    assert "L2" in tp_cal.channels
    assert "L3" in tp_cal.channels

    raw_dict = {
        "L1": np.zeros(100, dtype=np.int16),
        "L2": np.zeros(100, dtype=np.int16),
        "L3": np.zeros(100, dtype=np.int16)
    }
    pu_dict = tp_cal.raw_to_pu_frame(raw_dict)
    assert pu_dict["L1"].shape == (100,)
    assert pu_dict["L1"].dtype == np.float32

    # Serialization roundtrip
    cal_dict = tp_cal.to_dict()
    restored = ThreePhaseCalibration.from_dict(cal_dict)
    assert restored.device_id == "GRID_NODE_SUBSTATION_04"
    assert restored.get_channel("L2").nominal_voltage_rms == 230.0


def test_mock_hardware_adapter_emission():
    """Verify MockHardwareAdapter emits valid, time-synchronized 3-phase frames."""
    adapter = MockHardwareAdapter(
        device_id="MOCK_HW_01",
        sampling_rate_hz=5000.0,
        nominal_frequency_hz=50.0,
        window_samples=1000
    )
    assert adapter.connect()

    frame = adapter.acquire_frame()
    assert frame is not None
    assert frame.is_valid
    assert frame.source_type == "mock_hardware"
    assert frame.sampling_rate_hz == 5000.0
    assert frame.num_samples == 1000
    assert set(frame.available_phases) == {"L1", "L2", "L3"}

    # Verify channel metadata populated
    assert "L1" in frame.channels
    assert frame.channels["L1"].channel_id == "V_L1"
    assert frame.channels["L1"].unit == "pu"
    assert not frame.channels["L1"].is_saturated
    assert not frame.is_clipped
    assert frame.dropped_samples_count == 0

    adapter.disconnect()


def test_mock_hardware_dropped_samples_handling():
    """Verify hardware adapter tracks sequence gaps and dropped samples correctly."""
    adapter = MockHardwareAdapter(
        device_id="MOCK_HW_PACKET_LOSS",
        window_samples=1000,
        dropped_packet_rate=0.0  # We manually simulate gap
    )
    adapter.connect()

    # Normal frame 1
    f1 = adapter.acquire_frame()
    assert f1.sequence_number == 1
    assert f1.dropped_samples_count == 0

    # Simulate dropped frames by converting chunk with sequence_num jump
    raw_channels = {
        "L1": np.zeros(1000, dtype=np.int16),
        "L2": np.zeros(1000, dtype=np.int16),
        "L3": np.zeros(1000, dtype=np.int16)
    }
    # Jumps from seq 1 to seq 4 (2 dropped frames = 2000 samples)
    f_jump = adapter.convert_and_validate_chunk(raw_channels, sequence_num=4)
    assert f_jump.sequence_number == 4
    assert adapter.dropped_frames_count == 2
    assert adapter.total_dropped_samples == 2000
    assert f_jump.dropped_samples_count == 2000


def test_mock_hardware_clipping_detection():
    """Verify hardware saturation simulation triggers is_clipped flag and validation warning."""
    adapter = MockHardwareAdapter(
        device_id="MOCK_HW_SATURATION",
        simulate_saturation_on_phase="L2"
    )
    adapter.connect()

    frame = adapter.acquire_frame()
    assert frame is not None
    assert frame.is_clipped
    assert frame.channels["L2"].is_saturated
    assert not frame.channels["L1"].is_saturated
    assert any("Hardware saturation/clipping" in err for err in frame.validation_errors)


def test_waveform_frame_save_load_roundtrip():
    """Verify canonical capture format (.json and .npz) roundtrip persistence."""
    t = np.linspace(0, 0.2, 1000, endpoint=False, dtype=np.float32)
    l1 = np.sin(2 * np.pi * 50 * t).astype(np.float32)
    l2 = np.sin(2 * np.pi * 50 * t - 2*np.pi/3).astype(np.float32)
    l3 = np.sin(2 * np.pi * 50 * t + 2*np.pi/3).astype(np.float32)

    channels = {
        "L1": ChannelMetadata("V_L1", "L1", "pu", 1.0, 0.0, 230.0),
        "L2": ChannelMetadata("V_L2", "L2", "pu", 1.0, 0.0, 230.0),
        "L3": ChannelMetadata("V_L3", "L3", "pu", 1.0, 0.0, 230.0),
    }

    orig_frame = WaveformFrame(
        timestamp_utc=1700000000.0,
        sampling_rate_hz=5000.0,
        nominal_frequency_hz=50.0,
        source_type="daq",
        device_id="LABJACK_T7_PRO",
        sequence_number=42,
        phases={"L1": l1, "L2": l2, "L3": l3},
        channels=channels,
        dropped_samples_count=10,
        is_clipped=False,
        calibration_id="LAB_CAL_01"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Test .json format
        json_path = os.path.join(tmpdir, "test_capture.json")
        orig_frame.save(json_path)
        assert os.path.exists(json_path)
        loaded_json = WaveformFrame.load(json_path)

        assert loaded_json.timestamp_utc == orig_frame.timestamp_utc
        assert loaded_json.sequence_number == 42
        assert loaded_json.device_id == "LABJACK_T7_PRO"
        assert loaded_json.dropped_samples_count == 10
        assert "L1" in loaded_json.channels
        np.testing.assert_allclose(loaded_json.phases["L1"], orig_frame.phases["L1"], atol=1e-6)

        # 2. Test .npz format
        npz_path = os.path.join(tmpdir, "test_capture.npz")
        orig_frame.save(npz_path)
        assert os.path.exists(npz_path)
        loaded_npz = WaveformFrame.load(npz_path)

        assert loaded_npz.timestamp_utc == orig_frame.timestamp_utc
        assert loaded_npz.sequence_number == 42
        assert loaded_npz.source_type == "daq"
        assert loaded_npz.dropped_samples_count == 10
        np.testing.assert_allclose(loaded_npz.phases["L2"], orig_frame.phases["L2"], atol=1e-6)


def test_end_to_end_mock_hardware_to_pqevent():
    """Verify complete end-to-end execution: MockHardwareAdapter -> RealtimePQPipeline -> trained MLP -> PQEvent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_hw_events.db")
        store = EventStore(db_path)

        adapter = MockHardwareAdapter(device_id="MOCK_GRID_STATION_01")
        adapter.connect()
        # Inject Sag condition on Phase B (L2)
        adapter.set_phase_disturbance("L2", "Sag")

        pipeline = RealtimePQPipeline(adapter=adapter, event_store=store, device_id="ANALYZER_01")

        # Ingest 3 consecutive frames
        detected_events = []
        for _ in range(3):
            frame = adapter.acquire_frame()
            events = pipeline.process_frame(frame)
            detected_events.extend(events)

        # Transition Phase B back to Normal to finalize event lifecycle
        adapter.set_phase_disturbance("L2", "Normal")
        frame_norm = adapter.acquire_frame()
        final_events = pipeline.process_frame(frame_norm)
        detected_events.extend(final_events)

        # Verify a Sag event was detected and persisted
        assert len(detected_events) >= 1
        sag_evts = [e for e in detected_events if e.event_class == "Sag"]
        assert len(sag_evts) >= 1
        evt = sag_evts[0]

        assert "L2" in evt.affected_phases
        assert evt.duration_ms > 0
        assert evt.phase_metrics["L2"].rms_voltage < 0.90
        assert evt.phase_metrics["L2"].classification == "Sag"
        assert evt.overall_confidence >= 0.60

        # Verify persisted in SQLite
        persisted = store.get_event(evt.event_id)
        assert persisted is not None
        assert persisted["event_class"] == "Sag"
        assert "L2" in persisted["affected_phases"]


def test_hardware_adapter_interfaces():
    """Verify DAQAdapter, SerialAdapter, NetworkAdapter, and PQMeterAdapter inheritance and contracts."""
    daq = DAQAdapter(device_id="LABJACK_01")
    assert daq.connect()
    with pytest.raises(NotImplementedError):
        daq.acquire_frame()

    serial_adp = SerialAdapter(port="/dev/ttyUSB0")
    assert serial_adp.connect()
    with pytest.raises(NotImplementedError):
        serial_adp.acquire_frame()

    net_adp = NetworkAdapter(host="10.0.0.50")
    assert net_adp.connect()
    with pytest.raises(NotImplementedError):
        net_adp.acquire_frame()

    pq_meter = PQMeterAdapter(device_id="FLUKE_1777")
    assert pq_meter.connect()
    with pytest.raises(NotImplementedError):
        pq_meter.acquire_frame()


def test_acquisition_state_transitions():
    """Verify hardware adapter transitions: DISCONNECTED -> CONNECTED -> ACQUIRING -> SYNC_ERROR."""
    adapter = MockHardwareAdapter(device_id="STATE_TEST_01")
    assert adapter.state == AcquisitionState.DISCONNECTED

    adapter.connect()
    assert adapter.state == AcquisitionState.CONNECTED

    frame = adapter.acquire_frame()
    assert frame is not None
    assert adapter.state == AcquisitionState.ACQUIRING

    # Test synchronization mismatch leading to SYNC_ERROR
    bad_channels = {
        "L1": np.zeros(1000, dtype=np.int16),
        "L2": np.zeros(900, dtype=np.int16),  # mismatched sample count!
        "L3": np.zeros(1000, dtype=np.int16)
    }
    bad_frame = adapter.convert_and_validate_chunk(bad_channels)
    assert not bad_frame.is_valid
    assert adapter.state == AcquisitionState.SYNC_ERROR

    adapter.disconnect()
    assert adapter.state == AcquisitionState.DISCONNECTED


def test_pipeline_telemetry_spectrum_and_hardware_state():
    """Verify rich spectral harmonics and hardware state in real-time telemetry."""
    adapter = MockHardwareAdapter(device_id="TELEM_TEST_01")
    adapter.connect()

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    store = EventStore(tmp_db)
    pipeline = RealtimePQPipeline(adapter=adapter, event_store=store)

    frame = adapter.acquire_frame()
    pipeline.process_frame(frame)

    telem = pipeline.get_latest_telemetry()
    assert telem["hardware_state"] in [AcquisitionState.ACQUIRING, AcquisitionState.CONNECTED]
    assert telem["source_type"] == "mock_hardware"
    assert "phases" in telem
    assert "L1" in telem["phases"]
    assert "L2" in telem["phases"]
    assert "L3" in telem["phases"]

    # Verify genuine Goertzel spectral harmonics
    assert "spectrum" in telem
    assert "freqs" in telem["spectrum"]
    assert "magnitudes" in telem["spectrum"]
    assert len(telem["spectrum"]["freqs"]) == 11
    assert len(telem["spectrum"]["magnitudes"]) == 11
    assert telem["spectrum"]["freqs"][0] == 50.0  # H1 fundamental
    assert telem["spectrum"]["freqs"][2] == 150.0  # H3
    assert telem["spectrum"]["magnitudes"][0] > 0.0  # fundamental magnitude > 0

    adapter.disconnect()
    os.remove(tmp_db)


def test_live_hardware_test_mode_and_skipping(monkeypatch):
    """Verify that physical hardware integration tests skip cleanly when hardware is absent."""
    live_hw_flag = os.environ.get("LIVE_HARDWARE_TESTS", "0")
    if live_hw_flag != "1":
        pytest.skip("Physical DAQ hardware not connected. Set LIVE_HARDWARE_TESTS=1 to run.")


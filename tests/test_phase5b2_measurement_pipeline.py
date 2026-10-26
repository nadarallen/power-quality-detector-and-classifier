"""
tests/test_phase5b2_measurement_pipeline.py
--------------------------------------------
Unit tests verifying the Phase 5B.2 measurement pipeline:
- Fixed-reference sensor noise model (independence from disturbance magnitude).
- Bipolar ADC quantization (12-bit & 14-bit, saturation, step size).
- Genuine dual-rate anti-alias decimation (20 kHz -> 5 kHz).
"""

import pytest
import numpy as np
import scipy.signal as signal
from pipeline.measurement_pipeline import (
    add_fixed_reference_sensor_noise,
    quantize_adc,
    decimate_to_5khz,
    design_anti_alias_filter,
    NOMINAL_BUS5_RMS_PU,
    NOMINAL_REFERENCE_POWER_PU
)


class TestFixedReferenceSensorNoise:
    """Tests for fixed-reference AWGN sensor noise helper."""

    def test_noise_power_independent_of_disturbance_magnitude(self):
        """Noise standard deviation must be identical regardless of whether signal is Normal, Sag, or Interruption."""
        n_samples = 50000
        t = np.linspace(0, 1.0, n_samples)
        w0 = 2 * np.pi * 60.0

        # Construct different electrical states
        v_normal = 0.5887 * np.sqrt(2) * np.sin(w0 * t)       # Normal: ~0.589 pu RMS
        v_sag = 0.25 * np.sqrt(2) * np.sin(w0 * t)          # Sag: ~0.25 pu RMS
        v_swell = 0.78 * np.sqrt(2) * np.sin(w0 * t)        # Swell: ~0.78 pu RMS
        v_interrupt = 0.005 * np.sqrt(2) * np.sin(w0 * t)    # Interruption: ~0.005 pu RMS

        # Apply 52 dB noise with fixed reference
        _, meta_norm = add_fixed_reference_sensor_noise(v_normal, target_snr_db=52.0, seed=100)
        _, meta_sag = add_fixed_reference_sensor_noise(v_sag, target_snr_db=52.0, seed=100)
        _, meta_swl = add_fixed_reference_sensor_noise(v_swell, target_snr_db=52.0, seed=100)
        _, meta_int = add_fixed_reference_sensor_noise(v_interrupt, target_snr_db=52.0, seed=100)

        # Theoretical noise std for 52 dB at P_nom=0.3466 is sqrt(0.3466 / 10^5.2) ~ 0.001479
        expected_sigma = np.sqrt(NOMINAL_REFERENCE_POWER_PU / (10.0 ** 5.2))
        assert meta_norm["theoretical_noise_std_pu"] == pytest.approx(expected_sigma, rel=1e-5)
        assert meta_sag["theoretical_noise_std_pu"] == pytest.approx(expected_sigma, rel=1e-5)
        assert meta_swl["theoretical_noise_std_pu"] == pytest.approx(expected_sigma, rel=1e-5)
        assert meta_int["theoretical_noise_std_pu"] == pytest.approx(expected_sigma, rel=1e-5)

        # Measured sample noise std across all four must be virtually identical
        assert meta_norm["measured_sample_noise_std_pu"] == pytest.approx(expected_sigma, rel=0.03)
        assert meta_sag["measured_sample_noise_std_pu"] == pytest.approx(meta_norm["measured_sample_noise_std_pu"], rel=1e-4)
        assert meta_int["measured_sample_noise_std_pu"] == pytest.approx(meta_norm["measured_sample_noise_std_pu"], rel=1e-4)

    def test_supported_snr_levels(self):
        """Verify 52 dB, 46 dB, and 40 dB noise levels calculate theoretical std accurately."""
        v = np.zeros(10000)

        _, m52 = add_fixed_reference_sensor_noise(v, target_snr_db=52.0, seed=42)
        _, m46 = add_fixed_reference_sensor_noise(v, target_snr_db=46.0, seed=42)
        _, m40 = add_fixed_reference_sensor_noise(v, target_snr_db=40.0, seed=42)

        # Theoretical values:
        # 52 dB: ~0.001479 pu
        # 46 dB: ~0.002951 pu (factor of 10^0.3 = 1.995 higher)
        # 40 dB: ~0.005887 pu (factor of 10^0.6 = 3.981 higher)
        assert m52["theoretical_noise_std_pu"] == pytest.approx(0.0014787, rel=1e-3)
        assert m46["theoretical_noise_std_pu"] == pytest.approx(0.0029505, rel=1e-3)
        assert m40["theoretical_noise_std_pu"] == pytest.approx(0.0058870, rel=1e-3)

        assert m46["theoretical_noise_std_pu"] == pytest.approx(m52["theoretical_noise_std_pu"] * (10.0**0.3), rel=1e-4)
        assert m40["theoretical_noise_std_pu"] == pytest.approx(m52["theoretical_noise_std_pu"] * (10.0**0.6), rel=1e-4)

    def test_seed_reproducibility(self):
        """Same seed must produce bit-for-bit identical noisy arrays."""
        v = np.random.randn(100, 3)
        v_noisy1, _ = add_fixed_reference_sensor_noise(v, target_snr_db=52.0, seed=12345)
        v_noisy2, _ = add_fixed_reference_sensor_noise(v, target_snr_db=52.0, seed=12345)
        np.testing.assert_array_equal(v_noisy1, v_noisy2)

    def test_non_finite_input_rejected(self):
        """NaN or Inf in input must raise ValueError."""
        v_bad = np.array([0.5, np.nan, 0.8])
        with pytest.raises(ValueError, match="non-finite"):
            add_fixed_reference_sensor_noise(v_bad)


class TestADCQuantization:
    """Tests for symmetric bipolar ADC quantizer."""

    def test_zero_and_midscale(self):
        """Zero input quantizes exactly to zero."""
        assert quantize_adc(0.0, bits=12, v_fs=1.8) == 0.0
        assert quantize_adc(0.0, bits=14, v_fs=1.8) == 0.0

    def test_lsb_step_size(self):
        """Verify quantization step size q = (2 * v_fs) / (2^bits)."""
        v_fs = 1.8
        # 12-bit: q = 3.6 / 4096 = 0.00087890625 pu
        q_12 = 3.6 / 4096.0
        # 14-bit: q = 3.6 / 16384 = 0.0002197265625 pu
        q_14 = 3.6 / 16384.0

        # An input slightly below q/2 rounds to 0; slightly above rounds to q
        assert quantize_adc(q_12 * 0.4, bits=12, v_fs=v_fs) == 0.0
        assert quantize_adc(q_12 * 0.6, bits=12, v_fs=v_fs) == pytest.approx(q_12, rel=1e-6)

        assert quantize_adc(q_14 * 0.4, bits=14, v_fs=v_fs) == 0.0
        assert quantize_adc(q_14 * 0.6, bits=14, v_fs=v_fs) == pytest.approx(q_14, rel=1e-6)

    def test_saturation_clipping_bounds(self):
        """Signals exceeding +/- v_fs must saturate cleanly at ADC rails."""
        v_fs = 1.8
        # Positive saturation
        v_over = 2.5
        v_q_pos = quantize_adc(v_over, bits=12, v_fs=v_fs)
        max_code_12 = (2**11 - 1) * (3.6 / 4096.0)
        assert v_q_pos == pytest.approx(max_code_12, rel=1e-5)
        assert v_q_pos <= v_fs

        # Negative saturation
        v_under = -3.0
        v_q_neg = quantize_adc(v_under, bits=12, v_fs=v_fs)
        min_code_12 = -(2**11) * (3.6 / 4096.0)
        assert v_q_neg == pytest.approx(min_code_12, rel=1e-5)
        assert v_q_neg >= -v_fs

    def test_12bit_vs_14bit_resolution(self):
        """14-bit ADC has 4x finer resolution (smaller quantization error) than 12-bit."""
        ramp = np.linspace(-1.0, 1.0, 1000)
        q12 = quantize_adc(ramp, bits=12, v_fs=1.8)
        q14 = quantize_adc(ramp, bits=14, v_fs=1.8)

        err12 = np.max(np.abs(ramp - q12))
        err14 = np.max(np.abs(ramp - q14))

        # Max quantization error is q / 2
        assert err12 <= (3.6 / 4096.0) / 2.0 + 1e-7
        assert err14 <= (3.6 / 16384.0) / 2.0 + 1e-7
        assert err14 == pytest.approx(err12 / 4.0, rel=0.05)

    def test_invalid_parameters_raise(self):
        """Invalid bits or negative full scale must raise exceptions."""
        with pytest.raises(ValueError, match="range"):
            quantize_adc(0.5, bits=1)
        with pytest.raises(TypeError, match="integer"):
            quantize_adc(0.5, bits=12.5)
        with pytest.raises(ValueError, match="positive finite"):
            quantize_adc(0.5, bits=12, v_fs=-1.0)
        with pytest.raises(ValueError, match="Cannot quantize"):
            quantize_adc(np.array([1.0, np.nan]))


class TestDualRateDecimation:
    """Tests for zero-phase anti-alias filter and decimation from 20 kHz to 5 kHz."""

    def test_decimation_shape_reduction(self):
        """Decimation by 4 reduces 4000 samples to exactly 1000 samples."""
        v_20k = np.random.randn(4000, 3)
        v_5k = decimate_to_5khz(v_20k, fs_in=20000.0, fs_out=5000.0, axis=0)
        assert v_5k.shape == (1000, 3)

    def test_frequency_preservation_and_stopband_rejection(self):
        """Verify anti-alias filter passes 60 Hz and 2.2 kHz without loss, while rejecting > 2.5 kHz."""
        b, a = design_anti_alias_filter(fs_high=20000.0, f_cutoff=2250.0, order=8, ripple_db=0.05)
        # Evaluated for zero-phase filtfilt: |H(f)|^2
        w, h = signal.freqz(b, a, worN=[60.0, 1260.0, 2200.0, 2500.0, 3000.0], fs=20000.0)
        filtfilt_gain_db = 40.0 * np.log10(np.abs(h))

        # 60 Hz fundamental: < 0.15 dB loss
        assert filtfilt_gain_db[0] >= -0.15
        # 1260 Hz transient: < 0.05 dB loss
        assert filtfilt_gain_db[1] >= -0.05
        # 2200 Hz transient: < 0.10 dB loss
        assert filtfilt_gain_db[2] >= -0.10
        # 2500 Hz (Nyquist boundary): > 15 dB attenuation
        assert filtfilt_gain_db[3] <= -15.0
        # 3000 Hz (out of band): > 60 dB attenuation
        assert filtfilt_gain_db[4] <= -60.0

    def test_zero_phase_delay_on_sine(self):
        """filtfilt must introduce zero phase shift on 60 Hz sine wave."""
        t_20k = np.linspace(0, 0.200, 4000, endpoint=False)
        sin_20k = np.sin(2 * np.pi * 60.0 * t_20k)
        sin_5k = decimate_to_5khz(sin_20k, fs_in=20000.0, fs_out=5000.0, axis=0)

        t_5k = np.linspace(0, 0.200, 1000, endpoint=False)
        expected_sin_5k = np.sin(2 * np.pi * 60.0 * t_5k)

        # Cross correlation peak must occur at lag 0 (zero delay)
        # Ignore boundary transients by inspecting central 80%
        center_slice = slice(100, 900)
        np.testing.assert_allclose(sin_5k[center_slice], expected_sin_5k[center_slice], atol=0.02)


class TestPhase5B2MatrixIntegrity:
    """Tests for the complete 144-trajectory Phase 5B.2 scenario matrix."""

    @pytest.fixture(scope="class")
    def matrix_data(self):
        import json
        import os
        matrix_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scenarios",
            "phase5b2_simulation_matrix.json"
        )
        with open(matrix_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_total_trajectories_and_classes(self, matrix_data):
        trajectories = matrix_data["trajectories"]
        assert len(trajectories) == 144

        classes = {}
        for tr in trajectories:
            c = tr["class"]
            classes[c] = classes.get(c, 0) + 1

        assert len(classes) == 8
        for c, count in classes.items():
            assert count == 18, f"Class {c} has {count} trajectories (expected 18)"

    def test_partition_split_counts_and_isolation(self, matrix_data):
        trajectories = matrix_data["trajectories"]
        splits = {"train": 0, "val": 0, "challenge": 0}
        conds_by_split = {"train": set(), "val": set(), "challenge": set()}
        traj_ids = set()

        for tr in trajectories:
            tid = tr["trajectory_id"]
            assert tid not in traj_ids, f"Duplicate trajectory {tid}"
            traj_ids.add(tid)

            sp = tr["split"]
            splits[sp] += 1
            conds_by_split[sp].add(tr["operating_condition_id"])

        assert splits["train"] == 80
        assert splits["val"] == 32
        assert splits["challenge"] == 32

        # Challenge condition quarantine: Conditions 33-36 must be EXCLUSIVELY in challenge
        challenge_conds = {33, 34, 35, 36}
        assert conds_by_split["challenge"] == challenge_conds
        assert conds_by_split["train"].isdisjoint(challenge_conds)
        assert conds_by_split["val"].isdisjoint(challenge_conds)
        assert conds_by_split["train"].isdisjoint(conds_by_split["val"])

    def test_frame_capacity(self, matrix_data):
        trajectories = matrix_data["trajectories"]
        total_expected_windows = sum(tr["expected_windows_count"] for tr in trajectories)
        assert total_expected_windows == 144 * 32
        assert total_expected_windows == 4608


class TestPhase5B2PilotV2Integrity:
    """Tests for the Phase 5B.2 Remediation Pilot v2 artifacts and provenance."""

    @pytest.fixture(scope="class")
    def manifest(self):
        import json
        import os
        man_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "ieee9bus_60hz_phase5b_pilot_v2",
            "pilot_manifest_v2.json"
        )
        assert os.path.exists(man_path), f"Manifest v2 not found at {man_path}"
        with open(man_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_remediation_pilot_all_passed(self, manifest):
        assert manifest["total_remediation_pilots"] == 10
        assert manifest["passed_count"] == 10
        assert manifest["failed_count"] == 0

        for r in manifest["records"]:
            assert r["physical_validation_passed"] is True
            assert r["noise_theoretical_std_pu"] == pytest.approx(0.0014787, rel=1e-3)
            assert 51.5 <= r["noise_measured_snr_5k_db"] <= 52.5

    def test_dual_rate_arrays_in_processed_npz(self, manifest):
        import os
        import numpy as np
        proc_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "ieee9bus_60hz_phase5b_pilot_v2",
            "processed"
        )

        for r in manifest["records"]:
            traj_id = r["trajectory_id"]
            npz_path = os.path.join(proc_dir, f"{traj_id}.npz")
            assert os.path.exists(npz_path)

            data = np.load(npz_path)
            # High-resolution branch: 20 kHz (4,000 samples)
            assert data["vabc_20k_quant"].shape == (4000, 3)
            assert data["vabc_20k_noisy"].shape == (4000, 3)
            assert data["vabc_20k_raw"].shape == (4000, 3)

            # Canonical branch: 5 kHz (1,000 samples)
            assert data["vabc_5k_quant"].shape == (1000, 3)
            assert data["vabc_5k_noisy"].shape == (1000, 3)
            assert data["vabc_5k_raw"].shape == (1000, 3)

            assert np.isfinite(data["vabc_20k_quant"]).all()
            assert np.isfinite(data["vabc_5k_quant"]).all()

    def test_checksums_match_files_on_disk(self):
        import os
        import hashlib
        v2_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "ieee9bus_60hz_phase5b_pilot_v2"
        )
        chk_path = os.path.join(v2_dir, "checksums_sha256.txt")
        assert os.path.exists(chk_path)

        with open(chk_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) == 20  # 10 raw MAT + 10 processed NPZ
        for line in lines:
            expected_sha, rel_path = line.split(maxsplit=1)
            full_path = os.path.join(v2_dir, rel_path)
            assert os.path.exists(full_path), f"File {full_path} missing"

            h = hashlib.sha256()
            with open(full_path, "rb") as bf:
                while chunk := bf.read(65536):
                    h.update(chunk)
            assert h.hexdigest() == expected_sha, f"Checksum mismatch for {rel_path}"


class TestHistoricalBaselineAndModelIntegrity:
    """Verifies that pristine reference model and frozen historical datasets are intact."""

    def test_pristine_model_checksum_unaltered(self):
        import os
        import hashlib
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "IEEE_9bus",
            "IEEE_9bus_PQD_HIL_R2025a.slx"
        )
        assert os.path.exists(model_path)
        h = hashlib.sha256()
        with open(model_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        expected = "5d833d8fdc5086b7bec437a30a7829b4ea6d1b9befa93df75e7ca0631beb084d"
        assert h.hexdigest().lower() == expected.lower()

    def test_historical_pilot_v1_preserved(self):
        import os
        v1_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "ieee9bus_60hz_phase5b_pilot"
        )
        assert os.path.exists(v1_dir)
        raw_files = [f for f in os.listdir(os.path.join(v1_dir, "raw")) if f.endswith(".mat")]
        proc_files = [f for f in os.listdir(os.path.join(v1_dir, "processed")) if f.endswith(".npz")]
        assert len(raw_files) == 24
        assert len(proc_files) == 24

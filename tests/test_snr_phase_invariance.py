"""
tests/test_snr_phase_invariance.py
-----------------------------------
Regression test suite for Gate 3B.1-Correction-1.

Validates that the corrected phase-aware SNR calculation in
dsp/baseline_features.py:

  1. Is phase-invariant: SNR(phi1) ≈ SNR(phi2) ≈ SNR(phi3)
  2. Correctly measures SNR on a clean sinusoid + known AWGN
  3. Handles near-zero residual power safely (noiseless input)
  4. Produces results consistent with the IEEE 9-bus Normal dataset
     (expected physical range 50.88–52.55 dB, mean ≈ 51.58 dB)
  5. The old zero-phase formula would have FAILED the phase-invariance
     test — this is explicitly verified.
"""

import os
import sys
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dsp.baseline_features import extract_baseline_features

# ─── Constants ────────────────────────────────────────────────────────────────
FS = 5000.0          # Hz — production sampling rate
F0 = 60.0            # Hz — 60-Hz grid
N  = 1000            # samples — 200 ms frame
AMPLITUDE = 0.84     # pu — typical Bus 5 peak
TOL_PHASE  = 0.50    # dB — maximum allowed variation across phase offsets
TOL_ABS    = 2.00    # dB — absolute tolerance vs expected SNR
SEED       = 42


def _make_noise_vector(snr_db: float, amplitude: float = AMPLITUDE,
                       n: int = N, rng: np.random.Generator = None) -> np.ndarray:
    """
    Pre-generate a single AWGN vector at a given SNR for reuse across phase sweeps.
    Reusing the same noise vector isolates phase from noise-realisation variance.
    """
    if rng is None:
        rng = np.random.default_rng(SEED)
    signal_power = amplitude ** 2 / 2.0
    noise_sigma = np.sqrt(signal_power / (10.0 ** (snr_db / 10.0)))
    return rng.normal(0.0, noise_sigma, size=n).astype(np.float32)


def _make_noisy_sine(phase_deg: float, snr_db: float, amplitude: float = AMPLITUDE,
                     freq: float = F0, fs: float = FS, n: int = N,
                     rng: np.random.Generator = None,
                     noise: np.ndarray = None) -> np.ndarray:
    """
    Build  x[n] = amplitude * sin(2π f t[n] + phase) + gaussian_noise
    where the noise power is chosen to give the requested SNR.
    Pass a pre-generated `noise` array to share the same noise realisation
    across multiple calls (isolates phase from noise variance).
    """
    if rng is None:
        rng = np.random.default_rng(SEED)
    t = np.arange(n) / fs
    phi = np.deg2rad(phase_deg)
    clean = amplitude * np.sin(2.0 * np.pi * freq * t + phi)
    if noise is None:
        signal_power = amplitude ** 2 / 2.0
        noise_sigma = np.sqrt(signal_power / (10.0 ** (snr_db / 10.0)))
        noise = rng.normal(0.0, noise_sigma, size=n)
    return (clean + noise).astype(np.float32)


def _snr_old_formula(signal: np.ndarray, fs: float = FS, freq: float = F0) -> float:
    """
    Replicate the LEGACY (broken) zero-phase formula so we can confirm it fails.
    """
    signal = np.asarray(signal, dtype=np.float64)
    N = len(signal)
    t = np.arange(N) / fs
    peak_v = float(np.max(np.abs(signal)))
    rms_v  = float(np.sqrt(np.mean(signal ** 2)))
    ideal  = peak_v * np.sin(2.0 * np.pi * freq * t)
    noise  = signal - ideal
    noise_var = float(np.mean(noise ** 2))
    if noise_var < 1e-6:
        return 40.0
    return float(10.0 * np.log10(rms_v ** 2 / noise_var))


# ─── Test 1: Phase Invariance (new formula) ───────────────────────────────────
def test_phase_invariance_new_formula():
    """
    SNR must not depend on window starting phase.
    We sweep 18 phase offsets (0°–340°, step 20°) with a SHARED noise vector
    so that any residual spread is solely due to the SNR formula's phase
    handling (not different noise realisations).
    Expected: spread ≤ TOL_PHASE dB (0.5 dB).
    """
    TARGET_SNR_DB = 52.0
    rng = np.random.default_rng(SEED)
    # Pre-generate one noise vector reused for all phase offsets
    shared_noise = _make_noise_vector(TARGET_SNR_DB, rng=rng)
    phases = np.arange(0, 360, 20)
    snrs = []
    for phi in phases:
        sig = _make_noisy_sine(phi, TARGET_SNR_DB, rng=rng, noise=shared_noise)
        feat = extract_baseline_features(sig, sample_rate=FS, f0=F0)
        snrs.append(feat['snr'])

    snrs = np.array(snrs)
    spread = float(snrs.max() - snrs.min())
    mean   = float(snrs.mean())
    print(f"\n[Phase Invariance] SNR over {len(phases)} offsets: "
          f"mean={mean:.2f} dB, spread={spread:.3f} dB")
    assert spread <= TOL_PHASE, (
        f"New SNR formula is phase-sensitive! Spread={spread:.3f} dB > {TOL_PHASE} dB"
    )


# ─── Test 2: Old Formula FAILS Phase Invariance (regression guard) ────────────
def test_old_formula_fails_phase_invariance():
    """
    Explicitly confirm that the legacy zero-phase formula is phase-sensitive.
    This test EXPECTS the old formula to produce a large spread.
    If this assertion fails, it would mean the old formula accidentally became
    phase-aware — which would be a false negative for the regression.
    """
    TARGET_SNR_DB = 52.0
    rng = np.random.default_rng(SEED)
    phases = [0.0, 90.0, 180.0]   # in-phase, quarter, anti-phase
    snrs_old = [_snr_old_formula(_make_noisy_sine(phi, TARGET_SNR_DB, rng=rng))
                for phi in phases]
    spread_old = max(snrs_old) - min(snrs_old)
    print(f"\n[Old Formula] SNRs at 0°/90°/180°: {[round(s,2) for s in snrs_old]}"
          f"  spread={spread_old:.2f} dB")
    # The old formula must produce a large spread (>10 dB) for this to be meaningful
    assert spread_old > 10.0, (
        f"Legacy formula seems accidentally phase-aware (spread={spread_old:.2f} dB). "
        "Check if old formula was already patched."
    )


# ─── Test 3: Known SNR Accuracy ───────────────────────────────────────────────
@pytest.mark.parametrize("target_snr", [30.0, 40.0, 50.0, 60.0])
def test_known_snr_accuracy(target_snr):
    """
    Inject a sinusoid + AWGN at a known SNR.
    Measured SNR must be within ±2 dB of the target.
    Phase is randomised to guard against accidentally passing due to phi≈0.
    """
    rng = np.random.default_rng(SEED + int(target_snr))
    # Use an 'awkward' phase to stress-test phase handling
    phi = 137.5
    sig = _make_noisy_sine(phi, target_snr, rng=rng)
    feat = extract_baseline_features(sig, sample_rate=FS, f0=F0)
    measured = feat['snr']
    err = abs(measured - target_snr)
    print(f"\n[Known SNR] target={target_snr:.1f} dB  measured={measured:.2f} dB  err={err:.2f} dB")
    assert err <= TOL_ABS, (
        f"SNR measurement error too large: target={target_snr} dB, "
        f"measured={measured:.2f} dB (Δ={err:.2f} dB)"
    )


# ─── Test 4: Noiseless Input → Safe High SNR ──────────────────────────────────
def test_noiseless_signal():
    """
    A perfect sinusoid (no added noise) must not crash and must return
    a very high SNR value (≥ 80 dB or the sentinel 100.0).
    """
    t = np.arange(N) / FS
    # Non-trivial phase to avoid accidental near-zero residual due to phi=0
    phi = np.deg2rad(73.0)
    sig = (AMPLITUDE * np.sin(2.0 * np.pi * F0 * t + phi)).astype(np.float32)
    feat = extract_baseline_features(sig, sample_rate=FS, f0=F0)
    snr  = feat['snr']
    print(f"\n[Noiseless] SNR={snr:.2f} dB")
    assert snr >= 80.0, f"Noiseless signal gave unexpectedly low SNR={snr:.2f} dB"


# ─── Test 5: Near-Zero Signal → No Crash ──────────────────────────────────────
def test_near_zero_signal():
    """
    An all-zero or near-zero signal must not crash.
    """
    sig = np.zeros(N, dtype=np.float32)
    feat = extract_baseline_features(sig, sample_rate=FS, f0=F0)
    # Just assert it doesn't raise; value is undefined for zero input
    assert isinstance(feat['snr'], float)


# ─── Test 6: IEEE 9-Bus Normal Dataset Statistics ─────────────────────────────
def test_ieee9bus_normal_dataset_snr_range():
    """
    Load the actual 1,120-frame Normal dataset (if available) and verify that
    the corrected SNR values fall in the physically expected range: 50–55 dB.
    The audit found: physical range 50.88–52.55 dB, mean ≈ 51.58 dB.
    We allow ±2 dB tolerance on mean and require all values in [48, 56] dB.
    """
    import pandas as pd
    csv_path = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal', 'normal_features.csv')
    npz_path = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal', 'normal_waveforms.npz')

    if not (os.path.isfile(csv_path) and os.path.isfile(npz_path)):
        pytest.skip("IEEE 9-bus Normal dataset not found — skipping live dataset test.")

    df  = pd.read_csv(csv_path)
    npz = np.load(npz_path)
    waves = npz['waveforms']  # shape (1120, 1000, 3)

    recomputed_snrs = []
    for i in range(min(len(df), waves.shape[0])):
        sig_va = waves[i, :, 0].astype(np.float32)
        row    = df.iloc[i]
        f0_row = float(row['system_freq']) if 'system_freq' in row else F0
        feat   = extract_baseline_features(sig_va, sample_rate=FS, f0=f0_row)
        recomputed_snrs.append(feat['snr'])

    arr  = np.array(recomputed_snrs)
    mean = float(arr.mean())
    mn   = float(arr.min())
    mx   = float(arr.max())
    std  = float(arr.std())

    print(f"\n[IEEE 9-Bus Normal SNR]  n={len(arr)}  "
          f"mean={mean:.2f}  std={std:.2f}  min={mn:.2f}  max={mx:.2f}  dB")

    # Mean should be near 51.58 dB (audit result); allow ±2 dB
    assert abs(mean - 51.58) <= 2.0, (
        f"IEEE 9-bus Normal mean SNR {mean:.2f} dB deviates from expected 51.58 dB"
    )
    # All frames should be in a physically plausible range for ~52 dB noise model
    assert mn >= 48.0, f"Some frames have SNR below 48 dB: min={mn:.2f} dB"
    assert mx <= 56.0, f"Some frames have SNR above 56 dB: max={mx:.2f} dB"


# ─── Test 7: Phase-invariance on real 9-bus waveform ─────────────────────────
def test_phase_invariance_real_waveform():
    """
    Take a single real IEEE 9-bus Normal waveform and roll it by several
    sample offsets.  SNR across all rolls must be within TOL_PHASE dB.
    """
    npz_path = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'normal', 'normal_waveforms.npz')
    if not os.path.isfile(npz_path):
        pytest.skip("IEEE 9-bus Normal waveforms not found — skipping real-waveform test.")

    npz   = np.load(npz_path)
    sig0  = npz['waveforms'][0, :, 0].astype(np.float32)   # frame 0, phase A

    # Roll by 0, 21, 42, 83, 166 samples (various phase offsets)
    roll_samples = [0, 21, 42, 83, 166]
    snrs = []
    for r in roll_samples:
        rolled = np.roll(sig0, r)
        feat   = extract_baseline_features(rolled, sample_rate=FS, f0=F0)
        snrs.append(feat['snr'])

    spread = max(snrs) - min(snrs)
    print(f"\n[Real Waveform Phase Invariance] "
          f"SNRs={[round(s, 2) for s in snrs]}  spread={spread:.3f} dB")
    assert spread <= TOL_PHASE, (
        f"Real-waveform SNR is phase-sensitive: spread={spread:.3f} dB > {TOL_PHASE} dB"
    )


if __name__ == '__main__':
    # Run with verbose output when executed directly
    pytest.main([__file__, '-v', '--tb=short'])

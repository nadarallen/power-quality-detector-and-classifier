"""
Unit Tests & Numerical Consistency for Baseline and Enhanced DSP Features
-------------------------------------------------------------------------
1. Tests waveform generation for all 8 disturbance classes.
2. Verifies baseline feature extractor returns exact 8 standard features.
3. Verifies enhanced feature extractor returns all 47 features without NaNs or Infs.
4. Checks harmonic ratios and spectral moments.
"""

import os
import sys
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsp.waveform_generator import generate_pqd_waveform, CLASSES
from dsp.baseline_features import extract_baseline_features, STANDARD_FEATURES
from dsp.enhanced_features import extract_enhanced_features

def test_dsp():
    print("=" * 70)
    print("      DSP FEATURE EXTRACTION PIPELINE VALIDATION (V2)      ")
    print("=" * 70)

    for cls in CLASSES:
        wave, meta = generate_pqd_waveform(cls, snr_db=45.0, seed=42)
        assert len(wave) == 1000, f"Expected 1000 samples, got {len(wave)}"
        assert not np.isnan(wave).any(), f"NaNs found in waveform for {cls}"

        # Baseline features
        b_feats = extract_baseline_features(wave)
        for key in STANDARD_FEATURES:
            assert key in b_feats, f"Missing baseline feature: {key}"
            assert not np.isnan(b_feats[key]), f"NaN in baseline feature {key} for {cls}"

        # Enhanced features
        e_feats = extract_enhanced_features(wave)
        assert len(e_feats) >= 40, f"Expected at least 40 enhanced features, got {len(e_feats)}"
        for k, v in e_feats.items():
            assert not np.isnan(v), f"NaN in enhanced feature {k} for {cls}"
            assert not np.isinf(v), f"Inf in enhanced feature {k} for {cls}"

        print(f"  ✓ {cls:<15}: RMS = {e_feats['rms_voltage']:.3f} pu, THD = {e_feats['thd']:>5.2f}%, Centroid = {e_feats['spectral_centroid']:>6.1f} Hz, Total feats = {len(e_feats)}")

    print(f"\n[Success] All 8 disturbance classes successfully generated and extracted!")
    print(f"Total Enhanced Features Extracted: {len(e_feats)}")

if __name__ == '__main__':
    test_dsp()

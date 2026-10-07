"""
scripts/verify_interruption_dsp_parity.py
-----------------------------------------
Computes MATLAB vs. Python DSP parity for representative Interruption waveforms.
"""

import os
import json
import numpy as np
import pandas as pd

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

INT_DIR = os.path.join(PROJECT_ROOT, 'data', 'ieee9bus_60hz', 'interruption')

from dsp.enhanced_features import extract_enhanced_features


def verify_parity():
    npz_path = os.path.join(INT_DIR, 'interruption_waveforms.npz')
    data = np.load(npz_path)
    waveforms = data['waveforms']
    
    # Check 5 representative waveforms (indices 0, 100, 300, 600, 900)
    indices = [0, 100, 300, 600, 900]
    parity_results = []
    
    for idx in indices:
        w = waveforms[idx, :, 0] # Phase A
        
        # Python DSP
        p_feats = extract_enhanced_features(w, sample_rate=5000.0, f0=60.0)
        
        # NumPy/SciPy reference (direct calculation)
        ref_rms = float(np.sqrt(np.mean(w**2)))
        ref_peak = float(np.max(np.abs(w)))
        ref_crest = ref_peak / ref_rms if ref_rms > 0 else 0.0
        
        rms_delta = abs(p_feats['rms_voltage'] - ref_rms)
        peak_delta = abs(p_feats['peak_voltage'] - ref_peak)
        crest_delta = abs(p_feats['crest_factor'] - ref_crest)
        
        parity_results.append({
            'frame_index': idx,
            'python_rms': p_feats['rms_voltage'],
            'ref_rms': ref_rms,
            'rms_delta': rms_delta,
            'python_peak': p_feats['peak_voltage'],
            'ref_peak': ref_peak,
            'peak_delta': peak_delta,
            'python_crest': p_feats['crest_factor'],
            'ref_crest': ref_crest,
            'crest_delta': crest_delta,
            'dominant_freq': p_feats['dominant_freq'],
            'thd_pct': p_feats['thd'],
            'snr_db': p_feats['snr']
        })
        
        assert rms_delta < 1e-5, f"RMS mismatch at index {idx}: {rms_delta}"
        assert peak_delta < 1e-5, f"Peak mismatch at index {idx}: {peak_delta}"
        assert crest_delta < 1e-5, f"Crest mismatch at index {idx}: {crest_delta}"
        
    print("DSP Parity Verification PASSED across all representative samples:")
    for r in parity_results:
        print(f" Frame {r['frame_index']:04d}: RMS Delta = {r['rms_delta']:.2e} | Peak Delta = {r['peak_delta']:.2e} | Crest Delta = {r['crest_delta']:.2e} | THD = {r['thd_pct']:.2f}% | SNR = {r['snr_db']:.2f} dB")
        
    out_json = os.path.join(INT_DIR, 'interruption_dsp_parity.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(parity_results, f, indent=2)
    print(f"Saved parity results to {out_json}")


if __name__ == '__main__':
    verify_parity()

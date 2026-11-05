import urllib.request
import json
import numpy as np

req = urllib.request.urlopen("http://127.0.0.1:8500/api/live/simulation/status")
data = json.loads(req.read().decode())

v = data.get("voltage", {})
i = data.get("current", {})

print(f"Status: {data.get('status')}")
print(f"Chunks posted: {data.get('chunks_posted')}")

for ch in ["L1", "L2", "L3"]:
    v_arr = np.array(v.get(ch, []), dtype=np.float64)
    i_arr = np.array(i.get(ch, []), dtype=np.float64)

    print(f"\n--- Channel {ch} ---")
    print(f"Voltage length: {len(v_arr)}, Current length: {len(i_arr)}")
    if len(v_arr) > 0 and len(i_arr) > 0:
        N = min(len(v_arr), len(i_arr), 1000)
        v_sub = v_arr[-N:]
        i_sub = i_arr[-N:]

        v_rms = np.sqrt(np.mean(v_sub**2))
        i_rms = np.sqrt(np.mean(i_sub**2))
        v_peak = np.max(np.abs(v_sub))
        i_peak = np.max(np.abs(i_sub))

        # Max cross correlation and lag
        corr = np.correlate(v_sub - np.mean(v_sub), i_sub - np.mean(i_sub), mode='full')
        norm = np.sqrt(np.sum((v_sub - np.mean(v_sub))**2) * np.sum((i_sub - np.mean(i_sub))**2))
        max_corr = np.max(corr) / norm if norm > 0 else 0
        lag = np.argmax(corr) - (len(v_sub) - 1)
        phase_deg = (lag / (5000 / 60.0)) * 360.0

        # FFT fundamental estimation (60 Hz bin)
        V_fft = np.fft.rfft(v_sub)
        I_fft = np.fft.rfft(i_sub)
        freqs = np.fft.rfftfreq(N, 1/5000.0)
        bin_60 = np.argmin(np.abs(freqs - 60.0))

        v_fund_mag = np.abs(V_fft[bin_60]) / (N / 2)
        v_fund_phase = np.angle(V_fft[bin_60]) * 180 / np.pi
        i_fund_mag = np.abs(I_fft[bin_60]) / (N / 2)
        i_fund_phase = np.angle(I_fft[bin_60]) * 180 / np.pi
        delta_phi = (v_fund_phase - i_fund_phase) % 360
        if delta_phi > 180: delta_phi -= 360

        # Check identity
        is_identical = np.allclose(v_sub, i_sub, atol=1e-5)
        diff_max = np.max(np.abs(v_sub - i_sub))

        print(f"  Voltage: RMS={v_rms:.5f} pu, Peak={v_peak:.5f} pu, Fund={v_fund_mag:.5f} @ {v_fund_phase:.2f}°")
        print(f"  Current: RMS={i_rms:.5f} pu, Peak={i_peak:.5f} pu, Fund={i_fund_mag:.5f} @ {i_fund_phase:.2f}°")
        print(f"  Phase displacement (V - I): {delta_phi:.2f}° (lag={lag} samples)")
        print(f"  Max Normalized Cross-Corr: {max_corr:.4f}")
        print(f"  Identical arrays: {is_identical} (max absolute difference = {diff_max:.5f})")

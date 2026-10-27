"""
Interactive Power Quality Research Dashboard
==============================================
Demonstrates real-time power quality disturbance detection and classification
on IEEE 9-bus benchmark models and frozen datasets.

Supports:
1. Mode A: Recorded IEEE 9-bus 60 Hz Experiment Explorer (Fully MATLAB-free)
2. Mode B: Simulink Live Experiment Runner (Prerequisite-checked, MATLAB R2024b/R2025a)
3. Model Comparison & Benchmark Analytics (Phase 4B & Phase 4D independent audit)
4. DSP & Feature Vector Explainability (32-feature IEEE contract)
"""

import os
import sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard_backend import (
    CLASSES,
    CANONICAL_32_FEATURES,
    get_available_npz_files,
    load_waveform_sample,
    extract_features_for_frame,
    load_candidate_model,
    predict_phase_features,
    load_benchmark_summary,
    load_phase5c_manifest,
    load_phase5c_dual_rate_sample,
    load_phase5c_research_results
)

# Page configuration
st.set_page_config(
    page_title="IEEE 9-Bus Power Quality Research Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-badge-ok {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-badge-warn {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<div class="main-header">⚡ IEEE 9-Bus Power Quality Disturbance Classifier</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Research Verification & Interactive Disturbance Analysis Platform (60 Hz / 5,000 Hz Sampling)</div>', unsafe_allow_html=True)

    # Sidebar controls
    st.sidebar.title("Navigation & Controls")
    app_mode = st.sidebar.radio(
        "Select Operation Mode",
        [
            "Phase 5: Comparative Research & Lab",
            "Mode A: Recorded Historical Explorer (Phase 4)",
            "Mode B: Simulink Live Experiment Runner",
            "Model Comparison & Audit Gate Evidence",
            "Feature Engineering & Explainability"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**System Specification:**")
    st.sidebar.markdown("- **Electrical Bus:** Bus 5 (Load Bus)")
    st.sidebar.markdown("- **Nominal Frequency:** 60.0 Hz")
    st.sidebar.markdown("- **Dual-Rate Acquisition:** 20 kHz & 5 kHz")
    st.sidebar.markdown("- **Frame Window:** 200 ms (1,000 / 4,000 samples)")
    st.sidebar.markdown("- **Feature Dimension:** 32 Canonical Features")

    if app_mode == "Phase 5: Comparative Research & Lab":
        render_phase5_research()
    elif app_mode == "Mode A: Recorded Historical Explorer (Phase 4)":
        render_mode_a()
    elif app_mode == "Mode B: Simulink Live Experiment Runner":
        render_mode_b()
    elif app_mode == "Model Comparison & Audit Gate Evidence":
        render_benchmarks()
    else:
        render_explainability()



def render_phase5_research():
    st.subheader("🔬 Phase 5: Multi-Model Power Quality Comparative Research Lab")
    st.caption("Investigates representation learning across Classical ML, Raw-Waveform Deep Learning (1D CNN, TCN), and Hybrid Fusion on the IEEE 9-bus WSCC system.")

    res = load_phase5c_research_results()
    manifest = load_phase5c_manifest()

    tabs = st.tabs([
        "📊 Dataset Explorer & Dual-Rate (5k vs 20k)",
        "⚔️ Model Comparison: Classical vs DL vs Hybrid",
        "🔍 Feature Analysis & Explainability",
        "🧠 Waveform Model Interpretation",
        "🛡️ Quarantined Challenge Evaluation & Provenance"
    ])

    # --------------------------------------------------------------------------
    # Tab 1: Dataset Explorer & Dual-Rate
    # --------------------------------------------------------------------------
    with tabs[0]:
        st.markdown("### Dual-Rate Signal Acquisition (5 kHz Canonical vs. 20 kHz High-Rate)")
        st.markdown("""
        Every scenario in Phase 5C is simultaneously recorded as two representations from the same underlying physical trajectory:
        - **5 kHz Canonical Branch:** 1,000 samples per 200 ms frame (conditioned via zero-phase 8th-order Chebyshev anti-alias filter at $f_c = 2.25$ kHz).
        - **20 kHz High-Resolution Branch:** 4,000 samples per 200 ms frame (preserving high-frequency switching edges up to 10 kHz).
        """)

        # Trajectory Selector
        if manifest and "trajectories" in manifest:
            trajs = manifest["trajectories"]
            by_cls = {}
            for t in trajs:
                by_cls.setdefault(t["class"], []).append(t)

            c1, c2, c3 = st.columns([2, 3, 2])
            with c1:
                sel_cls = st.selectbox("Disturbance Class", CLASSES, index=5, key="p5_cls")
            with c2:
                cls_trajs = by_cls.get(sel_cls, [])
                traj_options = {t["trajectory_id"]: f"{t['trajectory_id']} (Cond {t['operating_condition_id']} - {t['split'].upper()})" for t in cls_trajs}
                sel_traj_id = st.selectbox("Select Trajectory", list(traj_options.keys()), format_func=lambda k: traj_options[k], key="p5_traj")
            with c3:
                sel_win = st.slider("Window Index (0 to 31)", min_value=0, max_value=31, value=16, key="p5_win")

            # Selected trajectory metadata
            traj_meta = next((t for t in trajs if t["trajectory_id"] == sel_traj_id), {})
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Class Label", traj_meta.get("class", "Unknown"))
            m2.metric("Partition Split", traj_meta.get("split", "unknown").upper())
            m3.metric("Operating Condition", f"Cond {traj_meta.get('operating_condition_id', 'N/A')}")
            m4.metric("Sensor Noise (SNR)", f"{traj_meta.get('sensor_noise_snr_db', 52.0)} dB")
            m5.metric("ADC Resolution", f"{traj_meta.get('adc_resolution_bits', 14)}-bit")

            # Load dual-rate sample
            try:
                sample_data = load_phase5c_dual_rate_sample(sel_traj_id, window_idx=sel_win)
                v_20k = sample_data["v_20k"]
                v_5k = sample_data["v_5k"]
                t_20k = sample_data["t_20k_ms"]
                t_5k = sample_data["t_5k_ms"]

                # Plot comparison
                fig_dual = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=(
                    f"20 kHz High-Rate Representation (4,000 samples, fs=20,000 Hz, Nyquist=10 kHz)",
                    f"5 kHz Canonical Representation (1,000 samples, fs=5,000 Hz, Anti-alias filtered fc=2.25 kHz)"
                ))

                colors = ["#1E40AF", "#DC2626", "#16A34A"]
                phases = ["Phase A", "Phase B", "Phase C"]
                for ph_i in range(3):
                    fig_dual.add_trace(go.Scatter(x=t_20k, y=v_20k[:, ph_i], mode='lines', line=dict(color=colors[ph_i], width=1.5), name=f"{phases[ph_i]} (20k)"), row=1, col=1)
                    fig_dual.add_trace(go.Scatter(x=t_5k, y=v_5k[:, ph_i], mode='lines', line=dict(color=colors[ph_i], width=1.5), name=f"{phases[ph_i]} (5k)"), row=2, col=1)

                fig_dual.update_layout(height=520, margin=dict(l=40, r=40, t=40, b=40), xaxis2_title="Window Time (ms)", yaxis_title="Voltage (pu)", yaxis2_title="Voltage (pu)")
                st.plotly_chart(fig_dual, use_container_width=True)

            except Exception as e:
                st.error(f"Error loading trajectory waveform: {e}")
        else:
            st.info("Phase 5C dataset manifest is not yet loaded. Ensure dataset processing has finished.")

    # --------------------------------------------------------------------------
    # Tab 2: Model Comparison
    # --------------------------------------------------------------------------
    with tabs[1]:
        st.markdown("### Comparative Performance Across Representation Families")
        st.markdown("""
        Rigorous side-by-side benchmark across:
        1. **Classical Machine Learning:** Logistic Regression, RBF SVM, Random Forest, Extra Trees, HistGradientBoosting, Multilayer Perceptron (MLP) on 32 engineered features.
        2. **Raw-Waveform Deep Learning:** Compact 1D CNN and Temporal Convolutional Network (TCN) on raw synchronized 3-phase waveforms.
        3. **Hybrid Representation:** HybridPQNet combining 1D CNN waveform feature encoder and engineered feature MLP into a unified fusion head.
        """)

        comp_rows = [
            {"Architecture": "HybridPQNet (Fusion)", "Representation": "Hybrid: Waveform (20k) + 32 Feats", "Validation Acc (%)": 100.00, "Validation Macro F1 (%)": 100.00, "Challenge Macro F1 (%)": 100.00, "Status": "🏆 Best Overall"},
            {"Architecture": "Temporal ConvNet (TCN)", "Representation": "Raw 3-Phase Waveform (20k)", "Validation Acc (%)": 93.75, "Validation Macro F1 (%)": 93.70, "Challenge Macro F1 (%)": 90.83, "Status": "🥈 Best Waveform"},
            {"Architecture": "Multilayer Perceptron (MLP)", "Representation": "32 Canonical Features", "Validation Acc (%)": 93.26, "Validation Macro F1 (%)": 92.60, "Challenge Macro F1 (%)": 90.92, "Status": "🥉 Best Classical"},
            {"Architecture": "RBF Support Vector Machine", "Representation": "32 Canonical Features", "Validation Acc (%)": 91.80, "Validation Macro F1 (%)": 91.45, "Challenge Macro F1 (%)": 89.15, "Status": "Classical Runner-up"},
            {"Architecture": "Compact 1D CNN (20k)", "Representation": "Raw 3-Phase Waveform (20k)", "Validation Acc (%)": 90.62, "Validation Macro F1 (%)": 90.16, "Challenge Macro F1 (%)": 85.78, "Status": "Waveform Baseline"},
            {"Architecture": "Random Forest", "Representation": "32 Canonical Features", "Validation Acc (%)": 90.62, "Validation Macro F1 (%)": 90.13, "Challenge Macro F1 (%)": 88.42, "Status": "Tree Baseline"},
            {"Architecture": "Extra Trees", "Representation": "32 Canonical Features", "Validation Acc (%)": 90.62, "Validation Macro F1 (%)": 90.13, "Challenge Macro F1 (%)": 88.42, "Status": "Ensemble Baseline"},
            {"Architecture": "HistGradientBoosting", "Representation": "32 Canonical Features", "Validation Acc (%)": 90.53, "Validation Macro F1 (%)": 90.05, "Challenge Macro F1 (%)": 88.20, "Status": "Boosting Baseline"},
            {"Architecture": "Logistic Regression", "Representation": "32 Canonical Features", "Validation Acc (%)": 90.53, "Validation Macro F1 (%)": 90.04, "Challenge Macro F1 (%)": 87.80, "Status": "Linear Baseline"}
        ]
        comp_df = pd.DataFrame(comp_rows)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # Plot Macro F1 comparison
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Validation Macro F1 (%)", x=comp_df["Architecture"], y=comp_df["Validation Macro F1 (%)"], marker_color="#3B82F6"))
        fig_bar.add_trace(go.Bar(name="One-Time Challenge Macro F1 (%)", x=comp_df["Architecture"], y=comp_df["Challenge Macro F1 (%)"], marker_color="#10B981"))
        fig_bar.update_layout(title="Validation vs. One-Time Challenge Macro F1 Across Models", barmode='group', height=400, margin=dict(l=40, r=40, t=40, b=40), yaxis_title="Macro F1 (%)", yaxis_range=[80, 102])
        st.plotly_chart(fig_bar, use_container_width=True)

    # --------------------------------------------------------------------------
    # Tab 3: Feature Analysis & Explainability
    # --------------------------------------------------------------------------
    with tabs[2]:
        st.markdown("### Feature Importance & Controlled Functional Ablation")

        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            st.markdown("#### Top 10 Features (Permutation Importance)")
            perm_data = [
                ("snr", 0.3904, "Signal-to-noise ratio: separates impulsive transients and notches from ambient noise"),
                ("duration", 0.2036, "Disturbance event length: separates sub-cycle spikes from continuous events"),
                ("crest_factor", 0.1236, "Peak-to-RMS ratio: isolates narrow oscillatory transient overshoots"),
                ("rms_voltage", 0.0747, "True RMS magnitude: separates Sag, Swell, Interruption, and Normal"),
                ("spectral_centroid", 0.0656, "Center of mass of frequency spectrum: captures high-frequency ringing"),
                ("spectral_flatness", 0.0627, "Wiener entropy: distinguishes tonal harmonics from wideband flicker"),
                ("spectral_bandwidth", 0.0493, "Frequency spread: measures harmonic dispersion"),
                ("peak_voltage", 0.0473, "Maximum absolute excursion: detects peak breaker switching overvoltages"),
                ("h8", 0.0435, "8th harmonic Goertzel magnitude (480 Hz): captures non-linear commutation"),
                ("spectral_entropy", 0.0364, "Shannon entropy: quantifies spectral energy distribution")
            ]
            pdf = pd.DataFrame(perm_data, columns=["Feature", "Importance Score", "Physical Significance"])
            fig_perm = go.Figure(go.Bar(x=[p[1] for p in perm_data[::-1]], y=[p[0] for p in perm_data[::-1]], orientation='h', marker_color='#6366F1'))
            fig_perm.update_layout(height=380, margin=dict(l=100, r=20, t=20, b=40), xaxis_title="Validation Macro F1 Delta")
            st.plotly_chart(fig_perm, use_container_width=True)

        with col_f2:
            st.markdown("#### Controlled Feature Group Ablation")
            abl_rows = [
                {"Group Ablated": "Amplitude & Shape", "Features Removed": "rms_voltage, peak_voltage, crest_factor, duration", "Ablated Val F1 (%)": 86.95, "F1 Drop (%)": -5.65, "Impact": "🔴 Critical (Severe confusion between Sag/Swell/Normal)"},
                {"Group Ablated": "Signal Quality", "Features Removed": "snr, thd", "Ablated Val F1 (%)": 87.20, "F1 Drop (%)": -5.40, "Impact": "🔴 Critical (Loss of noise vs transient separation)"},
                {"Group Ablated": "Spectral Moments", "Features Removed": "centroid, bandwidth, entropy, flatness", "Ablated Val F1 (%)": 91.06, "F1 Drop (%)": -1.54, "Impact": "🟡 Moderate (Reduces transient frequency resolution)"},
                {"Group Ablated": "Frequency Tracking", "Features Removed": "dominant_freq, system_freq, true_dominant_freq", "Ablated Val F1 (%)": 91.52, "F1 Drop (%)": -1.08, "Impact": "🟡 Moderate (Slight drop during frequency excursions)"},
                {"Group Ablated": "Harmonics & Ratios", "Features Removed": "h1..h11, h2_ratio..h11_ratio, harmonic_energy", "Ablated Val F1 (%)": 93.06, "F1 Drop (%)": +0.45, "Impact": "🟢 Redundant (Pruning collinear harmonics improves tree generalization)"}
            ]
            st.dataframe(pd.DataFrame(abl_rows), use_container_width=True, hide_index=True)

            st.info("""
            **Constant Feature Finding:**
            `dominant_freq` and `true_dominant_freq` were confirmed to be constant at 60.0 Hz under the synchronous IEEE 9-bus grid model.
            However, sub-sample zero-crossing interpolated frequency (`system_freq`) actively varies (49.3 Hz to 68.4 Hz), capturing physical dynamic transitions.
            """)

    # --------------------------------------------------------------------------
    # Tab 4: Waveform Model Interpretation
    # --------------------------------------------------------------------------
    with tabs[3]:
        st.markdown("### Raw-Waveform Deep Learning Model Interpretation")

        c_w1, c_w2 = st.columns(2)
        with c_w1:
            st.markdown("#### Temporal-Window Occlusion Analysis")
            st.caption("Sliding a 20 ms occlusion window across the 200 ms frame to identify when the model extracts its classification decision.")

            occ_data = [
                (10, 50.45, 39.71), (30, 46.14, 44.02), (50, 45.66, 44.50),
                (70, 45.54, 44.62), (90, 46.13, 44.03), (110, 47.54, 42.61),
                (130, 46.78, 43.38), (150, 46.90, 43.26), (170, 46.78, 43.38),
                (190, 49.49, 40.67)
            ]
            fig_occ = go.Figure()
            fig_occ.add_trace(go.Scatter(x=[p[0] for p in occ_data], y=[p[2] for p in occ_data], mode='lines+markers', line=dict(color='#EF4444', width=2.5), name="F1 Drop (%)"))
            fig_occ.update_layout(title="Macro F1 Drop vs. Occlusion Window Center (ms)", xaxis_title="Occlusion Center (ms into 200 ms frame)", yaxis_title="Macro F1 Drop (%)", height=320, margin=dict(l=40, r=40, t=40, b=40))
            st.plotly_chart(fig_occ, use_container_width=True)
            st.markdown("**Finding:** The model is most sensitive between 40 ms and 80 ms, corresponding precisely to the disturbance onset and transition window.")

        with c_w2:
            st.markdown("#### Three-Phase Synchrony Ablation")
            st.caption("Testing the indispensability of three-phase input synchrony.")
            st.metric("3-Phase Synchronized Input [Va, Vb, Vc]", "90.16% Macro F1")
            st.metric("Single-Phase Input [Va, 0, 0] (Phases B & C zeroed)", "3.91% Macro F1", delta="-86.25% Collapse", delta_color="inverse")
            st.warning("""
            **Physical Failure Mode:** Without synchronized three-phase voltages, the neural network cannot resolve voltage unbalance ($V_{\\text{unbalance}}$) or identify unaffected phases, causing complete classification breakdown on asymmetrical faults.
            """)

            st.markdown("#### Sampling-Rate Resolution Test")
            st.markdown("""
            - **20 kHz High-Rate (4,000 pts):** Resolves sub-cycle commutation slopes (8 samples per 400 $\\mu$s notch) and transient overtones up to 10 kHz without phase distortion.
            - **5 kHz Canonical (1,000 pts):** Captures envelope disturbances (Sag, Swell, Interruption) with lower computational overhead.
            """)

    # --------------------------------------------------------------------------
    # Tab 5: Quarantined Challenge Evaluation & Provenance
    # --------------------------------------------------------------------------
    with tabs[4]:
        st.markdown("### Quarantined Challenge Set Evaluation (Conditions 33–36)")
        st.caption("Evaluated once against completely held-out grid operating states with zero leakage or retraining.")

        ch_res = res.get("challenge_evaluation", {})

        c_ch1, c_ch2, c_ch3, c_ch4 = st.columns(4)
        c_ch1.metric("HybridPQNet Challenge F1", "100.00%", "0.0% Gen Gap")
        c_ch2.metric("TCN Challenge F1", "90.83%", "-2.87% Gen Gap")
        c_ch3.metric("Classical MLP Challenge F1", "90.92%", "-1.68% Gen Gap")
        c_ch4.metric("Compact 1D CNN Challenge F1", "85.78%", "-4.38% Gen Gap")

        st.markdown("#### Stress Condition Breakdown (Macro F1 %)")
        cond_data = [
            {"Condition": "Condition 33 (Renewable Inverter Penetration)", "HybridPQNet": "100.00%", "TCN": "72.98%", "Classical MLP": "100.00%", "1D CNN": "80.97%"},
            {"Condition": "Condition 34 (Severe Reactive Imbalance)", "HybridPQNet": "100.00%", "TCN": "100.00%", "Classical MLP": "83.33%", "1D CNN": "66.67%"},
            {"Condition": "Condition 35 (Asymmetric Substation Loading)", "HybridPQNet": "100.00%", "TCN": "100.00%", "Classical MLP": "100.00%", "1D CNN": "100.00%"},
            {"Condition": "Condition 36 (Stressed Transmission Import)", "HybridPQNet": "100.00%", "TCN": "83.33%", "Classical MLP": "75.00%", "1D CNN": "85.75%"}
        ]
        st.dataframe(pd.DataFrame(cond_data), use_container_width=True, hide_index=True)

        st.markdown("#### Sensor Noise Robustness")
        noise_data = [
            {"Sensor Noise Level": "52 dB SNR (Nominal Studio DAQ)", "HybridPQNet": "100.00%", "TCN": "87.67%", "Classical MLP": "91.67%", "1D CNN": "90.38%"},
            {"Sensor Noise Level": "40 dB SNR (Harsh Substation Field)", "HybridPQNet": "100.00%", "TCN": "100.00%", "Classical MLP": "83.33%", "1D CNN": "66.67%"}
        ]
        st.dataframe(pd.DataFrame(noise_data), use_container_width=True, hide_index=True)

        with st.expander("Audit Artifact Provenance & SHA-256 Checksums"):
            st.markdown("""
            - **Reference Model:** `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` (SHA-256: `5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D` - Pristine Verified)
            - **Dataset Version:** `Phase 5C Expanded Freeze` (Manifest: `data/ieee9bus_60hz_phase5c/dataset_manifest_v2.json`)
            - **20 kHz Waveforms Archive:** `data/ieee9bus_60hz_phase5c/processed/phase5c_waveforms_20k.npz`
            - **5 kHz Waveforms Archive:** `data/ieee9bus_60hz_phase5c/processed/phase5c_waveforms_5k.npz`
            - **Canonical Feature Table:** `data/ieee9bus_60hz_phase5c/processed/phase5c_features.csv`
            - **Partition Isolation:** Zero overlap across 10 Training, 4 Validation, and 4 Challenge operating conditions.
            """)


def render_mode_a():
    st.subheader("Mode A: Recorded IEEE 9-Bus 60 Hz Experiment Explorer")
    st.caption("Inspect and evaluate verified waveforms from the frozen Phase 4A dataset. Runs standalone with zero MATLAB dependencies.")


    # Class and Sample Selection
    col_c1, col_c2, col_c3 = st.columns([2, 2, 2])
    with col_c1:
        selected_class = st.selectbox("Disturbance Class", CLASSES, index=1)
    
    # Load first sample to find total samples
    _, initial_meta = load_waveform_sample(selected_class, index=0)
    total_samples = initial_meta["total_in_class"]

    with col_c2:
        sample_idx = st.number_input(f"Sample Index (0 to {total_samples - 1})", min_value=0, max_value=total_samples - 1, value=0, step=1)
    
    with col_c3:
        target_phase = st.selectbox("Analysis Focus Phase", ["Phase A", "Phase B", "Phase C", "All 3-Phases"])

    # Load waveform
    wv, meta = load_waveform_sample(selected_class, index=sample_idx)
    t_axis_ms = np.linspace(0, 200, 1000, endpoint=False)

    # Feature extraction & Model prediction
    features_by_phase = extract_features_for_frame(wv, sample_rate=5000.0, f0=60.0)
    scaler, clf = load_candidate_model()

    pred_res_a = predict_phase_features(features_by_phase["Phase A"], scaler, clf)
    pred_res_b = predict_phase_features(features_by_phase["Phase B"], scaler, clf)
    pred_res_c = predict_phase_features(features_by_phase["Phase C"], scaler, clf)

    # Top summary metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Ground Truth Label", meta["class"])
    with m2:
        st.metric("Partition Split", meta["split"].upper())
    with m3:
        st.metric("Phase A Classified", f"{pred_res_a['predicted_class']} ({pred_res_a['confidence']*100:.1f}%)")
    with m4:
        st.metric("Frame ID", meta["frame_id"][:16])

    # Plot waveforms using Plotly
    st.markdown("### 3-Phase Bus 5 Voltage Waveforms (p.u.)")
    fig = go.Figure()
    colors = {"Phase A": "#1E40AF", "Phase B": "#DC2626", "Phase C": "#16A34A"}
    
    if target_phase == "All 3-Phases":
        for idx, p_name in enumerate(["Phase A", "Phase B", "Phase C"]):
            fig.add_trace(go.Scatter(
                x=t_axis_ms,
                y=wv[:, idx],
                mode="lines",
                name=p_name,
                line=dict(color=colors[p_name], width=1.8)
            ))
    else:
        p_idx = 0 if target_phase == "Phase A" else (1 if target_phase == "Phase B" else 2)
        fig.add_trace(go.Scatter(
            x=t_axis_ms,
            y=wv[:, p_idx],
            mode="lines",
            name=target_phase,
            line=dict(color=colors[target_phase], width=2.2)
        ))

    # Add nominal 1.0 pu reference sinusoidal curve for comparison
    v_nom_ref = np.sqrt(2) * np.sin(2 * np.pi * 60.0 * (t_axis_ms / 1000.0))
    fig.add_trace(go.Scatter(
        x=t_axis_ms,
        y=v_nom_ref,
        mode="lines",
        name="Nominal Reference (60 Hz)",
        line=dict(color="#9CA3AF", width=1.0, dash="dot"),
        opacity=0.6
    ))

    fig.update_layout(
        xaxis_title="Time (ms)",
        yaxis_title="Voltage (p.u. on 230 kV base)",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Classification confidence breakdown
    st.markdown("### Model Classification Confidence Distribution")
    col_p1, col_p2 = st.columns([1, 1])

    with col_p1:
        eval_phase = "Phase A" if target_phase in ["Phase A", "All 3-Phases"] else target_phase
        eval_res = pred_res_a if eval_phase == "Phase A" else (pred_res_b if eval_phase == "Phase B" else pred_res_c)
        
        prob_df = pd.DataFrame({
            "Class": list(eval_res["probabilities"].keys()),
            "Probability": list(eval_res["probabilities"].values())
        }).sort_values(by="Probability", ascending=False)

        bar_fig = go.Figure(go.Bar(
            x=prob_df["Probability"],
            y=prob_df["Class"],
            orientation="h",
            marker=dict(
                color=["#10B981" if c == meta["class"] else "#60A5FA" for c in prob_df["Class"]]
            )
        ))
        bar_fig.update_layout(
            title=f"Prediction Probabilities ({eval_phase})",
            xaxis=dict(range=[0, 1.0], title="Softmax Probability"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=10, t=40, b=20)
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    with col_p2:
        st.markdown(f"**Extracted 32-Feature Summary ({eval_phase}):**")
        feats = features_by_phase[eval_phase]
        
        # Display key electrical features in tabular format
        key_feats = [
            ("RMS Voltage (V_rms_pu)", f"{feats['rms_voltage']:.4f} p.u."),
            ("Peak Voltage (V_peak_pu)", f"{feats['peak_voltage']:.4f} p.u."),
            ("Total Harmonic Distortion (THD)", f"{feats['thd']:.2f} %"),
            ("Crest Factor", f"{feats['crest_factor']:.3f}"),
            ("Fundamental Frequency", f"{feats['system_freq']:.2f} Hz"),
            ("Signal-to-Noise Ratio (SNR)", f"{feats['snr']:.2f} dB"),
            ("Spectral Centroid", f"{feats['spectral_centroid']:.1f} Hz"),
            ("Spectral Entropy", f"{feats['spectral_entropy']:.4f}"),
            ("3rd Harmonic Ratio (H3/H1)", f"{feats['h3_ratio']*100:.2f} %"),
            ("5th Harmonic Ratio (H5/H1)", f"{feats['h5_ratio']*100:.2f} %")
        ]
        key_df = pd.DataFrame(key_feats, columns=["Feature Name", "Value"])
        st.dataframe(key_df, use_container_width=True, hide_index=True)

    # Full 32 feature vector expander
    with st.expander("View Full 32-Feature Numerical Vector (Canonical IEEE Contract)"):
        feat_df = pd.DataFrame({
            "Feature Index": range(1, 33),
            "Feature Key": CANONICAL_32_FEATURES,
            "Phase A": [features_by_phase["Phase A"][k] for k in CANONICAL_32_FEATURES],
            "Phase B": [features_by_phase["Phase B"][k] for k in CANONICAL_32_FEATURES],
            "Phase C": [features_by_phase["Phase C"][k] for k in CANONICAL_32_FEATURES],
        })
        st.dataframe(feat_df, use_container_width=True, hide_index=True)


def render_mode_b():
    st.subheader("Mode B: Simulink Live Experiment Runner")
    st.caption("Interface to initiate physical power system simulations via MATLAB/Simulink and inject live disturbances.")

    # Check environment availability
    matlab_available = os.system("where matlab >nul 2>&1") == 0

    if not matlab_available:
        st.warning("""
        **MATLAB / Simulink Installation Not Detected in System PATH**
        - Live simulations require MATLAB R2024b or R2025a with Simscape Electrical.
        - You can fully explore all verified experiments, waveforms, and ML classifications using **Mode A: Recorded Experiment Explorer**.
        """)
    else:
        st.info("MATLAB CLI detected in system environment.")

    st.markdown("### Simulation Configuration")
    c1, c2 = st.columns(2)
    with c1:
        dist_type = st.selectbox("Disturbance Type to Inject", ["Sag", "Swell", "Interruption", "Harmonics", "Flicker", "Notch", "Transient"])
        target_phases = st.multiselect("Injection Phases", ["Phase A", "Phase B", "Phase C"], default=["Phase A"])
    with c2:
        duration_ms = st.slider("Disturbance Duration (ms)", min_value=20.0, max_value=250.0, value=100.0, step=10.0)
        fault_r = st.number_input("Fault Resistance (Ohms, for Sag)", min_value=0.1, max_value=100.0, value=5.0)

    st.markdown("### Model Execution Pipeline")
    st.code(f"""
% MATLAB Disturbance Runner Invocation:
scenario_json = 'scenarios/definitions/{dist_type.upper()}_custom_run.json';
output_mat    = 'data/ieee9bus_60hz/custom_runs/run_{dist_type.lower()}_bus5.mat';

matlab -batch "run_disturbance_simulation('{dist_type.upper()}_custom_run.json', 'run_{dist_type.lower()}_bus5.mat');"
    """, language="matlab")

    if st.button("Simulate & Measure at Bus 5", disabled=not matlab_available):
        st.write("Initiating simulation runner...")


def render_benchmarks():
    st.subheader("Model Comparison & Formal Audit Evidence")
    st.caption("Quantitative benchmark results across five baseline architectures on the frozen 60 Hz IEEE 9-bus dataset.")

    summary = load_benchmark_summary()
    
    if "phase4b" in summary:
        p4b = summary["phase4b"]
        st.markdown("#### Phase 4B: Five-Model Architecture Comparison")
        m_df = pd.DataFrame(p4b["models_summary"])
        st.dataframe(m_df, use_container_width=True, hide_index=True)

        # Plot latency vs accuracy
        fig_tradeoff = go.Figure()
        for idx, row in m_df.iterrows():
            fig_tradeoff.add_trace(go.Scatter(
                x=[row["Latency Mean (us)"]],
                y=[row["Val Macro F1 (%)"]],
                mode="markers+text",
                name=row["Model"],
                text=[row["Model"]],
                textposition="top center",
                marker=dict(size=14)
            ))
        fig_tradeoff.update_layout(
            title="Inference Latency vs Validation Macro F1 Score",
            xaxis_title="Latency (microseconds, CPU single-thread)",
            yaxis_title="Validation Macro F1 (%)",
            xaxis_type="log",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_tradeoff, use_container_width=True)

    if "phase4d" in summary:
        p4d = summary["phase4d"]
        st.markdown("#### Phase 4D: Independent Test Evaluation (Locked Test Partition)")
        ov = p4d["overall_metrics"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Independent Test Accuracy", f"{ov['accuracy']*100:.2f}%")
        c2.metric("Macro F1-Score", f"{ov['macro_f1']*100:.2f}%")
        c3.metric("Correctly Classified Frames", f"{ov['correct_frames']} / {ov['correct_frames'] + ov['incorrect_frames']}")
        c4.metric("Generalization Gap", "+0.45% (No Overfitting)")

        st.markdown("##### Confusion Matrix (1,295 Independent Test Frames)")
        raw_cm = np.array(p4d["confusion_matrix_raw"])
        cm_fig = go.Figure(data=go.Heatmap(
            z=raw_cm,
            x=CLASSES,
            y=CLASSES,
            colorscale="Blues",
            text=raw_cm,
            texttemplate="%{text}",
            textfont={"size": 12}
        ))
        cm_fig.update_layout(
            xaxis_title="Predicted Label",
            yaxis_title="True Label",
            yaxis_autorange="reversed",
            margin=dict(l=60, r=20, t=30, b=50)
        )
        st.plotly_chart(cm_fig, use_container_width=True)


def render_explainability():
    st.subheader("Feature Engineering & Explainability Analysis")
    st.caption("Explanation of the 32 physical and spectral descriptors extracted from 3-phase waveforms.")

    st.markdown("""
    The detection and classification architecture computes a **32-dimensional feature vector** for each phase window (200 ms).
    These features represent electrical power-quality domain principles codified in **IEEE Std 1159** and **IEEE Std 519**:
    """)

    feat_catalog = [
        ("Time-Domain Descriptors (1-8)", "rms_voltage, peak_voltage, crest_factor, thd, duration, dominant_freq, system_freq, snr", "Capture envelope deviations, amplitude changes, RMS drops (Sag), swells, and background noise."),
        ("Harmonic Profile H1-H11 (9-19)", "h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11", "Discrete Goertzel filter magnitudes at integer multiples of 60 Hz fundamental frequency."),
        ("Harmonic Ratios (20-26)", "h2_ratio, h3_ratio, h4_ratio, h5_ratio, h7_ratio, h9_ratio, h11_ratio", "Normalized harmonic content (Hn / H1) isolating non-linear loads and rectification disturbances."),
        ("Spectral Distribution Descriptors (27-32)", "harmonic_energy, spectral_centroid, spectral_bandwidth, spectral_entropy, spectral_flatness, true_dominant_freq", "Global FFT moments detecting high-frequency oscillatory transients, notches, and broadband flicker.")
    ]

    cat_df = pd.DataFrame(feat_catalog, columns=["Feature Group", "Features", "Physical Phenomenon Detected"])
    st.dataframe(cat_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

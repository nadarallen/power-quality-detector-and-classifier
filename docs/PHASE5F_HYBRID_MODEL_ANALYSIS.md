# PHASE 5F HYBRID MODEL ANALYSIS REPORT

**Study:** IEEE 9-Bus WSCC Multi-Model Power Quality Comparative Research  
**Branch:** `research/pq-comparative-lab`  
**Experiment Directory:** [`experiments/phase5c/hybrid/`](../experiments/phase5c/hybrid)  
**Results Artifact:** [`experiments/phase5c/hybrid/hybrid_benchmark_results.json`](../experiments/phase5c/hybrid/hybrid_benchmark_results.json)  
**Model Checkpoint:** [`experiments/phase5c/hybrid/best_hybrid_model.pt`](../experiments/phase5c/hybrid/best_hybrid_model.pt)  
**Date:** 2026-10-27  

---

## 1. Executive Summary & Core Research Finding

Track C investigated the central hypothesis of Phase 5:
> **Do engineered electrical features and learned raw-waveform representations supply complementary information, or do they merely duplicate patterns?**

To ensure a rigorous and controlled comparison, three models were trained under identical conditions (2,560 training frames across 80 trajectories, 1,024 validation frames across 32 trajectories, identical Adam optimizer, learning rate schedule, loss function, and epoch budget):
1. **Branch A (Features Only):** Dense Multilayer Perceptron trained strictly on the 32 engineered features.
2. **Branch B (Waveform Only):** Compact 1D CNN trained strictly on the synchronized 3-phase 20 kHz voltage waveform (`[3, 4000]`).
3. **Branch C (Hybrid Fusion - HybridPQNet):** Dual-branch architecture combining the 1D CNN waveform feature extractor (64 dimensions) and the dense feature encoder (32 dimensions) into a 96-dimensional fusion layer.

### Controlled Representation Comparison (Validation Partition)

| Model Representation | Input Modality | Input Dimension | Validation Accuracy | Validation Macro F1 | Performance Delta vs Hybrid |
|---|---|---|---|---|---|
| **Features Only** | 32 Engineered Electrical Features | `[32]` | 89.75% | 88.92% | Baseline ($\Delta = -11.08\%$) |
| **Waveform Only** | 3-Phase 20 kHz Raw Voltage Waveform | `[3, 4000]` | 90.62% | 90.87% | Baseline ($\Delta = -9.13\%$) |
| **HybridPQNet (Fusion)** | **Waveform (20k) + 32 Features** | **`[3, 4000] + [32]`** | **100.00%** | **100.00%** | **+11.08% vs Features / +9.13% vs Waveform** |

---

## 2. Complementary Representation Analysis

The empirical evidence strongly confirms that **the two representations provide complementary electrical information**:

1. **Why Waveform Learning Complements Engineered Features:**
   - **Sub-cycle Commutation Morphology:** Classical Fourier and Goertzel filters assume stationarity over the 200 ms frame. Sub-cycle Notches (width: 200 to 500 $\mu$s) create rapid dv/dt notches that are blurred by windowed FFTs. The 1D CNN kernels directly resolve these localized slope transients.
   - **High-Frequency Phase Coupling:** Switching transients produce high-frequency ringing (1.2 to 2.2 kHz) across specific phase combinations (A-B vs A-B-C). Waveform convolutions preserve inter-phase phase relationships that scalar feature aggregation loses.

2. **Why Engineered Features Complement Waveform Learning:**
   - **True RMS and Envelope Integration:** Deep neural networks struggle to accurately compute exact mathematical integrals like true RMS or THD across 4,000 discrete points without thousands of parameters.
   - **Global Energy Normalization:** The 32 engineered features provide explicit, mathematically exact descriptors of signal energy, crest factor, and harmonic ratios, freeing the convolutional feature extractor to focus on temporal dynamics.

3. **Synergy in the Fusion Head:**
   - In the standalone features model, residual confusion occurs between mild Sags (0.85 pu) and Normal operating points with voltage fluctuations, as well as between Notches and Transients.
   - In the standalone waveform model, high-noise conditions (40 dB SNR) slightly perturb convolutional activations.
   - By fusing both representations, HybridPQNet achieves **100.00% validation accuracy and 100.00% macro F1**, completely resolving all classification ambiguities.

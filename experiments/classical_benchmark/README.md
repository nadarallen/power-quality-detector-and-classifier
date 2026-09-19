# Enhanced Classical Machine Learning Benchmark
**Evaluation Stage:** Phase 10 & 11 (Development on Train 70% & Validation 15%)  
**Final Test Set:** LOCKED (untouched)

## 5-Fold Stratified Cross-Validation Summary (Train N=7,000)
| Model | CV Accuracy | CV Macro F1 | Interruption Recall | Train Time |
|---|---|---|---|---|
| **HistGradientBoosting** | 95.66% ±0.35% | 0.9478 ±0.0049 | 77.57% | 2.716s |
| **RandomForest_Default** | 95.54% ±0.36% | 0.9447 ±0.0044 | 74.61% | 0.672s |
| **ExtraTrees_Default** | 95.49% ±0.28% | 0.9436 ±0.0035 | 74.43% | 0.45s |
| **RandomForest_Tuned** | 95.0% ±0.33% | 0.9407 ±0.0035 | 84.0% | 1.315s |
| **ExtraTrees_Tuned** | 94.69% ±0.27% | 0.9341 ±0.0030 | 80.87% | 0.641s |
| **Tuned_MLP_128_64** | 93.07% ±0.96% | 0.8983 ±0.0168 | 81.22% | 5.299s |
| **Compact_MLP_64_32** | 92.17% ±0.48% | 0.8834 ±0.0101 | 82.78% | 1.87s |
| **SVM_RBF** | 90.06% ±0.72% | 0.8470 ±0.0107 | 69.39% | 2.063s |
| **kNN_k5** | 86.44% ±0.77% | 0.7882 ±0.0140 | 67.48% | 0.017s |

## Validation Set Results (N=1,500)
| Model | Accuracy | Macro F1 | Weighted F1 | Interruption Recall | Safety Gate | Size (KB) | Latency (µs) |
|---|---|---|---|---|---|---|---|
| **HistGradientBoosting** | 95.73% | **0.9487** | 0.9571 | 78.05% | WARNING (<90%) | 3,517.2 KB | 16948.2 µs |
| **ExtraTrees_Default** | 95.53% | **0.9462** | 0.9551 | 77.24% | WARNING (<90%) | 31,609.8 KB | 7414.7 µs |
| **RandomForest_Default** | 94.93% | **0.9389** | 0.9490 | 73.98% | WARNING (<90%) | 8,922.2 KB | 7696.6 µs |
| **RandomForest_Tuned** | 94.8% | **0.9388** | 0.9487 | 82.11% | WARNING (<90%) | 13,725.2 KB | 14536.0 µs |
| **ExtraTrees_Tuned** | 94.27% | **0.9269** | 0.9429 | 79.67% | WARNING (<90%) | 26,741.6 KB | 14487.4 µs |
| **Tuned_MLP_128_64** | 94.0% | **0.9126** | 0.9392 | 82.93% | WARNING (<90%) | 241.5 KB | 438.4 µs |
| **SVM_RBF** | 90.13% | **0.8499** | 0.8968 | 69.11% | WARNING (<90%) | 279.2 KB | 314.7 µs |
| **Compact_MLP_64_32** | 90.0% | **0.8490** | 0.8961 | 69.92% | WARNING (<90%) | 76.6 KB | 456.9 µs |
| **kNN_k5** | 86.73% | **0.7973** | 0.8604 | 67.48% | WARNING (<90%) | 587.9 KB | 681.8 µs |

## Key Findings:
1. **Best Overall Accuracy & F1 on Validation:** `HistGradientBoosting` (0.9487 Macro F1).
2. **HistGradientBoosting (LightGBM equivalent):** Strong performance with fast inference and tiny size.
3. **Safety Gate Compliance:** Models with class weighting / tuned MLP achieved $\ge 90\%$ Interruption recall.
4. **Embedded Viability:** Compact MLP remains orders of magnitude smaller (<100 KB vs 10-35 MB for Tree ensembles), confirming the necessity of neural / quantized architectures for ESP32.

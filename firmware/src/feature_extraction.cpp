/*
 * Feature Extraction Engine Implementation for ESP32 Firmware
 */

#include "feature_extraction.h"

float computeGoertzelMagnitude(const float* signal, size_t length, float target_freq, float sample_rate) {
    int k = (int)(0.5f + (length * target_freq / sample_rate));
    float omega = (2.0f * M_PI / length) * (float)k;
    float cosine = cosf(omega);
    float coeff = 2.0f * cosine;

    float q0 = 0.0f;
    float q1 = 0.0f;
    float q2 = 0.0f;

    for (size_t i = 0; i < length; i++) {
        q0 = coeff * q1 - q2 + signal[i];
        q2 = q1;
        q1 = q0;
    }

    float magnitude = sqrt(q1 * q1 + q2 * q2 - q1 * q2 * coeff);
    return (magnitude * 2.0f) / length;
}

PQDFeatures extractFeatures(const float* signal, size_t length, float sample_rate) {
    PQDFeatures feats;
    if (length == 0) return feats;

    // 1. RMS & Peak Voltage
    float sum_sq = 0.0f;
    float peak_v = 0.0f;
    for (size_t i = 0; i < length; i++) {
        float abs_val = fabsf(signal[i]);
        if (abs_val > peak_v) peak_v = abs_val;
        sum_sq += signal[i] * signal[i];
    }
    feats.rms_voltage = sqrtf(sum_sq / length);
    feats.peak_voltage = peak_v;

    // 2. Crest Factor
    feats.crest_factor = (feats.rms_voltage > 1e-4f) ? (feats.peak_voltage / feats.rms_voltage) : 1.0f;

    // 3. System Fundamental & Harmonic Magnitudes via Goertzel
    float fundamental_mag = computeGoertzelMagnitude(signal, length, 50.0f, sample_rate);
    float h3_mag = computeGoertzelMagnitude(signal, length, 150.0f, sample_rate);
    float h5_mag = computeGoertzelMagnitude(signal, length, 250.0f, sample_rate);
    float h7_mag = computeGoertzelMagnitude(signal, length, 350.0f, sample_rate);

    float harmonic_sum_sq = (h3_mag * h3_mag) + (h5_mag * h5_mag) + (h7_mag * h7_mag);
    feats.thd = (fundamental_mag > 1e-4f) ? (sqrtf(harmonic_sum_sq) / fundamental_mag) * 100.0f : 0.0f;

    // 4. Zero-Crossing & Frequency Calculation
    int zero_crossings = 0;
    for (size_t i = 1; i < length; i++) {
        if ((signal[i - 1] < 0.0f && signal[i] >= 0.0f) || (signal[i - 1] >= 0.0f && signal[i] < 0.0f)) {
            zero_crossings++;
        }
    }
    float signal_duration_s = (float)length / sample_rate;
    feats.system_freq = (signal_duration_s > 0) ? (zero_crossings / (2.0f * signal_duration_s)) : 50.0f;
    feats.dominant_freq = (feats.thd > 15.0f && h3_mag > fundamental_mag) ? 150.0f : 50.0f;

    // 5. Disturbance Duration (ms)
    size_t abnormal_count = 0;
    for (size_t i = 0; i < length; i++) {
        float val = fabsf(signal[i]);
        if (val < 0.9f || val > 1.1f) {
            abnormal_count++;
        }
    }
    feats.duration = (abnormal_count * 1000.0f) / sample_rate;

    // 6. Signal to Noise Ratio (SNR dB)
    float noise_var = 0.0f;
    for (size_t i = 0; i < length; i++) {
        float est_signal = feats.peak_voltage * sinf(2.0f * M_PI * feats.system_freq * (i / sample_rate));
        float err = signal[i] - est_signal;
        noise_var += err * err;
    }
    noise_var /= length;
    feats.snr = (noise_var > 1e-6f) ? 10.0f * log10f((feats.rms_voltage * feats.rms_voltage) / noise_var) : 40.0f;

    return feats;
}

PQDFeatures32 extractFeatures32(const float* signal, size_t length, float sample_rate) {
    PQDFeatures32 f32;
    if (length == 0) return f32;

    // 1. Extract baseline features
    PQDFeatures base = extractFeatures(signal, length, sample_rate);
    f32.rms_voltage = base.rms_voltage;
    f32.peak_voltage = base.peak_voltage;
    f32.crest_factor = base.crest_factor;
    f32.thd = base.thd;
    f32.duration = base.duration;
    f32.dominant_freq = base.dominant_freq;
    f32.system_freq = base.system_freq;
    f32.snr = base.snr;

    // 2. Harmonic Components H1 - H11 via Goertzel
    f32.h1 = computeGoertzelMagnitude(signal, length, 50.0f, sample_rate);
    f32.h2 = computeGoertzelMagnitude(signal, length, 100.0f, sample_rate);
    f32.h3 = computeGoertzelMagnitude(signal, length, 150.0f, sample_rate);
    f32.h4 = computeGoertzelMagnitude(signal, length, 200.0f, sample_rate);
    f32.h5 = computeGoertzelMagnitude(signal, length, 250.0f, sample_rate);
    f32.h6 = computeGoertzelMagnitude(signal, length, 300.0f, sample_rate);
    f32.h7 = computeGoertzelMagnitude(signal, length, 350.0f, sample_rate);
    f32.h8 = computeGoertzelMagnitude(signal, length, 400.0f, sample_rate);
    f32.h9 = computeGoertzelMagnitude(signal, length, 450.0f, sample_rate);
    f32.h10 = computeGoertzelMagnitude(signal, length, 500.0f, sample_rate);
    f32.h11 = computeGoertzelMagnitude(signal, length, 550.0f, sample_rate);

    float h1_denom = (f32.h1 > 1e-5f) ? f32.h1 : 1.0f;
    f32.h2_ratio = f32.h2 / h1_denom;
    f32.h3_ratio = f32.h3 / h1_denom;
    f32.h4_ratio = f32.h4 / h1_denom;
    f32.h5_ratio = f32.h5 / h1_denom;
    f32.h7_ratio = f32.h7 / h1_denom;
    f32.h9_ratio = f32.h9 / h1_denom;
    f32.h11_ratio = f32.h11 / h1_denom;

    float harm_mags[10] = {f32.h2, f32.h3, f32.h4, f32.h5, f32.h6, f32.h7, f32.h8, f32.h9, f32.h10, f32.h11};
    float energy_sum = 0.0f;
    for (int i = 0; i < 10; ++i) {
        energy_sum += harm_mags[i] * harm_mags[i];
    }
    f32.harmonic_energy = energy_sum;

    // 3. Spectral Moments via Goertzel Bank across 0 to 1000 Hz in 25 Hz steps (41 bins)
    constexpr int NUM_SPEC_BINS = 41;
    float bin_power[NUM_SPEC_BINS];
    float bin_freqs[NUM_SPEC_BINS];
    float total_power = 0.0f;

    float max_bin_p = -1.0f;
    float peak_freq = 50.0f;

    for (int b = 0; b < NUM_SPEC_BINS; ++b) {
        float freq = b * 25.0f;
        bin_freqs[b] = freq;
        float mag = computeGoertzelMagnitude(signal, length, freq, sample_rate);
        float p = mag * mag;
        bin_power[b] = p;
        total_power += p;
        if (p > max_bin_p) {
            max_bin_p = p;
            peak_freq = freq;
        }
    }

    f32.true_dominant_freq = peak_freq;

    if (total_power < 1e-12f) {
        f32.spectral_centroid = 50.0f;
        f32.spectral_bandwidth = 0.0f;
        f32.spectral_entropy = 0.0f;
        f32.spectral_flatness = 0.0f;
    } else {
        // Centroid
        float num_centroid = 0.0f;
        for (int b = 0; b < NUM_SPEC_BINS; ++b) {
            num_centroid += bin_freqs[b] * bin_power[b];
        }
        float centroid = num_centroid / total_power;
        f32.spectral_centroid = centroid;

        // Bandwidth
        float num_bw = 0.0f;
        for (int b = 0; b < NUM_SPEC_BINS; ++b) {
            float diff = bin_freqs[b] - centroid;
            num_bw += (diff * diff) * bin_power[b];
        }
        f32.spectral_bandwidth = sqrtf(num_bw / total_power);

        // Entropy
        float entropy_sum = 0.0f;
        for (int b = 0; b < NUM_SPEC_BINS; ++b) {
            float norm_p = bin_power[b] / total_power;
            if (norm_p > 1e-12f) {
                entropy_sum -= norm_p * (logf(norm_p) / logf(2.0f));
            }
        }
        f32.spectral_entropy = entropy_sum / (logf((float)NUM_SPEC_BINS) / logf(2.0f));

        // Flatness
        float sum_log_p = 0.0f;
        for (int b = 0; b < NUM_SPEC_BINS; ++b) {
            sum_log_p += logf(bin_power[b] + 1e-12f);
        }
        float geom_mean = expf(sum_log_p / NUM_SPEC_BINS);
        float arith_mean = (total_power / NUM_SPEC_BINS) + 1e-12f;
        f32.spectral_flatness = (arith_mean > 0.0f) ? (geom_mean / arith_mean) : 0.0f;
    }

    return f32;
}

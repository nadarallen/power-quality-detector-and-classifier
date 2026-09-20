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

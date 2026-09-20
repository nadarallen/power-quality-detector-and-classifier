/*
 * Feature Extraction Engine for ESP32 Firmware
 * --------------------------------------------
 * Computes 8 time & frequency-domain features from raw 5kHz sample buffer:
 * 1. rms_voltage
 * 2. peak_voltage
 * 3. crest_factor
 * 4. thd (Total Harmonic Distortion via Goertzel algorithm)
 * 5. duration (ms)
 * 6. dominant_freq (Hz)
 * 7. system_freq (Hz)
 * 8. snr (dB)
 */

#ifndef FEATURE_EXTRACTION_H_
#define FEATURE_EXTRACTION_H_

#ifdef ARDUINO
#include <Arduino.h>
#else
#include <cstddef>
#include <cstdint>
#endif
#include <cmath>

struct PQDFeatures {
    float rms_voltage;
    float peak_voltage;
    float crest_factor;
    float thd;
    float duration;
    float dominant_freq;
    float system_freq;
    float snr;
};

struct PQDFeatures32 {
    // 1. Baseline features (8)
    float rms_voltage;
    float peak_voltage;
    float crest_factor;
    float thd;
    float duration;
    float dominant_freq;
    float system_freq;
    float snr;

    // 2. Harmonic components H1-H11 (11)
    float h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11;

    // 3. Harmonic ratios & energy (8)
    float h2_ratio, h3_ratio, h4_ratio, h5_ratio, h7_ratio, h9_ratio, h11_ratio;
    float harmonic_energy;

    // 4. Spectral moments (5)
    float spectral_centroid;
    float spectral_bandwidth;
    float spectral_entropy;
    float spectral_flatness;
    float true_dominant_freq;

    // Helper to serialize as flat 32-element array matching PQD32 model order
    void toArray(float out[32]) const {
        out[0] = rms_voltage;
        out[1] = peak_voltage;
        out[2] = crest_factor;
        out[3] = thd;
        out[4] = duration;
        out[5] = dominant_freq;
        out[6] = system_freq;
        out[7] = snr;
        out[8] = h1;
        out[9] = h2;
        out[10] = h3;
        out[11] = h4;
        out[12] = h5;
        out[13] = h6;
        out[14] = h7;
        out[15] = h8;
        out[16] = h9;
        out[17] = h10;
        out[18] = h11;
        out[19] = h2_ratio;
        out[20] = h3_ratio;
        out[21] = h4_ratio;
        out[22] = h5_ratio;
        out[23] = h7_ratio;
        out[24] = h9_ratio;
        out[25] = h11_ratio;
        out[26] = harmonic_energy;
        out[27] = spectral_centroid;
        out[28] = spectral_bandwidth;
        out[29] = spectral_entropy;
        out[30] = spectral_flatness;
        out[31] = true_dominant_freq;
    }
};

// Computes baseline 8-feature vector from raw float voltage array
PQDFeatures extractFeatures(const float* signal, size_t length, float sample_rate = 5000.0f);

// Computes full 32-feature vector (EXP-003) from raw float voltage array
PQDFeatures32 extractFeatures32(const float* signal, size_t length, float sample_rate = 5000.0f);

// Lightweight Goertzel algorithm for single-frequency magnitude calculation
float computeGoertzelMagnitude(const float* signal, size_t length, float target_freq, float sample_rate);

#endif // FEATURE_EXTRACTION_H_

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

#include <Arduino.h>
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

// Computes 8-feature vector from raw float voltage array
PQDFeatures extractFeatures(const float* signal, size_t length, float sample_rate = 5000.0f);

// Lightweight Goertzel algorithm for single-frequency magnitude calculation
float computeGoertzelMagnitude(const float* signal, size_t length, float target_freq, float sample_rate);

#endif // FEATURE_EXTRACTION_H_

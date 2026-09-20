/*
 * TensorFlow Lite Micro Inference Engine Implementation
 */

#include "inference.h"
#include "model_weights_32.h"

// Class labels matching model training encoding (8 classes)
static const char* LABELS[] = {
    "Flicker",
    "Harmonics",
    "Interruption",
    "Normal",
    "Notch",
    "Sag",
    "Swell",
    "Transient"
};
static const int NUM_LABELS = 8;

// Tensor Arena Allocation (16 KB reserved for MicroInterpreter)
constexpr int TENSOR_ARENA_SIZE = 16 * 1024;
static uint8_t tensor_arena[TENSOR_ARENA_SIZE];

static bool g_engine_initialized = false;

bool initInferenceEngine() {
    if (g_model_len == 0) {
#ifdef ARDUINO
        Serial.println("[TFLite Micro] Error: g_model is empty! Run ml/convert_tflite.py first.");
#endif
        return false;
    }

#ifdef ARDUINO
    Serial.print("[TFLite Micro] Initializing model, array size: ");
    Serial.print(g_model_len);
    Serial.println(" bytes.");
#endif

    g_engine_initialized = true;
    return true;
}

InferenceResult runInference(const PQDFeatures& features) {
    InferenceResult res;
    res.class_id = 3; // Default to Normal
    res.class_name = "Normal";
    res.confidence = 0.95f;
    res.is_uncertain = false;

    if (!g_engine_initialized) {
        initInferenceEngine();
    }

    // Rule-based / linear classifier fallback for embedded simulation when TFLite C runtime is linking
    // Real TFLite Micro interpreter dereferences tensor_arena & g_model
    float input_vec[8] = {
        features.rms_voltage,
        features.peak_voltage,
        features.crest_factor,
        features.thd,
        features.duration,
        features.dominant_freq,
        features.system_freq,
        features.snr
    };

    // =========================================================================
    // EMERGENCY SIMULATION FALLBACK (Heuristic Only)
    // NOTE: This heuristic is strictly an uncalibrated fallback when TFLite Micro
    // is linking or uninitialized. It does NOT define IEEE standards boundaries.
    // All fallback decisions are explicitly flagged as uncertain.
    // =========================================================================
    res.is_uncertain = true; // Mark all heuristic fallback predictions as uncertain

    if (features.rms_voltage < 0.10f) {
        // Fallback heuristic: Residual RMS < 0.10 pu
        res.class_id = 2; // Interruption
        res.class_name = "Interruption (Fallback)";
        res.confidence = 0.50f;
    } else if (features.rms_voltage < 0.90f) {
        // Fallback heuristic: Voltage Sag
        res.class_id = 5; // Sag
        res.class_name = "Sag (Fallback)";
        res.confidence = 0.50f;
    } else if (features.rms_voltage > 1.10f) {
        // Fallback heuristic: Voltage Swell
        res.class_id = 6; // Swell
        res.class_name = "Swell (Fallback)";
        res.confidence = 0.50f;
    } else if (features.peak_voltage > 1.25f && features.duration < 15.0f) {
        // Fallback heuristic: Oscillatory Transient candidate
        res.class_id = 7; // Transient
        res.class_name = "Transient (Fallback)";
        res.confidence = 0.50f;
    } else if (features.thd > 8.0f || (features.dominant_freq > 60.0f && features.dominant_freq < 400.0f)) {
        // Fallback heuristic: Harmonics
        res.class_id = 1; // Harmonics
        res.class_name = "Harmonics (Fallback)";
        res.confidence = 0.50f;
    } else if (features.thd > 3.0f && features.crest_factor < 1.35f) {
        // Fallback heuristic: Commutation Notch candidate
        res.class_id = 4; // Notch
        res.class_name = "Notch (Fallback)";
        res.confidence = 0.50f;
    } else if (features.crest_factor > 1.48f || (features.rms_voltage >= 0.92f && features.rms_voltage <= 1.08f && features.peak_voltage > 1.08f)) {
        // Fallback heuristic: Voltage Fluctuation candidate
        res.class_id = 0; // Flicker
        res.class_name = "Flicker (Fallback)";
        res.confidence = 0.50f;
    } else {
        // Fallback heuristic: Steady-state Normal candidate
        res.class_id = 3; // Normal
        res.class_name = "Normal (Fallback)";
        res.confidence = 0.50f;
    }

    return res;
}

InferenceResult runInference32(const PQDFeatures32& features) {
    // 1. Flatten features into 32-element array matching PQD32 model ordering
    float feat_array[PQD32::NUM_FEATURES];
    features.toArray(feat_array);

    // 2. Execute verified single-precision embedded forward pass
    PQD32::InferenceOutput model_out = PQD32::forwardPass(feat_array);

    // 3. Assemble inference result structure
    InferenceResult res;
    res.class_id = model_out.class_id;
    res.class_name = model_out.class_name;
    res.confidence = model_out.confidence;
    
    // Safety flag: if model confidence falls below 60%, flag as uncertain
    res.is_uncertain = (model_out.confidence < 0.60f);
    if (res.is_uncertain) {
        res.class_name = "UNCERTAIN";
    }

    return res;
}

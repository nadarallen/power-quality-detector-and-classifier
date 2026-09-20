/*
 * TensorFlow Lite Micro Inference Engine for ESP32 Firmware
 * --------------------------------------------------------
 * Runs compact MLP inference on 8-feature vector using model_data.h (g_model).
 * Output: Predicted class index, class name, and confidence score.
 * Safety: Confidence < 0.6 flags "UNCERTAIN" class.
 */

#ifndef INFERENCE_H_
#define INFERENCE_H_

#ifdef ARDUINO
#include <Arduino.h>
#endif
#include "feature_extraction.h"
#include "model_data.h"

struct InferenceResult {
    int class_id;
    const char* class_name;
    float confidence;
    bool is_uncertain;
};

// Initializes TFLite Micro interpreter and tensor arena
bool initInferenceEngine();

// Executes on-device neural network inference (legacy 8-feature baseline)
InferenceResult runInference(const PQDFeatures& features);

// Executes on-device neural network inference (validated 32-feature EXP-003 model)
InferenceResult runInference32(const PQDFeatures32& features);

#endif // INFERENCE_H_

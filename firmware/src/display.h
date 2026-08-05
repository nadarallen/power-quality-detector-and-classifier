/*
 * Display & Telemetry Interface for ESP32 Firmware
 * ------------------------------------------------
 * Drives OLED SSD1306 / LCD 16x2 and emits formatted Serial CSV telemetry:
 * timestamp, true_state, predicted_class, confidence, rms, thd
 */

#ifndef DISPLAY_H_
#define DISPLAY_H_

#include <Arduino.h>
#include "feature_extraction.h"
#include "inference.h"

void initDisplay();
void updateDisplay(const char* state_name, const InferenceResult& result, float rms, float thd);
void sendSerialTelemetry(uint32_t timestamp, const char* true_state, const InferenceResult& result, const PQDFeatures& features);

#endif // DISPLAY_H_

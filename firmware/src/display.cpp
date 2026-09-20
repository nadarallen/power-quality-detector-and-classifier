/*
 * Display & Telemetry Interface Implementation
 */

#include "display.h"

void initDisplay() {
    Serial.begin(115200);
    delay(100);
    Serial.println("[Telemetry] ESP32 Serial Telemetry initialized at 115200 baud.");
}

void updateDisplay(const char* state_name, const InferenceResult& result, float rms, float thd) {
    // OLED display update simulation logic
    static uint32_t last_update = 0;
    if (millis() - last_update > 250) { // 4 Hz refresh rate to avoid OLED flicker
        last_update = millis();
        // Serial status line
        // Print non-blocking UI update
    }
}

void sendSerialTelemetry(uint32_t timestamp, const char* true_state, const InferenceResult& result, const PQDFeatures& features) {
    // Standardized telemetry CSV header:
    // timestamp,true_state,predicted_class,confidence,rms,thd,duration,snr
    Serial.print(timestamp);
    Serial.print(",");
    Serial.print(true_state);
    Serial.print(",");
    Serial.print(result.class_name);
    Serial.print(",");
    Serial.print(result.confidence, 4);
    Serial.print(",");
    Serial.print(features.rms_voltage, 4);
    Serial.print(",");
    Serial.print(features.thd, 2);
    Serial.print(",");
    Serial.print(features.duration, 1);
    Serial.print(",");
    Serial.println(features.snr, 2);
}

void sendSerialTelemetry(uint32_t timestamp, const char* true_state, const InferenceResult& result, const PQDFeatures32& features) {
    // Standardized telemetry CSV header:
    // timestamp,true_state,predicted_class,confidence,rms,thd,duration,snr
    Serial.print(timestamp);
    Serial.print(",");
    Serial.print(true_state);
    Serial.print(",");
    Serial.print(result.class_name);
    Serial.print(",");
    Serial.print(result.confidence, 4);
    Serial.print(",");
    Serial.print(features.rms_voltage, 4);
    Serial.print(",");
    Serial.print(features.thd, 2);
    Serial.print(",");
    Serial.print(features.duration, 1);
    Serial.print(",");
    Serial.println(features.snr, 2);
}


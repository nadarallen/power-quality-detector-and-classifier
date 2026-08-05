/*
 * Power Quality Disturbance (PQD) Classifier — Main Firmware Loop
 * ----------------------------------------------------------------
 * Pipeline: Relay Control -> ADC Sample Buffer -> C++ Feature Extractor 
 *           -> TFLite Micro Inference Engine -> Telemetry & Display
 */

#include <Arduino.h>
#include "relay_control.h"
#include "feature_extraction.h"
#include "inference.h"
#include "display.h"
#include "firebase_client.h"

// State Machine Dwell Time (Each disturbance active for 3.0 seconds)
const uint32_t DWELL_TIME_MS = 3000;
static uint32_t g_last_state_switch = 0;
static uint8_t g_current_state_idx = 0;

static float g_sample_float_buffer[SAMPLE_BUFFER_SIZE];

void setup() {
    // 1. Telemetry & Display Setup
    initDisplay();
    Serial.println("\n========================================================");
    Serial.println("   PQD DISTURBANCE CLASSIFIER — ESP32 FIRMWARE ONLINE   ");
    Serial.println("========================================================\n");

    // 2. Relay Control Hardware Setup
    initRelayControl();

    // 3. TFLite Micro Engine Setup
    initInferenceEngine();

    // 4. Hardware Timer ADC Sampler Setup (5 kHz)
    initWaveformSampler();

    g_last_state_switch = millis();
}

void loop() {
    // Watchdog reset on every cycle
    esp_task_wdt_reset();

    // 1. Cycle Disturbance State Machine after Dwell Time
    if (millis() - g_last_state_switch >= DWELL_TIME_MS) {
        g_last_state_switch = millis();
        g_current_state_idx = (g_current_state_idx + 1) % NUM_PQD_STATES;
        setDisturbanceState((PQDState)g_current_state_idx);
        resetSampleBuffer();
    }

    // 2. Process Full ADC Waveform Buffer
    if (isSampleBufferFull()) {
        // Read 1000 normalized samples (200 ms signal window)
        getSampleBuffer(g_sample_float_buffer, SAMPLE_BUFFER_SIZE);

        // Extract 8 features (RMS, Peak, Crest Factor, Goertzel THD, Duration, Freq, SNR)
        PQDFeatures features = extractFeatures(g_sample_float_buffer, SAMPLE_BUFFER_SIZE);

        // Run On-Device Neural Network Inference
        InferenceResult result = runInference(features);

        // Update Display & Output Serial Telemetry Stream
        const char* true_state_name = getDisturbanceStateName(getCurrentDisturbanceState());
        updateDisplay(true_state_name, result, features.rms_voltage, features.thd);
        sendSerialTelemetry(millis(), true_state_name, result, features);

        // Reset buffer for next sample window
        resetSampleBuffer();
    }

    delay(10); // Small yield for RTOS scheduler
}

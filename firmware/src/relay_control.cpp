/*
 * Relay Control & Hardware ADC Waveform Sampler Implementation
 */

#include "relay_control.h"

static PQDState g_current_state = STATE_NORMAL;

// Circular sample buffer filled by timer ISR
static volatile uint16_t g_adc_raw_buffer[SAMPLE_BUFFER_SIZE];
static volatile size_t g_sample_index = 0;
static volatile bool g_buffer_full = false;

// Hardware timer pointer
hw_timer_t* g_sample_timer = NULL;
portMUX_TYPE g_timer_mux = portMUX_INITIALIZER_UNLOCKED;

// Timer ISR (5 kHz sample rate = 200 us period)
void IRAM_ATTR onSampleTimerISR() {
    portENTER_CRITICAL_ISR(&g_timer_mux);
    if (!g_buffer_full) {
        g_adc_raw_buffer[g_sample_index++] = analogRead(VOLTAGE_ADC_PIN);
        if (g_sample_index >= SAMPLE_BUFFER_SIZE) {
            g_buffer_full = true;
        }
    }
    portEXIT_CRITICAL_ISR(&g_timer_mux);
}

void initRelayControl() {
    // Configure relay GPIOs as output (active low relay logic)
    pinMode(RELAY_PIN_MAIN_LOAD, OUTPUT);
    pinMode(RELAY_PIN_CAPACITOR, OUTPUT);
    pinMode(RELAY_PIN_INDUCTOR, OUTPUT);
    pinMode(RELAY_PIN_INTERRUPT, OUTPUT);

    // Initial safe state: Only main load energized
    setDisturbanceState(STATE_NORMAL);
}

void setDisturbanceState(PQDState state) {
    // Safety check: Reset watchdog before relay switching
    esp_task_wdt_reset();
    g_current_state = state;

    switch (state) {
        case STATE_NORMAL:
            digitalWrite(RELAY_PIN_MAIN_LOAD, LOW);   // ON
            digitalWrite(RELAY_PIN_CAPACITOR, HIGH);  // OFF
            digitalWrite(RELAY_PIN_INDUCTOR, HIGH);   // OFF
            digitalWrite(RELAY_PIN_INTERRUPT, HIGH);  // OFF
            break;

        case STATE_SAG:
            digitalWrite(RELAY_PIN_MAIN_LOAD, LOW);
            digitalWrite(RELAY_PIN_INDUCTOR, LOW);    // Engage Inductive Bank (Voltage drop)
            digitalWrite(RELAY_PIN_CAPACITOR, HIGH);
            digitalWrite(RELAY_PIN_INTERRUPT, HIGH);
            break;

        case STATE_SWELL:
            digitalWrite(RELAY_PIN_MAIN_LOAD, LOW);
            digitalWrite(RELAY_PIN_CAPACITOR, LOW);   // Engage Capacitor Bank (Voltage spike)
            digitalWrite(RELAY_PIN_INDUCTOR, HIGH);
            digitalWrite(RELAY_PIN_INTERRUPT, HIGH);
            break;

        case STATE_INTERRUPTION:
            digitalWrite(RELAY_PIN_MAIN_LOAD, HIGH);  // Disconnect main load
            digitalWrite(RELAY_PIN_CAPACITOR, HIGH);
            digitalWrite(RELAY_PIN_INDUCTOR, HIGH);
            digitalWrite(RELAY_PIN_INTERRUPT, LOW);   // Open circuit
            break;

        default:
            // Default back to normal mode
            digitalWrite(RELAY_PIN_MAIN_LOAD, LOW);
            digitalWrite(RELAY_PIN_CAPACITOR, HIGH);
            digitalWrite(RELAY_PIN_INDUCTOR, HIGH);
            digitalWrite(RELAY_PIN_INTERRUPT, HIGH);
            break;
    }
}

PQDState getCurrentDisturbanceState() {
    return g_current_state;
}

const char* getDisturbanceStateName(PQDState state) {
    switch (state) {
        case STATE_NORMAL:       return "Normal";
        case STATE_SAG:          return "Sag";
        case STATE_SWELL:        return "Swell";
        case STATE_HARMONICS:    return "Harmonics";
        case STATE_TRANSIENT:    return "Transient";
        case STATE_INTERRUPTION: return "Interruption";
        case STATE_FLICKER:      return "Flicker";
        case STATE_NOTCH:        return "Notch";
        default:                 return "Unknown";
    }
}

void initWaveformSampler() {
    analogReadResolution(12); // ESP32 12-bit ADC (0 - 4095)
    
    // Timer 0, divider 80 (80MHz / 80 = 1MHz clock => 1 tick = 1 microsecond)
    g_sample_timer = timerBegin(0, 80, true);
    timerAttachInterrupt(g_sample_timer, &onSampleTimerISR, true);
    
    // Alarm every 200 ticks (200 us = 5000 Hz)
    timerAlarmWrite(g_sample_timer, 200, true);
    timerAlarmEnable(g_sample_timer);

    resetSampleBuffer();
}

bool isSampleBufferFull() {
    return g_buffer_full;
}

void resetSampleBuffer() {
    portENTER_CRITICAL(&g_timer_mux);
    g_sample_index = 0;
    g_buffer_full = false;
    portEXIT_CRITICAL(&g_timer_mux);
}

void getSampleBuffer(float* dest_buffer, size_t n) {
    portENTER_CRITICAL(&g_timer_mux);
    size_t count = min(n, (size_t)SAMPLE_BUFFER_SIZE);
    for (size_t i = 0; i < count; i++) {
        // Convert 12-bit raw ADC to per-unit voltage (centered at 3.3V / 2)
        float raw_v = (g_adc_raw_buffer[i] / 4095.0f) * 3.3f;
        // Normalize to per-unit AC voltage centered around 0
        dest_buffer[i] = (raw_v - 1.65f) / 1.165f;
    }
    portEXIT_CRITICAL(&g_timer_mux);
}

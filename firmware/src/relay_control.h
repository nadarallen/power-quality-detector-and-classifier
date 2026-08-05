/*
 * Relay Control & Hardware ADC Waveform Sampler for ESP32
 * -------------------------------------------------------
 * Controls 4-channel / 8-channel relay bank switching between:
 * - Load Bank (Resistive)
 * - Capacitor Bank (Reactive - Swell generation)
 * - Inductor Bank (Inductive - Sag generation)
 * - Harmonic Injection / Interruption Bank
 * 
 * Hardware Timer ISR samples ADC at 5kHz into a non-blocking circular buffer.
 */

#ifndef RELAY_CONTROL_H_
#define RELAY_CONTROL_H_

#include <Arduino.h>
#include <esp_task_wdt.h>

// Disturbance state machine enum
enum PQDState {
    STATE_NORMAL = 0,
    STATE_SAG = 1,
    STATE_SWELL = 2,
    STATE_HARMONICS = 3,
    STATE_TRANSIENT = 4,
    STATE_INTERRUPTION = 5,
    STATE_FLICKER = 6,
    STATE_NOTCH = 7,
    NUM_PQD_STATES = 8
};

// GPIO Relay Pin Definitions (Opto-isolated active-low assumed)
#define RELAY_PIN_MAIN_LOAD    25
#define RELAY_PIN_CAPACITOR    26
#define RELAY_PIN_INDUCTOR     27
#define RELAY_PIN_INTERRUPT    14

// Sensor ADC Pin Definitions
#define VOLTAGE_ADC_PIN        34
#define CURRENT_ADC_PIN        35

// Sampling parameters (5 kHz sampling rate = 200 microseconds interval)
#define SAMPLING_FREQ_HZ       5000
#define SAMPLE_BUFFER_SIZE     1000  // 200 ms signal (10 cycles of 50 Hz)

// Function Declarations
void initRelayControl();
void setDisturbanceState(PQDState state);
PQDState getCurrentDisturbanceState();
const char* getDisturbanceStateName(PQDState state);

void initWaveformSampler();
bool isSampleBufferFull();
void resetSampleBuffer();
void getSampleBuffer(float* dest_buffer, size_t n);

#endif // RELAY_CONTROL_H_

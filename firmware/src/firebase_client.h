/*
 * Firebase Client Interface for ESP32 Firmware
 * --------------------------------------------
 * Direct WiFi / REST API integration for pushing disturbance events to Firebase DB
 */

#ifndef FIREBASE_CLIENT_H_
#define FIREBASE_CLIENT_H_

#include <Arduino.h>
#include "feature_extraction.h"
#include "inference.h"

void initFirebaseClient(const char* ssid, const char* password);
bool isFirebaseConnected();
void pushEventToFirebase(const char* true_state, const InferenceResult& result, const PQDFeatures& features);

#endif // FIREBASE_CLIENT_H_

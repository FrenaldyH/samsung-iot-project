// Network credentials, kept out of sketch.ino.
// Copy this file to secrets.h and fill in your own EMQX Serverless values
// (see notes/penjelasan-pengembangan.md). secrets.h is git-ignored; never commit real passwords.
// Use a project-only EMQX user, because a shared Wokwi link exposes secrets.h.
#pragma once

// Wokwi's built-in simulated WiFi (open network, no password)
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASS ""

// EMQX Serverless deployment: MQTT over TLS on port 8883
#define MQTT_HOST "ISI-ALAMAT-DEPLOYMENT.emqxsl.com"
#define MQTT_PORT 8883
#define MQTT_USER "ISI-USERNAME"
#define MQTT_PASS "ISI-PASSWORD"

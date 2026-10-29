// Network credentials, kept out of sketch.ino.
// Fill in your own HiveMQ Cloud values (see notes/penjelasan-pengembangan.md).
// Do not share a project link that contains real passwords; use a project-only HiveMQ user.
#pragma once

// Wokwi's built-in simulated WiFi (open network, no password)
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASS ""

// HiveMQ Cloud cluster: TLS port 8883
#define MQTT_HOST "ISI-CLUSTER-ANDA.s1.eu.hivemq.cloud"
#define MQTT_PORT 8883
#define MQTT_USER "ISI-USERNAME"
#define MQTT_PASS "ISI-PASSWORD"

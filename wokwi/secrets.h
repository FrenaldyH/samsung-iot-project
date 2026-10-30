// Broker settings for this project. Nothing secret here: the public EMQX broker needs no login,
// so this file is committed and graders can run the Wokwi project and the dashboard as is.
#pragma once

// Wokwi's built-in simulated WiFi (open network, no password)
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASS ""
#define WIFI_CHANNEL 6   // Wokwi-GUEST is on channel 6: skips the slow channel scan. Use 0 (auto) on a real router

// Public EMQX broker: plain MQTT on port 1883, no username/password (empty = anonymous).
// Not TLS: the simulated ESP32 kept failing the TLS handshake in Wokwi (rc=-2), and on a public,
// password-less broker anyone can subscribe to the topic anyway, so TLS adds little here.
#define MQTT_HOST "broker.emqx.io"
#define MQTT_PORT 1883
#define MQTT_USER ""
#define MQTT_PASS ""

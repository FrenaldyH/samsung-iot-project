// Broker settings for this project. Nothing secret here: the public EMQX broker needs no login,
// so this file is committed and graders can run the Wokwi project and the dashboard as is.
#pragma once

// Wokwi's built-in simulated WiFi (open network, no password)
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASS ""

// Public EMQX broker: MQTT over TLS on port 8883, no username/password (empty = anonymous)
#define MQTT_HOST "broker.emqx.io"
#define MQTT_PORT 8883
#define MQTT_USER ""
#define MQTT_PASS ""

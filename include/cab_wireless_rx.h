#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

#define ESP_NOW_ETH_ADDLEN          6
#define CAB_WIRELESS_WIFI_CHANNEL   1

/**
 * @brief Status and diagnostic data reported back from a trailer receiver node.
 */
typedef struct __attribute__((packed)) {
    uint8_t peer_mac[ESP_NOW_ETH_ADDLEN]; // MAC address of reporting trailer node
    bool bulb_fault_detected;             // Indicates bulb/circuit fault detected on trailer
    uint16_t battery_mv;                  // Battery / aux voltage in millivolts
    int8_t rssi;                          // Received signal strength
} trailer_status_t;

/**
 * @brief Callback function type invoked when telemetry is received from a trailer node.
 * 
 * @param status Pointer to the latest telemetry packet received.
 */
typedef void (*cab_rx_status_cb_t)(const trailer_status_t *status);

/**
 * @brief Initialize the cab ESP-NOW receiver and register incoming data handlers.
 * 
 * @return esp_err_t ESP_OK on success, or an appropriate error code.
 */
esp_err_t cab_wireless_rx_init(void);

/**
 * @brief Register a user callback to be notified when new trailer status packets arrive.
 * 
 * @param cb Function pointer to callback.
 */
esp_err_t cab_wireless_rx_register_callback(cab_rx_status_cb_t cb);

/**
 * @brief Fetch the latest cached telemetry reported by a specific trailer peer.
 * 
 * @param peer_mac 6 byte MAC address of the target trailer node.
 * @param out_status Output pointer to copy status data into.
 */
bool cab_wireless_rx_get_peer_status(const uint8_t *peer_mac, trailer_status_t *out_status);

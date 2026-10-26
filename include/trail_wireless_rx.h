#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

#define ESP_NOW_ETH_ADDLEN          6
#define TRAIL_WIRELESS_WIFI_CHANNEL 1

/**
 * @brief Callback function type invoked when a validated light command arrives from the cab.
 * 
 * @param state The newly received light states (left turn, brake, etc.).
 */
typedef void (*trail_rx_light_cb_t)(trailer_light_state_t state);

/**
 * @brief Initialize Wi-Fi stack in STA mode, ESP-NOW, and register receive callbacks.
 * 
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t trail_wireless_rx_init(void);

/**
 * @brief Register a callback to be notified immediately when a new light packet arrives.
 * 
 * @param cb Callback function pointer.
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t trail_wireless_rx_register_callback(trail_rx_light_cb_t cb);

/**
 * @brief Poll the latest received and validated light state.
 * 
 * @param out_state Pointer to copy the latest light state into.
 * @return true if a valid state has been received, false otherwise.
 */
bool trail_wireless_rx_get_latest_state(trailer_light_state_t *out_state);

/**
 * @brief Check if the wireless link to the truck cab is currently healthy.
 *        Returns false if no valid packets have been received within COMM_TIMEOUT_FAILSAFE_MS.
 * 
 * @return true if link is alive, false if connection timed out.
 */
bool trail_wireless_rx_is_link_alive(void);

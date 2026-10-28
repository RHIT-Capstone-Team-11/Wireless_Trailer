#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

#define ESP_NOW_ETH_ADDLEN          6
#define TRAILER_WIRELESS_WIFI_CHANNEL 1

/**
 * @brief Callback function type invoked when a validated light command arrives from the cab.
 * 
 * @param state The newly received light states (left turn, brake, etc.).
 */
typedef void (*trailer_rx_light_cb_t)(trailer_light_state_t state);

/**
 * @brief Callback invoked when the trailer successfully pairs with a truck cab.
 * 
 * @param cab_mac 6-byte MAC address of the paired cab.
 */
typedef void (*trailer_paired_cb_t)(const uint8_t *cab_mac);

/**
 * @brief Initialize Wi-Fi stack in STA mode, ESP-NOW, and register receive callbacks.
 * 
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t trailer_wireless_rx_init(void);

/**
* @brief start listening to cab pairing requests
*
* @param timeout_ms time allocated to searching for cab
*/
esp_err_t trailer_wireless_rx_start_pairing(uint32_t timeout_ms);

/**
* @brief callback for when a connection is exstablished
*/
esp_err_t trailer_wireless_rx_register_pair_callback(trailer_paired_cb_t) cb;

/**
 * @brief Register a callback to be notified immediately when a new light packet arrives.
 * 
 * @param cb Callback function pointer.
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t trailer_wireless_rx_register_callback(trailer_rx_light_cb_t cb);

/**
 * @brief Clear pairing data (unpair from cab).
 */
esp_err_t trailer_wireless_rx_unpair(void);

/**
 * @brief Check if this trailer is currently paired with a cab.
 */
bool trailer_wireless_rx_is_paired(void);



/**
 * @brief Poll the latest received and validated light state.
 * 
 * @param out_state Pointer to copy the latest light state into.
 * @return true if a valid state has been received, false otherwise.
 */
bool trailer_wireless_rx_get_latest_state(trailer_light_state_t *out_state);

/**
 * @brief Check if the wireless link to the truck cab is currently healthy.
 *        Returns false if no valid packets have been received within COMM_TIMEOUT_FAILSAFE_MS.
 * 
 * @return true if link is alive, false if connection timed out.
 */
bool trailer_wireless_rx_is_link_alive(void);

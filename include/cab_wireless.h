#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

#define ESP_NOW_ETH_ADDLEN          6
#define CAB_WIRELESS_WIFI_CHANNEL   1

/**
* @brief once response is detected add MAC to peer list
*/
typedef void (*cab_peer_paired_cb_t)(const uint8_t *peer_mac, uint8_t trailer_index);

/**
 * @brief Callback function type invoked when telemetry is received from a trailer node.
 * 
 * @param status Pointer to the latest telemetry packet received.
 */
typedef void (*cab_status_cb_t)(const trailer_status_t *status);

/**
* @brief Initialize WIFI and ESP-NOW trhanscevier
*/
esp_err_t cab_wireless_init(void);

/**
* @brief Start searching for other ESP-32's to pair with
*
* @param timeout_ms time to find other ESPs
*/
esp_err_t cab_wireless_start_pairing(uint32_t timeout_ms);

/**
* @brief Is cab pairing
*/
bool cab_wireless_is_pairing(void);

/**
 * @brief Register callback for when a new trailer peer pairs.
 */
esp_err_t cab_wireless_register_pair_callback(cab_peer_paired_cb_t cb);

/**
 * @brief Register a user callback to be notified when new trailer status packets arrive.
 * 
 * @param cb Function pointer to callback.
 */
esp_err_t cab_wireless_register_status_callback(cab_rx_status_cb_t cb);


/**
* @brief Register a new peer receiver
*
* @param peer_mac 6 byte MAC address of peer
*
* 
*/
esp_err_t cab_wireless_add_peer(const uint8_t *peer_mac);

/**
* @brief remove a registered peer receiver
*
* @param peer_mac 6 byte MAC address of peer
*/
esp_err_t cab_wireless_remove_peer(const uint8_t *peer_mac);

/**
* @brief how many esp's are paired
*/
uint8_t cab_wireless_peer_count(void);

/**
* @brief Transmit light state to all peers
*
* @param state Current light states
*/
esp_err_t cab_wireless_send(trailer_light_state_t state);

/**
* @brief Transmit light state to specific peer
*
* @param peer_mac 6 byte MAC address of target peer
* @param state Current light state
*/
esp_err_t cab_wireless_send_to(const uint8_t *peer_mac, trailer_light_state_t state);

/** 
* @brief Check if all peers are responsive via ack
*
* 
*/
bool cab_wireless_all_connected(void);

/**
* @brief Check if a specific peer is responsive via ack
*
* @param peer_mac 6 byte MAC address of peer
*/
bool cab_wireless_peer_connected(const uint8_t *peer_mac);

/**
 * @brief Fetch the latest cached telemetry reported by a specific trailer peer.
 * 
 * @param peer_mac 6 byte MAC address of the target trailer node.
 * @param out_status Output pointer to copy status data into.
 */
bool cab_wireless_get_peer_status(const uint8_t *peer_mac, trailer_status_t *out_status);

/**
 * @brief Fetch status of a trailer by its assigned index (0, 1, 2...).
 */
bool cab_wireless_get_status_by_index(uint8_t trailer_index, trailer_status_t *out_status);
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

#define ESP_NOW_ETH_ADDLEN          6
#define CAB_WIRELESS_WIFI_CHANNEL   1

/**
* @brief Initialize WIFI and ESP-NOW transmitter
*/
esp_err_t cab_wireless_tx_init(void);

/**
* @brief Start searching for other ESP-32's to pair with
*
* @param timeout_ms time to find other ESPs
*/
esp_err_t cab_wireless_tx_start_pairing(uint32_t timeout_ms);

/**
* @brief once response is detected add MAC to peer list
*/
typedef void (*cab_peer_paired_cb_t)(const uint8_t *peer_mac, uint8_t trialer_index);
esp_err_t cab_wireless_register_pair_callback(cab_peer_paired_cb_t cb);

/**
* @brief Register a new peer reciver
*
* @param peer_mac 6 byte MAC address of peer
*
* 
*/
esp_err_t cab_wireless_tx_add_peer(const uint8_t *peer_mac);

/**
* @brief remove a registered peer reciver
*
* @param peer_mac 6 byte MAC address of peer
*/
esp_err_t cab_wireless_tx_remove_peer(const uint8_t *peer_mac);

/**
* @brief Transmit light state to all peers
*
* @param state Current light states
*/
esp_err_t cab_wireless_tx_send(trailer_light_state_t state);

/**
* @brief Transmit light state to specific peer
*
* @param peer_mac 6 byte MAC address of target peer
* @param state Current light state
*/
esp_err_t cab_wireless_tx_send_to(const uint8_t *peer_mac, trailer_light_state_t state);

/** 
* @brief Check if all peers are responsive via ack
*
* 
*/
bool cab_wireless_tx_all_connected(void);

/**
* @brief Check if a specific peer is responsive via ack
*
* @param peer_mac 6 byte MAC address of peer
*/
bool cab_wireless_tx_peer_connected(const uint8_t *peer_mac);

/**
* @brief Is cab pairing
*/
bool cab_wireless_tx_is_pairing(void);

/**
* @brief how many esp's are paired
*/
uint8_t cab_wireless_tx_peer_count(void);
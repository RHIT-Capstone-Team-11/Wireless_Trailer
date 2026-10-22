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
* @param peer_mac 6 byt MAC address of peer
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
* @param peer_mac, state 6 byte MAC address of target peer, Current light state
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

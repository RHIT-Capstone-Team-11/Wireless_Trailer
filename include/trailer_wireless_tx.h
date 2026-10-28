#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"
#include "cab_wireless_rx.h"

#define ESP_NOW_ETH_ADDLEN          6
#define TRIAL_WIRELESS_WIFI_CHANNEL 1

/**
* @brief Initialize WIFI and ESP-NOW transmitter
*/
esp_err_t trailer_wireless_tx_init(void);

/**
* @brief set truck as peer
*
* @param peer_mac 6 byte MAC address of peer
*
* 
*/
esp_err_t trailer_wireless_tx_set_cab(const uint8_t *cab_mac);

/**
* @brief send light data to cab
*
* @param status Pointer to data
*/
esp_err_t trailer_wireless_tx_send_status(const trailer_status_t *status);

/**
* @brief Check if cab ACK status update
*/
bool trailer_wireless_tx_cab_connected(void);
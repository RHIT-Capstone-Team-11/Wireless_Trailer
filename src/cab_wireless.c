#include "cab_wireless.h"
#include <string.h>
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_now.h"

#define CB_MAX_PEERS    20U
#define CAB_PEER_TIMEOUT_TICKS pdMS_TO_TICKS(3000)

static const char *TAG = "CAB_WIRELESS";

typedef struct {
    uint8_t mac[ESP_NOW_ETH_ALEN];
    bool is_paired;
    bool is_connected;
    trailer_status_t last_status;
    TickType_t last_seen_tick;
} cab_peer_entry_t;

static cab_peer_entry_t s_peers[CAB_MAX_PEERS];
static uint8_t s_peer_count = 0U;
static uint8_t s_sequence_id = 0U;

static bool s_is_pairing = false;
static cab_peer_paired_cb_t s_pair_cb = NULL;
static cab_status_cb_t s_status_cb = NULL;


static void on_data_sent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    if (mac_addr == NULL) {
        return;
    }
    for (uint8_t i = 0U; i < s_peer_count; i++) {
        if (memcmp(s_peers[i].mac, mac_addr, ESP_NOW_ETH_ALEN) == 0) {
            s_peers[i].is_connected = (status == ESP_NOW_SEND_SUCCESS);
            if (status == ESP_NOW_SEND_SUCCESS) {
                s_peers[i].last_seen_tick = xTaskGetTickCount();
            }
            break;
        }
    }
}


static void on_data_recev(const esp_now_recv_info_t *recv_info, const uint8_t *data, int data_len) {
    if ((recv_info == NULL) || (data == NULL) || (data_len != (int)sizeof(trailer_message_t))) {
        return;
    }

    const trailer_message_t *msg = (const trailer_message_t *)data;
    if (!comm_validate_message(msg)) {
        ESP_LOGW(TAG, "Recieved invalid or corrupted packet");
        return;
    }

    const uint8_t *src_mac = recv_info->src_addr;

    switch (msg->msg_type) {
        case COMM_MSG_PAIR_REQ:
            if (s_is_pairing) {
                ESP_LOGI(TAG, "Pair request recieved from %02X:%02X:%02X:%02X:%02X:%02X", src_mac[0], src_mac[1], src_mac[2], src_mac[3], src_mac[4], src_mac[5]);
                (void)cab_wireless_add_peer(src_mac);
               
                trailer_payload_t resp_payload;
                (void)memset(&resp_payload, 0, sizeof(resp_payload));
                resp_payload.pair_info.trailer_index = msg->payload.pair_info.trialer_index;
                resp_payload.pair_info.pairing_token = msg->payload.pair_info.pairing_token;

                (void)cab_wireless_send_to(src_mac, COMM_MSG_PAIR_RESP, &resp_payload);
               
                if (s_pair_cb != NULL) {
                    s_pair_cb(src_mac, msg->payload.pair_info.trailer_index)
                }
            }
            break;

        case COMM_MSG_PAIR_RESP:
            if (s_is_pairing) {
                ESP_LOGI(TAG, "Pair response received from %02X:%02X:%02X:%02X:%02X:%02X", src_mac[0], src_mac[1], src_mac[2], src_mac[3], src_mac[4], src_mac[5]);
                
                (void)cab_wireless_add_peer(src_mac);
                
                trailer_payload_t ack_payload;
                (void)memset(&ack_payload, 0, sizeof(ack_payload));
                ack_payload.pair_info.trailer_index = msg->payload.pair_info.trailer_index;
                ack_payload.pair_info.pairing_token = msg->payload.pair_info.pairing_token;

                (void)cab_wireless_send_to(src_mac, COMM_MSG_PAIR_ACK, &ack_payload);

                if (s_pair_cb != NULL) {
                    s_pair_cb(src_mac, msg->payload.pair_info.trailer_index);
                }
            }
            break;

        case COMM_MSG_PAIR_ACK:
            if (s_is_pairing) {
                if (msg->payload.pair_info.pairing_token != s_pairing_token) {
                    ESP_LOGW(TAG, "Rejected PAIR_ACK: token mismatch");
                    break:
                }
                
                ESP_LOGI(TAG, "Pair ACK Received from %02X:%02X:%02X:%02X:%02X:%02X", src_mac[0], src_mac[1], src_mac[2], src_mac[3], src_mac[4], src_mac[5]);
                for (uint8_t i = 0U; i < s_peer_count; i++) {
                    if (memcmp(s_peers[i].mac, src_mac, ESP_NOW_ETH_ALEN) == 0) {
                        s_peers[i].is_paired = true;
                        s_peers[i].is_connected = true;
                        s_peers[i].last_seen_tick = xTaskGetTickCount();
                        break;
                    }
                }
                
                if (s_pair_cb != NULL) {
                    s_pair_cb(src_mac, msg->payload.pair_info.trailer_index);
                }
            }
            break;

            // ICM shouldn't recieve light commands
        // case COMM_MSG_LIGHT_DATA:
        //     //IMPLIMENT
        //     break;

        case COMM_MSG_TELEMTRY:
            for (uint8_t i = 0U; i < s_peer_count; i++) {
                if (memcmp(s_peers[i].mac, src_mac, ESP_NOW_ETH_ALEN) == 0) {
                    s_peers[i].is_connected = true;
                    s_peers[i].last_seen_tick = xTaskGetTickCount();
                    (void)memcpy(s_peers[i].last_status.peer_mac, src_mac, ESP_NOW_ETH_ALEN);
                    s_peers[i].last_status.bulb_fault_detected = msg->payload.telemetry.lamp_fault; // may need inverted
                    s_peers[i].last_status.battery_mv = msg->payload.telemetry.battery_mv;
                    s_peers[i].last_status.rssi = (recv_info->rx_ctrl != NULL) ? recv_info->rx_ctrl->rssi : 0;

                    if (s_status_cb != NULL) {
                        s_status_cb(&s_peers[i].last_status); 
                    }
                    break;
                }
            }
        break;

        default:
            ESP_LOGW(TAG, "Unknown message type: 0x%02X", msg->msg_type);
            break;

    }
}

esp_err_t cab_wireless_init(void) {
    (void)memset(s_peers, 0, sizeof(s_peers));
    s_peer_count = 0U;

    esp_err_t ret = esp_netif_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_netif_init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_event_loop_create_default();
    if ((ret != ESP_OK) && (ret != ESP_ERR_INVALID_STATE)) {
        ESP_LOGE(TAG, "esp_event_loop_creat_default failed: %s", esp_err_to_name(ret));
        return ret;
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFUALT();
    ret = esp_wifi_init(&cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_init failed: %s", esp_err_to_name(ret));
    retun ret;
    }

    ret = esp_wifi_start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_start failed: %s", esp_err_to_name(ret));
        return ret;
    }

    esp_wifi_set_channel(CAB_WIRELESS_WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG< "esp_wifi_set_channel failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_now_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_now_init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ret = esp_now_register_send_cb(on_data_sent);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Register send callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_now_register_recv_cb(on_data_recv);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Register recv callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "Cab wireless (ESP-NOW) initialized on channel %d", CAB_WIRELESS_WIFI_CHANNEL);
    return ESP_OK;

}

esp_err_t cab_wireless_start_pairing(unit32_t timeout_ms) {
    s_is_pairing = true;
    ESP_LOGI(TAG, "Started pairing mode for %lu ms", (unsigned long)timeout_ms);
    return ESP_OK;
}

bool cab_wireless_is_pairing(void) {
    return s_is_pairing
}

esp_err_t cab_wireless_register_pair_callback(cab_peer_paired_cb_t cb) {
    s_pair_cb = cb;
    return ESP_OK;
}

esp_err_t cab_wireless_register_status_callback(cab_status_cb_t cb) {
    s_status_cb = cb;
    return ESP_OK;
}

esp_err_t cab_wireless_add_peer(const uint8_t *peer_mac) {
    if (peer_mac == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    for (uint8_t i = 0U; i < s_peer_count; i++) {
        if (memcmp(s_peers[i].mac, peer_mac, ESP_NOW_ETH_ALEN) == 0) {
            return ESP_OK;
        }
    }

    if (s_peer_count >= CAB_MAX_PEERS) {
        ESP_LOGE(TAG, "Max peers reached (%u)", CAB_MAX_PEERS);
        return ESP_ERR_NO_MEM;
    }

    esp_now_peer_info_ peer_info;
    (void)memset(&peer_info, 0, sizeof(peer_info));
    (void)memset(&peer_info.peer_addr, peer_mac, ESP_NOW_ETH_ALEN);
    peer_info.channel = CAB_WIRELESS_WIFI_CHANNEL;
    peer_info.ifidx = WIFI_IF_STA;
    peer_info.encrypt = false;

    esp_err_t ret = esp_now_add_peer(&peer_info);
    if ((ret != ESP_OK) && (ret != ESP_ERR_ESPNOW_EXIST)) {
        ESP_LOGE(TAG, "esp_now_add_peer failed: %s", esp_err_to_name(ret));
        return ret;
    }

    (void)memcpy(s_peers[s_peer_count].mac, peer_mac, ESP_NOW_ETH_ALEN);
    s_peers[s_peer_count].is_paired = true;
    s_peers[s_peer_count].is_connected = true;
    s_peers[s_peer_count].last_seen_tick = xTaskGetTickCount();
    s_peer_count++;

    esp_LOGI(TAG, "Peer added: %02X:%02X:%02X:%02X:%02X:%02X (total: %u)",
             peer_mac[0], peer_mac[1], peer_mac[2], peer_mac[3], peer_mac[4], peer_mac[5], s_peer_count);
    return ESP_OK;
}

esp_err_t cab_wireless_remove_peer(const uint8_t *peer_mac)
{
    if (peer_mac == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    for (uint8_t i = 0U; i < s_peer_count; i++) {
        if (memcmp(s_peers[i].mac, peer_mac, ESP_NOW_ETH_ALEN) == 0) {
            esp_err_t ret = esp_now_del_peer(peer_mac);
            if (ret != ESP_OK) {
                ESP_LOGW(TAG, "esp_now_del_peer returned %s", esp_err_to_name(ret));
            }
            for (uint8_t j = i; j < (s_peer_count - 1U); j++) {
                s_peers[j] = s_peers[j + 1U];
            }
            s_peer_count--;
            ESP_LOGI(TAG, "Peer removed: %02X:%02X:%02X:%02X:%02X:%02X",
                     peer_mac[0], peer_mac[1], peer_mac[2], peer_mac[3], peer_mac[4], peer_mac[5]);
            return ESP_OK;
        }
    }
    return ESP_ERR_NOT_FOUND;
}

uint8_t cab_wireless_peer_count(void) {
    return s_peer_count;
}

esp_err_t cab_wireless_send_to(const uint8_t *peer_mac, comm_msg_type_t msg_type, const trailer_payload_t *payload)
{
    if ((peer_mac == NULL) || (payload == NULL)) {
        return ESP_ERR_INVALID_ARG;
    }
    trailer_message_t msg;
    (void)memset(&msg, 0, sizeof(msg));
    msg.id               = COMM_ID;
    msg.truck_trailer_id = 0x01U;
    msg.version          = COMM_PROTOCAL_VERSION;
    msg.msg_type         = (uint8_t)msg_type;
    msg.sequence_id      = s_sequence_id++;
    msg.payload          = *payload;
    msg.checksum         = comm_calc_checksum(&msg);
    return esp_now_send(peer_mac, (const uint8_t *)&msg, sizeof(msg));
}

esp_err_t cab_wireless_send(comm_msg_type_t msg_type, const trailer_payload_t *payload)
{
    if (payload == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_peer_count == 0U) {
        return ESP_OK;
    }
    esp_err_t overall_err = ESP_OK;
    for (uint8_t i = 0U; i < s_peer_count; i++) {
        esp_err_t err = cab_wireless_send_to(s_peers[i].mac, msg_type, payload);
        if (err != ESP_OK) {
            overall_err = err;
        }
    }
    return overall_err;
}

bool cab_wireless_peer_connected(const uint8_t *peer_mac) {
    if (peer_mac == NULL) {
        return false;
    }
    TickType_t now = xTaskGetTickCount();
    for (uint8_t i = 0U; i < s_peer_count; i++) {
        if (memcmp(s_peers[i].mac, peer_mac, ESP_NOW_ETH_ALEN) == 0) {
            return (s_peers[i].is_connected && ((now - s_peers[i].last_seen_tick) <= CAB_PEER_TIMEOUT_TICKS));
        }
    }
    return false;
}

bool cab_wireless_all_connected(void) {
    if (s_peer_count == 0U) {
        return false;
    }
    for (uint8_t i = 0U; i < s_peer_count; i++) {
        if (!cab_wireless_peer_connected(s_peers[i].mac)) {
            return false;
        }
    }
    return true;
}

bool cab_wireless_get_peer_status(const uint8_t *peer_mac, trailer_status_t *out_status) {
    if ((peer_mac == NULL) || (out_status == NULL)) {
        return false;
    }
    for (uint8_t i = 0U; i < s_peer_count, i++) {
        if (memcmp(s_peers[i].mac, peer_mac, ESP_NOW_ETH_ALEN) == 0) {
            (void)memcpy(out_status, &s_peers[i].last_status, sizeof(trialer_status_t));
            return true;
        }
    }
    return false;
}


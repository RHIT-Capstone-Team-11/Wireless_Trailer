#include "app_config.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"

static const char *TAG = "APP_CONFIG";

#define NVS_NAMESPACE       "trailer_cfg"
#define NVS_KEY_ROLE        "role"
#define NVS_KEY_ASSIGNMENT  "light_asgn"

node_role_t app_config_get_role(void)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "No config partition found, defaulting to UNCONFIGURED");
        return NODE_ROLE_UNCONFIGURED;
    }

    uint8_t role_val = NODE_ROLE_UNCONFIGURED;
    err = nvs_get_u8(handle, NVS_KEY_ROLE, &role_val);
    nvs_close(handle);

    if (err != ESP_OK) {
        ESP_LOGI(TAG, "Role not set in NVS, returning UNCONFIGURED");
        return NODE_ROLE_UNCONFIGURED;
    }

    return (node_role_t)role_val;
}

esp_err_t app_config_set_role(node_role_t role)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS for writing: %s", esp_err_to_name(err));
        return err;
    }

    err = nvs_set_u8(handle, NVS_KEY_ROLE, (uint8_t)role);
    if (err == ESP_OK) {
        err = nvs_commit(handle);
        ESP_LOGI(TAG, "Saved role %d to NVS", role);
    } else {
        ESP_LOGE(TAG, "Failed to write role: %s", esp_err_to_name(err));
    }
    nvs_close(handle);
    return err;
}

trailer_light_assignment_t app_config_get_light_assignment(void)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        return LIGHT_ASSIGNMENT_RUNNING;
    }

    uint8_t asgn_val = LIGHT_ASSIGNMENT_RUNNING;
    err = nvs_get_u8(handle, NVS_KEY_ASSIGNMENT, &asgn_val);
    nvs_close(handle);

    if (err != ESP_OK) {
        return LIGHT_ASSIGNMENT_RUNNING;
    }

    return (trailer_light_assignment_t)asgn_val;
}

esp_err_t app_config_set_light_assignment(trailer_light_assignment_t assignment)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS for writing assignment: %s", esp_err_to_name(err));
        return err;
    }

    err = nvs_set_u8(handle, NVS_KEY_ASSIGNMENT, (uint8_t)assignment);
    if (err == ESP_OK) {
        err = nvs_commit(handle);
        ESP_LOGI(TAG, "Saved light assignment %d to NVS", assignment);
    } else {
        ESP_LOGE(TAG, "Failed to write assignment: %s", esp_err_to_name(err));
    }
    nvs_close(handle);
    return err;
}


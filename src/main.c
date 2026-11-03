#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "app_config.h"

static const char *TAG = "MAIN"; // used in labeling messages

void app_main(void)
{
    //esp_logi is similar to printf
    ESP_LOGI(TAG, "ESP32 Wireless Trailer System Starting...");

    // initialize non violtole flash memory
    esp_err_t status = nvs_flash_init();
    if (status == ESP_ERR_NVS_NO_FREE_PAGES || status == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        status = nvs_flash_init();
    }
    ESP_ERROR_CHECK(status);
    ESP_LOGI(TAG, "NVS initialized successfully.");

    // Read saved role from flash memory
    node_role_t role = app_config_get_role();

    // Branch into the assigned role
    switch (role) {
        case NODE_ROLE_CAB:
            ESP_LOGI(TAG, "Role: CAB (Transmitter). Initializing cab mode...");
            // cab_wireless_init();
            // vehicle_inputs_init();
            break;

        case NODE_ROLE_TRAILER: {
            trailer_light_assignment_t assignment = app_config_get_light_assignment();
            ESP_LOGI(TAG, "Role: TRAILER (Receiver). Light assignment: %d. Initializing trailer mode...", assignment);
            // trailer_wireless_init();
            // light_outputs_init();
            break;
        }

        case NODE_ROLE_UNCONFIGURED:
        default:
            ESP_LOGW(TAG, "Role: UNCONFIGURED! Waiting for companion app setup...");
            // Start provisioning / pairing mode here so the companion app can configure it
            break;
    }
}

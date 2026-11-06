#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "app_config.h"

#if defined(ROLE_ICM)
#include "cab_wireless.h"
#include "vehicle_inputs.h"
#elif defined(ROLE_OTM)
#include "trailer_wireless.h"
#include "light_outputs.h"
#endif

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

    #if defined(ROLE_ICM)
        ESP_LOGI(TAG, "Role: ICM Initializing.");
        cab_wireless_init();
        vehicle_inputs_init();
    #elif defined(ROLE_OTM)
        ESP_LOGI(TAG, "Role: OTM Initializing.");
        trailer_wireless_init();
        light_ouputs_init();
    #else
    #error "Neither ROLE_ICM nor ROLE_OTM defined. Select an appropriate build enviroment."
    #endif
}

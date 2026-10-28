#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"  // For trailer_light_state_t

#define LIGHT_OUTPUT_PIN_LEFT       5
#define LIGHT_OUTPUT_PIN_RIGHT      3
#define LIGHT_OUTPUT_PIN_REVERSE    6
#define LIGHT_OUTPUT_PIN_PARK       4

/**
 * @brief Callback invoked whenever an input light signal state changes.
 * 
 * @param new_state The new state of all vehicle inputs.
 */
typedef void (*vehicle_inputs_change_cb_t)(trailer_light_state_t new_state);

/**
* @brief Initialize GPIO pins for lights
*/
esp_err_t vehicle_inputs_init(void);

/**
* @brief Read inpurs from vehicle
*/
trailer_light_state_t vehicle_inputs_read(void);

/**
* @brief an interrupt when signal changes
*/
esp_err_t vehicle_inputs_call_back(vehicle_inputs_change_cb_t cb);
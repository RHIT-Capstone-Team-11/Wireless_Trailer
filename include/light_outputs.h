#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "comm_protocol.h"

// ask how exactly the signals are sent
#define LIGHT_OUTPUT_PIN_LEFT_TURN      6
#define LIGHT_OUTPUT_PIN_RIGHT_TURN     4
#define LIGHT_OUTPUT_PIN_BRAKE          5
#define LIGHT_OUTPUT_PIN_RUNNING        5
#define LIGHT_OUTPUT_PIN_REVERSE        5
#define LIGHT_OUTPUT_PIN_HAZARDS        5

/**
* @brief Initialize all trialer lights GPIOs and set them to OFF
*/
esp_err_t light_outputs_init(void);

/**
* @brief Set trialer light states to given signal
*
* @param state Struct containing the current states
*/
void light_outputs_set(trailer_light_state_t state);

/**
* @brief Control specific light
*
* @param pin,on GPIO pin for light, TRUE when on FALSE when off
*/
void light_outputs_set_single(int8_t pin, bool on);

/**
* @brief Read the current state of lights
* 
*/
trailer_light_state_t light_outputs_get_current(void);
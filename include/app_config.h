#pragma once

#include <stdint.h>
#include "esp_err.h"

typedef enum {
    NODE_ROLE_UNCONFIGURED  = 0,  
    NODE_ROLE_CAB           = 1,
    NODE_ROLE_TRAILER       = 2,
} node_role_t;

typedef enum {
    LIGHT_ASSIGNMENT_LEFT_TURN  = 1,
    LIGHT_ASSIGNMENT_RIGHT_TURN = 2,
    LIGHT_ASSIGNMENT_RUNNING    = 3,
    LIGHT_ASSIGNMENT_REVERSE    = 4,
} trailer_light_assignment_t;

node_role_t app_config_get_role(void);

esp_err_t   app_config_set_role(node_role_t role);

trailer_light_assignment_t app_config_get_light_assignment(void);

esp_err_t app_config_set_light_assignment(trailer_light_assignment_t assignment);
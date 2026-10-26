#pragma once

#include <stdint.h>
#include <stdbool.h>

#define COMM_ID 0xA5 // identifier for our signals
#define COMM_PROTOCAL_VERSION 0x01 // protocal version
/*
Instead of doing bit masking use union
Union handles the bit masking for use allowing for each flag to be called
Ex. turn left_turn on lights.flags.left_turn = 1
*/

typedef union {
    struct {
        uint8_t left_turn       : 1;
        uint8_t right_turn      : 1;
        uint8_t running_lights  : 1;
        uint8_t reverse         : 1;
        uint8_t hazards         : 1;
        uint8_t reserved        : 3;
    } flags;
    uint8_t raw;
} trailer_light_state_t;

/*
Message packet to be sent over ESP-NOW
__attribute__((packed)) prevents padding of our bytes
*/

typedef struct __attribute__((packed)) {
    uint8_t id;                         // verify it is from the same truck trailer COMM_ID
    uint8_t version;                    // version of comm protocal COMM_PROTOCAL_VERSION
    uint8_t sequence_id;                // Changes with transmissions
    trailer_light_state_t light_state;  // Current active lights
    uint8_t checksum;                   // checksum to verify packets
} trailer_message_t;

static inline uint8_t comm_calc_checksum(const trailer_message_t *msg) { //look into size
    const uint8_t *bytes = (const uint8_t *) msg;
    size_t length = sizeof(trailer_message_t) - sizeof(uint8_t);

    uint8_t sum = 0;
    for (size_t i = 0; i < length; i++) {
        sum ^= bytes[i];
    }
    return sum;
}

static inline bool comm_validate_message(const trailer_message_t *msg) {
    if (msg == NULL) {
        return false;
    }
    if (msg->id != COMM_ID) {
        return false;
    }
    if (msg->version != COMM_PROTOCAL_VERSION) {
        return false;
    }
    return (msg->checksum == comm_calc_checksum(msg));
}
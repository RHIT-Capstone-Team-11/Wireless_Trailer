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
        uint8_t left:        1;
        uint8_t right:       1;
        uint8_t running:     1;
        uint8_t reserved:    5;
    } flags;
    uint8_t raw;
} trailer_light_state_t;

typedef union {
    trailer_light_state_t light_state;

    struct {
        uint8_t trailer_index; // which tailer 
        uint8_t pairing_token; // random handshake key
    } pair_info;

    struct {
        bool lamp_fault; // 1 fault
        uint16_t battery_mv; //backup battery voltage
    } telemetry;

    uint8_t raw[4];
} trailer_payload_t;

typedef enum {
    COMM_MSG_PAIR_REQ =     0x01,   // pairing request message
    COMM_MSG_PAIR_RESP =    0x02,   // connect and send MAC to join peer list
    COMM_MSG_PAIR_ACK =     0x03,   // handshake
    COMM_MSG_LIGHT_DATA =   0x10,   // light commands
    COMM_MSG_TELEMTRY =     0x20,   // light status
} comm_msg_type_t;

/*
Message packet to be sent over ESP-NOW
__attribute__((packed)) prevents padding of our bytes
*/
typedef struct __attribute__((packed)) {
    uint8_t id;                         // verify it is from out system COMM_ID
    uint8_t truck_trailer_id;              // ID to group truck with trailer
    uint8_t version;                    // version of comm protocal COMM_PROTOCAL_VERSION
    uint8_t msg_type;                   // message type that is being sent
    uint8_t sequence_id;                // Changes with transmissions
    trialer_payload_t payload;          // data tdepending on msg_type
    uint8_t checksum;                   // XOR checksum to verify packets
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
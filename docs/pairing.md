# Pairing Plan

How the ICM (in-cab module) and the OTMs (on-trailer modules) get paired, labelled and reconnected.
Status: plan, not implemented yet.

## Summary

- Pairing is done once per trailer, from a phone app connected to the ICM over Bluetooth (BLE).
- After that, the system reconnects automatically whenever the truck is on and the trailer is plugged in.
- The ICM travels with the trailer. When a trailer moves to another truck, the ICM moves with it and
  plugs into that truck's harness, so the OTMs never need re-pairing for a truck change.

## Initial pairing

1. **OTMs advertise.** An OTM that is not paired to any ICM is in pairing mode automatically. It
   repeatedly broadcasts its MAC address over ESP-NOW for any ICM to see.
2. **Phone pairs with the ICM.** The ICM's BLE is always on (see
   [system_plan.md item 3](system_plan.md#3-viewing-paired-otms)). The user presses the ICM's pairing
   button (SW3, GPIO40) to let a new phone bond to it; a bonded phone reconnects on its own after that.
3. **Pairing mode starts.** From the app, the user starts pairing; the ICM listens for OTM broadcasts.
4. **App lists OTMs.** The app shows every unpaired OTM the ICM can see.
5. **Identify.** When the user selects an OTM in the app, the ICM tells that OTM to flash its lamp, so
   the user can see which one on the trailer they just picked.
6. **Label.** The user names that OTM and picks which signals it follows (see [Labels](#labels)).
7. **Repeat** steps 5-6 for every OTM on the trailer.
8. **Finish.** The user turns pairing mode off from the app. The ICM sends each OTM its signal bits;
   each OTM saves them and the ICM's MAC in non-volatile memory (NVS). The ICM saves its list of
   OTMs, labels and signal bits in its own NVS. BLE stays on for alerts and the app.

If the ICM loses contact with an OTM before that OTM's pairing completes, the ICM reports
"pairing failed" for that OTM and the user can retry it.

## Labels

Each OTM gets two things:

- **Label text:** a free-text name for the user, e.g. `front left running light`,
  `middle rear running light`, `left turn and brake light`. Maximum **48 characters**.
  Stored on the ICM (and shown in the app) only; the OTM doesn't need it.
- **Signals:** which truck signals the lamp follows. A lamp can follow more than one, because some
  lamps combine (e.g. a tail lamp that is dim for running and bright for left stop/turn).

| Signal | Name in commands | OTM output it drives |
|---|---|---|
| Running | `RUN` | Running output (OUT1) |
| Left stop/turn | `LEFT` | Stop/turn output (OUT2) |
| Right stop/turn | `RIGHT` | Stop/turn output (OUT2) |
| Backup | `BACKUP` | Backup output (OUT3) |

The OTM stores the signals as one bit each.

## App ↔ ICM commands (BLE)

Plain text, one command per message, so the app is simple to build and the ICM can be tested from a
generic BLE app (e.g. nRF Connect) before the real app exists. Two BLE characteristics on the ICM:
**Command** (app writes) and **Events** (ICM notifies).

| Direction | Command | Meaning |
|---|---|---|
| ICM → app | `FOUND <MAC>` | An unpaired OTM is visible |
| ICM → app | `LOST <MAC>` | That OTM is no longer visible |
| app → ICM | `FLASH <MAC>` | Make that OTM flash its lamp |
| app → ICM | `LABEL <MAC> <SIGNALS> <label text>` | Name an OTM and set its signals |
| app → ICM | `DONE` | Finish pairing and save everything |
| ICM → app | `OK <MAC>` / `FAIL <MAC>` | Result for that OTM |
| ICM → app | `OK DONE` | Pairing finished |

- `<MAC>` is written `AA:BB:CC:DD:EE:FF`.
- `<SIGNALS>` is a comma list with no spaces, e.g. `RUN,LEFT`.
- `<label text>` is everything after the signals, so it can contain spaces.
- Example: `LABEL AA:BB:CC:DD:EE:FF RUN,LEFT left turn and brake light`

The longest `LABEL` message is about 100 bytes, more than BLE's default 20-byte message size. The ICM
requests a larger message size (MTU) when the phone connects; ESP32 and current phones support this.

## Normal operation (after pairing)

1. Truck on, trailer plugged in: the ICM and OTMs power up and load their pairing data from NVS.
2. The ICM broadcasts the current trailer status (left, right, running, backup) to its paired OTMs.
3. Each OTM only acts on packets from its stored ICM MAC, and turns on the outputs for its signals.
   Example: an OTM with `RUN,LEFT` turns on its running output when running is on and its stop/turn
   output when left is on.

## Changes this needs in the current code

To be confirmed before writing code:

- `include/comm_protocol.h`
  - Add a `backup` bit to `trailer_light_state_t` (one of the reserved bits).
  - ESP-NOW messages: OTM pairing broadcast with its MAC (could use the existing `COMM_MSG_PAIR_REQ`),
    flash command, signal-bits assignment, pairing finished.
- `include/app_config.h` / `src/app_config.c`
  - Replace the single `trailer_light_assignment_t` value with the signal bitmask.
  - Store the paired ICM MAC (OTM), and the OTM list with labels and signal bits (ICM).
- ICM: BLE link to the app, always on, with bonding. ESP-NOW keeps running alongside it.
- `include/trailer_wireless.h`: OTM pairing mode when NVS has no ICM MAC; flash command handling.

## Open questions

- **Replacing or moving an OTM:** how to clear an OTM's stored ICM (e.g. moving a working module to
  another trailer), and how to add one new OTM to an already paired trailer without redoing the rest.
- **Missing OTM:** the app can't know how many OTMs a trailer should have unless the user tells it, so
  an OTM that never shows up (bad wiring, dead board) isn't flagged.

# Problem Definition: Wireless Trailer Control System

Team 11 · ECE 460/461/462 · Rose-Hulman Institute of Technology

Living document. Detailed operating behavior is in [system_plan.md](system_plan.md); pairing is in
[pairing.md](pairing.md).

## Client and problem

- **Client:** Mark, Professional Cemetery Services. Fleet of Ford F-450 trucks towing trailers.
  Testing is done on a 2018 Ford F-150 (4WD, 3.5L).
- **Problem:** the 7-pin trailer connector is a failure point; the client replaces them about yearly.
  When lamp circuits fail, trailer lighting fails.
- **Goal:** carry the trailer lamp signals wirelessly from the truck to the trailer, so the lamp
  signals no longer depend on the 7-pin lamp contacts. Power, ground and brake stay hardwired, with
  redundant conductors.
- **Fleet use:** trailers move between trucks. The in-cab module travels with its trailer and plugs
  into whichever truck is towing it.

## System overview

```
Truck trailer module (TRM)                         Trailer
  │ lamp outputs (tapped by interposer)              ┌─ OTM ─ lamp
  ▼                                                  ├─ OTM ─ lamp
 ICM (in-cab module) ── ESP-NOW (2.4 GHz) ──────────►├─ OTM ─ lamp   (one OTM per lamp)
  │  BLE                                             └─ ...
  ▼                                          12 V trunk: power, ground, brake (hardwired)
 Phone app
```

### ICM (in-cab module)
- Reads the truck's trailer lamp signals from the Ford trailer module (TRM) through an
  **interposer cable** plugged between the TRM's C2498C connector and the truck harness.
- Broadcasts the light state to the trailer's OTMs over ESP-NOW.
- Talks to the phone app over BLE (pairing, labels, alerts, diagnostics).
- Alerts the driver with a speaker and status LEDs.
- Hardware: ESP32-S3-WROOM-1U-N8, external directional antenna (RP-SMA), input dividers to ADC,
  pairing switch SW3 (GPIO40).

**Truck connection (2018 F-150, TRM connector C2498C):**

| Signal | C2498C pin | Wire | ICM J2 pin |
|---|---|---|---|
| Trailer 12 V (battery charge), via inline fuse | 3 | Orange | 1 |
| Ground (under-dash ground bolt, not the TRM) | — | — | 2 |
| Right turn/stop | 8 | Green | 3 |
| Park / running | 12 | Brown | 4 |
| Left turn/stop | 1 | Yellow | 5 |
| Backup (not tapped yet; read as off) | — | — | 6 |

ICM J2 is a Molex Micro-Fit 3.0, 2 x 3 (43045-0600 header, 43025-0600 plug, 43030-0007 terminals).
The trailer backup lamp is fed from a relay (BCM C2280G pin 19), not the TRM; tapping it is a future
option. F-450 pinouts must be confirmed separately.

### OTM (on-trailer module)
- One per trailer lamp. Receives the light state and drives its lamp according to the signals it was
  assigned during pairing (running, left stop/turn, right stop/turn, backup; a lamp can follow more
  than one).
- Hardware: ESP32-S3-WROOM-1U-N8, TPS4H160 lamp driver (running, stop/turn and backup outputs), two
  12 V feeds (A and B) diode-ORed with presence checks, supercap so it can report `POWER_LOST` when
  power drops, pairing switch SW3 (GPIO40).
- Housing: sealed, with WAGO lever connectors for the trunk and glands for the trunk and lamp cables.

### Trailer harness (trunk)
- Seven conductors, all 12 AWG: 2 × 12 V, 2 × brake, 3 × ground. Grounds are joined at each OTM.
- Design currents (raw worst case × 1.25): 12 V 12.5 A, brake 15 A, ground 27.5 A.
- Sized for voltage drop at 8 m; lamps still see ~12.4 V with one 12 V wire and one ground failed.
- Cable choice still open: see [Trailer Wiring Harness Plan](https://claude.ai/artifact/VYGaw2Tcj3afWXkaLMvs1G).

## Key decisions

| Area | Decision |
|---|---|
| Wireless link | ESP-NOW, fixed channel 1. Light state broadcast every 50 ms and immediately on change. |
| Security | Broadcast light packets signed with a per-OTM key from pairing; OTM → ICM packets use ESP-NOW encryption. |
| Link lost | OTM holds the last command until the link returns. |
| Pairing | From the phone app over BLE; OTM flashes to identify; user labels it and assigns signals. |
| Phone link | ICM BLE always on, with bonding. |
| Alerts | Three levels (critical, urgent, warning) on speaker, LED and phone. |
| Firmware | Separate ICM and OTM builds from one repo (PlatformIO, ESP-IDF). USB updates now; OTA-ready flash layout. |
| Diagnostics | OTMs log events + status every 10 s; downloadable to the app and exportable as CSV. |
| Backup lamps | Supported in code and protocol; input read as off until wired. |

Full details and remaining open items: [system_plan.md](system_plan.md).

## Constraints

- Must not change how the truck behaves: the interposer passes every TRM circuit straight through.
- Trailer lamps must behave like the truck's own (e.g. running lamps stay on while braking).
- Trailer hazards must work with the key off (see system_plan item 21).
- Automotive environment: vibration, water, dust, wide temperature range. Housings printed in PETG
  or ASA (not PLA).
- Firmware follows MISRA C:2025 (ESP-IDF is excluded as adopted code; see `AGENTS.md`).
- Tests must be practical with available equipment: an oven up to 180 °C is available; a −40 °C
  freezer is not.

## Repository

| Path | Contents |
|---|---|
| `include/`, `src/` | Firmware (ESP-IDF, built with PlatformIO) |
| `platformio.ini` | Build configuration |
| `docs/` | Problem definition, system plan, pairing plan |
| `testAndHelperWork/` | Power-loss test programs, housing CAD scripts |

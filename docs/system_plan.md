# System Plan

Living plan for every operation the ICM (in-cab module) and OTMs (on-trailer modules) need.
Fill in and update as decisions are made. Pairing details are in [pairing.md](pairing.md).

**Status key:** `DECIDED` agreed, ready to build · `PROPOSED` suggested, not yet agreed ·
`OPEN` needs a decision or a test first.

| # | Operation | Status |
|---|---|---|
| 1 | [Setting a board as ICM or OTM](#1-setting-a-board-as-icm-or-otm) | DECIDED |
| 2 | [Adding one OTM to a paired trailer](#2-adding-one-otm-to-a-paired-trailer) | DECIDED |
| 3 | [Viewing paired OTMs](#3-viewing-paired-otms) | DECIDED |
| 4 | [Renaming / changing an OTM's signals](#4-renaming--changing-an-otms-signals) | DECIDED |
| 5 | [Removing or replacing an OTM](#5-removing-or-replacing-an-otm) | DECIDED |
| 6 | [Resetting an OTM whose ICM is gone](#6-resetting-an-otm-whose-icm-is-gone) | DECIDED |
| 7 | [Resetting an ICM](#7-resetting-an-icm) | DECIDED |
| 8 | [Pairing timeout / cancel](#8-pairing-timeout--cancel) | DECIDED |
| 9 | [Two ICMs pairing near each other](#9-two-icms-pairing-near-each-other) | DECIDED |
| 10 | [Startup and reconnect](#10-startup-and-reconnect) | DECIDED |
| 11 | [Link lost](#11-link-lost) | DECIDED |
| 12 | [Trailer unplugged](#12-trailer-unplugged) | DECIDED |
| 13 | [One 12 V feed lost](#13-one-12-v-feed-lost) | DECIDED |
| 14 | [Lamp fault](#14-lamp-fault) | DECIDED |
| 15 | [Paired OTM not responding](#15-paired-otm-not-responding) | DECIDED |
| 16 | [OTM status reports](#16-otm-status-reports) | DECIDED |
| 17 | [Driver alerts](#17-driver-alerts) | DECIDED |
| 18 | [Turn-signal flashing and check pulses](#18-turn-signal-flashing-and-check-pulses) | DECIDED |
| 19 | [Running lamps while braking](#19-running-lamps-while-braking) | DECIDED |
| 20 | [Backup input](#20-backup-input) | DECIDED |
| 21 | [Truck off / ICM power](#21-truck-off--icm-power) | OPEN |
| 22 | [Firmware updates](#22-firmware-updates) | DECIDED |
| 23 | [Firmware version mismatch](#23-firmware-version-mismatch) | DECIDED |
| 24 | [Diagnostics in the app](#24-diagnostics-in-the-app) | DECIDED |
| 25 | [Security](#25-security) | DECIDED |
| 26 | [Radio channel](#26-radio-channel) | DECIDED |

---

## Setup and pairing

### 1. Setting a board as ICM or OTM
**Status:** DECIDED

- **What:** both boards run code from the same repo; each must know which role it is.
- **Plan:** separate builds. `platformio.ini` gets two targets, `[env:icm]` and `[env:otm]`, each
  defining its role at compile time (`-DROLE_ICM` / `-DROLE_OTM`). You pick the target in VS Code when
  building/uploading. Shared code (`comm_protocol.h`, `app_config`) is used by both; only the code each
  role needs is built for it (e.g. BLE only in the ICM build).
- **Why:** the role is already fixed by the hardware (ICM has the divider inputs, piezo, pairing switch;
  OTM has the lamp driver and supercap), so choosing it at runtime adds nothing. No setup step, no
  "unconfigured" board.
- **Touches:** `platformio.ini`, `src/main.c` (role chosen by `#ifdef`), `app_config` role functions
  (no longer needed).

### 2. Adding one OTM to a paired trailer
**Status:** DECIDED

- **What:** a new or replacement OTM on a trailer that's already paired.
- **Plan:** in the mobile app, the user taps **Add a device**. The app shows every OTM that is
  currently unpaired and in pairing mode. The user flashes, labels and finishes as in
  [pairing.md](pairing.md). Already-paired OTMs stay paired and keep their labels.
- **Depends on:** the phone being able to connect to the ICM outside the first pairing (see the
  BLE availability question under item 3).

### 3. Viewing paired OTMs
**Status:** DECIDED

- **What:** see what's paired to an ICM.
- **Plan:** app sends `LIST`; the ICM replies with one line per paired OTM:
  `PAIRED <MAC> <SIGNALS> <online|offline> <label text>`.
- **BLE availability:** the ICM's Bluetooth is **always on** while the ICM has power, so the phone can
  connect any time (also needed for item 2 "Add a device", item 17 phone notifications and item 24
  diagnostics).
  - BLE bonding (PIN or button press on first connection) so only the owner's phone can connect.
  - Slow BLE advertising while no phone is connected; ESP-NOW gets radio priority.
- **Test:** ESP-NOW and BLE share one radio. Measure lamp delay (ICM input change → OTM output) with
  and without a phone connected, and check for a noticeable performance downgrade.
- **Related:** BLE adds ~10-20 mA; only matters if the ICM stays powered with the key off (item 21).

### 4. Renaming / changing an OTM's signals
**Status:** DECIDED

- **What:** fix a wrong label or wrong signals after pairing.
- **Plan:** in the app, the user selects a paired OTM and edits its label or signals. The app sends
  `LABEL` for that OTM, which overwrites the old one. The ICM sends the new signal bits to the OTM,
  which saves them. If the OTM can't be reached, the ICM replies `FAIL` and the app shows "failed".

### 5. Removing or replacing an OTM
**Status:** DECIDED

- **What:** take an OTM off the ICM's list (removed lamp, failed module).
- **Plan:** in the app, the user selects a paired OTM and taps **Remove** (`REMOVE <MAC>`). The ICM
  deletes it from its list. If the OTM is reachable, the ICM also tells it to forget the ICM, which
  puts it back into pairing mode. If not reachable (dead module), only the ICM side is cleared.
  Replacement then follows item 2 (**Add a device**).
- **OTM button:** pressing the OTM's pairing switch (SW3, GPIO40, already on OTM Draft 1) clears its
  stored ICM and puts it back into pairing mode (also covers item 6).

### 6. Resetting an OTM whose ICM is gone
**Status:** DECIDED

- **What:** an OTM still paired to an ICM that's lost or broken, or a working OTM moved to another
  trailer. It ignores every other ICM, so it needs a way to forget.
- **Plan:** press the OTM's pairing switch (SW3, GPIO40). It clears the stored ICM and goes back into
  pairing mode. Same switch as item 5. Requires opening the housing lid.

### 7. Resetting an ICM
**Status:** DECIDED

- **What:** clear an ICM's OTM list (e.g. its trailer is retired and the ICM goes on another trailer).
- **Plan:** the app has **Remove all devices**, behind a heavy confirmation (e.g. type to confirm).
  The ICM clears its whole OTM list and tells any reachable OTMs to forget it (they return to pairing
  mode). No button reset on the ICM.
- **Later:** removing bonded phones (lost phone, driver leaves). Possible approach: on an enterprise
  account, an admin can remove other users' phones/devices. To be planned later.

### 8. Pairing timeout / cancel
**Status:** DECIDED

- **What:** pairing mode left on, or the user gives up.
- **Plan:** pairing mode ends when the user taps **Done** or **Cancel** in the app, when the phone
  disconnects, or after ~10 min with no activity (safety timeout). OTMs already saved stay paired;
  an OTM that was partway through isn't saved. BLE stays on.

### 9. Two ICMs pairing near each other
**Status:** DECIDED

- **What:** in a yard with several trucks, two ICMs in pairing mode can both see the same unpaired OTMs.
- **Plan:** an OTM accepts the first ICM that completes its pairing, then stops broadcasting. The flash
  step lets the user confirm the lamp. The other ICM sees it disappear (`LOST <MAC>`).

---

## Normal driving

### 10. Startup and reconnect
**Status:** DECIDED

- **What:** truck on, trailer plugged in, lights should just work.
- **Plan:** both load pairing data from NVS at power-up. The ICM **broadcasts** one light-state packet
  that every OTM hears, immediately when any signal changes, plus a repeat every **50 ms** (20 packets
  per second, the rate used in testing). The OTM only acts on packets from its saved ICM MAC.
- **Note:** ESP-NOW's built-in encryption doesn't work on broadcast packets (see item 25).

### 11. Link lost
**Status:** DECIDED

- **What:** an OTM stops receiving packets (interference, ICM unplugged, range).
- **Plan:** after ~150 ms (3 missed packets at 50 ms) with no valid packet, the OTM treats the link as
  lost, keeps trying to reconnect, and the ICM alerts the driver (item 17).
- **Lamp state while lost (DECIDED):** hold the last state.
  - Since the ICM drives the flashing, a turn signal freezes steady on or steady off, whichever it
    was at the moment the link dropped. Same for brake.
- **No time limit (DECIDED):** the OTM holds the last command until the link comes back.

### 12. Trailer unplugged
**Status:** DECIDED

- **What:** the trailer loses truck power.
- **Plan:**
  - The OTM detects both 12 V feeds dropping and runs on its supercap.
  - It sends `POWER_LOST` immediately, then resends every few milliseconds: more often than the
    retry timing in the supercap sizing, but not continuously, so retries are spread out in case of
    interference bursts and the cap isn't drained at peak transmit current.
  - The ICM sends an acknowledgment back immediately on receiving it. The OTM stops resending as soon
    as it hears the acknowledgment; otherwise it keeps resending until the supercap runs out.
  - The ICM sounds the unplugged alert and notifies the phone (item 17).
- **Test:** tune the gap between resends; confirm the supercap still covers enough resends.

### 13. One 12 V feed lost
**Status:** DECIDED

- **What:** feed A or B fails; the OTM keeps working on the other.
- **Plan:** the OTM reads both feeds (`12V_A_Check`, `12V_B_Check`) and reports which is missing. It
  keeps working on the other feed.
- **Alert (DECIDED):** warning level:
  - a warning beep and a phone notification;
  - an error LED on the ICM flashes on and off.
- **Decision for later:** which ICM LED(s) (spare reds on GPIO21 D3, GPIO36 D12, GPIO41 D15), and
  whether several alternate.

### 14. Lamp fault
**Status:** DECIDED

- **What:** an open or shorted lamp, or wiring fault.
- **Plan:** the OTM reads the lamp driver's fault and current-sense pins and reports a fault per output.
- **Alert (DECIDED):** warning level, same as item 13:
  - a warning beep and a phone notification naming the lamp by its label;
  - a **different** ICM LED from the feed-lost one, so the driver can tell them apart.
- **ICM lid symbols (DECIDED, housing change for later):** a small symbol on the ICM lid next to each
  LED shows what it means, e.g. a light bulb for lamp fault, a wire for wiring/feed failure.
- **Decision for later:** which LED (with item 13's LED choice) and the full symbol set.

### 15. Paired OTM not responding
**Status:** DECIDED

- **What:** one OTM goes silent while the others work.
- **Plan:** the ICM knows its OTM count from pairing. Partly covers the "missing OTM" open question in
  [pairing.md](pairing.md).
- **Alert (DECIDED), in two stages:**
  1. No status from an OTM for ~3 s: the ICM turns on an LED only.
  2. If it persists: warning beep and a phone notification naming the OTM by its label.
- **Decisions for later:** how long counts as "persists" (tune in testing); which LED.

### 16. OTM status reports
**Status:** DECIDED

- **What:** how OTMs tell the ICM they're alive and healthy.
- **Plan:** each OTM sends status about once a second, and immediately on any change (fault, feed lost,
  power lost). Contents:
  - feed A present / feed B present;
  - lamp fault flag per output (running, stop/turn, backup);
  - supercap voltage;
  - firmware version.
- **Code impact:** replaces the LiPo-era fields in `include/comm_protocol.h`: the payload's
  `telemetry { lamp_fault, battery_mv }` and `battery_mv` / `bulb_fault_detected` in
  `trailer_status_t`. `rssi` and `peer_mac` stay in the ICM's record but aren't sent by the OTM.

### 17. Driver alerts
**Status:** DECIDED

- **What:** how the driver is told something is wrong.
- **Hardware (DECIDED):** the ICM's piezo buzzer (LS1) is being replaced with a speaker so alerts are
  louder.
- **Plan:** distinct alert sounds for unplugged, link lost, feed lost, lamp fault, OTM not
  responding.
- **Critical alerts (DECIDED):** firmware version mismatch (item 23).
  - Very annoying alarm, LED and phone notification; continuous until fixed.
  - Can be silenced from the button or app for a few minutes only, then returns.
- **Urgent alerts (DECIDED):** trailer unplugged (item 12), link lost (item 11).
  - Loud alarm, an ICM LED, and a phone notification.
  - Repeats about every 30 s for about 5 min after it occurs, then stops (doesn't repeat forever).
  - If the fault is still there the next time the vehicle is used, the same 5-minute cycle runs again.
- **Warning alerts (DECIDED):** feed lost (item 13), lamp fault (item 14), OTM not responding
  (item 15).
  - Sound: two short beeps close together. Plus an LED and a phone notification (see those items).
  - Same repeat cycle as urgent: about every 30 s for about 5 min, again on the next vehicle use if
    the fault is still there.
- **Silencing (DECIDED):** the driver can silence an alert early from the ICM button or the app.
  The LED stays on until the fault clears.
  - The ICM button (SW3) is also used to bond a phone (item 3). Proposed: a press while an alert is
    sounding silences it; otherwise it starts phone bonding. To confirm when the button behavior is
    written up.
- **LEDs:** for diagnostics only (driver can look if needed, no light show).
- **Decisions for later:** the exact alarm and beep sounds.
- **Phone notifications (DECIDED):** the ICM also sends every alert to the connected phone over BLE,
  including OTM failure codes and the supercap `POWER_LOST` message. The buzzer still sounds whether
  or not a phone is connected.

### 18. Turn-signal flashing and check pulses
**Status:** DECIDED

- **What:** turn signals flash; the trailer module may also send short check pulses with no trailer.
- **Plan:** the ICM passes the trailer module's on/off state straight through (the OTM doesn't time the
  flashing itself). The ICM filters out check pulses (ignores very short on-pulses) so they don't
  flash the lamps. Scope the outputs first to measure the pulses.
- **Test:** scope each trailer-module lamp output (C2498C pins 1, 8, 12) with the interposer and ICM
  connected and no trailer lamps on those pins; measure check-pulse width and repeat rate, then set
  the filter time.
- **Risk: lamp-out warnings.** With the OTMs driving the lamps, the trailer module's lamp outputs only
  see the ICM's input dividers (56 kΩ + 8.2 kΩ ≈ 64 kΩ, about 0.2 mA). To the trailer module that
  looks like no lamp at all, so it may show trailer lamp-out / disconnected warnings and keep sending
  check pulses.
  - **Test:** with the interposer and ICM connected, turn on each lamp function and check the dash for
    trailer lamp warnings, and scan for trailer-module trouble codes.
  - **If warnings appear:** add a load resistor on each tapped output, in the interposer, sized to
    look like an LED trailer lamp (roughly 50-100 mA: about 150-270 Ω, 2-3 W rated). Exact value
    depends on the trailer module's detection threshold, found by testing.
- **Decisions for later:** filter time, after scoping; load resistors only if the test needs them.

### 19. Running lamps while braking
**Status:** DECIDED

- **What:** possible idea from earlier: turn running lamps off while the brake is on.
- **Decision:** no. Running lamps stay on while braking, the same as on the truck today. The OTMs
  follow the truck's signals as-is.

### 20. Backup input
**Status:** DECIDED

- **What:** backup isn't tapped for now.
- **Plan:** keep backup in the ICM, protocol and code. The ICM reads the backup input as off until
  it's wired.

### 21. Truck off / ICM power
**Status:** OPEN

- **What:** the ICM and the OTMs (through the 12 V trunk) are powered from the orange wire (trailer
  battery charge, C2498C pin 3). The trailer module itself is always powered (C2498A pins 1-2, VBATT),
  so it still flashes its turn outputs for hazards with the key off.
- **Requirement:** trailer hazards must work with the key off. Unlike a normal trailer, our lamps are
  powered from the 12 V trunk, not the lamp wires, so the trunk must be live whenever hazards run.
- **Test first (later):** does the orange wire stay live with the key off?
  - **If it turns off with the key:** the ICM and OTMs lose power, so no key-off hazards.
  - **If it stays live:** hazards work, but parked draw is high: ICM ~15-25 mA plus 16 OTMs at
    ~38 mA ≈ 0.6 A, which drains the battery in a few days. OTMs can't simply sleep, since they must
    keep listening for hazards.
- **Proposed approach (either result): hold relay in the interposer.**
  - Relay contacts switch the 12 V trunk + ICM from a separate fused always-hot battery feed (sized for
    the ~12.5 A trunk design current; not the trailer module's VBATT pins).
  - Coil turned on by the orange wire (key on) OR any lamp output active (hazards), with a hold timer
    of a few minutes after the last signal.
  - Key-off hazards work, and parked draw is near zero.
  - Also gives "new vehicle use" detection for the alert cycle in item 17 (trunk power-up).
- **Fallback for ICM power only:** a truck USB port (the ICM already accepts USB power through its
  diode-OR; most Ford ports switch off with the key). Doesn't solve key-off hazards for the OTMs.
- **Hardware note:** D7 (ICM green "12V_TRM present" LED, R7 6.8 kΩ) draws ~1.6 mA continuously. If
  the ICM ends up on an always-hot feed, switch it from a GPIO or remove it.
- **Decision needed:** after the orange-wire test.

---

## Maintenance

### 22. Firmware updates
**Status:** DECIDED

- **Now:** update over USB-C on both boards.
- **From the start:** use ESP-IDF's two-slot (OTA) flash layout, so wireless updates can be added later
  without re-partitioning boards in the field.
- **Later: wireless updates through the app.**
  1. Phone → ICM over BLE in chunks with resume and checksum (~1 MB, ~20 s-1 min).
  2. ICM → each OTM over ESP-NOW (≤250-byte packets, acknowledged, ~4,000 per OTM). Espressif's
     `esp-now` library has an update component that covers most of this.
  3. Each OTM verifies, switches slot, reboots, and rolls back if the new firmware doesn't start.
  4. Only while parked; check versions after (item 23); optionally signed firmware.

### 23. Firmware version mismatch
**Status:** DECIDED

- **Plan:** packets already carry a protocol version. An OTM receiving a different version doesn't
  guess at the packet's meaning; it reports "update needed" and the app shows it for that OTM.
- **Lamps while mismatched (DECIDED):** hold the last state, same as a lost link (item 11).
- **Alert (DECIDED): critical.** A very annoying alarm so nobody keeps driving with it, plus LED and
  phone notification.
- **Critical alarm behavior (DECIDED):** continuous until fixed. The driver can silence it from the
  button or app, but only for a few minutes; then it comes back, repeating until the firmware matches.
- **Decision for later:** length of the silenced period.

### 24. Diagnostics in the app
**Status:** DECIDED

- **Live view:** for each OTM: online/offline, signal strength, faults per output, feed A/B status,
  supercap voltage, firmware version. Available any time the phone is connected (BLE always on,
  item 3).
- **History log on each OTM (DECIDED): events + status every 10 s.**
  - Events (~16 bytes each): lamp/wiring fault, feed lost/restored, power lost, link lost/restored.
  - Status every 10 s (~12 bytes): feeds, faults, supercap voltage, signal strength.
  - Stored in a ~1-2 MB log partition in the OTM's 8 MB flash, wrapping around when full. At 1 MB:
    about a week of 10 s status plus a long event history. Flash wear is negligible.
  - Written to flash in batches every few seconds; the supercap's energy stays reserved for
    `POWER_LOST`.
  - Timestamps: the phone gives the ICM the real time over BLE; the ICM passes it to the OTMs in the
    light packets.
- **Download:** on request in the app, one OTM at a time: OTM → ICM over ESP-NOW (~4,000 packets per
  MB, ~10-30 s), then ICM → phone over BLE (~20 s-1 min). The app can view it and export as CSV.

### 25. Security
**Status:** DECIDED

- **Goal:** a nearby device can't control the lamps or fake OTM reports.
- **Light packets, ICM → all OTMs (DECIDED): signed broadcast.**
  - ESP-NOW's built-in encryption doesn't work on broadcasts (item 10), so light packets are signed
    instead.
  - During pairing, the ICM gives each OTM a secret key, sent one-to-one with ESP-NOW's built-in
    encryption.
  - Every light packet carries a counter and a short signature (~4-8 bytes) made with the key.
  - OTMs ignore packets with a bad signature or an old counter (blocks fake and replayed packets).
- **OTM → ICM packets (status, `POWER_LOST`, logs):** sent one-to-one, so they use ESP-NOW's built-in
  encryption. ESP-NOW supports up to 17 encrypted peers when configured, enough for 16 OTMs.
- **Decision for later:** key handling when an OTM is removed or re-paired (new key per pairing).

### 26. Radio channel
**Status:** DECIDED

- **Plan (DECIDED):** fixed at channel 1 on both sides (already in the code).
- **Test note:** track dropped packets in testing. If drops are higher than expected, try other
  channels (e.g. 6 and 11) and consider letting the app choose the channel.

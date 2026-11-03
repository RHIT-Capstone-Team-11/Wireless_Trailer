POWER-LOSS HOLD-UP TEST  (sizes the OTM supercap)

Goal: measure the ENERGY the OTM's ESP32 uses from the moment power is cut until the ICM has the
"power lost" message, then size the supercap from that energy.

---------------------------------------------------------------------------------------------
WIRING
---------------------------------------------------------------------------------------------
Bench supply (set ~4.0 V) (+) --> toggle switch --> node A
node A --> 1N4001 diode (anode)    diode cathode = VCAP
    (silicon, NOT Schottky: Schottky leakage can hold the sense line up after the cut)
VCAP --> sender ESP32 3V3 pin (not 5V/VIN: skip the board regulator)
VCAP --> test capacitor (+), capacitor (-) --> GND           (start with 0.05-0.1 F, low ESR)
VCAP --> 100k --> ADC node --> 100k --> GND; 0.1 uF ADC node to GND; ADC node --> sender GPIO6
node A --> 1k --> SENSE --> 4.7k --> GND;  SENSE --> sender GPIO4 AND receiver GPIO4
Supply (-) --> sender GND --> receiver GND (common ground, required)
Receiver ESP32: laptop USB, Serial Monitor 115200.   Sender: NO USB during trials.
Optional scope: CH1 SENSE, CH2 sender GPIO5 (high until the message is ACKed), CH3 VCAP.

Classic ESP32 boards: move VCAP_PIN to 34 (GPIO6 is a flash pin on those).
Dev boards: the USB-serial chip / LEDs on 3V3 add load; a bare module is more accurate.

---------------------------------------------------------------------------------------------
STEP 1  Lowest voltage the sender can still transmit at
---------------------------------------------------------------------------------------------
Set RAMP_TEST = true in BOTH sketches. Supply straight to the sender 3V3 (no diode, no capacitor).
Start at 3.3 V and turn it down ~0.05 V at a time. The receiver prints every packet with its
voltage; the last one before they stop = V_min for this board (transmitting is the worst case).

---------------------------------------------------------------------------------------------
STEP 2  Hold-up trials
---------------------------------------------------------------------------------------------
RAMP_TEST = false in both. Paste the receiver's MAC into the sender. Set C_TEST_F in the
receiver to the MEASURED capacitance. Flip the switch off, wait for the CSV line, switch on.
Do 50+ trials, then repeat at the real distance (truck cab to trailer), through metal.

CSV columns: trial, got_msg, rx_latency_ms (cut -> message received), sender_ack_ms,
attempts, v_detect_mV, v_after_ack_mV, energy_mJ, alive_pkts, last_alive_ms, v_last_mV, rssi

Pick C_TEST so VCAP drops 0.2-0.5 V during the message (ADC is only good to ~20 mV).
Message missing (got_msg = 0)? Use a bigger test cap. Drop < 0.1 V? Use a smaller one.
Use the WORST trial (highest energy_mJ), not the average.

---------------------------------------------------------------------------------------------
STEP 3  Size the real supercap
---------------------------------------------------------------------------------------------
  C >= k * 2 * E / ( eff * (V_full^2 - V_min^2) )

  E      worst energy_mJ / 1000   (joules)
  eff    efficiency of the converter between the supercap and 3.3 V (~0.85 boost)
  V_full supercap charge voltage (e.g. 2.5 V on a 2.7 V cell, derated)
  V_min  lowest supercap voltage the converter still runs from (its datasheet)
  k      margin >= 2-3: capacitance falls in the cold and with age (~30 % end of life),
         plus tolerance

  Example: E = 0.10 J, eff = 0.85, 2.5 V -> 1.0 V, k = 3  =>  C >= 0.13 F

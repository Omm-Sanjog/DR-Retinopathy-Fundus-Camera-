# Wiring and electrical design

| Function | Raspberry Pi 5 (8 GB) pin | Connection |
|---|---|---|
| Camera | CSI/DSI-0 (22-pin FPC) | Camera Module 3 NoIR |
| IR LED string (alignment) | GPIO18 / PWM0 (pin 12) | 220 Ω → gate of Q1 (AO3400), 100 kΩ gate→GND |
| White LED flash (capture) | GPIO19 / PWM1 (pin 35) | 220 Ω → gate of Q2 (AO3400), 100 kΩ gate→GND |
| Capture button | GPIO17 (pin 11) | to GND, 10 kΩ pull-up to 3.3 V (or internal pull-up) |
| Display | DSI-1 or HDMI-0 | 5″ touch display |
| Power | USB-C | 5.1 V / 5 A PD supply or PD power bank |

```
 5V ──┬── 68Ω ──►|── IR850 ──┐        5V ──┬── 100Ω ──►|── WHITE ──┐
      ├── 68Ω ──►|── IR850 ──┤             └── 100Ω ──►|── WHITE ──┤
      ├── 68Ω ──►|── IR850 ──┤                                     │
      └── 68Ω ──►|── IR850 ──┤                                   D │ Q2 AO3400
                           D │ Q1 AO3400        GPIO19 ─220Ω─ G ────┤
          GPIO18 ─220Ω─ G ───┤                         100k │      S │
                   100k │  S │                            GND      GND
                       GND  GND
```

## Calculations

| Quantity | Calculation | Result |
|---|---|---|
| IR LED resistor | (5.0 − 1.5 V) / 50 mA | 70 Ω → **68 Ω** (51.5 mA, 0.18 W → use 0.25 W) |
| White LED resistor | (5.0 − 3.0 V) / 20 mA | **100 Ω** (0.04 W) |
| IR string current | 4 × 51.5 mA | 206 mA |
| MOSFET loss | 0.206² × 0.05 Ω | ≈ 2 mW |
| Gate current | 3.3 V / 220 Ω | 15 mA peak |
| Peak system power | Pi 6.1 + display 1.5 + camera 0.6 + IR 1.0 + flash 0.2 + fan 0.4 | ≈ 9.8 W |
| Runtime | 31 Wh usable / 7 W average | ≈ 4.4 h |

- IR PWM at **20 kHz** to avoid rolling-shutter banding; flash at 100 % duty for ≤ 200 ms.
- SELV only (≤ 5.1 V) — no mains inside the hand-held unit.
- Light exposure must be measured at the eye plane (ISO 15004-2) **before imaging anyone**.

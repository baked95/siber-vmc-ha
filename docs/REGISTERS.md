# Modbus register map — Airios ventilation units (Siber DF EVO and friends)

Holding registers, **literal addressing** (use `41000`, not `1000`/`999`).
The ventilation unit answers on Modbus device id **2** (the id you set as
"Slave UID to bind to"); the bridge itself answers on id **1**.

Verified on: Siber DF EVO 2 with `DFEVORFETH` bridge
(Airios `BRDG-02EM23`, unit identifier `VMD-02RPS78-2`, firmware 0x0712).

## Read-only

| Register | Meaning | Unit | Type | Notes |
|---|---|---|---|---|
| 41000 | Current ventilation speed | — | uint16 | 0 off · 1 low · 2 medium · 3 high · 11-13 timer override · 21 away · 23 boost · 24 auto |
| 41003 | Error code | — | uint16 | 0 = no fault. Cached: first read may fail |
| 41005-41006 | Indoor temperature | °C | float32 | **word-swapped** |
| 41007-41008 | Outdoor temperature | °C | float32 | word-swapped |
| 41009-41010 | Exhaust air temperature | °C | float32 | word-swapped |
| 41011-41012 | Supply air temperature | °C | float32 | word-swapped |
| 41013 | Pre-heater | % | uint16 | 239 (0xEF) = not available |
| 41014 | Filter dirty | — | uint16 | 0 ok · 1 dirty |
| 41015 | Defrosting | — | uint16 | 0/1 |
| 41016 | Bypass position | % | uint16 | 0 closed · 100 open |
| 41017 | Indoor humidity | % | uint16 | 239 = not available on VMD-02RPS78 |
| 41018 | Outdoor humidity | % | uint16 | 239 = not available |
| 41019-41020 | Inlet air flow | m³/h | float32 | word-swapped |
| 41021-41022 | Exhaust air flow | m³/h | float32 | word-swapped |
| 41023 | Air quality | % | uint16 | 239 = not available |
| 41025 | CO2 level | ppm | uint16 | 32767 (0x7FFF) = not available |
| 41026 | Post-heater | % | uint16 | 239 = not available |
| 41027 | Ventilation capability bits | — | uint16 | bit11 auto · bit12 boost · bit13 timer · bit15 off. `61440` = boost+timer+off, **no auto mode** |
| 41040 | Filter time remaining | days | uint16 | Cached: reading it triggers the query; first read may fail |
| 41041 | Filter timer duration | days | uint16 | Cached |
| 41042 | Filter time percentage | % | uint16 | Cached |

## Read / write

| Register | Meaning | Values |
|---|---|---|
| **41500** | Requested system ventilation speed | 0 off · 1 away (absolute min) · 2 low · 3 nominal · 4 high · 5 auto · 7 boost |
| **41550** | Bypass valve mode | 255 auto · 0 closed · 100 open |
| 41501-41503 | Timer override for speed 1/2/3 | minutes (max 18 h) |
| 42000 | Reset filter timer | write 0 |
| 42001-42008 | Supply/exhaust fan % per speed step | % |
| 42009-42010 | Frost protection pre-heater setpoint | °C (-20..50) |
| 42011-42012 | Pre-heater setpoint | °C (-20..50) |
| 42013-42014 | Free ventilation heating setpoint | °C (0..30) |
| 42015-42016 | Free ventilation cooling offset | K (1..10) |

## Gotchas worth knowing

1. **Only one Modbus connection at a time.** If the vendor's "BRDG Modbus
   Tester" tool is connected, Home Assistant reads nothing (entities go
   `unavailable`). Close one before using the other.
2. **`41500` is not readable on all units** — reads return an exception even
   though writes work. Read the actual speed from `41000`.
3. **Floats need word swapping.** In HA: `data_type: float32` + `swap: word`.
   Without it you get values like `-0.00` or absurd magnitudes.
4. **Cached registers** (error code, filter days/percentage) answer on the
   *second* read; the first one triggers the internal query.
5. `239` (0xEF) and `32767` (0x7FFF) are "sensor not available" markers, not
   real measurements. Don't expose those entities if your unit lacks the sensor.

## Registers this package does not use

`pyairios`' `models/vmd_02rps78.py` models this exact unit and mentions a few
more that are worth knowing about:

| Register | Meaning |
|---|---|
| 41001 / 41002 | Exhaust / supply fan speed (%) |
| 41043 / 41044 | Exhaust / supply fan RPM |
| 41050 | Bypass mode |
| 41051 | Bypass status |
| 41024 | Air quality basis |
| 41041 | Filter timer duration (days) |

Source: Siber RS485 gateway manual (register table is shared between the RS485
and Ethernet bridges) plus hands-on probing of a real DF EVO 2 unit.

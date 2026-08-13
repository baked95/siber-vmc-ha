Adds support for the **BRDG-02EM23** Ethernet bridge (sold by Siber as
`DFEVORFETH`), tested end to end against real hardware.

This builds directly on @silverailscolo's `eb-orcon-model` branch — the model
class, the transport-based bridge selection and the `ProductId` entry are their
work. They don't own the hardware, so I completed the three TODOs their branch
left open, with values read from a live bridge. Discussion in #13.

## What was missing, and what the hardware says

**1. The product ID.** The branch had
`BRDG_02EM23 = 0x0001C800  # TODO fill in a verified ID`. My bridge reports
`116808` = **`0x0001C848`** on register `40002` — one below
`BRDG_02R13 = 0x0001C849`. Cross-checked against `PRODUCT_NAME` (`40011`), which
reads `'BRDG-02EM23'`.

**2. The default Modbus device id.** The new model carried the RS485 default of
`207`. The Ethernet bridge answers on id **1**, with the first bound unit on 2.

**3. The serial registers.** The Ethernet model inherited `41998` parity,
`41999` stop bits, `42000` baudrate and `42001` Modbus device id from the RS485
model. The bridge answers `IllegalDataAddress` (exception code 2) for all four,
and because `fetch()` walks every readable register, **their presence made every
fetch fail**:

```
pyairios.exceptions.AiriosReadException: Got an error while reading register 41998
(length 4) from device id 1: ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
```

This PR removes those registers plus the `serial_config()` /
`set_serial_config()` methods that read them, and the imports left unused.

## Test results

Hardware: `BRDG-02EM23` Ethernet bridge + bound `VMD-02RPS78-2`
(Siber DF EVO 2 ducted unit). pyairios on Python 3.13, Modbus TCP on port 502.

```
connect(): True

bridge identity
  product id                   <ProductId.BRDG_02EM23: 116808>
  product name                 'BRDG-02EM23'
  software version             65329
  rf address                   7893700
  bridge class                 BRDG02EM23

nodes()
  modbus id 2: 0x0001C892 (VMD-02RPS78) rf=0x821EC4 ['Siber DF Evo', 'Siber DF Optima 2']

fetch(all_props=False, with_status=False)   → node 1: 60 props, node 2: 52 props
fetch(all_props=True,  with_status=True)    → node 1: 76 props, node 2: 79 props
```

## README

Also updated the *Supported devices* list: the tested unit is a **Siber DF Evo 2**
(the bridge reports the bound node's description as
`['Siber DF Evo', 'Siber DF Optima 2']`, same `VMD-02RPS78` controller), and added
the Ethernet bridge itself — sold by Siber as **DFEVORFETH** — since that is the
piece this PR is about.

One thing I noticed while doing that, and I may well be misreading it: the Orcon
line lists `Airios VMD-02EM23-2`, but `EM23` looks like the bridge family rather
than a unit controller, and the branch's new unit model is `vmd_15rms86.py` /
`ProductId.VMD_15RPS86`. Should that line say `VMD-15RPS86`? I've left it
untouched in case it is intentional. (Tiny related nit: the module is named
`vmd_15rms86.py` — RMS — while the enum says `VMD_15RPS86` — RPS.)

No behaviour change for RS485 users: `BRDG02R13` keeps its own registers and its
`DEFAULT_DEVICE_ID = 207`.

## Notes from the hardware that may be worth follow-up work

Not addressed in this PR, to keep it focused, but happy to send separate patches:

- **Cached registers.** `41003` (error code) and `41040`-`41042` (filter days /
  duration / percentage) fail on the first read after boot and answer on the
  second. A single retry would make them reliable.
- **Write-only register.** `41500` (requested ventilation speed) is not readable
  on `VMD-02RPS78-2`; reads raise. The actual speed is `41000`.
- **"Sensor not fitted" markers.** `239` (0xEF) and `32767` (0x7FFF) are not
  measurements. On my unit that covers indoor/outdoor humidity, air quality, CO2
  and both heaters, so consumers should skip those entities rather than report
  239 %.
- **Capability bits.** `41027` tells you which modes the unit supports — mine
  reports `61440` (boost + timer + off, no auto), so a fixed mode list would
  offer something the unit cannot do.

## Getting the bridge to speak local Modbus TCP at all

Worth documenting somewhere, because it stops most people before they get here:
out of the box this bridge is a Modbus-over-WebSocket *client* towards the vendor
cloud and has **zero open TCP ports**. It only listens on 502 if you pair it
*without* configuring the cloud server URL (factory reset, set outgoing product
type, bind the unit as slave 2, and stop before the "Server URL" step). Also, it
accepts exactly **one** Modbus connection at a time.

I have the hardware here and I'm happy to test any further change.

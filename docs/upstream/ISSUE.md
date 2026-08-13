# Issue draft — pyairios  (ready to post)

**Repo:** https://github.com/scabrero/pyairios/issues/new
**Title:** BRDG-02EM23 (Ethernet bridge): product ID missing and serial-only registers break `fetch()`

---

Hi, and thanks for pyairios and the Home Assistant component — they are the only
serious work out there on these Airios bridges.

I have the **Ethernet** bridge `BRDG-02EM23` (sold by Siber as `DFEVORFETH`)
with a bound `VMD-02RPS78-2` (Siber DF EVO 2). I had been driving it from Home
Assistant with hand-written `modbus:` YAML over TCP, and then discovered that
pyairios already has everything needed: `AiriosTcpTransport` works, `nodes()`
discovers the unit, and my unit is already modelled in `models/vmd_02rps78.py`.

Two small things stop it from working end to end. I have the hardware here and
I am happy to send the PR.

### 1. The Ethernet bridge's product ID is not in the `ProductId` enum

```
product id      FAILED: ValueError: 116808 is not a valid ProductId
product name    'BRDG-02EM23'
```

`116808` is `0x0001C848` — one below `BRDG_02R13 = 0x0001C849`.

### 2. `BRDG02R13`'s serial-only registers make `fetch()` fail

`Airios.__init__` always instantiates `BRDG02R13`, whose register set includes
`41998` parity, `41999` stop bits, `42000` baudrate and `42001` Modbus device
id. The Ethernet bridge answers `IllegalDataAddress` for all of them, so both
`fetch(all_props=False)` and `fetch(all_props=True)` raise:

```
pyairios.exceptions.AiriosReadException: Got an error while reading register 41998
(length 4) from device id 1: ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
```

Related: `DEFAULT_DEVICE_ID = 207` is also wrong for this bridge — mine answers
on Modbus id **1**, with the bound unit on id 2.

### Full probe output

Ethernet bridge at `192.168.72.226:502`, bridge device id 1, pyairios 1.1.0,
Python 3.13 (probe script: https://github.com/baked95/siber-vmc-ha/tools/test_pyairios_tcp.py):

```
== pyairios over TCP → 192.168.72.226:502, bridge device id 1

connect()
  connected: True

bridge identity (registers 40002/40004/40011)
  product id                   FAILED: ValueError: 116808 is not a valid ProductId
  product name                 'BRDG-02EM23'
  software version             65329
  rf address                   7893700

serial-only bridge registers (expected to fail on an Ethernet bridge)
  serial baudrate 42000        FAILED: AiriosReadException: Got an error while reading
                               register 42000 (length 1) from device id 1:
                               ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
  modbus device id 42001       FAILED: AiriosReadException: ... register 42001 ... exception_code=2

nodes()
  modbus id 2: 0x0001C892 (VMD-02RPS78) rf=0x821EC4 ['Siber DF Evo', 'Siber DF Optima 2']

fetch(all_props=False)
  AiriosReadException: ... register 41998 (length 4) ... exception_code=2

fetch(all_props=True)
  AiriosReadException: ... register 41998 (length 1) ... exception_code=2
```

Note `nodes()` works perfectly over TCP — the RF/binding layer is fine, it is
only the bridge's own register set and product ID that are RS485-specific.

### What I would propose

Split the bridge like `models/` already does for units: a shared bridge base
class with the common registers (time, uptime, OEM code, Modbus events, reset,
binding, node addresses), `BRDG02R13` keeping the four serial registers and
`DEFAULT_DEVICE_ID = 207`, and a new `BRDG02EM23` with
`ProductId.BRDG_02EM23 = 0x0001C848` and `DEFAULT_DEVICE_ID = 1`.

For picking the model, which shape would you prefer?

1. Infer from the transport type (TCP → Ethernet bridge, RTU → RS485).
2. An explicit `bridge_product_id=` argument to `Airios`, defaulting to today's
   behaviour.
3. Read register `40002` on connect and select the model from what the bridge
   reports.

I lean towards 3 with 2 as an override, since `PRODUCT_NAME` (`40011`) already
reads correctly even when the ID is unknown, and it gives a clean
`AiriosUnknownProductException` for future bridges instead of a bare
`ValueError`. But it is your library — say which you want and I will send the PR
with tests, and the Home Assistant config-flow side afterwards.

### Other notes from real hardware, in case they are useful

* Getting this bridge to speak local Modbus TCP at all requires pairing it
  **without** a cloud server URL. Out of the box it is a Modbus-over-WebSocket
  *client* to `wss://gw.sibercloud.com` with zero open TCP ports, which is why
  people conclude it cannot do Modbus TCP. What worked (via Siber support):
  factory reset (button 10 s), set outgoing product type, bind the unit as
  slave 2, and stop before the "Server URL" step.
* The bridge accepts exactly **one** Modbus connection at a time. Any vendor
  tool left connected makes everything else read nothing.
* On `VMD-02RPS78-2`, register `41500` (requested ventilation speed) is
  write-only — reads return an exception; the actual speed is `41000`.
* `41003` (error code) and `41040`-`41042` (filter days / duration / percentage)
  behave like cached values: first read after boot fails, second returns the
  value. One retry fixes it.
* `239` (0xEF) and `32767` (0x7FFF) are "sensor not fitted" markers. On my unit
  that is indoor/outdoor humidity, air quality, CO2 and both heaters.
* `41027` capability bits are worth honouring when building mode lists: mine
  reports `61440` = boost + timer + off, i.e. **no auto mode**.
* FWIW my bridge reports software version `65329` (`0xFF31`), which looks like a
  placeholder rather than a version — no idea if that is expected.

My YAML-only workaround plus the verified register notes are here, for anyone
who lands on this issue while looking for a solution today:
https://github.com/baked95/siber-vmc-ha

Thanks again for the work.

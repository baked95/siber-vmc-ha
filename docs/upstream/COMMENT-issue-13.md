I have this exact hardware working, so I can answer the question concretely:
an Ethernet bridge `BRDG-02EM23` (sold by Siber as `DFEVORFETH`) with a bound
`VMD-02RPS78-2` (Siber DF EVO 2). I probed it with pyairios 1.1.0 over
`AiriosTcpTransport`, and the short version is that **very little is missing** —
the transport already works, `nodes()` discovers the unit, and the unit itself is
already modelled in `models/vmd_02rps78.py`.

Two things break it:

**1. The Ethernet bridge's product ID is not in the `ProductId` enum.**

```
product id      FAILED: ValueError: 116808 is not a valid ProductId
product name    'BRDG-02EM23'
```

`116808` is `0x0001C848` — one below `BRDG_02R13 = 0x0001C849`. Note
`PRODUCT_NAME` (`40011`) reads fine even when the ID is unknown.

**2. `BRDG02R13`'s serial-only registers make every `fetch()` fail.**

`Airios.__init__` always instantiates `BRDG02R13`, whose register set includes
`41998` parity, `41999` stop bits, `42000` baudrate and `42001` Modbus device id.
The Ethernet bridge answers `IllegalDataAddress` for all four, so both
`fetch(all_props=False)` and `fetch(all_props=True)` raise:

```
pyairios.exceptions.AiriosReadException: Got an error while reading register 41998
(length 4) from device id 1: ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
```

Related: `DEFAULT_DEVICE_ID = 207` is wrong for this bridge — mine answers on
Modbus id **1**, with the bound unit on id 2.

<details>
<summary>Full probe output (pyairios 1.1.0, Python 3.13, bridge at 192.168.72.226:502)</summary>

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
  serial baudrate 42000        FAILED: AiriosReadException: register 42000, exception_code=2
  modbus device id 42001       FAILED: AiriosReadException: register 42001, exception_code=2

nodes()
  modbus id 2: 0x0001C892 (VMD-02RPS78) rf=0x821EC4 ['Siber DF Evo', 'Siber DF Optima 2']

fetch(all_props=False)
  AiriosReadException: register 41998 (length 4), exception_code=2

fetch(all_props=True)
  AiriosReadException: register 41998 (length 1), exception_code=2
```

Probe script: https://github.com/baked95/siber-vmc-ha/blob/main/tools/test_pyairios_tcp.py

</details>

**So the changes I would expect are:** split the bridge the way `models/`
already does for units — a shared bridge base class with the common registers
(time, uptime, OEM code, Modbus events, reset, binding, node addresses),
`BRDG02R13` keeping the four serial registers and `DEFAULT_DEVICE_ID = 207`, and
a new `BRDG02EM23` with `ProductId.BRDG_02EM23 = 0x0001C848` and
`DEFAULT_DEVICE_ID = 1`. On the HA side, a network branch in the config flow
(host, port 502, bridge Modbus id defaulting to 1).

@scabrero I am happy to send both PRs and I have the hardware here to test.
Before writing anything, how would you like the bridge model to be chosen?

1. Infer it from the transport type (TCP → Ethernet, RTU → RS485).
2. An explicit `bridge_product_id=` argument to `Airios`, defaulting to today's
   behaviour.
3. Read register `40002` on connect and select the model from what the bridge
   reports, raising `AiriosUnknownProductException` for unknown bridges.

I lean towards 3 with 2 as an override, but it is your library — tell me which
you prefer and I will follow it.

---

A few other findings from the hardware that may save whoever picks this up some
time (@silverailscolo, this may be relevant for the Orcon user too):

* Out of the box this bridge does **not** listen on TCP 502 at all: it is a
  Modbus-over-WebSocket *client* towards the vendor cloud
  (`wss://gw.sibercloud.com` in Siber's case), so `nmap` shows zero open ports
  and people conclude Modbus TCP is unsupported. It only listens locally if you
  pair it **without** configuring the server URL. What worked here, per Siber
  support: factory reset (button 10 s), set outgoing product type, bind the unit
  as slave 2, and stop before the "Server URL" step.
* The bridge accepts exactly **one** Modbus connection at a time. Any vendor
  configuration tool left connected makes everything else read nothing.
* On `VMD-02RPS78-2`, register `41500` (requested ventilation speed) is
  write-only: reads return an exception, the actual speed is `41000`.
* `41003` (error code) and `41040`-`41042` (filter days / duration / percentage)
  behave like cached values — the first read after boot fails and the second
  returns the value. One retry is enough.
* `239` (0xEF) and `32767` (0x7FFF) mean "sensor not fitted", not a measurement.
  On my unit that is indoor/outdoor humidity, air quality, CO2 and both heaters.
* `41027` capability bits are worth honouring when building mode lists: mine
  reports `61440` = boost + timer + off, i.e. **no auto mode**.
* My bridge reports software version `65329` (`0xFF31`), which looks more like a
  placeholder than a version.

In the meantime, for anyone landing here who just wants their unit in Home
Assistant today, I published the plain-`modbus:` YAML package I have been using
plus a verified register map and the cloud-free pairing procedure:
https://github.com/baked95/siber-vmc-ha

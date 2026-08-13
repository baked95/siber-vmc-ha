Thanks @silverailscolo — I pulled your `eb-orcon-model` branch and ran it
against my real `BRDG-02EM23` with a bound `VMD-02RPS78-2`. Your structure works
(picking the bridge model from the transport type is exactly right); what is left
is the three things your own TODOs point at. I can fill all of them in from
hardware:

**1. The product ID.** `constants.py` has
`BRDG_02EM23 = 0x0001C800  # TODO fill in a verified ID`. The real value my
bridge reports on register `40002` is **`0x0001C848`** (`116808`) — one below
`BRDG_02R13 = 0x0001C849`. `PRODUCT_NAME` (`40011`) reads `'BRDG-02EM23'`, which
is a handy cross-check.

**2. `DEFAULT_DEVICE_ID`.** `models/brdg_02em23.py` still carries the RS485
default of `207`; my Ethernet bridge answers on Modbus id **1** (bound unit on
2). `Airios.__init__` also defaults to `BRDG02R13_DEFAULT_DEVICE_ID`, so the TCP
path should default to the EM23 value instead.

**3. The serial-only registers.** The new model still declares `41998` parity,
`41999` stop bits, `42000` baudrate and `42001` Modbus device id. The Ethernet
bridge answers `IllegalDataAddress` (exception code 2) for all four, and since
`fetch()` walks every readable register, **that alone makes every fetch fail**:

```
pyairios.exceptions.AiriosReadException: Got an error while reading register 41998
(length 4) from device id 1: ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
```

Dropping those four registers (and the serial-config getters/setters that go
with them) from the Ethernet model is enough — no other RS485 assumption bit me.

### Result with those three fixes applied to your branch

**It works end to end.** Bridge identified as `BRDG02EM23`, node discovery finds
the unit on Modbus id 2, and `fetch()` completes for both nodes — 76 properties
from the bridge and 79 from the ventilation unit, with and without
`all_props`/`with_status`. Nothing else needed patching.

<details>
<summary>Probe output</summary>

```
patch 1/3  ProductId.BRDG_02EM23 -> 0x0001C848
patch 2/3  DEFAULT_DEVICE_ID 207 -> 1
patch 3/3  4 serial-only registers removed from the model

== eb-orcon-model over TCP → 192.168.72.226:502, bridge device id 1

connect(): True

bridge identity
  product id                   <ProductId.BRDG_02EM23: 116808>
  product name                 'BRDG-02EM23'
  software version             65329
  rf address                   7893700
  bridge class                 BRDG02EM23

nodes()
  modbus id 2: 0x0001C892 (VMD-02RPS78) rf=0x821EC4 ['Siber DF Evo', 'Siber DF Optima 2']

fetch({'all_props': False, 'with_status': False})
  node 1: 60 properties
  node 2: 52 properties

fetch({'all_props': True, 'with_status': True})
  node 1: 76 properties
  node 2: 79 properties
```

</details>

Script I used, in case you want to reproduce it on the Orcon:
https://github.com/baked95/siber-vmc-ha/blob/main/tools/test_eb_branch.py
(it pip-installs your branch, applies the three patches and probes).

### Registers you may be missing

From my own probing of the DF EVO (`VMD-02RPS78`), things worth knowing when you
compare with the Orcon:

* `41500` (requested speed) is **write-only** on this unit — reads raise. The
  actual speed is `41000`.
* `41003` (error code) and `41040`-`41042` (filter days / duration / percentage)
  answer only on the **second** read; the first triggers the internal query.
  A single retry makes them reliable.
* `239` (0xEF) and `32767` (0x7FFF) are "sensor not fitted" markers. On mine:
  indoor/outdoor humidity, air quality, CO2 and both heaters.
* `41027` capability bits tell you which modes exist — mine reports `61440`
  (boost + timer + off, **no** auto mode), so a hardcoded mode list would offer
  something the unit cannot do.
* `41550` is the bypass valve mode (255 auto / 0 closed / 100 open).

Full verified map: https://github.com/baked95/siber-vmc-ha/blob/main/docs/REGISTERS.md

Happy to send this as a PR against your branch if you prefer that over
@scabrero merging it directly — whatever gets it upstream fastest. And I can
test any further change on real Ethernet hardware within a day.

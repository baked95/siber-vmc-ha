# PR 1 draft — pyairios: model-aware bridge layer

**Only write this after the maintainer answers the API question in the issue.**
What follows is the version of the change I would send if he picks option 3
(probe the product ID, allow an override). All the facts below are confirmed
against real hardware — see the probe output in `ISSUE.md`.

**Branch:** `ethernet-bridge-support`
**Title:** Select the bridge model from the reported product ID; add BRDG-02EM23

## Description to paste in the PR

Follow-up to #<issue>. The TCP transport already worked; what stopped the
Ethernet bridge (`BRDG-02EM23`, Siber `DFEVORFETH`) from being usable was the
bridge layer:

* `Airios.__init__` hard-codes `BRDG02R13` with `DEFAULT_DEVICE_ID = 207`
* `ProductId` had no entry for the Ethernet bridge
* the RS485 register set includes serial-only registers that do not exist there

This PR introduces a small bridge base class, moves the RS485-specific bits into
`BRDG02R13`, adds `BRDG02EM23`, and selects the model from the product ID read
at connect time (with an explicit override for offline construction). Tested
against real hardware: `BRDG-02EM23` firmware 0x0712 with a bound
`VMD-02RPS78-2`, on Modbus ids 1 and 2.

No behaviour change for existing RS485 users: same class, same default device
id, same registers.

## Shape of the change

**`constants.py`** — new product ID (exact value from the hardware probe):

```python
class ProductId(IntEnum):
    BRDG_02R13 = 0x0001C849
    BRDG_02EM23 = 0x0001C848    # confirmed on real hardware
    ...
```

…plus its `__str__` branch.

**`models/bridge.py`** (new) — everything the two bridges share: time/uptime,
OEM code, Modbus events, reset, binding registers, node addresses, `nodes()`,
`bind_controller()`, `bind_accessory()`, `unbind()`. Essentially today's
`BRDG02R13` minus the serial registers.

**`models/brdg_02r13.py`** — becomes `class BRDG02R13(AiriosBridge)` and only
adds `SERIAL_PARITY 41998`, `SERIAL_STOP_BITS 41999`, `SERIAL_BAUDRATE 42000`,
`MODBUS_DEVICE_ID 42001`. `DEFAULT_DEVICE_ID = 207` stays here.

**`models/brdg_02em23.py`** (new) — `class BRDG02EM23(AiriosBridge)`,
`DEFAULT_DEVICE_ID = 1`, `pr_description() -> ["Airios Ethernet RF Gateway"]`,
plus the Ethernet-specific registers if/when their addresses are confirmed (IP
address and assignment mode, server URL; `MODBUS_EVENTS` is already in the
shared set). Ship it without those first: an otherwise empty subclass is enough
to make the bridge work, since the failure today is purely the four serial
registers plus the missing product ID.

**`__init__.py`** — pick the model instead of hard-coding it:

```python
class Airios:
    def __init__(
        self,
        transport: AiriosBaseTransport,
        device_id: int | None = None,
        bridge_product_id: ProductId | None = None,
    ) -> None:
        ...
        if bridge_product_id is None:
            bridge_product_id = (
                ProductId.BRDG_02EM23
                if isinstance(transport, AiriosTcpTransport)
                else ProductId.BRDG_02R13
            )
        if device_id is None:
            device_id = DEFAULT_DEVICE_IDS[bridge_product_id]
        self.bridge = bridge_factory(bridge_product_id, device_id, self._client)
```

and in `connect()`, after the Modbus link is up, read `40002` and, if it
disagrees with the assumption, rebuild `self.bridge` with the right model and
log it at info level. Raise a clear `AiriosUnknownProductException` naming the
value for bridges we do not model yet, instead of a bare `ValueError`.

## Robustness fixes worth folding in (all seen on real hardware)

* **Retry cached registers once.** `41003`, `41040`, `41041`, `41042` fail on
  the first read and answer on the second. Currently that surfaces as a read
  exception on startup.
* **Do not treat write-only registers as readable.** `41500` on
  `VMD-02RPS78-2` returns an exception on read; the value to display is `41000`.
* **Treat `239` / `32767` as "not available"** rather than a measurement, so
  units without humidity/CO2/heater sensors do not report 239 %.
* **Expose `41027` capability bits** so consumers can build the real list of
  supported modes (mine: `61440`, i.e. no auto mode).

## Tests

* Unit tests for `bridge_factory` / product-ID selection and for the
  `DEFAULT_DEVICE_IDS` mapping.
* A mocked-client test that a `BRDG02EM23` instance exposes no serial registers
  and a `BRDG02R13` still does — i.e. that `fetch()` no longer touches
  `41998`-`42001` on the Ethernet bridge.
* Manual test log from the real Ethernet bridge attached to the PR
  (`nodes()` discovery + full `fetch()`).

# Siber DF EVO → Home Assistant (local Modbus TCP)

Full local control of a **Siber DF EVO** heat-recovery ventilation unit from
Home Assistant, through the **Airios `BRDG-02EM23` Ethernet bridge**
(sold by Siber as `DFEVORFETH`) — **no cloud, no vendor app**.

Drop one YAML package in, change one IP, restart. Everything below is verified
against real hardware, not copied from a datasheet.

| | |
|---|---|
| Unit | Siber DF EVO 2 (`VMD-02RPS78-2`) |
| Bridge | Airios `BRDG-02EM23` / Siber `DFEVORFETH`, firmware 0x0712 |
| Transport | Modbus TCP, port 502, device id 2 |
| Home Assistant | 2024.8+ (uses the built-in `modbus` integration) |

## What you get

**Sensors** — indoor / outdoor / supply / exhaust temperature, inlet and exhaust
air flow (m³/h), bypass position, current speed (as text), heat-recovery
efficiency (%), filter status + days remaining, error code, defrost status.

**Control** — speed selector (Off · Away · Low · Nominal · High · Boost),
bypass mode (Auto · Closed · Open), a timed manual boost script that restores
the previous speed when it finishes, and a filter-timer reset script.

**Automations** — writes to the unit when a selector changes, dirty-filter
alert, error-code alert. Optional smarter ones (cooking boost, away mode,
summer night free-cooling, quiet night) are in [`docs/EXAMPLES.md`](docs/EXAMPLES.md).

## Install

1. **Put the bridge in local Modbus mode.** Out of the box it only speaks
   Modbus-over-WebSocket to the vendor cloud and has *no open TCP ports*.
   Follow [`docs/BRIDGE_SETUP.md`](docs/BRIDGE_SETUP.md) — factory reset, then
   pair *without* configuring the cloud server URL.
2. Enable packages in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Copy [`packages/siber_vmc.yaml`](packages/siber_vmc.yaml) into
   `config/packages/` and replace `BRIDGE_IP` with your bridge's address
   (give it a static lease first).
4. Restart Home Assistant. You should see `sensor.vmc_*` entities with values.
5. Turn on `input_boolean.vmc_auto` if you want the automations to act.

## Five things that will cost you an evening if nobody tells you

1. **The bridge accepts exactly one Modbus connection.** If the vendor's
   *BRDG Modbus Tester* is open on your PC, Home Assistant reads nothing.
2. **Register addressing is literal** — `41000` means `41000`, no 40001 offset.
3. **Floats are word-swapped.** `data_type: float32` + `swap: word`, always.
4. **`41500` (requested speed) is write-only** on this unit. Read the actual
   speed from `41000`.
5. **`239` / `32767` mean "sensor not fitted"**, not a measurement. On the
   DF EVO 2 that is humidity, air quality, CO2 and the pre/post-heaters.

Full register table and more notes: [`docs/REGISTERS.md`](docs/REGISTERS.md).

## Related work

There is a proper custom component for Airios bridges by @scabrero:
[`homeassistant-airios-component`](https://github.com/scabrero/homeassistant-airios-component)
+ [`pyairios`](https://github.com/scabrero/pyairios). If you have the **RS485**
bridge (`BRDG-02R13`), use that instead of this repo — it gives you real devices,
binding and proper entities.

For the **Ethernet** bridge, as of mid-2026: `pyairios` already ships a TCP
transport (`AiriosTcpTransport`), but its bridge layer is hard-coded to the RS485
model (`BRDG02R13`, default Modbus id 207) and its `ProductId` enum has no entry
for `BRDG-02EM23`. Making it model-aware looks like a small change, and the unit
itself (`VMD-02RPS78`) is already fully modelled there. That work — probe script,
issue draft and PR drafts — lives in [`docs/upstream/`](docs/upstream/README.md).
Until it lands, the YAML package here works today.

## Compatibility

The register map is shared across Airios `VMD-02RPS78` based units, so other
Siber DF EVO variants and rebadged models (Vasco, Brink, Orcon and others using
Airios RF modules) are likely to work. If you try one, please open an issue with
your model and what did or didn't work.

## Licence & credits

MIT — see [`LICENSE`](LICENSE). Built by **Sergio Baquedano** while integrating
his own unit; register map from the Siber RS485 gateway manual, cloud-free
pairing procedure from Siber technical support, and everything else from
probing the hardware until it answered.

*Not affiliated with Siber or Airios. Use at your own risk: writing Modbus
registers can change how your ventilation unit runs.*

# PR 2 draft — homeassistant-airios-component: Ethernet bridge in the config flow

Depends on PR 1 being released in pyairios. I could not read the component's
current `config_flow.py` while writing this, so **check first** whether it
already offers a network option — if it does, this PR may shrink to little more
than defaults and documentation.

**Title:** Add Ethernet bridge (Modbus TCP) support to the config flow

## Description to paste in the PR

Adds setup over Modbus TCP for the `BRDG-02EM23` Ethernet bridge, using the
bridge-model selection added in pyairios <version>. Tested on real hardware:
`BRDG-02EM23` + `VMD-02RPS78-2` (Siber DF EVO 2), bridge on Modbus id 1, unit
on id 2. Serial setup is untouched.

## Shape of the change

* **First step:** menu — *Serial (RS485)* / *Network (Modbus TCP)*.
* **Network step:** `host` (required), `port` (default `502`), `device_id`
  (default `1`, the Ethernet bridge default; the RS485 default of 207 is wrong
  here). Validate by connecting and reading the bridge product ID; abort with a
  clear message if the value is not a bridge we model.
* **Unique ID:** the bridge RF address / serial, not the host, so a DHCP change
  does not create a duplicate entry.
* **Config entry data:** store `transport: "tcp"` alongside host/port/device id,
  and branch on it when building the `Airios` instance in `__init__.py`.
* **Reconfigure / options:** allow changing the host, for people who move the
  bridge to a new IP.
* **Errors:** map connection failures to `cannot_connect` and add a note about
  the single-connection limit — it is by far the most likely support question:
  *"the bridge accepts only one Modbus connection at a time; close any vendor
  configuration tool before setting this up."*

## Docs to add to the README

* Ethernet bridge must be paired **without** a cloud server URL, otherwise it
  never listens on TCP 502 (link to `BRIDGE_SETUP.md` or inline the procedure).
* Default Modbus ids: bridge 1, first bound unit 2.
* One Modbus connection at a time.
* Model names people search for: `BRDG-02EM23`, Siber `DFEVORFETH`, Siber DF EVO.

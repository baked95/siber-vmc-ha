# Upstream contribution — working folder

Goal: make @scabrero's Airios stack work with the **Ethernet** bridge
(`BRDG-02EM23`, sold by Siber as `DFEVORFETH`), so Ethernet owners get a proper
integration with device discovery, binding and entities instead of hand-written
Modbus YAML.

## What the source code actually says (pyairios 1.1.0, checked)

| Claim | Reality |
|---|---|
| "The library only supports the RS485 model" (repo READMEs) | Outdated. `pyairios.client` already defines `AiriosTcpTransport(host, port)` and `AsyncAiriosModbusTcpClient`, and `Airios.__init__` dispatches on the transport type. |
| Bridge model | Hard-coded: `Airios.__init__` always builds `BRDG02R13(device_id, client)`, default `device_id=207`. Our Ethernet bridge answers on id **1**. |
| Product IDs | `ProductId` enum knows `BRDG_02R13 = 0x0001C849`, `VMD_02RPS78 = 0x0001C892`, `VMN_05LM02`, `VMN_02LM11`, `VMD_07RPS13`. **No entry for `BRDG_02EM23 = 0x0001C848`** (confirmed by probing), so `ProductId(value)` raises `ValueError`. |
| Bridge registers | `BRDG02R13` registers include serial-only ones: `41998` parity, `41999` stop bits, `42000` baudrate, `42001` Modbus device id. The Ethernet bridge answers `IllegalDataAddress` for all four, so **every `fetch()` raises** (confirmed). |
| The unit itself | Fully modelled in `models/vmd_02rps78.py` — that is exactly the Siber DF EVO unit (`VMD-02RPS78-2`), including registers we hadn't found by hand (`41043/41044` fan RPM, `41050/41051` bypass mode and status). |

So the contribution is **not** "add TCP" — it is "make the bridge layer
model-aware so the Ethernet bridge is recognised", plus a docs fix.

## Order of work

1. ~~Run `tools/test_pyairios_tcp.py`~~ **done**, results in `ISSUE.md`:
   the Ethernet bridge reports product ID **`0x0001C848`** (`116808`, one below
   the RS485 bridge) and name `BRDG-02EM23`; `nodes()` discovers the unit
   correctly on Modbus id 2; `fetch()` fails only on the RS485-specific
   registers `41998`-`42001`.
2. **There is already an open issue for this**: scabrero/pyairios#13
   ("TCP support", opened 2026-03-29 by @silverailscolo, unanswered) asks
   literally "what extra changes would be required?" — with a user who has a
   `BRDG-02EM23` but apparently cannot test it. So the move is to *answer there*,
   not to open a duplicate: post `COMMENT-issue-13.md`.
   `ISSUE.md` is kept only as a fallback in case #13 gets closed as stale.
3. Wait for the maintainer's preference on API shape before coding (`PR1.md`
   proposes one, but it is his call).
4. `PR1.md` → pyairios. `PR2.md` → the HA component.

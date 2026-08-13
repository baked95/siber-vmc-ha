# Putting the Airios/Siber Ethernet bridge in local Modbus TCP mode

Out of the box the `DFEVORFETH` bridge (Airios `BRDG-02EM23`) talks to the
vendor cloud over **Modbus-over-WebSocket** and does **not** listen on TCP 502.
`nmap` shows zero open ports. To use it locally you must pair it *without*
configuring the cloud server.

> Trade-off: with the cloud URL removed, the vendor mobile app stops working.
> The bridge accepts a single connection anyway, so it is one or the other.

## What you need

* The vendor's `BRDG Modbus Tester` Windows tool (ask your installer/support).
* A **data-capable** micro-USB cable (the one shipped for power usually is not).
* The password printed on / encoded in the bridge QR code (only if you ever
  want to go back to cloud mode).

## Procedure (factory reset + pair, no cloud)

1. Hold the bridge button ~10 s → factory reset.
2. Connect the bridge to the PC by USB and open `BRDG Modbus Tester`.
3. In *Product Type*, set `RAW hex` = `0001C892` and press **Set**.
4. *Initiate binding type* → `3 - Outgoing ProductType`.
5. *Slave UID to bind to* → `2`  (this becomes the Modbus id of your unit).
6. Power-cycle the ventilation unit.
7. Press **Bind** and wait for `Binding successful`.
8. **STOP HERE.** Do *not* fill in *Server URL* and do *not* set
   *Modbus events* to 3 — that is what pushes the bridge into cloud mode.
9. Optional but recommended, static IP: write the address in *IP address* and
   set *IP address assignment* = `2` (press Enter after each field).
10. Disconnect the tool, plug the bridge into Ethernet. All three LEDs should
    light up with no PC attached.

## Verify

```bash
nmap -Pn -p 502 --open <BRIDGE_IP>     # expect: 502/tcp open  mbap
```

A quick read of the current speed (device id 2, register 41000) should return
a sensible value (0-3, 11-13, 21, 23 or 24):

```python
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient("<BRIDGE_IP>", port=502, timeout=5)
c.connect()
print(c.read_holding_registers(address=41000, count=1, device_id=2).registers)
```

(On pymodbus 3.x the keyword is `device_id`; older versions use `slave`.)

## Troubleshooting

| Symptom | Cause |
|---|---|
| No open ports at all | Bridge still in cloud mode → redo the pairing without step 8 |
| Entities `unavailable` in HA | The Windows tester is holding the only allowed connection |
| Connecting by IP in the tester fails | Normal in cloud mode: the bridge is a WebSocket *client*, it does not listen |
| Values like `-0.00` or huge numbers | Missing `swap: word` on float32 registers |

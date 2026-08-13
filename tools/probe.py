#!/usr/bin/env python3
"""Probe an Airios/Siber bridge over Modbus TCP and dump the known registers.

    pip install pymodbus
    python3 probe.py 192.168.1.50

Reads twice where needed (some registers are cached and fail the first time).
Remember: the bridge allows only ONE Modbus connection — close the vendor's
BRDG Modbus Tester and stop Home Assistant's modbus hub before running this.
"""
import struct
import sys

from pymodbus.client import ModbusTcpClient

UNIT = 2  # ventilation unit; the bridge itself is 1

U16 = [
    (41000, "current speed", "0 off/1 low/2 med/3 high/11-13 timer/21 away/23 boost/24 auto"),
    (41003, "error code", "0 = ok"),
    (41013, "pre-heater %", "239 = n/a"),
    (41014, "filter dirty", "0/1"),
    (41015, "defrosting", "0/1"),
    (41016, "bypass position %", ""),
    (41017, "indoor humidity %", "239 = n/a"),
    (41018, "outdoor humidity %", "239 = n/a"),
    (41023, "air quality %", "239 = n/a"),
    (41025, "CO2 ppm", "32767 = n/a"),
    (41026, "post-heater %", "239 = n/a"),
    (41027, "capability bits", "61440 = boost+timer+off"),
    (41040, "filter days remaining", "cached"),
    (41041, "filter timer days", "cached"),
    (41042, "filter percentage", "cached"),
]
F32 = [
    (41005, "indoor temperature", "°C"),
    (41007, "outdoor temperature", "°C"),
    (41009, "exhaust temperature", "°C"),
    (41011, "supply temperature", "°C"),
    (41019, "inlet flow", "m³/h"),
    (41021, "exhaust flow", "m³/h"),
]


def read(client, address, count):
    for _ in range(2):  # cached registers answer on the second try
        r = client.read_holding_registers(address=address, count=count, device_id=UNIT)
        if not r.isError():
            return r.registers
    return None


def main(host):
    client = ModbusTcpClient(host, port=502, timeout=5)
    if not client.connect():
        sys.exit(f"cannot connect to {host}:502 — is the bridge in cloud mode?")
    print(f"{'reg':>6}  {'value':>10}  name")
    for addr, name, note in U16:
        regs = read(client, addr, 1)
        val = "ERR" if regs is None else regs[0]
        print(f"{addr:>6}  {val:>10}  {name}" + (f"   ({note})" if note else ""))
    for addr, name, unit in F32:
        regs = read(client, addr, 2)
        if regs is None:
            val = "ERR"
        else:  # float32 with swapped words
            val = round(struct.unpack(">f", struct.pack(">HH", regs[1], regs[0]))[0], 2)
        print(f"{addr:>6}  {val:>10}  {name} [{unit}]")
    client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

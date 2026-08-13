#!/usr/bin/env python3
"""Probe an Airios Ethernet bridge (BRDG-02EM23) with pyairios over Modbus TCP.

pyairios already ships a TCP transport (AiriosTcpTransport, since 1.0.x), but its
bridge layer assumes the RS485 model BRDG-02R13. This script collects the facts
needed to report/fix Ethernet-bridge support upstream:

  * what product ID and product name the Ethernet bridge reports
  * whether node enumeration works (bound units and their Modbus ids)
  * whether a full fetch() of bridge + unit succeeds, and what fails if not

Requires Python 3.13 (pyairios 1.1.0). Easiest way, no host pollution:

    docker run --rm -it --network host python:3.13-slim sh -c \
      "pip -q install pyairios && python - <BRIDGE_IP> [BRIDGE_MODBUS_ID]" \
      < test_pyairios_tcp.py

Remember the bridge accepts ONE Modbus connection at a time: stop Home
Assistant's modbus hub (or the vendor tester) before running this.
"""

from __future__ import annotations

import asyncio
import sys
import traceback

from pyairios import Airios, AiriosTcpTransport
from pyairios.properties import AiriosBridgeProperty as bp
from pyairios.properties import AiriosDeviceProperty as dp


def show(label, result):
    value = getattr(result, "value", result)
    print(f"  {label:<28} {value!r}")


async def main(host: str, bridge_id: int) -> None:
    print(f"== pyairios over TCP → {host}:502, bridge device id {bridge_id}\n")
    api = Airios(AiriosTcpTransport(host=host, port=502), device_id=bridge_id)

    print("connect()")
    print(f"  connected: {await api.connect()}\n")

    print("bridge identity (registers 40002/40004/40011)")
    for label, coro in (
        ("product id", api.bridge.device_product_id()),
        ("product name", api.bridge.device_product_name()),
        ("software version", api.bridge.device_software_version()),
        ("rf address", api.bridge.device_rf_address()),
    ):
        try:
            show(label, await coro)
        except Exception as err:  # noqa: BLE001 - we want the failure text verbatim
            print(f"  {label:<28} FAILED: {type(err).__name__}: {err}")
    print()

    print("serial-only bridge registers (expected to fail on an Ethernet bridge)")
    for label, prop in (
        ("serial baudrate 42000", bp.SERIAL_BAUDRATE),
        ("modbus device id 42001", bp.MODBUS_DEVICE_ID),
    ):
        try:
            show(label, await api.bridge.get(prop))
        except Exception as err:  # noqa: BLE001
            print(f"  {label:<28} FAILED: {type(err).__name__}: {err}")
    print()

    print("nodes()")
    try:
        nodes = await api.nodes()
        for node in nodes:
            print(f"  modbus id {node.modbus_address}: {node.product_id} "
                  f"rf=0x{node.rf_address:06X} {node.description}")
        if not nodes:
            print("  (none reported)")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    print()

    print("fetch(all_props=False)")
    try:
        data = await api.fetch(all_props=False, with_status=False)
        for key, dev in data.nodes.items():
            props = getattr(dev, "__dict__", dev)
            print(f"  node {key}: {len(props)} properties")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    print()

    print("fetch(all_props=True)")
    try:
        data = await api.fetch(all_props=True, with_status=True)
        print(f"  ok, {len(data.nodes)} nodes")
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    api.close()
    print("\ndone — paste this output into the upstream issue")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1))

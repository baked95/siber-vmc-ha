#!/usr/bin/env python3
"""Test silverailscolo's `eb-orcon-model` pyairios branch against a real
BRDG-02EM23 Ethernet bridge, applying the three fixes its TODOs ask for.

The branch adds `models/brdg_02em23.py` and picks the bridge model from the
transport type, but it is still a copy of the RS485 model:

  1. ProductId.BRDG_02EM23 = 0x0001C800   # "TODO fill in a verified ID"
     → real value, read from hardware: 0x0001C848
  2. DEFAULT_DEVICE_ID = 207 (RS485 default); the Ethernet bridge answers on 1
  3. it keeps the serial-only registers 41998-42001 (parity / stop bits /
     baudrate / Modbus device id), which the Ethernet bridge rejects with
     IllegalDataAddress — that alone makes every fetch() fail

This script patches those three points in the installed package, then probes.
Run it with the branch installed, Python 3.13:

    docker run --rm -i --network host python:3.13-slim sh -c \
      'pip -q install "pyairios @ git+https://github.com/silverailscolo/pyairios@eb-orcon-model" \
       && python - 192.168.72.226 1' < test_eb_branch.py

The bridge accepts ONE Modbus connection at a time: stop Home Assistant's
modbus hub (or the vendor tester) first.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
import traceback

VERIFIED_PRODUCT_ID = "0x0001C848"


def patch_package() -> pathlib.Path:
    """Apply the three fixes to the installed pyairios, before importing it."""
    import importlib.util

    spec = importlib.util.find_spec("pyairios")
    if spec is None or not spec.origin:
        sys.exit("pyairios is not installed")
    pkg = pathlib.Path(spec.origin).parent

    consts = pkg / "constants.py"
    text = consts.read_text()
    if "0x0001C800" in text:
        text = text.replace(
            "BRDG_02EM23 = 0x0001C800  # TODO fill in a verified ID",
            f"BRDG_02EM23 = {VERIFIED_PRODUCT_ID}  # verified on real hardware",
        ).replace("BRDG_02EM23 = 0x0001C800", f"BRDG_02EM23 = {VERIFIED_PRODUCT_ID}")
        consts.write_text(text)
        print(f"patch 1/3  ProductId.BRDG_02EM23 -> {VERIFIED_PRODUCT_ID}")
    else:
        print("patch 1/3  product ID already set")

    model = pkg / "models" / "brdg_02em23.py"
    text = model.read_text()
    changed = False

    if "DEFAULT_DEVICE_ID = 207" in text:
        text = text.replace("DEFAULT_DEVICE_ID = 207", "DEFAULT_DEVICE_ID = 1")
        changed = True
        print("patch 2/3  DEFAULT_DEVICE_ID 207 -> 1")

    dropped = 0
    keep = []
    for line in text.splitlines(keepends=True):
        if any(f"bp.{name}" in line and "Register(" in line
               for name in ("SERIAL_PARITY", "SERIAL_STOP_BITS",
                            "SERIAL_BAUDRATE", "MODBUS_DEVICE_ID")):
            dropped += 1
            continue
        keep.append(line)
    if dropped:
        text = "".join(keep)
        changed = True
        print(f"patch 3/3  {dropped} serial-only registers removed from the model")

    if changed:
        model.write_text(text)
    return pkg


def show(label, result):
    print(f"  {label:<28} {getattr(result, 'value', result)!r}")


async def probe(host: str, bridge_id: int) -> None:
    from pyairios import Airios, AiriosTcpTransport

    print(f"\n== eb-orcon-model over TCP → {host}:502, bridge device id {bridge_id}\n")
    api = Airios(AiriosTcpTransport(host=host, port=502), device_id=bridge_id)
    print(f"connect(): {await api.connect()}\n")

    print("bridge identity")
    for label, coro in (
        ("product id", api.bridge.device_product_id()),
        ("product name", api.bridge.device_product_name()),
        ("software version", api.bridge.device_software_version()),
        ("rf address", api.bridge.device_rf_address()),
    ):
        try:
            show(label, await coro)
        except Exception as err:  # noqa: BLE001
            print(f"  {label:<28} FAILED: {type(err).__name__}: {err}")
    print(f"  {'bridge class':<28} {type(api.bridge).__name__}")
    print()

    print("nodes()")
    try:
        for node in await api.nodes():
            print(f"  modbus id {node.modbus_address}: {node.product_id} "
                  f"rf=0x{node.rf_address:06X} {node.description}")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    print()

    for kwargs in ({"all_props": False, "with_status": False},
                   {"all_props": True, "with_status": True}):
        print(f"fetch({kwargs})")
        try:
            data = await api.fetch(**kwargs)
            for key, dev in data.nodes.items():
                props = dict(getattr(dev, "data", None) or dev)
                print(f"  node {key}: {len(props)} properties")
                if key != bridge_id:
                    for name, value in list(props.items())[:12]:
                        print(f"      {name} = {getattr(value, 'value', value)!r}")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        print()

    api.close()
    print("done — paste this into scabrero/pyairios#13")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    patch_package()
    asyncio.run(probe(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1))

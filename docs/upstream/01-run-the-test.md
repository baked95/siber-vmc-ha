# Step 1 — get the facts from the real bridge

pyairios 1.1.0 needs Python 3.13; Ubuntu 24.04 ships 3.12, so run it in a
throwaway container with host networking. **Stop Home Assistant's Modbus hub
first** — the bridge only accepts one Modbus connection at a time.

```bash
# on the machine that can reach the bridge
cd /path/to/siber-vmc-ha/tools

# 1) free the bridge: stop HA (or comment out the modbus hub and restart)
docker stop homeassistant

# 2) probe with pyairios over TCP (bridge Modbus id = 1)
docker run --rm -i --network host python:3.13-slim sh -c \
  'pip -q install pyairios && python - 192.168.72.226 1' < test_pyairios_tcp.py \
  | tee pyairios-tcp-report.txt

# 3) bring HA back
docker start homeassistant
```

## What each result means

* **Bridge product ID reads fine and is a known value** → nothing to add to the
  enum; the only real problem is the hard-coded `device_id=207` default and the
  serial registers. Small PR.
* **`ValueError: Unknown product ID value 0001Cxxx`** → we have found the
  Ethernet bridge's product ID. That value is the missing piece: it needs an
  enum entry plus a `models/brdg_02em23.py` model. Report the exact number.
* **`nodes()` lists `modbus id 2: 0x0001C892 (VMD-02RPS78)`** → excellent news:
  discovery works over TCP and the whole entity layer should follow.
* **Serial registers fail** → expected, and the argument for splitting the
  bridge model. Copy the exact exception text into the issue.
* **`fetch(all_props=True)` raises but `all_props=False` works** → say so; it
  tells the maintainer the failure is in the optional property set, not in the
  transport.

Keep `pyairios-tcp-report.txt`; it is the evidence the issue is built on.

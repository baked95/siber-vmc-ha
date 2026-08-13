#!/bin/bash
# Prepara el PR a scabrero/pyairios con soporte para la pasarela Ethernet
# BRDG-02EM23, partiendo de la rama eb-orcon-model de silverailscolo y aplicando
# los tres arreglos verificados en hardware real.
#
# Uso:  ./preparar-pr-pyairios.sh <tu-usuario-github>
# Requiere: gh autenticado (gh auth login) y git.
#
# NO abre el PR: deja la rama subida y te imprime el comando final para que
# revises el diff antes de enviarlo.
set -eu

USER="${1:?falta tu usuario de GitHub}"
WORK="${HOME}/proyectos/pyairios-pr"
BRANCH="brdg-02em23-ethernet-bridge"

command -v gh >/dev/null || { echo "Falta gh (brew install gh)"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Ejecuta primero: gh auth login"; exit 1; }

echo ">> 1) Fork y clon"
mkdir -p "$(dirname "$WORK")"
if [ ! -d "$WORK/.git" ]; then
  gh repo fork scabrero/pyairios --clone=false --remote=false >/dev/null 2>&1 || true
  git clone "https://github.com/$USER/pyairios.git" "$WORK"
fi
cd "$WORK"
git remote get-url upstream >/dev/null 2>&1 || \
  git remote add upstream https://github.com/scabrero/pyairios.git
git remote get-url eb >/dev/null 2>&1 || \
  git remote add eb https://github.com/silverailscolo/pyairios.git
git fetch --all --quiet

echo ">> 2) Rama a partir del trabajo de silverailscolo"
git checkout -B "$BRANCH" eb/eb-orcon-model

echo ">> 3) Aplicando los tres arreglos verificados en hardware"
python3 - <<'PY'
import pathlib, re, sys

root = pathlib.Path("src/pyairios")
changes = []

# --- 1) product ID real de la pasarela Ethernet -----------------------------
consts = root / "constants.py"
t = consts.read_text()
if "0x0001C800" in t:
    t = re.sub(r"BRDG_02EM23 = 0x0001C800[^\n]*",
               "BRDG_02EM23 = 0x0001C848", t)
    consts.write_text(t)
    changes.append("constants.py: BRDG_02EM23 = 0x0001C848")

# --- 2) y 3) modelo de la pasarela Ethernet ---------------------------------
model = root / "models" / "brdg_02em23.py"
t = model.read_text()

if "DEFAULT_DEVICE_ID = 207" in t:
    t = t.replace("DEFAULT_DEVICE_ID = 207", "DEFAULT_DEVICE_ID = 1")
    changes.append("brdg_02em23.py: DEFAULT_DEVICE_ID = 1")

# registros de puerto serie: no existen en la pasarela Ethernet
lines, dropped = [], 0
for line in t.splitlines(keepends=True):
    if "Register(" in line and any(f"bp.{n}" in line for n in
            ("SERIAL_PARITY", "SERIAL_STOP_BITS", "SERIAL_BAUDRATE", "MODBUS_DEVICE_ID")):
        dropped += 1
        continue
    lines.append(line)
t = "".join(lines)
if dropped:
    changes.append(f"brdg_02em23.py: {dropped} registros de serie eliminados")

# métodos que leen/escriben esos registros
m = re.search(r"\n    async def serial_config\(.*?(?=\n    async def modbus_events\()",
              t, re.S)
if m:
    t = t[:m.start()] + "\n" + t[m.end():]
    changes.append("brdg_02em23.py: serial_config()/set_serial_config() eliminados")

# imports que quedan sin uso
for name in ("Baudrate", "Parity", "SerialConfig", "StopBits"):
    if len(re.findall(rf"\b{name}\b", t)) == 1:   # solo el import
        t = re.sub(rf"\n\s+{name},", "", t, count=1)
        changes.append(f"brdg_02em23.py: import {name} eliminado")

model.write_text(t)

if not changes:
    sys.exit("No se ha cambiado nada: ¿ya estaba parcheado?")
for c in changes:
    print(f"   · {c}")
PY

echo
echo ">> 4) Comprobación rápida de sintaxis"
python3 -m compileall -q src/pyairios >/dev/null && echo "   compila"
grep -n "SERIAL_\|MODBUS_DEVICE_ID" src/pyairios/models/brdg_02em23.py && \
  echo "   ATENCION: quedan referencias a registros de serie" || \
  echo "   sin referencias a registros de serie"

echo
echo ">> 5) Commit"
git add -A
git commit -q -m "Add BRDG-02EM23 Ethernet bridge support

Builds on silverailscolo's eb-orcon-model branch, completing its three TODOs
with values verified against real hardware (BRDG-02EM23 + VMD-02RPS78-2):

- ProductId.BRDG_02EM23 is 0x0001C848 (the bridge reports 116808 on register
  40002; its PRODUCT_NAME reads 'BRDG-02EM23')
- DEFAULT_DEVICE_ID is 1 for the Ethernet bridge, not the RS485 default of 207
- the Ethernet bridge has no serial port: registers 41998-42001 answer
  IllegalDataAddress and, since fetch() walks every readable register, their
  presence made every fetch() fail

Tested end to end: bridge identified, nodes() discovers the bound unit on
Modbus id 2, and fetch() returns 76 properties for the bridge and 79 for the
ventilation unit, with and without all_props/with_status.

Co-authored-by: silverailscolo <silverailscolo@users.noreply.github.com>"

echo ">> 6) Subiendo la rama"
git push -u origin "$BRANCH" --force-with-lease

cat <<EOF

Rama subida: https://github.com/$USER/pyairios/tree/$BRANCH

REVISA EL DIFF ANTES DE ABRIR EL PR:
  cd $WORK && git diff upstream/main...$BRANCH

Y cuando estés conforme:
  gh pr create --repo scabrero/pyairios \\
    --base main --head $USER:$BRANCH \\
    --title "Add BRDG-02EM23 Ethernet bridge support (tested on real hardware)" \\
    --body-file ~/ha-audit/siber-vmc-ha/docs/upstream/PR-pyairios-body.md --web
EOF

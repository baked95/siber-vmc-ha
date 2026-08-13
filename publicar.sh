#!/bin/bash
# Publica este repo en GitHub y prepara el issue de upstream.
# Uso:  ./publicar.sh <tu-usuario-github> [nombre-repo]
# Requiere: gh (brew install gh) y haber hecho 'gh auth login' una vez.
set -eu

USER="${1:?falta tu usuario de GitHub}"
REPO="${2:-siber-vmc-ha}"
URL="https://github.com/$USER/$REPO"

command -v gh >/dev/null || { echo "Falta gh. Instala: brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Falta login. Ejecuta: gh auth login"; exit 1; }

echo ">> 1) Sustituyendo el placeholder de URL por $URL"
grep -rl '<<< REPO URL >>>' . --include='*.md' | while read -r f; do
  python3 - "$f" "$URL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace('<<< REPO URL >>>', sys.argv[2]))
PY
  echo "   $f"
done

echo ">> 2) Generando el cuerpo limpio del issue (docs/upstream/ISSUE-body.md)"
python3 - <<'PY'
import pathlib
src = pathlib.Path('docs/upstream/ISSUE.md').read_text()
body = src.split('\n---\n', 1)[1].strip() + '\n'
pathlib.Path('docs/upstream/ISSUE-body.md').write_text(body)
print("   listo")
PY

echo ">> 3) Commit inicial"
if [ ! -d .git ]; then
  git init -b main >/dev/null
fi
git add -A
git -c user.name="${GIT_NAME:-$(git config user.name || echo 'Sergio Baquedano')}" \
    commit -q -m "Siber DF EVO over local Modbus TCP: YAML package, register map and bridge setup" || true

echo ">> 4) Creando el repo y subiendo"
if gh repo view "$USER/$REPO" >/dev/null 2>&1; then
  echo "   ya existe, solo push"
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "git@github.com:$USER/$REPO.git"
  git push -u origin main
else
  gh repo create "$USER/$REPO" --public --source=. --push \
    --description "Local Modbus TCP control of a Siber DF EVO HRV unit (Airios BRDG-02EM23 Ethernet bridge) from Home Assistant — no cloud"
fi

echo
echo "Repo listo: $URL"
echo
echo "Para publicar el issue en pyairios (revísalo antes: docs/upstream/ISSUE-body.md):"
echo
echo "  gh issue create --repo scabrero/pyairios \\"
echo "    --title 'BRDG-02EM23 (Ethernet bridge): product ID missing and serial-only registers break fetch()' \\"
echo "    --body-file docs/upstream/ISSUE-body.md --web"
echo
echo "(--web abre el borrador en el navegador para darle el último repaso antes de enviar;"
echo " quita esa opción si lo quieres publicar directamente desde la terminal.)"

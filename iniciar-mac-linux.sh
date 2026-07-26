#!/usr/bin/env bash
# Arranca el servidor de Textos Sagrados.
set -uo pipefail
cd "$(dirname "$0")/backend"

GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'

if [ ! -d ".venv" ]; then
    echo "${YELLOW}  Todavía no has instalado el programa.${RESET}"
    echo "  Ejecuta primero:  bash instalar-mac-linux.sh"
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f "data/corpus.db" ]; then
    if [ -f "data/sample.db" ]; then
        echo "${YELLOW}  AVISO: no encuentro los textos completos.${RESET}"
        echo "  Arranco con el corpus de prueba (solo 100 versículos)."
        export TS_DB_PATH=data/sample.db
    else
        echo "${RED}  No hay ninguna base de datos.${RESET}"
        echo "  Ejecuta:  bash instalar-mac-linux.sh"
        exit 1
    fi
fi

echo
echo "${GREEN}  ============================================${RESET}"
echo "${GREEN}   Servidor de Textos Sagrados EN MARCHA${RESET}"
echo "${GREEN}  ============================================${RESET}"
echo
echo "  Para comprobar que funciona, abre en tu navegador:"
echo "      http://localhost:8000/docs"
echo
echo "  Deja esta terminal abierta mientras uses la aplicación."
echo "  Para apagarlo, pulsa Ctrl+C."
echo

(sleep 2 && (open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null)) &
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/usr/bin/env bash
# ============================================================
#  Textos Sagrados - Instalación automática (macOS y Linux)
#
#  Uso:  bash instalar-mac-linux.sh
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
RED=$'\033[31m'; RESET=$'\033[0m'

echo
echo "${BOLD}  ============================================${RESET}"
echo "${BOLD}   TEXTOS SAGRADOS - Instalación automática${RESET}"
echo "${BOLD}  ============================================${RESET}"
echo
echo "  Este proceso hará cuatro cosas:"
echo "    1. Comprobar que tienes Python instalado"
echo "    2. Preparar el entorno e instalar lo necesario"
echo "    3. Descargar los textos completos de internet"
echo "    4. Arrancar el servidor"
echo
echo "  Tarda entre 5 y 20 minutos según tu conexión."
echo
read -rp "  Pulsa Intro para empezar... "

# ---------- 1. Python ----------
echo
echo "  [1/4] Comprobando Python..."
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"; break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo
    echo "${YELLOW}  No he encontrado Python 3.10 o superior.${RESET}"
    echo
    echo "  QUÉ HACER:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    Opción A (recomendada), si tienes Homebrew:"
        echo "      brew install python@3.12"
        echo
        echo "    Opción B: descárgalo de https://www.python.org/downloads/"
    else
        echo "    En Ubuntu/Debian:   sudo apt install python3 python3-venv python3-pip"
        echo "    En Fedora:          sudo dnf install python3 python3-pip"
    fi
    echo
    echo "  Cuando termines, vuelve a ejecutar este script."
    exit 1
fi
echo "        Encontrado: $($PYTHON --version)"

# ---------- 2. Entorno ----------
echo
echo "  [2/4] Preparando el entorno (puede tardar unos minutos)..."
cd backend

if [ ! -d ".venv" ]; then
    if ! "$PYTHON" -m venv .venv 2>/dev/null; then
        echo "${RED}  ERROR: no se pudo crear el entorno.${RESET}"
        echo "  En Ubuntu/Debian puede faltar un paquete:"
        echo "      sudo apt install python3-venv"
        exit 1
    fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip --quiet

# --only-binary=:all: obliga a usar paquetes ya compilados. Sin esto, si tu
# Python es más reciente que algún paquete, pip intenta compilarlo desde
# fuente: tarda muchísimo, suele fallar y dispara falsos positivos de
# antivirus.
if ! python -m pip install --only-binary=:all: -r requirements-base.txt --quiet; then
    echo "        Reintentando sin restricción de binarios..."
    python -m pip install -r requirements-base.txt --quiet || true
fi

# El código de salida de pip no basta: comprobamos que los módulos importan.
if ! python -c "import fastapi, uvicorn, numpy, httpx, pydantic_settings" 2>/dev/null; then
    echo "${RED}  ERROR: las dependencias no se instalaron correctamente.${RESET}"
    echo "  Versión de Python detectada: $(python --version)"
    exit 1
fi
echo "        Entorno listo."

# ---------- 3. Corpus ----------
echo
echo "  [3/4] Comprobando las fuentes de los textos..."
echo
python scripts/fetch_corpus.py --check
echo
echo "  Si alguna fuente aparece como FALLO, el programa la omitirá"
echo "  y seguirá con las demás."
echo
read -rp "  Pulsa Intro para descargar los textos... "

echo
echo "  Descargando. Esto es lo que más tarda. No cierres la terminal."
echo
if ! python scripts/fetch_corpus.py --out data/corpus.db --skip-failed; then
    echo
    echo "${YELLOW}  La descarga no se completó del todo.${RESET}"
    echo "  Puedes volver a ejecutar este script: continuará desde donde"
    echo "  lo dejó, sin repetir lo ya descargado."
fi

# ---------- 4. Arrancar ----------
echo
echo "${GREEN}  ============================================${RESET}"
echo "${GREEN}   INSTALACIÓN COMPLETADA${RESET}"
echo "${GREEN}  ============================================${RESET}"
echo
echo "  A partir de ahora, para usar la aplicación ejecuta:"
echo "      ${BOLD}bash iniciar-mac-linux.sh${RESET}"
echo
echo "  Arrancando el servidor..."
sleep 2
cd ..
exec bash iniciar-mac-linux.sh

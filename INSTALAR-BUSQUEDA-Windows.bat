@echo off
REM ============================================================
REM  Instala la BUSQUEDA POR SIGNIFICADO.
REM  Es un extra: la aplicacion funciona sin esto.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Busqueda por significado
color 0F

echo.
echo   ============================================
echo    BUSQUEDA POR SIGNIFICADO
echo   ============================================
echo.
echo   Permite buscar ideas en lugar de palabras.
echo.
echo   Por ejemplo, si escribes "perdonar a quien te ha
echo   hecho dano", encuentra los pasajes que hablan de eso
echo   aunque no contengan ninguna de esas palabras.
echo.
echo   ANTES DE EMPEZAR, DEBES SABER:
echo.
echo     - Descarga unos 2 a 3 GB (el motor y el modelo^)
echo     - Ocupa unos 3 GB en tu disco duro
echo     - El calculo tarda entre 3 y 15 minutos
echo     - Puedes interrumpirlo: continua donde lo dejo
echo.
echo   La aplicacion YA FUNCIONA sin esto. Es un extra.
echo.
set /p SEGUIR="   Continuar? (S/N): "
if /i not "!SEGUIR!"=="S" (
    echo.
    echo   Cancelado. No se ha cambiado nada.
    goto :fin
)

if not exist "backend\.venv\Scripts\activate.bat" (
    color 0C
    echo.
    echo   ERROR: primero ejecuta INSTALAR-Windows.bat
    goto :fin
)

cd backend
call ".venv\Scripts\activate.bat"

if not exist "data\corpus.db" (
    color 0C
    echo.
    echo   ERROR: faltan los textos. Ejecuta INSTALAR-Windows.bat
    goto :fin
)

echo.
echo   [1/2] Descargando el motor de calculo...
echo         Esto es lo mas pesado. Puede tardar bastante.
echo.

REM  --only-binary evita que pip intente compilar desde codigo fuente,
REM  que en Windows falla y ademas dispara falsos positivos del antivirus.
python -m pip install --only-binary=:all: -r requirements-semantic.txt
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   No se pudo instalar con paquetes precompilados.
    echo.
    echo   Causa mas probable: tu version de Python es demasiado
    echo   reciente y el motor aun no la soporta.
    echo.
    python --version
    echo.
    echo   OPCIONES:
    echo     1. Sigue usando la aplicacion sin esta funcion.
    echo        Todo lo demas funciona igual.
    echo     2. Instala Python 3.12 y vuelve a ejecutar
    echo        INSTALAR-Windows.bat y luego este archivo.
    echo.
    goto :fin
)

python -c "import sentence_transformers" 2>nul
if !errorlevel! neq 0 (
    color 0C
    echo.
    echo   ERROR: se instalo pero no carga correctamente.
    echo   Puede que el antivirus bloqueara algun archivo.
    goto :fin
)
echo.
echo         Motor instalado.

echo.
echo   [2/2] Calculando el significado de cada versiculo...
echo.
echo         La primera vez descarga un modelo de 470 MB y
echo         durante esa descarga NO se ve progreso. Espera.
echo.

python scripts\build_embeddings.py
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   El calculo no termino. Vuelve a ejecutar este archivo:
    echo   continuara desde donde lo dejo.
    goto :fin
)

color 0A
echo.
echo   ============================================
echo    LISTO
echo   ============================================
echo.
echo   Ahora:
echo     1. CIERRA la ventana negra del servidor
echo     2. Doble clic en INICIAR-Windows.bat
echo     3. Recarga la pagina con F5
echo.
echo   Aparecera una pestana nueva: "Por significado"
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

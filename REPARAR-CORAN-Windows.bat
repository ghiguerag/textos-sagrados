@echo off
REM ============================================================
REM  Vuelve a descargar el Coran en INGLES.
REM
REM  El Coran se habia descargado en arabe por error: se pidio una
REM  edicion que no existe y la API devolvio el texto original sin
REM  avisar. Por eso todas las comparaciones con el Coran daban 0.
REM
REM  No toca los otros tres textos.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Reparar el Coran
color 0F

echo.
echo   ============================================
echo    REPARAR EL CORAN
echo   ============================================
echo.
echo   Se detecto que el Coran esta en arabe en lugar de
echo   ingles. Todas sus comparaciones daban cero.
echo.
echo   Esto va a:
echo     1. Descargar el Coran en ingles (Pickthall, 1930^)
echo     2. Borrar las obras que esten en el idioma equivocado
echo     3. Comprobar que todo el corpus esta correcto
echo.
echo   Tarda uno o dos minutos. Los otros tres textos no
echo   se tocan.
echo.
pause

if not exist "backend\.venv\Scripts\activate.bat" (
    color 0C
    echo   ERROR: primero ejecuta INSTALAR-Windows.bat
    goto :fin
)

cd backend
call ".venv\Scripts\activate.bat"

echo.
echo   [1/3] Comprobando el estado actual...
echo.
python scripts\revisar_corpus.py

echo.
echo   [2/3] Descargando el Coran en ingles...
echo.
python scripts\fetch_corpus.py --source quran-pickthall --force
if !errorlevel! neq 0 (
    color 0C
    echo.
    echo   No se pudo descargar. Comprueba tu conexion.
    echo   El corpus anterior sigue intacto.
    goto :fin
)

echo.
echo   [3/4] Quitando las obras en el idioma equivocado...
echo.
python scripts\limpiar_corpus.py --si
if !errorlevel! neq 0 (
    color 0E
    echo   No se pudo limpiar. Pasame lo de arriba.
    goto :fin
)

echo.
echo   [4/4] Verificando el resultado...
echo.
python scripts\revisar_corpus.py
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   Sigue habiendo problemas. Pasame lo de arriba.
    goto :fin
)

color 0A
echo.
echo   ============================================
echo    CORAN REPARADO
echo   ============================================
echo.
echo   Si tienes la busqueda por significado instalada,
echo   hay que recalcular sus vectores para el Coran:
echo.
echo     python scripts\build_embeddings.py --engine ligero
echo.
echo   Despues, reinicia el servidor.
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

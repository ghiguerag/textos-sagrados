@echo off
REM ============================================================
REM  Busqueda por significado, VERSION LIGERA.
REM  Sin PyTorch. Esta es la que se empaquetaria en la app.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Busqueda ligera
color 0F

echo.
echo   ============================================
echo    BUSQUEDA POR SIGNIFICADO - VERSION LIGERA
echo   ============================================
echo.
echo   Hace lo mismo que la version completa, pero con un
echo   modelo comprimido en lugar de una red neuronal.
echo.
echo   COMPARACION:
echo.
echo     Version completa   3 GB      calidad maxima
echo     Version ligera     530 MB    algo menos de calidad
echo     Version minima     ~130 MB   la mas comprimida
echo.
echo   Esta es la que tendria sentido meter dentro de la app
echo   publicada. La completa es demasiado grande para eso.
echo.
echo   Puedes instalar las dos y comparar los resultados.
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
echo   Que version quieres?
echo.
echo     1 = minima    (~130 MB, 128 dimensiones, comprimida^)
echo     2 = ligera    (~530 MB, todas las dimensiones^)
echo.
set /p OPCION="   Elige 1 o 2 [1]: "
if "!OPCION!"=="2" (set MOTOR=ligero) else (set MOTOR=minimo)

echo.
echo   [1/2] Instalando el motor ligero...
echo.
python -m pip install --only-binary=:all: -r requirements-light.txt
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   No se pudo instalar.
    python --version
    echo.
    echo   Sigue funcionando todo lo demas de la aplicacion.
    goto :fin
)

python -c "import model2vec" 2>nul
if !errorlevel! neq 0 (
    color 0C
    echo   ERROR: se instalo pero no carga.
    goto :fin
)
echo         Motor instalado.

echo.
echo   [2/2] Calculando con el motor "!MOTOR!"...
echo         Sera mucho mas rapido que la version completa.
echo.
python scripts\build_embeddings.py --engine !MOTOR!
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   El calculo no termino. Vuelve a ejecutar este archivo.
    goto :fin
)

color 0A
echo.
echo   ============================================
echo    LISTO
echo   ============================================
echo.
echo   Si tambien tienes la version completa instalada,
echo   puedes medir cuanta calidad se pierde:
echo.
echo     python scripts\comparar_motores.py --base calidad --contra !MOTOR!
echo.
echo   Te dira, con tus textos reales, si merece la pena
echo   empaquetar la ligera en la app.
echo.
echo   Reinicia el servidor para usarla.
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

@echo off
REM ============================================================
REM  Elimina del corpus las obras que estan en el idioma
REM  equivocado. No descarga nada.
REM
REM  IMPORTANTE: cierra antes el servidor. Si esta abierto,
REM  tiene la base de datos bloqueada y esto fallara.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Limpiar corpus
color 0F

echo.
echo   ============================================
echo    LIMPIAR EL CORPUS
echo   ============================================
echo.

REM  Comprobar que el servidor no esta ocupando la base de datos.
set PID_SERVIDOR=
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:"TCP.*:8000 .*LISTENING"') do (
    if not defined PID_SERVIDOR set PID_SERVIDOR=%%P
)
if defined PID_SERVIDOR (
    color 0E
    echo   El servidor esta funcionando y tiene la base de datos
    echo   abierta. Hay que cerrarlo antes.
    echo.
    set /p CERRAR="   Lo cierro ahora? (S/N) [S]: "
    if /i "!CERRAR!"=="N" (
        echo.
        echo   Cierra la ventana negra del servidor y vuelve a
        echo   ejecutar este archivo.
        goto :fin
    )
    taskkill /PID !PID_SERVIDOR! /F >nul 2>&1
    timeout /t 2 >nul
    echo   Servidor cerrado.
    color 0F
)

if not exist "backend\.venv\Scripts\activate.bat" (
    color 0C
    echo   ERROR: primero ejecuta INSTALAR-Windows.bat
    goto :fin
)

cd backend
call ".venv\Scripts\activate.bat"

echo.
echo   Buscando obras en el idioma equivocado...
echo.
python scripts\limpiar_corpus.py

echo.
set /p SEGUIR="   Eliminarlas? (S/N) [S]: "
if /i "!SEGUIR!"=="N" (
    echo.
    echo   Cancelado. No se ha cambiado nada.
    goto :fin
)

echo.
echo   Eliminando. La primera vez tarda un poco porque hay
echo   que crear un indice. No cierres la ventana.
echo.
python scripts\limpiar_corpus.py --si
if !errorlevel! neq 0 (
    color 0C
    echo   No se pudo completar. Pasame lo de arriba.
    goto :fin
)

echo.
echo   Comprobando el resultado...
echo.
python scripts\revisar_corpus.py

color 0A
echo.
echo   ============================================
echo    LISTO
echo   ============================================
echo.
echo   Arranca el servidor con INICIAR-Windows.bat
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

@echo off
REM ============================================================
REM  Textos Sagrados - Instalacion automatica para Windows
REM  Haz doble clic en este archivo. No necesitas saber programar.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
color 0F
title Textos Sagrados - Instalacion

REM  Si el usuario hace doble clic y algo falla en las primeras lineas, la
REM  ventana se cerraria antes de que le diera tiempo a leer nada. Esta
REM  comprobacion se hace lo primero y siempre deja la ventana abierta.
if not exist "backend\scripts\fetch_corpus.py" (
    color 0C
    echo.
    echo   ERROR: este archivo no esta en la carpeta correcta.
    echo.
    echo   INSTALAR-Windows.bat tiene que estar en la misma carpeta que
    echo   las carpetas "backend", "app" y "docs".
    echo.
    echo   Carpeta desde la que se ejecuto:
    echo   %~dp0
    echo.
    pause
    exit /b 1
)

set LOG=%~dp0informe-instalacion.txt
echo Instalacion iniciada el %date% a las %time% > "%LOG%"

echo.
echo   ============================================
echo    TEXTOS SAGRADOS - Instalacion automatica
echo   ============================================
echo.
echo   Este proceso hara cuatro cosas:
echo     1. Comprobar que tienes Python instalado
echo     2. Preparar el entorno e instalar lo necesario
echo     3. Descargar los textos completos de internet
echo     4. Arrancar el servidor
echo.
echo   Tarda entre 5 y 20 minutos segun tu conexion.
echo.
pause

REM ---------- 1. Comprobar Python ----------
echo.
echo   [1/4] Comprobando Python...
set PYTHON=
for %%P in (python py python3) do (
    if not defined PYTHON (
        %%P --version >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=2" %%V in ('%%P --version 2^>^&1') do (
                for /f "tokens=1,2 delims=." %%a in ("%%V") do (
                    if %%a geq 3 if %%b geq 10 set PYTHON=%%P
                )
            )
        )
    )
)

if not defined PYTHON (
    color 0E
    echo.
    echo   No he encontrado Python 3.10 o superior en tu ordenador.
    echo.
    echo   QUE HACER:
    echo     1. Abre https://www.python.org/downloads/
    echo     2. Descarga la version mas reciente
    echo     3. IMPORTANTE: al instalar, marca la casilla
    echo        "Add Python to PATH" en la primera pantalla
    echo     4. Cuando termine, vuelve a hacer doble clic aqui
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('!PYTHON! --version 2^>^&1') do (
    echo         Encontrado: %%V
    echo Python: %%V >> "%LOG%"
)

REM ---------- 2. Entorno y dependencias ----------
echo.
echo   [2/4] Preparando el entorno (puede tardar unos minutos)...
cd backend

if not exist ".venv" (
    !PYTHON! -m venv .venv
    if !errorlevel! neq 0 (
        color 0C
        echo   ERROR: no se pudo crear el entorno.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet

REM  --only-binary=:all: obliga a pip a usar solo paquetes ya compilados.
REM  Sin esto, si tu Python es mas reciente que algun paquete, pip intenta
REM  compilarlo, lo cual (a) tarda muchisimo, (b) suele fallar por falta de
REM  compilador y (c) hace saltar al antivirus con un falso positivo.
python -m pip install --only-binary=:all: -r requirements-base.txt --quiet
if !errorlevel! neq 0 (
    echo         Reintentando sin restriccion de binarios...
    python -m pip install -r requirements-base.txt --quiet
)

REM  Comprobacion real: que los modulos se puedan importar. El codigo de
REM  salida de pip no basta, porque el antivirus puede borrar un archivo a
REM  medio proceso y dejar el paquete a medias.
python -c "import fastapi, uvicorn, numpy, httpx, pydantic_settings" 2>nul
if !errorlevel! neq 0 (
    color 0C
    echo.
    echo   ERROR: las dependencias no se instalaron correctamente.
    echo.
    echo   Causa mas probable: tu antivirus bloqueo un archivo temporal
    echo   durante la instalacion. Es un falso positivo conocido.
    echo.
    echo   QUE HACER:
    echo     1. Abre Norton y ve al historial de seguridad
    echo     2. Si ves un aviso sobre un archivo en la carpeta Temp
    echo        con "pip-install" en la ruta, era este proceso
    echo     3. Vuelve a ejecutar este instalador
    echo.
    echo   Si vuelve a fallar, dime que version de Python tienes:
    python --version
    echo.
    pause
    exit /b 1
)
echo         Entorno listo.

REM ---------- 3. Descargar corpus ----------
echo.
echo   [3/4] Comprobando las fuentes de los textos...
echo.
python scripts\fetch_corpus.py --check
echo.
echo   Si alguna fuente aparece como FALLO, el programa la omitira
echo   y seguira con las demas.
echo.
pause

echo.
echo   Descargando los textos. Esto es lo que mas tarda.
echo   No cierres esta ventana.
echo.
python scripts\fetch_corpus.py --out data\corpus.db --skip-failed
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   La descarga no se completo del todo.
    echo   Puedes volver a ejecutar este instalador: continuara
    echo   desde donde lo dejo, sin repetir lo ya descargado.
    pause
)

REM ---------- 4. Arrancar ----------
echo.
echo   [4/4] Todo listo.
echo.
color 0A
echo   ============================================
echo    INSTALACION COMPLETADA
echo   ============================================
echo.
echo   A partir de ahora, para usar la aplicacion solo tienes
echo   que hacer doble clic en:  INICIAR-Windows.bat
echo.
echo   Arrancando el servidor...
echo.
timeout /t 3 >nul
cd ..
call INICIAR-Windows.bat

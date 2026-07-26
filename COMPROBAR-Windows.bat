@echo off
REM ============================================================
REM  Comprueba en que estado esta la instalacion.
REM  No instala ni cambia nada. Solo mira y te lo cuenta.
REM  Esta ventana NO se cierra sola.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Comprobacion
color 0F

set LOG=%~dp0informe-comprobacion.txt
echo Informe generado el %date% a las %time% > "%LOG%"
echo Carpeta: %~dp0 >> "%LOG%"
echo. >> "%LOG%"

echo.
echo   ============================================
echo    COMPROBACION DE LA INSTALACION
echo   ============================================
echo.
echo   Carpeta actual:
echo   %~dp0
echo.

REM ---------- 0. Estamos en la carpeta correcta? ----------
if not exist "backend\scripts\fetch_corpus.py" (
    color 0C
    echo   [X] ESTE ARCHIVO NO ESTA EN LA CARPETA CORRECTA
    echo.
    echo   No encuentro la carpeta "backend" junto a este archivo.
    echo.
    echo   El archivo COMPROBAR-Windows.bat tiene que estar en la MISMA
    echo   carpeta que las carpetas "backend", "app" y "docs".
    echo.
    echo   Si moviste o copiaste solo este archivo, vuelve a ponerlo
    echo   dentro de la carpeta textos-sagrados.
    echo.
    echo   [X] Carpeta incorrecta >> "%LOG%"
    goto :final
)
echo   [OK] Carpeta correcta.
echo   [OK] Carpeta correcta >> "%LOG%"

REM ---------- 1. Python ----------
echo.
echo   --- 1. Python ---
set PYTHON=
for %%P in (python py python3) do (
    if not defined PYTHON (
        %%P --version >nul 2>&1
        if !errorlevel! equ 0 set PYTHON=%%P
    )
)
if not defined PYTHON (
    color 0E
    echo   [X] Python NO esta instalado, o Windows no lo encuentra.
    echo.
    echo   SOLUCION: instalalo desde https://www.python.org/downloads/
    echo   y marca la casilla "Add Python to PATH" en la primera pantalla.
    echo   [X] Python no encontrado >> "%LOG%"
    goto :final
)
for /f "tokens=*" %%V in ('!PYTHON! --version 2^>^&1') do (
    echo   [OK] %%V
    echo   [OK] %%V >> "%LOG%"
)

REM ---------- 2. Entorno ----------
echo.
echo   --- 2. Entorno de trabajo ---
if not exist "backend\.venv\Scripts\python.exe" (
    color 0E
    echo   [X] El entorno NO esta creado.
    echo       Falta la carpeta backend\.venv
    echo.
    echo   SOLUCION: ejecuta INSTALAR-Windows.bat
    echo   [X] Entorno no creado >> "%LOG%"
    goto :final
)
echo   [OK] Entorno creado.
echo   [OK] Entorno creado >> "%LOG%"

REM ---------- 3. Dependencias ----------
echo.
echo   --- 3. Programas necesarios ---
call backend\.venv\Scripts\activate.bat
python -c "import fastapi, uvicorn, numpy, httpx, pydantic_settings" 2>nul
if !errorlevel! neq 0 (
    color 0E
    echo   [X] Faltan programas necesarios o estan incompletos.
    echo.
    echo   Detalle:
    python -c "import fastapi" 2>nul || echo       - falta fastapi
    python -c "import uvicorn" 2>nul || echo       - falta uvicorn
    python -c "import numpy" 2>nul || echo       - falta numpy
    python -c "import httpx" 2>nul || echo       - falta httpx
    python -c "import pydantic_settings" 2>nul || echo       - falta pydantic-settings
    echo.
    echo   SOLUCION: ejecuta INSTALAR-Windows.bat otra vez.
    echo   [X] Dependencias incompletas >> "%LOG%"
    goto :final
)
echo   [OK] Todos los programas necesarios estan instalados.
echo   [OK] Dependencias completas >> "%LOG%"

REM ---------- 4. Textos ----------
echo.
echo   --- 4. Textos descargados ---
if not exist "backend\data\corpus.db" (
    color 0E
    echo   [X] Los textos NO estan descargados.
    echo       Falta el archivo backend\data\corpus.db
    echo.
    echo   SOLUCION: ejecuta INSTALAR-Windows.bat
    echo   [X] Corpus no descargado >> "%LOG%"
    goto :final
)
for %%A in ("backend\data\corpus.db") do set TAM=%%~zA
set /a TAMMB=!TAM! / 1048576
echo   [OK] Archivo de textos encontrado (!TAMMB! MB^)
echo   [OK] corpus.db: !TAMMB! MB >> "%LOG%"
echo.
echo   Contenido:
python -c "import sqlite3,sys; c=sqlite3.connect('backend/data/corpus.db'); [print(f'        {r[0]:<18} {r[1]:>7} versiculos  {r[2]:>9} palabras') for r in c.execute('SELECT id,total_verses,total_tokens FROM works ORDER BY tradition')]" 2>nul
if !errorlevel! neq 0 echo        (no se pudo leer el contenido)
python -c "import sqlite3; c=sqlite3.connect('backend/data/corpus.db'); [print(f'  {r[0]} {r[1]} {r[2]}') for r in c.execute('SELECT id,total_verses,total_tokens FROM works')]" >> "%LOG%" 2>nul

REM ---------- 5. Servidor ----------
echo.
echo   --- 5. Servidor ---
python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/health',timeout=3)" 2>nul
if !errorlevel! equ 0 (
    color 0A
    echo   [OK] El servidor esta FUNCIONANDO ahora mismo.
    echo        Abre http://localhost:8000/docs en tu navegador.
    echo   [OK] Servidor activo >> "%LOG%"
) else (
    echo   [-]  El servidor no esta encendido ahora mismo.
    echo        Eso es normal si no lo has arrancado.
    echo        Para encenderlo: doble clic en INICIAR-Windows.bat
    echo   [-] Servidor apagado >> "%LOG%"
)

color 0A
echo.
echo   ============================================
echo    TODO CORRECTO. La instalacion esta completa.
echo   ============================================

:final
echo.
echo   ----------------------------------------------------
echo   He guardado este informe en:
echo   informe-comprobacion.txt
echo   (en esta misma carpeta)
echo   ----------------------------------------------------
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

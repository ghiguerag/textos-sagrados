@echo off
REM ============================================================
REM  Arranca el servidor de Textos Sagrados.
REM  Esta ventana no se cierra sola pase lo que pase.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Servidor
color 0F

set LOG=%~dp0informe-servidor.txt
echo Arranque del %date% a las %time% > "%LOG%"

echo.
echo   Carpeta: %~dp0
echo.
echo %~dp0 | findstr /i "OneDrive Dropbox \"Google Drive\"" >nul
if not errorlevel 1 (
    color 0E
    echo   AVISO: el proyecto esta en una carpeta sincronizada con la nube.
    echo   Eso puede hacer que el arranque tarde mucho o falle, porque los
    echo   archivos se vacian para ahorrar espacio y hay que rebajarlos.
    echo.
    echo   Si va lento, ejecuta ANCLAR-ARCHIVOS-Windows.bat
    echo.
    color 0F
)

if not exist "backend\scripts\fetch_corpus.py" (
    color 0C
    echo   ERROR: este archivo no esta en la carpeta correcta.
    echo   Debe estar junto a las carpetas backend, app y docs.
    echo   ERROR: carpeta incorrecta >> "%LOG%"
    goto :fin
)

cd backend

if not exist ".venv\Scripts\activate.bat" (
    color 0E
    echo   Todavia no has instalado el programa.
    echo   Haz doble clic primero en INSTALAR-Windows.bat
    echo   ERROR: entorno no creado >> "%LOG%"
    goto :fin
)

call ".venv\Scripts\activate.bat"
if !errorlevel! neq 0 (
    color 0C
    echo   ERROR: no se pudo activar el entorno.
    echo   ERROR: activate fallo >> "%LOG%"
    goto :fin
)

if exist "data\corpus.db" (
    echo   Textos completos encontrados.
) else (
    if exist "data\sample.db" (
        color 0E
        echo   AVISO: uso el corpus de prueba, solo 100 versiculos.
        set TS_DB_PATH=data\sample.db
    ) else (
        color 0C
        echo   ERROR: no hay ninguna base de datos.
        echo   Ejecuta INSTALAR-Windows.bat
        echo   ERROR: sin base de datos >> "%LOG%"
        goto :fin
    )
)

echo.
echo   Comprobando que todo carga...
python -c "import fastapi, uvicorn" 2>>"%LOG%"
if !errorlevel! neq 0 (
    color 0C
    echo   ERROR: faltan programas necesarios.
    echo   Ejecuta INSTALAR-Windows.bat otra vez.
    goto :fin
)

REM ---------- El puerto 8000 debe estar libre ----------
REM  Si quedo un servidor anterior abierto, el nuevo no puede arrancar y
REM  ademas el navegador seguiria hablando con el viejo, que tiene el codigo
REM  antiguo. Es la causa de que un arreglo "no surta efecto".
set PID_VIEJO=
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:"TCP.*:8000 .*LISTENING"') do (
    if not defined PID_VIEJO set PID_VIEJO=%%P
)

if defined PID_VIEJO (
    color 0E
    echo.
    echo   ====================================================
    echo    YA HAY UN SERVIDOR FUNCIONANDO
    echo   ====================================================
    echo.
    echo   Otro servidor esta usando el puerto 8000
    echo   (numero de proceso: !PID_VIEJO!^)
    echo.
    echo   Seguramente es una ventana negra que dejaste abierta.
    echo   Mientras siga viva, el navegador habla con ELLA, no con
    echo   esta, asi que los cambios nuevos no se veran.
    echo.
    set /p CERRAR="   Cierro el servidor antiguo? (S/N) [S]: "
    if /i "!CERRAR!"=="N" (
        echo.
        echo   De acuerdo. Cierra tu esa otra ventana y vuelve a
        echo   ejecutar este archivo.
        goto :fin
    )
    echo.
    echo   Cerrando el servidor antiguo...
    taskkill /PID !PID_VIEJO! /F >nul 2>&1
    timeout /t 2 >nul

    REM  Comprobar que el puerto quedo libre de verdad
    set SIGUE=
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:"TCP.*:8000 .*LISTENING"') do (
        if not defined SIGUE set SIGUE=%%P
    )
    if defined SIGUE (
        color 0C
        echo   No pude cerrarlo. Cierra a mano todas las ventanas
        echo   negras tituladas "Textos Sagrados - Servidor" y
        echo   vuelve a ejecutar este archivo.
        goto :fin
    )
    echo   Servidor antiguo cerrado. El puerto esta libre.
    color 0F
)

color 0A
echo.
echo   ============================================
echo    SERVIDOR EN MARCHA
echo   ============================================
echo.
echo   El navegador se abrira solo cuando el servidor este listo.
echo   Si tarda, es normal: espera.
echo.
echo   Direccion:  http://localhost:8000
echo.
echo   Deja esta ventana abierta mientras uses la aplicacion.
echo   Para apagarlo, cierra esta ventana.
echo.
echo   ----------------------------------------------------
echo.

REM  Abrir el navegador SOLO cuando el servidor responda de verdad. Antes se
REM  abria de inmediato y aparecia "localhost rechazo la conexion", porque el
REM  servidor tardaba unos segundos en estar listo. En carpetas sincronizadas
REM  con la nube puede tardar bastante mas.
start "" /min python scripts\abrir_navegador.py

REM  Sin --host 0.0.0.0 para no exponer el servidor a la red local:
REM  solo accesible desde este ordenador. Si quieres usarlo desde el
REM  movil, cambia 127.0.0.1 por 0.0.0.0.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1

echo.
color 0E
echo   ----------------------------------------------------
echo   El servidor se ha detenido.
echo.
echo   Si arriba pone "10048" o "solo se permite un uso de
echo   cada direccion", significa que habia otro servidor
echo   abierto. Vuelve a ejecutar este archivo: ahora lo
echo   detecta y se ofrece a cerrarlo.
echo.
echo   Si ves otros errores, copialos y pasamelos.
echo   ----------------------------------------------------

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

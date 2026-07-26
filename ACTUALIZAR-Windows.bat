@echo off
REM ============================================================
REM  Copia los archivos nuevos sobre tu instalacion, SIN borrar
REM  el entorno ni los textos que ya descargaste.
REM
REM  Ejecuta este archivo desde la carpeta que te pasa Claude.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Actualizar
color 0F

echo.
echo   ============================================
echo    ACTUALIZAR UNA INSTALACION EXISTENTE
echo   ============================================
echo.
echo   Origen (archivos nuevos):
echo   %~dp0
echo.
for /f "tokens=2 delims==" %%V in ('findstr /c:"API_VERSION = " "%~dp0backend\app\main.py"') do (
    set VER=%%V
    echo   Version que se va a copiar: !VER!
)
echo.

if not exist "backend\app\static\index.html" (
    color 0C
    echo   ERROR: no encuentro los archivos nuevos.
    echo   Ejecuta este .bat desde la carpeta que te paso Claude.
    goto :fin
)

echo   Escribe la ruta de TU carpeta instalada y pulsa Intro.
echo.
echo   Para copiarla: abre tu carpeta en el Explorador, haz clic en la
echo   barra de direcciones de arriba, y copia lo que aparece.
echo.
echo   Ejemplo:
echo   C:\Users\%USERNAME%\OneDrive\Documentos\Claude IA\PROYECTOS\textos-sagrados
echo.
set /p DESTINO="   Ruta: "

REM  Quitar comillas si el usuario pego la ruta entrecomillada
set DESTINO=%DESTINO:"=%

if not exist "%DESTINO%\backend\scripts\fetch_corpus.py" (
    color 0C
    echo.
    echo   ERROR: ahi no hay una instalacion de Textos Sagrados.
    echo   Ruta probada: %DESTINO%
    echo.
    echo   Debe ser la carpeta que contiene las carpetas backend, app y docs.
    goto :fin
)

REM  Python guarda una version compilada de cada archivo en __pycache__.
REM  Si queda una antigua puede seguir usandose y los cambios no surten
REM  efecto, asi que se borran antes de copiar.
REM
REM  IMPORTANTE: solo dentro de las carpetas DEL PROYECTO. La carpeta .venv
REM  tiene mas de diez mil archivos temporales de los paquetes instalados;
REM  borrarlos no aporta nada, tarda muchisimo y OneDrive tendria que
REM  sincronizar miles de borrados.
echo.
echo   Limpiando archivos temporales de Python del proyecto...
for %%C in (app scripts tests) do (
    if exist "%DESTINO%\backend\%%C" (
        for /d /r "%DESTINO%\backend\%%C" %%D in (__pycache__) do (
            if exist "%%D" rd /s /q "%%D" 2>nul
        )
    )
)

echo   Copiando... (no se borrara nada de lo que ya tienes)
echo.

REM  /E incluye subcarpetas, /Y sobrescribe sin preguntar.
REM  Se excluyen .venv y los .db para no tocar el entorno instalado ni los
REM  76 MB de textos ya descargados.
robocopy "%~dp0." "%DESTINO%" /E /NFL /NDL /NJH /NJS /NC /NS ^
  /XD ".venv" "__pycache__" "cache" ^
  /XF "*.db" "*.db-journal" "informe-*.txt" >nul

if !errorlevel! geq 8 (
    color 0C
    echo   ERROR durante la copia.
    goto :fin
)

color 0A
echo   ============================================
echo    ACTUALIZADO CORRECTAMENTE
echo   ============================================
echo.
echo   Se conservaron intactos:
echo     - el entorno instalado (.venv^)
echo     - los textos descargados (corpus.db^)
echo.
color 0E
echo   ****************************************************
echo   *  IMPORTANTE: REINICIA EL SERVIDOR                 *
echo   ****************************************************
echo.
echo   Si tenias el servidor encendido, sigue usando el
echo   codigo viejo: no se entera de los archivos nuevos.
echo.
echo   1. CIERRA la ventana negra del servidor
echo   2. Doble clic en INICIAR-Windows.bat
echo   3. Recarga el navegador con CTRL + F5
echo.
echo   El paso 3 con CTRL es importante: sin el, el navegador
echo   reutiliza la pantalla vieja que tiene guardada.
echo.
echo   Arriba a la derecha de la pagina veras la version.
echo   Si dice que no coinciden, repite estos 3 pasos.
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

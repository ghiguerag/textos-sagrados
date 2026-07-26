@echo off
REM ============================================================
REM  Ejecuta la aplicacion de escritorio EN MODO PRUEBA, con la
REM  ventana negra visible, para ver en directo que hace.
REM
REM  Es la MISMA app; solo que aqui vemos todos los mensajes.
REM  Sirve para diagnosticar y, de paso, ya funciona como app.
REM ============================================================
setlocal
cd /d "%~dp0\backend"
title Textos Sagrados - Modo prueba
color 0F

if not exist ".venv\Scripts\activate.bat" (
    color 0C
    echo   Primero ejecuta INSTALAR-Windows.bat
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"

echo.
echo   Arrancando en modo prueba. Veras aqui todo lo que hace.
echo   Se abrira una ventana con la aplicacion.
echo   Deja esta ventana negra abierta mientras la uses.
echo.

python desktop.py

echo.
echo   ----------------------------------------------------
echo   La aplicacion se ha cerrado.
echo   Si ves errores arriba, copialos y pasamelos.
echo   ----------------------------------------------------
echo.
pause

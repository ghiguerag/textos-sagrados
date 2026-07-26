@echo off
REM ============================================================
REM  Convierte Textos Sagrados en un programa de escritorio.
REM
REM  Construye FUERA de OneDrive (en una carpeta local rapida) y
REM  deja un acceso directo "Textos Sagrados" en tu Escritorio.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Textos Sagrados - Construir la app
color 0F

echo.
echo   ============================================
echo    CONSTRUIR LA APLICACION DE ESCRITORIO
echo   ============================================
echo.
echo   Crea un programa de Windows con icono propio.
echo   Tarda unos minutos.
echo.
pause

if not exist "backend\.venv\Scripts\activate.bat" (
    color 0C
    echo   ERROR: primero ejecuta INSTALAR-Windows.bat
    goto :fin
)
if not exist "backend\data\corpus.db" (
    color 0C
    echo   ERROR: faltan los textos. Ejecuta INSTALAR-Windows.bat
    goto :fin
)

cd backend
call ".venv\Scripts\activate.bat"

REM  Cerrar cualquier instancia abierta que pueda bloquear archivos: el
REM  ejecutable y la ventana de Edge que abrio con NUESTRO perfil (no el
REM  Edge normal del usuario, que se distingue por la ruta del perfil).
taskkill /IM "Textos Sagrados.exe" /F >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like '*TextosSagradosApp*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
timeout /t 2 >nul

echo.
echo   [1/4] Instalando las herramientas de empaquetado...
echo.
python -m pip install --only-binary=:all: -r requirements-desktop.txt
if !errorlevel! neq 0 (
    echo         Reintentando sin restriccion de binarios...
    python -m pip install -r requirements-desktop.txt
)
python -c "import PyInstaller" 2>nul
if !errorlevel! neq 0 (
    color 0C
    echo   No se pudo instalar PyInstaller. Comprueba tu conexion.
    goto :fin
)

REM  Construir en una carpeta LOCAL, nunca dentro de OneDrive: los archivos
REM  temporales de compilacion cambian sin parar y OneDrive los bloquea,
REM  provocando "Acceso denegado" al reemplazar la version anterior.
set "BUILD=%LOCALAPPDATA%\TextosSagrados"
if exist "%BUILD%\dist" rmdir /s /q "%BUILD%\dist" 2>nul

echo.
echo   [2/4] Construyendo el ejecutable (lo que mas tarda)...
echo.
python -m PyInstaller --noconfirm --distpath "%BUILD%\dist" --workpath "%BUILD%\build" TextosSagrados.spec
if !errorlevel! neq 0 (
    color 0E
    echo.
    echo   La construccion fallo. Copia el error de arriba y pasamelo.
    goto :fin
)

echo.
echo   [3/4] Copiando los textos junto al programa...
echo.
set "APP=%BUILD%\dist\Textos Sagrados"
if not exist "%APP%\data" mkdir "%APP%\data"
copy /Y "data\corpus.db" "%APP%\data\" >nul
copy /Y "data\lexicon.json" "%APP%\data\" >nul

echo   [4/4] Creando el acceso directo en el Escritorio...
set "EXE=%APP%\Textos Sagrados.exe"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Textos Sagrados.lnk'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%APP%'; $s.Save()" >nul 2>&1

color 0A
echo.
echo   ============================================
echo    LISTO
echo   ============================================
echo.
echo   Tienes un acceso directo "Textos Sagrados" en tu
echo   Escritorio. Doble clic para abrir la aplicacion.
echo.
echo   El programa esta en:
echo     %EXE%
echo.
echo   Para llevarlo a la Microsoft Store, sigue
echo   docs\empaquetado-windows.md
echo.

:fin
echo.
echo   Esta ventana no se cerrara sola.
echo.
pause

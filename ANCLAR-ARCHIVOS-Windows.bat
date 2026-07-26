@echo off
REM ============================================================
REM  Obliga a OneDrive a mantener el proyecto SIEMPRE en el disco.
REM
REM  OneDrive, para ahorrar espacio, convierte archivos que no usas
REM  en accesos directos vacios. Cuando un programa los necesita,
REM  tiene que descargarlos otra vez y todo se queda colgado.
REM
REM  Con un proyecto que tiene miles de archivos, esto lo rompe.
REM ============================================================
setlocal
cd /d "%~dp0"
title Textos Sagrados - Anclar archivos
color 0F

echo.
echo   ============================================
echo    MANTENER LOS ARCHIVOS SIEMPRE EN EL DISCO
echo   ============================================
echo.
echo   Carpeta: %~dp0
echo.
echo   Esto le dice a OneDrive que NO vacie los archivos de
echo   este proyecto. Seguiran teniendo copia en la nube,
echo   pero tambien estaran siempre en tu disco duro.
echo.
echo   Ocupara alrededor de 5 GB de forma permanente,
echo   sobre todo por los programas de la busqueda por
echo   significado.
echo.
echo   Puede tardar varios minutos si hay mucho que bajar.
echo.
pause

echo.
echo   Anclando archivos...
echo   (si OneDrive empieza a descargar, dejalo terminar^)
echo.

REM  +P marca el archivo como "mantener siempre en este dispositivo".
REM  -U quita la marca de "solo en la nube".
attrib +P -U "%~dp0*" /s /d >nul 2>&1

echo.
color 0A
echo   ============================================
echo    LISTO
echo   ============================================
echo.
echo   OneDrive puede seguir descargando un rato en segundo
echo   plano. Miralo en el icono de la nube, abajo a la
echo   derecha: cuando no tenga flechas girando, ha acabado.
echo.
echo   Despues, arranca el servidor normalmente.
echo.
echo   ----------------------------------------------------
echo   ALTERNATIVA MAS SOLIDA
echo.
echo   Si sigue dando problemas, lo mejor es sacar el
echo   proyecto de OneDrive del todo. Dimelo y te preparo
echo   el traslado.
echo   ----------------------------------------------------
echo.
pause

@echo off
chcp 65001 > nul
cls
echo =========================================================
echo    COMPILADOR DE INSTALADORES - SISTEMA DE SUPERVISION UPC
echo =========================================================
echo.

SET "PROYECTO=%~dp0"
SET "APP_PROF=%PROYECTO%AppProfesor"
SET "APP_SUP=%PROYECTO%AppSupervision"

echo Verificando PyInstaller...
where pyinstaller >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller no encontrado. Instalando...
    pip install pyinstaller
)
echo [OK] PyInstaller disponible.
echo.

echo Descargando instalador de Python 3.12.10 (si no existe)...
IF NOT EXIST "%PROYECTO%python-3.12.10-amd64.exe" (
    curl -o "%PROYECTO%python-3.12.10-amd64.exe" https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
)
echo [OK] Python 3.12.10 listo.
echo.

REM ==============================
REM COMPILAR PANEL DOCENTE (PROF)
REM ==============================
echo [1/4] Compilando lanzador del Panel Docente...
cd /d "%APP_PROF%"
pyinstaller --clean launcher.spec
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo la compilacion del Panel Docente.
    pause
    exit /b 1
)
echo [OK] Panel Docente compilado. Archivo: dist\PanelDocente_UPC.exe
echo.

REM ==============================
REM COMPILAR SUPERVISION (ESTUD)
REM ==============================
echo [2/4] Compilando lanzador de Supervision (Estudiante)...
cd /d "%APP_SUP%"
pyinstaller --clean launcher.spec
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo la compilacion de Supervision UPC.
    pause
    exit /b 1
)
echo [OK] Supervision UPC compilado. Archivo: dist\SupervisionUPC.exe
echo.

REM ==============================
REM CREAR INSTALADORES CON INNO SETUP
REM ==============================
echo [3/4] Buscando Inno Setup...
SET "INNO="
IF EXIST "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" SET "INNO=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
IF EXIST "C:\Program Files\Inno Setup 6\ISCC.exe" SET "INNO=C:\Program Files\Inno Setup 6\ISCC.exe"
IF EXIST "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" SET "INNO=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

IF "%INNO%"=="" (
    echo.
    echo [AVISO] Inno Setup no esta instalado.
    echo Para crear los instaladores .exe finales:
    echo   1. Descarga Inno Setup desde: https://jrsoftware.org/isinfo.php
    echo   2. Instalalo y luego abre:
    echo      - %APP_PROF%\installer_profesor.iss
    echo      - %APP_SUP%\installer_estudiante.iss
    echo   3. Presiona Build en cada uno.
    echo.
) ELSE (
    echo [OK] Inno Setup encontrado.
    echo.
    echo [4/4] Generando instalador del Panel Docente...
    cd /d "%APP_PROF%"
    "%INNO%" installer_profesor.iss
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Fallo el instalador del Panel Docente.
        pause
        exit /b 1
    )
    echo [OK] Instalador generado: AppProfesor\installer_output\Instalar_PanelDocente_UPC.exe
    echo.

    echo [4/4] Generando instalador de Supervision UPC...
    cd /d "%APP_SUP%"
    "%INNO%" installer_estudiante.iss
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Fallo el instalador de Supervision UPC.
        pause
        exit /b 1
    )
    echo [OK] Instalador generado: AppSupervision\installer_output\Instalar_SupervisionUPC.exe
    echo.
)

echo =========================================================
echo  PROCESO COMPLETADO
echo =========================================================
echo.
echo Archivos generados:
echo   Profesor : AppProfesor\installer_output\Instalar_PanelDocente_UPC.exe
echo   Estudiante: AppSupervision\installer_output\Instalar_SupervisionUPC.exe
echo.
echo Estos archivos son los instaladores finales para distribuir.
echo.
pause

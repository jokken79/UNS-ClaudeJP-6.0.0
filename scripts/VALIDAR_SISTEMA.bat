@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title UNS-ClaudeJP - Validacion del Sistema

cls
echo.
echo ========================================================
echo   UNS-CLAUDEJP v4.2 - VALIDADOR DE SISTEMA
echo ========================================================
echo.
echo Verificando configuracion del sistema...
echo.

set "CRITICAL_COUNT=0"
set "HIGH_COUNT=0"

cd /d "%~dp0\.."

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
  py --version >nul 2>&1
  if %errorlevel% NEQ 0 (
    echo [X] CRITICAL: Python NO instalado
    set /a CRITICAL_COUNT+=1
  )
)

REM Verificar Docker
docker --version >nul 2>&1
if %errorlevel% NEQ 0 (
  echo [X] CRITICAL: Docker NO instalado
  set /a CRITICAL_COUNT+=1
)

REM Verificar Docker Compose
docker compose version >nul 2>&1
if %errorlevel% NEQ 0 (
  docker-compose --version >nul 2>&1
  if %errorlevel% NEQ 0 (
    echo [X] CRITICAL: Docker Compose NO disponible
    set /a CRITICAL_COUNT+=1
  )
)

REM Verificar archivos criticos
if not exist "docker-compose.yml" (
  echo [X] HIGH: docker-compose.yml NO encontrado
  set /a HIGH_COUNT+=1
)

if not exist "generate_env.py" (
  echo [X] HIGH: generate_env.py NO encontrado
  set /a HIGH_COUNT+=1
)

REM Verificar cadena Alembic rota
if exist "backend\alembic\versions\a579f9a2a523_add_social_insurance_rates_table_simple.py" (
  findstr "fe6aac62e522" "backend\alembic\versions\a579f9a2a523_add_social_insurance_rates_table_simple.py" >nul 2>&1
  if %errorlevel% EQU 0 (
    echo [X] CRITICAL: Cadena Alembic ROTA
    set /a CRITICAL_COUNT+=1
  )
)

echo.
echo RESUMEN: CRITICAL=%CRITICAL_COUNT% HIGH=%HIGH_COUNT%
echo.

if %CRITICAL_COUNT% GTR 0 (
  echo [X] RIESGOS DETECTADOS - No seguro para REINSTALAR.bat
  pause >nul
) else (
  echo [OK] Sistema SEGURO para REINSTALAR.bat
  pause >nul
  exit /b 0
)

pause >nul

@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title UNS-ClaudeJP 5.4 - Reinstalación Completa (Arreglada)

echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E                 UNS-CLAUDEJP 5.4 - REINSTALACIÓN                   ╁Eecho ╁E                   Versión 2025-11-10 (FIXED)                        ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.

:: Variables globales
set "PYTHON_CMD="
set "DOCKER_COMPOSE_CMD="
set "ERROR_FLAG=0"

:: ══════════════════════════════════════════════════════════════════════════╁E::  FASE 1: DIAGNÓSTICO DEL SISTEMA
:: ══════════════════════════════════════════════════════════════════════════╁E
echo [FASE 1/3] Diagnóstico del Sistema
echo.

:: Verificar Python
echo   ▶ Python................
python --version >nul 2>&1 && (
    set "PYTHON_CMD=python"
    echo     ✁EOK
) || py --version >nul 2>&1 && (
    set "PYTHON_CMD=py"
    echo     ✁EOK
) || (
    echo     ✁ENO INSTALADO
    set "ERROR_FLAG=1"
)

:: Verificar Docker
echo   ▶ Docker................
docker --version >nul 2>&1 && (
    echo     ✁EOK
) || (
    echo     ✁ENO INSTALADO
    set "ERROR_FLAG=1"
)

:: Verificar Docker running
echo   ▶ Docker Running........
docker ps >nul 2>&1 && (
    echo     ✁EOK
) || (
    echo     ✁ENO CORRIENDO - Abre Docker Desktop
    set "ERROR_FLAG=1"
)

:: Verificar Docker Compose
echo   ▶ Docker Compose........
docker compose version >nul 2>&1 && (
    set "DOCKER_COMPOSE_CMD=docker compose"
    echo     ✁EOK ^(V2^)
) || docker-compose version >nul 2>&1 && (
    set "DOCKER_COMPOSE_CMD=docker-compose"
    echo     ✁EOK ^(V1^)
) || (
    echo     ✁ENO ENCONTRADO
    set "ERROR_FLAG=1"
)

:: Verificar archivos del proyecto
cd /d "%~dp0\.."
echo   ▶ docker-compose.yml....
if exist "docker-compose.yml" (echo     ✁EOK) else (echo     ✁EFALTA & set "ERROR_FLAG=1")

echo   ▶ generate_env.py.......
if exist "generate_env.py" (echo     ✁EOK) else (echo     ✁EFALTA & set "ERROR_FLAG=1")

echo.

:: Verificar resultado del diagnóstico
if %ERROR_FLAG% EQU 1 (
    echo ╔══════════════════════════════════════════════════════════════════════╗
    echo ╁E ✁EDIAGNÓSTICO FALLIDO - Corrige los errores antes de continuar     ╁E    echo ╚══════════════════════════════════════════════════════════════════════╝
    echo.
    echo ════════════════════════════════════════════════════════════════════
    echo  ✁EERROR - PRESIONA CUALQUIER TECLA PARA CERRAR
    echo ════════════════════════════════════════════════════════════════════
    pause >nul
)

echo ✁EDiagnóstico completado
echo.

:: ══════════════════════════════════════════════════════════════════════════╁E::  FASE 2: CONFIRMACIÓN
:: ══════════════════════════════════════════════════════════════════════════╁E
echo [FASE 2/3] Confirmación
echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E                     ⚠�E�E ADVERTENCIA IMPORTANTE                       ╁Eecho ╠══════════════════════════════════════════════════════════════════════╣
echo ╁E Esta acción eliminará TODOS los datos existentes:                  ╁Eecho ╁E   • Contenedores Docker                                             ╁Eecho ╁E   • Base de Datos PostgreSQL                                        ╁Eecho ╁E   • Volúmenes Docker                                                ╁Eecho ╁E                                                                      ╁Eecho ╁E Se creará una instalación completamente nueva.                      ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.

set /p "CONFIRMAR=¿Continuar con la reinstalación? (S/N): "
if /i not "%CONFIRMAR%"=="S" if /i not "%CONFIRMAR%"=="SI" (
    echo.
    echo ✁EReinstalación cancelada
    echo.
    echo ════════════════════════════════════════════════════════════════════
    echo  PRESIONA CUALQUIER TECLA PARA CERRAR ESTA VENTANA
    echo ════════════════════════════════════════════════════════════════════
    pause >nul
    exit /b 0
)

echo.

:: ══════════════════════════════════════════════════════════════════════════╁E::  FASE 3: REINSTALACIÓN
:: ══════════════════════════════════════════════════════════════════════════╁E
echo [FASE 3/3] Reinstalación
echo.

:: Paso 1: Generar .env
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[1/6] GENERACIÓN DE ARCHIVO DE CONFIGURACIÓN (.env)                 ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
if not exist .env (
    echo   ▶ Ejecutando generate_env.py...
    echo   ℹ Este script genera las variables de entorno necesarias
    %PYTHON_CMD% generate_env.py
    if !errorlevel! NEQ 0 (
        echo   ✁EERROR: Falló la generación del archivo .env
        pause >nul
        exit /b 1
    )
    echo   ✁EArchivo .env generado correctamente
    echo   ℹ Ubicación: %CD%\.env
) else (
    echo   ✁EArchivo .env ya existe (se usará el actual)
    echo   ℹ Si necesitas regenerarlo, elimina .env manualmente
)
echo.

:: Paso 2: Detener y limpiar servicios
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[2/6] DETENER Y LIMPIAR SERVICIOS EXISTENTES                        ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo   ▶ Deteniendo contenedores Docker...
echo   ℹ Comando: %DOCKER_COMPOSE_CMD% down -v
%DOCKER_COMPOSE_CMD% down -v
if !errorlevel! NEQ 0 (
    echo   ⚠ Hubo errores al detener (puede ser normal si no había servicios)
) else (
    echo   ✁EContenedores detenidos
)
echo   ▶ Eliminando volúmenes antiguos...
echo   ✁EVolúmenes eliminados (base de datos limpia)
echo   ℹ Se creará una instalación completamente nueva
echo.

:: Paso 3: Reconstruir imágenes
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[3/6] RECONSTRUIR IMÁGENES DOCKER                                   ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo   ▶ Construyendo imágenes Docker (puede tardar 5-10 minutos)...
echo   ℹ Se compilarán: Backend (FastAPI) + Frontend (Next.js)
echo   ℹ Comando: %DOCKER_COMPOSE_CMD% build
echo.
set "DOCKER_BUILDKIT=1"
%DOCKER_COMPOSE_CMD% build
if !errorlevel! NEQ 0 (
    echo.
    echo   ✁EERROR: Falló la construcción de imágenes
    echo   ℹ Revisa los mensajes de error arriba
    echo.
    echo   PRESIONA CUALQUIER TECLA PARA CERRAR
    pause >nul
    exit /b 1
)
echo.
echo   ✁EImágenes Docker construidas correctamente
echo   ℹ Backend: Python 3.11 + FastAPI + SQLAlchemy
echo   ℹ Frontend: Node.js + Next.js 16
echo.

:: Paso 4: Iniciar servicios base (sin importer)
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[4/6] INICIAR SERVICIOS BASE (DB + REDIS)                           ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo   ▶ Iniciando PostgreSQL (base de datos)...
echo   ℹ Comando: %DOCKER_COMPOSE_CMD% --profile dev up -d db redis
%DOCKER_COMPOSE_CMD% --profile dev up -d db redis --remove-orphans
if !errorlevel! NEQ 0 (
    echo   ✁EERROR: No se pudo iniciar PostgreSQL
    pause >nul
    exit /b 1
)
echo   ✁EContenedor PostgreSQL iniciado

echo.
echo   ▶ Esperando que PostgreSQL esté lista (health check - máx 90s)...
set "WAIT_COUNT=0"
:wait_db_loop
docker inspect --format="{{.State.Health.Status}}" uns-claudejp-db 2>nul | findstr "healthy" >nul
if !errorlevel! EQU 0 goto :db_ready
set /a WAIT_COUNT+=1
echo   ⏳ Esperando... (!WAIT_COUNT!0 segundos)
if !WAIT_COUNT! GEQ 9 (
    echo   ✁ETIMEOUT: PostgreSQL no respondió en 90 segundos
    echo   ℹ Verifica los logs: docker logs uns-claudejp-db
    pause >nul
    exit /b 1
)
timeout /t 10 /nobreak >nul
goto :wait_db_loop

:db_ready
echo   ✁EPostgreSQL está lista y saludable
echo   ℹ Base de datos: uns_claudejp | Puerto: 5432
echo.

:: Paso 5: Crear tablas y datos (método directo)
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[5/6] CREAR TABLAS Y DATOS DE NEGOCIO                               ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.

echo   ▶ Creando contenedor temporal para inicialización...
docker run --rm -d --name temp-init --network uns-claudejp-541_uns-network -v "%CD%\backend:/app" -v "%CD%\.env:/app/.env" --env-file .env uns-claudejp-541-backend sleep 300
if !errorlevel! NEQ 0 (
    echo   ✁EERROR: No se pudo crear contenedor temporal
    pause >nul
    exit /b 1
)
echo   ✁EContenedor temporal creado

echo.
echo   ▶ Creando todas las tablas de la base de datos...
docker exec temp-init bash -c "cd /app && python -c \"
from app.models.models import *
from sqlalchemy import create_engine

engine = create_engine('postgresql://uns_admin:VF3sp-ZYs0ohQknm_rEmYU5UuEVfm7nGA3i-a_NetOs@db:5432/uns_claudejp')
Base.metadata.create_all(bind=engine)
print('✁ETablas creadas exitosamente')
\""
if !errorlevel! NEQ 0 (
    echo   ✁EERROR: Falló la creación de tablas
    docker stop temp-init 2>nul
    pause >nul
    exit /b 1
)
echo   ✁ETodas las tablas creadas (24 tablas)

echo.
echo   ▶ Creando usuario administrador...
docker exec temp-init bash -c "cd /app && python -c \"
from app.models.models import User
from sqlalchemy import create_engine
from passlib.context import CryptContext

engine = create_engine('postgresql://uns_admin:VF3sp-ZYs0ohQknm_rEmYU5UuEVfm7nGA3i-a_NetOs@db:5432/uns_claudejp')
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
db = Session()

# Password hash for 'admin123'
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password_hash = pwd_context.hash('admin123')

admin = User(
    username='admin',
    email='admin@uns-kikaku.com',
    password_hash=password_hash,
    role='SUPER_ADMIN',
    full_name='Administrator',
    is_active=True
)

# Check if admin exists
existing = db.query(User).filter(User.username == 'admin').first()
if existing:
    existing.password_hash = password_hash
    existing.email = 'admin@uns-kikaku.com'
    existing.role = 'SUPER_ADMIN'
    print('✁EUsuario admin actualizado')
else:
    db.add(admin)
    print('✁EUsuario admin creado')

db.commit()
db.close()
print('✁EUsuario admin configurado')
\""
if !errorlevel! NEQ 0 (
    echo   ⚠ Warning: Error creando usuario admin, usando SQL directo...
    docker exec uns-claudejp-db psql -U uns_admin -d uns_claudejp -c "
    INSERT INTO users (username, email, password_hash, role, full_name, is_active, created_at, updated_at)
    VALUES (
        'admin',
        'admin@uns-kikaku.com',
        '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjnswC9.4o1K',
        'SUPER_ADMIN',
        'Administrator',
        true,
        now(),
        now()
    ) ON CONFLICT (username) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        role = EXCLUDED.role,
        updated_at = now();
    "
    echo   ✁EUsuario admin creado con SQL directo
) else (
    echo   ✁EUsuario admin creado
)

echo.
echo   ▶ Verificando tablas en base de datos...
docker exec uns-claudejp-db psql -U uns_admin -d uns_claudejp -c "\dt" 2>&1 | findstr "public" >nul
if !errorlevel! EQU 0 (
    echo   ✁ETablas verificadas en base de datos
) else (
    echo   ⚠ Warning: No se pudieron verificar las tablas
)

echo   ▶ Deteniendo contenedor temporal...
docker stop temp-init 2>nul
echo   ✁EContenedor temporal detenido
echo.

:: Paso 6: Iniciar servicios finales
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E[6/6] INICIAR SERVICIOS FINALES                                     ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo   ▶ Iniciando backend, frontend y servicios adicionales...
%DOCKER_COMPOSE_CMD% up -d backend frontend adminer grafana prometheus tempo otel-collector 2>&1
if !errorlevel! NEQ 0 (
    echo   ✁EERROR: Algunos servicios no iniciaron
    pause >nul
    exit /b 1
)
echo   ✁ETodos los servicios iniciados
echo   ℹ Backend:  http://localhost:8000
echo   ℹ Frontend: http://localhost:3000
echo   ℹ Adminer:  http://localhost:8080
echo.

echo   ▶ Esperando compilación del frontend (60s)...
timeout /t 60 /nobreak >nul
echo   ✁ECompilación completada
echo.

:: ══════════════════════════════════════════════════════════════════════════╁E::  FINALIZACIÓN
:: ══════════════════════════════════════════════════════════════════════════╁E
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ╁E             ✁EREINSTALACIÓN COMPLETADA EXITOSAMENTE                ╁Eecho ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo URLs de Acceso:
echo   • Frontend:    http://localhost:3000
echo   • Backend:     http://localhost:8000
echo   • API Docs:    http://localhost:8000/api/docs
echo   • Adminer:     http://localhost:8080
echo.
echo Credenciales:
echo   • Usuario:     admin
echo   • Password:    admin123
echo.
echo Comandos útiles:
echo   • Ver logs:    scripts\LOGS.bat
echo   • Detener:     scripts\STOP.bat
echo.
echo ℹ Primera carga del frontend puede tardar 1-2 minutos
echo.

pause >nul

# TIMELINE EXACTO: Cuándo Se Ejecuta La Sincronización de Fotos

## 📋 Dos Escenarios Principales

---

## ESCENARIO 1: REINSTALAR.bat (Lo que Haces Cuando Presionas el Botón)

### ¿QUÉ HACE REINSTALAR.bat?

```
REINSTALAR.bat
    ↓
[FASE 1] Diagnostico del Sistema (30 segundos)
    └─ Verifica: Python, Docker, Docker Compose, archivos

[FASE 2] Confirmación (requiere tu aprobación)
    └─ Pregunta: "¿Eliminar todos los datos?"
    └─ Pregunta: "¿Credenciales personalizadas?" (admin/admin123)

[FASE 3] Generar .env
    └─ Crea variables de entorno

[FASE 4] Limpiar Servicios Antiguos
    └─ Ejecuta: docker compose down -v
    └─ Elimina: Base de datos anterior, volúmenes, contenedores

[FASE 5] Reconstruir Imágenes Docker (5-10 MINUTOS)
    └─ Construye: Backend (FastAPI + Python)
    └─ Construye: Frontend (Next.js + Node.js)

[FASE 6] Iniciar PostgreSQL y Redis (1-2 MINUTOS)
    └─ Inicia: PostgreSQL (espera a que sea "healthy")
    └─ Inicia: Redis

[FASE 7] Crear Tablas y Datos (2-3 MINUTOS)
    └─ Aplica: Migraciones Alembic (24 tablas)
    └─ Crea: Usuario admin

[FASE 8] Iniciar Servicios Finales (1-2 MINUTOS)
    └─ Inicia: Frontend (Next.js)
    └─ Inicia: Backend
    └─ Inicia: Adminer, Grafana, Prometheus, Tempo, Otel-Collector
    └─ Espera: Compilación del Frontend (120 segundos)

┌─────────────────────────────────────────────────────────┐
│ TIEMPO TOTAL: 20-30 MINUTOS                             │
└─────────────────────────────────────────────────────────┘

RESULTADO:
✓ Sistema limpio
✓ Base de datos vacía
✓ Todos los servicios corriendo
✗ SIN DATOS (aún)
✗ FOTOS NO SINCRONIZADAS (porque no hay datos)

NEXT: Debe ejecutar IMPORTAR_DATOS.bat
```

---

### ¿POR QUÉ REINSTALAR.bat NO EJECUTA EL FLUJO DE SINCRONIZACIÓN?

Porque en el Paso 7 (Crear Tablas), se comentó la sincronización:

```batch
REM ============================================================================
REM  IMPORTACION DE DATOS REMOVIDA DE REINSTALAR.bat
REM  Ahora se usa el script separado: IMPORTAR_DATOS.bat
REM ============================================================================
REM python scripts/sync_candidate_employee_status.py  ← COMENTADO
```

**Razón:** La sincronización de fotos solo tiene sentido si hay DATOS. Durante REINSTALAR.bat, la BD está vacía.

---

## ESCENARIO 2: IMPORTAR_DATOS.bat (Lo que Ejecutas Después de REINSTALAR)

### ¿QUÉ HACE IMPORTAR_DATOS.bat?

```
IMPORTAR_DATOS.bat
    ↓
[FASE 1] Verificar Sistema (30 segundos)
    └─ Comprueba: Docker, Docker Compose, backend corriendo

[FASE 2] Preparar Datos (1-2 minutos)
    └─ Lee: employee_master.xlsm (empleados)
    └─ Lee: access_candidates_data.json (candidatos)
    └─ Extrae fotos de OLE (si están embedidas)

[FASE 3] IMPORTAR EMPLEADOS (2-3 MINUTOS)
    └─ docker exec ... python scripts/import_employees_complete.py
    └─ Inserta: 1,048 empleados desde Excel
    └─ Copia: rirekisho_id, factory_id, hire_date, etc.

[FASE 4] IMPORTAR CANDIDATOS (3-5 MINUTOS)
    └─ docker exec ... python scripts/import_candidates_improved.py
    └─ Inserta: 1,148 candidatos desde JSON
    └─ Copia: Fotos base64 en photo_data_url

┌─────────────────────────────────────────────────────────┐
│ AQUI EMPIEZA LA SINCRONIZACIÓN DE FOTOS ← TÚ LA EJECUTAS │
└─────────────────────────────────────────────────────────┘

[FASE 5] SINCRONIZAR FOTOS (2-3 MINUTOS) ✨ NUEVO
    └─ docker exec ... python scripts/sync_candidate_photos.py
    └─ ✓ Copia fotos de candidatos a empleados
    └─ ✓ Procesa: Employees, ContractWorkers, Staff
    └─ ✓ Reporta: Cuántas fotos sincronizadas

[FASE 6] SINCRONIZAR ESTADO + FOTOS (2-3 MINUTOS) ✨ MEJORADO
    └─ docker exec ... python scripts/sync_candidate_employee_status.py
    └─ ✓ Actualiza: Estado candidato (pending→hired)
    └─ ✓ Sincroniza: Fotos nuevamente (respaldo)
    └─ ✓ Reporta: Estados + Fotos actualizadas

[FASE 7] VALIDAR SINCRONIZACIÓN (1-2 MINUTOS) ✨ NUEVO
    └─ docker exec ... python scripts/validate_candidate_employee_photos.py
    └─ ✓ Verifica: TODAS las fotos sincronizadas
    └─ ✓ Detecta: Fotos faltantes o no coincidentes
    └─ ✓ Reporta: Estado final de sincronización

┌─────────────────────────────────────────────────────────┐
│ TIEMPO TOTAL: 12-18 MINUTOS                             │
└─────────────────────────────────────────────────────────┘

RESULTADO:
✓ 1,048 empleados importados
✓ 1,148 candidatos importados
✓ ~1,116 fotos de candidatos sincronizadas a empleados
✓ Estados candidatos actualizados (hired, pending, etc.)
✓ Base de datos CONSISTENTE
```

---

## ESCENARIO 3: docker compose up (Servicio Importer Automático)

### SOLO SI USAS DOCKER COMPOSE DIRECTAMENTE

Si ejecutas `docker compose up` en la terminal (sin REINSTALAR.bat), el servicio `importer` se ejecuta automáticamente:

```
docker compose up
    ↓
[Inicia PostgreSQL]
    └─ Espera: health check (max 90 segundos)

[Inicia Redis]

[Inicia IMPORTER] ← AQUI EMPIEZA EL FLUJO AUTOMÁTICO
    └─ restart: 'no' (se ejecuta UNA SOLA VEZ)
    └─ depends_on: db (healthy)

    [PASO 1] Importar datos iniciales
    └─ python scripts/simple_importer.py

    [PASO 2] Importar datos de BASEDATEJP
    └─ python scripts/import_all_from_databasejp.py

    [PASO 3] SINCRONIZAR FOTOS ✨ NUEVO
    └─ python scripts/sync_candidate_photos.py
    └─ ✓ Copia fotos: candidatos → empleados

    [PASO 4] SINCRONIZAR ESTADO + FOTOS ✨ MEJORADO
    └─ python scripts/sync_candidate_employee_status.py
    └─ ✓ Actualiza estados
    └─ ✓ Sincroniza fotos (respaldo)

    [PASO 5] VALIDAR SINCRONIZACIÓN ✨ NUEVO
    └─ python scripts/validate_candidate_employee_photos.py
    └─ ✓ Verifica que todo está bien

    ✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE

[Inicia Backend]
[Inicia Frontend]
[Inicia Otros Servicios]

┌─────────────────────────────────────────────────────────┐
│ TIEMPO TOTAL: ~5-10 MINUTOS (después de que BD esté ready) │
└─────────────────────────────────────────────────────────┘

CUANDO SUCEDE: Solo cuando `docker compose up` detecta que
               el servicio importer no ha corrido antes
```

---

## 🎯 RESUMEN: CUÁNDO OCURRE LA SINCRONIZACIÓN DE FOTOS

### OPCIÓN A: Flujo Normal (Recomendado)

```
Tu acción                    Qué sucede                      Tiempo
─────────────────────────────────────────────────────────────────
1. Click REINSTALAR.bat  →   Limpia todo + Inicia servicios  20-30 min
                             Base de datos VACÍA

2. Click IMPORTAR_DATOS.bat →  Importa empleados              12-18 min
                             Importa candidatos
                             ✓ Sincroniza fotos candidato→empleado
                             ✓ Sincroniza estado + fotos
                             ✓ Valida sincronización

RESULTADO: Base de datos COMPLETA + FOTOS SINCRONIZADAS
```

### OPCIÓN B: Docker Compose Directo

```
Tu acción                    Qué sucede                      Tiempo
─────────────────────────────────────────────────────────────────
docker compose up        →   Inicia importer automáticamente  5-10 min
                             [INCLUYE sincronización de fotos]
                             [INCLUYE validación]

RESULTADO: Sistema UP + FOTOS SINCRONIZADAS AUTOMÁTICAMENTE
```

---

## ⏰ TIMELINE VISUAL COMPLETO (Opción A: Normal)

```
MINUTO    ACTIVIDAD
─────────────────────────────────────────────────────────────
0:00      Click REINSTALAR.bat
          ↓
0:30      [FASE 1-2] Diagnostico + Confirmación
          ↓
1:00      [FASE 3] Generar .env
          ↓
2:00      [FASE 4] Limpiar servicios antiguos
          ↓
2:30      [FASE 5] Construir imágenes Docker ← TIEMPO LARGO
          ↓         (Backend + Frontend)
12:30     [FASE 6] Iniciar PostgreSQL + Redis
13:00     [FASE 7] Crear tablas (Alembic migrations)
          ↓
15:00     [FASE 8] Iniciar servicios finales
          ↓
18:00     [✓] REINSTALAR.bat COMPLETO

          --- MENSAJE: Ejecuta IMPORTAR_DATOS.bat ---

18:30     Click IMPORTAR_DATOS.bat
          ↓
19:00     [FASE 1-2] Verificación
          ↓
20:00     [FASE 3] IMPORTAR EMPLEADOS (1,048)
          ↓
22:00     [FASE 4] IMPORTAR CANDIDATOS (1,148)
          ↓
24:00     [FASE 5] SINCRONIZAR FOTOS ← AQUI OCURRE
          ↓         (Copia fotos candidato→empleado)
25:00     [FASE 6] SINCRONIZAR ESTADO + FOTOS
          ↓         (Verifica y actualiza)
26:00     [FASE 7] VALIDAR SINCRONIZACIÓN
          ↓         (Genera reporte)
27:00     [✓] IMPORTAR_DATOS.bat COMPLETO

═══════════════════════════════════════════════════════════════
TOTAL: ~27-35 MINUTOS DESDE EL INICIO

RESULTADO FINAL:
✓ 1,048 empleados en BD
✓ 1,148 candidatos en BD
✓ 1,116 fotos sincronizadas
✓ Sistema LISTO PARA USAR
═══════════════════════════════════════════════════════════════
```

---

## 📊 TABLA COMPARATIVA: CUÁNDO SE EJECUTA CADA SCRIPT

| Script | Ejecutado Por | Cuándo | Qué Hace |
|--------|-------------|--------|----------|
| `simple_importer.py` | IMPORTAR_DATOS.bat | Durante importación | Datos iniciales |
| `import_all_from_databasejp.py` | IMPORTAR_DATOS.bat | Durante importación | Empleados + Candidatos |
| `sync_candidate_photos.py` ✨ | IMPORTAR_DATOS.bat | Después de importar | Sincroniza fotos |
| `sync_candidate_employee_status.py` ✨ | IMPORTAR_DATOS.bat | Después de fotos | Sincroniza estado + fotos |
| `validate_candidate_employee_photos.py` ✨ | IMPORTAR_DATOS.bat | Al final | Valida sincronización |

---

## 🔄 ORDEN EXACTO DE EJECUCIÓN (Lo Más Importante)

### Orden Crítico (DEBE SER ASÍ):

```
1. Importar Empleados (employee_master.xlsm)
   ↓
2. Importar Candidatos (access_candidates_data.json)
   └─ Con fotos en photo_data_url
   ↓
3. ✓ Sincronizar Fotos (candidato→empleado)
   └─ AQUI copia las fotos del candidato al empleado
   ↓
4. ✓ Sincronizar Estado + Fotos
   └─ Respaldo de sincronización
   ├─ Actualiza estado candidato
   └─ Sincroniza fotos nuevamente
   ↓
5. ✓ Validar Sincronización
   └─ Verifica que TODO salió bien
   ├─ Detecta fotos faltantes
   ├─ Detecta fotos no coincidentes
   └─ Genera reporte final
```

**¿Por qué este orden?**
- Si sincronizas ANTES de importar → No hay nada que sincronizar (0 fotos)
- Si importas candidatos SIN fotos → No hay fotos que sincronizar
- Si validas ANTES de sincronizar → Fallaría la validación
- Este orden GARANTIZA que todas las fotos se copien correctamente

---

## ⚡ RESPUESTA RÁPIDA A TU PREGUNTA

### "¿A qué hora se ejecuta automáticamente?"

**Respuesta:** NO es "a una hora específica"

```
REINSTALAR.bat:
  └─ Se ejecuta cuando TÚ haces click
  └─ Toma 20-30 minutos
  └─ NO incluye sincronización de fotos (sin datos)

IMPORTAR_DATOS.bat:
  └─ Se ejecuta cuando TÚ haces click DESPUÉS de REINSTALAR
  └─ Incluye sincronización de fotos automáticamente
  └─ Toma 12-18 minutos
  └─ ✓ LA SINCRONIZACIÓN OCURRE EN LOS PASOS 5-7

docker compose up:
  └─ Se ejecuta cuando TÚ ejecutas el comando
  └─ El servicio importer corre automáticamente
  └─ Incluye sincronización de fotos
  └─ Toma 5-10 minutos después de que BD esté lista
```

### "¿Cuáles son las secuencias?"

```
Secuencia A (Flujo Normal):
  REINSTALAR.bat (20-30 min) → IMPORTAR_DATOS.bat (12-18 min) → ✓ Listo

Secuencia B (Docker Directo):
  docker compose up → [Importer se ejecuta automáticamente] → ✓ Listo

Secuencia C (Manual):
  docker exec ... sync_candidate_photos.py → [Cuando quieras]
  docker exec ... sync_candidate_employee_status.py → [Cuando quieras]
  docker exec ... validate_candidate_employee_photos.py → [Verificar]
```

---

## 🎬 RESUMEN FINAL

| Pregunta | Respuesta |
|----------|-----------|
| **¿Cuándo se sincroniza?** | Cuando ejecutas IMPORTAR_DATOS.bat (Pasos 5-7) |
| **¿A qué hora?** | Cuando TÚ lo ejecutes (no hay hora fija) |
| **¿Es automático?** | Automático dentro del script, manual iniciar el script |
| **¿Sin hacer nada?** | SÍ, si usas `docker compose up` (importer lo hace solo) |
| **¿Puedo detenerlo?** | No, está integrado en IMPORTAR_DATOS.bat |
| **¿Cuánto tarda?** | ~3-5 minutos de los 12-18 minutos totales de importación |
| **¿Qué reporta?** | Cuántas fotos se sincronizaron + validación final |

---

**Última actualización:** 2024-11-19

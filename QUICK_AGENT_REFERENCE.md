# ⚡ QUICK AGENT REFERENCE - Comando Rápido para Invocar Agentes

## 🚀 Invocar un Agente (Formato Simple)

```bash
# Syntax
claude-task <agent-name> --task "<descripción>" --scope "<alcance>" --priority <nivel>

# Ejemplo
claude-task logging-standardization-agent --priority critical
```

---

## 📋 TABLA DE AGENTES RÁPIDA

| # | Agente | Fase | Prioridad | Duración | Comando |
|---|--------|------|-----------|----------|---------|
| 1 | `logging-standardization-agent` | 1 | 🔴 CRITICAL | 2-3h | `claude-task logging-standardization-agent --priority critical` |
| 2 | `assignment-service-refactor-agent` | 1 | 🔴 CRITICAL | 4-6h | `claude-task assignment-service-refactor-agent --source /backend/app/services/assignment_service.py --target-size 20KB` |
| 3 | `yukyu-service-refactor-agent` | 1 | 🔴 CRITICAL | 4-6h | `claude-task yukyu-service-refactor-agent` |
| 4 | `payroll-service-refactor-agent` | 1 | 🔴 CRITICAL | 4-6h | `claude-task payroll-service-refactor-agent` |
| 5 | `capacity-verification-agent` | 1 | 🔴 CRITICAL | 1-2h | `claude-task capacity-verification-agent --file /backend/app/services/apartment_service.py --line 142` |
| 6 | `permission-system-completion-agent` | 1 | 🔴 CRITICAL | 1-2h | `claude-task permission-system-completion-agent --file /backend/app/core/rate_limiter.py --todos 4` |
| 7 | `file-upload-security-agent` | 2 | 🟠 HIGH | 3-4h | `claude-task file-upload-security-agent --target /backend/app/api/candidates.py --validations "mime-type\|file-size\|virus-scan"` |
| 8 | `audit-trail-completion-agent` | 2 | 🟠 HIGH | 3-4h | `claude-task audit-trail-completion-agent --database postgresql` |
| 9 | `secrets-management-agent` | 2 | 🟠 HIGH | 2-3h | `claude-task secrets-management-agent --audit-scope "all .env usage"` |
| 10 | `database-indexing-agent` | 2 | 🟠 HIGH | 3-4h | `claude-task database-indexing-agent --database postgresql --create-indexes "composite\|partial"` |
| 11 | `ocr-parallelization-agent` | 2 | 🟠 HIGH | 4-6h | `claude-task ocr-parallelization-agent --current-latency "5-10s" --target-latency "1-2s"` |
| 12 | `n-plus-one-query-agent` | 2 | 🟠 HIGH | 3-4h | `claude-task n-plus-one-query-agent --scope "all endpoints"` |
| 13 | `frontend-code-splitting-agent` | 2 | 🟠 HIGH | 3-4h | `claude-task frontend-code-splitting-agent --framework "next.js" --target-reduction "20%"` |
| 14 | `state-management-consistency-agent` | 2 | 🟠 HIGH | 2-3h | `claude-task state-management-consistency-agent --framework "zustand"` |
| 15 | `integration-test-agent` | 3 | 🟡 MEDIUM | 4-5h | `claude-task integration-test-agent --workflows "candidate-to-employee\|payroll-calculation"` |
| 16 | `ocr-integration-test-agent` | 3 | 🟡 MEDIUM | 3-4h | `claude-task ocr-integration-test-agent --providers "azure\|gemini\|easyocr"` |
| 17 | `e2e-expansion-agent` | 3 | 🟡 MEDIUM | 4-5h | `claude-task e2e-expansion-agent --framework "playwright" --test-journeys 15` |
| 18 | `api-documentation-agent` | 3 | 🟡 MEDIUM | 2-3h | `claude-task api-documentation-agent --generate "openapi\|postman"` |
| 19 | `changelog-generator-agent` | 3 | 🟡 MEDIUM | 1-2h | `claude-task changelog-generator-agent --analyze-commits` |
| 20 | `websocket-notifications-agent` | 3 | 🟡 MEDIUM | 4-5h | `claude-task websocket-notifications-agent --framework "fastapi-websockets"` |
| 21 | `advanced-analytics-agent` | 4 | 🔵 NICE-TO-HAVE | 5-6h | `claude-task advanced-analytics-agent --dashboards "payroll\|hiring\|retention"` |
| 22 | `reporting-engine-agent` | 4 | 🔵 NICE-TO-HAVE | 5-6h | `claude-task reporting-engine-agent --features "scheduled\|pdf\|email"` |
| 23 | `multi-language-support-agent` | 4 | 🔵 NICE-TO-HAVE | 6-8h | `claude-task multi-language-support-agent --languages "EN\|JA\|ES"` |
| 24 | `monitoring-observability-agent` | 4 | 🔵 NICE-TO-HAVE | 5-6h | `claude-task monitoring-observability-agent --stack "opentelemetry\|prometheus\|grafana"` |
| 25 | `backup-recovery-agent` | 4 | 🔵 NICE-TO-HAVE | 3-4h | `claude-task backup-recovery-agent --automation "daily\|weekly"` |

---

## 🎯 EJECUCIÓN RECOMENDADA

### Día 1: LOGGING (Bloquea el resto)
```bash
# 1. DEBE ejecutarse primero
claude-task logging-standardization-agent --priority critical

# Espera a que se complete ✅
# Resultado: Logging estructurado en toda la app
```

### Días 2-3: REFACTORING + TODOS (Paralelo, pero después de logging)
```bash
# Ejecutar en paralelo (después de logging completar)
claude-task assignment-service-refactor-agent &
claude-task yukyu-service-refactor-agent &
claude-task payroll-service-refactor-agent &
claude-task capacity-verification-agent &
claude-task permission-system-completion-agent

# Espera a todos completar
wait
```

### Días 4-5: SEGURIDAD + PERFORMANCE (Paralelo)
```bash
# Ejecutar en paralelo
claude-task file-upload-security-agent &
claude-task audit-trail-completion-agent &
claude-task secrets-management-agent &
claude-task database-indexing-agent &
claude-task ocr-parallelization-agent &
claude-task n-plus-one-query-agent &
claude-task frontend-code-splitting-agent &
claude-task state-management-consistency-agent

wait
```

### Días 6-8: TESTING + DOCUMENTACIÓN (Paralelo)
```bash
# Ejecutar en paralelo
claude-task integration-test-agent &
claude-task ocr-integration-test-agent &
claude-task e2e-expansion-agent &
claude-task api-documentation-agent &
claude-task changelog-generator-agent &
claude-task websocket-notifications-agent

wait
```

### Días 9+: NICE-TO-HAVE (Secuencial)
```bash
# Ejecutar en orden
claude-task advanced-analytics-agent
claude-task reporting-engine-agent
claude-task multi-language-support-agent
claude-task monitoring-observability-agent
claude-task backup-recovery-agent
```

---

## 🔍 VERIFICAR PROGRESO

```bash
# Después de Fase 1
✅ git log --oneline | head -10  # Ver commits
✅ pytest /backend/tests -q       # Tests pasando
✅ grep -r "print(" /backend/app | grep -v test | wc -l  # Should be 0

# Después de Fase 2
✅ find /backend/app/services -name "*.py" -exec wc -l {} \; | sort -rn
✅ # Todos < 600 lines (< 25KB)

# Después de Fase 3
✅ pytest /backend/tests/integration -v
✅ cd frontend && npm run build  # Check bundle size
```

---

## 🚨 SI ALGO VA MAL

```bash
# Revertir último agente
git reset --hard HEAD~1

# Ver qué pasó
git diff HEAD~1 HEAD

# Crear issue
# Re-ejecutar agente con fixes
```

---

## 📊 RESUMEN RÁPIDO

**Total Agentes**: 25
**Tiempo Estimado**:
- Fase 1: 2 días
- Fase 2: 2-3 días
- Fase 3: 2-3 días
- Fase 4: 1+ semana

**Total**: ~8-12 semanas (siguiendo el plan)

**Impacto Esperado**:
- ✅ 100+ mejoras de código
- ✅ 30-50% mejora de performance
- ✅ 95%+ test coverage
- ✅ Cero deuda técnica en áreas críticas
- ✅ Monitoreo completo

---

## 📖 DOCUMENTACIÓN COMPLETA

Para más detalles:
- **AGENT_ORCHESTRATION_PLAN.md** - Plan completo de 25 agentes
- **AGENT_EXECUTION_GUIDE.md** - Guía detallada paso-a-paso
- **COMPREHENSIVE_ANALYSIS_DETAILED.md** - Análisis técnico completo

---

## 🎬 COMENZAR AHORA

```bash
# Step 1: Leer el plan
cat AGENT_ORCHESTRATION_PLAN.md

# Step 2: Ejecutar Fase 1
claude-task logging-standardization-agent --priority critical

# Step 3: Monitorear
git status
pytest /backend/tests -q

# Step 4: Proceder a siguiente agente
# (Ver AGENT_EXECUTION_GUIDE.md para próximos pasos)
```

---

**Preguntas?** Revisa AGENT_EXECUTION_GUIDE.md o el plan detallado. 🚀

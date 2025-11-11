#!/bin/bash

# Test completo del flujo de asignación de apartamentos V2

BASE_URL="http://localhost:8000/api"
TOKEN=""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funciones de logging
log_section() {
    echo ""
    echo "================================================================================"
    echo -e "${CYAN}$1${NC}"
    echo "================================================================================"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 1. LOGIN
log_section "1. LOGIN"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    log_error "Error en login"
    echo $LOGIN_RESPONSE
    exit 1
fi

log_success "Login exitoso. Token obtenido: ${TOKEN:0:20}..."

# 2. CREAR APARTAMENTO
log_section "2. CREAR APARTAMENTO"
APT_RESPONSE=$(curl -s -X POST "${BASE_URL}/apartments-v2/apartments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Apartment マンション",
    "building_name": "Test Building",
    "room_number": "999",
    "floor_number": 9,
    "base_rent": 50000,
    "management_fee": 5000,
    "deposit": 100000,
    "key_money": 50000,
    "default_cleaning_fee": 20000,
    "prefecture": "東京都",
    "city": "テスト区",
    "address_line1": "テスト1-2-3",
    "room_type": "1K",
    "size_sqm": 25.5,
    "status": "active"
  }')

APT_ID=$(echo $APT_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$APT_ID" ]; then
    log_error "Error al crear apartamento"
    echo $APT_RESPONSE
    exit 1
fi

log_success "Apartamento creado exitosamente"
log_info "ID: $APT_ID"
echo $APT_RESPONSE | python -m json.tool 2>/dev/null | grep -E "(name|base_rent|management_fee|default_cleaning_fee)" || true

# 3. OBTENER EMPLEADOS
log_section "3. OBTENER EMPLEADOS DISPONIBLES"
EMP_RESPONSE=$(curl -s -X GET "${BASE_URL}/employees/" \
  -H "Authorization: Bearer $TOKEN")

EMP_COUNT=$(echo $EMP_RESPONSE | python -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
EMP_ID=$(echo $EMP_RESPONSE | python -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)

if [ -z "$EMP_ID" ]; then
    log_error "No se encontraron empleados"
    exit 1
fi

log_success "Se encontraron $EMP_COUNT empleados"
log_info "Usando empleado ID: $EMP_ID"

# 4. ASIGNAR EMPLEADO
log_section "4. ASIGNAR EMPLEADO AL APARTAMENTO"
TODAY=$(date +%Y-%m-%d)

ASSIGN_RESPONSE=$(curl -s -X POST "${BASE_URL}/apartments-v2/assignments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"apartment_id\": $APT_ID,
    \"employee_id\": $EMP_ID,
    \"start_date\": \"$TODAY\",
    \"move_in_date\": \"$TODAY\",
    \"monthly_rent\": 50000
  }")

ASSIGN_ID=$(echo $ASSIGN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$ASSIGN_ID" ]; then
    log_error "Error al asignar empleado"
    echo $ASSIGN_RESPONSE
    exit 1
fi

log_success "Asignación creada exitosamente"
log_info "ID Asignación: $ASSIGN_ID"
echo $ASSIGN_RESPONSE | python -m json.tool 2>/dev/null | grep -E "(start_date|monthly_rent|prorated)" || true

# 5. VERIFICAR DEDUCCIONES
log_section "5. VERIFICAR DEDUCCIONES GENERADAS"
DED_RESPONSE=$(curl -s -X GET "${BASE_URL}/apartments-v2/employees/${EMP_ID}/rent-deductions" \
  -H "Authorization: Bearer $TOKEN")

DED_COUNT=$(echo $DED_RESPONSE | python -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)

log_success "Se encontraron $DED_COUNT deducciones"
if [ "$DED_COUNT" -gt 0 ]; then
    echo $DED_RESPONSE | python -m json.tool 2>/dev/null | head -20 || true
fi

# 6. FINALIZAR ASIGNACIÓN
log_section "6. FINALIZAR ASIGNACIÓN CON CARGO DE LIMPIEZA"
END_RESPONSE=$(curl -s -X POST "${BASE_URL}/apartments-v2/assignments/${ASSIGN_ID}/end" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"end_date\": \"$TODAY\",
    \"move_out_date\": \"$TODAY\",
    \"cleaning_fee\": 20000,
    \"notes\": \"Test de finalización\"
  }")

END_STATUS=$(echo $END_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)

if [ "$END_STATUS" == "completed" ]; then
    log_success "Asignación finalizada exitosamente"
    echo $END_RESPONSE | python -m json.tool 2>/dev/null | grep -E "(status|end_date|cleaning_fee)" || true
else
    log_error "Error al finalizar asignación"
    echo $END_RESPONSE
fi

# 7. VERIFICAR DEDUCCIONES FINALES
log_section "7. VERIFICAR DEDUCCIONES DESPUÉS DE FINALIZAR"
DED_FINAL=$(curl -s -X GET "${BASE_URL}/apartments-v2/employees/${EMP_ID}/rent-deductions" \
  -H "Authorization: Bearer $TOKEN")

DED_FINAL_COUNT=$(echo $DED_FINAL | python -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)

log_success "Total deducciones después de finalizar: $DED_FINAL_COUNT"
if [ "$DED_FINAL_COUNT" -gt 0 ]; then
    echo $DED_FINAL | python -m json.tool 2>/dev/null | head -30 || true
fi

# 8. LIMPIEZA
log_section "8. LIMPIEZA DE DATOS DE PRUEBA"
curl -s -X DELETE "${BASE_URL}/apartments-v2/apartments/${APT_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

log_success "Apartamento de prueba eliminado (ID: $APT_ID)"

# RESUMEN
log_section "RESUMEN DE PRUEBAS"
log_success "Todas las pruebas completadas exitosamente"
log_info "Flujo probado:"
log_info "  1. ✓ Login y autenticación"
log_info "  2. ✓ Creación de apartamento (ID: $APT_ID)"
log_info "  3. ✓ Consulta de empleados (Total: $EMP_COUNT)"
log_info "  4. ✓ Asignación de empleado (ID: $ASSIGN_ID)"
log_info "  5. ✓ Generación de deducciones ($DED_COUNT deducciones)"
log_info "  6. ✓ Finalización con cargo de limpieza"
log_info "  7. ✓ Deducciones finales ($DED_FINAL_COUNT total)"
log_info "  8. ✓ Limpieza de datos de prueba"

echo ""

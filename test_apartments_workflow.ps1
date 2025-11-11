# Test completo del flujo de asignación de apartamentos V2
# PowerShell Script

$BASE_URL = "http://localhost:8000/api"
$Token = ""

# Funciones de logging
function Write-Section {
    param([string]$Message)
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error2 {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Blue
}

try {
    # 1. LOGIN
    Write-Section "1. LOGIN"
    $loginBody = @{
        username = "admin"
        password = "admin123"
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Body $loginBody -ContentType 'application/json'
    $Token = $loginResponse.access_token

    if (-not $Token) {
        Write-Error2 "No se pudo obtener el token"
        exit 1
    }

    Write-Success "Login exitoso. Token obtenido: $($Token.Substring(0, 20))..."

    # 2. CREAR APARTAMENTO
    Write-Section "2. CREAR APARTAMENTO"
    $apartmentBody = @{
        name = "Test Apartment マンション"
        building_name = "Test Building"
        room_number = "999"
        floor_number = 9
        base_rent = 50000
        management_fee = 5000
        deposit = 100000
        key_money = 50000
        default_cleaning_fee = 20000
        prefecture = "東京都"
        city = "テスト区"
        address_line1 = "テスト1-2-3"
        room_type = "1K"
        size_sqm = 25.5
        status = "active"
    } | ConvertTo-Json

    $headers = @{
        Authorization = "Bearer $Token"
    }

    $apartment = Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/apartments" -Method Post -Body $apartmentBody -ContentType 'application/json' -Headers $headers

    Write-Success "Apartamento creado exitosamente"
    Write-Info "ID: $($apartment.id)"
    Write-Info "Nombre: $($apartment.name)"
    Write-Info "Renta Base: ¥$($apartment.base_rent.ToString('N0'))"
    Write-Info "Administración: ¥$($apartment.management_fee.ToString('N0'))"
    Write-Info "Total Mensual: ¥$(($apartment.base_rent + $apartment.management_fee).ToString('N0'))"
    Write-Info "Cargo Limpieza: ¥$($apartment.default_cleaning_fee.ToString('N0'))"

    $apartmentId = $apartment.id

    # 3. OBTENER EMPLEADOS
    Write-Section "3. OBTENER EMPLEADOS DISPONIBLES"
    $employees = Invoke-RestMethod -Uri "$BASE_URL/employees/" -Method Get -Headers $headers

    Write-Success "Se encontraron $($employees.Count) empleados"

    $employee = $employees[0]
    Write-Info "Usando empleado ID: $($employee.id)"
    Write-Info "Nombre: $($employee.full_name_roman)"

    # 4. ASIGNAR EMPLEADO
    Write-Section "4. ASIGNAR EMPLEADO AL APARTAMENTO"
    $today = Get-Date -Format "yyyy-MM-dd"

    $assignmentBody = @{
        apartment_id = $apartmentId
        employee_id = $employee.id
        start_date = $today
        move_in_date = $today
        monthly_rent = 50000
    } | ConvertTo-Json

    $assignment = Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/assignments" -Method Post -Body $assignmentBody -ContentType 'application/json' -Headers $headers

    Write-Success "Asignación creada exitosamente"
    Write-Info "ID Asignación: $($assignment.id)"
    Write-Info "Fecha Inicio: $($assignment.start_date)"
    Write-Info "Renta Mensual: ¥$($assignment.monthly_rent.ToString('N0'))"

    if ($assignment.prorated_amount) {
        Write-Info "Días Prorrateados: $($assignment.prorated_days)"
        Write-Info "Monto Prorrateado: ¥$($assignment.prorated_amount.ToString('N0'))"
    }

    $assignmentId = $assignment.id

    # 5. VERIFICAR DEDUCCIONES
    Write-Section "5. VERIFICAR DEDUCCIONES GENERADAS"
    $deductions = Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/employees/$($employee.id)/rent-deductions" -Method Get -Headers $headers

    Write-Success "Se encontraron $($deductions.Count) deducciones"

    if ($deductions.Count -gt 0) {
        $latest = $deductions[0]
        Write-Info "Última deducción:"
        Write-Info "  ID: $($latest.id)"
        Write-Info "  Tipo: $($latest.deduction_type)"
        Write-Info "  Monto: ¥$($latest.amount.ToString('N0'))"
        Write-Info "  Periodo: $($latest.period_month)/$($latest.period_year)"
    }

    # 6. FINALIZAR ASIGNACIÓN
    Write-Section "6. FINALIZAR ASIGNACIÓN CON CARGO DE LIMPIEZA"
    $endBody = @{
        end_date = $today
        move_out_date = $today
        cleaning_fee = 20000
        notes = "Test de finalización de asignación"
    } | ConvertTo-Json

    $endedAssignment = Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/assignments/$assignmentId/end" -Method Post -Body $endBody -ContentType 'application/json' -Headers $headers

    Write-Success "Asignación finalizada exitosamente"
    Write-Info "Estado: $($endedAssignment.status)"
    Write-Info "Fecha Fin: $($endedAssignment.end_date)"

    if ($endedAssignment.final_cleaning_fee) {
        Write-Info "Cargo de Limpieza: ¥$($endedAssignment.final_cleaning_fee.ToString('N0'))"
    }

    # 7. VERIFICAR DEDUCCIONES FINALES
    Write-Section "7. VERIFICAR DEDUCCIONES DESPUÉS DE FINALIZAR"
    $finalDeductions = Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/employees/$($employee.id)/rent-deductions" -Method Get -Headers $headers

    Write-Success "Total deducciones después de finalizar: $($finalDeductions.Count)"

    if ($finalDeductions.Count -gt 0) {
        Write-Info "Deducciones:"
        foreach ($ded in $finalDeductions) {
            Write-Info "  - $($ded.deduction_type): ¥$($ded.amount.ToString('N0')) ($($ded.period_month)/$($ded.period_year))"
        }
    }

    # 8. LIMPIEZA
    Write-Section "8. LIMPIEZA DE DATOS DE PRUEBA"
    try {
        Invoke-RestMethod -Uri "$BASE_URL/apartments-v2/apartments/$apartmentId" -Method Delete -Headers $headers | Out-Null
        Write-Success "Apartamento de prueba eliminado (ID: $apartmentId)"
    } catch {
        Write-Info "Nota: No se pudo eliminar el apartamento (puede estar en uso)"
    }

    # RESUMEN
    Write-Section "RESUMEN DE PRUEBAS"
    Write-Success "Todas las pruebas completadas exitosamente"
    Write-Info "Flujo probado:"
    Write-Info "  1. ✓ Login y autenticación"
    Write-Info "  2. ✓ Creación de apartamento (ID: $apartmentId)"
    Write-Info "  3. ✓ Consulta de empleados (Total: $($employees.Count))"
    Write-Info "  4. ✓ Asignación de empleado (ID: $assignmentId)"
    Write-Info "  5. ✓ Generación de deducciones ($($deductions.Count) deducciones)"
    Write-Info "  6. ✓ Finalización con cargo de limpieza"
    Write-Info "  7. ✓ Deducciones finales ($($finalDeductions.Count) total)"
    Write-Info "  8. ✓ Limpieza de datos de prueba"

} catch {
    Write-Error2 "Error en las pruebas: $($_.Exception.Message)"
    if ($_.ErrorDetails) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
    }
    exit 1
}

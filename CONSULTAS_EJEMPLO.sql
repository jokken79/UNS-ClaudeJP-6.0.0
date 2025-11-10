-- CONSULTAS DE EJEMPLO - SISTEMA SHATAKU

-- 1. Buscar apartamentos disponibles
SELECT a.*, 
       a.capacity - COUNT(aa.id) as available_slots
FROM apartments a
LEFT JOIN apartment_assignments aa ON a.id = aa.apartment_id AND aa.status = 'ACTIVE'
WHERE a.is_available = true
GROUP BY a.id, a.capacity
HAVING COUNT(aa.id) < a.capacity;

-- 2. Costo total por empleado
SELECT e.full_name_kanji, a.apartment_code,
       aa.monthly_rent,
       COALESCE(SUM(rd.amount), 0) as additional_charges,
       aa.monthly_rent + COALESCE(SUM(rd.amount), 0) as total_cost
FROM employees e
JOIN apartment_assignments aa ON e.id = aa.employee_id AND aa.status = 'ACTIVE'
JOIN apartments a ON aa.apartment_id = a.id
LEFT JOIN rent_deductions rd ON aa.id = rd.assignment_id AND rd.is_active = true
GROUP BY e.full_name_kanji, a.apartment_code, aa.monthly_rent;

-- 3. Historial de asignaciones
SELECT aa.assignment_date, a.apartment_code, aa.status
FROM apartment_assignments aa
JOIN apartments a ON aa.apartment_id = a.id
WHERE aa.employee_id = 1
ORDER BY aa.assignment_date DESC;

-- 4. Dashboard de ocupacion
SELECT a.building_type, a.prefecture,
       COUNT(a.id) as total_apartments,
       COUNT(aa.id) as occupied,
       ROUND(COUNT(aa.id) * 100.0 / COUNT(a.id), 2) as occupancy_rate
FROM apartments a
LEFT JOIN apartment_assignments aa ON a.id = aa.apartment_id AND aa.status = 'ACTIVE'
GROUP BY a.building_type, a.prefecture;

-- 5. Alertas de renovacion
SELECT a.apartment_code, a.contract_end_date,
       (a.contract_end_date - CURRENT_DATE) as days_remaining
FROM apartments a
WHERE a.contract_end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days';

-- 6. Resumen por apartamento
SELECT a.apartment_code, a.capacity,
       COUNT(aa.id) as current_occupants,
       SUM(aa.monthly_rent) as total_rent
FROM apartments a
LEFT JOIN apartment_assignments aa ON a.id = aa.apartment_id AND aa.status = 'ACTIVE'
GROUP BY a.id, a.apartment_code, a.capacity;

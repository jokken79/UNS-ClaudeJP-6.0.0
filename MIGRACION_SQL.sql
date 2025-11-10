-- MIGRACION SISTEMA SHATAKU 2025-11-10

-- 1. CREAR TABLAS
CREATE TABLE additional_charges (
    id SERIAL PRIMARY KEY,
    charge_name VARCHAR(100) NOT NULL,
    charge_type VARCHAR(30) NOT NULL,
    calculation_type VARCHAR(20) NOT NULL,
    base_amount INTEGER,
    due_day_of_month INTEGER DEFAULT 25,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE apartment_assignments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id),
    apartment_id INTEGER REFERENCES apartments(id),
    status VARCHAR(20) NOT NULL,
    start_date DATE,
    end_date DATE,
    monthly_rent INTEGER NOT NULL,
    payment_method VARCHAR(30) DEFAULT 'SALARY_DEDUCTION',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE rent_deductions (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER REFERENCES apartment_assignments(id),
    charge_id INTEGER REFERENCES additional_charges(id),
    amount INTEGER NOT NULL,
    deduction_type VARCHAR(20) DEFAULT 'SALARY_DEDUCTION',
    is_active BOOLEAN DEFAULT true
);

-- 2. INSERTAR DATOS
INSERT INTO additional_charges VALUES
(1, 'Electricity', 'UTILITY', 'VOLUME_BASED', NULL, 25, true),
(2, 'Gas', 'UTILITY', 'VOLUME_BASED', NULL, 25, true),
(3, 'Water', 'UTILITY', 'FIXED', 2000, 25, true),
(4, 'Internet', 'SERVICE', 'FIXED', 5000, 25, true),
(5, 'Management Fee', 'FEE', 'FIXED', 3000, 25, true);

-- 3. MIGRAR ASIGNACIONES
INSERT INTO apartment_assignments (employee_id, apartment_id, status, start_date, monthly_rent)
SELECT e.id, e.apartment_id, 'ACTIVE', e.apartment_start_date, e.apartment_rent
FROM employees e WHERE e.apartment_id IS NOT NULL;

-- 4. CREAR INDICES
CREATE INDEX idx_assignments_emp ON apartment_assignments(employee_id);
CREATE INDEX idx_assignments_apt ON apartment_assignments(apartment_id);
CREATE INDEX idx_deductions_assign ON rent_deductions(assignment_id);

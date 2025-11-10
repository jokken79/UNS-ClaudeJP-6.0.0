-- ================================================================
-- MIGRACIÓN DE DATOS - SISTEMA DE 社宅 (Shataku/Apartamentos)
-- Fecha: 2025-11-10
-- Versión: 5.4.1
-- ================================================================

-- FASE 1: BACKUP DE DATOS EXISTENTES
CREATE TABLE apartments_backup AS SELECT * FROM apartments;
CREATE TABLE employees_apartment_backup AS SELECT 
    id, apartment_id, apartment_start_date, apartment_move_out_date,
    apartment_rent, apartment_deduction, is_corporate_housing
FROM employees WHERE apartment_id IS NOT NULL;

-- FASE 2: CREAR NUEVAS TABLAS

-- 1. additional_charges
CREATE TABLE IF NOT EXISTS additional_charges (
    id SERIAL PRIMARY KEY,
    charge_name VARCHAR(100) NOT NULL,
    charge_name_en VARCHAR(100),
    charge_type VARCHAR(30) NOT NULL,
    description TEXT,
    calculation_type VARCHAR(20) NOT NULL,
    unit_type VARCHAR(20),
    base_amount INTEGER,
    min_amount INTEGER,
    max_amount INTEGER,
    due_day_of_month INTEGER DEFAULT 25,
    is_mandatory BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. apartment_assignments
CREATE TABLE IF NOT EXISTS apartment_assignments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    apartment_id INTEGER REFERENCES apartments(id) ON DELETE CASCADE,
    assignment_type VARCHAR(20) NOT NULL DEFAULT 'PRIMARY',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    assignment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_date DATE,
    end_date DATE,
    move_in_date DATE,
    move_out_date DATE,
    monthly_rent INTEGER NOT NULL DEFAULT 0,
    rent_currency VARCHAR(3) DEFAULT 'JPY',
    payment_method VARCHAR(30) DEFAULT 'SALARY_DEDUCTION',
    company_subsidy INTEGER DEFAULT 0,
    employee_contribution INTEGER,
    contract_signed BOOLEAN DEFAULT false,
    contract_signed_date DATE,
    contract_document_path VARCHAR(500),
    room_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    CONSTRAINT valid_assignment_dates CHECK (start_date <= end_date OR end_date IS NULL),
    CONSTRAINT valid_payment CHECK (employee_contribution >= 0 AND company_subsidy >= 0)
);

-- 3. rent_deductions
CREATE TABLE IF NOT EXISTS rent_deductions (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES apartment_assignments(id) ON DELETE CASCADE,
    charge_id INTEGER NOT NULL REFERENCES additional_charges(id),
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    amount INTEGER NOT NULL DEFAULT 0,
    amount_type VARCHAR(20) NOT NULL DEFAULT 'FIXED',
    deduction_type VARCHAR(20) NOT NULL DEFAULT 'SALARY_DEDUCTION',
    last_reading_date DATE,
    last_reading_value DECIMAL(10,2),
    rate_per_unit DECIMAL(8,2),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    CONSTRAINT valid_deduction_dates CHECK (effective_date <= end_date OR end_date IS NULL),
    CONSTRAINT positive_amount CHECK (amount > 0)
);

-- FASE 3: INSERTAR DATOS INICIALES
INSERT INTO additional_charges (charge_name, charge_name_en, charge_type, calculation_type, unit_type, base_amount, due_day_of_month) 
VALUES 
    ('電気代', 'Electricity', 'UTILITY', 'VOLUME_BASED', 'KWH', NULL, 25),
    ('ガス代', 'Gas', 'UTILITY', 'VOLUME_BASED', 'CUBIC_METER', NULL, 25),
    ('水道代', 'Water', 'UTILITY', 'FIXED', 'MONTH', 2000, 25),
    ('インターネット代', 'Internet', 'SERVICE', 'FIXED', 'MONTH', 5000, 25),
    ('管理費', 'Management Fee', 'FEE', 'FIXED', 'MONTH', 3000, 25),
    ('駐車場代', 'Parking', 'SERVICE', 'FIXED', 'MONTH', 5000, 25)
ON CONFLICT DO NOTHING;

-- FASE 4: MIGRAR ASIGNACIONES
INSERT INTO apartment_assignments (
    employee_id, apartment_id, assignment_type, status,
    assignment_date, start_date, end_date,
    monthly_rent, payment_method, created_at
)
SELECT 
    e.id, e.apartment_id, 'PRIMARY',
    CASE 
        WHEN e.apartment_start_date IS NOT NULL AND e.apartment_move_out_date IS NULL THEN 'ACTIVE'
        WHEN e.apartment_move_out_date IS NOT NULL THEN 'TERMINATED'
        ELSE 'PENDING'
    END,
    COALESCE(e.apartment_start_date, e.hire_date, CURRENT_DATE),
    e.apartment_start_date, e.apartment_move_out_date,
    COALESCE(e.apartment_rent, a.monthly_rent, 0),
    'SALARY_DEDUCTION', NOW()
FROM employees e
JOIN apartments a ON e.apartment_id = a.id
WHERE e.apartment_id IS NOT NULL;

-- Crear deducciones básicas
INSERT INTO rent_deductions (assignment_id, charge_id, effective_date, amount, amount_type, deduction_type, is_active)
SELECT 
    aa.id, ac.id, COALESCE(aa.start_date, CURRENT_DATE),
    COALESCE(ac.base_amount, 0), 'FIXED', 'SALARY_DEDUCTION',
    CASE WHEN aa.status = 'ACTIVE' THEN true ELSE false END
FROM apartment_assignments aa
CROSS JOIN additional_charges ac
WHERE aa.status = 'ACTIVE' AND ac.is_active = true AND ac.base_amount > 0;

-- FASE 5: CREAR ÍNDICES
CREATE INDEX idx_assignments_employee ON apartment_assignments(employee_id);
CREATE INDEX idx_assignments_apartment ON apartment_assignments(apartment_id);
CREATE INDEX idx_deductions_assignment ON rent_deductions(assignment_id);
CREATE INDEX idx_deductions_active ON rent_deductions(is_active) WHERE is_active = true;

-- FASE 6: CREAR TRIGGERS
CREATE OR REPLACE FUNCTION check_apartment_capacity()
RETURNS TRIGGER AS $$
DECLARE
    current_occupants INTEGER;
    max_capacity INTEGER;
BEGIN
    IF NEW.status = 'ACTIVE' THEN
        SELECT capacity INTO max_capacity FROM apartments WHERE id = NEW.apartment_id;
        SELECT COUNT(*) INTO current_occupants
        FROM apartment_assignments
        WHERE apartment_id = NEW.apartment_id AND status = 'ACTIVE'
        AND id != COALESCE(NEW.id, 0);
        
        IF current_occupants >= max_capacity THEN
            RAISE EXCEPTION 'Apartment capacity exceeded';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_capacity
    BEFORE INSERT OR UPDATE ON apartment_assignments
    FOR EACH ROW
    EXECUTE FUNCTION check_apartment_capacity();

-- VALIDACIÓN
SELECT 
    'MIGRACIÓN COMPLETADA' as status,
    CURRENT_TIMESTAMP as timestamp,
    (SELECT COUNT(*) FROM apartment_assignments) as total_assignments;

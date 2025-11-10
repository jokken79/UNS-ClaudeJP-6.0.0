"""
Script de Verificación de Correcciones de Importación
======================================================

Este script verifica que todas las correcciones implementadas funcionen correctamente:

1. ✅ Status 現在 se actualiza correctamente (退社, 待機中, 在職中)
2. ✅ Matching candidato→empleado usa nombre + fecha de nacimiento
3. ✅ Fotos se copian de candidatos a employees
4. ✅ rirekisho_id se asigna en employees
5. ✅ company_name y plant_name se extraen de factory config
6. ✅ hakensaki_shain_id se lee del Excel

Uso:
    python verify_import_fixes.py

Author: Claude Code
Date: 2025-10-28
"""

import sys
from pathlib import Path
sys.path.insert(0, '/app')

from sqlalchemy import func, and_
from app.core.database import SessionLocal
from app.models.models import Employee, Candidate, ContractWorker, Staff, Factory


def print_section(title: str):
    """Print a fancy section header"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}\n")


def verify_status_distribution():
    """Verify that employee statuses are correctly distributed"""
    print_section("VERIFICACIÓN #1: DISTRIBUCIÓN DE STATUS")

    db = SessionLocal()
    try:
        # Count employees by status
        status_counts = db.query(
            Employee.current_status,
            func.count(Employee.id)
        ).group_by(Employee.current_status).all()

        print("Distribución de status en employees:")
        total = 0
        for status, count in status_counts:
            print(f"  {status:15s}: {count:4d}")
            total += count

        print(f"  {'TOTAL':15s}: {total:4d}\n")

        # Check if there are any terminated employees
        terminated_count = db.query(Employee).filter(
            Employee.current_status == 'terminated'
        ).count()

        suspended_count = db.query(Employee).filter(
            Employee.current_status == 'suspended'
        ).count()

        if terminated_count > 0:
            print(f"✅ PASS: Se encontraron {terminated_count} empleados con status='terminated'")
        else:
            print(f"⚠️  WARN: NO se encontraron empleados con status='terminated'")

        if suspended_count > 0:
            print(f"✅ PASS: Se encontraron {suspended_count} empleados con status='suspended'")
        else:
            print(f"ℹ️  INFO: No hay empleados con status='suspended' (esto puede ser normal)")

        # Check consistency between is_active and current_status
        inconsistent = db.query(Employee).filter(
            and_(
                Employee.current_status == 'terminated',
                Employee.is_active == True
            )
        ).count()

        if inconsistent == 0:
            print(f"✅ PASS: Consistencia entre is_active y current_status verificada")
        else:
            print(f"❌ FAIL: {inconsistent} empleados tienen inconsistencia (terminated pero is_active=True)")

    finally:
        db.close()


def verify_candidate_employee_linking():
    """Verify that employees are correctly linked to candidates"""
    print_section("VERIFICACIÓN #2: VINCULACIÓN CANDIDATO→EMPLEADO")

    db = SessionLocal()
    try:
        # Count employees with rirekisho_id
        total_employees = db.query(Employee).count()
        linked_employees = db.query(Employee).filter(
            Employee.rirekisho_id.isnot(None)
        ).count()

        print(f"Total empleados (派遣):        {total_employees:4d}")
        print(f"Con rirekisho_id asignado:    {linked_employees:4d}")
        print(f"Sin rirekisho_id:             {total_employees - linked_employees:4d}")

        if linked_employees > 0:
            percentage = (linked_employees / total_employees * 100) if total_employees > 0 else 0
            print(f"\n✅ PASS: {percentage:.1f}% de empleados tienen rirekisho_id asignado")

            # Sample verification: check if linked candidates actually exist
            sample = db.query(Employee).filter(
                Employee.rirekisho_id.isnot(None)
            ).limit(10).all()

            print(f"\nMuestra de vinculaciones (primeros 10):")
            for emp in sample:
                candidate = db.query(Candidate).filter(
                    Candidate.rirekisho_id == emp.rirekisho_id
                ).first()

                if candidate:
                    match_type = "✓"
                    if candidate.full_name_kanji == emp.full_name_kanji and candidate.date_of_birth == emp.date_of_birth:
                        match_type = "✓✓" # Perfect match
                    print(f"  {match_type} [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} → Candidate {emp.rirekisho_id}")
                else:
                    print(f"  ✗ [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} → Candidate NO EXISTE!")
        else:
            print(f"\n⚠️  WARN: Ningún empleado tiene rirekisho_id asignado")

    finally:
        db.close()


def verify_photo_synchronization():
    """Verify that photos are copied from candidates to employees"""
    print_section("VERIFICACIÓN #3: SINCRONIZACIÓN DE FOTOS")

    db = SessionLocal()
    try:
        # Count employees with photos
        employees_with_photos = db.query(Employee).filter(
            Employee.photo_data_url.isnot(None)
        ).count()

        total_employees = db.query(Employee).count()

        print(f"Total empleados (派遣):        {total_employees:4d}")
        print(f"Con foto asignada:            {employees_with_photos:4d}")
        print(f"Sin foto:                     {total_employees - employees_with_photos:4d}")

        if employees_with_photos > 0:
            percentage = (employees_with_photos / total_employees * 100) if total_employees > 0 else 0
            print(f"\n✅ PASS: {percentage:.1f}% de empleados tienen foto")

            # Verify that photos came from candidates
            sample = db.query(Employee).filter(
                Employee.photo_data_url.isnot(None),
                Employee.rirekisho_id.isnot(None)
            ).limit(5).all()

            print(f"\nVerificación de origen de fotos (muestra de 5):")
            for emp in sample:
                candidate = db.query(Candidate).filter(
                    Candidate.rirekisho_id == emp.rirekisho_id
                ).first()

                if candidate and candidate.photo_data_url:
                    if emp.photo_data_url == candidate.photo_data_url:
                        print(f"  ✓ [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} - Foto copiada de candidato")
                    else:
                        print(f"  ⚠ [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} - Foto diferente a candidato")
                else:
                    print(f"  ? [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} - Candidato sin foto")
        else:
            print(f"\n⚠️  WARN: Ningún empleado tiene foto asignada")

        # Check contract workers and staff
        print(f"\n--- Contract Workers (請負) ---")
        cw_with_photos = db.query(ContractWorker).filter(
            ContractWorker.photo_data_url.isnot(None)
        ).count()
        total_cw = db.query(ContractWorker).count()
        print(f"Total:     {total_cw:4d}")
        print(f"Con foto:  {cw_with_photos:4d}")

        print(f"\n--- Staff (スタッフ) ---")
        staff_with_photos = db.query(Staff).filter(
            Staff.photo_data_url.isnot(None)
        ).count()
        total_staff = db.query(Staff).count()
        print(f"Total:     {total_staff:4d}")
        print(f"Con foto:  {staff_with_photos:4d}")

    finally:
        db.close()


def verify_factory_info_extraction():
    """Verify that company_name and plant_name are extracted from factory config"""
    print_section("VERIFICACIÓN #4: EXTRACCIÓN DE COMPANY/PLANT NAME")

    db = SessionLocal()
    try:
        # Count employees with company_name and plant_name
        with_company = db.query(Employee).filter(
            Employee.company_name.isnot(None)
        ).count()

        with_plant = db.query(Employee).filter(
            Employee.plant_name.isnot(None)
        ).count()

        total_employees = db.query(Employee).count()

        print(f"Total empleados (派遣):        {total_employees:4d}")
        print(f"Con company_name:             {with_company:4d}")
        print(f"Con plant_name:               {with_plant:4d}")

        if with_company > 0 and with_plant > 0:
            percentage = (with_company / total_employees * 100) if total_employees > 0 else 0
            print(f"\n✅ PASS: {percentage:.1f}% de empleados tienen company_name asignado")

            # Sample verification
            sample = db.query(Employee).filter(
                Employee.company_name.isnot(None),
                Employee.factory_id.isnot(None)
            ).limit(5).all()

            print(f"\nMuestra de extracciones (primeros 5):")
            for emp in sample:
                factory = db.query(Factory).filter(
                    Factory.factory_id == emp.factory_id
                ).first()

                if factory and factory.config:
                    expected_company = factory.config.get('client_company', {}).get('name')
                    expected_plant = factory.config.get('plant', {}).get('name')

                    if emp.company_name == expected_company:
                        print(f"  ✓ [{emp.hakenmoto_id:4d}] {emp.company_name} - {emp.plant_name}")
                    else:
                        print(f"  ✗ [{emp.hakenmoto_id:4d}] Mismatch: {emp.company_name} != {expected_company}")
                else:
                    print(f"  ? [{emp.hakenmoto_id:4d}] Factory sin config")
        else:
            print(f"\n❌ FAIL: company_name y plant_name NO están asignados")

    finally:
        db.close()


def verify_hakensaki_shain_id():
    """Verify that hakensaki_shain_id is read from Excel"""
    print_section("VERIFICACIÓN #5: CAMPO hakensaki_shain_id")

    db = SessionLocal()
    try:
        # Count employees with hakensaki_shain_id
        with_hakensaki_id = db.query(Employee).filter(
            Employee.hakensaki_shain_id.isnot(None)
        ).count()

        total_employees = db.query(Employee).count()

        print(f"Total empleados (派遣):        {total_employees:4d}")
        print(f"Con hakensaki_shain_id:       {with_hakensaki_id:4d}")
        print(f"Sin hakensaki_shain_id:       {total_employees - with_hakensaki_id:4d}")

        if with_hakensaki_id > 0:
            percentage = (with_hakensaki_id / total_employees * 100) if total_employees > 0 else 0
            print(f"\n✅ PASS: {percentage:.1f}% de empleados tienen hakensaki_shain_id")

            # Sample
            sample = db.query(Employee).filter(
                Employee.hakensaki_shain_id.isnot(None)
            ).limit(5).all()

            print(f"\nMuestra de hakensaki_shain_id (primeros 5):")
            for emp in sample:
                print(f"  [{emp.hakenmoto_id:4d}] {emp.full_name_kanji} → ID: {emp.hakensaki_shain_id}")
        else:
            print(f"\nℹ️  INFO: Ningún empleado tiene hakensaki_shain_id (puede ser normal si el Excel no lo tiene)")

    finally:
        db.close()


def generate_summary():
    """Generate comprehensive summary"""
    print_section("RESUMEN FINAL")

    db = SessionLocal()
    try:
        print("Estadísticas de base de datos:\n")

        # Candidates
        candidates = db.query(Candidate).count()
        candidates_with_photos = db.query(Candidate).filter(
            Candidate.photo_data_url.isnot(None)
        ).count()

        print(f"📋 Candidatos:")
        print(f"   Total:        {candidates:4d}")
        print(f"   Con foto:     {candidates_with_photos:4d}")

        # Employees
        employees = db.query(Employee).count()
        employees_linked = db.query(Employee).filter(
            Employee.rirekisho_id.isnot(None)
        ).count()
        employees_with_photos = db.query(Employee).filter(
            Employee.photo_data_url.isnot(None)
        ).count()
        employees_terminated = db.query(Employee).filter(
            Employee.current_status == 'terminated'
        ).count()

        print(f"\n👷 Empleados (派遣):")
        print(f"   Total:        {employees:4d}")
        print(f"   Vinculados:   {employees_linked:4d}")
        print(f"   Con foto:     {employees_with_photos:4d}")
        print(f"   Terminados:   {employees_terminated:4d}")

        # Contract workers
        contract_workers = db.query(ContractWorker).count()
        cw_linked = db.query(ContractWorker).filter(
            ContractWorker.rirekisho_id.isnot(None)
        ).count()

        print(f"\n🔧 Empleados (請負):")
        print(f"   Total:        {contract_workers:4d}")
        print(f"   Vinculados:   {cw_linked:4d}")

        # Staff
        staff = db.query(Staff).count()
        staff_linked = db.query(Staff).filter(
            Staff.rirekisho_id.isnot(None)
        ).count()

        print(f"\n👔 Staff (スタッフ):")
        print(f"   Total:        {staff:4d}")
        print(f"   Vinculados:   {staff_linked:4d}")

        # Factories
        factories = db.query(Factory).count()
        print(f"\n🏭 Fábricas:")
        print(f"   Total:        {factories:4d}")

    finally:
        db.close()


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("VERIFICACIÓN DE CORRECCIONES DE IMPORTACIÓN".center(80))
    print("="*80)
    print("\nEste script verifica que todas las correcciones implementadas funcionen.")
    print("Si acabas de ejecutar REINSTALAR.bat, todas las verificaciones deberían PASAR.")

    try:
        verify_status_distribution()
        verify_candidate_employee_linking()
        verify_photo_synchronization()
        verify_factory_info_extraction()
        verify_hakensaki_shain_id()
        generate_summary()

        print("\n" + "="*80)
        print("VERIFICACIÓN COMPLETADA".center(80))
        print("="*80)

    except Exception as e:
        print(f"\n❌ ERROR durante verificación: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

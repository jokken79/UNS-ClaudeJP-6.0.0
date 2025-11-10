"""
Script para importar configuraciones de fábricas desde archivos JSON
Importa todos los archivos de config/factories/ a la base de datos
"""
import os
import json
import sys
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.models import Factory
from sqlalchemy import text


def parse_work_hours(work_hours_str):
    """
    Parse work hours from Japanese format
    Example: "昼勤：7時00分～15時30分　夜勤：19時00分～3時30分"
    Returns list of shifts
    """
    shifts = []

    # Try to find shift patterns
    patterns = [
        # Pattern 1: 昼勤：7時00分～15時30分
        r'昼勤[：:]\\s*(\\d{1,2})時(\\d{2})分[～~]\\s*(\\d{1,2})時(\\d{2})分',
        # Pattern 2: 夜勤：19時00分～3時30分
        r'夜勤[：:]\\s*(\\d{1,2})時(\\d{2})分[～~]\\s*(\\d{1,2})時(\\d{2})分',
        # Pattern 3: 朝番：8時00分～17時00分
        r'朝番[：:]\\s*(\\d{1,2})時(\\d{2})分[～~]\\s*(\\d{1,2})時(\\d{2})分',
    ]

    # Check for 昼勤 (day shift)
    day_match = re.search(patterns[0], work_hours_str)
    if day_match:
        start_h, start_m, end_h, end_m = day_match.groups()
        shifts.append({
            "shift_name": "昼勤",
            "start_time": f"{int(start_h):02d}:{int(start_m):02d}",
            "end_time": f"{int(end_h):02d}:{int(end_m):02d}",
            "break_minutes": 45  # Default from example
        })

    # Check for 夜勤 (night shift)
    night_match = re.search(patterns[1], work_hours_str)
    if night_match:
        start_h, start_m, end_h, end_m = night_match.groups()
        shifts.append({
            "shift_name": "夜勤",
            "start_time": f"{int(start_h):02d}:{int(start_m):02d}",
            "end_time": f"{int(end_h):02d}:{int(end_m):02d}",
            "break_minutes": 45  # Default from example
        })

    return shifts


def parse_break_time(break_time_str):
    """
    Parse break time to extract duration in minutes
    Example: "昼勤：11時00分～11時45分 まで (45分)"
    Returns break minutes
    """
    # Try to find minutes in parentheses first
    minutes_match = re.search(r'\\((\\d+)分\\)', break_time_str)
    if minutes_match:
        return int(minutes_match.group(1))

    # Try to calculate from time range
    time_match = re.search(r'(\\d{1,2})時(\\d{2})分[～~]\\s*(\\d{1,2})時(\\d{2})分', break_time_str)
    if time_match:
        start_h, start_m, end_h, end_m = map(int, time_match.groups())
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        return end_minutes - start_minutes

    return 60  # Default 60 minutes


def import_factory_from_json(json_path, db):
    """Import a single factory from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract company and plant info FIRST (needed for factory_id)
        client_company = data.get('client_company', {})
        plant = data.get('plant', {})

        company_name = client_company.get('name', '').strip()
        plant_name = plant.get('name', '').strip()

        # Rebuild factory_id using DOUBLE underscore __ to match import_data.py convention
        # This ensures consistency with employee data imports
        if company_name and plant_name:
            factory_id = f"{company_name}__{plant_name}"
        elif company_name:
            factory_id = f"{company_name}__"
        elif plant_name:
            factory_id = f"__{plant_name}"
        else:
            # Fallback to JSON factory_id if no company/plant info
            factory_id = data.get('factory_id', '')
            if not factory_id:
                print(f"❌ No factory_id in {json_path.name}")
                return False

        # Check if factory already exists
        existing = db.query(Factory).filter(Factory.factory_id == factory_id).first()
        if existing:
            print(f"⏭️  Factory {factory_id} already exists, skipping")
            return False

        # Extract schedule info
        schedule = data.get('schedule', {})

        # Build full name
        if company_name and plant_name:
            full_name = f"{company_name} {plant_name}"
        elif company_name:
            full_name = company_name
        elif plant_name:
            full_name = plant_name
        else:
            full_name = factory_id

        # Skip factories with generic names (Factory-XX)
        import re
        generic_pattern = re.compile(r'^Factory-\d+$')
        if generic_pattern.match(full_name):
            print(f"⏭️  Skipping generic factory: {factory_id} (no real data)")
            return False

        # Extract address (prefer plant address, fallback to company)
        address = plant.get('address') or client_company.get('address')

        # Extract phone (prefer plant phone, fallback to company)
        phone = plant.get('phone') or client_company.get('phone')

        # Extract contact person
        responsible_person = client_company.get('responsible_person', {})
        contact_person = responsible_person.get('name', '')

        # Parse shifts from schedule
        work_hours = schedule.get('work_hours', '')
        break_time_str = schedule.get('break_time', '')

        shifts = []
        if work_hours:
            shifts = parse_work_hours(work_hours)
            # Update break minutes from break_time if available
            if break_time_str and shifts:
                break_minutes = parse_break_time(break_time_str)
                for shift in shifts:
                    shift['break_minutes'] = break_minutes

        # Build config object
        config = {
            "shifts": shifts,
            "overtime_rules": {
                "normal_rate_multiplier": 1.25,
                "night_rate_multiplier": 1.5,
                "holiday_rate_multiplier": 1.35,
                "night_start": "22:00",
                "night_end": "05:00"
            },
            "bonuses": {
                "attendance_bonus": 0,
                "perfect_attendance_bonus": 0,
                "transportation_allowance": 0,
                "meal_allowance": 0,
                "housing_allowance": 0,
                "other_allowances": None
            },
            "holidays": {
                "weekly_holidays": ["土", "日"],
                "public_holidays": True,
                "company_holidays": []
            },
            "attendance_rules": {
                "late_penalty": 0,
                "absence_penalty": 0,
                "early_leave_penalty": 0,
                "grace_period_minutes": 5,
                "require_advance_notice": True
            }
        }

        # Create factory record
        new_factory = Factory(
            factory_id=factory_id,
            name=full_name[:100],  # Limit to 100 chars
            company_name=company_name[:100] if company_name else None,
            plant_name=plant_name[:100] if plant_name else None,
            address=address,
            phone=phone[:20] if phone else None,
            contact_person=contact_person[:100] if contact_person else None,
            config=config,
            is_active=True
        )

        db.add(new_factory)
        db.commit()

        print(f"✅ Imported: {factory_id} - {full_name}")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error importing {json_path.name}: {str(e)}")
        return False


def main():
    """Main import function"""
    print("=" * 80)
    print("🏭 Factory JSON Import Script")
    print("=" * 80)

    # Path to factories config directory
    config_dir = Path(__file__).parent.parent / "config" / "factories"

    if not config_dir.exists():
        print(f"❌ Directory not found: {config_dir}")
        return

    print(f"\\n📁 Reading from: {config_dir}")

    # Get all JSON files
    json_files = list(config_dir.glob("*.json"))

    # Filter out mapping and backup files
    json_files = [
        f for f in json_files
        if f.name not in ['factory_id_mapping.json', 'factory-01-example.json']
        and not f.name.startswith('backup')
    ]

    print(f"📋 Found {len(json_files)} factory JSON files\\n")

    if not json_files:
        print("❌ No factory JSON files found")
        return

    # Create database session
    db = SessionLocal()

    try:
        imported = 0
        skipped = 0
        errors = 0

        for json_file in sorted(json_files):
            result = import_factory_from_json(json_file, db)
            if result is True:
                imported += 1
            elif result is False:
                skipped += 1
            else:
                errors += 1

        print("\\n" + "=" * 80)
        print("📊 Import Summary:")
        print(f"   ✅ Imported: {imported}")
        print(f"   ⏭️  Skipped (already exist): {skipped}")
        print(f"   ❌ Errors: {errors}")
        print(f"   📊 Total processed: {len(json_files)}")
        print("=" * 80)

        if imported > 0:
            print("\\n🎉 Factories imported successfully!")
            print("   You can now view and edit them at: http://localhost:3000/factories")

    finally:
        db.close()


if __name__ == "__main__":
    main()

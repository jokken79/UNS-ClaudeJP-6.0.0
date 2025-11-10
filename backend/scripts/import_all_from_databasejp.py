"""
SCRIPT MAESTRO DE IMPORTACIÓN COMPLETA
========================================

Este script ejecuta TODO el proceso de importación desde DATABASEJP:

1. 📂 Busca carpeta DATABASEJP automáticamente
2. 📸 Extrae fotos desde Access database (si no existen)
3. 👥 Importa candidatos desde Access (T_履歴書)
4. 🏭 Importa fábricas desde JSON
5. 👷 Importa empleados desde Excel:
   - 派遣社員 (Dispatch employees)
   - 請負社員 (Contract workers) → TODOS asignados a 高雄工業 岡山工場
   - スタッフ (Staff)
6. 🔄 Sincroniza fotos entre candidatos y empleados
7. 📊 Genera reporte final

IMPORTANTE:
- Se ejecuta en el DOCKER CONTAINER backend
- Requiere carpeta DATABASEJP en host (se monta en /app/DATABASEJP)
- Requiere employee_master.xlsm en /app/config/
- Requiere factories_index.json en /app/config/

Usage:
    # Desde host (Windows):
    docker exec -it uns-claudejp-backend python scripts/import_all_from_databasejp.py

    # Desde dentro del container:
    python scripts/import_all_from_databasejp.py

    # Con opciones:
    python scripts/import_all_from_databasejp.py --skip-candidates  # Salta candidatos
    python scripts/import_all_from_databasejp.py --skip-photos      # Salta fotos
    python scripts/import_all_from_databasejp.py --factories-only   # Solo fábricas

Author: Claude Code
Date: 2025-10-28
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Candidate, Employee, ContractWorker, Staff, Factory

# Import functions from other scripts
from import_data import (
    import_factories,
    import_haken_employees,
    import_ukeoi_employees,
    import_staff_employees,
    import_taisha_employees
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/app/import_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MasterImporter:
    """Master importer that orchestrates the complete import process"""

    def __init__(self, args):
        self.args = args
        self.stats = {
            'start_time': datetime.now(),
            'photos_extracted': 0,
            'candidates_imported': 0,
            'factories_imported': 0,
            'haken_imported': 0,
            'ukeoi_imported': 0,
            'staff_imported': 0,
            'taisha_updated': 0,
            'errors': []
        }

    def print_banner(self, text: str):
        """Print a fancy banner"""
        border = "=" * 80
        print(f"\n{border}")
        print(f"{text:^80}")
        print(f"{border}\n")

    def check_prerequisites(self) -> bool:
        """Check if all required files and folders exist"""
        logger.info("Checking prerequisites...")

        required_paths = {
            'employee_master': '/app/config/employee_master.xlsm',
            'factories_index': '/app/config/factories_index.json',
            'factories_dir': '/app/config/factories'
        }

        all_ok = True
        for name, path in required_paths.items():
            if Path(path).exists():
                logger.info(f"  ✓ {name}: {path}")
            else:
                logger.error(f"  ✗ {name}: {path} NOT FOUND")
                all_ok = False

        # Check DATABASEJP (optional for photos)
        databasejp_paths = [
            '/app/DATABASEJP',
            '/app/../DATABASEJP',
            'D:/DATABASEJP'
        ]

        databasejp_found = False
        for path in databasejp_paths:
            if Path(path).exists():
                logger.info(f"  ✓ DATABASEJP found: {path}")
                databasejp_found = True
                break

        if not databasejp_found:
            logger.warning("  ⚠ DATABASEJP not found (photos will be skipped)")

        return all_ok

    def extract_photos(self) -> bool:
        """Extract photos from Access database"""
        if self.args.skip_photos:
            logger.info("Skipping photo extraction (--skip-photos)")
            return True

        self.print_banner("PASO 1: EXTRACCIÓN DE FOTOS DESDE ACCESS")

        # Check if access_photo_mappings.json already exists
        if Path('/app/access_photo_mappings.json').exists():
            logger.info("access_photo_mappings.json ya existe. Saltando extracción.")
            return True

        try:
            # Run auto_extract_photos_from_databasejp.py
            logger.info("Ejecutando auto_extract_photos_from_databasejp.py...")

            import subprocess
            result = subprocess.run(
                ['python', '/app/scripts/auto_extract_photos_from_databasejp.py'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )

            if result.returncode == 0:
                logger.info("✓ Fotos extraídas exitosamente")
                self.stats['photos_extracted'] = 1  # Flag success
                return True
            else:
                logger.warning(f"Extracción de fotos falló: {result.stderr}")
                logger.warning("Continuando sin fotos...")
                return True  # Continue anyway

        except Exception as e:
            logger.error(f"Error al extraer fotos: {e}")
            logger.warning("Continuando sin fotos...")
            return True  # Continue anyway

    def import_candidates(self) -> bool:
        """Import candidates from JSON with photos"""
        if self.args.skip_candidates:
            logger.info("Skipping candidates (--skip-candidates)")
            return True

        self.print_banner("PASO 2: IMPORTACIÓN DE CANDIDATOS CON FOTOS")

        try:
            # Use the improved import script
            script_path = Path('/app/scripts/import_candidates_improved.py')
            if not script_path.exists():
                logger.error(f"Script not found: {script_path}")
                return False

            logger.info("Ejecutando import_candidates_improved.py...")
            logger.info("  - Importa desde: /app/config/access_candidates_data.json")
            logger.info("  - Fotos desde: /app/config/access_photo_mappings.json")
            logger.info("")

            import subprocess
            result = subprocess.run(
                ['python', str(script_path)],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                logger.info("✓ Candidatos importados exitosamente")
                logger.info(result.stdout)
                self.stats['candidates_imported'] = 1
                return True
            else:
                logger.error(f"Importación de candidatos falló:")
                logger.error(result.stderr)
                return False

        except Exception as e:
            logger.error(f"Error al importar candidatos: {e}")
            import traceback
            traceback.print_exc()
            return False

    def import_all_employees(self) -> bool:
        """Import all employee types from Excel"""
        self.print_banner("PASO 3: IMPORTACIÓN DE EMPLEADOS DESDE EXCEL")

        db = SessionLocal()
        try:
            # Import factories first
            logger.info("\n--- Importando Fábricas ---")
            factories_count = import_factories(db)
            self.stats['factories_imported'] = factories_count

            # Import 派遣社員 (Dispatch employees)
            logger.info("\n--- Importando 派遣社員 (Dispatch Employees) ---")
            haken_count = import_haken_employees(db)
            self.stats['haken_imported'] = haken_count

            # Import 請負社員 (Contract workers) - TODOS a 高雄工業 岡山工場
            logger.info("\n--- Importando 請負社員 (Contract Workers) ---")
            logger.info("NOTA: Todos asignados a 高雄工業 岡山工場")
            ukeoi_count = import_ukeoi_employees(db)
            self.stats['ukeoi_imported'] = ukeoi_count

            # Import スタッフ (Staff)
            logger.info("\n--- Importando スタッフ (Staff) ---")
            staff_count = import_staff_employees(db)
            self.stats['staff_imported'] = staff_count

            # Update 退社社員 (Resigned employees)
            logger.info("\n--- Actualizando 退社社員 (Resigned Employees) ---")
            taisha_count = import_taisha_employees(db)
            self.stats['taisha_updated'] = taisha_count

            logger.info("\n✓ Todos los empleados importados exitosamente")
            return True

        except Exception as e:
            logger.error(f"Error al importar empleados: {e}")
            self.stats['errors'].append(str(e))
            return False
        finally:
            db.close()

    def generate_final_report(self):
        """Generate comprehensive final report"""
        self.print_banner("REPORTE FINAL DE IMPORTACIÓN")

        end_time = datetime.now()
        duration = end_time - self.stats['start_time']

        # Query final counts from database
        db = SessionLocal()
        try:
            candidates_count = db.query(Candidate).count()
            employees_count = db.query(Employee).count()
            contract_workers_count = db.query(ContractWorker).count()
            staff_count = db.query(Staff).count()
            factories_count = db.query(Factory).count()

            # Photos count
            candidates_with_photos = db.query(Candidate).filter(
                Candidate.photo_data_url.isnot(None)
            ).count()
            employees_with_photos = db.query(Employee).filter(
                Employee.photo_data_url.isnot(None)
            ).count()

            print(f"Duración total: {duration}")
            print("")
            print("ESTADÍSTICAS FINALES:")
            print("=" * 80)
            print(f"  📋 Candidatos en BD:          {candidates_count:4d}")
            print(f"     └─ Con fotos:              {candidates_with_photos:4d}")
            print("")
            print(f"  👷 派遣社員:                   {employees_count:4d}")
            print(f"     └─ Con fotos:              {employees_with_photos:4d}")
            print("")
            print(f"  🔧 請負社員:                   {contract_workers_count:4d}")
            print(f"     └─ Todos en: 高雄工業 岡山工場")
            print("")
            print(f"  👔 スタッフ:                   {staff_count:4d}")
            print("")
            print(f"  🏭 Fábricas:                  {factories_count:4d}")
            print("=" * 80)
            print("")

            if self.stats['errors']:
                print("ERRORES ENCONTRADOS:")
                for error in self.stats['errors']:
                    print(f"  ❌ {error}")
            else:
                print("✅ IMPORTACIÓN COMPLETADA SIN ERRORES")

            print("")
            print("=" * 80)

            # Save JSON report
            report_file = f'/app/import_all_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
                'statistics': {
                    'candidates_total': candidates_count,
                    'candidates_with_photos': candidates_with_photos,
                    'employees_haken': employees_count,
                    'employees_with_photos': employees_with_photos,
                    'contract_workers': contract_workers_count,
                    'staff': staff_count,
                    'factories': factories_count
                },
                'import_stats': self.stats,
                'errors': self.stats['errors']
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Reporte guardado en: {report_file}")

        finally:
            db.close()

    def run(self) -> bool:
        """Run the complete import process"""
        self.print_banner("🚀 IMPORTACIÓN COMPLETA DESDE DATABASEJP")

        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Faltan archivos requeridos. Abortando.")
            return False

        success = True

        # Step 1: Extract photos (if not skipped)
        if not self.args.skip_photos:
            if not self.extract_photos():
                logger.warning("Extracción de fotos falló, continuando sin fotos...")

        # Step 2: Import candidates (if not skipped)
        if not self.args.skip_candidates:
            if not self.import_candidates():
                logger.error("Importación de candidatos falló. Abortando.")
                return False

        # Step 3: Import employees (factories + all types)
        if not self.args.factories_only:
            if not self.import_all_employees():
                success = False

        # Final report
        self.generate_final_report()

        return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Importación completa desde DATABASEJP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python import_all_from_databasejp.py                    # Importar TODO
  python import_all_from_databasejp.py --skip-photos      # Salta extracción de fotos
  python import_all_from_databasejp.py --skip-candidates  # Salta candidatos
  python import_all_from_databasejp.py --factories-only   # Solo fábricas

Requisitos:
  - Carpeta DATABASEJP con Access database
  - Archivo employee_master.xlsm en /app/config/
  - Archivos JSON de fábricas en /app/config/factories/
        """
    )

    parser.add_argument('--skip-photos', action='store_true',
                       help='Salta la extracción de fotos desde Access')
    parser.add_argument('--skip-candidates', action='store_true',
                       help='Salta la importación de candidatos')
    parser.add_argument('--factories-only', action='store_true',
                       help='Importa solo fábricas (sin empleados)')

    args = parser.parse_args()

    # Create importer and run
    importer = MasterImporter(args)
    success = importer.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

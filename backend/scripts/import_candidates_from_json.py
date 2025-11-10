"""
📥 Importador de Candidatos desde JSON
========================================

Este script importa candidatos desde el archivo JSON exportado por
export_candidates_to_json.py a la base de datos PostgreSQL.

Se ejecuta DENTRO del contenedor Docker y lee el archivo JSON
que fue exportado en Windows.

Usage:
    python import_candidates_from_json.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, date
import logging

# Add parent directory to path
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.models.models import Candidate, CandidateStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_json_data(json_file):
    """Carga datos desde JSON"""
    logger.info(f"Cargando datos desde: {json_file}")

    if not Path(json_file).exists():
        logger.error(f"Archivo no encontrado: {json_file}")
        return None

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"✓ Archivo cargado: {data['metadata']['total_records']} candidatos")
    return data

def import_candidate(db: Session, candidate_data: dict, stats: dict):
    """Importa un candidato individual"""

    # Mapeo de campos Access → PostgreSQL
    # Aquí necesitarás mapear los nombres de columnas de Access
    # a los campos del modelo Candidate

    try:
        # Ejemplo de mapeo (deberás ajustar según tu esquema)
        candidate = Candidate(
            rirekisho_id=candidate_data.get('履歴書№'),
            full_name_kanji=candidate_data.get('氏名'),
            full_name_kana=candidate_data.get('フリガナ'),
            # ... mapear todos los campos necesarios
            status=CandidateStatus.PENDING,
            created_at=datetime.now()
        )

        db.add(candidate)
        db.commit()
        stats['imported'] += 1

        if stats['imported'] % 100 == 0:
            logger.info(f"  Importados {stats['imported']} candidatos...")

    except IntegrityError as e:
        db.rollback()
        stats['duplicates'] += 1
        logger.debug(f"Duplicado: {candidate_data.get('履歴書№')}")

    except Exception as e:
        db.rollback()
        stats['errors'] += 1
        logger.error(f"Error importando candidato: {e}")

def import_all_candidates(json_file):
    """Importa todos los candidatos desde JSON"""

    # Cargar datos
    data = load_json_data(json_file)
    if not data:
        return False

    candidates = data['candidates']
    total = len(candidates)

    logger.info(f"Iniciando importación de {total} candidatos...")

    # Estadísticas
    stats = {
        'imported': 0,
        'duplicates': 0,
        'errors': 0
    }

    db = SessionLocal()
    try:
        for candidate_data in candidates:
            import_candidate(db, candidate_data, stats)

        logger.info("=" * 80)
        logger.info("RESUMEN DE IMPORTACIÓN")
        logger.info("=" * 80)
        logger.info(f"✓ Importados:  {stats['imported']}")
        logger.info(f"⚠ Duplicados:  {stats['duplicates']}")
        logger.info(f"✗ Errores:     {stats['errors']}")
        logger.info("=" * 80)

        return True

    finally:
        db.close()

def main():
    """Función principal"""
    json_file = '/app/config/access_candidates_data.json'

    logger.info("=" * 80)
    logger.info("IMPORTACIÓN DE CANDIDATOS DESDE JSON")
    logger.info("=" * 80)

    success = import_all_candidates(json_file)

    if success:
        logger.info("✅ Importación completada exitosamente")
        return 0
    else:
        logger.error("❌ Importación falló")
        return 1

if __name__ == "__main__":
    sys.exit(main())

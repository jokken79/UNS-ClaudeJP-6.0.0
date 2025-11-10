"""
Script simple para importar candidatos reales desde JSON
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Candidate

def import_candidates_from_json():
    """Importa candidatos reales desde access_candidates_data.json"""

    json_file = Path('/app/config/access_candidates_data.json')

    if not json_file.exists():
        print(f"⚠️  Archivo de candidatos reales no encontrado: {json_file}")
        print("   Los candidatos reales solo se importan si existe access_candidates_data.json")
        return False

    print(f"📂 Cargando: {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ El JSON debe ser un array")
            return False

        print(f"✓ Archivo cargado: {len(data)} candidatos")

    except json.JSONDecodeError as e:
        print(f"❌ Error al parsear JSON: {e}")
        return False

    # Conectar a BD
    db = SessionLocal()
    imported_count = 0
    skipped_count = 0
    error_count = 0

    try:
        for idx, record in enumerate(data, 1):
            try:
                # Verificar si ya existe por rirekisho_id
                rirekisho_id = record.get('履歴書ID')
                if not rirekisho_id:
                    print(f"⚠️  Registro {idx}: sin 履歴書ID, saltando")
                    skipped_count += 1
                    continue

                existing = db.query(Candidate).filter(
                    Candidate.rirekisho_id == str(rirekisho_id)
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Mapear campos de Access a modelo Candidate
                candidate = Candidate(
                    rirekisho_id=str(rirekisho_id),  # Convertir a string
                    full_name_kanji=record.get('氏名') or '',
                    full_name_kana=record.get('フリガナ') or '',
                    full_name_roman=record.get('氏名（ローマ字)') or '',
                    date_of_birth=record.get('生年月日'),
                    gender=record.get('性別'),
                    nationality=record.get('国籍') or '',
                    residence_status=record.get('在留資格') or '',
                    residence_expiry=record.get('（在留カード記載）在留期限'),
                    residence_card_number=record.get('在留カード番号'),
                    phone=record.get('電話番号') or '',
                    mobile=record.get('携帯電話') or '',
                    current_address=record.get('現住所') or '',
                    address_banchi=record.get('番地') or '',
                    postal_code=record.get('郵便番号'),
                    address_building=record.get('物件名'),
                    license_number=record.get('運転免許番号及び条件'),
                    license_expiry=record.get('運転免許期限'),
                    car_ownership=record.get('自動車所有', False),
                    voluntary_insurance=record.get('任意保険加入', False),
                )

                db.add(candidate)
                imported_count += 1

                # Commit cada 50 registros
                if imported_count % 50 == 0:
                    db.commit()
                    print(f"✓ {imported_count} candidatos importados...")

            except Exception as e:
                error_count += 1
                print(f"❌ Error en registro {idx} (ID {rirekisho_id}): {str(e)[:100]}")
                continue

        # Commit final
        db.commit()

        print(f"""
╔════════════════════════════════════════╗
║    IMPORTACIÓN COMPLETADA              ║
╚════════════════════════════════════════╝
✓ Importados:  {imported_count}
⊘ Saltados:    {skipped_count}
✗ Errores:     {error_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

        return True

    except Exception as e:
        print(f"❌ Error general: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == '__main__':
    success = import_candidates_from_json()
    sys.exit(0 if success else 1)

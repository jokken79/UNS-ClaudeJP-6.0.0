#!/usr/bin/env python3
"""
Script de verificación para asegurar que hay candidatos importados
Se ejecuta después del startup para validar el estado de la BD
"""
import sys
from pathlib import Path

sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.models import Candidate

def verify_candidates():
    """Verifica que existan candidatos en la BD"""

    db = SessionLocal()
    try:
        # Contar candidatos
        total_candidates = db.query(Candidate).count()

        print(f"""
╔════════════════════════════════════════════════════════════╗
║          VERIFICACIÓN DE CANDIDATOS IMPORTADOS             ║
╚════════════════════════════════════════════════════════════╝
Total de candidatos en BD: {total_candidates}
        """)

        if total_candidates == 0:
            print("⚠️  ADVERTENCIA: No hay candidatos en la base de datos")
            print("    Los candidatos deben importarse manualmente.")
            return False
        elif total_candidates < 100:
            print(f"⚠️  ADVERTENCIA: Solo hay {total_candidates} candidatos")
            print("    Se esperaba al menos 100 candidatos")
            return False
        else:
            print(f"✅ CORRECTO: {total_candidates} candidatos disponibles")

            # Mostrar distribución por nacionalidad (primeros 5)
            candidates = db.query(Candidate).limit(5).all()
            if candidates:
                print("\n📋 Primeros candidatos:")
                for cand in candidates[:3]:
                    name = cand.full_name_kanji or "N/A"
                    nat = cand.nationality or "N/A"
                    print(f"   • {name} ({nat})")

            return True

    except Exception as e:
        print(f"❌ Error al verificar candidatos: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    success = verify_candidates()
    sys.exit(0 if success else 1)

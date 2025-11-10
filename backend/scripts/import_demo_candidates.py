"""
Script para importar candidatos de demostración a PostgreSQL
Demo Candidates for UNS-ClaudeJP 5.2
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Candidate

def create_demo_candidates():
    """Create sample candidates for demonstration"""

    demo_data = [
        {
            "seimei_kanji": "田中 太郎",
            "seimei_katakana": "タナカ タロウ",
            "seimei_romaji": "Tanaka Taro",
            "birth_date": "1990-05-15",
            "nationality": "Vietnam",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2025-12-31",
            "phone": "090-1234-5678",
            "email": "tanaka.taro@example.com",
            "address_prefecture": "愛知県",
            "address_city": "名古屋市中区",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 3,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "山田 花子",
            "seimei_katakana": "ヤマダ ハナコ",
            "seimei_romaji": "Yamada Hanako",
            "birth_date": "1992-08-22",
            "nationality": "Philippines",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2026-06-30",
            "phone": "090-2345-6789",
            "email": "yamada.hanako@example.com",
            "address_prefecture": "岐阜県",
            "address_city": "岐阜市",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 2,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "鈴木 健太",
            "seimei_katakana": "スズキ ケンタ",
            "seimei_romaji": "Suzuki Kenta",
            "birth_date": "1988-11-30",
            "nationality": "Indonesia",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2025-09-15",
            "phone": "090-3456-7890",
            "email": "suzuki.kenta@example.com",
            "address_prefecture": "静岡県",
            "address_city": "浜松市中区",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 4,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "佐藤 美咲",
            "seimei_katakana": "サトウ ミサキ",
            "seimei_romaji": "Sato Misaki",
            "birth_date": "1995-03-08",
            "nationality": "Thailand",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2026-01-20",
            "phone": "090-4567-8901",
            "email": "sato.misaki@example.com",
            "address_prefecture": "愛知県",
            "address_city": "豊田市",
            "qualification": "Technical Skill Level 1",
            "work_experience_years": 1,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "加藤 優太",
            "seimei_katakana": "カトウ ユウタ",
            "seimei_romaji": "Kato Yuta",
            "birth_date": "1991-07-12",
            "nationality": "Vietnam",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2026-05-10",
            "phone": "090-5678-9012",
            "email": "kato.yuta@example.com",
            "address_prefecture": "岡山県",
            "address_city": "岡山市北区",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 3,
            "current_status": "employed",
        },
        {
            "seimei_kanji": "小林 由美",
            "seimei_katakana": "コバヤシ ユミ",
            "seimei_romaji": "Kobayashi Yumi",
            "birth_date": "1993-09-25",
            "nationality": "Myanmar",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2025-11-30",
            "phone": "090-6789-0123",
            "email": "kobayashi.yumi@example.com",
            "address_prefecture": "愛知県",
            "address_city": "一宮市",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 2,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "伊藤 翔太",
            "seimei_katakana": "イトウ ショウタ",
            "seimei_romaji": "Ito Shota",
            "birth_date": "1989-12-18",
            "nationality": "Cambodia",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2026-03-25",
            "phone": "090-7890-1234",
            "email": "ito.shota@example.com",
            "address_prefecture": "岐阜県",
            "address_city": "大垣市",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 5,
            "current_status": "employed",
        },
        {
            "seimei_kanji": "中村 桜子",
            "seimei_katakana": "ナカムラ サクラコ",
            "seimei_romaji": "Nakamura Sakurako",
            "birth_date": "1994-04-30",
            "nationality": "Laos",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2025-08-15",
            "phone": "090-8901-2345",
            "email": "nakamura.sakura@example.com",
            "address_prefecture": "静岡県",
            "address_city": "静岡市葵区",
            "qualification": "Technical Skill Level 1",
            "work_experience_years": 1,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "高橋 拓也",
            "seimei_katakana": "タカハシ タクヤ",
            "seimei_romaji": "Takahashi Takuya",
            "birth_date": "1987-01-05",
            "nationality": "Bangladesh",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2026-02-28",
            "phone": "090-9012-3456",
            "email": "takahashi.takuya@example.com",
            "address_prefecture": "愛知県",
            "address_city": "瀬戸市",
            "qualification": "Technical Skill Level 2",
            "work_experience_years": 4,
            "current_status": "seeking",
        },
        {
            "seimei_kanji": "渡辺 麗奈",
            "seimei_katakana": "ワタナベ レイナ",
            "seimei_romaji": "Watanabe Reina",
            "birth_date": "1996-06-14",
            "nationality": "Nepal",
            "visa_status": "Specific Skilled Worker (SSW)",
            "visa_expiry": "2025-10-20",
            "phone": "090-0123-4567",
            "email": "watanabe.reina@example.com",
            "address_prefecture": "岡山県",
            "address_city": "倉敷市",
            "qualification": "Technical Skill Level 1",
            "work_experience_years": 1,
            "current_status": "seeking",
        },
    ]

    db = SessionLocal()
    try:
        # Check if candidates already exist
        existing_count = db.query(Candidate).count()
        if existing_count > 0:
            print(f"  ⚠ {existing_count} candidatos ya existen. Saltando importación de demostración.")
            return

        candidates_created = 0
        for data in demo_data:
            candidate = Candidate(
                seimei_kanji=data["seimei_kanji"],
                seimei_katakana=data["seimei_katakana"],
                seimei_romaji=data["seimei_romaji"],
                birth_date=datetime.strptime(data["birth_date"], "%Y-%m-%d").date(),
                nationality=data["nationality"],
                visa_status=data["visa_status"],
                visa_expiry=datetime.strptime(data["visa_expiry"], "%Y-%m-%d").date(),
                phone=data["phone"],
                email=data["email"],
                address_prefecture=data["address_prefecture"],
                address_city=data["address_city"],
                qualification=data["qualification"],
                work_experience_years=data["work_experience_years"],
                status=data["current_status"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(candidate)
            candidates_created += 1

        db.commit()
        print(f"✓ Importados {candidates_created} candidatos de demostración")

    except Exception as e:
        db.rollback()
        print(f"✗ Error al importar candidatos: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    print("==================================================")
    print("IMPORTANDO CANDIDATOS DE DEMOSTRACIÓN")
    print("==================================================")
    create_demo_candidates()

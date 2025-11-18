"""
Import 1,156 candidates WITH PHOTOS from JSON file
=====================================================

This script imports candidates from all_candidates_with_photos.json
with complete field mapping and photo_data_url support.

Features:
- Batch processing (100 records per commit)
- Progress reporting
- Error handling with detailed logs
- Photo data preservation
- Duplicate detection

Usage:
    docker exec -it uns-claudejp-600-backend-1 bash
    cd /app
    python scripts/import_candidates_with_photos.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any

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


def parse_date(date_str):
    """Parse date from various formats"""
    if not date_str or date_str == 'None' or date_str == '':
        return None

    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError, AttributeError):
        pass

    try:
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except (ValueError, TypeError):
                continue
    except (ValueError, TypeError, AttributeError):
        pass

    return None


def parse_int(value):
    """Parse integer safely"""
    if not value or str(value).strip() == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_float(value):
    """Parse float safely"""
    if not value or str(value).strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_bool(value):
    """Convert Japanese yes/no to boolean"""
    if not value:
        return None
    value_str = str(value).strip()
    return value_str in ['有', '○', 'はい', 'Yes', '1', 'TRUE']


def normalize_percentage(value):
    """Normalize percentage values to standard format (0-100)"""
    if not value:
        return None
    value_str = str(value).strip().replace('%', '').strip()
    try:
        num = float(value_str)
        if num > 100:
            return '100%'
        elif num < 0:
            return '0%'
        else:
            return f'{int(num)}%'
    except (ValueError, TypeError):
        return value_str


def import_candidate(db: Session, data: dict, stats: dict) -> bool:
    """Import a single candidate with complete field mapping"""

    try:
        # Extract rirekisho_id - primary unique identifier
        rirekisho_id_raw = data.get('履歴書ID', data.get('履歴書№'))

        if not rirekisho_id_raw or str(rirekisho_id_raw) == 'None':
            stats['errors'] += 1
            logger.error(f"  Missing rirekisho_id for: {data.get('氏名', 'Unknown')}")
            return False

        rirekisho_id = str(rirekisho_id_raw).strip()

        # Check if already exists
        existing = db.query(Candidate).filter(Candidate.rirekisho_id == rirekisho_id).first()
        if existing:
            stats['duplicates'] += 1
            logger.debug(f"  Duplicate: {rirekisho_id}")
            return False

        # Get photo data
        photo_data_url = data.get('photo_data_url')
        if photo_data_url:
            stats['with_photo'] = stats.get('with_photo', 0) + 1

        # Create candidate with COMPLETE mapped fields
        candidate = Candidate(
            rirekisho_id=rirekisho_id,

            # === BASIC INFO (基本情報) ===
            full_name_kanji=data.get('氏名'),
            full_name_kana=data.get('フリガナ'),
            full_name_roman=data.get('氏名（ローマ字)'),
            gender=data.get('性別'),
            date_of_birth=parse_date(data.get('生年月日')),
            nationality=data.get('国籍'),
            marital_status=data.get('配偶者'),
            hire_date=parse_date(data.get('入社日')),
            reception_date=parse_date(data.get('受付日')),
            arrival_date=parse_date(data.get('来日')),

            # === PHOTO (写真) ===
            photo_data_url=photo_data_url,

            # === CONTACT (連絡先) ===
            phone=data.get('電話番号'),
            mobile=data.get('携帯電話'),

            # === ADDRESS (住所情報) ===
            postal_code=data.get('郵便番号'),
            current_address=data.get('現住所'),
            address=data.get('現住所'),
            address_banchi=data.get('番地'),
            address_building=data.get('物件名'),
            registered_address=data.get('登録住所'),

            # === PASSPORT & VISA (パスポート・ビザ) ===
            passport_number=data.get('パスポート番号'),
            passport_expiry=parse_date(data.get('パスポート期限')),
            residence_card_number=data.get('在留カード番号'),
            residence_status=data.get('在留資格'),
            residence_expiry=parse_date(data.get('（在留カード記載）在留期限')),

            # === DRIVER'S LICENSE (運転免許) ===
            license_number=data.get('運転免許番号及び条件'),
            license_expiry=parse_date(data.get('運転免許期限')),
            car_ownership=data.get('自動車所有'),
            voluntary_insurance=data.get('任意保険加入'),

            # === QUALIFICATIONS (資格・免許) ===
            forklift_license=data.get('ﾌｫｰｸﾘﾌﾄ免許'),
            tama_kake=data.get('玉掛'),
            mobile_crane_under_5t=data.get('移動式ｸﾚｰﾝ運転士(5ﾄﾝ未満)'),
            mobile_crane_over_5t=data.get('移動式ｸﾚｰﾝ運転士(5ﾄﾝ以上)'),
            gas_welding=data.get('ｶﾞｽ溶接作業者'),

            # === FAMILY (家族構成) - Member 1 ===
            family_name_1=data.get('家族構成氏名1'),
            family_relation_1=data.get('家族構成続柄1'),
            family_age_1=parse_int(data.get('年齢1')),
            family_residence_1=data.get('居住1'),
            family_separate_address_1=data.get('別居住住所1'),

            # === FAMILY - Member 2 ===
            family_name_2=data.get('家族構成氏名2'),
            family_relation_2=data.get('家族構成続柄2'),
            family_age_2=parse_int(data.get('年齢2')),
            family_residence_2=data.get('居住2'),
            family_separate_address_2=data.get('別居住住所2'),

            # === FAMILY - Member 3 ===
            family_name_3=data.get('氏名3'),
            family_relation_3=data.get('家族構成続柄3'),
            family_age_3=parse_int(data.get('年齢3')),
            family_residence_3=data.get('居住3'),
            family_separate_address_3=data.get('別居住住所3'),

            # === FAMILY - Member 4 ===
            family_name_4=data.get('家族構成氏名4'),
            family_relation_4=data.get('家族構成続柄4'),
            family_age_4=parse_int(data.get('年齢4')),
            family_residence_4=data.get('居住4'),
            family_separate_address_4=data.get('別居住住所4'),

            # === FAMILY - Member 5 ===
            family_name_5=data.get('家族構成氏名5'),
            family_relation_5=data.get('家族構成続柄5'),
            family_age_5=parse_int(data.get('年齢5')),
            family_residence_5=data.get('居住5'),
            family_separate_address_5=data.get('別居住住所5'),

            # === LANGUAGE SKILLS (言語スキル - actual model fields) ===
            can_speak=data.get('日本語話せる'),
            can_understand=data.get('日本語聞き取れる'),
            can_read_kana=data.get('ひらがな・カタカナ読める'),
            can_write_kana=data.get('ひらがな・カタカナ書ける'),

            # === PHYSICAL (身体情報) ===
            height=parse_float(data.get('身長')),
            weight=parse_float(data.get('体重')),
            shoe_size=parse_float(data.get('靴のサイズ')),
            waist=parse_int(data.get('ウエスト')),
            blood_type=data.get('血液型'),
            vision_left=parse_float(data.get('視力左　左')),
            vision_right=parse_float(data.get('視力左　右')),
            allergy_exists=data.get('アレルギー　有'),

            # === WORK EXPERIENCE (経験作業 - Boolean fields) ===
            exp_nc_lathe=parse_bool(data.get('NC機械')),
            exp_painting=parse_bool(data.get('塗装')),
            exp_forklift=parse_bool(data.get('ﾌｫｰｸﾘﾌﾄ')),
            exp_packing=parse_bool(data.get('梱包（電子）')),
            exp_food_processing=parse_bool(data.get('食品製造')),
            exp_line_leader=parse_bool(data.get('ﾌｫｰｸﾘﾌﾄﾘｰﾀﾞｰ')),
            exp_other=data.get('その他'),

            # === COMMUTE (通勤) ===
            commute_method=data.get('通勤方法'),

            # === INTERVIEW (面接・検査) ===
            interview_result=data.get('面接後即OK'),
            antigen_test_kit=data.get('非常召集キット'),
            antigen_test_date=parse_date(data.get('非常召集キット数量')),

            # === JAPANESE ABILITY (日本語能力) ===
            japanese_qualification=data.get('日本語能力資格'),
            japanese_level=data.get('スキルLevel'),

            # === EMERGENCY CONTACT (緊急連絡先) ===
            emergency_contact_name=data.get('緊急連絡先　氏名'),
            emergency_contact_relation=data.get('緊急連絡先　名前'),
            emergency_contact_phone=data.get('緊急連絡先　電話番号'),

            # === EDUCATION (学歴) ===
            major=data.get('最終学歴'),

            # === WORK HISTORY Entry 7 (only this one exists in model) ===
            work_history_company_7=data.get('職歴年社名7'),
            work_history_entry_company_7=data.get('職歴入社会社名7'),
            work_history_exit_company_7=data.get('職歴退社会社名7'),

            # === STATUS ===
            status=CandidateStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        db.add(candidate)
        stats['imported'] += 1
        return True

    except Exception as e:
        stats['errors'] += 1
        logger.error(f"  Error importing {rirekisho_id}: {str(e)[:100]}")
        return False


def import_candidates_batch(json_file: str, batch_size: int = 100):
    """Import candidates in batches with progress reporting"""

    logger.info("=" * 80)
    logger.info("IMPORTING CANDIDATES WITH PHOTOS")
    logger.info("=" * 80)

    # Load JSON file
    logger.info(f"Loading JSON file: {json_file}")

    if not Path(json_file).exists():
        logger.error(f"File not found: {json_file}")
        return False

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    candidates = data.get('candidates', [])
    total = len(candidates)

    logger.info(f"Total candidates to import: {total}")
    logger.info(f"Batch size: {batch_size}")
    logger.info("")

    # Statistics
    stats = {
        'imported': 0,
        'duplicates': 0,
        'errors': 0,
        'with_photo': 0
    }

    db = SessionLocal()
    start_time = datetime.now()

    try:
        for i, candidate_data in enumerate(candidates, 1):
            # Import candidate
            import_candidate(db, candidate_data, stats)

            # Commit in batches
            if i % batch_size == 0:
                db.commit()
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = i / elapsed if elapsed > 0 else 0
                logger.info(f"  Progress: {i}/{total} ({i/total*100:.1f}%) - "
                          f"{stats['imported']} imported, {stats['with_photo']} with photos - "
                          f"{rate:.1f} records/sec")

        # Final commit
        db.commit()

        # Final report
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("")
        logger.info("=" * 80)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total processed:     {total}")
        logger.info(f"✓ Imported:          {stats['imported']}")
        logger.info(f"📸 With photos:       {stats['with_photo']}")
        logger.info(f"⚠ Duplicates:        {stats['duplicates']}")
        logger.info(f"✗ Errors:            {stats['errors']}")
        logger.info(f"⏱ Time elapsed:      {elapsed:.1f} seconds")
        logger.info(f"⚡ Import rate:       {total/elapsed:.1f} records/sec")
        logger.info("=" * 80)

        # Verify in database
        logger.info("")
        logger.info("Verifying database records...")
        total_candidates = db.query(Candidate).count()
        candidates_with_photos = db.query(Candidate).filter(Candidate.photo_data_url.isnot(None)).count()
        logger.info(f"Total candidates in DB: {total_candidates}")
        logger.info(f"Candidates with photos: {candidates_with_photos}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error during import: {e}")
        return False

    finally:
        db.close()


def main():
    """Main entry point"""
    json_file = '/app/config/all_candidates_with_photos.json'

    success = import_candidates_batch(json_file, batch_size=100)

    if success:
        logger.info("✅ Import completed successfully")
        return 0
    else:
        logger.error("❌ Import failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

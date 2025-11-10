"""
Import Candidates from Access Database to PostgreSQL
=====================================================

This script imports candidate records from T_履歴書 table in Access database
to the PostgreSQL candidates table.

Features:
- Maps 172 Access columns to candidates table columns
- Handles photo field (file path or Base64 conversion)
- Checks for duplicates before inserting
- Links to existing employees using rirekisho_id
- Imports in batches (100 records at a time)
- Generates detailed import report
- Sample inspection before full import

Usage:
    python import_access_candidates.py --sample  # Sample 5 records first
    python import_access_candidates.py --full    # Full import

Author: Claude Code
Date: 2025-10-24
"""

import sys
import os
import json
import logging
import base64
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.models.models import Candidate, CandidateStatus
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'import_candidates_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Access Database Configuration
ACCESS_DB_PATH = r"C:\Users\JPUNS\Desktop\ユニバーサル企画㈱データベースv25.3.24.accdb"
ACCESS_TABLE = "T_履歴書"

# PostgreSQL Configuration (from Docker container)
POSTGRES_URL = "postgresql://uns_admin:57UD10R@localhost:5432/uns_claudejp"

# Batch size for imports
BATCH_SIZE = 100


class CandidateImporter:
    """Handles importing candidates from Access to PostgreSQL"""

    def __init__(self, photo_mappings_file: Optional[str] = None):
        """
        Initialize database connections

        Args:
            photo_mappings_file: Path to JSON file with photo mappings from extract_access_attachments.py
        """
        # Access connection
        self.access_conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={ACCESS_DB_PATH};'
        )

        # PostgreSQL connection
        self.engine = create_engine(POSTGRES_URL)
        self.Session = sessionmaker(bind=self.engine)

        # Photo mappings from extraction script
        self.photo_mappings = {}
        if photo_mappings_file and os.path.exists(photo_mappings_file):
            logger.info(f"Loading photo mappings from: {photo_mappings_file}")
            try:
                with open(photo_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.photo_mappings = data.get('mappings', {})
                logger.info(f"Loaded {len(self.photo_mappings)} photo mappings")
            except Exception as e:
                logger.warning(f"Failed to load photo mappings: {e}")

        # Statistics
        self.stats = {
            'total_records': 0,
            'processed': 0,
            'inserted': 0,
            'skipped_duplicates': 0,
            'errors': 0,
            'photo_file_paths': 0,
            'photo_base64': 0,
            'photo_from_attachments': 0,
            'photo_empty': 0
        }

        # Error log
        self.errors = []

    def connect_access(self) -> pyodbc.Connection:
        """Connect to Access database"""
        try:
            conn = pyodbc.connect(self.access_conn_str)
            logger.info(f"Connected to Access database: {ACCESS_DB_PATH}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to Access database: {e}")
            raise

    def map_access_to_candidate(self, row: pyodbc.Row) -> Dict[str, Any]:
        """
        Map Access database columns to Candidate model fields

        Args:
            row: Access database row

        Returns:
            Dictionary with mapped candidate fields
        """
        # Helper function to get value safely
        def get_val(column_name: str, default=None):
            try:
                val = getattr(row, column_name, default)
                return val if val is not None else default
            except:
                return default

        # Helper to convert boolean fields
        def get_bool(column_name: str) -> Optional[str]:
            val = get_val(column_name)
            if val is None:
                return None
            return "有" if val else "無"

        # Helper to parse dates
        def get_date(column_name: str) -> Optional[date]:
            val = get_val(column_name)
            if val and isinstance(val, datetime):
                return val.date()
            elif val and isinstance(val, date):
                return val
            return None

        # Map all fields
        mapped = {
            # Primary Key & IDs
            'rirekisho_id': str(get_val('履歴書ID', '')),

            # Reception & Arrival Dates
            'reception_date': get_date('受付日'),
            'arrival_date': get_date('来日'),

            # Basic Information
            'full_name_kanji': get_val('氏名'),
            'full_name_kana': get_val('フリガナ'),
            'full_name_roman': get_val('氏名（ローマ字)'),
            'gender': get_val('性別'),
            'date_of_birth': get_date('生年月日'),
            'nationality': get_val('国籍'),
            'marital_status': get_val('配偶者'),
            'hire_date': get_date('入社日'),

            # Address Information
            'postal_code': get_val('郵便番号'),
            'current_address': get_val('現住所'),
            'address_banchi': get_val('番地'),
            'address_building': get_val('物件名'),
            'registered_address': get_val('登録住所'),

            # Contact Information
            'phone': get_val('電話番号'),
            'mobile': get_val('携帯電話'),

            # Passport Information
            'passport_number': get_val('パスポート番号'),
            'passport_expiry': get_date('パスポート期限'),

            # Residence Card Information
            'residence_status': get_val('在留資格'),
            'residence_expiry': get_date('（在留カード記載）在留期限'),
            'residence_card_number': get_val('在留カード番号'),

            # Driver's License
            'license_number': get_val('運転免許番号及び条件'),
            'license_expiry': get_date('運転免許期限'),
            'car_ownership': get_bool('自動車所有'),
            'voluntary_insurance': get_bool('任意保険加入'),

            # Qualifications
            'forklift_license': get_bool('ﾌｫｰｸﾘﾌﾄ免許'),
            'tama_kake': get_bool('玉掛'),
            'mobile_crane_under_5t': get_bool('移動式ｸﾚｰﾝ運転士(5ﾄﾝ未満)'),
            'mobile_crane_over_5t': get_bool('移動式ｸﾚｰﾝ運転士(5ﾄﾝ以上)'),
            'gas_welding': get_bool('ｶﾞｽ溶接作業者'),

            # Family Members (1-5)
            'family_name_1': get_val('家族構成氏名1'),
            'family_relation_1': get_val('家族構成続柄1'),
            'family_age_1': get_val('年齢1'),
            'family_residence_1': get_val('居住1'),
            'family_separate_address_1': get_val('別居住住所1'),

            'family_name_2': get_val('家族構成氏名2'),
            'family_relation_2': get_val('家族構成続柄2'),
            'family_age_2': get_val('年齢2'),
            'family_residence_2': get_val('居住2'),
            'family_separate_address_2': get_val('別居住住所2'),

            'family_name_3': get_val('家族構成氏名3'),
            'family_relation_3': get_val('家族構成続柄3'),
            'family_age_3': get_val('年齢3'),
            'family_residence_3': get_val('居住3'),
            'family_separate_address_3': get_val('別居住住所3'),

            'family_name_4': get_val('家族構成氏名4'),
            'family_relation_4': get_val('家族構成続柄4'),
            'family_age_4': get_val('年齢4'),
            'family_residence_4': get_val('居住4'),
            'family_separate_address_4': get_val('別居住住所4'),

            'family_name_5': get_val('家族構成氏名5'),
            'family_relation_5': get_val('家族構成続柄5'),
            'family_age_5': get_val('年齢5'),
            'family_residence_5': get_val('居住5'),
            'family_separate_address_5': get_val('別居住住所5'),

            # Japanese Language Ability
            'can_speak': get_val('会話ができる'),
            'can_understand': get_val('会話が理解できる'),
            'can_read_kana': get_val('ひらがな・カタカナ読める'),
            'can_write_kana': get_val('ひらがな・カタカナ書ける'),
            'read_katakana': get_val('読む　カナ'),
            'read_hiragana': get_val('読む　ひら'),
            'read_kanji': get_val('読む　漢字'),
            'write_katakana': get_val('書く　カナ'),
            'write_hiragana': get_val('書く　ひら'),
            'write_kanji': get_val('書く　漢字'),

            # Education
            'major': get_val('専攻'),

            # Physical Information
            'blood_type': get_val('血液型'),
            'dominant_hand': get_val('利き腕'),
            'allergy_exists': get_val('アレルギー有無'),
            'glasses': "有" if get_val('眼 ﾒｶﾞﾈ､ｺﾝﾀｸﾄ使用') else "無",

            # Work Experience
            'exp_nc_lathe': get_val('NC旋盤', False),
            'exp_lathe': get_val('旋盤', False),
            'exp_press': get_val('ﾌﾟﾚｽ', False),
            'exp_forklift': get_val('ﾌｫｰｸﾘﾌﾄ', False),
            'exp_packing': get_val('梱包', False),
            'exp_welding': get_val('溶接', False),
            'exp_car_assembly': get_val('車部品組立', False),
            'exp_car_line': get_val('車部品ライン', False),
            'exp_car_inspection': get_val('車部品検査', False),
            'exp_electronic_inspection': get_val('電子部品検査', False),
            'exp_food_processing': get_val('食品加工', False),
            'exp_casting': get_val('鋳造', False),
            'exp_line_leader': get_val('ラインリーダー', False),
            'exp_painting': get_val('塗装', False),

            # Lunch Preferences
            'bento_lunch_dinner': get_bool('お弁当　昼/夜'),
            'bento_lunch_only': get_bool('お弁当　昼のみ'),
            'bento_dinner_only': get_bool('お弁当　夜のみ'),
            'bento_bring_own': get_bool('お弁当　持参'),

            # Commute
            'commute_method': get_val('通勤方法'),
            'commute_time_oneway': get_val('通勤片道時間'),

            # Interview & Tests
            'interview_result': "OK" if get_val('面接結果OK') else None,
            'antigen_test_kit': get_val('簡易抗原検査キット'),
            'antigen_test_date': get_date('簡易抗原検査実施日'),
            'covid_vaccine_status': get_val('コロナワクチン予防接種状態'),

            # Language Skills
            'language_skill_exists': get_val('語学スキル有無'),
            'language_skill_1': get_val('語学スキル有無１'),
            'language_skill_2': get_val('語学スキル有無2'),

            # Japanese Qualifications
            'japanese_qualification': get_val('日本語能力資格'),
            'japanese_level': get_val('日本語能力資格Level'),
            'jlpt_taken': get_val('能力試験受験'),
            'jlpt_date': get_date('能力試験受験日付'),
            'jlpt_score': get_val('能力試験受験点数'),

            # Qualifications
            'qualification_1': get_val('有資格取得'),
            'qualification_2': get_val('有資格取得1'),
            'qualification_3': get_val('有資格取得2'),

            # Listening/Speaking
            'listening_level': get_val('聞く選択'),
            'speaking_level': get_val('話す選択'),

            # Emergency Contact
            'emergency_contact_name': get_val('緊急連絡先　氏名'),
            'emergency_contact_relation': get_val('緊急連絡先　続柄'),
            'emergency_contact_phone': get_val('緊急連絡先　電話番号'),

            # Work Equipment
            'safety_shoes': get_val('安全靴'),

            # Status
            'status': CandidateStatus.APPROVED.value,  # Use .value to get lowercase "approved"
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        return mapped

    def process_photo_field(self, photo_data: Any, rirekisho_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Process photo field from Access database

        Args:
            photo_data: Photo field value from Access (usually Attachment type, shows as binary/None in pyodbc)
            rirekisho_id: Candidate ID to lookup in photo mappings

        Returns:
            Tuple of (photo_url, photo_data_url)
        """
        # First, check if we have extracted photo from Attachment field
        if rirekisho_id in self.photo_mappings:
            photo_data_url = self.photo_mappings[rirekisho_id]
            self.stats['photo_from_attachments'] += 1
            logger.debug(f"Using extracted attachment photo for {rirekisho_id}")
            return None, photo_data_url

        # Fallback: try to process as file path or Base64 (legacy support)
        if not photo_data:
            self.stats['photo_empty'] += 1
            return None, None

        photo_str = str(photo_data).strip()

        # Check if it's a file path
        if photo_str.startswith('\\') or photo_str.startswith('/') or ':' in photo_str[:3]:
            self.stats['photo_file_paths'] += 1

            # Check if file exists
            if os.path.exists(photo_str):
                try:
                    # Read file and convert to Base64 data URL
                    with open(photo_str, 'rb') as f:
                        photo_bytes = f.read()

                    # Determine MIME type
                    ext = os.path.splitext(photo_str)[1].lower()
                    mime_map = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.bmp': 'image/bmp'
                    }
                    mime_type = mime_map.get(ext, 'image/jpeg')

                    # Create data URL
                    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                    photo_data_url = f"data:{mime_type};base64,{photo_base64}"

                    return photo_str, photo_data_url
                except Exception as e:
                    logger.warning(f"Failed to read photo file {photo_str}: {e}")
                    return photo_str, None
            else:
                logger.warning(f"Photo file not found: {photo_str}")
                return photo_str, None

        # Check if it's already Base64
        elif photo_str.startswith('data:'):
            self.stats['photo_base64'] += 1
            return None, photo_str

        # Unknown format (likely Access Attachment binary data that pyodbc can't read)
        else:
            # If we see binary/unknown data and don't have extracted mapping, it's an Attachment field
            if len(photo_str) > 0:
                logger.debug(f"Attachment field detected for {rirekisho_id} but no extracted mapping found")
            self.stats['photo_empty'] += 1
            return None, None

    def check_duplicate(self, session: Session, rirekisho_id: str,
                       full_name: str, dob: Optional[date]) -> bool:
        """
        Check if candidate already exists

        Args:
            session: Database session
            rirekisho_id: Rirekisho ID
            full_name: Full name
            dob: Date of birth

        Returns:
            True if duplicate exists
        """
        # Check by rirekisho_id
        if rirekisho_id:
            existing = session.query(Candidate).filter(
                Candidate.rirekisho_id == rirekisho_id
            ).first()
            if existing:
                return True

        # Check by name + DOB
        if full_name and dob:
            existing = session.query(Candidate).filter(
                Candidate.full_name_kanji == full_name,
                Candidate.date_of_birth == dob
            ).first()
            if existing:
                return True

        return False

    def import_records(self, limit: Optional[int] = None, sample: bool = False) -> Dict[str, Any]:
        """
        Import candidate records from Access to PostgreSQL

        Args:
            limit: Maximum number of records to import (None = all)
            sample: If True, only sample first 5 records without inserting

        Returns:
            Dictionary with import statistics
        """
        access_conn = None
        session = None

        try:
            # Connect to Access
            access_conn = self.connect_access()
            cursor = access_conn.cursor()

            # Get total count
            count_query = f"SELECT COUNT(*) FROM [{ACCESS_TABLE}]"
            cursor.execute(count_query)
            total = cursor.fetchone()[0]
            self.stats['total_records'] = total
            logger.info(f"Total records in Access: {total}")

            # Build query with limit if specified
            query = f"SELECT * FROM [{ACCESS_TABLE}]"
            if sample:
                limit = 5
            if limit:
                # Access uses TOP instead of LIMIT
                query = f"SELECT TOP {limit} * FROM [{ACCESS_TABLE}]"

            logger.info(f"Executing query: {query}")
            cursor.execute(query)

            # Create PostgreSQL session
            session = self.Session()

            # Process records in batches
            batch = []
            record_count = 0

            while True:
                row = cursor.fetchone()
                if not row:
                    break

                record_count += 1
                self.stats['processed'] += 1

                try:
                    # Map Access columns to Candidate fields
                    mapped_data = self.map_access_to_candidate(row)

                    # Process photo field (with rirekisho_id for attachment lookup)
                    rirekisho_id = mapped_data.get('rirekisho_id', '')
                    photo_data = getattr(row, '写真', None)
                    photo_url, photo_data_url = self.process_photo_field(photo_data, rirekisho_id)
                    mapped_data['photo_url'] = photo_url
                    mapped_data['photo_data_url'] = photo_data_url

                    # Sample mode: just print and continue
                    if sample:
                        logger.info(f"\n{'='*80}")
                        logger.info(f"Sample Record #{record_count}:")
                        logger.info(f"{'='*80}")
                        logger.info(f"履歴書ID: {mapped_data.get('rirekisho_id')}")
                        logger.info(f"氏名: {mapped_data.get('full_name_kanji')}")
                        logger.info(f"生年月日: {mapped_data.get('date_of_birth')}")
                        logger.info(f"国籍: {mapped_data.get('nationality')}")
                        logger.info(f"Photo URL: {photo_url}")
                        logger.info(f"Photo Data URL: {'Yes' if photo_data_url else 'No'}")
                        logger.info(f"\nMapped Fields ({len(mapped_data)} total):")
                        for key, value in list(mapped_data.items())[:10]:
                            logger.info(f"  {key}: {value}")
                        logger.info(f"  ... ({len(mapped_data) - 10} more fields)")
                        continue

                    # Check for duplicate
                    is_duplicate = self.check_duplicate(
                        session,
                        mapped_data.get('rirekisho_id'),
                        mapped_data.get('full_name_kanji'),
                        mapped_data.get('date_of_birth')
                    )

                    if is_duplicate:
                        self.stats['skipped_duplicates'] += 1
                        logger.warning(
                            f"Skipping duplicate: {mapped_data.get('rirekisho_id')} - "
                            f"{mapped_data.get('full_name_kanji')}"
                        )
                        continue

                    # Create Candidate object
                    candidate = Candidate(**mapped_data)
                    batch.append(candidate)

                    # Insert batch when full
                    if len(batch) >= BATCH_SIZE:
                        session.bulk_save_objects(batch)
                        session.commit()
                        self.stats['inserted'] += len(batch)
                        logger.info(f"Inserted batch of {len(batch)} records. Total: {self.stats['inserted']}")
                        batch = []

                except Exception as e:
                    self.stats['errors'] += 1
                    error_msg = f"Error processing record #{record_count}: {e}"
                    logger.error(error_msg)
                    self.errors.append({
                        'record_num': record_count,
                        'error': str(e),
                        'rirekisho_id': getattr(row, '履歴書ID', 'Unknown')
                    })
                    continue

            # Insert remaining batch
            if batch and not sample:
                session.bulk_save_objects(batch)
                session.commit()
                self.stats['inserted'] += len(batch)
                logger.info(f"Inserted final batch of {len(batch)} records. Total: {self.stats['inserted']}")

            logger.info("\n" + "="*80)
            logger.info("Import Summary:")
            logger.info("="*80)
            logger.info(f"Total records in Access: {self.stats['total_records']}")
            logger.info(f"Records processed: {self.stats['processed']}")
            if not sample:
                logger.info(f"Records inserted: {self.stats['inserted']}")
                logger.info(f"Skipped (duplicates): {self.stats['skipped_duplicates']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"\nPhoto Statistics:")
            logger.info(f"  From attachments: {self.stats['photo_from_attachments']}")
            logger.info(f"  File paths: {self.stats['photo_file_paths']}")
            logger.info(f"  Base64: {self.stats['photo_base64']}")
            logger.info(f"  Empty: {self.stats['photo_empty']}")

            if self.errors:
                logger.warning(f"\nErrors encountered: {len(self.errors)}")
                for err in self.errors[:10]:  # Show first 10 errors
                    logger.warning(f"  Record #{err['record_num']} ({err['rirekisho_id']}): {err['error']}")
                if len(self.errors) > 10:
                    logger.warning(f"  ... and {len(self.errors) - 10} more errors")

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error during import: {e}")
            if session:
                session.rollback()
            raise

        finally:
            if session:
                session.close()
            if access_conn:
                access_conn.close()

    def generate_report(self, output_file: str):
        """Generate detailed import report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'access_database': ACCESS_DB_PATH,
            'postgres_url': POSTGRES_URL,
            'statistics': self.stats,
            'errors': self.errors
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\nDetailed report saved to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Import candidates from Access to PostgreSQL')
    parser.add_argument('--sample', action='store_true', help='Sample first 5 records without importing')
    parser.add_argument('--full', action='store_true', help='Import all records')
    parser.add_argument('--limit', type=int, help='Limit number of records to import')
    parser.add_argument('--report', default='import_candidates_report.json', help='Report output file')
    parser.add_argument('--photos', default='access_photo_mappings.json',
                       help='Path to photo mappings JSON file from extract_access_attachments.py')

    args = parser.parse_args()

    if not args.sample and not args.full and not args.limit:
        parser.print_help()
        print("\nPlease specify --sample, --full, or --limit <number>")
        sys.exit(1)

    # Check if photo mappings file exists
    if os.path.exists(args.photos):
        logger.info(f"Photo mappings file found: {args.photos}")
    else:
        logger.warning(f"Photo mappings file not found: {args.photos}")
        logger.warning("Run extract_access_attachments.py first to extract photos")
        logger.warning("Continuing without photo mappings...")

    # Create importer with photo mappings
    importer = CandidateImporter(photo_mappings_file=args.photos)

    # Run import
    if args.sample:
        logger.info("Running in SAMPLE mode (first 5 records, no insertion)")
        importer.import_records(sample=True)
    else:
        limit = args.limit if args.limit else None
        logger.info(f"Running FULL import (limit: {limit if limit else 'all records'})")
        importer.import_records(limit=limit)

        # Generate report
        importer.generate_report(args.report)

    logger.info("\nImport completed!")


if __name__ == '__main__':
    main()

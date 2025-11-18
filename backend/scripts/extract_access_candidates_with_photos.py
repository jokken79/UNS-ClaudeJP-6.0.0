"""
Extract candidates and photos from Access Database with Base64 encoding
========================================================================

This script extracts candidate data and their photos from the Access database.
It converts photos to Base64 Data URLs for direct insertion into PostgreSQL.

Requirements:
- pyodbc (for Access database connection)
- Pillow (for image processing)

Usage:
    # Run on Windows host (outside Docker)
    python extract_access_candidates_with_photos.py

Output:
    - candidates_with_photos.json: Complete candidate data with Base64 photos
    - Photos also saved to temporary folder for verification
"""

import pyodbc
import json
import logging
import os
import base64
import io
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from PIL import Image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'extract_access_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
project_root = Path(__file__).parent.parent.parent
ACCESS_DB_PATH = project_root / "BASEDATEJP" / "ユニバーサル企画㈱データベースv25.3.24_be.accdb"
ACCESS_TABLE = "T_履歴書"
OUTPUT_JSON = project_root / "config" / "candidates_with_photos.json"
TEMP_PHOTOS_DIR = project_root / "temp" / "extracted_photos"

# Ensure directories exist
TEMP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime, date, and Decimal objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def convert_photo_to_base64(photo_data):
    """
    Convert binary photo data to Base64 Data URL

    Args:
        photo_data: Binary photo data from Access

    Returns:
        str: Base64 Data URL (data:image/jpeg;base64,...)
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(photo_data))

        # Convert to RGB if necessary (removes alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background

        # Optimize size: resize if too large
        max_dimension = 800
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Save to bytes buffer with compression
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        # Convert to Base64
        b64_data = base64.b64encode(buffer.read()).decode('utf-8')

        # Create Data URL
        data_url = f"data:image/jpeg;base64,{b64_data}"

        return data_url

    except Exception as e:
        logger.warning(f"Failed to convert photo to Base64: {e}")
        return None


def map_access_to_postgres(access_record, photo_data_url=None):
    """
    Map Access database fields to PostgreSQL candidate schema

    Args:
        access_record: Dictionary with Access field names
        photo_data_url: Base64 Data URL of photo

    Returns:
        dict: Mapped candidate data for PostgreSQL
    """

    # Basic mapping (adjust field names based on actual Access schema)
    candidate = {
        # Identity fields
        "rirekisho_id": access_record.get("履歴書番号") or access_record.get("ID"),
        "full_name_kanji": access_record.get("氏名") or access_record.get("名前"),
        "full_name_furigana": access_record.get("フリガナ"),
        "full_name_roman": access_record.get("ローマ字氏名"),

        # Photo
        "photo_data_url": photo_data_url,

        # Personal info
        "date_of_birth": access_record.get("生年月日"),
        "age": access_record.get("年齢"),
        "gender": access_record.get("性別"),
        "nationality": access_record.get("国籍"),

        # Contact
        "email": access_record.get("メールアドレス") or access_record.get("Email"),
        "phone": access_record.get("電話番号") or access_record.get("携帯電話"),
        "emergency_contact": access_record.get("緊急連絡先"),

        # Address
        "postal_code": access_record.get("郵便番号"),
        "address": access_record.get("住所"),

        # Residence status
        "residence_card_number": access_record.get("在留カード番号"),
        "visa_type": access_record.get("在留資格"),
        "residence_expiry": access_record.get("在留期限"),

        # Education
        "education_level": access_record.get("最終学歴"),
        "school_name": access_record.get("学校名"),
        "graduation_date": access_record.get("卒業年月"),

        # Work experience
        "previous_companies": access_record.get("職歴"),
        "skills": access_record.get("資格・スキル"),

        # Japanese language
        "japanese_level": access_record.get("日本語レベル") or access_record.get("日本語能力"),
        "jlpt_level": access_record.get("JLPT"),

        # Employment status
        "employment_status": access_record.get("雇用状態") or access_record.get("状態"),
        "entry_date": access_record.get("入社日"),
        "leave_date": access_record.get("退社日"),

        # Documents
        "has_driver_license": bool(access_record.get("運転免許証")),
        "driver_license_number": access_record.get("免許証番号"),

        # Banking
        "bank_name": access_record.get("銀行名"),
        "bank_branch": access_record.get("支店名"),
        "bank_account_number": access_record.get("口座番号"),
        "bank_account_holder": access_record.get("口座名義"),

        # Additional info
        "notes": access_record.get("備考") or access_record.get("メモ"),

        # Metadata
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # Remove None values
    candidate = {k: v for k, v in candidate.items() if v is not None}

    return candidate


def extract_candidates_and_photos():
    """
    Extract candidates and their photos from Access database

    Returns:
        tuple: (candidate_count, photo_count, json_file_path)
    """
    try:
        # Build connection string
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={ACCESS_DB_PATH};'
        )

        logger.info("=" * 80)
        logger.info("EXTRACTING CANDIDATES WITH PHOTOS FROM ACCESS DATABASE")
        logger.info("=" * 80)
        logger.info(f"Database: {ACCESS_DB_PATH}")
        logger.info(f"Table: {ACCESS_TABLE}")
        logger.info(f"Output JSON: {OUTPUT_JSON}")
        logger.info(f"Temp photos: {TEMP_PHOTOS_DIR.absolute()}")
        logger.info("")

        # Check if database file exists
        if not ACCESS_DB_PATH.exists():
            logger.error(f"Database file not found: {ACCESS_DB_PATH}")
            return 0, 0, None

        logger.info("Connecting to Access database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Get all records
        query = f"SELECT * FROM [{ACCESS_TABLE}]"
        logger.info(f"Executing query: {query}")
        cursor.execute(query)

        # Get column names
        columns = [column[0] for column in cursor.description]
        logger.info(f"Found {len(columns)} columns")
        logger.info(f"First 10 columns: {', '.join(columns[:10])}")

        # Find photo column
        photo_column = None
        for col in columns:
            if col.lower() in ['photo', 'picture', '写真', 'imagen', 'foto']:
                photo_column = col
                logger.info(f"Found photo column: {photo_column}")
                break

        if not photo_column:
            logger.warning("No photo column found! Will extract without photos.")

        # Fetch all rows
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} total records")
        logger.info("")

        # Process records
        candidates = []
        photo_count = 0
        records_with_photos = 0

        logger.info("Processing records...")
        for idx, row in enumerate(rows, 1):
            # Convert row to dictionary
            access_record = {}
            photo_data = None

            for i, column in enumerate(columns):
                value = row[i]

                # Handle photo data
                if column == photo_column and value is not None:
                    photo_data = value
                elif value is not None and not isinstance(value, bytes):
                    access_record[column] = value

            # Convert photo to Base64 if available
            photo_data_url = None
            if photo_data:
                photo_data_url = convert_photo_to_base64(photo_data)

                if photo_data_url:
                    photo_count += 1
                    records_with_photos += 1

                    # Also save photo to temp folder for verification
                    candidate_id = access_record.get("履歴書番号") or access_record.get("ID") or f"unknown_{idx}"
                    temp_photo_path = TEMP_PHOTOS_DIR / f"candidate_{candidate_id}.jpg"

                    try:
                        # Decode Base64 and save
                        photo_bytes = base64.b64decode(photo_data_url.split(',')[1])
                        with open(temp_photo_path, 'wb') as f:
                            f.write(photo_bytes)
                    except Exception as e:
                        logger.warning(f"Failed to save temp photo for record {idx}: {e}")

            # Map to PostgreSQL schema
            candidate = map_access_to_postgres(access_record, photo_data_url)
            candidates.append(candidate)

            # Progress update
            if idx % 50 == 0:
                logger.info(f"  Processed {idx}/{len(rows)} records ({photo_count} photos converted)")

        logger.info("")
        logger.info("Saving candidates to JSON...")

        # Save to JSON file
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

        logger.info(f"  ✓ Saved to: {OUTPUT_JSON}")

        # Get file size
        file_size_mb = OUTPUT_JSON.stat().st_size / (1024 * 1024)

        logger.info("")
        logger.info("=" * 80)
        logger.info("EXTRACTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Total candidates: {len(candidates)}")
        logger.info(f"Records with photos: {records_with_photos}")
        logger.info(f"Photos converted to Base64: {photo_count}")
        logger.info(f"JSON file size: {file_size_mb:.2f} MB")
        logger.info(f"JSON file: {OUTPUT_JSON}")
        logger.info(f"Temp photos: {TEMP_PHOTOS_DIR.absolute()}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify the JSON file was created successfully")
        logger.info("  2. Check temp photos folder to verify photo extraction")
        logger.info("  3. Use import_candidates_from_json.py to import into PostgreSQL")
        logger.info("=" * 80)

        conn.close()
        return len(candidates), photo_count, str(OUTPUT_JSON)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("EXTRACTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        logger.error("=" * 80)
        return 0, 0, None


if __name__ == '__main__':
    candidates, photos, json_file = extract_candidates_and_photos()

    if candidates > 0:
        print("\n✅ Extraction successful!")
        print(f"   Candidates extracted: {candidates}")
        print(f"   Photos converted: {photos}")
        print(f"   JSON file: {json_file}")
    else:
        print("\n❌ Extraction failed. Check the log file for details.")

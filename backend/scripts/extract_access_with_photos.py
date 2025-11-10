"""
Extract candidates and photos from Access Database
===================================================

This script extracts candidate data and their photos from the Access database.
It saves photos to a specified directory and creates a JSON mapping file.

Requirements:
- pyodbc (for Access database connection)
- Pillow (for image processing)

Usage:
    # Run on Windows host (outside Docker)
    python extract_access_with_photos.py

Output:
    - access_candidates_data.json: Candidate data
    - access_photo_mappings.json: Photo filename mappings
    - Photos saved to: ../uploads/photos/candidates/
"""

import pyodbc
import json
import logging
import os
import base64
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

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
ACCESS_DB_PATH = project_root / "base-datos" / "ユニバーサル企画㈱データベースv25.3.24.accdb"
ACCESS_TABLE = "T_履歴書"
OUTPUT_DATA_FILE = project_root / "config" / "access_candidates_data.json"
OUTPUT_PHOTOS_FILE = project_root / "config" / "access_photo_mappings.json"
PHOTOS_DIR = project_root / "uploads" / "photos" / "candidates"

# Ensure photos directory exists
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime, date, and bytes objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return super().default(obj)


def extract_candidates_and_photos():
    """
    Extract candidates and their photos from Access database

    Returns:
        tuple: (candidate_count, photo_count)
    """
    try:
        # Build connection string
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={ACCESS_DB_PATH};'
        )

        logger.info("=" * 80)
        logger.info("EXTRACTING CANDIDATES AND PHOTOS FROM ACCESS DATABASE")
        logger.info("=" * 80)
        logger.info(f"Database: {ACCESS_DB_PATH}")
        logger.info(f"Table: {ACCESS_TABLE}")
        logger.info(f"Photos directory: {PHOTOS_DIR.absolute()}")
        logger.info("")

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
        logger.info(f"Columns: {', '.join(columns[:10])}..." if len(columns) > 10 else f"Columns: {', '.join(columns)}")

        # Find photo column (usually named 'photo' or '写真' or 'Picture')
        photo_column = None
        for col in columns:
            if col.lower() in ['photo', 'picture', '写真', 'imagen']:
                photo_column = col
                logger.info(f"Found photo column: {photo_column}")
                break

        # Fetch all rows
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} records")
        logger.info("")

        # Convert to list of dicts and extract photos
        data = []
        photo_mappings = {}
        photo_count = 0

        logger.info("Processing records...")
        for idx, row in enumerate(rows, 1):
            record = {}
            photo_filename = None

            for i, column in enumerate(columns):
                value = row[i]

                # Handle photo data (binary)
                if column == photo_column and value is not None:
                    try:
                        # Generate unique filename
                        candidate_id = row[0] if row[0] else f"unknown_{idx}"  # First column is usually ID
                        photo_filename = f"candidate_{candidate_id}.jpg"
                        photo_path = PHOTOS_DIR / photo_filename

                        # Save photo to file
                        with open(photo_path, 'wb') as f:
                            f.write(value)

                        photo_count += 1
                        photo_mappings[str(candidate_id)] = photo_filename
                        record['photo_filename'] = photo_filename

                        if idx % 50 == 0:
                            logger.info(f"  Processed {idx}/{len(rows)} records ({photo_count} photos extracted)")

                    except Exception as e:
                        logger.warning(f"  Failed to extract photo for record {idx}: {e}")
                        record[column] = None
                else:
                    # Convert other data to JSON-serializable types
                    if value is not None and not isinstance(value, bytes):
                        record[column] = value
                    else:
                        record[column] = None

            data.append(record)

        logger.info("")
        logger.info("Saving candidate data...")
        # Save candidate data to JSON
        with open(OUTPUT_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        logger.info(f"  ✓ Saved to: {OUTPUT_DATA_FILE}")

        # Save photo mappings to JSON
        logger.info("Saving photo mappings...")
        with open(OUTPUT_PHOTOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(photo_mappings, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✓ Saved to: {OUTPUT_PHOTOS_FILE}")

        logger.info("")
        logger.info("=" * 80)
        logger.info("EXTRACTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Total candidates: {len(data)}")
        logger.info(f"Total photos extracted: {photo_count}")
        logger.info(f"Photos saved to: {PHOTOS_DIR.absolute()}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Copy the following files to your project root:")
        logger.info(f"     - {OUTPUT_DATA_FILE}")
        logger.info(f"     - {OUTPUT_PHOTOS_FILE}")
        logger.info(f"  2. Run REINSTALAR.bat to import candidates with photos")
        logger.info("=" * 80)

        conn.close()
        return len(data), photo_count

    except Exception as e:
        logger.error("=" * 80)
        logger.error("EXTRACTION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        logger.error("=" * 80)
        return 0, 0


if __name__ == '__main__':
    candidates, photos = extract_candidates_and_photos()

    if candidates > 0:
        print("\n✅ Extraction successful!")
        print(f"   Candidates: {candidates}")
        print(f"   Photos: {photos}")
    else:
        print("\n❌ Extraction failed. Check the log file for details.")

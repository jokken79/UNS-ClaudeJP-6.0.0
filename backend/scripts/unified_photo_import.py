"""
Unified Photo Import Service
=============================

This script consolidates all photo import functionality into a single CLI tool.

Replaces:
- import_photos_by_name.py
- import_photos_from_json.py
- import_photos_from_access.py (and v2, simple, corrected variants)
- extract_access_with_photos.py
- import_access_candidates_with_photos.py
- extract_access_attachments.py

Features:
- Extract photos from Access database
- Import photos to PostgreSQL candidates table
- Verify photo import status
- Generate detailed import reports
- Dry-run mode for safe testing
- Resume capability for interrupted imports
- Batch processing for large datasets

Usage:
    python unified_photo_import.py extract --dry-run
    python unified_photo_import.py extract --limit 10
    python unified_photo_import.py import --file access_photo_mappings.json
    python unified_photo_import.py import --resume-from 500
    python unified_photo_import.py verify
    python unified_photo_import.py report --csv-export report.csv

Requirements:
    - pywin32 (for Access extraction)
    - PostgreSQL running
    - SQLAlchemy, psycopg2

Author: Claude Code
Date: 2025-10-26
Version: 1.0
"""

import sys
import os
import json
import logging
import base64
import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import win32com.client
    import pythoncom
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'unified_photo_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Access Database Configuration
ACCESS_DB_PATH = r"D:\ユニバーサル企画㈱データベースv25.3.24.accdb"
ACCESS_TABLE = "T_履歴書"
PHOTO_FIELD = "写真"
ID_FIELD = "履歴書ID"

# PostgreSQL Configuration
POSTGRES_USER = os.getenv('POSTGRES_USER', 'uns_admin')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'uns_claudejp')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

if os.path.exists('/.dockerenv'):
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'db')
else:
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')

POSTGRES_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Output files
DEFAULT_OUTPUT_JSON = "access_photo_mappings.json"


class AccessPhotoExtractor:
    """Extracts photo attachments from Access database using COM automation"""

    def __init__(self):
        """Initialize extractor"""
        self.access_app = None
        self.db = None
        self.stats = {
            'total_records': 0,
            'processed': 0,
            'with_attachments': 0,
            'without_attachments': 0,
            'extraction_successful': 0,
            'extraction_failed': 0,
            'errors': 0
        }
        self.photo_mappings = {}
        self.errors = []

    def connect_access(self) -> bool:
        """Connect to Access database using COM automation"""
        if not HAS_WIN32COM:
            logger.error("pywin32 not installed. Cannot use COM automation.")
            logger.error("Install with: pip install pywin32")
            return False

        try:
            pythoncom.CoInitialize()
            logger.info("Creating Access application instance...")
            self.access_app = win32com.client.Dispatch("Access.Application")

            try:
                self.access_app.CloseCurrentDatabase()
            except:
                pass

            logger.info(f"Opening Access database: {ACCESS_DB_PATH}")
            self.access_app.OpenCurrentDatabase(ACCESS_DB_PATH)
            self.db = self.access_app.CurrentDb()

            logger.info("Successfully connected to Access database")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Access database: {e}")
            return False

    def close_access(self):
        """Close Access database and release COM objects"""
        try:
            if self.access_app:
                logger.info("Closing Access database...")
                self.access_app.CloseCurrentDatabase()
                self.access_app.Quit()
                self.access_app = None
                self.db = None
            pythoncom.CoUninitialize()
        except Exception as e:
            logger.warning(f"Error closing Access: {e}")

    def extract_attachment_data(self, attachment_field) -> Optional[str]:
        """Extract binary data from Attachment field and convert to Base64 data URL"""
        try:
            if not attachment_field.Value:
                return None

            attachment_rs = attachment_field.Value

            if attachment_rs.RecordCount == 0:
                return None

            attachment_rs.MoveFirst()

            filename = attachment_rs.Fields("FileName").Value
            file_type = attachment_rs.Fields("FileType").Value
            file_data = attachment_rs.Fields("FileData").Value

            logger.debug(f"Found attachment: {filename} (type: {file_type})")

            if isinstance(file_data, (bytes, bytearray)):
                photo_bytes = bytes(file_data)
            else:
                photo_bytes = bytes(file_data)

            ext = os.path.splitext(filename)[1].lower() if filename else ''
            mime_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_map.get(ext, 'image/jpeg')

            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            photo_data_url = f"data:{mime_type};base64,{photo_base64}"

            logger.debug(f"Converted to data URL (length: {len(photo_data_url)})")
            return photo_data_url

        except Exception as e:
            logger.error(f"Error extracting attachment data: {e}")
            raise

    def extract_photos(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Extract photos from Access database"""
        if not self.connect_access():
            logger.error("Cannot proceed without Access connection")
            return self.stats

        try:
            sql = f"SELECT [{ID_FIELD}], [{PHOTO_FIELD}] FROM [{ACCESS_TABLE}]"

            if limit:
                sql = f"SELECT TOP {limit} [{ID_FIELD}], [{PHOTO_FIELD}] FROM [{ACCESS_TABLE}]"

            logger.info(f"Executing query: {sql}")
            if dry_run:
                logger.info("DRY RUN MODE - No data will be saved")

            recordset = self.db.OpenRecordset(sql)

            recordset.MoveLast()
            self.stats['total_records'] = recordset.RecordCount
            recordset.MoveFirst()

            logger.info(f"Total records to process: {self.stats['total_records']}")

            record_num = 0

            while not recordset.EOF:
                record_num += 1
                self.stats['processed'] += 1

                try:
                    rirekisho_id = recordset.Fields(ID_FIELD).Value

                    if not rirekisho_id:
                        logger.warning(f"Record #{record_num} has no ID, skipping")
                        recordset.MoveNext()
                        continue

                    rirekisho_id = str(rirekisho_id).strip()

                    attachment_field = recordset.Fields(PHOTO_FIELD)

                    if not attachment_field.Value or attachment_field.Value.RecordCount == 0:
                        self.stats['without_attachments'] += 1
                        logger.debug(f"Record #{record_num} ({rirekisho_id}): No attachments")
                        recordset.MoveNext()
                        continue

                    self.stats['with_attachments'] += 1

                    logger.info(f"Processing record #{record_num} ({rirekisho_id})...")

                    if not dry_run:
                        photo_data_url = self.extract_attachment_data(attachment_field)

                        if photo_data_url:
                            self.stats['extraction_successful'] += 1
                            self.photo_mappings[rirekisho_id] = photo_data_url
                            logger.info(f"  SUCCESS: Extracted photo for {rirekisho_id}")
                        else:
                            self.stats['extraction_failed'] += 1
                            logger.warning(f"  FAILED: Could not extract photo data")
                    else:
                        self.stats['extraction_successful'] += 1
                        logger.info(f"  DRY RUN: Would extract photo for {rirekisho_id}")

                except Exception as e:
                    self.stats['errors'] += 1
                    error_msg = f"Error processing record #{record_num}: {e}"
                    logger.error(error_msg)
                    self.errors.append({
                        'record_num': record_num,
                        'rirekisho_id': rirekisho_id if 'rirekisho_id' in locals() else 'Unknown',
                        'error': str(e)
                    })

                finally:
                    recordset.MoveNext()

            recordset.Close()

            logger.info("\n" + "="*80)
            logger.info("Extraction Summary:")
            logger.info("="*80)
            logger.info(f"Total records: {self.stats['total_records']}")
            logger.info(f"Records processed: {self.stats['processed']}")
            logger.info(f"With attachments: {self.stats['with_attachments']}")
            logger.info(f"Without attachments: {self.stats['without_attachments']}")
            logger.info(f"Extraction successful: {self.stats['extraction_successful']}")
            logger.info(f"Extraction failed: {self.stats['extraction_failed']}")
            logger.info(f"Errors: {self.stats['errors']}")

            if self.errors:
                logger.warning(f"\nErrors encountered: {len(self.errors)}")
                for err in self.errors[:10]:
                    logger.warning(f"  Record #{err['record_num']} ({err['rirekisho_id']}): {err['error']}")
                if len(self.errors) > 10:
                    logger.warning(f"  ... and {len(self.errors) - 10} more errors")

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error during extraction: {e}")
            raise

        finally:
            self.close_access()

    def save_mappings(self, output_file: str):
        """Save photo mappings to JSON file"""
        if not self.photo_mappings:
            logger.warning("No photo mappings to save")
            return

        output_data = {
            'timestamp': datetime.now().isoformat(),
            'access_database': ACCESS_DB_PATH,
            'table': ACCESS_TABLE,
            'photo_field': PHOTO_FIELD,
            'statistics': self.stats,
            'mappings': self.photo_mappings
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"\nPhoto mappings saved to: {output_file}")
            logger.info(f"Total mappings: {len(self.photo_mappings)}")

        except Exception as e:
            logger.error(f"Failed to save mappings: {e}")


class PhotoImporter:
    """Imports photos from JSON to PostgreSQL database"""

    def __init__(self):
        """Initialize importer"""
        self.engine = None
        self.db = None
        self.stats = {
            'total_photos': 0,
            'updated': 0,
            'skipped': 0,
            'not_found': 0,
            'errors': 0
        }

    def connect_db(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            safe_url = POSTGRES_URL.replace(f':{POSTGRES_PASSWORD}@', ':****@') if POSTGRES_PASSWORD else POSTGRES_URL
            logger.info(f"Connecting to PostgreSQL: {safe_url}")
            self.engine = create_engine(POSTGRES_URL)
            Session = sessionmaker(bind=self.engine)
            self.db = Session()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def close_db(self):
        """Close database connection"""
        if self.db:
            self.db.close()

    def import_photos(self, photo_file: str, resume_from: Optional[int] = None,
                     dry_run: bool = False, batch_size: int = 50) -> Dict[str, Any]:
        """Import photos from JSON file to PostgreSQL"""
        logger.info("=" * 80)
        logger.info("IMPORTING PHOTOS FROM JSON TO POSTGRESQL")
        logger.info("=" * 80)

        if not os.path.exists(photo_file):
            logger.error(f"Photo mappings file not found: {photo_file}")
            return self.stats

        logger.info(f"\nLoading photo mappings from: {photo_file}")
        try:
            with open(photo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            mappings = data.get('mappings', {})
            stats_info = data.get('statistics', {})

            logger.info(f"Loaded {len(mappings)} photo mappings")
            logger.info(f"Extraction statistics:")
            logger.info(f"  Total records: {stats_info.get('total_records')}")
            logger.info(f"  With attachments: {stats_info.get('with_attachments')}")

        except Exception as e:
            logger.error(f"Failed to load photo mappings: {e}")
            return self.stats

        if not mappings:
            logger.warning("No photo mappings found in file")
            return self.stats

        if not self.connect_db():
            return self.stats

        if dry_run:
            logger.info("\nDRY RUN MODE - No database updates will be performed")

        self.stats['total_photos'] = len(mappings)
        mapping_items = list(mappings.items())

        start_index = resume_from if resume_from else 0
        if start_index > 0:
            logger.info(f"Resuming from record #{start_index}")

        logger.info(f"\nProcessing {len(mapping_items) - start_index} photos...")

        for idx, (rirekisho_id, photo_data_url) in enumerate(mapping_items[start_index:], start=start_index):
            try:
                if dry_run:
                    logger.info(f"  [{idx+1}/{len(mapping_items)}] Would update {rirekisho_id}")
                    self.stats['updated'] += 1
                else:
                    sql = text("""
                        UPDATE candidates
                        SET photo_data_url = :photo_data_url
                        WHERE rirekisho_id = :rirekisho_id AND photo_data_url IS NULL
                    """)

                    result = self.db.execute(sql, {
                        'photo_data_url': photo_data_url,
                        'rirekisho_id': rirekisho_id
                    })
                    self.db.commit()

                    if result.rowcount > 0:
                        self.stats['updated'] += 1
                        if self.stats['updated'] % batch_size == 0:
                            logger.info(f"  Updated: {self.stats['updated']} photos")
                    else:
                        self.stats['not_found'] += 1
                        logger.debug(f"Candidate not found or already has photo: {rirekisho_id}")

            except Exception as e:
                self.stats['errors'] += 1
                if self.db:
                    self.db.rollback()
                logger.error(f"Error updating {rirekisho_id}: {e}")

        self.close_db()

        logger.info("\n" + "=" * 80)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total photos to import:    {self.stats['total_photos']}")
        logger.info(f"Successfully updated:      {self.stats['updated']}")
        logger.info(f"Candidates not found:      {self.stats['not_found']}")
        logger.info(f"Errors:                    {self.stats['errors']}")

        if self.stats['updated'] > 0 and self.stats['total_photos'] > 0:
            success_rate = (self.stats['updated'] * 100) // self.stats['total_photos']
            logger.info(f"Success rate:              {success_rate}%")

        logger.info("=" * 80 + "\n")

        return self.stats


def verify_photos():
    """Verify photo import status"""
    logger.info("=" * 80)
    logger.info("VERIFYING PHOTO IMPORT STATUS")
    logger.info("=" * 80)

    try:
        engine = create_engine(POSTGRES_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Count candidates with photos
        sql_with_photos = text("""
            SELECT COUNT(*) FROM candidates
            WHERE photo_data_url IS NOT NULL AND photo_data_url != ''
        """)
        with_photos = db.execute(sql_with_photos).scalar()

        # Count candidates without photos
        sql_without_photos = text("""
            SELECT COUNT(*) FROM candidates
            WHERE photo_data_url IS NULL OR photo_data_url = ''
        """)
        without_photos = db.execute(sql_without_photos).scalar()

        # Count employees with photos
        sql_employees = text("""
            SELECT COUNT(*) FROM employees
            WHERE photo_data_url IS NOT NULL AND photo_data_url != ''
        """)
        employees_with_photos = db.execute(sql_employees).scalar()

        total_candidates = with_photos + without_photos

        logger.info(f"\nCandidates:")
        logger.info(f"  Total candidates:       {total_candidates}")
        logger.info(f"  With photos:            {with_photos}")
        logger.info(f"  Without photos:         {without_photos}")

        if total_candidates > 0:
            percentage = (with_photos * 100) // total_candidates
            logger.info(f"  Coverage:               {percentage}%")

        logger.info(f"\nEmployees:")
        logger.info(f"  With photos:            {employees_with_photos}")

        # Verify photo data integrity
        logger.info(f"\nVerifying photo data integrity...")
        sql_sample = text("""
            SELECT rirekisho_id, photo_data_url
            FROM candidates
            WHERE photo_data_url IS NOT NULL
            LIMIT 5
        """)
        samples = db.execute(sql_sample).fetchall()

        valid_count = 0
        for rirekisho_id, photo_url in samples:
            try:
                if photo_url.startswith('data:image'):
                    base64_data = photo_url.split(',', 1)[1]
                    image_bytes = base64.b64decode(base64_data)
                    if len(image_bytes) > 0:
                        valid_count += 1
            except:
                pass

        logger.info(f"  Sample validation:      {valid_count}/5 photos valid")

        db.close()

        logger.info("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Error during verification: {e}")


def generate_report(csv_export: Optional[str] = None):
    """Generate detailed import report"""
    logger.info("=" * 80)
    logger.info("GENERATING PHOTO IMPORT REPORT")
    logger.info("=" * 80)

    try:
        engine = create_engine(POSTGRES_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Get detailed statistics
        sql = text("""
            SELECT
                rirekisho_id,
                seimei_romaji,
                CASE WHEN photo_data_url IS NOT NULL THEN 'Yes' ELSE 'No' END as has_photo,
                CASE WHEN photo_data_url IS NOT NULL
                    THEN LENGTH(photo_data_url)
                    ELSE 0
                END as photo_size
            FROM candidates
            ORDER BY rirekisho_id
        """)

        results = db.execute(sql).fetchall()

        logger.info(f"\nTotal candidates analyzed: {len(results)}")

        if csv_export:
            with open(csv_export, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Rirekisho ID', 'Name', 'Has Photo', 'Photo Size (bytes)'])

                for row in results:
                    writer.writerow([row[0], row[1], row[2], row[3]])

            logger.info(f"Report exported to: {csv_export}")

        # Summary statistics
        with_photos = sum(1 for r in results if r[2] == 'Yes')
        without_photos = len(results) - with_photos
        avg_size = sum(r[3] for r in results if r[3] > 0) // with_photos if with_photos > 0 else 0

        logger.info(f"\nSummary:")
        logger.info(f"  Candidates with photos:    {with_photos}")
        logger.info(f"  Candidates without photos: {without_photos}")
        logger.info(f"  Average photo size:        {avg_size:,} bytes")

        db.close()

        logger.info("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Error generating report: {e}")


# CLI Commands
import click

@click.group()
def cli():
    """Unified photo import and extraction service"""
    pass


@cli.command()
@click.option('--db-path', default=ACCESS_DB_PATH, help='Access database path')
@click.option('--limit', type=int, help='Limit number of photos to extract')
@click.option('--dry-run', is_flag=True, help='Show what would be extracted without saving')
@click.option('--output', default=DEFAULT_OUTPUT_JSON, help='Output JSON file')
def extract(db_path, limit, dry_run, output):
    """Extract photos from Access database"""
    if not HAS_WIN32COM:
        logger.error("pywin32 is required for COM automation")
        logger.error("Install with: pip install pywin32")
        sys.exit(1)

    if not os.path.exists(db_path):
        logger.error(f"Access database not found: {db_path}")
        sys.exit(1)

    extractor = AccessPhotoExtractor()
    extractor.extract_photos(limit=limit, dry_run=dry_run)

    if not dry_run and extractor.photo_mappings:
        extractor.save_mappings(output)
    elif dry_run:
        logger.info("\nDry run completed - no files saved")
    else:
        logger.warning("No photos extracted, nothing to save")


@cli.command()
@click.option('--file', default=DEFAULT_OUTPUT_JSON, help='Photo mappings JSON file')
@click.option('--resume-from', type=int, help='Resume from record number')
@click.option('--dry-run', is_flag=True, help='Preview import without updating database')
@click.option('--batch-size', type=int, default=50, help='Batch size for progress reports')
def import_photos(file, resume_from, dry_run, batch_size):
    """Import photos from JSON to database"""
    importer = PhotoImporter()
    importer.import_photos(file, resume_from=resume_from, dry_run=dry_run, batch_size=batch_size)


@cli.command()
def verify():
    """Verify photo import status"""
    verify_photos()


@cli.command()
@click.option('--csv-export', help='Export report to CSV file')
def report(csv_export):
    """Generate detailed import report"""
    generate_report(csv_export=csv_export)


if __name__ == '__main__':
    cli()

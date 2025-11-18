"""
URGENT: Extract ALL Photos from Access Database
================================================

Extracts ALL 1,156 candidate photos from Access database attachments
and saves them to JSON with Base64 Data URLs.

Requirements:
    - pywin32 (win32com)
    - Microsoft Access installed (for COM automation)

Usage:
    python extract_all_photos_urgente.py

Output:
    - all_candidates_with_photos.json (complete JSON with all candidates + photos)
    - extraction_report.txt (detailed report)
"""

import sys
import os
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import win32com.client
    import pythoncom
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False
    print("ERROR: pywin32 not installed")
    print("Install with: pip install pywin32")
    sys.exit(1)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
ACCESS_DB_PATH = PROJECT_ROOT / "BASEDATEJP" / "ユニバーサル企画㈱データベースv25.3.24_be.accdb"
ACCESS_TABLE = "T_履歴書"
PHOTO_FIELD = "写真"
OUTPUT_JSON = PROJECT_ROOT / "config" / "all_candidates_with_photos.json"
REPORT_FILE = PROJECT_ROOT / "config" / "extraction_report.txt"

# Setup logging
log_file = f'extract_photos_urgente_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UrgentPhotoExtractor:
    """Urgent photo extraction for ALL candidates"""

    def __init__(self):
        self.access_app = None
        self.db = None
        self.stats = {
            'total_records': 0,
            'processed': 0,
            'with_photos': 0,
            'without_photos': 0,
            'extraction_success': 0,
            'extraction_failed': 0,
            'errors': 0
        }
        self.candidates = []
        self.errors = []

    def connect_access(self) -> bool:
        """Connect to Access database"""
        try:
            logger.info("Initializing COM...")
            pythoncom.CoInitialize()

            logger.info("Creating Access application...")
            self.access_app = win32com.client.Dispatch("Access.Application")

            # Close any open database
            try:
                self.access_app.CloseCurrentDatabase()
            except:
                pass

            logger.info(f"Opening database: {ACCESS_DB_PATH}")
            self.access_app.OpenCurrentDatabase(str(ACCESS_DB_PATH))
            self.db = self.access_app.CurrentDb()

            logger.info("Successfully connected to Access database")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def close_access(self):
        """Close Access database"""
        try:
            if self.access_app:
                logger.info("Closing Access...")
                self.access_app.CloseCurrentDatabase()
                self.access_app.Quit()
                self.access_app = None
                self.db = None
            pythoncom.CoUninitialize()
        except Exception as e:
            logger.warning(f"Error closing Access: {e}")

    def extract_attachment_to_base64(self, attachment_field) -> Optional[str]:
        """Extract attachment and convert to Base64 Data URL"""
        try:
            if not attachment_field.Value:
                return None

            attachment_rs = attachment_field.Value

            if attachment_rs.RecordCount == 0:
                return None

            # Move to first attachment
            attachment_rs.MoveFirst()

            # Get attachment data
            filename = attachment_rs.Fields("FileName").Value
            file_data = attachment_rs.Fields("FileData").Value

            # Convert to bytes
            if isinstance(file_data, (bytes, bytearray)):
                photo_bytes = bytes(file_data)
            else:
                photo_bytes = bytes(file_data)

            # Determine MIME type from extension
            ext = os.path.splitext(filename)[1].lower() if filename else ''
            mime_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_map.get(ext, 'image/jpeg')

            # Convert to Base64 Data URL
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            photo_data_url = f"data:{mime_type};base64,{photo_base64}"

            return photo_data_url

        except Exception as e:
            logger.error(f"Error extracting attachment: {e}")
            return None

    def extract_all_candidates(self) -> Dict[str, Any]:
        """Extract ALL candidates with photos"""
        logger.info("=" * 80)
        logger.info("URGENT PHOTO EXTRACTION - ALL CANDIDATES")
        logger.info("=" * 80)
        logger.info(f"Database: {ACCESS_DB_PATH}")
        logger.info(f"Table: {ACCESS_TABLE}")
        logger.info(f"Photo field: {PHOTO_FIELD}")
        logger.info("")

        if not self.connect_access():
            logger.error("Cannot proceed without Access connection")
            return {}

        try:
            # Get ALL fields from table
            sql = f"SELECT * FROM [{ACCESS_TABLE}]"

            logger.info(f"Executing: {sql}")
            recordset = self.db.OpenRecordset(sql)

            # Count records
            recordset.MoveLast()
            self.stats['total_records'] = recordset.RecordCount
            recordset.MoveFirst()

            logger.info(f"Total records: {self.stats['total_records']:,}")
            logger.info("")

            # Get all field names
            field_names = []
            for i in range(recordset.Fields.Count):
                field_names.append(recordset.Fields(i).Name)

            logger.info(f"Total fields: {len(field_names)}")
            logger.info("")

            # Find photo field index
            photo_field_idx = -1
            for i, name in enumerate(field_names):
                if name == PHOTO_FIELD:
                    photo_field_idx = i
                    break

            if photo_field_idx < 0:
                logger.error(f"Photo field '{PHOTO_FIELD}' not found!")
                logger.error(f"Available fields: {', '.join(field_names)}")
                return {}

            logger.info(f"Photo field found at index: {photo_field_idx}")
            logger.info("")
            logger.info("Processing records...")
            logger.info("")

            record_num = 0
            last_progress = 0

            while not recordset.EOF:
                record_num += 1
                self.stats['processed'] += 1

                # Progress update every 10%
                progress = int((record_num / self.stats['total_records']) * 100)
                if progress >= last_progress + 10:
                    logger.info(f"Progress: {progress}% ({record_num:,} / {self.stats['total_records']:,})")
                    last_progress = progress

                try:
                    # Extract ALL fields for this candidate
                    candidate = {}

                    for i in range(recordset.Fields.Count):
                        field_name = recordset.Fields(i).Name

                        # Skip photo field (will handle separately)
                        if field_name == PHOTO_FIELD:
                            continue

                        try:
                            field_value = recordset.Fields(i).Value

                            # Convert to JSON-serializable types
                            if field_value is None:
                                candidate[field_name] = None
                            elif isinstance(field_value, (str, int, float, bool)):
                                candidate[field_name] = field_value
                            elif hasattr(field_value, 'isoformat'):  # datetime/date
                                candidate[field_name] = field_value.isoformat()
                            else:
                                candidate[field_name] = str(field_value)

                        except Exception as e:
                            # Some fields might not be readable
                            candidate[field_name] = None

                    # Extract photo attachment
                    photo_data_url = None
                    attachment_field = recordset.Fields(PHOTO_FIELD)

                    if attachment_field.Value and attachment_field.Value.RecordCount > 0:
                        self.stats['with_photos'] += 1
                        photo_data_url = self.extract_attachment_to_base64(attachment_field)

                        if photo_data_url:
                            self.stats['extraction_success'] += 1
                        else:
                            self.stats['extraction_failed'] += 1
                    else:
                        self.stats['without_photos'] += 1

                    # Add photo to candidate
                    candidate['photo_data_url'] = photo_data_url

                    # Add metadata
                    candidate['_extracted_at'] = datetime.now().isoformat()
                    candidate['_record_number'] = record_num

                    self.candidates.append(candidate)

                except Exception as e:
                    self.stats['errors'] += 1
                    error_msg = f"Error processing record #{record_num}: {e}"
                    logger.error(error_msg)
                    self.errors.append({
                        'record_num': record_num,
                        'error': str(e)
                    })

                finally:
                    recordset.MoveNext()

            recordset.Close()

            # Final summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("EXTRACTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total records: {self.stats['total_records']:,}")
            logger.info(f"Processed: {self.stats['processed']:,}")
            logger.info(f"With photos: {self.stats['with_photos']:,}")
            logger.info(f"Without photos: {self.stats['without_photos']:,}")
            logger.info(f"Extraction successful: {self.stats['extraction_success']:,}")
            logger.info(f"Extraction failed: {self.stats['extraction_failed']:,}")
            logger.info(f"Errors: {self.stats['errors']:,}")

            if self.stats['with_photos'] > 0:
                success_rate = (self.stats['extraction_success'] / self.stats['with_photos']) * 100
                logger.info(f"Success rate: {success_rate:.1f}%")

            if self.errors:
                logger.warning(f"\nErrors encountered: {len(self.errors)}")
                for err in self.errors[:5]:
                    logger.warning(f"  Record #{err['record_num']}: {err['error']}")
                if len(self.errors) > 5:
                    logger.warning(f"  ... and {len(self.errors) - 5} more errors")

            logger.info("=" * 80)

            return {
                'success': True,
                'statistics': self.stats,
                'candidates': self.candidates,
                'errors': self.errors
            }

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            self.close_access()

    def save_to_json(self):
        """Save candidates to JSON file"""
        if not self.candidates:
            logger.warning("No candidates to save")
            return False

        try:
            logger.info("")
            logger.info("Saving to JSON...")

            # Ensure output directory exists
            OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

            output_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'extract_all_photos_urgente.py',
                'database': str(ACCESS_DB_PATH),
                'table': ACCESS_TABLE,
                'photo_field': PHOTO_FIELD,
                'statistics': self.stats,
                'total_candidates': len(self.candidates),
                'candidates': self.candidates
            }

            with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            file_size_mb = OUTPUT_JSON.stat().st_size / (1024 * 1024)

            logger.info(f"✓ Saved to: {OUTPUT_JSON}")
            logger.info(f"✓ File size: {file_size_mb:.2f} MB")
            logger.info(f"✓ Total candidates: {len(self.candidates):,}")

            return True

        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            return False

    def generate_report(self):
        """Generate extraction report"""
        try:
            with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("URGENT PHOTO EXTRACTION REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Database: {ACCESS_DB_PATH}\n")
                f.write(f"Table: {ACCESS_TABLE}\n")
                f.write(f"Photo field: {PHOTO_FIELD}\n")
                f.write("\n")
                f.write("STATISTICS:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total records: {self.stats['total_records']:,}\n")
                f.write(f"Processed: {self.stats['processed']:,}\n")
                f.write(f"With photos: {self.stats['with_photos']:,}\n")
                f.write(f"Without photos: {self.stats['without_photos']:,}\n")
                f.write(f"Extraction successful: {self.stats['extraction_success']:,}\n")
                f.write(f"Extraction failed: {self.stats['extraction_failed']:,}\n")
                f.write(f"Errors: {self.stats['errors']:,}\n")
                f.write("\n")

                if self.stats['with_photos'] > 0:
                    success_rate = (self.stats['extraction_success'] / self.stats['with_photos']) * 100
                    f.write(f"Success rate: {success_rate:.1f}%\n")

                f.write("\n")
                f.write("OUTPUT FILES:\n")
                f.write("-" * 80 + "\n")
                f.write(f"JSON: {OUTPUT_JSON}\n")
                f.write(f"Report: {REPORT_FILE}\n")
                f.write(f"Log: {log_file}\n")

                if self.errors:
                    f.write("\n")
                    f.write("ERRORS:\n")
                    f.write("-" * 80 + "\n")
                    for err in self.errors:
                        f.write(f"Record #{err['record_num']}: {err['error']}\n")

                f.write("\n")
                f.write("=" * 80 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 80 + "\n")

            logger.info(f"✓ Report saved to: {REPORT_FILE}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return False


def main():
    """Main execution"""
    print("")
    print("=" * 80)
    print("URGENT PHOTO EXTRACTION - ALL 1,156 CANDIDATES")
    print("=" * 80)
    print("")

    # Check if database exists
    if not ACCESS_DB_PATH.exists():
        print(f"ERROR: Database not found: {ACCESS_DB_PATH}")
        return 1

    # Create extractor
    extractor = UrgentPhotoExtractor()

    # Extract all candidates
    result = extractor.extract_all_candidates()

    if not result.get('success'):
        print("")
        print("❌ EXTRACTION FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return 1

    # Save to JSON
    if not extractor.save_to_json():
        print("")
        print("❌ FAILED TO SAVE JSON")
        return 1

    # Generate report
    extractor.generate_report()

    # Final message
    print("")
    print("=" * 80)
    print("✅ EXTRACTION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Total candidates: {len(extractor.candidates):,}")
    print(f"With photos: {extractor.stats['with_photos']:,}")
    print(f"Without photos: {extractor.stats['without_photos']:,}")
    print(f"Success rate: {(extractor.stats['extraction_success'] / max(extractor.stats['with_photos'], 1)) * 100:.1f}%")
    print("")
    print("OUTPUT FILES:")
    print(f"  JSON: {OUTPUT_JSON}")
    print(f"  Report: {REPORT_FILE}")
    print(f"  Log: {log_file}")
    print("")
    print("NEXT STEPS:")
    print("  1. Verify JSON file exists and has correct data")
    print("  2. Import to PostgreSQL using import script")
    print("=" * 80)
    print("")

    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Extraction cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

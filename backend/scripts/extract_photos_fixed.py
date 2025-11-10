"""
Fixed Photo Extraction Script

This script handles the case where photos are stored as filenames rather than binary data.
It uses pyodbc to connect to Access and extract photo filename references.
"""

import sys
import os
import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging with UTF-8 encoding to avoid cp932 issues
log_file = f'extract_photos_fixed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_databasejp_folder() -> Optional[Path]:
    """Search for BASEDATEJP folder"""
    
    logger.info("Searching for BASEDATEJP folder...")
    
    search_paths = [
        Path.cwd() / "BASEDATEJP",
        Path.cwd().parent / "BASEDATEJP",
        Path.cwd().parent.parent / "BASEDATEJP",
        Path("D:/BASEDATEJP"),
        Path(os.path.expanduser("~")) / "BASEDATEJP",
    ]

    for path in search_paths:
        if path.exists() and path.is_dir():
            logger.info(f"Found database folder at: {path}")
            return path

    logger.warning("BASEDATEJP folder not found")
    return None

def find_access_database(databasejp_path: Path) -> Optional[Path]:
    """Search for .accdb files in BASEDATEJP folder"""
    
    logger.info(f"Searching for Access database files in {databasejp_path}...")
    
    # Look for the specific known database name
    known_db_names = [
        "ユニバーサル企画㈱データベースv25.3.24_be.accdb",
        "ユニバーサル企画㈱データベースv25.3.24.accdb",
        "ユニバーサル企画㈱データベース.accdb",
    ]

    for db_name in known_db_names:
        db_path = databasejp_path / db_name
        if db_path.exists():
            logger.info(f"Found specific database: {db_name}")
            logger.info(f"  Size: {db_path.stat().st_size / (1024*1024):.1f} MB")
            return db_path

    # Search for any .accdb files
    logger.info("Specific database not found, searching for any .accdb files...")
    accdb_files = list(databasejp_path.glob("**/*.accdb"))

    if not accdb_files:
        logger.warning("No .accdb files found in BASEDATEJP")
        return None

    logger.info(f"Found {len(accdb_files)} Access database file(s)")

    # Sort by size (descending) to get the main database
    accdb_files.sort(key=lambda p: p.stat().st_size, reverse=True)

    selected_db = accdb_files[0]
    logger.info(f"Selected largest database: {selected_db.name} ({selected_db.stat().st_size / (1024*1024):.1f} MB)")

    return selected_db

def extract_photos_using_pyodbc(access_db_path: Path) -> Dict[str, Any]:
    """Extract photos using pyodbc with filename handling"""
    
    logger.info(f"\nStarting photo extraction using pyodbc from: {access_db_path}")

    try:
        import pyodbc
    except ImportError:
        logger.error("pyodbc not installed!")
        logger.error("Install with: pip install pyodbc")
        return {"error": "pyodbc_not_installed"}

    try:
        # Connection string for Access
        conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={access_db_path};"
        
        logger.info("Connecting to database...")
        conn = pyodbc.connect(conn_str)
        logger.info("Successfully connected to database")
        
        cursor = conn.cursor()
        
        # Get all tables
        tables = cursor.tables(tableType='TABLE').fetchall()
        logger.info(f"Found {len(tables)} tables")
        
        # Find the table with photos (T_履歴書)
        photo_table = None
        for table_info in tables:
            table_name = table_info[2]
            logger.debug(f"Checking table: {table_name}")
            if "履歴書" in table_name or "履歴" in table_name or "RIREKISHO" in table_name.upper():
                photo_table = table_name
                logger.info(f"Found photo table: {photo_table}")
                break
        
        if not photo_table:
            logger.error("Photo table T_履歴書 not found")
            return {"error": "no_photo_table_found"}
        
        # Get table structure
        columns = cursor.columns(table=photo_table).fetchall()
        logger.info(f"Table {photo_table} has {len(columns)} columns")
        
        # Find photo column (写真)
        photo_column = None
        id_column = None
        
        for col_info in columns:
            col_name = col_info[2]
            col_type = col_info[3]
            logger.debug(f"Column: {col_name} (Type: {col_type})")
            
            # Find ID column first
            if not id_column and ("ID" in col_name.upper() or col_name == columns[0][2]):
                id_column = col_name
                logger.info(f"Using ID column: {id_column}")
            
            # Find photo column - check for Japanese characters and English
            if "写真" in col_name or "Photo" in col_name or "photo" in col_name or "写" in col_name:
                photo_column = col_name
                logger.info(f"Found photo column: {photo_column}")
                break
        
        # If still not found, try column 9 (based on analysis)
        if not photo_column and len(columns) >= 9:
            photo_column = columns[8][2]  # Column 9 (0-indexed)
            logger.info(f"Using column 9 as photo column: {photo_column}")
        
        if not photo_column:
            logger.error("Photo column (写真) not found")
            return {"error": "no_photo_column_found"}
        
        if not id_column:
            # Use first column as ID if no specific ID column found
            id_column = columns[0][2]
            logger.info(f"Using first column as ID: {id_column}")
        
        # Check photo column content type
        logger.info("Analyzing photo column content...")
        try:
            sample_query = f"SELECT TOP 3 [{id_column}], [{photo_column}] FROM [{photo_table}] WHERE [{photo_column}] IS NOT NULL"
            logger.debug(f"Sample query: {sample_query}")
            cursor.execute(sample_query)
            sample_rows = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Failed to query with column names: {e}")
            # Try using column indices instead
            logger.info("Trying column indices instead...")
            sample_query = f"SELECT TOP 3 * FROM [{photo_table}] WHERE [{photo_column}] IS NOT NULL"
            logger.debug(f"Alternative query: {sample_query}")
            cursor.execute(sample_query)
            sample_rows = cursor.fetchall()
        
        is_filename_based = False
        id_col_index = 0  # First column is ID
        photo_col_index = 8  # Column 9 (0-indexed)
        
        for row in sample_rows:
            record_id = row[id_col_index]
            photo_value = row[photo_col_index]
            if isinstance(photo_value, str) and ('.' in photo_value.lower() and any(ext in photo_value.lower() for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif'])):
                is_filename_based = True
                logger.info(f"Photo column contains filenames: ID={record_id}, Photo={photo_value}")
                break
            elif isinstance(photo_value, bytes):
                logger.info(f"Photo column contains binary data: ID={record_id}, Size={len(photo_value)} bytes")
                break
        
        # Extract photos
        if is_filename_based:
            logger.info("Extracting photo filenames from database...")
            return extract_photo_filenames(cursor, photo_table, id_column, photo_column)
        else:
            logger.info("Extracting binary photo data from database...")
            return extract_binary_photos(cursor, photo_table, id_column, photo_column)
    
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"error": str(e)}

def extract_photo_filenames(cursor, table_name: str, id_column: str, photo_column: str) -> Dict[str, Any]:
    """Extract photo filenames and create mappings"""
    
    try:
        query = f"SELECT * FROM [{table_name}] WHERE [{photo_column}] IS NOT NULL AND [{photo_column}] <> ''"
        cursor.execute(query)
    except Exception as e:
        logger.warning(f"Failed to query with column names, using *: {e}")
        query = f"SELECT * FROM [{table_name}]"
        cursor.execute(query)
    
    mappings = {}
    total_records = 0
    extracted_photos = 0
    errors = 0
    
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} total records, filtering for photo filenames...")
    
    # Use column indices: 0 for ID, 8 for photo (column 9)
    id_col_index = 0
    photo_col_index = 8
    
    for row in rows:
        total_records += 1
        
        try:
            record_id = str(row[id_col_index]) if row[id_col_index] else f"record_{total_records}"
            photo_filename = str(row[photo_col_index]).strip() if row[photo_col_index] else None
            
            if photo_filename and photo_filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
                # Create a data URL placeholder for the filename
                # In a real implementation, you might need to locate the actual image files
                photo_data_url = f"filename:{photo_filename}"
                mappings[record_id] = photo_data_url
                extracted_photos += 1
                logger.debug(f"Mapped ID {record_id} -> {photo_filename}")
            else:
                if photo_filename:  # Only log if there was a value but not a valid filename
                    logger.debug(f"Invalid photo filename for ID {record_id}: {photo_filename}")
        
        except Exception as e:
            errors += 1
            logger.debug(f"Error processing record {total_records}: {e}")
        
        if total_records % 100 == 0:
            logger.info(f"  Processed {total_records} records, extracted {extracted_photos} photos")
    
    logger.info(f"\nFilename extraction complete:")
    logger.info(f"  Total records processed: {total_records}")
    logger.info(f"  Photo filenames extracted: {extracted_photos}")
    logger.info(f"  Errors: {errors}")
    
    return {
        "success": True,
        "method": "filenames",
        "total_records": total_records,
        "with_photos": extracted_photos,
        "errors": errors,
        "mappings": mappings
    }

def extract_binary_photos(cursor, table_name: str, id_column: str, photo_column: str) -> Dict[str, Any]:
    """Extract binary photo data"""
    
    try:
        query = f"SELECT * FROM [{table_name}] WHERE [{photo_column}] IS NOT NULL"
        cursor.execute(query)
    except Exception as e:
        logger.warning(f"Failed to query with column names, using *: {e}")
        query = f"SELECT * FROM [{table_name}]"
        cursor.execute(query)
    
    mappings = {}
    total_records = 0
    extracted_photos = 0
    errors = 0
    
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} total records, filtering for binary photo data...")
    
    # Use column indices: 0 for ID, 8 for photo (column 9)
    id_col_index = 0
    photo_col_index = 8
    
    for row in rows:
        total_records += 1
        
        try:
            record_id = str(row[id_col_index]) if row[id_col_index] else f"record_{total_records}"
            photo_data = row[photo_col_index]
            
            if photo_data and isinstance(photo_data, bytes):
                # Convert binary data to base64
                base64_data = base64.b64encode(photo_data).decode('utf-8')
                photo_data_url = f"data:image/jpeg;base64,{base64_data}"
                mappings[record_id] = photo_data_url
                extracted_photos += 1
                logger.debug(f"Extracted binary photo for ID {record_id}: {len(photo_data)} bytes")
        
        except Exception as e:
            errors += 1
            logger.debug(f"Error processing record {total_records}: {e}")
        
        if total_records % 50 == 0:
            logger.info(f"  Processed {total_records} records, extracted {extracted_photos} photos")
    
    logger.info(f"\nBinary extraction complete:")
    logger.info(f"  Total records processed: {total_records}")
    logger.info(f"  Photos extracted: {extracted_photos}")
    logger.info(f"  Errors: {errors}")
    
    return {
        "success": True,
        "method": "binary",
        "total_records": total_records,
        "with_photos": extracted_photos,
        "errors": errors,
        "mappings": mappings
    }

def save_photo_mappings(mappings: Dict, output_path: Path, method: str) -> bool:
    """Save photo mappings to JSON file"""
    
    try:
        output = {
            "timestamp": datetime.now().isoformat(),
            "source": "fixed_extract_from_databasejp",
            "method": method,
            "statistics": {
                "total_mappings": len(mappings)
            },
            "mappings": mappings
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved mappings to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving mappings: {e}")
        return False

def main():
    """Main extraction workflow"""
    
    logger.info("=" * 80)
    logger.info("FIXED PHOTO EXTRACTION SCRIPT")
    logger.info("=" * 80)
    
    # Check if access_photo_mappings.json already exists
    output_file = Path.cwd() / "access_photo_mappings.json"
    if output_file.exists():
        logger.info(f"access_photo_mappings.json already exists.")
        response = input("Overwrite existing file? (S/N): ")
        if response.upper() not in ['S', 'SI']:
            logger.info("Extraction cancelled.")
            return 0
    
    # Find BASEDATEJP folder
    databasejp_path = find_databasejp_folder()
    if not databasejp_path:
        logger.error("Could not find BASEDATEJP folder.")
        return 1
    
    # Find Access database
    access_db = find_access_database(databasejp_path)
    if not access_db:
        logger.error("Could not find Access database in BASEDATEJP folder.")
        return 1
    
    # Extract photos
    result = extract_photos_using_pyodbc(access_db)
    
    if "error" in result:
        logger.error(f"Extraction failed: {result['error']}")
        return 1
    
    # Save mappings
    if result.get("mappings"):
        method = result.get("method", "unknown")
        if save_photo_mappings(result["mappings"], output_file, method):
            logger.info("\n" + "=" * 80)
            logger.info("EXTRACTION SUCCESSFUL")
            logger.info("=" * 80)
            logger.info(f"Method used: {method}")
            logger.info(f"Photos extracted: {result['with_photos']}")
            logger.info(f"Output file: {output_file}")
            
            if method == "filenames":
                logger.info("\nNOTE: Photos are stored as filenames in the database.")
                logger.info("You may need to locate the actual image files separately.")
            
            return 0
        else:
            logger.error("Failed to save photo mappings")
            return 1
    else:
        logger.warning("No photos were extracted")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
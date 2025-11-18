#!/usr/bin/env python3
"""
Import photos from all_candidates_with_photos.json to PostgreSQL

This script:
1. Reads all_candidates_with_photos.json (contains base64 photos)
2. Updates candidates.photo_data_url in PostgreSQL
3. Reports statistics

Usage:
    python scripts/import_photos_from_all_candidates.py
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.models import Candidate

def import_photos():
    """Import photos from all_candidates_with_photos.json"""

    json_file = Path('/app/config/all_candidates_with_photos.json')

    print("""
╔════════════════════════════════════════════════════════════╗
║      IMPORTING PHOTOS FROM all_candidates_with_photos.json ║
╚════════════════════════════════════════════════════════════╝
""")

    # Check if JSON file exists
    if not json_file.exists():
        print(f"❌ ERROR: {json_file} NOT FOUND")
        return False

    # Read JSON file
    print(f"📂 Reading JSON file: {json_file}")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON: {e}")
        return False

    candidates_data = data.get('candidates', [])
    print(f"✓ Found {len(candidates_data)} candidates in JSON")

    # Connect to database
    db = SessionLocal()
    updated = 0
    skipped = 0
    errors = 0

    try:
        for i, candidate_data in enumerate(candidates_data):
            if (i + 1) % 100 == 0:
                print(f"  Processing {i + 1}/{len(candidates_data)}...")

            photo_data_url = candidate_data.get('photo_data_url')  # Already formatted photo data URL
            full_name = candidate_data.get('氏名')  # Full name for matching

            if not full_name:
                skipped += 1
                continue

            if not photo_data_url:
                skipped += 1
                continue

            try:

                # Update candidate - match by full name (KANJI)
                candidate = db.query(Candidate).filter(
                    Candidate.full_name_kanji == full_name
                ).first()

                if candidate:
                    candidate.photo_data_url = photo_data_url
                    db.commit()
                    updated += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"  ⚠ Error updating candidate {full_name}: {e}")
                db.rollback()
                errors += 1

    finally:
        db.close()

    # Report results
    print(f"""
╔════════════════════════════════════════════════════════════╗
║                   IMPORT COMPLETED                         ║
╚════════════════════════════════════════════════════════════╝

✅ Updated:   {updated}
⏭️  Skipped:    {skipped}
❌ Errors:     {errors}

Total candidates: {len(candidates_data)}
Success rate: {(updated / len(candidates_data) * 100):.1f}%
""")

    return True

if __name__ == '__main__':
    import_photos()

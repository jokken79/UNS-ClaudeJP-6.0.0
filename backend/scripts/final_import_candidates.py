#!/usr/bin/env python3
"""
Final robust import of candidates with photos from JSON to PostgreSQL
Handles all error cases and generates IDs as needed
"""

import json
import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.models import Candidate
from app.core.config import settings

def load_candidates_from_json(json_path: str):
    """Load candidates from JSON file"""
    print(f"\n[*] Loading JSON from {json_path}...")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find candidates list
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ['candidates', 'data', 'records', 'items']:
            if key in data and isinstance(data[key], list):
                candidates = data[key]
                break
        else:
            # Find first list with dicts
            candidates = None
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    candidates = val
                    print(f"  Found candidates under key: {key}")
                    break

            if not candidates:
                raise ValueError("Could not find candidates list in JSON")
    else:
        raise ValueError(f"JSON root is {type(data)}, expected list or dict")

    print(f"  [OK] Found {len(candidates)} candidates")
    return candidates

def import_candidates(json_file: str) -> dict:
    """Import candidates from JSON to PostgreSQL"""

    print("\n" + "=" * 80)
    print("FINAL CANDIDATE IMPORT WITH PHOTOS")
    print("=" * 80)

    try:
        # Load data
        candidates = load_candidates_from_json(json_file)

        # Create database connection
        print(f"\n[*] Connecting to database...")
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        print(f"  [OK] Connected to PostgreSQL\n")

        stats = {
            'total_input': len(candidates),
            'imported': 0,
            'with_photos': 0,
            'errors': 0,
            'skipped': 0
        }

        print("[*] Importing candidates...\n")

        for idx, row in enumerate(candidates, 1):
            try:
                # Extract name (required)
                name = None
                for name_field in ['氏名', 'full_name_roman', '名前', 'name']:
                    if name_field in row and row[name_field]:
                        name = str(row[name_field]).strip()
                        if name:
                            break

                if not name:
                    stats['skipped'] += 1
                    continue

                # Generate or get rirekisho_id
                rirekisho_id = (
                    row.get('履歴書ID') or
                    row.get('rirekisho_id') or
                    f'RIR{str(idx+1000).zfill(5)}'
                )

                # Create candidate
                candidate = Candidate(
                    rirekisho_id=str(rirekisho_id),
                    full_name_roman=name,
                    full_name_kanji=row.get('氏名') or row.get('full_name_kanji'),
                    full_name_kana=row.get('氏名（カナ）') or row.get('full_name_kana'),
                    date_of_birth=row.get('生年月日') or row.get('date_of_birth'),
                    age=row.get('年齢') or row.get('age'),
                    gender=row.get('性別') or row.get('gender'),
                    nationality=row.get('国籍') or row.get('nationality'),
                    phone=row.get('電話') or row.get('phone'),
                    email=row.get('メール') or row.get('email'),
                    address=row.get('住所') or row.get('address'),
                    photo_data_url=row.get('写真') or row.get('photo_data_url'),
                    status='pending'
                )

                session.add(candidate)
                stats['imported'] += 1

                if candidate.photo_data_url:
                    stats['with_photos'] += 1

                # Batch commit every 100 records
                if stats['imported'] % 100 == 0:
                    session.commit()
                    print(f"  [OK] Imported {stats['imported']} candidates (photos: {stats['with_photos']})")

            except Exception as e:
                session.rollback()
                stats['errors'] += 1
                if stats['errors'] <= 5:  # Print only first 5 errors
                    print(f"  [!] Error at row {idx}: {str(e)[:100]}")
                continue

        # Final commit
        session.commit()

        # Verify import
        total_in_db = session.query(Candidate).count()
        total_photos_in_db = session.query(Candidate).filter(
            Candidate.photo_data_url != None
        ).count()

        print("\n" + "=" * 80)
        print("IMPORT RESULTS")
        print("=" * 80)
        print(f"Input records:       {stats['total_input']}")
        print(f"Imported:            {stats['imported']}")
        print(f"Total in database:   {total_in_db}")
        print(f"With photos:         {stats['with_photos']} (in DB: {total_photos_in_db})")
        print(f"Skipped:             {stats['skipped']}")
        print(f"Errors:              {stats['errors']}")
        print("=" * 80 + "\n")

        session.close()
        return stats

    except Exception as e:
        print(f"\n[X] CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    json_file = "/app/access_candidates_data.json"

    if not os.path.exists(json_file):
        print(f"[X] JSON file not found: {json_file}")
        sys.exit(1)

    result = import_candidates(json_file)

    if result and result['imported'] > 0:
        print("[OK] Import successful!")
        sys.exit(0)
    else:
        print("[X] Import failed or no records imported")
        sys.exit(1)

#!/usr/bin/env python3
"""
Robust candidate import from JSON with photo support
Handles flexible JSON structure (wrapped or direct array)
"""

import json
import sys
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from app.models.models import Candidate
from app.core.config import settings

def load_json_flexibly(json_file: str) -> List[Dict[str, Any]]:
    """Load JSON file and extract candidates list, handling various structures"""
    print(f"\n[*] Loading JSON from {json_file}...")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Try to extract candidates list from various possible structures
    candidates_list = None

    if isinstance(data, list):
        # Direct array of candidates
        candidates_list = data
        print(f"  [OK] JSON is direct array with {len(candidates_list)} items")

    elif isinstance(data, dict):
        # Try common keys for candidates array
        possible_keys = ['candidates', 'data', 'records', 'items', 'results']

        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                candidates_list = data[key]
                print(f"  [OK] Found candidates under key '{key}' with {len(candidates_list)} items")
                break

        # If not found in common keys, look for the first list in the dict
        if candidates_list is None:
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check if items look like candidates (have expected fields)
                    if isinstance(value[0], dict):
                        candidates_list = value
                        print(f"  [OK] Found candidate list under key '{key}' with {len(candidates_list)} items")
                        break

    if candidates_list is None:
        raise ValueError("Could not extract candidates list from JSON. Structure unclear.")

    if not isinstance(candidates_list, list):
        raise ValueError(f"Candidates is not a list, got {type(candidates_list)}")

    return candidates_list


def normalize_candidate(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw candidate data to match database schema"""

    normalized = {
        'rirekisho_id': None,
        'full_name_roman': None,
        'full_name_kanji': None,
        'full_name_kana': None,
        'date_of_birth': None,
        'age': None,
        'gender': None,
        'nationality': None,
        'phone': None,
        'email': None,
        'address': None,
        'photo_data_url': None,
        'status': 'pending'
    }

    # Map common field names to database schema
    field_mappings = {
        '履歴書ID': 'rirekisho_id',
        '名前（ローマ字）': 'full_name_roman',
        '氏名（カナ）': 'full_name_kana',
        '氏名': 'full_name_kanji',
        '生年月日': 'date_of_birth',
        '年齢': 'age',
        '性別': 'gender',
        '国籍': 'nationality',
        '電話': 'phone',
        '携帯': 'phone',
        'メール': 'email',
        'EMAIL': 'email',
        '住所': 'address',
        '写真': 'photo_data_url',
        'photo_data_url': 'photo_data_url',
    }

    # Apply field mappings
    for src_field, dst_field in field_mappings.items():
        if src_field in raw_data and raw_data[src_field] is not None:
            value = raw_data[src_field]

            # Skip if value is empty string
            if isinstance(value, str) and not value.strip():
                continue

            # Special handling for specific fields
            if dst_field == 'date_of_birth':
                # Try to parse date
                if isinstance(value, str):
                    try:
                        # Try various date formats
                        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']:
                            try:
                                parsed = datetime.strptime(value, fmt)
                                normalized[dst_field] = parsed.date()
                                break
                            except ValueError:
                                continue
                    except:
                        pass
            elif dst_field == 'age':
                try:
                    normalized[dst_field] = int(value) if value else None
                except (ValueError, TypeError):
                    pass
            elif dst_field == 'photo_data_url':
                # Store photo data URL as-is
                if isinstance(value, str) and value.strip():
                    normalized[dst_field] = value
            else:
                # Store as string, trimmed
                if isinstance(value, str):
                    normalized[dst_field] = value.strip() or None
                else:
                    normalized[dst_field] = value

    # Use all remaining fields as fallback if primary name is empty
    if not normalized['full_name_roman']:
        for key in raw_data.keys():
            if 'name' in key.lower() and raw_data[key]:
                normalized['full_name_roman'] = str(raw_data[key]).strip()
                break

    # If still no name, skip this record
    if not normalized['full_name_roman']:
        return None

    return normalized


def import_candidates(json_file: str, batch_size: int = 100) -> int:
    """Import candidates from JSON to PostgreSQL database"""

    print("\n" + "=" * 80)
    print("IMPORTING CANDIDATES FROM JSON")
    print("=" * 80)

    # Load candidates from JSON
    candidates_data = load_json_flexibly(json_file)

    # Create database session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    imported_count = 0
    skipped_count = 0
    photo_count = 0

    try:
        print(f"\n[*] Processing {len(candidates_data)} candidates...")

        for idx, raw_candidate in enumerate(candidates_data, 1):
            # Normalize candidate data
            candidate_dict = normalize_candidate(raw_candidate)

            if not candidate_dict:
                skipped_count += 1
                continue

            try:
                # Create candidate object
                candidate = Candidate(**candidate_dict)
                session.add(candidate)

                if candidate.photo_data_url:
                    photo_count += 1

                imported_count += 1

                # Commit in batches
                if imported_count % batch_size == 0:
                    session.commit()
                    print(f"  [OK] Imported {imported_count} candidates (batch at row {idx})")

            except Exception as e:
                session.rollback()
                print(f"  [!] Error importing candidate {idx}: {str(e)[:100]}")
                skipped_count += 1

        # Final commit
        session.commit()

        # Verify import
        total_candidates = session.query(Candidate).count()
        total_with_photos = session.query(Candidate).filter(
            Candidate.photo_data_url != None
        ).count()

        print("\n" + "=" * 80)
        print("IMPORT RESULTS")
        print("=" * 80)
        print(f"Total imported:        {imported_count}")
        print(f"Total in database:     {total_candidates}")
        print(f"With photos:           {total_with_photos}")
        print(f"Skipped:               {skipped_count}")
        print(f"Success rate:          {(imported_count / len(candidates_data) * 100):.1f}%")
        print("=" * 80 + "\n")

        return imported_count

    except Exception as e:
        print(f"\n[X] Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

    finally:
        session.close()


if __name__ == "__main__":
    json_file = "/app/access_candidates_data.json"

    try:
        count = import_candidates(json_file)
        sys.exit(0 if count > 0 else 1)
    except Exception as e:
        print(f"[X] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

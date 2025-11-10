#!/usr/bin/env python3
"""Debug photo data format"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.models import Candidate
import base64

db = SessionLocal()
candidate = db.query(Candidate).filter(
    Candidate.photo_data_url.isnot(None),
    Candidate.photo_data_url != ''
).first()

if candidate:
    photo = candidate.photo_data_url
    print('=== FOTO INFO ===')
    print(f'ID: {candidate.id}')
    print(f'Nombre: {candidate.full_name_roman}')
    print(f'Length: {len(photo)}')
    print(f'Starts with data:image: {photo.startswith("data:image")}')

    # Check for common issues
    has_nulls = '\x00' in photo
    print(f'Has null bytes: {has_nulls}')

    # Check first 200 chars
    print(f'First 200 chars: {repr(photo[:200])}')

    # Check if valid base64 after prefix
    if photo.startswith('data:image'):
        parts = photo.split(',', 1)
        if len(parts) == 2:
            try:
                # Try to decode a small portion
                decoded = base64.b64decode(parts[1][:100])
                print(f'Base64 decode test: SUCCESS ({len(decoded)} bytes)')
            except Exception as e:
                print(f'Base64 decode test: FAILED - {e}')
        else:
            print('ERROR: No comma separator found')
db.close()

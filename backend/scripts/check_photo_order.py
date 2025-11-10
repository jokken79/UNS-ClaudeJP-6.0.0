import sys
sys.path.insert(0, '/app')
from app.core.database import SessionLocal
from app.models.models import Candidate
import base64

db = SessionLocal()

# Get the first 10 candidates with photos
candidates = db.query(Candidate).filter(
    Candidate.photo_data_url.isnot(None)
).filter(
    Candidate.photo_data_url != ''
).limit(10).all()

print('First 10 candidates with photos:')
for c in candidates:
    base64_data = c.photo_data_url.split(',', 1)[1] if ',' in c.photo_data_url else c.photo_data_url
    image_bytes = base64.b64decode(base64_data)
    first_4 = image_bytes[:4].hex()

    jpeg_pos = image_bytes.find(b'\xFF\xD8\xFF')
    png_pos = image_bytes.find(b'\x89\x50\x4E\x47')

    marker_pos = jpeg_pos if jpeg_pos != -1 else png_pos

    print(f'ID {c.id}: First 4: {first_4} | Marker at: {marker_pos}')

db.close()

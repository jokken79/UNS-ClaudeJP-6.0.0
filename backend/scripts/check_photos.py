#!/usr/bin/env python3
"""Check how many candidates have photos"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.models import Candidate

db = SessionLocal()

total = db.query(Candidate).count()
with_photos = db.query(Candidate).filter(
    Candidate.photo_data_url.isnot(None),
    Candidate.photo_data_url != ''
).count()

print(f"Candidatos totales: {total}")
print(f"Con fotos: {with_photos}")
print(f"Sin fotos: {total - with_photos}")
print(f"Porcentaje con fotos: {(with_photos/total*100):.1f}%")

db.close()

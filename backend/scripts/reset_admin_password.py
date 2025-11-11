#!/usr/bin/env python3
"""Reset admin user password to admin123"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.models import User
from app.services.auth_service import AuthService

db = SessionLocal()

# Buscar usuario admin
admin = db.query(User).filter(User.username == 'admin').first()

if admin:
    # Resetear contraseña a 'admin123'
    admin.password_hash = AuthService.get_password_hash('admin123')
    db.commit()
    print("✅ Contraseña de admin reseteada exitosamente")
    print("   Username: admin")
    print("   Password: admin123")
else:
    print("❌ Usuario admin no encontrado")

db.close()

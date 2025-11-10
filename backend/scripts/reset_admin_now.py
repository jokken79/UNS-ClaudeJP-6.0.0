#!/usr/bin/env python3
"""Script para resetear la contraseña del admin a admin123"""
import sys
sys.path.insert(0, '/app')

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
import os

# Configuración de hash de contraseña
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Generar hash de la contraseña
new_password = "admin123"
hashed_password = pwd_context.hash(new_password)

print(f"✅ Hash generado para 'admin123'")
print(f"Hash: {hashed_password[:50]}...")

# Conectar a la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://uns_admin:uns_admin_password@db:5432/uns_claudejp")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Actualizar contraseña del usuario admin
        result = conn.execute(
            text("UPDATE users SET hashed_password = :hashed_password WHERE username = 'admin'"),
            {"hashed_password": hashed_password}
        )
        conn.commit()
        
        # Verificar la actualización
        user = conn.execute(
            text("SELECT id, username, role, is_active FROM users WHERE username = 'admin'")
        ).fetchone()
        
        if user:
            print(f"\n✅ Contraseña actualizada exitosamente!")
            print(f"   ID: {user[0]}")
            print(f"   Username: {user[1]}")
            print(f"   Role: {user[2]}")
            print(f"   Is Active: {user[3]}")
            print(f"\n🔐 Credenciales:")
            print(f"   Usuario: admin")
            print(f"   Contraseña: admin123")
        else:
            print("❌ Usuario admin no encontrado")
            
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

#!/usr/bin/env python3
"""Reset admin password to admin123"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
import psycopg2

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database connection
conn = psycopg2.connect(
    host="db",
    database="uns_claudejp",
    user="uns_admin",
    password="uns_password_secure_2024"
)

try:
    cur = conn.cursor()
    
    # Hash the password
    hashed = pwd_context.hash("admin123")
    
    # Update admin password
    cur.execute(
        "UPDATE users SET hashed_password = %s WHERE username = 'admin'",
        (hashed,)
    )
    
    conn.commit()
    
    # Verify
    cur.execute("SELECT username, email FROM users WHERE username = 'admin'")
    result = cur.fetchone()
    
    if result:
        print(f"✅ Password reset successful for user: {result[0]} ({result[1]})")
        print("🔑 New password: admin123")
    else:
        print("❌ Admin user not found")
    
    cur.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()

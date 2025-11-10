#!/usr/bin/env python3
"""Fix admin password in database"""
import psycopg2
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database connection from environment
POSTGRES_USER = os.getenv('POSTGRES_USER', 'uns_admin')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'uns_claudejp')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'db')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

conn = psycopg2.connect(
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT
)

try:
    cur = conn.cursor()

    # Generate correct hash
    password = "admin123"
    correct_hash = pwd_context.hash(password)

    print(f"Updating admin password...")
    print(f"Password: {password}")
    print(f"New hash: {correct_hash}")

    # Update password
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (correct_hash, "admin")
    )

    conn.commit()

    # Verify
    cur.execute("SELECT username, password_hash FROM users WHERE username = 'admin'")
    result = cur.fetchone()

    if result:
        username, db_hash = result
        verification = pwd_context.verify(password, db_hash)
        print(f"\nVerification:")
        print(f"  Username: {username}")
        print(f"  Hash in DB: {db_hash[:30]}...")
        print(f"  Password verification: {verification}")

        if verification:
            print("\n✅ SUCCESS: Password updated correctly!")
        else:
            print("\n❌ ERROR: Password verification failed!")

    cur.close()

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

finally:
    conn.close()

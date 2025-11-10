#!/usr/bin/env python3
"""
Ensure admin user exists and has correct password.
This is idempotent - safe to run multiple times.
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.models import User
from app.services.auth_service import AuthService
from app.core.config import settings

def ensure_admin_user():
    """Ensure admin user exists with correct password."""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if admin exists
        admin = session.query(User).filter(User.username == "admin").first()
        
        if not admin:
            print("🔨 Creating new admin user...")
            auth_service = AuthService()
            hashed_password = auth_service.get_password_hash("admin123")
            
            admin = User(
                username="admin",
                email="admin@uns-kikaku.com",
                password_hash=hashed_password,
                full_name="Administrator",
                role="super_admin",
                is_active=True
            )
            session.add(admin)
            session.commit()
            print("✅ Admin user created successfully!")
            
        else:
            print("🔐 Admin user exists, verifying password...")
            auth_service = AuthService()
            
            # Check if password is correct
            if auth_service.verify_password("admin123", admin.password_hash):
                print("✅ Password is correct - no action needed")
            else:
                print("🔧 Password is incorrect - fixing...")
                admin.password_hash = auth_service.get_password_hash("admin123")
                session.commit()
                print("✅ Password updated successfully!")
        
        # Final verification
        admin = session.query(User).filter(User.username == "admin").first()
        if admin:
            auth_service = AuthService()
            is_valid = auth_service.verify_password("admin123", admin.password_hash)
            
            print("\n📋 Final verification:")
            print(f"  • Username: {admin.username}")
            print(f"  • Email: {admin.email}")
            print(f"  • Role: {admin.role}")
            print(f"  • Active: {admin.is_active}")
            print(f"  • Password valid: {'✅ YES' if is_valid else '❌ NO'}")
            
            if is_valid:
                print("\n🎉 SUCCESS: Admin user is ready!")
                return True
            else:
                print("\n❌ ERROR: Password verification failed!")
                return False
        else:
            print("\n❌ ERROR: Admin user not found after creation!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("UNS-ClaudeJP 5.2 - Ensure Admin User")
    print("=" * 60)
    print()
    
    success = ensure_admin_user()
    sys.exit(0 if success else 1)

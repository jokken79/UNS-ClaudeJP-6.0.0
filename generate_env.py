#!/usr/bin/env python3
"""
Generate .env file from .env.example

This script copies .env.example to .env if it doesn't exist.
Required for initial setup on Linux/macOS.

Usage:
    python generate_env.py
"""

import shutil
import os
import sys
from pathlib import Path

def main():
    """Generate .env file from .env.example"""

    env_example = Path('.env.example')
    env_file = Path('.env')

    # Check if .env.example exists
    if not env_example.exists():
        print("❌ Error: .env.example not found")
        sys.exit(1)

    # Check if .env already exists
    if env_file.exists():
        print(f"ℹ️  .env already exists, skipping")
        return 0

    try:
        # Copy .env.example to .env
        shutil.copy(str(env_example), str(env_file))
        print(f"✓ Created .env from .env.example")

        # Print instructions
        print("\n📋 Next steps:")
        print("1. Edit .env and configure required variables:")
        print("   - POSTGRES_PASSWORD (change-me-in-local)")
        print("   - SECRET_KEY (random string)")
        print("   - REDIS_PASSWORD (change-me-in-local)")
        print("   - GRAFANA_ADMIN_PASSWORD (change-me-in-local)")
        print("")
        print("2. Start services:")
        print("   Windows: scripts\\START.bat")
        print("   Linux/macOS: docker compose up -d")
        print("")

        return 0

    except Exception as e:
        print(f"❌ Error creating .env: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())

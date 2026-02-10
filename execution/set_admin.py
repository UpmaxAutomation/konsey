#!/usr/bin/env python3
"""Set a user as admin by email."""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import update, select
from backend.database.connection import AsyncSessionLocal
from backend.database.models import User


async def set_admin(email: str, is_admin: bool = True):
    """Set admin status for a user by email."""
    async with AsyncSessionLocal() as db:
        # Find user
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"User not found: {email}")
            return False

        # Update admin status
        await db.execute(
            update(User)
            .where(User.email == email)
            .values(is_admin=is_admin)
        )
        await db.commit()

        print(f"{'Set' if is_admin else 'Removed'} admin for: {email}")
        print(f"User ID: {user.id}")
        return True


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "sa@upmaxnow.com"
    asyncio.run(set_admin(email))

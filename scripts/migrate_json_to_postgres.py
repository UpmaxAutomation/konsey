#!/usr/bin/env python3
"""
Migration script to move data from JSON files to PostgreSQL.
Run this after setting up the database and before switching to production.

Usage:
    python scripts/migrate_json_to_postgres.py [--admin-email admin@example.com] [--admin-password admin123]
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.connection import engine, AsyncSessionLocal, init_db
from backend.database.models import (
    User, UserSettings, Conversation, Message, Folder, Rating
)
from backend.auth.password import hash_password


async def migrate_data(admin_email: str = "admin@example.com", admin_password: str = "admin123"):
    """Migrate all JSON data to PostgreSQL."""

    print("=" * 60)
    print("LLM Council: JSON to PostgreSQL Migration")
    print("=" * 60)

    # Initialize database
    print("\n[1/6] Initializing database...")
    await init_db()
    print("      Database tables created.")

    async with AsyncSessionLocal() as db:
        # Create admin user
        print("\n[2/6] Creating admin user...")
        admin = User(
            email=admin_email,
            password_hash=hash_password(admin_password),
            name="Admin",
            is_verified=True,
            is_admin=True,
        )
        db.add(admin)
        await db.flush()

        # Create default settings for admin
        admin_settings = UserSettings(
            user_id=admin.id,
            council_models=[
                "openai/gpt-4o",
                "google/gemini-2.5-flash",
                "anthropic/claude-sonnet-4",
                "x-ai/grok-3",
            ],
            chairman_model="google/gemini-2.5-flash",
        )
        db.add(admin_settings)
        print(f"      Admin user created: {admin_email}")

        # Migrate folders
        print("\n[3/6] Migrating folders...")
        folders_file = Path("data/conversations/folders.json")
        folder_count = 0
        if folders_file.exists():
            with open(folders_file) as f:
                folders_data = json.load(f)
                for folder_data in folders_data.get("folders", []):
                    folder = Folder(
                        id=folder_data["id"],
                        user_id=admin.id,
                        name=folder_data["name"],
                        color=folder_data.get("color", "#4a90e2"),
                        icon=folder_data.get("icon", "folder"),
                    )
                    db.add(folder)
                    folder_count += 1
        print(f"      Migrated {folder_count} folders.")

        # Migrate conversations
        print("\n[4/6] Migrating conversations...")
        conversations_dir = Path("data/conversations")
        conv_count = 0
        msg_count = 0

        if conversations_dir.exists():
            for conv_file in conversations_dir.glob("*.json"):
                if conv_file.name == "folders.json":
                    continue

                try:
                    with open(conv_file) as f:
                        conv_data = json.load(f)

                    # Create conversation
                    conv = Conversation(
                        id=uuid.UUID(conv_data["id"]),
                        user_id=admin.id,
                        title=conv_data.get("title", "Imported Conversation"),
                        folder_id=conv_data.get("folder_id"),
                        tags=conv_data.get("tags", []),
                        created_at=datetime.fromisoformat(conv_data["created_at"].replace("Z", "+00:00"))
                        if conv_data.get("created_at") else datetime.utcnow(),
                    )
                    db.add(conv)
                    await db.flush()
                    conv_count += 1

                    # Migrate messages
                    for idx, msg_data in enumerate(conv_data.get("messages", [])):
                        message = Message(
                            conversation_id=conv.id,
                            message_index=idx,
                            role=msg_data.get("role", "user"),
                            message_type=msg_data.get("type", "council"),
                            content=msg_data.get("content"),
                            stage1=msg_data.get("stage1"),
                            stage2=msg_data.get("stage2"),
                            stage3=msg_data.get("stage3"),
                            metadata=msg_data.get("metadata"),
                            thinking=msg_data.get("thinking"),
                            model=msg_data.get("model"),
                            usage_info=msg_data.get("usage_info"),
                            attached_files=msg_data.get("attached_files", []),
                        )
                        db.add(message)
                        msg_count += 1

                except Exception as e:
                    print(f"      Warning: Failed to migrate {conv_file.name}: {e}")

        print(f"      Migrated {conv_count} conversations with {msg_count} messages.")

        # Migrate ratings
        print("\n[5/6] Migrating ratings...")
        ratings_file = Path("data/ratings.json")
        rating_count = 0
        if ratings_file.exists():
            try:
                with open(ratings_file) as f:
                    ratings_data = json.load(f)
                    for rating_data in ratings_data.get("ratings", []):
                        rating = Rating(
                            user_id=admin.id,
                            conversation_id=uuid.UUID(rating_data["conversation_id"]),
                            message_index=rating_data["message_index"],
                            model_id=rating_data["model_id"],
                            rating=rating_data["rating"],
                            feedback_text=rating_data.get("feedback_text"),
                            query_category=rating_data.get("query_category"),
                        )
                        db.add(rating)
                        rating_count += 1
            except Exception as e:
                print(f"      Warning: Failed to migrate ratings: {e}")

        print(f"      Migrated {rating_count} ratings.")

        # Commit all changes
        print("\n[6/6] Committing changes...")
        await db.commit()
        print("      All data committed to database.")

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"\nAdmin credentials:")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    print("\nYou can now start the application with Docker:")
    print("  docker-compose up -d")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate JSON data to PostgreSQL")
    parser.add_argument("--admin-email", default="admin@example.com", help="Admin email")
    parser.add_argument("--admin-password", default="admin123", help="Admin password")
    args = parser.parse_args()

    asyncio.run(migrate_data(args.admin_email, args.admin_password))

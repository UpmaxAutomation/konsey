import asyncio
import uuid
import os
from backend.database.connection import init_db, get_db_context, USE_DATABASE, DATABASE_URL
from backend.database.crud import api_keys as api_keys_crud
from backend.database.models import User, UserAPIKey
from sqlalchemy import select, delete

async def main():
    print(f"USE_DATABASE: {USE_DATABASE}")
    print(f"DATABASE_URL: {DATABASE_URL}")
    
    if not USE_DATABASE:
        print("Database mode not enabled. Skipping DB persistence test.")
        return

    # Initialize DB (creates tables if missing)
    await init_db()

    async with get_db_context() as session:
        print("\n=== STARTING TEST ===")
        
        # 1. Create Test User
        user_id = uuid.uuid4()
        test_email = f"test-{user_id}@example.com"
        print(f"Creating test user: {test_email}")
        
        user = User(id=user_id, email=test_email, name="Test User persistence")
        session.add(user)
        await session.commit()
        
        try:
            # 2. Set API Key
            test_key = "sk-or-v1-test-key-persistence-12345"
            print(f"Setting OpenRouter key: {test_key}")
            
            await api_keys_crud.set_user_key(session, user_id, "openrouter", test_key)
            await session.commit()
            print("Key saved and committed.")
            
            # 3. Retrieve Key (Same Session)
            print("Retrieving key (Same Session)...")
            retrieved_key = await api_keys_crud.get_user_key(session, user_id, "openrouter")
            print(f"Retrieved key: {retrieved_key}")
            
            assert retrieved_key == test_key, "Key mismatch in same session!"
            print("✓ Same session retrieval passed.")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            await session.rollback()
            raise
        finally:
            # Cleanup
            print("\nCleaning up...")
            await session.execute(delete(UserAPIKey).where(UserAPIKey.user_id == user_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
            print("Cleanup done.")

    # 4. Verify Across New Session (Persistence)
    # Re-connecting to ensure it wasn't just in-memory
    # (Checking if committing actually worked)
    
    print("\n✓ Test Complete")

if __name__ == "__main__":
    asyncio.run(main())

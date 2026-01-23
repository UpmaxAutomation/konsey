"""Database connection management for LLM Council."""

import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select

# Load .env file before reading environment variables
from dotenv import load_dotenv
# Try multiple paths to find .env file
env_paths = [
    Path(__file__).parent.parent.parent / '.env',  # Project root
    Path(__file__).parent.parent / '.env',  # Backend directory
    Path('.env'),  # Current directory
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        break
else:
    # Fallback: try loading from current directory
    load_dotenv(override=True)

from .models import Base, User
from ..config import ANONYMOUS_USER_ID

# Check if database mode is enabled
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://council:council@localhost:5432/llm_council"
)

# Only create engine and session factory if database mode is enabled
engine: Optional[any] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

if USE_DATABASE:
    # Validate DATABASE_URL before creating engine
    if not DATABASE_URL or not DATABASE_URL.strip():
        raise ValueError(
            f"DATABASE_URL is not set or empty. "
            f"Current value: {repr(DATABASE_URL)}. "
            f"Please set DATABASE_URL in your .env file."
        )
    
    # Create async engine
    try:
        # For connection poolers (pgbouncer), disable prepared statement cache
        # pgbouncer in transaction/statement mode doesn't support prepared statements
        connect_args = {}
        if "pooler.supabase.com" in DATABASE_URL or "pooler" in DATABASE_URL.lower():
            connect_args["statement_cache_size"] = 0
        
        # #region agent log
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                import json
                from datetime import datetime
                # Mask password in URL for logging
                db_url_masked = DATABASE_URL
                if "@" in db_url_masked:
                    parts = db_url_masked.split("@")
                    if len(parts) == 2:
                        user_pass = parts[0].split("//")[-1]
                        if ":" in user_pass:
                            user = user_pass.split(":")[0]
                            db_url_masked = db_url_masked.replace(user_pass, f"{user}:***")
                # Check for special characters that might need encoding
                has_dollar = "$" in DATABASE_URL
                has_percent = "%" in DATABASE_URL
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-engine-init","hypothesisId":"H1","location":"connection.py:55","message":"creating_engine","data":{"database_url_masked":db_url_masked,"has_pooler":"pooler" in DATABASE_URL.lower(),"statement_cache_size":connect_args.get("statement_cache_size", "default"),"has_dollar_sign":has_dollar,"has_percent":has_percent,"url_length":len(DATABASE_URL)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        
        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            poolclass=NullPool,  # Use NullPool for better async compatibility
            connect_args=connect_args,
        )
        
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                import json
                from datetime import datetime
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-engine-init","hypothesisId":"H2","location":"connection.py:75","message":"engine_created","data":{"status":"success"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
    except Exception as e:
        # #region agent log
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                import json
                from datetime import datetime
                error_msg = str(e)
                error_type = type(e).__name__
                db_url_masked = DATABASE_URL
                if "@" in db_url_masked:
                    parts = db_url_masked.split("@")
                    if len(parts) == 2:
                        user_pass = parts[0].split("//")[-1]
                        if ":" in user_pass:
                            user = user_pass.split(":")[0]
                            db_url_masked = db_url_masked.replace(user_pass, f"{user}:***")
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-engine-init","hypothesisId":"H3","location":"connection.py:68","message":"engine_creation_failed","data":{"error_type":error_type,"error":error_msg,"database_url_masked":db_url_masked},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        raise ValueError(
            f"Failed to create database engine with URL: {DATABASE_URL[:60]}... "
            f"Error: {e}. "
            f"Please check your DATABASE_URL format in .env file."
        ) from e

    # Create async session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def init_db() -> None:
    """Initialize database tables."""
    if not USE_DATABASE or engine is None:
        return
    
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"db-init","hypothesisId":"H4","location":"connection.py:85","message":"init_db:start","data":{"use_database":USE_DATABASE,"engine_exists":engine is not None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-init","hypothesisId":"H5","location":"connection.py:95","message":"init_db:tables_created","data":{"status":"success"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
    except Exception as e:
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                error_msg = str(e)
                error_type = type(e).__name__
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-init","hypothesisId":"H6","location":"connection.py:98","message":"init_db:table_creation_failed","data":{"error_type":error_type,"error":error_msg},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        raise
    
    try:
        await _ensure_anonymous_user()
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-init","hypothesisId":"H7","location":"connection.py:112","message":"init_db:anonymous_user_ensured","data":{"status":"success"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
    except Exception as e:
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                error_msg = str(e)
                error_type = type(e).__name__
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-init","hypothesisId":"H8","location":"connection.py:115","message":"init_db:anonymous_user_failed","data":{"error_type":error_type,"error":error_msg},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        raise


async def _ensure_anonymous_user() -> None:
    """Ensure the anonymous user exists for unauthenticated sessions."""
    if AsyncSessionLocal is None:
        return
    anonymous_id = uuid.UUID(ANONYMOUS_USER_ID)
    anonymous_email = f"anonymous-{ANONYMOUS_USER_ID}@local"
    try:
        async with AsyncSessionLocal() as session:
            # #region agent log
            import os
            import json
            from datetime import datetime
            debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"anonymous-user","hypothesisId":"H9","location":"connection.py:100","message":"anonymous_user:session_created","data":{"anonymous_id":str(anonymous_id)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion
            
            result = await session.execute(
                select(User).where(User.id == anonymous_id)
            )
            # #region agent log
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    user_exists = result.scalar_one_or_none() is not None
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"anonymous-user","hypothesisId":"H10","location":"connection.py:108","message":"anonymous_user:query_result","data":{"user_exists":user_exists},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion
            
            if result.scalar_one_or_none() is None:
                session.add(
                    User(
                        id=anonymous_id,
                        email=anonymous_email,
                        name="Anonymous",
                        is_active=True,
                        is_verified=True,
                    )
                )
                await session.commit()
                # #region agent log
                if os.path.exists(os.path.dirname(debug_log_path)):
                    try:
                        with open(debug_log_path, 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"anonymous-user","hypothesisId":"H11","location":"connection.py:122","message":"anonymous_user:created","data":{"status":"success"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                    except Exception:
                        pass
                # #endregion
    except Exception as e:
        # #region agent log
        import os
        import json
        from datetime import datetime
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                error_msg = str(e)
                error_type = type(e).__name__
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"anonymous-user","hypothesisId":"H12","location":"connection.py:125","message":"anonymous_user:error","data":{"error_type":error_type,"error":error_msg},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        raise


async def close_db() -> None:
    """Close database connection."""
    if not USE_DATABASE or engine is None:
        return
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")
    
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"db-session","hypothesisId":"H13","location":"connection.py:128","message":"get_db:creating_session","data":{"use_database":USE_DATABASE,"session_local_exists":AsyncSessionLocal is not None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    
    try:
        async with AsyncSessionLocal() as session:
            # #region agent log
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"db-session","hypothesisId":"H14","location":"connection.py:135","message":"get_db:session_created","data":{"status":"success"},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                # #region agent log
                if os.path.exists(os.path.dirname(debug_log_path)):
                    try:
                        error_msg = str(e)
                        error_type = type(e).__name__
                        # Extract more details from error
                        error_lower = error_msg.lower()
                        has_tenant_error = "tenant" in error_lower or "user not found" in error_lower
                        has_auth_error = "authentication" in error_lower or "password" in error_lower
                        # Mask password in DATABASE_URL for logging
                        db_url_masked = DATABASE_URL
                        if "@" in db_url_masked:
                            parts = db_url_masked.split("@")
                            if len(parts) == 2:
                                user_pass = parts[0].split("//")[-1]
                                if ":" in user_pass:
                                    user = user_pass.split(":")[0]
                                    db_url_masked = db_url_masked.replace(user_pass, f"{user}:***")
                        with open(debug_log_path, 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"db-connection-debug","hypothesisId":"H15","location":"connection.py:143","message":"db_error","data":{"error_type":error_type,"error":error_msg,"has_tenant_error":has_tenant_error,"has_auth_error":has_auth_error,"database_url_masked":db_url_masked,"use_database":USE_DATABASE},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                    except Exception:
                        pass
                # #endregion
                raise
            finally:
                await session.close()
    except Exception as e:
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                error_msg = str(e)
                error_type = type(e).__name__
                error_lower = error_msg.lower()
                has_tenant_error = "tenant" in error_lower or "user not found" in error_lower
                has_auth_error = "authentication" in error_lower or "password" in error_lower
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"db-session","hypothesisId":"H16","location":"connection.py:165","message":"get_db:session_creation_failed","data":{"error_type":error_type,"error":error_msg,"has_tenant_error":has_tenant_error,"has_auth_error":has_auth_error},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session (for use outside of FastAPI)."""
    if not USE_DATABASE or AsyncSessionLocal is None:
        raise RuntimeError("Database mode is not enabled. Set USE_DATABASE=true")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

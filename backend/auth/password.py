"""Password hashing utilities using Argon2."""

from passlib.context import CryptContext

# Configure Argon2 password context
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=2,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if password hash needs to be updated."""
    return pwd_context.needs_update(hashed_password)

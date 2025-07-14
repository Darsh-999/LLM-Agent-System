# backend/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against its hashed version.

    Args:
    - plain_password (str): The password to verify.
    - hashed_password (str): The stored, hashed password.

    Returns:
    - bool: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password.

    Args:
    - password (str): The password to hash.

    Returns:
    - str: The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any]) -> str:
    """
    Creates a JWT access token.

    Args:
    - data (Dict[str, Any]): The data to encode in the token (the "payload").

    Returns:
    - str: The encoded JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

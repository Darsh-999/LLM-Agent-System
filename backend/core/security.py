# backend/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .models import TokenData

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

def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes a JWT access token and validates its signature and expiration.

    Args:
    - token (str): The JWT token to decode.

    Returns:
    - Optional[TokenData]: The decoded token data if valid, otherwise None.
    
    Raises:
    - HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Subject (sub) claim missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(email=email, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

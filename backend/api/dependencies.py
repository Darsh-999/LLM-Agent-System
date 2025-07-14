# backend/api/dependencies.py

from typing import Annotated, Dict, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from backend.core.security import decode_access_token
from backend.db.user_manager import get_user_by_email
from backend.core.models import UserOut
from backend.core.logging_config import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    request: Request, token: Annotated[str, Depends(oauth2_scheme)]
) -> Dict[str, Any]:
    """
    A dependency function to get the current authenticated user.

    This function is used to protect endpoints. It performs the following:
    1. Extracts the token from the Authorization header.
    2. Decodes and validates the JWT.
    3. Retrieves the user from the database based on the token's subject.
    4. Raises an HTTP 401 exception if any step fails.

    Args:
    - request (Request): The incoming request object, used to access the database.
    - token (str): The bearer token provided by the client.

    Returns:
    - Dict[str, Any]: The user document from the database.
    """
    token_data = decode_access_token(token)
    if not token_data or not token_data.email:
        logger.warning("Token decoding failed or email missing in token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_email(request.app.db, token_data.email)
    if user is None:
        logger.warning(f"User from token not found in DB: {token_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Authenticated user: {user['email']}")
    return user

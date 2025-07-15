# backend/api/dependencies.py

from typing import Annotated, Any, Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from backend.core.logging_config import logger
from backend.core.models import Role, UserOut
from backend.core.security import decode_access_token
from backend.db.user_manager import get_user_by_email

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


async def require_manager_role(
    current_user: Annotated[Dict, Depends(get_current_user)],
) -> Dict[str, Any]:
    """
    A dependency that requires the current user to have the 'manager' role.
    Raises a 403 Forbidden error if the user does not have permission.
    """
    if current_user.get("role") != "manager":
        logger.warning(
            f"User '{current_user['email']}' with role '{current_user.get('role')}' attempted manager-only action."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for your user role.",
        )
    return current_user


async def require_upload_pdf_permission(
    current_user: Annotated[Dict, Depends(get_current_user)],
) -> Dict[str, Any]:
    """
    A dependency that requires the user to be a 'manager' or 'assistant_manager'.
    Raises a 403 Forbidden error if the user does not have permission.
    """
    user_role = current_user.get("role")
    if user_role not in ["manager", "assistant_manager"]:
        logger.warning(
            f"User '{current_user['email']}' with role '{user_role}' attempted to upload a PDF."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload PDFs.",
        )
    return current_user


async def require_upload_link_permission(
    current_user: Annotated[Dict, Depends(get_current_user)],
) -> Dict[str, Any]:
    """
    A dependency that requires the user to be a 'manager' or 'developer'.
    Raises a 403 Forbidden error if the user does not have permission.
    """
    user_role = current_user.get("role")
    if user_role not in ["manager", "developer"]:
        logger.warning(
            f"User '{current_user['email']}' with role '{user_role}' attempted to submit a web link."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to submit web links.",
        )
    return current_user

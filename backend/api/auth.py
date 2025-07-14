# backend/api/auth.py

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.core.logging_config import logger
from backend.core.models import Token, UserCreate, UserOut
from backend.core.security import create_access_token, verify_password
from backend.db.user_manager import create_new_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(request: Request, user_in: UserCreate) -> UserOut:
    """
    Handles user registration.

    - Validates the incoming user data.
    - Checks for existing users.
    - Hashes the password.
    - Stores the new user in the database.
    """
    logger.info(f"Registration attempt for email: {user_in.email}")

    created_user = await create_new_user(request.app.db, user_in)

    return UserOut(**created_user)


@router.post("/login", response_model=Token)
async def login(
    request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    Handles user login and JWT token generation.
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    user = await get_user_by_email(request.app.db, form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}
    )

    logger.info(f"User logged in successfully: {form_data.username}")
    return Token(access_token=access_token, token_type="bearer")

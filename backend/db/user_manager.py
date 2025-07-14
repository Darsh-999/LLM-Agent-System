# backend/db/user_manager.py

from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from backend.core.models import UserInDB
from backend.core.security import get_password_hash
from backend.core.logging_config import logger

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single user from the database by their email.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - email (str): The user's email address.

    Returns:
    - Optional[Dict[str, Any]]: The user document if found, otherwise None.
    """
    user = await db["users"].find_one({"email": email})
    return user

async def create_new_user(db: AsyncIOMotorDatabase, user_data: UserInDB) -> Dict[str, Any]:
    """
    Creates a new user in the database.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - user_data (UserInDB): The user data to be stored.

    Returns:
    - Dict[str, Any]: The created user document.

    Raises:
    - HTTPException: If a user with the same email already exists.
    """
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        logger.warning(f"Attempted to register existing user: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    user_doc = {
        "email": user_data.email,
        "hashed_password": hashed_password,
        "role": user_data.role,
    }

    result = await db["users"].insert_one(user_doc)
    logger.info(f"New user created: {user_data.email}, role: {user_data.role}")

    new_user = await db["users"].find_one({"_id": result.inserted_id})
    return new_user
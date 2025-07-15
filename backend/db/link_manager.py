from typing import List, Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.models import WebLinkBase
from backend.core.logging_config import logger


async def create_link_record(
    db: AsyncIOMotorDatabase, link_data: WebLinkBase
) -> Dict[str, Any]:
    """Creates a new web link record in the database."""
    link_doc = link_data.model_dump(mode="json")  # Use mode="json" for HttpUrl
    result = await db["web_links"].insert_one(link_doc)
    logger.info(
        f"Web link record created for '{link_data.url}' by user '{link_data.owner_email}'."
    )
    new_link = await db["web_links"].find_one({"_id": result.inserted_id})
    return new_link


async def get_links_by_owner(
    db: AsyncIOMotorDatabase, owner_email: str
) -> List[Dict[str, Any]]:
    """Retrieves a list of all web links owned by a specific user."""
    cursor = db["web_links"].find({"owner_email": owner_email})
    return await cursor.to_list(length=None)


async def get_link_by_id(
    db: AsyncIOMotorDatabase, link_id: str
) -> Optional[Dict[str, Any]]:
    """Retrieves a single web link by its ID."""
    return await db["web_links"].find_one({"_id": ObjectId(link_id)})


async def delete_link_record(db: AsyncIOMotorDatabase, link_id: str) -> bool:
    """
    Deletes a web link record from the database.
    This version does not perform an ownership check, as it's intended
    to be called by an authorized role (manager).

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - link_id (str): The ID of the link to delete.

    Returns:
    - bool: True if deletion was successful, False otherwise.
    """
    logger.info(f"Admin action: Deleting web link record '{link_id}'.")

    result = await db["web_links"].delete_one({"_id": ObjectId(link_id)})

    if result.deleted_count == 1:
        logger.info(f"Successfully deleted web link record '{link_id}'.")
        return True

    logger.warning(f"Failed to delete web link record '{link_id}' from database.")
    return False

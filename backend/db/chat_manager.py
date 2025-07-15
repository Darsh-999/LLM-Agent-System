from typing import List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from backend.core.models import ChatSessionBase, ChatMessageBase, Citation
from backend.core.logging_config import logger


async def create_chat_session(
    db: AsyncIOMotorDatabase, session_data: ChatSessionBase
) -> Dict[str, Any]:
    """Creates a new, empty chat session."""
    session_doc = session_data.model_dump()
    session_doc["created_at"] = datetime.now()
    result = await db["chat_sessions"].insert_one(session_doc)
    logger.info(
        f"New chat session created with id '{result.inserted_id}' for user '{session_data.owner_email}'."
    )
    new_session = await db["chat_sessions"].find_one({"_id": result.inserted_id})
    return new_session


async def get_chats_by_owner(
    db: AsyncIOMotorDatabase, owner_email: str
) -> List[Dict[str, Any]]:
    """Retrieves all chat sessions for a specific user."""
    cursor = (
        db["chat_sessions"].find({"owner_email": owner_email}).sort("created_at", -1)
    )
    return await cursor.to_list(length=None)


async def get_chat_session_by_id(
    db: AsyncIOMotorDatabase, chat_id: str
) -> Dict[str, Any]:
    """Retrieves a single chat session by its ID."""
    return await db["chat_sessions"].find_one({"_id": ObjectId(chat_id)})


async def add_message_to_chat(
    db: AsyncIOMotorDatabase,
    chat_id: str,
    message_data: ChatMessageBase,
    citations: List[Citation] = [],
) -> Dict[str, Any]:
    """Adds a new message to a specific chat session."""
    message_doc = message_data.model_dump()
    message_doc["chat_id"] = ObjectId(chat_id)
    message_doc["created_at"] = datetime.now()
    message_doc["citations"] = [c.model_dump() for c in citations]

    result = await db["chat_messages"].insert_one(message_doc)
    logger.info(f"Message from '{message_data.role}' added to chat '{chat_id}'.")
    new_message = await db["chat_messages"].find_one({"_id": result.inserted_id})
    return new_message


async def get_messages_by_chat_id(
    db: AsyncIOMotorDatabase, chat_id: str
) -> List[Dict[str, Any]]:
    """Retrieves all messages for a specific chat session, sorted by creation time."""
    cursor = (
        db["chat_messages"].find({"chat_id": ObjectId(chat_id)}).sort("created_at", 1)
    )
    return await cursor.to_list(length=None)


async def update_chat_title(db: AsyncIOMotorDatabase, chat_id: str, title: str):
    """Updates the title of a chat session."""
    await db["chat_sessions"].update_one(
        {"_id": ObjectId(chat_id)}, {"$set": {"title": title}}
    )
    logger.info(f"Updated title for chat '{chat_id}' to '{title}'.")

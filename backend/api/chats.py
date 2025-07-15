# backend/api/chats.py

from typing import List, Dict, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Path
from bson import ObjectId

from backend.api.dependencies import get_current_user
from backend.core.logging_config import logger
from backend.core.models import (
    ChatSessionBase,
    ChatSessionOut,
    ChatMessageBase,
    ChatMessageOut,
)
from backend.db import chat_manager
from backend.services.rag_service import get_rag_response

router = APIRouter(prefix="/chats", tags=["Chat Management"])


@router.post("/", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_new_chat(
    request: Request, current_user: Annotated[Dict, Depends(get_current_user)]
):
    """Creates a new, empty chat session for the logged-in user."""
    session_data = ChatSessionBase(owner_email=current_user["email"])
    new_session = await chat_manager.create_chat_session(request.app.db, session_data)
    return ChatSessionOut.model_validate(new_session)


@router.get("/", response_model=List[ChatSessionOut])
async def list_user_chats(
    request: Request, current_user: Annotated[Dict, Depends(get_current_user)]
):
    """Lists all past chat sessions for the logged-in user."""
    chats = await chat_manager.get_chats_by_owner(request.app.db, current_user["email"])
    return [ChatSessionOut.model_validate(chat) for chat in chats]


@router.get("/{chat_id}/messages", response_model=List[ChatMessageOut])
async def get_chat_messages(
    request: Request,
    current_user: Annotated[Dict, Depends(get_current_user)],
    chat_id: str = Path(
        ..., description="The ID of the chat session to retrieve messages for."
    ),
):
    """Retrieves all messages for a specific, completed chat session."""
    # Verify ownership
    chat_session = await chat_manager.get_chat_session_by_id(request.app.db, chat_id)
    if not chat_session or chat_session["owner_email"] != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found."
        )

    messages = await chat_manager.get_messages_by_chat_id(request.app.db, chat_id)
    return [ChatMessageOut.model_validate(msg) for msg in messages]


@router.post("/{chat_id}/query", response_model=ChatMessageOut)
async def post_chat_query(
    request: Request,
    current_user: Annotated[Dict, Depends(get_current_user)],
    chat_id: str = Path(
        ..., description="The ID of the chat session to post the query to."
    ),
    query: str = Body(..., embed=True, description="The user's question."),
):
    """
    The main interaction endpoint.
    - Takes a user's question.
    - Calls the RAG service to get a response.
    - Saves the user query and assistant response to the database.
    - Returns the assistant's response.
    """
    logger.info(f"User '{current_user['email']}' posted query to chat '{chat_id}'.")

    # 1. Verify ownership of the chat
    chat_session = await chat_manager.get_chat_session_by_id(request.app.db, chat_id)
    if not chat_session or chat_session["owner_email"] != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found."
        )

    # 2. Save the user's message
    user_message = ChatMessageBase(role="user", content=query)
    await chat_manager.add_message_to_chat(request.app.db, chat_id, user_message)

    # 3. Get chat history
    message_history = await chat_manager.get_messages_by_chat_id(
        request.app.db, chat_id
    )

    # 4. Get RAG response
    try:
        answer, citations = await get_rag_response(query, message_history)
    except Exception as e:
        logger.error(
            f"Error getting RAG response for chat '{chat_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get a response from the AI service.",
        )

    # 5. Save the assistant's response
    assistant_message = ChatMessageBase(role="assistant", content=answer)
    saved_assistant_message = await chat_manager.add_message_to_chat(
        request.app.db, chat_id, assistant_message, citations
    )

    # 6. Update chat title with the first user query if it's a new chat
    if len(message_history) <= 1 and len(query) > 0:  # This is the first real message
        title = query[:50] + "..." if len(query) > 50 else query
        await chat_manager.update_chat_title(request.app.db, chat_id, title)

    return ChatMessageOut.model_validate(saved_assistant_message)

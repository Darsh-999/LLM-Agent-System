# backend/db/pdf_manager.py

import os
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.logging_config import logger
from backend.core.models import PDFBase

PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "uploaded_pdfs")


async def create_pdf_record(
    db: AsyncIOMotorDatabase, pdf_data: PDFBase
) -> Dict[str, Any]:
    """
    Creates a new PDF record in the database.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - pdf_data (PDFBase): The PDF metadata to store.

    Returns:
    - Dict[str, Any]: The newly created PDF document from the database.
    """
    pdf_doc = pdf_data.model_dump()
    result = await db["pdfs"].insert_one(pdf_doc)
    logger.info(
        f"PDF record created for '{pdf_data.filename}' by user '{pdf_data.owner_email}'."
    )

    new_pdf = await db["pdfs"].find_one({"_id": result.inserted_id})
    return new_pdf


async def get_pdfs_by_owner(
    db: AsyncIOMotorDatabase, owner_email: str
) -> List[Dict[str, Any]]:
    """
    Retrieves a list of all PDFs owned by a specific user.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - owner_email (str): The email of the user who owns the PDFs.

    Returns:
    - List[Dict[str, Any]]: A list of PDF documents.
    """

    cursor = db["pdfs"].find({"owner_email": owner_email})
    pdfs = await cursor.to_list(length=None)  # length=None to get all documents
    logger.info(f"Retrieved {len(pdfs)} PDFs for user '{owner_email}'.")
    return pdfs


async def get_pdf_by_id(
    db: AsyncIOMotorDatabase, pdf_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single PDF by its ID.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - pdf_id (str): The ID of the PDF to retrieve.

    Returns:
    - Optional[Dict[str, Any]]: The PDF document if found, otherwise None.
    """
    try:
        object_id = ObjectId(pdf_id)
    except Exception:
        logger.warning(f"Invalid PDF ID format received: {pdf_id}")
        return None

    pdf = await db["pdfs"].find_one({"_id": object_id})
    return pdf


async def delete_pdf_record(
    db: AsyncIOMotorDatabase, pdf_id: str, owner_email: str
) -> bool:
    """

    Deletes a PDF record from the database and its corresponding file from disk.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - pdf_id (str): The ID of the PDF to delete.
    - owner_email (str): The email of the user attempting the deletion, for ownership verification.

    Returns:
    - bool: True if deletion was successful, False otherwise.
    """
    pdf_to_delete = await get_pdf_by_id(db, pdf_id)

    if not pdf_to_delete:
        logger.warning(
            f"User '{owner_email}' attempted to delete non-existent PDF with id '{pdf_id}'."
        )
        return False

    if pdf_to_delete["owner_email"] != owner_email:
        logger.error(
            f"SECURITY: User '{owner_email}' attempted to delete PDF owned by '{pdf_to_delete['owner_email']}'."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have permission to delete this file.",
        )

    file_path = os.path.join(PDF_STORAGE_PATH, pdf_to_delete["filename"])
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully deleted PDF file: {file_path}")
        else:
            logger.warning(f"PDF file not found on disk for deletion: {file_path}")
    except OSError as e:
        logger.error(f"Error deleting file {file_path}: {e}")

    result = await db["pdfs"].delete_one({"_id": ObjectId(pdf_id)})

    if result.deleted_count == 1:
        logger.info(
            f"Successfully deleted PDF record '{pdf_id}' for user '{owner_email}'."
        )
        return True

    logger.warning(
        f"Failed to delete PDF record '{pdf_id}' from database for user '{owner_email}'."
    )
    return False


async def delete_pdf_record_as_admin(
    db: AsyncIOMotorDatabase, pdf_doc: Dict[str, Any]
) -> bool:
    """
    Deletes a PDF record and its file from disk without an ownership check.
    To be used by authorized roles like 'manager'.

    Args:
    - db (AsyncIOMotorDatabase): The database instance.
    - pdf_doc (Dict[str, Any]): The full PDF document to be deleted.

    Returns:
    - bool: True if deletion was successful, False otherwise.
    """
    pdf_id_str = str(pdf_doc["_id"])
    logger.info(f"Admin action: Deleting PDF record '{pdf_id_str}'.")

    file_path = os.path.join(PDF_STORAGE_PATH, pdf_doc["filename"])
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully deleted PDF file: {file_path}")
        else:
            logger.warning(f"PDF file not found on disk for deletion: {file_path}")
    except OSError as e:
        logger.error(f"Error deleting file {file_path}: {e}")

    result = await db["pdfs"].delete_one({"_id": pdf_doc["_id"]})

    return result.deleted_count == 1

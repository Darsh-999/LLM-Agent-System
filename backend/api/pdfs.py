# backend/api/pdfs.py

import os
import shutil
from typing import Annotated, Dict, List

import fitz
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from backend.api.dependencies import get_current_user
from backend.core.config import settings
from backend.core.logging_config import logger
from backend.core.models import PDFBase, PDFOut
from backend.db.pdf_manager import (
    create_pdf_record,
    delete_pdf_record,
    get_pdfs_by_owner,
)
from backend.services.pdf_processor import process_and_embed_pdfs

router = APIRouter(prefix="/pdfs", tags=["PDF Management"])

PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "uploaded_pdfs")
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_and_process_pdfs(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[Dict, Depends(get_current_user)],
    files: List[UploadFile] = File(...),
):
    """
    Accepts one or more PDF files, saves them, and triggers a background
    task to process and create embeddings for them.

    Responds immediately with a confirmation message.
    """
    user_email = current_user["email"]
    logger.info(f"User '{user_email}' initiated bulk upload of {len(files)} files.")

    user_temp_dir = os.path.join(settings.PDF_STORAGE_PATH, user_email, "temp")
    os.makedirs(user_temp_dir, exist_ok=True)

    saved_file_paths = []
    for file in files:
        if file.content_type != "application/pdf":
            logger.warning(
                f"Skipping non-PDF file '{file.filename}' uploaded by '{user_email}'."
            )
            continue

        try:
            file_path = os.path.join(user_temp_dir, os.path.basename(file.filename))
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_file_paths.append(file_path)
        finally:
            file.file.close()

    if not saved_file_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF files were uploaded.",
        )

    background_tasks.add_task(
        process_and_embed_pdfs, file_paths=saved_file_paths, owner_email=user_email
    )

    logger.info(
        f"Task for processing {len(saved_file_paths)} PDFs for '{user_email}' has been added to background."
    )

    return {
        "message": f"{len(saved_file_paths)} PDF(s) received and are being processed in the background. "
        "They will appear in your list shortly."
    }


@router.get("/", response_model=List[PDFOut])
async def list_user_pdfs(
    request: Request, current_user: Annotated[Dict, Depends(get_current_user)]
):
    """
    Retrieves a list of all PDFs uploaded by the current authenticated user.

    This is a protected endpoint.
    """
    logger.info(f"Fetching PDFs for user '{current_user['email']}'")

    pdfs_from_db = await get_pdfs_by_owner(request.app.db, current_user["email"])

    response_pdfs = [PDFOut.model_validate(pdf) for pdf in pdfs_from_db]
    
    return response_pdfs


@router.delete("/{pdf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pdf(
    request: Request,
    pdf_id: str,
    current_user: Annotated[Dict, Depends(get_current_user)],
):
    """
    Deletes a specific PDF owned by the current authenticated user.
    This deletes both the file from disk and the record from the database.

    This is a protected endpoint.
    """
    logger.info(
        f"User '{current_user['email']}' attempting to delete PDF with id: {pdf_id}"
    )

    success = await delete_pdf_record(request.app.db, pdf_id, current_user["email"])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF with id '{pdf_id}' not found.",
        )

    return None

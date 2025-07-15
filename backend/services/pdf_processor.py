# backend/services/pdf_processor.py

import multiprocessing
import os
from typing import List

import fitz
import motor.motor_asyncio
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.core.config import settings
from backend.core.logging_config import logger
from backend.core.models import PDFBase
from backend.db.pdf_manager import create_pdf_record


def _load_and_process_single_pdf(file_path: str):
    """
    Worker function: Loads a single PDF file and adds source_type metadata.
    """
    try:
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_type"] = "pdf"
        return docs
    except Exception as e:
        logger.error(f"Error loading PDF in worker process {file_path}: {e}")
        return []


async def process_and_embed_pdfs(file_paths: List[str], owner_email: str):
    logger.info(
        f"Background task started: Processing {len(file_paths)} PDFs for user '{owner_email}'."
    )

    db_client = None
    try:
        logger.info("Loading documents with multiprocessing...")
        with multiprocessing.Pool() as pool:
            results = pool.map(_load_and_process_single_pdf, file_paths)

        all_docs = [doc for sublist in results for doc in sublist]

        if not all_docs:
            logger.warning(
                "No documents were successfully loaded. Aborting background task."
            )
            return

        logger.info(
            f"Successfully loaded {len(all_docs)} pages from {len(file_paths)} files."
        )

        logger.info("Splitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        chunks = text_splitter.split_documents(all_docs)
        logger.info(f"Split into {len(chunks)} text chunks.")

        logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL_NAME}")
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

        logger.info(f"Creating/updating vector store at: {settings.CHROMA_DB_PATH}")
        await Chroma.afrom_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.CHROMA_DB_PATH,
        )
        logger.info("Successfully saved embeddings to ChromaDB.")

        logger.info("Creating PDF records in MongoDB...")
        db_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        db = db_client[settings.DATABASE_NAME]

        for file_path in file_paths:
            try:
                with fitz.open(file_path) as doc:
                    page_count = doc.page_count
                    title = (
                        doc.metadata.get("title")
                        or os.path.splitext(os.path.basename(file_path))[0]
                    )

                relative_path = os.path.join(owner_email, os.path.basename(file_path))

                pdf_data = PDFBase(
                    filename=relative_path,
                    title=title,
                    page_count=page_count,
                    owner_email=owner_email,
                )
                await create_pdf_record(db, pdf_data)
            except Exception as e:
                logger.error(f"Failed to create MongoDB record for {file_path}: {e}")

        logger.info(f"Background task finished for user '{owner_email}'.")

    except Exception as e:
        logger.error(
            f"A critical error occurred during background PDF processing: {e}",
            exc_info=True,
        )
    finally:
        if db_client:
            db_client.close()

        logger.info("Cleaning up temporary PDF files.")
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.error(f"Error cleaning up file {path}: {e}")
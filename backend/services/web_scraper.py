# backend/services/web_scraper.py

import asyncio
from typing import List

# LangChain components
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# App-specific imports
from backend.core.config import settings
from backend.core.logging_config import logger
from backend.core.models import WebLinkBase
from backend.db.link_manager import create_link_record
import motor.motor_asyncio
import os


async def scrape_and_embed_links(urls: List[str], owner_email: str):
    """
    Background task: Scrapes web pages, creates embeddings, stores them in
    ChromaDB, and updates MongoDB.
    """
    logger.info(
        f"Background task started: Scraping {len(urls)} URLs for user '{owner_email}'."
    )

    db_client = None
    try:
        logger.info("Loading documents from web links...")

        loader = WebBaseLoader(web_paths=urls)
        loader.requests_per_second = 2
        all_docs = list(loader.lazy_load())

        if not all_docs:
            logger.warning("No content successfully loaded from URLs. Aborting task.")
            return

        for doc in all_docs:
            doc.metadata["source_type"] = "web"

        logger.info(f"Successfully loaded content from {len(all_docs)} URLs.")

        logger.info("Splitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        chunks = text_splitter.split_documents(all_docs)
        logger.info(f"Split into {len(chunks)} text chunks.")

        logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL_NAME}")
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

        logger.info(f"Adding embeddings to vector store at: {settings.CHROMA_DB_PATH}")
        await Chroma.afrom_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.CHROMA_DB_PATH,
        )
        logger.info("Successfully saved web page embeddings to ChromaDB.")

        logger.info("Creating web link records in MongoDB...")
        db_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        db = db_client[settings.DATABASE_NAME]

        for doc in all_docs:
            url = doc.metadata.get("source")
            title = doc.metadata.get("title", f"Content from {url}")

            link_data = WebLinkBase(url=url, title=title, owner_email=owner_email)
            await create_link_record(db, link_data)

        logger.info(f"Background scraping task finished for user '{owner_email}'.")

    except Exception as e:
        logger.error(
            f"A critical error occurred during background web scraping: {e}",
            exc_info=True,
        )
    finally:
        if db_client:
            db_client.close()

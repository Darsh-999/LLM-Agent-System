# backend/main.py

import os
from contextlib import asynccontextmanager
from typing import Dict

import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI

from backend.api import auth, pdfs, chats, links
from backend.core.config import settings
from backend.core.logging_config import logger

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Connecting to MongoDB...")
    try:
        app.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        app.db = app.mongodb_client[DATABASE_NAME]
        logger.info("Successfully connected to MongoDB.")
        yield
    finally:
        logger.info("Application shutdown: Closing MongoDB connection...")
        if hasattr(app, "mongodb_client"):
            app.mongodb_client.close()
            logger.info("MongoDB connection closed.")


app = FastAPI(
    title="Agentic RAG System API",
    description="API for a RAG system with PDF and web scraping capabilities.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(pdfs.router)
app.include_router(chats.router)
app.include_router(links.router)


@app.get("/", tags=["Health Check"])
async def root_health_check() -> Dict[str, str]:
    """
    Root Health Check Endpoint.
    """
    logger.info("Root health check endpoint was called.")
    return {"status": "ok"}

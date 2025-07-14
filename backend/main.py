# backend/main.py

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from typing import Dict

import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")


def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    logger = logging.getLogger("rag_app")
    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024 * 5, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger


logger = setup_logging()


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


@app.get("/", tags=["Health Check"])
async def root_health_check() -> Dict[str, str]:
    """
    Root Health Check Endpoint.
    """
    logger.info("Root health check endpoint was called.")
    return {"status": "ok"}

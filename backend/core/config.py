# backend/core/config.py

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    MONGO_URI: str
    DATABASE_NAME: str

    JWT_SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    GOOGLE_API_KEY: str
    COHERE_API_KEY: str

    PDF_STORAGE_PATH: str = "uploaded_pdfs"
    CHROMA_DB_PATH: str = "chroma_db"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    WEB_SCRAPER_REQUEST_TIMEOUT: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

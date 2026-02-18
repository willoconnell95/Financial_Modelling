from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Set
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Financial Modelling Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"

    # Database
    DATABASE_URL: str = "sqlite:///./data/financial_modelling.db"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # OpenAI (optional - enables enhanced NLP)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Extraction defaults
    EXTRACTION_CONFIDENCE_THRESHOLD: float = 0.6

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions(self) -> Set[str]:
        return {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

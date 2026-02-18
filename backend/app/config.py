import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Financial Modelling Platform"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./financial_model.db",
        env="DATABASE_URL",
    )

    # Storage
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")

    # LLM (optional - used for advanced NLP command parsing)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    llm_provider: str = Field(default="local", env="LLM_PROVIDER")  # local | openai | anthropic

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="ALLOWED_ORIGINS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

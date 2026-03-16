"""Application configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ResumeGPT"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "resume_gpt"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    JWT_SECRET_KEY: str = "resume-gpt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    CHAT_API_KEY: str | None = Field(default=None, validation_alias="CHAT_API_KEY")

    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"
    RESUME_UPLOAD_DIR: Path = UPLOAD_DIR / "resumes"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_RESUME_EXTENSIONS: set[str] = {
        ".pdf",
        ".docx",
        ".doc",
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
    }

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = {"env_prefix": "RESUME_GPT_", "env_file": ".env"}


settings = Settings()
settings.RESUME_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

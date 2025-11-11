from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Backend"
    DEBUG: bool = True
    # DATABASE_URL: str = "sqlite:///./app.db"
    # SECRET_KEY: str = "your-secret-key-change-this"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

settings = Settings()


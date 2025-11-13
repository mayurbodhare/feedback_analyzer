from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Backend"
    DEBUG: bool = True
    # DATABASE_URL: str
    BREVO_API_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    SENDER_EMAIL: str

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

settings = Settings()


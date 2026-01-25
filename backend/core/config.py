import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)
BACKEND_DIR = BASE_DIR / "backend"
# Base directory of the project
TEMPLATES_DIR = BACKEND_DIR / "templates"
STATIC_DIR = BACKEND_DIR / "public"


class Settings:
    URL: str = os.getenv("URL")
    PROJECT_NAME: str = "Over-Bet Cash Game Tracker"
    PROJECT_VERSION: str = "0.1.0"

    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", 5435)
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "tdd")
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 600  # 10h

    TEST_USER_EMAIL = "test@example.com"
    TEST_USER_PASSWORD = "test_password"
    RESEND_API_KEY = os.getenv("MAIL_PASSWORD")

    PASSWORD_LENGTH = 4
    NICK_LENGTH = 1


settings = Settings()

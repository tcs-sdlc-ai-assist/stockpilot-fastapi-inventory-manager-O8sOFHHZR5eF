import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-super-secret-key")

DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")

DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin1234")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./tmp/stockpilot.db")

SESSION_COOKIE_NAME: str = "stockpilot_session"

SESSION_MAX_AGE: int = int(os.getenv("SESSION_MAX_AGE", "86400"))
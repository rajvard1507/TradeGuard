import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing from .env")
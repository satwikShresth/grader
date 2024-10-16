from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UNZIP_DIR = BASE_DIR.parent / "unzipped"
TEMPLATES = BASE_DIR / "templates"
STATIC = BASE_DIR / "static"
UPLOAD_DIR.mkdir(exist_ok=True)
UNZIP_DIR.mkdir(exist_ok=True)

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "app")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{
    POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UNZIP_DIR = BASE_DIR.parent / "unzipped"
TEMPLATES = BASE_DIR / "templates"
STATIC = BASE_DIR / "static"
UPLOAD_DIR.mkdir(exist_ok=True)
UNZIP_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{BASE_DIR.parent}/database/students.db"

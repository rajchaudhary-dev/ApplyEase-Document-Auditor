import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage Bucket Directory
BUCKET_DIR = Path(os.getenv("BUCKET_STORAGE_DIR", BASE_DIR / "storage_bucket"))
BUCKET_DIR.mkdir(parents=True, exist_ok=True)

# Database File Path
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "applyease_dossier.db"))

# Gemini API Model Configuration
# Use gemini-3.8-flash for multimodal extraction & auditing
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Asset Constraints (Default portal thresholds)
PHOTO_CONSTRAINTS = {
    "min_kb": int(os.getenv("MIN_PHOTO_SIZE_KB", 20)),
    "max_kb": int(os.getenv("MAX_PHOTO_SIZE_KB", 50)),
    "width": 200,
    "height": 230,
    "format": "JPEG"
}

SIGNATURE_CONSTRAINTS = {
    "min_kb": int(os.getenv("MIN_SIG_SIZE_KB", 10)),
    "max_kb": int(os.getenv("MAX_SIG_SIZE_KB", 20)),
    "width": 140,
    "height": 60,
    "format": "JPEG"
}

DOCUMENT_CONSTRAINTS = {
    "max_kb": 300,
    "format": "JPEG"
}

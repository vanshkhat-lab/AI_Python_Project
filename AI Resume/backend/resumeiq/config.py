from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 100_000
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES * 2 + MAX_TEXT_LENGTH + 256 * 1024
MAX_PDF_PAGES = 200
MIN_EXTRACTED_TEXT_LENGTH = 20
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(ROOT / 'backend' / 'resumeiq' / 'resumeiq.sqlite3').as_posix()}",
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

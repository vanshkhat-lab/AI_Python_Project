from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 100_000
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES * 2 + MAX_TEXT_LENGTH + 256 * 1024
MAX_PDF_PAGES = 200
MIN_EXTRACTED_TEXT_LENGTH = 20


def _split_list_env(name: str, default: str | list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        values = default if isinstance(default, list) else [default]
    else:
        values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values


FRONTEND_ORIGINS = _split_list_env("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_ORIGIN = FRONTEND_ORIGINS[0]
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(ROOT / 'backend' / 'resumeiq' / 'resumeiq.sqlite3').as_posix()}",
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

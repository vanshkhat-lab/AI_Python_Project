from __future__ import annotations

import re
import unicodedata
from typing import TypedDict

import pymupdf

from backend.resumeiq.config import MAX_PDF_PAGES, MIN_EXTRACTED_TEXT_LENGTH
from resume_analyzer.documents import DocumentError

SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx"}
SUPPORTED_JOB_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ExtractionMetadata(TypedDict):
    character_count: int
    page_count: int | None
    warnings: list[str]


def _normalize_text(text: str) -> str:
    text = "".join(
        char for char in text
        if char in "\n\r\t" or not unicodedata.category(char).startswith("C")
    )
    return re.sub(r"[ \t]+", " ", text).strip()


def _extract_pdf(content: bytes) -> tuple[str, list[str], int]:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentError("Password-protected PDF files are not supported.")
            if document.page_count > MAX_PDF_PAGES:
                raise DocumentError(
                    f"This PDF has more than {MAX_PDF_PAGES} pages and cannot be processed."
                )
            pages_with_text = [
                (page.get_text("text"), bool(page.get_images()))
                for page in document
            ]
            page_text = [text for text, _has_images in pages_with_text]
            may_be_scanned = any(
                not text.strip() and has_images
                for text, has_images in pages_with_text
            )
            text = "\n".join(page_text)
            pages = document.page_count
    except DocumentError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as error:
        raise DocumentError(
            "The document could not be opened. Please upload another copy."
        ) from error

    warnings: list[str] = []
    if len(text.strip()) < MIN_EXTRACTED_TEXT_LENGTH:
        if may_be_scanned:
            raise DocumentError("This PDF may be scanned. OCR is not enabled.")
        raise DocumentError(
            "We could not extract enough readable text from this PDF."
        )
    if may_be_scanned:
        warnings.append(
            "One or more image-only pages may be scanned; OCR is not enabled."
        )
    return _normalize_text(text), warnings, pages


def extract_upload(content: bytes, filename: str, allowed: set[str]) -> str:
    text, _metadata = extract_upload_with_metadata(content, filename, allowed)
    return text


def extract_upload_with_metadata(
    content: bytes, filename: str, allowed: set[str]
) -> tuple[str, ExtractionMetadata]:
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise DocumentError(
            f"Unsupported file type {extension or '(none)'!r}. "
            f"Allowed types: {allowed_text}."
        )
    if not content:
        raise DocumentError("The document appears to be empty.")
    if extension == ".pdf":
        text, warnings, page_count = _extract_pdf(content)
    else:
        from io import BytesIO

        from resume_analyzer.documents import extract_text as legacy_extract_text

        try:
            extracted = legacy_extract_text(BytesIO(content), extension)
        except DocumentError as error:
            if "Scanned/image-only PDFs" in str(error):
                raise DocumentError("The document appears to be empty.") from error
            raise
        text = _normalize_text(extracted)
        warnings = []
        page_count = None

    if len(text) < MIN_EXTRACTED_TEXT_LENGTH:
        raise DocumentError("The document contains too little readable text.")
    return text, {
        "character_count": len(text),
        "page_count": page_count,
        "warnings": warnings,
    }

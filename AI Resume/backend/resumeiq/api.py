from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timezone

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.resumeiq.config import (
    FRONTEND_ORIGIN,
    MAX_REQUEST_BYTES,
    MAX_TEXT_LENGTH,
    MAX_UPLOAD_BYTES,
)
from backend.resumeiq.db import create_tables, get_db
from backend.resumeiq.models import AnalysisRecord, ClientFeedbackRecord
from backend.resumeiq.schemas import (
    AnalysisReport,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    JobDescriptionRequest,
    JobDescriptionResponse,
    TextAnalysisRequest,
)
from backend.resumeiq.services.ai import get_recommendations, recommendations_configured
from backend.resumeiq.services.analysis import analyze_resume
from backend.resumeiq.services.documents import (
    SUPPORTED_JOB_EXTENSIONS,
    SUPPORTED_RESUME_EXTENSIONS,
    DocumentError,
    ExtractionMetadata,
    extract_upload_with_metadata,
)
from backend.resumeiq.services.job_parser import parse_job_description
from backend.resumeiq.services.reports import make_pdf_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    yield


app = FastAPI(
    title="ResumeIQ API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def reject_oversized_requests(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return _error_response(
                    413, "request_too_large", "The request exceeds the allowed size."
                )
        except ValueError:
            return _error_response(400, "invalid_content_length", "Invalid content length.")
    return await call_next(request)


def _error_response(status: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, error: RequestValidationError):
    return _error_response(
        422, "validation_error", "The request is invalid or missing required fields."
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, error: StarletteHTTPException):
    code = {
        404: "not_found",
        415: "unsupported_media_type",
        413: "request_too_large",
        422: "validation_error",
    }.get(error.status_code, "request_error")
    detail = (
        error.detail
        if isinstance(error.detail, str)
        else "The request could not be completed."
    )
    return _error_response(error.status_code, code, detail)


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, error: Exception):
    logger.error("Unhandled ResumeIQ API error (type: %s).", type(error).__name__)
    return _error_response(500, "internal_error", "The server could not complete the request.")


async def _read_upload(
    upload: UploadFile, allowed: set[str]
) -> tuple[str, ExtractionMetadata]:
    filename = upload.filename or ""
    if not filename:
        await upload.close()
        raise HTTPException(status_code=400, detail="The uploaded file has no filename.")
    try:
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Each uploaded file must be 5 MB or smaller.",
            )
        text, metadata = await asyncio.to_thread(
            extract_upload_with_metadata, content, filename, allowed
        )
    except DocumentError as error:
        status = 415 if str(error).startswith("Unsupported file type") else 400
        raise HTTPException(status_code=status, detail=str(error)) from error
    finally:
        await upload.close()
    return text, metadata


async def _resume_text(resume_file: UploadFile) -> tuple[str, ExtractionMetadata]:
    text, metadata = await _read_upload(resume_file, SUPPORTED_RESUME_EXTENSIONS)
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="Extracted resume text exceeds the 100,000 character limit.",
        )
    return text, metadata


async def _job_text(job_file: UploadFile) -> tuple[str, ExtractionMetadata]:
    text, metadata = await _read_upload(job_file, SUPPORTED_JOB_EXTENSIONS)
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="Extracted job text exceeds the 100,000 character limit.",
        )
    return text, metadata


def _make_report(
    resume_text: str,
    job_description: str,
    generate_ai: bool = False,
    extraction_warnings: list[str] | None = None,
) -> AnalysisReport:
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="The job description cannot be empty.")
    if len(job_description) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="Job description exceeds the 100,000 character limit.",
        )
    data = analyze_resume(resume_text, job_description)
    if extraction_warnings:
        data["warnings"] = list(dict.fromkeys(data["warnings"] + extraction_warnings))
    suggestions, ai_status = (
        get_recommendations(resume_text, data)
        if generate_ai
        else ([], "not_configured" if not recommendations_configured() else "not_requested")
    )
    data["ai_recommendations"] = suggestions
    data["ai_status"] = ai_status
    if ai_status == "unavailable":
        data["warnings"].append(
            "Optional AI recommendations are unavailable; deterministic analysis is unaffected."
        )
    if suggestions:
        data["plain_text"] += "\nOPTIONAL AI WORDING SUGGESTIONS\n"
        data["plain_text"] += "".join(
            f"- {suggestion['suggestion']} "
            f"(evidence: {suggestion['evidence_quote']})\n"
            for suggestion in suggestions
        )
    return AnalysisReport.model_validate(data)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", version=app.version, ai_recommendations=recommendations_configured()
    )


@router.get("/feedback", response_model=list[FeedbackResponse])
def list_feedback(db: Session = Depends(get_db)) -> list[FeedbackResponse]:
    records = db.scalars(
        select(ClientFeedbackRecord)
        .order_by(ClientFeedbackRecord.created_at.desc(), ClientFeedbackRecord.id.desc())
        .limit(50)
    ).all()
    return [
        FeedbackResponse(
            feedback_id=record.id,
            message=record.message,
            created_at=record.created_at,
        )
        for record in records
    ]


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    body: FeedbackRequest, db: Session = Depends(get_db)
) -> FeedbackResponse:
    record = ClientFeedbackRecord(message=body.message)
    db.add(record)
    db.commit()
    db.refresh(record)
    return FeedbackResponse(
        feedback_id=record.id,
        message=record.message,
        created_at=record.created_at,
    )


@router.post("/extract/resume")
@router.post("/resumes/extract")
async def extract_resume(resume_file: UploadFile):
    text, metadata = await _resume_text(resume_file)
    return {
        "filename": resume_file.filename,
        "text": text,
        "metadata": metadata,
        "warnings": metadata["warnings"],
    }


@router.post("/extract/job-description")
async def extract_job_description(job_file: UploadFile):
    text, metadata = await _job_text(job_file)
    return {"filename": job_file.filename, "text": text, "metadata": metadata}


@router.post(
    "/job-descriptions/extract", response_model=JobDescriptionResponse
)
def extract_job_description_text(body: JobDescriptionRequest):
    return parse_job_description(body.text)


def _persist_report(report: AnalysisReport, db: Session) -> AnalysisReport:
    record = AnalysisRecord(report=report.model_dump(exclude={"analysis_id", "created_at"}))
    db.add(record)
    db.commit()
    db.refresh(record)
    created_at = record.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return AnalysisReport.model_validate(
        {**record.report, "analysis_id": record.id, "created_at": created_at.isoformat()}
    )


@router.post("/analyze", response_model=AnalysisReport)
async def analyze(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            payload = TextAnalysisRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as error:
            raise HTTPException(
                status_code=422, detail="The analysis request is invalid."
            ) from error
        report = await asyncio.to_thread(
            _make_report,
            payload.resume_text,
            payload.job_description,
            payload.generate_ai_recommendations,
        )
        return _persist_report(report, db) if payload.save_analysis else report

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        resume_file = form.get("resume_file")
        if not isinstance(resume_file, StarletteUploadFile):
            raise HTTPException(status_code=422, detail="A resume file is required.")
        job_description = str(form.get("job_description", ""))
        job_file = form.get("job_file")
        resume_text, resume_metadata = await _resume_text(resume_file)
        extraction_warnings = list(resume_metadata["warnings"])
        if isinstance(job_file, StarletteUploadFile) and job_file.filename:
            job_description, job_metadata = await _job_text(job_file)
            extraction_warnings.extend(job_metadata["warnings"])
        if len(job_description) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=413,
                detail="Job description exceeds the 100,000 character limit.",
            )
        generate_ai = str(form.get("generate_ai_recommendations", "false")).lower() == "true"
        save_analysis = str(form.get("save_analysis", "false")).lower() == "true"
        report = await asyncio.to_thread(
            _make_report,
            resume_text,
            job_description,
            generate_ai,
            extraction_warnings,
        )
        return _persist_report(report, db) if save_analysis else report

    raise HTTPException(
        status_code=415,
        detail="Use a JSON or multipart/form-data request for analysis.",
    )


@router.post("/analyze/text", response_model=AnalysisReport)
def analyze_text(body: TextAnalysisRequest, db: Session = Depends(get_db)):
    report = _make_report(
        body.resume_text,
        body.job_description,
        body.generate_ai_recommendations,
    )
    return _persist_report(report, db) if body.save_analysis else report


@router.get("/analyses")
def list_analyses(db: Session = Depends(get_db)):
    records = db.scalars(select(AnalysisRecord).order_by(AnalysisRecord.created_at.desc())).all()
    return [
        {
            "analysis_id": record.id,
            "created_at": record.created_at.isoformat(),
            "score": record.report["score"],
            "job_title": record.report.get("job_title"),
        }
        for record in records
    ]


def _get_analysis(analysis_id: str, db: Session) -> AnalysisRecord:
    record = db.get(AnalysisRecord, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis history item not found.")
    return record


@router.get("/analyses/{analysis_id}", response_model=AnalysisReport)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    record = _get_analysis(analysis_id, db)
    created_at = record.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return AnalysisReport.model_validate(
        {**record.report, "analysis_id": record.id, "created_at": created_at.isoformat()}
    )


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    record = _get_analysis(analysis_id, db)
    db.delete(record)
    db.commit()
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}/report")
def download_analysis_report(analysis_id: str, db: Session = Depends(get_db)):
    record = _get_analysis(analysis_id, db)
    return Response(
        content=make_pdf_report(record.report),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="resumeiq-{analysis_id}.pdf"'
        },
    )


app.include_router(router)

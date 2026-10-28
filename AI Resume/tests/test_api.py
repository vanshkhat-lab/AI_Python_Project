from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from typing import Any, Mapping

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.resumeiq.api import app
from backend.resumeiq.db import Base, get_db


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_docx_bytes() -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph("Python developer with 4 years of experience.")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def text_analysis_payload() -> dict[str, str]:
    return {
        "resume_text": "Python developer with 4 years of experience.",
        "job_description": "Python developer with 3 years of experience.",
    }


def test_health_endpoint_and_ai_status(client: TestClient):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "1.0.0"
    assert "ai_recommendations" in response.json()


def test_client_feedback_is_saved_and_returned_to_future_visitors(client: TestClient):
    submitted = client.post(
        "/api/feedback",
        json={"message": "The experience section is helpful."},
    )

    assert submitted.status_code == 201
    saved = submitted.json()
    assert saved["message"] == "The experience section is helpful."
    assert saved["feedback_id"]
    assert saved["created_at"]
    assert client.get("/api/feedback").json() == [saved]


def test_client_feedback_rejects_blank_and_oversized_messages(client: TestClient):
    blank = client.post("/api/feedback", json={"message": "   "})
    oversized = client.post("/api/feedback", json={"message": "x" * 1001})

    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "validation_error"
    assert client.get("/api/feedback").json() == []


def test_resume_extraction_uses_pymupdf_and_returns_metadata(client: TestClient):
    from reportlab.pdfgen.canvas import Canvas

    buffer = BytesIO()
    pdf = Canvas(buffer)
    pdf.drawString(72, 720, "Senior Python engineer with extensive project experience.")
    pdf.save()

    response = client.post(
        "/api/resumes/extract",
        files={"resume_file": ("resume.pdf", buffer.getvalue(), "application/pdf")},
    )

    assert response.status_code == 200
    assert "Senior Python engineer" in response.json()["text"]
    assert response.json()["metadata"]["page_count"] == 1
    assert response.json()["metadata"]["character_count"] > 20
    assert response.json()["warnings"] == []


def test_job_description_parser_returns_requirements_and_responsibilities(
    client: TestClient,
):
    response = client.post(
        "/api/job-descriptions/extract",
        json={
            "text": (
                "Senior Data Analyst\n"
                "Required: Python, SQL, and 3 years of experience.\n"
                "Preferred: Tableau.\n"
                "Responsibilities:\n"
                "- Build reports and explain findings to stakeholders."
            )
        },
    )

    assert response.status_code == 200
    parsed = response.json()
    assert parsed["job_title"] == "Senior Data Analyst"
    assert {
        "name": "Python",
        "category": "skill",
        "priority": "required",
    } in parsed["requirements"]
    assert {
        "name": "Tableau",
        "category": "skill",
        "priority": "preferred",
    } in parsed["requirements"]
    assert parsed["requirements"][-1]["category"] == "experience"
    assert "Build reports" in parsed["responsibilities"][0]


def test_job_description_parser_rejects_empty_input_and_warns_for_short_text(
    client: TestClient,
):
    empty = client.post("/api/job-descriptions/extract", json={"text": "   "})
    short = client.post(
        "/api/job-descriptions/extract",
        json={"text": "A curious and thoughtful person."},
    )

    assert empty.status_code == 422
    assert short.status_code == 200
    assert "unusually short" in " ".join(short.json()["warnings"]).lower()
    assert "reliable skills" in " ".join(short.json()["warnings"]).lower()


def test_json_analysis_saves_only_when_requested(client: TestClient):
    payload = {
        "resume_text": "EXPERIENCE\nBuilt Python services for customers.",
        "job_description": "Python developer required.",
    }
    transient = client.post("/api/analyze", json=payload)
    saved = client.post("/api/analyze", json={**payload, "save_analysis": True})

    assert transient.status_code == 200
    assert transient.json()["analysis_id"] is None
    assert saved.status_code == 200
    assert saved.json()["analysis_id"]
    assert client.get("/api/analyses").json()[0]["analysis_id"] == saved.json()["analysis_id"]


def test_core_analysis_survives_optional_ai_provider_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def unavailable_recommendations(
        _resume: str, _report: Mapping[str, Any]
    ) -> tuple[list[dict[str, object]], str]:
        return [], "unavailable"

    monkeypatch.setenv("OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(
        "backend.resumeiq.api.get_recommendations",
        unavailable_recommendations,
    )

    response = client.post(
        "/api/analyze",
        json={
            **text_analysis_payload(),
            "generate_ai_recommendations": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == 50
    assert response.json()["ai_status"] == "unavailable"
    assert any(
        "AI recommendations are unavailable" in warning
        for warning in response.json()["warnings"]
    )


def test_text_analysis_returns_typed_report(client: TestClient):
    response = client.post("/api/analyze/text", json=text_analysis_payload())

    assert response.status_code == 200
    assert response.json()["matched_skills"] == []
    assert response.json()["uncertain_skills"] == ["Python"]
    assert response.json()["score"] == 50


def test_missing_and_malformed_analysis_fields_return_json_error(client: TestClient):
    response = client.post("/api/analyze/text", json={"resume_text": "Python"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_analyze_upload_extracts_docx_and_reports_unsupported_types(client: TestClient):
    success = client.post(
        "/api/analyze",
        data={"job_description": "Python developer with 3 years of experience."},
        files={
            "resume_file": (
                "resume.docx",
                make_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    unsupported = client.post(
        "/api/analyze",
        data={"job_description": "Python"},
        files={"resume_file": ("resume.rtf", b"bad")},
    )

    assert success.status_code == 200
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_media_type"


def test_resume_extraction_endpoint_and_size_limit(client: TestClient):
    extracted = client.post(
        "/api/resumes/extract",
        files={"resume_file": ("resume.docx", make_docx_bytes())},
    )
    oversized = client.post(
        "/api/resumes/extract",
        files={"resume_file": ("resume.pdf", b"x" * (5 * 1024 * 1024 + 1))},
    )

    assert extracted.status_code == 200
    assert "Python developer" in extracted.json()["text"]
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "request_too_large"


def test_upload_errors_are_consistent_json(client: TestClient):
    response = client.post(
        "/api/extract/resume",
        files={"resume_file": ("resume.pdf", b"not a pdf")},
    )

    assert response.status_code == 400
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message"}


def test_empty_job_description_returns_json_error(client: TestClient):
    response = client.post(
        "/api/analyze",
        data={"job_description": "   "},
        files={"resume_file": ("resume.docx", make_docx_bytes())},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_no_detected_requirements_does_not_claim_a_match(client: TestClient):
    response = client.post(
        "/api/analyze/text",
        json={
            "resume_text": "I enjoy solving challenging problems.",
            "job_description": "We are seeking a curious and thoughtful person.",
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] is None
    assert response.json()["criteria"] == []
    assert "no meaningful score" in response.json()["plain_text"].lower()


def test_cors_allows_only_configured_local_frontend_origin(client: TestClient):
    allowed = client.get(
        "/api/health", headers={"Origin": "http://localhost:5173"}
    )
    denied = client.get(
        "/api/health", headers={"Origin": "http://example.com"}
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_history_save_read_pdf_delete_and_unknown_id(client: TestClient):
    saved = client.post(
        "/api/analyze",
        json={**text_analysis_payload(), "save_analysis": True},
    )
    analysis_id = saved.json()["analysis_id"]
    loaded = client.get(f"/api/analyses/{analysis_id}")
    pdf = client.get(f"/api/analyses/{analysis_id}/report")
    listing = client.get("/api/analyses")
    removed = client.delete(f"/api/analyses/{analysis_id}")
    unknown = client.get("/api/analyses/unknown")

    assert saved.status_code == 200
    assert loaded.status_code == 200
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"
    assert listing.json()[0]["analysis_id"] == analysis_id
    assert removed.status_code == 204
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"
    assert client.get(f"/api/analyses/{analysis_id}/report").status_code == 404
    assert client.delete(f"/api/analyses/{analysis_id}").status_code == 404

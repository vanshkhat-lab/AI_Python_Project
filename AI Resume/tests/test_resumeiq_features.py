from __future__ import annotations

from io import BytesIO

from PIL import Image

from backend.resumeiq.config import MAX_PDF_PAGES
from backend.resumeiq.schemas import AnalysisReport
from backend.resumeiq.services.analysis import analyze_resume
from backend.resumeiq.services.documents import (
    DocumentError,
    _normalize_text,
    extract_upload_with_metadata,
)
from backend.resumeiq.services.job_parser import parse_job_description
from resume_analyzer.documents import DocumentError as LegacyDocumentError


def test_required_and_preferred_weights_follow_documented_formula():
    report = analyze_resume(
        "Built Python services.",
        "Python is required. Docker is preferred.",
    )

    assert report["score"] == 67
    assert [criterion["weight"] for criterion in report["criteria"]] == [2, 1]
    assert report["requirements"][1]["priority"] == "preferred"


def test_partial_and_uncertain_credit_and_no_requirement_score():
    partial = analyze_resume("Currently learning Python.", "Python is required.")
    uncertain = analyze_resume("SKILLS\nPython", "Python is required.")
    no_requirements = analyze_resume("Resume content is readable.", "A motivated person.")

    assert partial["score"] == 50
    assert uncertain["score"] == 0
    assert uncertain["requirements"][0]["status"] == "uncertain"
    assert no_requirements["score"] is None
    assert no_requirements["criteria"] == []


def test_explicitly_nonrequired_mention_is_not_scored_and_score_is_deterministic():
    optional = analyze_resume(
        "Built Python services.",
        "Python is not required for this role.",
    )
    first = analyze_resume("Built Python services.", "Python is required.")
    second = analyze_resume("Built Python services.", "Python is required.")

    assert optional["requirements"] == []
    assert optional["score"] is None
    assert first["score"] == second["score"] == 100


def test_nonrequired_skill_is_not_reintroduced_by_a_neutral_mention():
    parsed = parse_job_description(
        "Java is not required. The team currently uses Java for a legacy service."
    )

    assert all(item["name"] != "Java" for item in parsed["requirements"])


def test_legacy_saved_reports_receive_conservative_evidence_defaults():
    payload = analyze_resume("EXPERIENCE\nBuilt Python services.", "Python is required.")
    for requirement in payload["requirements"]:
        requirement.pop("reason")
        requirement.pop("confidence")
    payload["ai_recommendations"] = [
        {
            "suggestion": "Emphasize the existing Python services.",
            "evidence_quote": "Built Python services.",
        }
    ]

    report = AnalysisReport.model_validate(payload)

    assert report.requirements[0].confidence == "low"
    assert report.ai_recommendations[0].introduces_new_claim is None


def test_aliases_cover_postgres_javascript_typescript_and_sklearn():
    report = analyze_resume(
        "Built systems with Postgres, JS, TS, and sklearn.",
        "PostgreSQL, JavaScript, TypeScript, and scikit-learn are required.",
    )

    assert report["matched_skills"] == [
        "JavaScript",
        "TypeScript",
        "PostgreSQL",
        "Scikit-learn",
    ]


def test_preferred_experience_is_parsed_and_weighted_as_preferred():
    report = analyze_resume(
        "Software developer with 2 years of experience.",
        "Python is required. 3 years of experience is preferred.",
    )

    experience = next(item for item in report["requirements"] if item["category"] == "experience")
    assert experience["priority"] == "preferred"
    assert experience["status"] == "partially_supported"


def test_experience_summary_includes_preferred_years_without_claiming_required():
    report = analyze_resume(
        "Software developer with 2 years of experience.",
        "Software developer. 3 years of experience is preferred.",
    )

    assert report["experience"]["required_years"] is None
    assert "3 years of experience as preferred" in report["experience"]["summary"]
    assert "resume explicitly states 2 years" in report["experience"]["summary"]
    assert any(
        item["category"] == "experience" and item["priority"] == "preferred"
        for item in report["requirements"]
    )


def test_inline_experience_heading_with_years_and_skill_is_parsed():
    job_description = "Experience Required :Tableau: 8 years (Required)"

    parsed = parse_job_description(job_description)
    report = analyze_resume("Tableau analyst with 6 years of experience.", job_description)
    experience = next(
        item for item in report["requirements"] if item["category"] == "experience"
    )

    assert {
        "name": "8 years of experience",
        "category": "experience",
        "priority": "required",
    } in parsed["requirements"]
    assert experience["priority"] == "required"
    assert experience["status"] == "partially_supported"
    assert report["experience"]["required_years"] == 8
    assert "asks for 8 years" in report["experience"]["summary"]


def test_experience_section_parses_years_on_following_requirement_line():
    parsed = parse_job_description(
        "Experience Required:\nTableau: 8 years (Required)\nSkills:\nPython"
    )

    assert {
        "name": "8 years of experience",
        "category": "experience",
        "priority": "required",
    } in parsed["requirements"]


def test_corrupt_pdf_and_scanned_pdf_have_controlled_messages():
    try:
        extract_upload_with_metadata(b"not a PDF", "resume.pdf", {".pdf"})
    except DocumentError as error:
        assert "could not be opened" in str(error).lower()
    else:
        raise AssertionError("A corrupt PDF was accepted.")

    image_stream = BytesIO()
    Image.new("RGB", (20, 20), color="white").save(image_stream, format="PNG")
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(page.rect, stream=image_stream.getvalue())
    scanned_pdf = document.tobytes()
    document.close()

    try:
        extract_upload_with_metadata(scanned_pdf, "scanned.pdf", {".pdf"})
    except DocumentError as error:
        assert "scanned" in str(error).lower()
        assert "ocr is not enabled" in str(error).lower()
    else:
        raise AssertionError("An image-only scanned PDF was accepted.")


def test_pdf_page_limit_and_text_normalization():
    import pymupdf

    document = pymupdf.open()
    for _ in range(MAX_PDF_PAGES + 1):
        document.new_page()
    oversized_page_pdf = document.tobytes()
    document.close()

    try:
        extract_upload_with_metadata(oversized_page_pdf, "pages.pdf", {".pdf"})
    except DocumentError as error:
        assert "page" in str(error).lower()
    else:
        raise AssertionError("A PDF over the page limit was accepted.")

    assert _normalize_text("  Python\x00\t services \n") == "Python services"


def test_password_protected_pdf_is_rejected():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("test-password")
    buffer = BytesIO()
    writer.write(buffer)

    try:
        extract_upload_with_metadata(buffer.getvalue(), "locked.pdf", {".pdf"})
    except DocumentError as error:
        assert "password-protected" in str(error).lower()
    else:
        raise AssertionError("A password-protected PDF was accepted.")


def test_docx_extension_cannot_hide_invalid_content():
    try:
        extract_upload_with_metadata(b"not a DOCX", "resume.docx", {".docx"})
    except LegacyDocumentError as error:
        assert "could not be read" in str(error).lower()
    else:
        raise AssertionError("Invalid DOCX content was accepted.")

from __future__ import annotations

from io import BytesIO
from typing import Protocol, cast

from PIL import Image

from backend.resumeiq.config import MAX_PDF_PAGES
from backend.resumeiq.schemas import AnalysisReport
from backend.resumeiq.services.analysis import analyze_resume
from backend.resumeiq.services.documents import (
    DocumentError,
    extract_upload_with_metadata,
)
from backend.resumeiq.services.job_parser import parse_job_description
from resume_analyzer.documents import DocumentError as LegacyDocumentError


class _PdfCanvas(Protocol):
    def drawImage(
        self, image: object, x: float, y: float, *, width: float, height: float
    ) -> object: ...

    def save(self) -> None: ...


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
    assert uncertain["score"] == 50
    assert uncertain["requirements"][0]["status"] == "partially_supported"
    assert uncertain["requirements"][0]["evidence_type"] == "explicitly_listed"
    assert no_requirements["score"] is None
    assert no_requirements["criteria"] == []


def test_keyword_mentions_without_usage_context_do_not_receive_full_credit():
    report = analyze_resume(
        "EXPERIENCE\nPython\nSQL\nAWS",
        "Python, SQL, and AWS are required.",
    )

    assert report["score"] == 0
    assert report["uncertain_skills"] == ["Python", "SQL", "AWS"]
    assert all(item["confidence"] == "low" for item in report["requirements"])


def test_skills_with_concrete_usage_context_still_receive_full_credit():
    report = analyze_resume(
        "EXPERIENCE\nBuilt internal tools in Python and SQL to automate monthly reporting.",
        "Python and SQL are required.",
    )

    assert report["score"] == 100
    assert report["matched_skills"] == ["Python", "SQL"]


def test_sql_dialects_are_recognized_as_sql_evidence():
    report = analyze_resume(
        "EXPERIENCE\nBuilt reporting tools using MySQL and SQLite.",
        "SQL is required.",
    )

    assert report["matched_skills"] == ["SQL"]
    assert report["requirements"][0]["evidence"] == (
        "Built reporting tools using MySQL and SQLite."
    )


def test_sql_dialect_in_skills_list_is_detected_without_overstating_evidence():
    report = analyze_resume("SKILLS\nMySQL", "SQL is required.")

    assert report["partial_skills"] == ["SQL"]
    assert report["missing_skills"] == []
    assert report["requirements"][0]["evidence_type"] == "explicitly_listed"


def test_exact_html_css_and_sql_in_technical_skills_receive_partial_credit():
    report = analyze_resume(
        "Technical Skills: Python, React.js, HTML, CSS, SQL",
        "Required Skills: HTML, CSS, SQL",
    )

    requirements = {item["name"]: item for item in report["requirements"]}
    assert set(requirements) == {"HTML", "CSS", "SQL"}
    assert all(item["evidence_type"] == "explicitly_listed" for item in requirements.values())
    assert all(item["status"] == "partially_supported" for item in requirements.values())
    assert all("Technical Skills:" in item["evidence"] for item in requirements.values())
    assert report["partial_skills"] == ["SQL", "HTML", "CSS"]
    assert report["uncertain_skills"] == []
    assert report["criteria"][0]["coverage"] == 0.5
    assert report["score"] == 50
    assert "evidence type: explicitly listed" in report["plain_text"]


def test_skill_matching_is_case_insensitive_in_skills_sections():
    report = analyze_resume(
        "Technical Skills: html, css",
        "Required Skills: HTML, CSS",
    )

    assert report["partial_skills"] == ["HTML", "CSS"]
    assert all(
        item["evidence_type"] == "explicitly_listed"
        for item in report["requirements"]
    )


def test_bullet_separated_skill_list_supports_exact_skills():
    report = analyze_resume(
        "Technical Skills:\n- Python\n- React.js\n- HTML\n- CSS",
        "Required Skills: HTML, CSS",
    )

    assert report["partial_skills"] == ["HTML", "CSS"]
    assert report["missing_skills"] == []
    assert all(
        item["evidence_type"] == "explicitly_listed"
        for item in report["requirements"]
    )


def test_listed_skill_does_not_prove_advanced_proficiency_or_years():
    report = analyze_resume(
        "Technical Skills: HTML, CSS",
        "Required Skills: Advanced HTML proficiency and 3 years of professional experience.",
    )

    html = next(item for item in report["requirements"] if item["name"] == "HTML")
    experience = next(item for item in report["requirements"] if item["category"] == "experience")
    assert html["evidence_type"] == "explicitly_listed"
    assert html["status"] == "partially_supported"
    assert "does not establish proficiency" in html["reason"]
    assert experience["status"] == "uncertain"
    assert report["score"] < 100


def test_missing_html_receives_no_credit_when_not_listed():
    report = analyze_resume(
        "Technical Skills: Python, SQL, MongoDB",
        "Required Skills: HTML",
    )

    assert report["missing_skills"] == ["HTML"]
    assert report["requirements"][0]["evidence_type"] == "missing"
    assert report["score"] == 0


def test_substrings_in_unrelated_words_do_not_match_html_or_css():
    report = analyze_resume(
        "Experience with htmlize tooling and the SCSS preprocessor.",
        "Required Skills: HTML, CSS",
    )

    assert report["missing_skills"] == ["HTML", "CSS"]
    assert report["score"] == 0


def test_project_action_evidence_is_demonstrated_for_html_and_css():
    report = analyze_resume(
        "Project: Developed responsive web pages using HTML and CSS.",
        "Required Skills: HTML, CSS",
    )

    assert report["matched_skills"] == ["HTML", "CSS"]
    assert all(
        item["evidence_type"] == "demonstrated"
        for item in report["requirements"]
    )


def test_skills_heading_alone_does_not_support_any_requirement():
    report = analyze_resume(
        "Skills",
        "Required Skills: HTML, CSS",
    )

    assert report["missing_skills"] == ["HTML", "CSS"]
    assert report["score"] == 0


def test_skill_aliases_and_extended_skills_headings_are_normalized():
    report = analyze_resume(
        "Programming Languages: ReactJS, NodeJS, HTML5, CSS3, .NET",
        "Required Skills: React.js, Node.js, HTML, CSS, .NET",
    )

    assert set(report["partial_skills"]) == {"React", "Node.js", "HTML", "CSS", ".NET"}
    assert all(
        item["evidence_type"] == "explicitly_listed"
        for item in report["requirements"]
    )
    assert "JavaScript" not in report["required_skills"]


def test_usage_of_one_skill_does_not_support_other_skills_after_semicolon():
    report = analyze_resume(
        "EXPERIENCE\nDeveloped reports using Python; SQL and AWS were listed in my old coursework.",
        "Python, SQL, and AWS are required.",
    )

    assert report["score"] == 33
    assert report["matched_skills"] == ["Python"]
    assert report["uncertain_skills"] == ["SQL", "AWS"]


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


def test_degree_field_mismatch_is_detected_in_resumeiq_analysis():
    job_description = "Bachelor's degree in Mechanical Engineering is required."
    parsed = parse_job_description(job_description)
    report = analyze_resume(
        "EDUCATION\nBachelor's degree in Electronics Engineering",
        job_description,
    )

    assert {
        "name": "Bachelor's degree in Mechanical Engineering",
        "category": "qualification",
        "priority": "required",
    } in parsed["requirements"]
    assert report["score"] == 0
    assert report["missing_qualifications"] == ["Bachelor's degree in Mechanical Engineering"]


def test_abbreviated_degree_field_mismatch_is_detected_by_parser_and_analysis():
    job_description = "B.E. in Mechanical Engineering is required."
    parsed = parse_job_description(job_description)
    report = analyze_resume(
        "EDUCATION\nB.Tech (Electronics and Communication Engineering)",
        job_description,
    )

    assert {
        "name": "Bachelor's degree in Mechanical Engineering",
        "category": "qualification",
        "priority": "required",
    } in parsed["requirements"]
    assert report["score"] == 0
    assert report["missing_qualifications"] == ["Bachelor's degree in Mechanical Engineering"]


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
    experience = next(item for item in report["requirements"] if item["category"] == "experience")

    experience_requirement = next(
        item for item in parsed["requirements"] if item["category"] == "experience"
    )
    assert experience_requirement["name"] == "8 years of experience"
    assert experience_requirement["priority"] == "required"
    assert experience_requirement["minimum_years"] == 8
    assert experience_requirement["maximum_years"] == 8
    assert experience["priority"] == "required"
    assert experience["status"] == "partially_supported"
    assert report["experience"]["required_years"] == 8
    assert "asks for at least 8 years" in report["experience"]["summary"]


def test_experience_section_parses_years_on_following_requirement_line():
    parsed = parse_job_description(
        "Experience Required:\nTableau: 8 years (Required)\nSkills:\nPython"
    )

    experience_requirement = next(
        item for item in parsed["requirements"] if item["category"] == "experience"
    )
    assert experience_requirement["name"] == "8 years of experience"
    assert experience_requirement["priority"] == "required"


def test_job_parser_categorizes_sections_and_does_not_score_responsibilities():
    job_description = (
        "Junior .NET Developer\n"
        "Role overview\nBuild services for internal users.\n"
        "Responsibilities\n- Develop REST APIs and maintain SQL reports.\n"
        "Experience required\n0–2 years of experience.\n"
        "Required skills\nC#, SQL, Git.\n"
        "Preferred skills\nAzure.\n"
        "Required qualifications\nBachelor's degree in Computer Science.\n"
        "Preferred qualifications\nPMP certification.\n"
        "Optional requirements\nDocker.\n"
    )
    parsed = parse_job_description(job_description)
    parsed_by_name = {item["name"]: item for item in parsed["requirements"]}

    assert parsed_by_name["C#"]["priority"] == "required"
    assert parsed_by_name["Azure"]["priority"] == "preferred"
    assert parsed_by_name["Docker"]["priority"] == "optional"
    assert parsed_by_name["Bachelor's degree in Computer Science"]["priority"] == "required"
    assert parsed_by_name["PMP"]["priority"] == "preferred"
    assert parsed["responsibilities"] == ["Develop REST APIs and maintain SQL reports."]
    assert {
        "name": "Develop REST APIs and maintain SQL reports.",
        "category": "responsibility",
        "priority": "required",
    } in parsed["requirements"]

    report = analyze_resume("Built Python tools.", job_description)
    assert all(item["category"] != "responsibility" for item in report["requirements"])
    assert "REST API" not in report["matched_skills"]


def test_job_parser_reads_explicit_requirements_inside_role_overview_paragraphs():
    parsed = parse_job_description(
        "Junior Developer\n"
        "Role overview\n"
        "Must have SQL experience and deliver reliable reporting.\n"
        "Experience required\n"
        "Between 0 and 2 years.\n"
        "Optional or desirable requirements\n"
        "Docker.\n"
    )

    requirements_by_name = {item["name"]: item for item in parsed["requirements"]}
    assert requirements_by_name["SQL"]["priority"] == "required"
    assert requirements_by_name["0-2 years of experience"].get("minimum_years") == 0
    assert requirements_by_name["0-2 years of experience"].get("maximum_years") == 2
    assert requirements_by_name["Docker"]["priority"] == "optional"


def test_experience_range_preserves_bounds_and_does_not_target_the_maximum():
    report = analyze_resume(
        "Projects\nBuilt a small web application.",
        "Experience required:\n0–2 years of relevant experience.",
    )

    requirement = next(item for item in report["requirements"] if item["category"] == "experience")
    assert requirement["name"] == "0-2 years of experience"
    assert requirement["minimum_years"] == 0
    assert requirement["maximum_years"] == 2
    assert "0–2 years" in requirement["original_text"]
    assert requirement["status"] == "not_applicable"
    assert report["experience"]["required_years"] == 0
    assert report["experience"]["required_max_years"] == 2
    assert report["score"] is None
    assert not any("claim 2 years" in item.lower() for item in report["improvements"])


def test_positive_experience_range_does_not_misstate_an_exact_requirement():
    ranged = analyze_resume(
        "EDUCATION\nCompleted a programming course.",
        "1–2 years of experience required.",
    )
    exact = analyze_resume(
        "EDUCATION\nCompleted a programming course.",
        "2 years of experience required.",
    )

    assert any(
        "maximum of 2 years is not a target to claim" in item for item in ranged["improvements"]
    )
    assert not any("listed maximum" in item for item in exact["improvements"])


def test_project_internship_and_training_durations_are_not_counted_as_professional_total():
    project_only = analyze_resume(
        "PROJECTS\nWorked on a personal project for 5 years.",
        "2 years of professional experience required.",
    )
    internship_only = analyze_resume(
        "INTERNSHIPS\nCompleted an internship with 2 years of experience.",
        "2 years of professional experience required.",
    )
    explicit_work = analyze_resume(
        "PROFESSIONAL EXPERIENCE\nSoftware developer with 1 year of experience.",
        "2 years of professional experience required.",
    )

    assert project_only["experience"]["candidate_years"] is None
    assert internship_only["experience"]["candidate_years"] is None
    assert explicit_work["experience"]["candidate_years"] == 1
    assert (
        next(item for item in explicit_work["requirements"] if item["category"] == "experience")[
            "status"
        ]
        == "partially_supported"
    )


def test_rest_api_and_postman_project_evidence_are_matched_independently():
    report = analyze_resume(
        "PROJECTS\nDeveloped REST API endpoints and used Postman to test requests.",
        "Required skills:\nREST API\nPostman",
    )

    assert report["matched_skills"] == ["REST API", "Postman"]
    assert all(item["status"] == "matched" for item in report["requirements"])


def test_github_keyword_does_not_prove_git_proficiency():
    report = analyze_resume(
        "PROJECTS\nPublished a portfolio on GitHub.",
        "Git is required.",
    )

    assert report["missing_skills"] == ["Git"]


def test_ai_agent_testing_does_not_prove_api_testing_or_postman():
    report = analyze_resume(
        "PROJECTS\nTested AI agents and evaluated their generated answers.",
        "Required skills:\nAPI Testing\nPostman",
    )

    assert report["missing_skills"] == ["API Testing", "Postman"]


def test_csharp_and_aspnet_core_project_evidence_matches():
    report = analyze_resume(
        "PROJECTS\nBuilt a task tracker using C# and ASP.NET Core.",
        "Required skills:\nC#\nASP.NET Core",
    )

    assert report["matched_skills"] == ["C#", "ASP.NET Core"]


def test_no_job_specific_skill_evidence_scores_zero():
    report = analyze_resume(
        "EDUCATION\nCompleted a general business program.",
        "Required skills:\nRust\nKubernetes",
    )

    assert report["missing_skills"] == ["Rust", "Kubernetes"]
    assert report["score"] == 0


def test_relevant_skill_and_education_matches_score_consistently():
    report = analyze_resume(
        "EDUCATION\nBachelor's degree in Computer Science.\n"
        "PROJECTS\nBuilt a service with Python and SQL.",
        "Required skills:\nPython\nSQL\n"
        "Required qualifications:\nBachelor's degree in Computer Science.",
    )

    assert report["score"] == 100
    assert round(sum(item["points"] for item in report["criteria"])) == 100


def test_malformed_objective_is_not_rewritten_or_treated_as_skill_evidence():
    resume = (
        "OBJECTIVE\nSeeking an Seeking career in AI,Fullstack developer,data analysts position."
    )
    report = analyze_resume(resume, "Required skills:\nPython\nData Analysis")

    assert report["requirements"][0]["status"] == "missing"
    assert report["requirements"][1]["status"] == "missing"
    assert report["relevant_experience"] == []


def test_long_evidence_excerpt_is_clear_when_source_text_continues():
    continuation = " and then documented the results for the project team."
    sentence = "Built a service with Python and SQL " + "x" * 360 + continuation
    report = analyze_resume(sentence, "Python is required.")

    evidence = report["requirements"][0]["evidence"]
    assert evidence is not None
    assert evidence.endswith("...")
    assert len(evidence) <= 350
    assert continuation in sentence


def test_wrapped_evidence_lines_are_joined_without_losing_source_context():
    resume = "EXPERIENCE\nExperienced in applying Excel, SQL,\nPostman, and REST APIs."
    report = analyze_resume(resume, "SQL is required.")

    evidence = report["requirements"][0]["evidence"]
    assert evidence == "Experienced in applying Excel, SQL, Postman, and REST APIs."
    assert report["relevant_experience"] == [evidence]


def test_evidence_keeps_original_date_and_context_punctuation():
    resume = (
        "PROJECTS\nAI Agent Testing & Evaluation "
        "(September 2026 \u2013 Present): Tested AI-powered applications."
    )
    report = analyze_resume(resume, "Testing is required.")

    assert "\u2013" in report["requirements"][0]["evidence"]
    assert "September 2026 \u2013 Present" in report["requirements"][0]["evidence"]


def test_career_interests_are_not_claimed_as_technical_skills():
    report = analyze_resume(
        "OBJECTIVE\nSeeking roles in Python, React, and SQL.",
        "Required skills:\nPython\nReact\nSQL",
    )

    assert set(report["uncertain_skills"]) == {"Python", "React", "SQL"}
    assert report["matched_skills"] == []
    assert report["relevant_experience"] == []


def test_qualification_requires_actual_education_evidence():
    report = analyze_resume(
        "EXPERIENCE\nWorked on data reports.\nEDUCATION\nBachelor's degree in History.",
        "Required qualifications:\nBachelor's degree in Computer Science",
    )

    assert report["missing_qualifications"] == ["Bachelor's degree in Computer Science"]
    assert report["matched_qualifications"] == []


def test_relevant_course_requirement_matches_education_coursework():
    report = analyze_resume(
        "EDUCATION\nCoursework: Database Systems and Data Modeling.",
        "Required qualifications:\nRelevant coursework in Database Systems.",
    )

    assert report["matched_qualifications"] == ["Relevant coursework in Database Systems"]


def test_specific_certification_does_not_count_twice_as_generic_certification():
    parsed = parse_job_description("Required qualifications:\nPMP certification.")

    qualification_names = [
        item["name"] for item in parsed["requirements"] if item["category"] == "qualification"
    ]
    assert qualification_names == ["PMP"]


def test_duplicate_and_nonmatched_requirements_score_from_statuses_once():
    report = analyze_resume(
        "SKILLS\nPython\nPROJECTS\nCurrently learning SQL.",
        "Required skills:\nPython, Python, SQL, Java",
    )

    assert {item["name"] for item in report["requirements"]} == {
        "Python",
        "SQL",
        "Java",
    }
    status_by_name = {item["name"]: item["status"] for item in report["requirements"]}
    assert status_by_name == {
        "Python": "partially_supported",
        "SQL": "partially_supported",
        "Java": "missing",
    }
    assert report["score"] == round(sum(item["points"] for item in report["criteria"]))
    assert report["score"] <= 100


def test_corrupt_pdf_and_scanned_pdf_have_controlled_messages():
    try:
        extract_upload_with_metadata(b"not a PDF", "resume.pdf", {".pdf"})
    except DocumentError as error:
        assert "could not be opened" in str(error).lower()
    else:
        raise AssertionError("A corrupt PDF was accepted.")

    image_stream = BytesIO()
    Image.new("RGB", (20, 20), color="white").save(image_stream, format="PNG")
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    scanned_pdf_buffer = BytesIO()
    pdf = cast(_PdfCanvas, Canvas(scanned_pdf_buffer))
    pdf.drawImage(ImageReader(image_stream), 72, 720, width=20, height=20)
    pdf.save()
    scanned_pdf = scanned_pdf_buffer.getvalue()

    try:
        extract_upload_with_metadata(scanned_pdf, "scanned.pdf", {".pdf"})
    except DocumentError as error:
        assert "scanned" in str(error).lower()
        assert "ocr is not enabled" in str(error).lower()
    else:
        raise AssertionError("An image-only scanned PDF was accepted.")


def test_pdf_page_limit_and_text_normalization():
    from docx import Document
    from pypdf import PdfWriter

    document = PdfWriter()
    for _ in range(MAX_PDF_PAGES + 1):
        document.add_blank_page(width=100, height=100)
    pdf_buffer = BytesIO()
    document.write(pdf_buffer)
    oversized_page_pdf = pdf_buffer.getvalue()

    try:
        extract_upload_with_metadata(oversized_page_pdf, "pages.pdf", {".pdf"})
    except DocumentError as error:
        assert "page" in str(error).lower()
    else:
        raise AssertionError("A PDF over the page limit was accepted.")

    docx = Document()
    docx.add_paragraph("  Python\t services are available \n")
    docx_buffer = BytesIO()
    docx.save(docx_buffer)
    normalized_text, _ = extract_upload_with_metadata(
        docx_buffer.getvalue(), "resume.docx", {".docx"}
    )
    assert normalized_text == "Python services are available"


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

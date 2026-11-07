from __future__ import annotations

import json
import logging
from io import BytesIO

from flask import Flask, abort, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from resume_analyzer.analyzer import analyze_resume
from resume_analyzer.documents import DocumentError, extract_text

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_JOB_EXTENSIONS = {".pdf", ".docx", ".txt"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
logging.basicConfig(level=logging.INFO)


def _uploaded_text(field_name: str, allowed_extensions: set[str]) -> str:
    uploaded = request.files.get(field_name)
    if uploaded is None or not uploaded.filename:
        return ""

    filename = uploaded.filename
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in allowed_extensions:
        raise DocumentError(
            f"Unsupported file type for {filename!r}. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}."
        )
    return extract_text(uploaded.stream, extension)


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error: RequestEntityTooLarge):
    return render_template(
        "index.html", error="The combined upload is too large. The limit is 5 MB."
    ), 413


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    try:
        resume_text = _uploaded_text("resume_file", ALLOWED_RESUME_EXTENSIONS)
        if not resume_text.strip():
            raise DocumentError("Upload a PDF or DOCX resume with extractable text.")

        job_description = request.form.get("job_description", "").strip()
        uploaded_job_description = _uploaded_text(
            "job_file", ALLOWED_JOB_EXTENSIONS
        ).strip()
        if uploaded_job_description:
            job_description = uploaded_job_description
        if not job_description:
            raise DocumentError(
                "Paste a job description or upload a PDF, DOCX, or TXT file."
            )

        report = analyze_resume(resume_text, job_description)
    except DocumentError as error:
        return render_template("index.html", error=str(error)), 400

    return render_template("index.html", report=report)


@app.post("/download")
def download_report():
    raw_report = request.form.get("report_json", "")
    try:
        report = json.loads(raw_report)
    except json.JSONDecodeError:
        abort(400, description="The report data is invalid.")
    if not isinstance(report, dict) or "score" not in report:
        abort(400, description="The report data is incomplete.")

    content = report.get("plain_text")
    if not isinstance(content, str):
        abort(400, description="The report does not contain a downloadable summary.")

    return send_file(
        BytesIO(content.encode("utf-8")),
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name="resume-match-report.txt",
    )


if __name__ == "__main__":
    app.run(debug=False)

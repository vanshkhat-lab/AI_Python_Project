import json
import unittest
from io import BytesIO

from docx import Document

from app import app


def make_docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Python engineer with 5 years of experience.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


class AppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_homepage_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RoleFit", response.data)
        self.assertIn(b"resume-file-name", response.data)

    def test_analysis_renders_report_and_downloads_text(self):
        response = self.client.post(
            "/analyze",
            data={
                "resume_file": (BytesIO(make_docx_bytes()), "resume.docx"),
                "job_description": "Python engineer with 3 years of experience.",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DOCUMENT MATCH SCORE", response.data)
        self.assertIn(b"Download report", response.data)

    def test_uploaded_job_description_takes_precedence_over_pasted_text(self):
        response = self.client.post(
            "/analyze",
            data={
                "resume_file": (BytesIO(make_docx_bytes()), "resume.docx"),
                "job_description": "SQL required.",
                "job_file": (BytesIO(b"Python required."), "job.txt"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Python", response.data)
        self.assertNotIn(b"SQL", response.data)

    def test_unsupported_resume_type_is_reported(self):
        response = self.client.post(
            "/analyze",
            data={
                "resume_file": (BytesIO(b"data"), "resume.rtf"),
                "job_description": "Python engineer",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Unsupported file type", response.data)

    def test_report_download_rejects_invalid_json(self):
        response = self.client.post(
            "/download", data={"report_json": "not json"}
        )

        self.assertEqual(response.status_code, 400)

    def test_report_download_returns_plain_text_attachment(self):
        report = {"score": 75, "plain_text": "Resume match score: 75"}
        response = self.client.post(
            "/download", data={"report_json": json.dumps(report)}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertEqual(response.data, b"Resume match score: 75")


if __name__ == "__main__":
    unittest.main()

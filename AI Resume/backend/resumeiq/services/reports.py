from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def make_pdf_report(report: dict) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="ResumeIQ Analysis Report",
    )
    styles = getSampleStyleSheet()
    story = [Paragraph("ResumeIQ Analysis Report", styles["Title"]), Spacer(1, 12)]
    for line in report.get("plain_text", "").splitlines():
        if line.strip():
            story.append(Paragraph(escape(line), styles["BodyText"]))
        else:
            story.append(Spacer(1, 7))
    document.build(story)
    return buffer.getvalue()

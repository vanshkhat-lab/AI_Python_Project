import unittest
from io import BytesIO

from docx import Document
from pypdf import PdfWriter

from resume_analyzer.documents import DocumentError, extract_text


def make_docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Python developer with five years of experience.")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Skills: SQL, Docker"
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def make_text_pdf_bytes() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length 53 >>\nstream\nBT /F1 14 Tf 72 720 Td "
        b"(PDF Python engineer) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


class ExtractTextTests(unittest.TestCase):
    def test_extracts_docx_paragraphs_and_table_cells(self):
        text = extract_text(BytesIO(make_docx_bytes()), ".docx")

        self.assertIn("Python developer", text)
        self.assertIn("Skills: SQL, Docker", text)

    def test_extracts_utf8_text_with_bom(self):
        text = extract_text(BytesIO(b"\xef\xbb\xbfPython engineer"), ".txt")

        self.assertEqual(text, "Python engineer")

    def test_extracts_text_from_pdf(self):
        text = extract_text(BytesIO(make_text_pdf_bytes()), ".pdf")

        self.assertIn("PDF Python engineer", text)

    def test_rejects_valid_pdf_without_text(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        stream = BytesIO()
        writer.write(stream)

        with self.assertRaisesRegex(DocumentError, "No readable text"):
            extract_text(BytesIO(stream.getvalue()), ".pdf")

    def test_rejects_unsupported_extension(self):
        with self.assertRaisesRegex(DocumentError, "Unsupported file type"):
            extract_text(BytesIO(b"content"), ".rtf")

    def test_rejects_unreadable_docx(self):
        with self.assertRaisesRegex(DocumentError, "could not be read"):
            extract_text(BytesIO(b"not a docx"), ".docx")

    def test_rejects_unreadable_pdf(self):
        with self.assertRaisesRegex(DocumentError, "could not be read"):
            extract_text(BytesIO(b"not a pdf"), ".pdf")

    def test_rejects_documents_without_text(self):
        with self.assertRaisesRegex(DocumentError, "No readable text"):
            extract_text(BytesIO(b"   "), ".txt")


if __name__ == "__main__":
    unittest.main()

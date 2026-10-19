# ResumeIQ architecture

## Components

- **React/TypeScript/Vite** renders the dashboard and calls the backend using a
  reusable API client. The browser validates for usability, but the backend is
  authoritative.
- **FastAPI** owns request validation, bounded uploads, CORS, extraction,
  requirement parsing, matching, scoring, persistence, and PDF downloads.
- **Document service** uses PyMuPDF for PDF text extraction and the existing
  python-docx-backed extraction utility for DOCX. Uploaded content is held in
  memory by the application and never executed or written into project files.
- **Matching service** reuses the existing analyzer for section-aware evidence
  and skill/qualification matching. The FastAPI layer applies the current
  per-requirement score and attaches reasons, confidence, warnings, and
  job-description metadata. The legacy Flask interface and its historical
  score remain supported separately.
- **Optional OpenAI provider** is invoked only after user consent and only by
  the backend. Its output is schema-constrained and checked against exact
  resume text; it is never authoritative for matching or score.
- **SQLAlchemy/SQLite** stores report JSON only after an explicit save choice.
  Original uploaded files and full extracted resume text are not persisted.
- **ReportLab** generates a downloadable PDF from saved report content; plain
  text export is available for transient results.

## Request flow

1. The user selects a PDF/DOCX resume and pastes or attaches a job description.
   Merely selecting a file does not upload it.
2. The frontend enforces format/size hints and sends one analysis request.
3. FastAPI checks request size and file presence, extension, byte limit, and
   content readability. PDF extraction rejects encrypted, oversized-page-count,
   corrupt, empty, and image-only/low-text files with controlled messages.
4. Deterministic parsing finds supported title, skills, qualifications,
   experience requirements, and responsibilities. The job text itself is not
   replaced with generated content.
5. The existing evidence matcher compares requirements with actual extracted
   resume text. The backend computes each status and score.
6. Rule-based suggestions are returned. If the user explicitly consented and
   an OpenAI key exists, a short-lived provider request may add validated
   wording suggestions. A provider failure does not change the core result.
7. The frontend renders backend data. On explicit save, the client submits the
   same source documents for authoritative re-analysis with persistence enabled;
   only the resulting report is retained.
8. History APIs list, retrieve, and delete saved report JSON. PDF files are
   generated on demand and are not stored as original files.

## Persistence and privacy

`AnalysisRecord` holds a UUID, timestamp, and report JSON in SQLite. The report
can include resume evidence snippets, so saved history contains personal data.
Saving is opt-in; transient analysis is not written to the database. Deleting a
history record removes it from subsequent API reads. The app does not implement
accounts, authorization, encryption-at-rest, or per-user isolation, so a
shared deployment is not appropriate without additional security work.

## Score

Required requirements carry weight 2; preferred requirements carry weight 1.
Matched evidence earns full credit, partial evidence half credit, and missing
or uncertain evidence no credit. The score is the weighted-credit percentage,
rounded to a whole number. No reliable requirements means no score (`null`).
The scoring code does not call the AI provider.

## Current boundaries

The skill vocabulary and title/responsibility parser are heuristic and finite.
Detected items can be reviewed, but not edited independently in the current UI.
Responsibilities are surfaced but not scored. OCR, user accounts, migrations,
and multi-user privacy controls are not implemented.

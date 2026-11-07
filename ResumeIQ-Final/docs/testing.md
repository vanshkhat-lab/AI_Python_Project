# Testing ResumeIQ

## Commands (Windows PowerShell)

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check backend resume_analyzer app.py tests
Set-Location frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
npm.cmd audit
```

## Backend coverage

Pytest covers the preserved analyzer/document parser and the FastAPI
application, including:

- PDF, DOCX, and TXT extraction, including PyMuPDF metadata and image-only
  scanned-PDF guidance.
- Corrupt/unsupported/oversized inputs, empty descriptions, invalid payloads,
  short/no-requirement descriptions, and controlled JSON errors.
- Alias matching, evidence sections, partial/uncertain findings, required and
  preferred scoring weights, experience, zero-requirement score behavior, and
  score boundaries.
- Health/version, extraction and job parsing endpoints, CORS, history save,
  retrieval, deletion, unknown IDs, and PDF signature/download behavior.
- Missing/unavailable AI and rejection of unsupported AI recommendations.

Tests use temporary database overrides and synthetic test files; no real
resumes or production history should be used. Starlette's TestClient uses
`httpx2`, the supported client implementation, to avoid its deprecated
`httpx` compatibility path.

## Frontend coverage

Vitest and React Testing Library cover selected filenames/replacement,
unsupported format, missing description, loading, result rendering, backend
errors, explicit save/PDF links, and starting a fresh analysis. TypeScript
checking and production bundling run in `npm.cmd run build`; ESLint runs in
`npm.cmd run lint`.

## Manual smoke workflow

1. Start FastAPI and Vite as described in the README.
2. Check `GET http://127.0.0.1:8000/api/health` and open `/docs`.
3. Upload synthetic selectable-text PDF or DOCX and enter a complete job
   description.
4. Verify requirement evidence and the displayed score explanation.
5. Save only when desired; open and delete the saved result, then download its
   PDF.
6. Retry with unsupported, corrupt, scanned, and oversized inputs.

No end-to-end browser automation command is currently configured.

# ResumeIQ

ResumeIQ is a local resume-to-job-description analyzer. It extracts text from
PDF and DOCX resumes, detects job requirements, compares them with evidence in
the resume, explains a deterministic score, and can save reports and generate
PDF exports. The default React/FastAPI application remains useful without an
AI key. The original Flask interface is retained as a legacy entry point.

## Features

- React, TypeScript, and Vite dashboard with PDF/DOCX upload, pasted or
  uploaded job descriptions, validation, loading/error states, filename
  display, requirement review, analysis history, and report downloads.
- FastAPI backend with typed request/response models, bounded input, controlled
  JSON errors, restricted CORS, OpenAPI documentation, and `httpx2`-backed
  Starlette TestClient tests.
- PyMuPDF PDF text extraction with page limits and scanned-PDF/OCR guidance;
  python-docx extraction for paragraph and table text. The legacy Flask path
  retains its pypdf extraction implementation.
- Deterministic matching with required/preferred priorities, skill aliases,
  section-aware evidence, partial/missing/uncertain states, reasons, and
  confidence notes.
- Optional backend-only OpenAI recommendations. They require explicit user
  consent, do not affect the score, and are rejected when the evidence quote
  or supported-claim checks fail.
- SQLite/SQLAlchemy saved history. Saving is explicit; originals are not
  persisted. Saved reports can be opened, deleted, or downloaded as PDF.
- Client feedback form at the end of the dashboard. Feedback is stored in
  SQLite and the newest 50 entries are shown on later visits to the same
  application instance.
- Text export remains available for transient results.

## Score and limitations

For each detected skill, qualification, or stated experience requirement:

- Required requirement weight: **2**; preferred requirement weight: **1**.
- Matched evidence receives credit **1.0**; partially supported evidence
  receives **0.5**; missing or uncertain evidence receives **0**.
- The backend calculates `100 × sum(weight × credit) / sum(weight)` and rounds
  to the nearest whole number. If no reliable requirements are detected, the
  score is `null` and the UI displays “Unable to calculate.”

This is a text-evidence comparison, not an employability or hiring probability.
The vocabulary and parser are intentionally finite. They do not infer years of
experience from employment dates. A skill mention without a nearby example of
using it is uncertain evidence and receives no score credit; concrete actions
such as building, testing, or deploying with a skill count as contextual
evidence only when the action is close to that skill mention in the same
sentence or clause. Responsibilities are extracted for context but are not
scored as requirements. Detected requirements can be reviewed, but are not
individually editable in the current UI; edit the job description itself and
review the refreshed parse before analyzing.

PDFs must contain selectable text. OCR is not enabled. File processing limits
are 5 MB per upload, 200 PDF pages, and 100,000 extracted/pasted characters.
The app has no user accounts, authentication, authorization, encryption, or
multi-user isolation. Do not expose it or its SQLite database to untrusted
users or a public network. Saving stores the report and evidence excerpts,
which can contain personal information, but not the original file or complete
extracted resume text. Client feedback is visible to anyone using the same
instance and is not tied to a user account; do not submit personal or sensitive
information.

The legacy Flask interface is available for compatibility, and retains its
original 70% skills / 20% stated experience / 10% qualifications scoring
formula. Use the React/FastAPI application for the current required/preferred
formula described above.

## Architecture and folders

```text
backend/
  resumeiq/
    api.py                 FastAPI routes, validation, CORS, error responses
    config.py              Limits and environment-based configuration
    db.py, models.py       SQLAlchemy / SQLite persistence
    schemas.py             Pydantic request and response contracts
    services/
      analysis.py          Requirement score and report orchestration
      documents.py         PyMuPDF, DOCX, and text extraction
      job_parser.py        Deterministic requirement/title/responsibility parse
      ai.py                Optional OpenAI provider and output validation
      reports.py           PDF report generator
frontend/
  src/
    App.tsx                Responsive dashboard, results, history, privacy
    api.ts                 Typed fetch client, timeout and response checks
    types.ts               API response types
    style.css              Responsive visual system
resume_analyzer/           Preserved matching and legacy document services
tests/                     Pytest unit and API integration tests
docs/                      Architecture, API, testing, troubleshooting
```

The React app calls FastAPI over HTTP. The backend owns extraction, parsing,
matching, scoring, optional AI, persistence, and PDF generation. The browser
never calculates the authoritative score.

## Prerequisites

- Python 3.10 or newer.
- Node.js 20 or newer and npm.
- Windows PowerShell commands below use the project path
  `D:\Desktop\python project\AI Resume`; update it if the folder is elsewhere.

## Install (Windows PowerShell)

Open PowerShell at the project folder:

```powershell
cd "D:\Desktop\python project\AI Resume"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm.cmd ci
```

The first Python requirements file installs FastAPI, extraction, reporting,
database, and test dependencies. The root requirements file adds Flask for the
preserved legacy app. `npm.cmd` avoids PowerShell execution-policy issues with
the npm PowerShell shim.

## Configure and run

Copy the examples if you want to customize values:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

Vite loads `frontend\.env` when started. The backend reads process environment
variables and does not automatically load `backend\.env.example`; configure it
in the backend PowerShell session:

```powershell
cd "D:\Desktop\python project\AI Resume"
$env:FRONTEND_ORIGIN = "http://localhost:5173"
# Optional; leave unset to disable external AI processing:
# $env:OPENAI_API_KEY = "your-server-side-key"
# $env:OPENAI_MODEL = "gpt-4.1-mini"
.\.venv\Scripts\python.exe -m uvicorn backend.resumeiq.api:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd "D:\Desktop\python project\AI Resume\frontend"
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open <http://localhost:5173>. The dashboard uses the Vite development proxy
unless `VITE_API_BASE_URL` is set. The backend is at
<http://127.0.0.1:8000>; FastAPI documentation is at
<http://127.0.0.1:8000/docs>.

Tables are created when FastAPI starts. The default database is
`backend/resumeiq/resumeiq.sqlite3` and is excluded from version control.
`DATABASE_URL` can point to a different SQLAlchemy SQLite URL. No database
migration tool is configured; schema creation uses SQLAlchemy
`metadata.create_all`.

### Optional OpenAI recommendations

Install the optional SDK:

```powershell
cd "D:\Desktop\python project\AI Resume"
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-ai.txt
```

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the backend process
environment, restart FastAPI, then select the AI consent checkbox before
analysis. When selected, the provider receives resume text (truncated to
40,000 characters) and deterministic findings. It does not receive API keys or
the job description, and it cannot set the score. Without a configured key,
the core analysis and rule-based suggestions remain available.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Single allowed CORS origin. |
| `DATABASE_URL` | Project-local SQLite file | SQLAlchemy database URL. |
| `OPENAI_API_KEY` | Unset | Optional, server-side OpenAI key. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Optional OpenAI model. |
| `VITE_API_BASE_URL` | Empty (Vite `/api` proxy) | Optional API origin visible to the browser; never put secrets here. |

See [backend/.env.example](./backend/.env.example) and
[frontend/.env.example](./frontend/.env.example). The Vite value is public in
the compiled browser bundle and must never contain credentials.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status and application version. |
| POST | `/api/resumes/extract` | Multipart `resume_file` PDF/DOCX extraction. |
| POST | `/api/job-descriptions/extract` | JSON `{ "text": "..." }` parsing. |
| POST | `/api/analyze` | JSON resume text or multipart resume upload; optionally requests AI and/or saves explicitly. |
| POST | `/api/analyze/text` | JSON text-analysis compatibility endpoint. |
| GET | `/api/analyses` | List saved report summaries. |
| GET | `/api/analyses/{analysis_id}` | Retrieve a saved report. |
| DELETE | `/api/analyses/{analysis_id}` | Delete a saved report. |
| GET | `/api/analyses/{analysis_id}/report` | Generate/download saved PDF. |
| GET | `/api/feedback` | List the 50 newest client feedback entries. |
| POST | `/api/feedback` | Save a public feedback message (up to 1,000 characters). |

The legacy upload extraction routes remain at `/api/extract/resume` and
`/api/extract/job-description`. Errors use
`{"error":{"code":"...","message":"..."}}`. Full schemas and examples are in
[docs/api.md](./docs/api.md).

## Tests and quality checks

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

Backend tests cover legacy behavior, matching, PDF/DOCX extraction, aliases,
required/preferred scoring, corrupt/scanned/oversized documents, error
responses, CORS, optional AI validation, persistence, 404s, and PDF generation.
Frontend tests cover file state, validation, loading, results, errors, save,
and reset. See [docs/testing.md](./docs/testing.md).

## Troubleshooting

- **Missing Python dependencies:** use the project `.venv` Python explicitly
  for installation and server startup; do not use a different global
  interpreter.
- **Frontend cannot reach the API:** keep both servers running, verify port
  8000 and 5173, and configure `FRONTEND_ORIGIN` to the browser origin.
- **No text from a PDF:** it may be scanned/image-only; OCR is not included.
- **AI suggestions unavailable:** core analysis remains valid. Verify the
  backend-only key/model settings and restart the backend.
- **Saved history appears shared:** this local MVP has no authentication or
  per-user authorization. Do not deploy it as a multi-user service.

More details: [docs/troubleshooting.md](./docs/troubleshooting.md).

## Further documentation

- [Architecture](./docs/architecture.md)
- [API reference](./docs/api.md)
- [Testing guide](./docs/testing.md)
- [Troubleshooting](./docs/troubleshooting.md)

## GitHub publishing checklist

Review `.gitignore`; verify that `.env`, the SQLite database, `.venv`, generated
frontend bundles, and `node_modules` are excluded. Do not add real resumes,
provider keys, or personal test data. Use only synthetic documents in tests.


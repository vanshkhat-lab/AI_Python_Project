# ResumeIQ troubleshooting

## Python imports or server startup fails

Run commands from the project root and use
`.\.venv\Scripts\python.exe` explicitly. If dependencies changed, install:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Do not install packages into one Python interpreter and launch another.

## Dashboard cannot reach the backend

Keep both processes running. FastAPI defaults to `127.0.0.1:8000`, Vite to
`localhost:5173`. Open the frontend as `http://localhost:5173` when
`FRONTEND_ORIGIN` is its default. If using another origin, set
`FRONTEND_ORIGIN` to that exact origin and restart FastAPI. A non-empty
`VITE_API_BASE_URL` bypasses Vite's `/api` development proxy.

## Upload rejected or no text extracted

Only PDF and DOCX resumes are supported. Each file may be at most 5 MB; PDF
documents may have at most 200 pages. The filename extension and actual parser
content must agree. Password-protected, corrupt, empty, or low-text documents
are rejected. Scanned PDFs require OCR, which is not available; try a
text-selectable export.

## No useful requirements or score

The parser uses a finite deterministic skill and qualification vocabulary. A
short description may not contain enough information. Add explicit required
and preferred skills, qualifications, experience, and responsibilities; use
the “Review detected requirements” control before analyzing.

## AI suggestions are unavailable

AI is optional and off unless selected in the UI. Install
`backend\requirements-ai.txt`, set `OPENAI_API_KEY` only in the backend
process environment, verify `OPENAI_MODEL`, and restart FastAPI. A provider
failure leaves the deterministic result intact. Never set the secret as a
`VITE_` variable.

## History cannot be found or deleted

The default SQLite file is `backend/resumeiq/resumeiq.sqlite3`. Changing
`DATABASE_URL` points the app to a different database. Saved history belongs
to that local database and is not associated with user accounts. The current
app has no multi-user authorization.

## Ports are already in use

Check whether another API or Vite process is still running. Either stop the
specific process in its own terminal or choose different ports and update
`FRONTEND_ORIGIN`, Vite's API base/proxy configuration, and the startup URL
consistently.

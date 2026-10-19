# ResumeIQ API

FastAPI docs: `/docs`; OpenAPI JSON: `/api/openapi.json`. All errors use:

```json
{"error":{"code":"validation_error","message":"The request is invalid."}}
```

## Endpoints

### `GET /api/health`

Returns `200`:

```json
{"status":"ok","version":"1.0.0","ai_recommendations":false}
```

### `POST /api/resumes/extract`

Multipart form field: `resume_file` (PDF or DOCX, maximum 5 MB).
Returns `200` with extracted `text`, `filename`, `metadata.character_count`,
`metadata.page_count` (PDF only), and `warnings`.

Errors: `400` unreadable/empty/protected content; `413` oversize; `415`
unsupported extension; `422` missing multipart field.

Legacy alias: `POST /api/extract/resume`. A legacy job-file extractor remains
available at `POST /api/extract/job-description`.

### `POST /api/job-descriptions/extract`

JSON request:

```json
{"text":"Senior Data Analyst\nRequired: Python and SQL.\nPreferred: Tableau."}
```

Returns `200` with `job_title`, structured `requirements` (each has `name`,
`category`, and `priority`), `responsibilities`, and `warnings`. Parsing is
heuristic and does not replace the user-provided text. Empty or invalid input
returns `422`; short or unrecognized content is returned with warnings.

### `POST /api/analyze`

JSON input:

```json
{
  "resume_text":"EXPERIENCE\nBuilt Python services.",
  "job_description":"Python is required.",
  "save_analysis":false,
  "generate_ai_recommendations":false
}
```

Alternatively send multipart form fields `resume_file`, `job_description`,
optional `job_file`, `save_analysis`, and `generate_ai_recommendations`.
If `job_file` is supplied it takes precedence over the pasted description.
The current UI uses this upload form so it does not upload files until the
user starts analysis.

The response contains a nullable `score`, `scoring_note`, requirements and
their evidence/status/reason/confidence, experience, requirements breakdown,
recommendations, warnings, and optional `analysis_id`/`created_at` when
`save_analysis` is true. Saving stores report JSON but not the source file or
full extracted resume text.

Score formula: `100 × sum(weight × credit) / sum(weight)`, rounded to an
integer. Required weight `2`; preferred weight `1`; matched credit `1`,
partial `0.5`, missing/uncertain `0`. Zero detected requirements returns
`score: null`, not zero.

Errors: `400` unreadable files; `413` file, text, request, or extracted-text
limit; `415` unsupported format; `422` empty/malformed input. If optional AI
fails, analysis succeeds with an AI status/warning.

`POST /api/analyze/text` remains as a JSON text-analysis compatibility route
with the same request fields.

### Saved history

- `GET /api/analyses` returns summaries (`analysis_id`, `created_at`, `score`,
  `job_title`) without complete resume text.
- `GET /api/analyses/{analysis_id}` returns saved report JSON.
- `DELETE /api/analyses/{analysis_id}` returns `204` after deletion.
- `GET /api/analyses/{analysis_id}/report` returns a generated `application/pdf`.

Unknown IDs return `404`. History is local to the configured database; there
is no authentication or multi-user authorization.

### Client feedback

- `GET /api/feedback` returns up to 50 newest feedback entries with
  `feedback_id`, `message`, and `created_at`.
- `POST /api/feedback` accepts `{"message":"..."}` and returns the saved entry
  with status `201`. Messages must contain 1–1,000 non-whitespace characters.

Feedback persists in the same SQLite database and is displayed to all visitors
of that application instance. There are no user accounts or moderation tools;
the dashboard warns visitors not to include personal or sensitive information.

## Limits and errors

- 5 MB per uploaded file; multipart requests are separately bounded.
- 100,000 characters for text inputs and extracted document text.
- 200 pages per PDF.
- Unsupported files use `415`; corrupt/unreadable documents use `400`;
  oversized requests use `413`; malformed/empty request payloads use `422`.
- Error messages do not expose server paths or raw tracebacks.

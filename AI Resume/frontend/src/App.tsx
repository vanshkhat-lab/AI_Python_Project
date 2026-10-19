import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import {
  analyzeDocuments,
  apiUrl,
  deleteHistoryItem,
  downloadTextReport,
  getFeedback,
  getAnalysis,
  getHistory,
  parseJobDescription,
  submitFeedback,
} from "./api";
import type {
  AnalysisReport,
  ClientFeedback,
  HistoryItem,
  ParsedJobDescription,
  RequirementEvidence,
  RequirementStatus,
} from "./types";

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const MAX_TEXT_LENGTH = 100_000;
const MAX_FEEDBACK_LENGTH = 1000;
const RESUME_EXTENSIONS = [".pdf", ".docx"];
const JOB_EXTENSIONS = [".pdf", ".docx", ".txt"];

function validateFile(file: File, extensions: string[]): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!extensions.includes(extension)) {
    return `Unsupported file type. Choose ${extensions.join(" or ")}.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) return "Each file must be 5 MB or smaller.";
  return null;
}

function FilePicker({
  id,
  title,
  hint,
  accept,
  selected,
  onChange,
  onClear,
  compact = false,
  disabled = false,
}: {
  id: string;
  title: string;
  hint: string;
  accept: string;
  selected: File | null;
  onChange: (file: File | null) => void;
  onClear: () => void;
  compact?: boolean;
  disabled?: boolean;
}) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.files?.[0] ?? null);
    event.target.value = "";
  };

  if (compact) {
    return (
      <div className="compact-picker">
        {selected ? (
          <span className="selected-job" title={selected.name}>
            {selected.name}
          </span>
        ) : null}
        <label className="compact-upload" htmlFor={id}>
          {selected ? "Change file" : `＋ ${title}`}
        </label>
        {selected ? (
          <button className="clear-file" type="button" onClick={onClear} aria-label="Remove job description file" disabled={disabled}>
            ×
          </button>
        ) : null}
        <input
          id={id}
          className="visually-hidden"
          type="file"
          accept={accept}
          onChange={handleChange}
          disabled={disabled}
        />
      </div>
    );
  }

  return (
    <div className={`resume-picker${selected ? " has-file" : ""}`}>
      <span className="upload-icon" aria-hidden="true">{selected ? "✓" : "↑"}</span>
      <div className="upload-copy">
        <strong>{selected ? selected.name : title}</strong>
        <small>{selected ? `${hint} · ${(selected.size / 1024).toFixed(0)} KB` : hint}</small>
      </div>
      <label className="choose-file" htmlFor={id}>
        {selected ? "Change file" : "Choose file"}
      </label>
      {selected ? (
        <button className="clear-file" type="button" onClick={onClear} aria-label="Remove resume file" disabled={disabled}>
          ×
        </button>
      ) : null}
      <input
        id={id}
        className="visually-hidden"
        type="file"
        accept={accept}
        onChange={handleChange}
        aria-label={title}
        disabled={disabled}
      />
    </div>
  );
}

function StatusPill({ status }: { status: RequirementStatus }) {
  const labels: Record<RequirementStatus, string> = {
    matched: "Evidence found",
    partially_supported: "Partial evidence",
    missing: "Not found",
    uncertain: "Needs review",
  };
  return <span className={`status-pill status-${status}`}>{labels[status]}</span>;
}

function RequirementEvidenceList({
  requirements,
  emptyMessage,
}: {
  requirements: RequirementEvidence[];
  emptyMessage: string;
}) {
  if (!requirements.length) return <p className="empty-note">{emptyMessage}</p>;

  return (
    <ul className="requirement-list">
      {requirements.map((item) => (
        <li key={`${item.category}-${item.name}-${item.priority}`}>
          <div className="requirement-top">
            <strong>{item.name}</strong>
            <StatusPill status={item.status} />
          </div>
          <div className="requirement-meta">
            {item.priority} · {item.confidence} confidence
          </div>
          <p className="requirement-reason">{item.reason}</p>
          {item.evidence ? <blockquote>{item.evidence}</blockquote> : null}
        </li>
      ))}
    </ul>
  );
}

function RequirementCard({
  title,
  requirements,
}: {
  title: string;
  requirements: RequirementEvidence[];
}) {
  return (
    <article className="requirement-card">
      <div className="report-card-title">
        <h3>{title}</h3>
        <span className="count">{requirements.length}</span>
      </div>
      <RequirementEvidenceList
        requirements={requirements}
        emptyMessage="No requirements detected in this group."
      />
    </article>
  );
}

export default function App() {
  const [resume, setResume] = useState<File | null>(null);
  const [jobFile, setJobFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fileError, setFileError] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [generateAi, setGenerateAi] = useState(false);
  const [jobSummary, setJobSummary] = useState<ParsedJobDescription | null>(null);
  const [parsingJob, setParsingJob] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [feedbackItems, setFeedbackItems] = useState<ClientFeedback[]>([]);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(true);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");
  const [feedbackSuccess, setFeedbackSuccess] = useState("");

  useEffect(() => {
    let active = true;
    void getFeedback()
      .then((items) => {
        if (active) setFeedbackItems(items);
      })
      .catch((caught: unknown) => {
        if (active) {
          setFeedbackError(
            caught instanceof Error ? caught.message : "Could not load client feedback.",
          );
        }
      })
      .finally(() => {
        if (active) setFeedbackLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const setSelectedResume = (file: File | null) => {
    setFileError("");
    if (file) {
      const validation = validateFile(file, RESUME_EXTENSIONS);
      if (validation) {
        setFileError(validation);
        setResume(null);
        return;
      }
    }
    setResume(file);
  };

  const setSelectedJobFile = (file: File | null) => {
    setFileError("");
    if (file) {
      const validation = validateFile(file, JOB_EXTENSIONS);
      if (validation) {
        setFileError(validation);
        setJobFile(null);
        return;
      }
    }
    setJobFile(file);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (!resume) {
      setError("Choose a PDF or DOCX resume before starting the analysis.");
      return;
    }
    if (!jobFile && !jobDescription.trim()) {
      setError("Paste a job description or attach a PDF, DOCX, or TXT file.");
      return;
    }
    if (jobDescription.length > MAX_TEXT_LENGTH) {
      setError("The pasted job description must be 100,000 characters or fewer.");
      return;
    }
    setLoading(true);
    setReport(null);
    try {
      const result = await analyzeDocuments(
        resume,
        jobDescription,
        jobFile ?? undefined,
        generateAi,
      );
      setReport(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleParseJob = async () => {
    if (!jobDescription.trim()) return;
    setError("");
    setParsingJob(true);
    try {
      setJobSummary(await parseJobDescription(jobDescription));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not process the job description.");
    } finally {
      setParsingJob(false);
    }
  };

  const handleSave = async () => {
    if (!report) return;
    setError("");
    setSaving(true);
    try {
      if (!resume) throw new Error("Select the original resume to save this analysis.");
      const saved = await analyzeDocuments(
        resume,
        jobDescription,
        jobFile ?? undefined,
        generateAi,
        true,
      );
      setReport(saved);
      setHistory(await getHistory());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this analysis.");
    } finally {
      setSaving(false);
    }
  };

  const handleHistory = async () => {
    setError("");
    try {
      setHistory(await getHistory());
      setHistoryOpen((current) => !current);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load saved analyses.");
    }
  };

  const handleDeleteHistory = async (id: string) => {
    if (!window.confirm("Delete this saved analysis? This cannot be undone.")) return;
    setError("");
    try {
      await deleteHistoryItem(id);
      setHistory(await getHistory());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete this analysis.");
    }
  };

  const handleOpenHistory = async (id: string) => {
    setError("");
    try {
      setReport(await getAnalysis(id));
      setHistoryOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not open this analysis.");
    }
  };

  const handleRetryAi = async () => {
    if (!resume || (!jobFile && !jobDescription.trim())) return;
    setError("");
    setLoading(true);
    try {
      const result = await analyzeDocuments(
        resume,
        jobDescription,
        jobFile ?? undefined,
        true,
      );
      setReport(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not retry AI recommendations.");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedbackSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedbackError("");
    setFeedbackSuccess("");
    const message = feedbackText.trim();
    if (!message) {
      setFeedbackError("Write feedback before submitting.");
      return;
    }
    setFeedbackSubmitting(true);
    try {
      const saved = await submitFeedback(message);
      setFeedbackItems((items) => [saved, ...items].slice(0, 50));
      setFeedbackText("");
      setFeedbackSuccess("Thank you. Your feedback is saved and visible below.");
    } catch (caught) {
      setFeedbackError(
        caught instanceof Error ? caught.message : "Could not save your feedback.",
      );
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const startNew = () => {
    setResume(null);
    setJobFile(null);
    setJobDescription("");
    setReport(null);
    setError("");
    setFileError("");
    setJobSummary(null);
    setGenerateAi(false);
  };

  const requiredRequirements = report?.requirements.filter((item) => item.priority === "required") ?? [];
  const preferredRequirements = report?.requirements.filter((item) => item.priority === "preferred") ?? [];
  const experienceRequirements = report?.requirements.filter((item) => item.category === "experience") ?? [];
  const qualificationRequirements = report?.requirements.filter((item) => item.category === "qualification") ?? [];

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ResumeIQ home">
          <span className="brand-mark">R</span> resume<span>iq</span>
        </a>
        <button className="history-toggle" type="button" onClick={handleHistory}>
          Saved analyses
        </button>
      </header>

      {historyOpen ? (
        <section className="history-panel" aria-label="Saved analysis history">
          <div className="history-heading">
            <h2>Saved analyses</h2>
            <button type="button" onClick={() => setHistoryOpen(false)} aria-label="Close saved analyses">×</button>
          </div>
          {history.length ? history.map((item) => (
            <div className="history-item" key={item.analysis_id}>
              <span>
                {item.job_title ? `${item.job_title} · ` : ""}Score {item.score ?? "—"} ·{" "}
                {new Date(item.created_at).toLocaleString()}
                <small className="history-id">ID: {item.analysis_id}</small>
              </span>
              <div className="history-actions">
                <button type="button" onClick={() => void handleOpenHistory(item.analysis_id)}>Open</button>
                <a href={apiUrl(`/api/analyses/${item.analysis_id}/report`)} download>PDF</a>
                <button type="button" onClick={() => void handleDeleteHistory(item.analysis_id)}>Delete</button>
              </div>
            </div>
          )) : <p className="empty-note">No saved analyses yet.</p>}
        </section>
      ) : null}

      <section className="hero">
        <div className="eyebrow"><span className="eyebrow-dot" /> RESUME MATCH ANALYZER</div>
        <h1>Make your experience<br /><span className="muted-heading">visible to the role.</span></h1>
        <p className="hero-copy">Compare what your resume says with what a role asks for. See the evidence, understand the score, and choose what to improve.</p>
        <div className="trust-line">Private by default · No employability promises · Your claims stay yours</div>
      </section>

      <section className="workspace-grid">
        <div className="form-card">
          <div className="card-heading">
            <span className="step-number">01</span>
            <div><h2>Bring the two sides together</h2><p>Choose your resume, then paste or attach the job description.</p></div>
          </div>
          <form onSubmit={handleSubmit} noValidate>
            <label className="field-label" htmlFor="resume-upload">Your resume <span className="required">Required</span></label>
            <FilePicker
              id="resume-upload"
              title="Choose a resume file"
              hint="PDF or DOCX · up to 5 MB"
              accept=".pdf,.docx"
              selected={resume}
              onChange={setSelectedResume}
              onClear={() => setSelectedResume(null)}
              disabled={loading || saving}
            />

            <div className="field-row">
              <label className="field-label" htmlFor="job-description">Job description <span className="optional">Paste or upload</span></label>
              <FilePicker
                id="job-upload"
                title="Attach job description"
                hint="PDF, DOCX, or TXT"
                accept=".pdf,.docx,.txt"
                selected={jobFile}
                onChange={setSelectedJobFile}
                onClear={() => setSelectedJobFile(null)}
                compact
                disabled={loading || saving}
              />
            </div>
            <textarea
              id="job-description"
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              maxLength={MAX_TEXT_LENGTH}
              disabled={loading || saving}
              rows={8}
              placeholder="Paste the role's responsibilities, skills, experience, and qualifications here. An attached file takes precedence."
              aria-describedby="job-description-help"
            />
            <p className="field-help" id="job-description-help">
              {jobDescription.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()} characters
              {jobFile ? ` · ${jobFile.name} will be used instead of pasted text` : ""}
              {!jobFile && jobDescription.trim().length > 0 && jobDescription.trim().length < 80
                ? " · This description is short; adding requirements may improve the analysis."
                : ""}
            </p>
            {jobDescription.trim().length > 0 ? (
              <button
                className="secondary-button parse-job-button"
                type="button"
                onClick={() => void handleParseJob()}
                disabled={parsingJob || loading || saving}
              >
                {parsingJob ? "Reviewing requirements…" : "Review detected requirements"}
              </button>
            ) : null}
            {jobSummary ? (
              <div className="job-summary" aria-live="polite">
                <strong>{jobSummary.job_title ?? "Job title not identified"}</strong>
                {jobSummary.requirements.length ? (
                  <ul>
                    {jobSummary.requirements.map((item) => (
                      <li key={`${item.category}-${item.name}`}>
                        {item.name} · {item.priority}
                      </li>
                    ))}
                  </ul>
                ) : <p>No reliable requirements were detected. Add more detail before analysis.</p>}
                {jobSummary.warnings.map((warning) => <p className="field-help" key={warning}>{warning}</p>)}
              </div>
            ) : null}
            <label className="consent-row">
              <input
                type="checkbox"
                checked={generateAi}
                onChange={(event) => setGenerateAi(event.target.checked)}
                disabled={loading || saving}
              />
              <span>Request optional AI wording suggestions. Resume excerpts may be sent to OpenAI; the score stays deterministic.</span>
            </label>
            {fileError ? <p className="alert" role="alert">{fileError}</p> : null}
            {error ? <p className="alert" role="alert">{error}</p> : null}
            <button className="analyze-button" type="submit" disabled={loading || saving}>
              {loading ? <><span className="spinner" /> Analyzing documents…</> : <>Analyze my match <span aria-hidden="true">↗</span></>}
            </button>
            {loading ? <p className="loading-note" role="status">Extracting document text and comparing stated evidence. Your files are not saved.</p> : null}
          </form>
        </div>

        <aside className="method-card">
          <div className="method-kicker">HOW IT WORKS</div>
          <h2>A score you<br />can understand.</h2>
          <p>The deterministic score compares explicit evidence—not a prediction of employability.</p>
          <div className="weight-list">
            <div><span>Required requirements</span><strong>weight 2</strong></div>
            <div><span>Preferred requirements</span><strong>weight 1</strong></div>
            <div><span>Matched / partial / missing</span><strong>1 / 0.5 / 0 credit</strong></div>
          </div>
          <div className="method-foot"><span className="info-icon">i</span><span>Score = 100 × weighted credits ÷ total requirement weight. Uncertain evidence receives zero credit; preferred requirements count at half the weight. Dates are never used to guess experience duration.</span></div>
        </aside>
      </section>

      <section className="privacy-section">
        <button type="button" className="secondary-button" onClick={() => setPrivacyOpen((open) => !open)}>
          {privacyOpen ? "Hide privacy and methodology" : "Privacy and methodology"}
        </button>
        {privacyOpen ? (
          <div className="privacy-details">
            <h2>Privacy and methodology</h2>
            <p>PDF and DOCX resumes up to 5 MB are accepted. Files are processed for this request and are not retained by default. Choosing “Save analysis” retains the report, including evidence excerpts and job details, in the local SQLite database; it does not retain the original file. Use Saved analyses to open or delete it.</p>
            <p>When you explicitly request AI suggestions, resume excerpts may be sent to OpenAI using the server-side configuration. AI never sets the score. Without a configured provider, deterministic analysis remains available.</p>
            <p>Required requirements have weight 2 and preferred requirements weight 1; evidence credits are 1 for matched, 0.5 for partial, and 0 for missing or uncertain. Scores are document comparisons, not hiring probabilities. The app has no authentication, encryption, or multi-user isolation.</p>
          </div>
        ) : null}
      </section>

      {report ? (
        <section className="results" aria-live="polite">
          <div className="results-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-dot" /> YOUR ANALYSIS</div>
              <h2>Here’s where you stand.</h2>
              <p>Use this as a tailoring guide, not a hiring prediction.</p>
            </div>
            <div className="result-actions">
              <button type="button" className="secondary-button" onClick={() => void downloadTextReport(report)}>Download text</button>
              {report.analysis_id ? (
                <a className="download-button" href={apiUrl(`/api/analyses/${report.analysis_id}/report`)} download>Download PDF</a>
              ) : (
                <button type="button" className="download-button" onClick={() => void handleSave()} disabled={saving || loading}>
                  {saving ? "Saving…" : "Save analysis"}
                </button>
              )}
              <button type="button" className="secondary-button" onClick={startNew} disabled={saving || loading}>New analysis</button>
            </div>
          </div>
          {report.analysis_id ? null : (
            <p className="field-help save-disclosure">Saving stores this report, detected job details, and resume evidence excerpts in local history. The uploaded file itself is not stored.</p>
          )}
          {report.job_title ? <p className="result-job-title">Analysis for: {report.job_title}</p> : null}
          {report.warnings.map((warning) => <p className="warning-note" role="status" key={warning}>{warning}</p>)}

          <div className="result-grid">
            <article className="score-card">
              <div className="score-label">OVERALL REQUIREMENT MATCH <span className="info-icon" title={report.scoring_note}>i</span></div>
              <div className="score-number">{report.score ?? "—"}{report.score !== null ? <small>/100</small> : null}</div>
              {report.score !== null ? <div className="score-track"><span style={{ width: `${report.score}%` }} /></div> : null}
              <p>{report.score !== null ? "Evidence-based comparison, not a guarantee of employability." : "Unable to calculate a score: no reliable requirements were detected."}</p>
            </article>
            <article className="breakdown-card">
              <h3>Scoring breakdown</h3>
              {report.criteria.length ? report.criteria.map((criterion) => (
                <div className="criterion" key={criterion.name}>
                  <div className="criterion-top"><strong>{criterion.name}</strong><span>{criterion.points.toFixed(1)} pts</span></div>
                  <div className="criterion-track"><span style={{ width: `${Math.round(criterion.coverage * 100)}%` }} /></div>
                  <p>{criterion.detail} · {Math.round(criterion.effective_weight * 100)}% effective weight</p>
                </div>
              )) : <p className="empty-note">No criteria were available to score. Review the job description and try again.</p>}
            </article>
          </div>
          <p className="scoring-note">{report.scoring_note}</p>

          <div className="report-grid">
            <RequirementCard title="Required evidence" requirements={requiredRequirements} />
            <RequirementCard title="Preferred evidence" requirements={preferredRequirements} />
            <article className="report-card">
              <div className="report-card-title"><h3>Experience & qualifications</h3></div>
              <p>{report.experience.summary}</p>
              <h4>Experience requirements</h4>
              <RequirementEvidenceList
                requirements={experienceRequirements}
                emptyMessage="No experience requirement was detected in the job description."
              />
              <h4>Qualifications</h4>
              <RequirementEvidenceList
                requirements={qualificationRequirements}
                emptyMessage="No qualification requirements were detected in the job description."
              />
              {report.responsibilities.length ? (
                <>
                  <h4>Responsibilities detected</h4>
                  <ul className="responsibility-list">{report.responsibilities.map((item) => <li key={item}>{item}</li>)}</ul>
                </>
              ) : null}
            </article>
          </div>

          <div className="detail-grid">
            <article className="detail-card">
              <div className="section-overline">RELEVANT RESUME TEXT</div>
              <h3>What the analysis picked up</h3>
              {report.relevant_experience.length ? (
                <ul className="evidence-list">{report.relevant_experience.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>
              ) : <p>No directly relevant excerpts were detected in the resume text.</p>}
            </article>
            <article className="detail-card">
              <div className="section-overline">NEXT STEPS</div>
              <h3>Rule-based improvement suggestions.</h3>
              <ul className="suggestion-list">
                {report.improvements.map((item) => <li key={item}><span aria-hidden="true">↗</span>{item}</li>)}
                {report.ai_recommendations.map((item) => (
                  <li key={item.suggestion}>
                    <span aria-hidden="true">✳</span>
                    <span>
                      {item.suggestion}
                      <small>
                        {item.explanation}
                        {item.introduces_new_claim === null
                          ? " This saved suggestion predates current claim checks; review it carefully."
                          : ""}
                      </small>
                      <blockquote>{item.evidence_quote}</blockquote>
                    </span>
                  </li>
                ))}
              </ul>
              {report.ai_status === "unavailable" ? <p className="field-help">Optional AI suggestions were unavailable; deterministic analysis is unaffected.</p> : null}
              {report.ai_status === "not_configured" ? <p className="field-help">AI suggestions are optional and not configured.</p> : null}
              {report.ai_status === "not_requested" ? <p className="field-help">Optional AI suggestions were not requested.</p> : null}
              {(report.ai_status === "unavailable" || report.ai_status === "not_requested") && resume ? (
                <button className="secondary-button" type="button" onClick={() => void handleRetryAi()} disabled={loading || saving}>
                  {loading ? "Retrying…" : report.ai_status === "unavailable" ? "Retry AI recommendations" : "Request AI recommendations"}
                </button>
              ) : null}
              <p className="ethics-note">Only include claims you can honestly support. No experience or qualifications are invented.</p>
            </article>
          </div>
        </section>
      ) : null}

      <section className="feedback-section" aria-labelledby="feedback-title">
        <div className="feedback-intro">
          <div className="section-overline">HELP US IMPROVE</div>
          <h2 id="feedback-title">Client feedback</h2>
          <p>Tell us what worked well or what we should improve.</p>
          <p className="feedback-privacy">
            Feedback is visible to everyone using this ResumeIQ instance. Please do not include
            personal or sensitive information.
          </p>
        </div>
        <form className="feedback-form" onSubmit={(event) => void handleFeedbackSubmit(event)}>
          <label className="field-label" htmlFor="client-feedback">Your feedback</label>
          <textarea
            id="client-feedback"
            value={feedbackText}
            onChange={(event) => setFeedbackText(event.target.value)}
            maxLength={MAX_FEEDBACK_LENGTH}
            rows={4}
            placeholder="Share your experience with ResumeIQ…"
            disabled={feedbackSubmitting}
          />
          <div className="feedback-form-footer">
            <span className="field-help">
              {feedbackText.length} / {MAX_FEEDBACK_LENGTH} characters
            </span>
            <button
              type="submit"
              className="secondary-button"
              disabled={feedbackSubmitting || !feedbackText.trim()}
            >
              {feedbackSubmitting ? "Saving…" : "Submit feedback"}
            </button>
          </div>
          {feedbackError ? <p className="alert" role="alert">{feedbackError}</p> : null}
          {feedbackSuccess ? <p className="feedback-success" role="status">{feedbackSuccess}</p> : null}
        </form>
        <div className="feedback-wall" aria-live="polite">
          <h3>Previous feedback</h3>
          {feedbackLoading ? <p className="empty-note">Loading feedback…</p> : null}
          {!feedbackLoading && feedbackItems.length === 0 && !feedbackError ? (
            <p className="empty-note">No feedback yet. You can be the first to share yours.</p>
          ) : null}
          {feedbackItems.length ? (
            <ul className="feedback-list">
              {feedbackItems.map((item) => (
                <li key={item.feedback_id}>
                  <p>{item.message}</p>
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString()}
                  </time>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </section>

      <footer><span>RESUMEIQ</span><p>Uploads are not retained by the app. Saving history is explicit and stores report data only.</p></footer>
    </main>
  );
}

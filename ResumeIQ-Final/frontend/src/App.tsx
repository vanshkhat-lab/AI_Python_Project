import { useEffect, useMemo, useState } from "react";
import {
  analyzeFile,
  analyzeText,
  listFeedback,
  submitFeedback,
} from "./api";
import type { AnalysisReport, CustomerFeedback, HistoryItem } from "./types";

const HISTORY_STORAGE_KEY = "resumeiq-session-history";

const formatScore = (score: number | null) => (score === null ? "Unable to calculate" : `${score}/100`);
const evidenceTypeLabel = (evidenceType: string | null) => {
  const labels: Record<string, string> = {
    demonstrated: "Demonstrated",
    explicitly_listed: "Explicitly listed",
    partial: "Partial",
    uncertain: "Uncertain",
    missing: "Missing",
  };
  return evidenceType ? labels[evidenceType] ?? evidenceType : null;
};

function App() {
  const [jobDescription, setJobDescription] = useState(
    "Senior .NET Developer\n\nRequired Skills:\n- C#\n- ASP.NET Core\n- SQL Server\n- REST API\n\nPreferred Skills:\n- Docker\n- React\n\nQualifications:\n- Bachelor's degree in Computer Science or related field\n\nExperience Required:\n- 3+ years of backend development"
  );
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [result, setResult] = useState<AnalysisReport | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [feedback, setFeedback] = useState<CustomerFeedback[]>([]);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.removeItem("resumeiq-local-history");
      const raw = sessionStorage.getItem(HISTORY_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as HistoryItem[];
        const localReports = parsed.filter((item) => item.report?.plain_text);
        setHistory(localReports);
        sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(localReports));
      }
    } catch {
      setHistory([]);
    }

    listFeedback()
      .then(setFeedback)
      .catch((feedbackFetchError: unknown) => {
        setFeedbackError(
          feedbackFetchError instanceof Error
            ? feedbackFetchError.message
            : "Unable to load customer feedback.",
        );
      });
  }, []);

  const handleSubmitFeedback = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = feedbackMessage.trim();
    if (!message) return;

    setFeedbackLoading(true);
    setFeedbackError(null);
    try {
      const savedFeedback = await submitFeedback(message);
      setFeedback((current) => [savedFeedback, ...current].slice(0, 50));
      setFeedbackMessage("");
    } catch (feedbackSubmitError) {
      setFeedbackError(
        feedbackSubmitError instanceof Error
          ? feedbackSubmitError.message
          : "Unable to submit feedback.",
      );
    } finally {
      setFeedbackLoading(false);
    }
  };

  const scoreBadge = useMemo(() => {
    if (!result) {
      return { label: "No report", tone: "neutral" };
    }
    if (result.score === null) {
      return { label: "Needs review", tone: "warning" };
    }
    if (result.score >= 80) {
      return { label: "Strong match", tone: "good" };
    }
    if (result.score >= 50) {
      return { label: "Moderate match", tone: "neutral" };
    }
    return { label: "Low match", tone: "danger" };
  }, [result]);

  const requirementLabel = (status: string) => {
    const map: Record<string, string> = {
      matched: "Supported match",
      partially_supported: "Partial evidence",
      missing: "Missing evidence",
      uncertain: "Needs review",
      not_applicable: "Not assessed",
    };
    return map[status] ?? status;
  };

  const saveHistory = (report: AnalysisReport) => {
    const nextEntry: HistoryItem = {
      analysis_id: report.analysis_id ?? `${Date.now()}`,
      created_at: report.created_at ?? new Date().toISOString(),
      score: report.score,
      job_title: report.job_title,
      report,
    };

    setHistory((current) => {
      const next = [nextEntry, ...current.filter((item) => item.analysis_id !== nextEntry.analysis_id)];
      sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);

    try {
      let report: AnalysisReport;
      if (resumeFile) {
        const formData = new FormData();
        formData.append("resume_file", resumeFile);
        formData.append("job_description", jobDescription);
        report = await analyzeFile(formData);
      } else if (resumeText.trim()) {
        report = await analyzeText({
          resume_text: resumeText,
          job_description: jobDescription,
        });
      } else {
        throw new Error("Please upload a resume or paste resume text before analyzing.");
      }

      setResult(report);
      saveHistory(report);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenHistory = async (id: string) => {
    const item = history.find((entry) => entry.analysis_id === id);
    if (!item?.report?.plain_text) {
      setError("This saved report is unavailable in this browser.");
      return;
    }
    setError(null);
    setResult(item.report);
  };

  const handleDeleteHistory = (id: string) => {
    setHistory((current) => {
      const next = current.filter((item) => item.analysis_id !== id);
      sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const handleClearHistory = () => {
    setHistory([]);
    sessionStorage.removeItem(HISTORY_STORAGE_KEY);
  };

  const downloadText = () => {
    if (!result) return;
    const file = new Blob([result.plain_text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(file);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "resumeiq-report.txt";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadJson = () => {
    if (!result) return;
    const file = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(file);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "resumeiq-report.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-row">
            <div className="brand-mark">R</div>
            <div>
              <h1>ResumeIQ</h1>
            </div>
          </div>
          <p>Compare your resume with a job description and understand how well your documented experience, skills, and qualifications align with the role.</p>
        </div>
        <nav className="nav">
          <a href="#analyze">Analyze Resume</a>
          <a href="#history">History</a>
          <a href="#customer-feedback">Customer feedback</a>
        </nav>
      </header>

      <main className="page">
        <section className="hero card">
          <div>
            <span className="eyebrow">Transparent matching</span>
            <h2>Evidence-based resume scoring</h2>
            <p>
              The score measures documented alignment, not hiring probability or guaranteed employability.
            </p>
          </div>
        </section>

        <section id="analyze" className="workspace">
          <div className="panel card">
            <div className="panel-header">
              <h3>Resume upload</h3>
              <span className="file-size">Max 5 MB</span>
            </div>
            <label className="dropzone">
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)}
              />
              <span>{resumeFile ? resumeFile.name : "Drag & drop or choose a resume file"}</span>
            </label>
            {resumeFile && (
              <div className="meta-row">
                <span>{resumeFile.name}</span>
                <span>{(resumeFile.size / 1024 / 1024).toFixed(2)} MB</span>
                <button type="button" className="button secondary" onClick={() => setResumeFile(null)}>
                  Remove file
                </button>
              </div>
            )}

            <label className="field-label">Or paste resume text</label>
            <textarea
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste the resume text here if you do not want to upload a file."
            />
          </div>

          <div className="panel card">
            <div className="panel-header">
              <h3>Job description</h3>
            </div>
            <textarea
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the full job description here..."
            />
            <div className="actions-row">
              <button className="button primary" type="button" onClick={handleAnalyze} disabled={loading}>
                {loading ? "Analyzing..." : "Analyze Resume"}
              </button>
              <button type="button" className="button ghost" onClick={() => setJobDescription("")}>Clear</button>
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>
        </section>

        {result && (
          <section className="results card">
            <div className="result-header">
              <div>
                <span className="eyebrow">Analysis</span>
                <h3>{result.job_title ?? "Job title not detected"}</h3>
              </div>
              <div className={`score-badge ${scoreBadge.tone}`}>{formatScore(result.score)}</div>
            </div>

            <div className="result-summary">
              <div>
                <span>Analysis status</span>
                <strong>{result.score === null ? "needs review" : "complete"}</strong>
              </div>
              <div>
                <span>Match summary</span>
                <strong>{scoreBadge.label}</strong>
              </div>
              <div>
                <span>Score explanation</span>
                <strong>{result.scoring_note}</strong>
              </div>
            </div>

            <div className="stats-grid">
              <div className="stat-box">
                <span>Matched skills</span>
                <strong>{result.matched_skills.length}</strong>
              </div>
              <div className="stat-box">
                <span>Missing skills</span>
                <strong>{result.missing_skills.length}</strong>
              </div>
              <div className="stat-box">
                <span>Matched qualifications</span>
                <strong>{result.matched_qualifications.length}</strong>
              </div>
              <div className="stat-box">
                <span>Warnings</span>
                <strong>{result.warnings.length}</strong>
              </div>
            </div>

            <div className="categories-grid">
              {result.criteria.length > 0 ? (
                result.criteria.map((criterion) => (
                  <div key={criterion.name} className="criterion-card">
                    <div className="criterion-header">
                      <span>{criterion.name}</span>
                      <strong>{criterion.points.toFixed(1)} pts</strong>
                    </div>
                    <div className="criterion-bar">
                      <span style={{ width: `${Math.max(8, Math.min(100, criterion.coverage * 100))}%` }} />
                    </div>
                    <small>{criterion.detail}</small>
                  </div>
                ))
              ) : (
                <div className="criterion-card empty">
                  <span>No scoreable criteria were detected.</span>
                </div>
              )}
            </div>

            <div className="results-grid">
              <div>
                <h4>Required skills</h4>
                <ul>{result.required_skills.length ? result.required_skills.map((skill) => <li key={skill}>{skill}</li>) : <li>None detected</li>}</ul>
              </div>
              <div>
                <h4>Preferred skills</h4>
                <ul>{result.preferred_skills.length ? result.preferred_skills.map((skill) => <li key={skill}>{skill}</li>) : <li>None detected</li>}</ul>
              </div>
              <div>
                <h4>Resume strengths</h4>
                <ul>{result.matched_skills.length ? result.matched_skills.map((skill) => <li key={skill}>{skill}</li>) : <li>No confirmed strengths</li>}</ul>
              </div>
              <div>
                <h4>Missing evidence</h4>
                <ul>{result.missing_skills.length ? result.missing_skills.map((skill) => <li key={skill}>{skill}</li>) : <li>No missing skills recorded</li>}</ul>
              </div>
            </div>

            <div className="detail-panel">
              <h4>Requirement-by-requirement review</h4>
              <div className="requirement-table">
                {result.requirements.length ? (
                  result.requirements.map((requirement) => (
                    <div key={`${requirement.name}-${requirement.priority}`} className="requirement-row">
                      <div className="requirement-meta">
                        <strong>{requirement.name}</strong>
                        <span>{requirement.priority}</span>
                      </div>
                      <div className={`status-pill ${requirement.status}`}>
                        {requirementLabel(requirement.status)}
                      </div>
                      {evidenceTypeLabel(requirement.evidence_type) && (
                        <div className={`evidence-type-pill ${requirement.evidence_type}`}>
                          {evidenceTypeLabel(requirement.evidence_type)}
                        </div>
                      )}
                      <p>{requirement.reason}</p>
                      {requirement.evidence && <small>Evidence: “{requirement.evidence}”</small>}
                    </div>
                  ))
                ) : (
                  <p>No individual requirements were extracted.</p>
                )}
              </div>
            </div>

            <details className="collapse-box">
              <summary>What ResumeIQ extracted</summary>
              <div className="collapse-body">
                <div className="extracted-grid">
                  <div>
                    <h5>Detected job title</h5>
                    <p>{result.job_title ?? "Not detected"}</p>
                  </div>
                  <div>
                    <h5>Required skills</h5>
                    <p>{result.required_skills.length ? result.required_skills.join(", ") : "None detected"}</p>
                  </div>
                  <div>
                    <h5>Preferred skills</h5>
                    <p>{result.preferred_skills.length ? result.preferred_skills.join(", ") : "None detected"}</p>
                  </div>
                  <div>
                    <h5>Responsibilities</h5>
                    <p>{result.responsibilities.length ? result.responsibilities.join("; ") : "No responsibilities parsed"}</p>
                  </div>
                  <div>
                    <h5>Qualifications</h5>
                    <p>{result.required_qualifications.length ? result.required_qualifications.join(", ") : "No qualifications detected"}</p>
                  </div>
                  <div>
                    <h5>Extraction warnings</h5>
                    <p>{result.warnings.length ? result.warnings.join("; ") : "None"}</p>
                  </div>
                </div>
              </div>
            </details>

            <div className="recommendations">
              <h4>Actionable recommendations</h4>
              <ul>{result.improvements.length ? result.improvements.map((item) => <li key={item}>{item}</li>) : <li>No recommendations needed.</li>}</ul>
            </div>

            <div className="report-actions">
              <button type="button" className="button primary" onClick={downloadText}>Download TXT</button>
              <button type="button" className="button secondary" onClick={downloadJson}>Export JSON</button>
            </div>
          </section>
        )}

        <section className="community-grid">
          <section id="history" className="card history-panel">
          <div className="panel-header">
            <h3>History</h3>
            {history.length > 0 && (
              <button type="button" className="button ghost" onClick={handleClearHistory}>Clear history</button>
            )}
          </div>

          {history.length === 0 ? (
            <p className="empty-state">Saved reports appear here after you analyze a resume.</p>
          ) : (
            <ul className="history-list">
              {history.map((item) => (
                <li key={item.analysis_id} className="history-item">
                  <div>
                    <strong>{item.job_title ?? "Untitled analysis"}</strong>
                    <small>{new Date(item.created_at).toLocaleString()}</small>
                  </div>
                  <div className="history-meta">
                    <span>{formatScore(item.score)}</span>
                    <button type="button" className="button secondary" onClick={() => handleOpenHistory(item.analysis_id)}>Open</button>
                    <button type="button" className="button ghost" onClick={() => handleDeleteHistory(item.analysis_id)}>Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          </section>

          <section id="customer-feedback" className="card feedback-panel">
            <div className="panel-header">
              <div>
                <h3>Customer feedback</h3>
                <p className="feedback-note">
                  Shared with future visitors. Please do not include personal information.
                </p>
              </div>
            </div>
            <form className="feedback-form" onSubmit={handleSubmitFeedback}>
              <label className="field-label" htmlFor="customer-feedback-message">
                Leave feedback
              </label>
              <textarea
                id="customer-feedback-message"
                value={feedbackMessage}
                onChange={(event) => setFeedbackMessage(event.target.value)}
                maxLength={1000}
                placeholder="Tell others about your experience..."
                required
              />
              <div className="feedback-form-footer">
                <small>{feedbackMessage.length}/1000</small>
                <button
                  type="submit"
                  className="button primary"
                  disabled={feedbackLoading || !feedbackMessage.trim()}
                >
                  {feedbackLoading ? "Submitting..." : "Submit feedback"}
                </button>
              </div>
            </form>
            {feedbackError && <div className="error-box">{feedbackError}</div>}
            <div className="feedback-list" aria-live="polite">
              {feedback.length === 0 ? (
                <p className="empty-state">No customer feedback yet. Be the first to share.</p>
              ) : (
                feedback.map((entry) => (
                  <article key={entry.feedback_id} className="feedback-item">
                    <p>{entry.message}</p>
                    <small>{new Date(entry.created_at).toLocaleString()}</small>
                  </article>
                ))
              )}
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;

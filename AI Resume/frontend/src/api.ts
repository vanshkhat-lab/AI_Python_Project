import type {
  AnalysisReport,
  ClientFeedback,
  HistoryItem,
  ParsedJobDescription,
} from "./types";

interface ApiErrorBody {
  error?: {
    message?: string;
  };
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 120_000;

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function fetchApi(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(apiUrl(path), {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error("The request took too long. Please try again.");
    }
    if (error instanceof TypeError) {
      throw new Error("ResumeIQ could not reach the backend. Check that it is running, then retry.");
    }
    throw error;
  }
}

async function assertResponse(response: Response): Promise<void> {
  if (response.ok) return;
  let message = `Request failed (${response.status}).`;
  try {
    const payload = (await response.json()) as ApiErrorBody;
    if (payload.error?.message) message = payload.error.message;
  } catch {
    // Retain the status message when an intermediary returned non-JSON content.
  }
  throw new Error(message);
}

async function responseJson<T>(response: Response): Promise<T> {
  await assertResponse(response);
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("The backend returned an invalid response. Please try again.");
  }
}

function isAnalysisReport(value: unknown): value is AnalysisReport {
  if (!value || typeof value !== "object") return false;
  const report = value as Partial<AnalysisReport>;
  return (
    (report.score === null || typeof report.score === "number") &&
    Array.isArray(report.requirements) &&
    Array.isArray(report.criteria) &&
    Array.isArray(report.warnings) &&
    Array.isArray(report.responsibilities) &&
    typeof report.plain_text === "string" &&
    typeof report.scoring_note === "string"
  );
}

export async function analyzeDocuments(
  resume: File,
  jobDescription: string,
  jobFile?: File,
  generateAiRecommendations = false,
  saveAnalysis = false,
): Promise<AnalysisReport> {
  const formData = new FormData();
  formData.append("resume_file", resume);
  formData.append("job_description", jobDescription);
  formData.append("generate_ai_recommendations", String(generateAiRecommendations));
  formData.append("save_analysis", String(saveAnalysis));
  if (jobFile) formData.append("job_file", jobFile);
  const response = await fetchApi("/api/analyze", {
    method: "POST",
    body: formData,
  });
  const result: unknown = await responseJson(response);
  if (!isAnalysisReport(result)) {
    throw new Error("The backend returned an incomplete analysis. Please try again.");
  }
  return result;
}

export async function parseJobDescription(text: string): Promise<ParsedJobDescription> {
  const result: unknown = await responseJson(
    await fetchApi("/api/job-descriptions/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  );
  if (
    !result ||
    typeof result !== "object" ||
    !Array.isArray((result as ParsedJobDescription).requirements) ||
    !Array.isArray((result as ParsedJobDescription).warnings)
  ) {
    throw new Error("The backend returned an invalid job description summary.");
  }
  return result as ParsedJobDescription;
}

export async function getHistory(): Promise<HistoryItem[]> {
  const result: unknown = await responseJson(await fetchApi("/api/analyses"));
  if (
    !Array.isArray(result) ||
    !result.every(
      (item) =>
        item &&
        typeof item === "object" &&
        typeof (item as HistoryItem).analysis_id === "string" &&
        typeof (item as HistoryItem).created_at === "string",
    )
  ) {
    throw new Error("The backend returned invalid saved analysis history.");
  }
  return result as HistoryItem[];
}

function isClientFeedback(value: unknown): value is ClientFeedback {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ClientFeedback>;
  return (
    typeof item.feedback_id === "string" &&
    typeof item.message === "string" &&
    typeof item.created_at === "string"
  );
}

export async function getFeedback(): Promise<ClientFeedback[]> {
  const result: unknown = await responseJson(await fetchApi("/api/feedback"));
  if (!Array.isArray(result) || !result.every(isClientFeedback)) {
    throw new Error("The backend returned invalid client feedback.");
  }
  return result;
}

export async function submitFeedback(message: string): Promise<ClientFeedback> {
  const result: unknown = await responseJson(
    await fetchApi("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),
  );
  if (!isClientFeedback(result)) {
    throw new Error("The backend returned invalid feedback confirmation.");
  }
  return result;
}

export async function getAnalysis(id: string): Promise<AnalysisReport> {
  const result: unknown = await responseJson(
    await fetchApi(`/api/analyses/${encodeURIComponent(id)}`),
  );
  if (!isAnalysisReport(result)) {
    throw new Error("The backend returned an incomplete saved analysis.");
  }
  return result;
}

export async function deleteHistoryItem(id: string): Promise<void> {
  const response = await fetchApi(`/api/analyses/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  await assertResponse(response);
}

export async function downloadTextReport(report: AnalysisReport): Promise<void> {
  const blob = new Blob([report.plain_text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "resumeiq-analysis.txt";
  link.click();
  URL.revokeObjectURL(url);
}

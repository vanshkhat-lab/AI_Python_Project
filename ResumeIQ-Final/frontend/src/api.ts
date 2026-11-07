import type { AnalysisReport, CustomerFeedback } from "./types";

const API_BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload?.error?.message ?? "The request could not be completed.";
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function healthCheck() {
  return request<{ status: string; version: string; ai_recommendations: boolean }>("/health");
}

export async function listFeedback(): Promise<CustomerFeedback[]> {
  return request("/feedback");
}

export async function submitFeedback(message: string): Promise<CustomerFeedback> {
  return request("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export async function analyzeText(payload: {
  resume_text: string;
  job_description: string;
  save_analysis?: boolean;
  generate_ai_recommendations?: boolean;
}): Promise<AnalysisReport> {
  return request<AnalysisReport>("/analyze/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function analyzeFile(payload: FormData): Promise<AnalysisReport> {
  return request<AnalysisReport>("/analyze", {
    method: "POST",
    body: payload,
  });
}

export async function listAnalyses(): Promise<Array<{ analysis_id: string; created_at: string; score: number | null; job_title: string | null }>> {
  return request("/analyses");
}

export async function getAnalysis(id: string): Promise<AnalysisReport> {
  return request<AnalysisReport>(`/analyses/${id}`);
}

export async function deleteAnalysis(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/analyses/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Could not delete the saved analysis.");
  }
}

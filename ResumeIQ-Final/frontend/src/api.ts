import { supabase } from "./supabase";
import type { AnalysisReport, CustomerFeedback } from "./types";

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const API_BASE = `${API_ORIGIN}/api`;

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const {
    data: { session },
    error: authError,
  } = await supabase.auth.getSession();

  if (authError || !session?.access_token) {
    throw new Error("Please log in to continue.");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers ?? {}),
      Authorization: `Bearer ${session.access_token}`,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));

    const message =
      payload?.error?.message ??
      (typeof payload?.detail === "string"
        ? payload.detail
        : "The request could not be completed.");

    throw new Error(message);
  }

  const data = (await response.json()) as T;
  if (path === "/analyze" || path === "/analyze/text") {
    window.dispatchEvent(new Event("resumeiq:credits-changed"));
  }
  return data;
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

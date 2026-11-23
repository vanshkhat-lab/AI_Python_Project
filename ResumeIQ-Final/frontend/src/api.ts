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

export interface PaymentConfiguration {
  mode: "test" | "live";
  enabled: boolean;
}

// This endpoint returns public payment readiness data; it contains no credentials.
export async function getPaymentConfiguration(): Promise<PaymentConfiguration> {
  const response = await fetch(`${API_BASE}/payments/config`);
  if (!response.ok) throw new Error("Payment status is currently unavailable.");
  const data = (await response.json()) as PaymentConfiguration;
  if (!["test", "live"].includes(data.mode) || typeof data.enabled !== "boolean") {
    throw new Error("Invalid payment configuration.");
  }
  return data;
}

export interface RazorpayCreditOrder {
  key_id: string;
  order_id: string;
  amount: number;
  currency: string;
  credits: number;
  mode: "test" | "live";
}

export async function createCreditOrder(): Promise<RazorpayCreditOrder> {
  return request<RazorpayCreditOrder>("/payments/create-order", { method: "POST" });
}

export async function verifyCreditPayment(payload: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}): Promise<{ status: string; credits_added: number; already_processed: boolean }> {
  const result = await request<{ status: string; credits_added: number; already_processed: boolean }>(
    "/payments/verify",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  window.dispatchEvent(new Event("resumeiq:credits-changed"));
  return result;
}

export async function checkCreditPayment(orderId: string): Promise<{
  status: string;
  credits: number;
}> {
  const result = await request<{ status: string; credits: number }>(
    `/payments/orders/${encodeURIComponent(orderId)}`,
  );
  if (result.status === "paid") {
    window.dispatchEvent(new Event("resumeiq:credits-changed"));
  }
  return result;
}


// Staging test-mode refund utility. No customer secrets are exposed to the browser.
export async function refundLatestUnusedTestPack(): Promise<{
  status: string;
  refund_id?: string | null;
  reason?: string;
}> {
  const { data: purchases, error } = await supabase
    .from("credit_purchases")
    .select("razorpay_order_id,status,credits_available")
    .eq("payment_mode", "test")
    .in("status", ["paid", "refund_pending", "refunded"])
    .order("paid_at", { ascending: false })
    .limit(10);

  if (error) throw new Error("Could not look up the test purchase.");
  const purchase = purchases?.find(
    item => item.status === "refund_pending"
      || (item.status === "paid" && item.credits_available === 5)
  ) ?? purchases?.find(item => item.status === "refunded");
  if (!purchase) return { status: "not_found" };
  const orderId = purchase.razorpay_order_id as string;
  const path = `/payments/refunds/${encodeURIComponent(orderId)}`;
  const result = await request<{
    status: string; refund_id?: string | null; reason?: string
  }>(path, { method: purchase.status === "paid" ? "POST" : "GET" });
  window.dispatchEvent(new Event("resumeiq:credits-changed"));
  return result;
}

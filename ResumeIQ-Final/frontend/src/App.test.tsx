import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { healthCheck, listAnalyses, listFeedback, submitFeedback } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  analyzeFile: vi.fn(),
  analyzeText: vi.fn(),
  deleteAnalysis: vi.fn(),
  getAnalysis: vi.fn(),
  healthCheck: vi.fn(),
  listAnalyses: vi.fn(),
  listFeedback: vi.fn(),
  submitFeedback: vi.fn(),
}));

describe("ResumeIQ app", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(healthCheck).mockResolvedValue({
      status: "ok",
      version: "1.0.0",
      ai_recommendations: false,
    });
    vi.mocked(listAnalyses).mockResolvedValue([]);
    vi.mocked(listFeedback).mockResolvedValue([]);
    vi.mocked(submitFeedback).mockReset();
  });

  it("renders the app title and description", () => {
    render(<App />);

    expect(screen.getByText("ResumeIQ")).toBeInTheDocument();
    expect(screen.getByText(/Compare your resume with a job description/i)).toBeInTheDocument();
    expect(screen.queryByText("API status")).not.toBeInTheDocument();
    expect(listAnalyses).not.toHaveBeenCalled();
  });

  it("shows only locally stored history and does not request shared server history", async () => {
    sessionStorage.setItem(
      "resumeiq-session-history",
      JSON.stringify([
        {
          analysis_id: "browser-only-report",
          created_at: "2026-11-04T10:00:00Z",
          score: 75,
          job_title: "Private local report",
          report: { plain_text: "Saved in this browser" },
        },
      ]),
    );

    render(<App />);

    expect(await screen.findByText("Private local report")).toBeInTheDocument();
    expect(listAnalyses).not.toHaveBeenCalled();
  });

  it("shows previous feedback and shares newly submitted feedback", async () => {
    vi.mocked(listFeedback).mockResolvedValue([
      {
        feedback_id: "previous-feedback",
        message: "The report is easy to understand.",
        created_at: "2026-11-04T10:00:00Z",
      },
    ]);
    vi.mocked(submitFeedback).mockResolvedValue({
      feedback_id: "new-feedback",
      message: "Helpful and clear.",
      created_at: "2026-11-04T11:00:00Z",
    });

    render(<App />);
    expect(await screen.findByText("The report is easy to understand.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Leave feedback"), {
      target: { value: "Helpful and clear." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith("Helpful and clear.");
      expect(screen.getByText("Helpful and clear.")).toBeInTheDocument();
    });
  });
});

import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const report = {
  score: 75,
  required_skills: ["Python"],
  preferred_skills: ["Docker"],
  matched_skills: ["Python"],
  partial_skills: [],
  missing_skills: [],
  uncertain_skills: [],
  experience: {
    required_years: 3,
    candidate_years: 4,
    summary: "The resume states 4 years.",
  },
  required_qualifications: [],
  preferred_qualifications: [],
  matched_qualifications: [],
  missing_qualifications: [],
  uncertain_qualifications: [],
  requirements: [
    {
      name: "Python",
      category: "skill",
      priority: "required",
      status: "matched",
      evidence: "Built Python services.",
      section: "experience",
      reason: "The resume includes contextual evidence supporting this requirement.",
      confidence: "high",
    },
  ],
  relevant_experience: ["Built Python services."],
  improvements: ["Keep examples specific."],
  criteria: [
    {
      name: "Python",
      weight: 2,
      effective_weight: 1,
      coverage: 1,
      points: 100,
      detail: "Required requirement: matched",
    },
  ],
  scoring_note: "Transparent scoring.",
  job_title: "Software Engineer",
  responsibilities: [],
  warnings: [],
  plain_text: "ResumeIQ report",
  analysis_id: null,
  created_at: null,
  ai_recommendations: [],
  ai_status: "not_configured",
};

function mockJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response;
}

function mockApiResponses(
  ...responses: Array<Response | (() => Promise<Response>)>
) {
  const pending = [...responses];
  vi.mocked(fetch).mockImplementation((input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/feedback") && method === "GET") {
      return Promise.resolve(mockJsonResponse([]));
    }
    const next = pending.shift();
    return typeof next === "function"
      ? next()
      : Promise.resolve(next ?? mockJsonResponse({}));
  });
}

function resumeInput(): HTMLInputElement {
  const input = document.querySelector<HTMLInputElement>("#resume-upload");
  if (!input) throw new Error("Resume upload input was not rendered.");
  return input;
}

describe("ResumeIQ dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockJsonResponse([])));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows the chosen resume filename and allows replacing it", async () => {
    const user = userEvent.setup();
    render(<App />);
    const input = resumeInput();
    const first = new File(["resume"], "first-resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await user.upload(input, first);
    expect(screen.getByText("first-resume.docx")).toBeInTheDocument();

    const replacement = new File(["resume"], "updated-resume.pdf", {
      type: "application/pdf",
    });
    await user.upload(input, replacement);
    expect(screen.getByText("updated-resume.pdf")).toBeInTheDocument();
  });

  it("shows the selected job description filename", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.upload(
      document.querySelector<HTMLInputElement>("#job-upload")!,
      new File(["Python required"], "role-description.txt", { type: "text/plain" }),
    );
    expect(screen.getByText("role-description.txt")).toBeInTheDocument();
    expect(screen.getByText(/will be used instead of pasted text/)).toBeInTheDocument();
  });

  it("validates unsupported files before making a request", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["bad"], "resume.rtf", { type: "application/rtf" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Unsupported file type");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("rejects files larger than the 5 MB limit before upload", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.upload(
      resumeInput(),
      new File([new Uint8Array(5 * 1024 * 1024 + 1)], "large-resume.pdf", {
        type: "application/pdf",
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("5 MB or smaller");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("validates the job description before submit", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("Paste a job description");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("shows loading and renders real API results", async () => {
    const user = userEvent.setup();
    let resolveFetch!: (value: Response) => void;
    mockApiResponses(
      () => new Promise<Response>((resolve) => { resolveFetch = resolve; }),
    );
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "Python required.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    expect(screen.getByRole("status")).toHaveTextContent("Extracting document text");
    resolveFetch(mockJsonResponse(report));
    expect(await screen.findByText("Here’s where you stand.")).toBeInTheDocument();
    expect(screen.getAllByText("Built Python services.")).toHaveLength(2);
  });

  it("shows API errors to the user", async () => {
    const user = userEvent.setup();
    mockApiResponses(
      mockJsonResponse({ error: { code: "request_error", message: "Corrupt PDF." } }, 400),
    );
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "Python required.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Corrupt PDF.");
  });

  it("shows experience and qualification requirements in their report section", async () => {
    const user = userEvent.setup();
    mockApiResponses(
      mockJsonResponse({
        ...report,
        experience: {
          required_years: 5,
          candidate_years: 3,
          summary: "The job description asks for 5 years; the resume explicitly states 3 years.",
        },
        requirements: [
          ...report.requirements,
          {
            name: "5 years of experience",
            category: "experience",
            priority: "required",
            status: "partially_supported",
            evidence: "Software developer with 3 years of experience.",
            section: "experience",
            reason: "The resume states some experience, but less than the stated requirement.",
            confidence: "high",
          },
          {
            name: "Bachelor's degree",
            category: "qualification",
            priority: "preferred",
            status: "missing",
            evidence: null,
            section: null,
            reason: "No supporting evidence was found in the extracted resume text.",
            confidence: "medium",
          },
        ],
      }),
    );
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "5 years of experience preferred.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));

    const experienceCard = screen.getByRole("heading", { name: "Experience & qualifications" }).closest("article");
    expect(experienceCard).not.toBeNull();
    expect(within(experienceCard!).getByText("Experience requirements")).toBeInTheDocument();
    expect(within(experienceCard!).getByText("5 years of experience")).toBeInTheDocument();
    expect(within(experienceCard!).getByText("Bachelor's degree")).toBeInTheDocument();
    expect(within(experienceCard!).getByText("Software developer with 3 years of experience.")).toBeInTheDocument();
  });

  it("does not present a zero score when no reliable requirements were found", async () => {
    const user = userEvent.setup();
    mockApiResponses(
      mockJsonResponse({
        ...report,
        score: null,
        requirements: [],
        criteria: [],
        warnings: ["No reliable requirements were detected."],
      }),
    );
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "A thoughtful person.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    expect(await screen.findByText("—")).toBeInTheDocument();
    expect(screen.getByText(/Unable to calculate a score/)).toBeInTheDocument();
  });

  it("reviews parsed requirements before analysis", async () => {
    const user = userEvent.setup();
    mockApiResponses(
      mockJsonResponse({
        job_title: "Senior Engineer",
        requirements: [{ name: "Python", category: "skill", priority: "required" }],
        responsibilities: [],
        warnings: [],
      }),
    );
    render(<App />);
    await user.type(screen.getByLabelText(/Job description/), "Senior Engineer. Python required.");
    await user.click(screen.getByRole("button", { name: "Review detected requirements" }));
    expect(await screen.findByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText("Python · required")).toBeInTheDocument();
  });

  it("displays an AI warning and lets the user retry recommendations", async () => {
    const user = userEvent.setup();
    const unavailable = { ...report, ai_status: "unavailable" };
    const available = {
      ...report,
      ai_status: "available",
      ai_recommendations: [
        {
          recommendation_type: "wording",
          original_resume_text_reference: "Built Python services.",
          suggestion: "Emphasize Python services in your bullet.",
          explanation: "Clarify the Python services in the cited wording.",
          evidence_quote: "Built Python services.",
          introduces_new_claim: false,
        },
      ],
    };
    mockApiResponses(mockJsonResponse(unavailable), mockJsonResponse(available));
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "Python required.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    await screen.findByText("Optional AI suggestions were unavailable; deterministic analysis is unaffected.");
    await user.click(screen.getByRole("button", { name: "Retry AI recommendations" }));
    expect(await screen.findByText("Emphasize Python services in your bullet.")).toBeInTheDocument();
  });

  it("saves explicitly and reveals a PDF download link", async () => {
    const user = userEvent.setup();
    mockApiResponses(
      mockJsonResponse(report),
      mockJsonResponse({ ...report, analysis_id: "saved-123" }),
      mockJsonResponse([]),
    );
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "Python required.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    await screen.findByText("Here’s where you stand.");
    await user.click(screen.getByRole("button", { name: /save analysis/i }));
    expect(await screen.findByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      "/api/analyses/saved-123/report",
    );
    expect(fetch).toHaveBeenCalledTimes(4);
  });

  it("clears the form when starting a new analysis", async () => {
    const user = userEvent.setup();
    mockApiResponses(mockJsonResponse(report));
    render(<App />);
    await user.upload(
      resumeInput(),
      new File(["resume"], "resume.pdf", { type: "application/pdf" }),
    );
    await user.type(screen.getByLabelText(/Job description/), "Python required.");
    await user.click(screen.getByRole("button", { name: /analyze my match/i }));
    await screen.findByText("Here’s where you stand.");
    await user.click(screen.getByRole("button", { name: "New analysis" }));
    expect(screen.queryByText("Here’s where you stand.")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Job description/)).toHaveValue("");
  });

  it("opens a saved result from history", async () => {
    const user = userEvent.setup();
    mockApiResponses(
        mockJsonResponse([
          {
            analysis_id: "saved-abc",
            created_at: "2026-02-01T12:00:00Z",
            score: 75,
            job_title: "Software Engineer",
          },
        ]),
      mockJsonResponse({ ...report, analysis_id: "saved-abc" }),
    );
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Saved analyses" }));
    await user.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByText("Here’s where you stand.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      "/api/analyses/saved-abc/report",
    );
  });

  it("asks for confirmation before deleting a history item", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    mockApiResponses(
        mockJsonResponse([
          {
            analysis_id: "saved-delete",
            created_at: "2026-02-01T12:00:00Z",
            score: 70,
            job_title: null,
          },
        ]),
      mockJsonResponse(undefined, 204),
      mockJsonResponse([]),
    );
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Saved analyses" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    expect(fetch).toHaveBeenCalledTimes(2);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(fetch).toHaveBeenCalledTimes(4);
    expect(await screen.findByText("No saved analyses yet.")).toBeInTheDocument();
  });

  it("saves feedback and displays it again on the next visit", async () => {
    const user = userEvent.setup();
    const savedFeedback = {
      feedback_id: "feedback-123",
      message: "The evidence explanations made the score easy to understand.",
      created_at: "2026-10-19T08:00:00Z",
    };
    let persisted: typeof savedFeedback[] = [];
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/feedback") && method === "GET") {
        return mockJsonResponse(persisted);
      }
      if (url.endsWith("/api/feedback") && method === "POST") {
        persisted = [savedFeedback, ...persisted];
        return mockJsonResponse(savedFeedback, 201);
      }
      return mockJsonResponse({});
    });

    const { unmount } = render(<App />);
    await user.type(
      screen.getByLabelText("Your feedback"),
      savedFeedback.message,
    );
    await user.click(screen.getByRole("button", { name: "Submit feedback" }));
    expect(await screen.findByText(savedFeedback.message)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Your feedback is saved");

    unmount();
    render(<App />);
    expect(await screen.findByText(savedFeedback.message)).toBeInTheDocument();
  });
});

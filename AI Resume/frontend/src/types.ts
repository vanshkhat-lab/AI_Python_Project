export type RequirementStatus =
  | "matched"
  | "partially_supported"
  | "missing"
  | "uncertain";

export interface RequirementEvidence {
  name: string;
  category: "skill" | "qualification" | "experience";
  priority: "required" | "preferred";
  status: RequirementStatus;
  evidence: string | null;
  section: string | null;
  reason: string;
  confidence: "high" | "medium" | "low";
}

export interface AIRecommendation {
  recommendation_type: "wording" | "keyword" | "gap";
  original_resume_text_reference: string | null;
  suggestion: string;
  explanation: string;
  evidence_quote: string;
  introduces_new_claim: boolean | null;
}

export interface ScoringCriterion {
  name: string;
  weight: number;
  effective_weight: number;
  coverage: number;
  points: number;
  detail: string;
}

export interface AnalysisReport {
  score: number | null;
  required_skills: string[];
  preferred_skills: string[];
  matched_skills: string[];
  partial_skills: string[];
  missing_skills: string[];
  uncertain_skills: string[];
  experience: {
    required_years: number | null;
    candidate_years: number | null;
    summary: string;
  };
  required_qualifications: string[];
  preferred_qualifications: string[];
  matched_qualifications: string[];
  missing_qualifications: string[];
  uncertain_qualifications: string[];
  requirements: RequirementEvidence[];
  relevant_experience: string[];
  improvements: string[];
  criteria: ScoringCriterion[];
  scoring_note: string;
  job_title: string | null;
  responsibilities: string[];
  warnings: string[];
  plain_text: string;
  analysis_id: string | null;
  created_at: string | null;
  ai_recommendations: AIRecommendation[];
  ai_status: "not_configured" | "not_requested" | "available" | "unavailable";
}

export interface HistoryItem {
  analysis_id: string;
  created_at: string;
  score: number | null;
  job_title: string | null;
}

export interface ParsedJobDescription {
  job_title: string | null;
  requirements: Array<{
    name: string;
    category: "skill" | "qualification" | "experience";
    priority: "required" | "preferred";
  }>;
  responsibilities: string[];
  warnings: string[];
}

export interface ClientFeedback {
  feedback_id: string;
  message: string;
  created_at: string;
}

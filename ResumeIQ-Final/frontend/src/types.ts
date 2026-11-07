export type RequirementStatus =
  | "matched"
  | "partially_supported"
  | "missing"
  | "uncertain"
  | "not_applicable";

export type Priority = "required" | "preferred" | "optional";

export interface RequirementEvidence {
  name: string;
  category: "skill" | "qualification" | "experience";
  priority: Priority;
  status: RequirementStatus;
  evidence_type: "demonstrated" | "explicitly_listed" | "partial" | "uncertain" | "missing" | null;
  evidence: string | null;
  section: string | null;
  reason: string;
  confidence: "high" | "medium" | "low";
  minimum_years: number | null;
  maximum_years: number | null;
  original_text: string | null;
}

export interface ScoringCriterion {
  name: string;
  weight: number;
  effective_weight: number;
  coverage: number;
  points: number;
  detail: string;
}

export interface ExperienceReport {
  required_years: number | null;
  candidate_years: number | null;
  summary: string;
  required_max_years: number | null;
  original_requirement: string | null;
}

export interface AnalysisReport {
  score: number | null;
  required_skills: string[];
  preferred_skills: string[];
  matched_skills: string[];
  partial_skills: string[];
  missing_skills: string[];
  uncertain_skills: string[];
  experience: ExperienceReport;
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
  optional_responsibilities: string[];
  warnings: string[];
  plain_text: string;
  analysis_id: string | null;
  created_at: string | null;
  ai_status: "not_configured" | "not_requested" | "available" | "unavailable";
  ai_recommendations: Array<{
    suggestion: string;
    evidence_quote: string;
    recommendation_type: string;
    explanation: string;
  }>;
}

export interface HistoryItem {
  analysis_id: string;
  created_at: string;
  score: number | null;
  job_title: string | null;
  report: AnalysisReport;
}

export interface CustomerFeedback {
  feedback_id: string;
  message: string;
  created_at: string;
}

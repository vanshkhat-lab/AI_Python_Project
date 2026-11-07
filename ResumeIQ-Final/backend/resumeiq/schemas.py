from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.resumeiq.config import MAX_TEXT_LENGTH


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    version: str
    ai_recommendations: bool


class TextAnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resume_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    job_description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    save_analysis: bool = False
    generate_ai_recommendations: bool = False


class JobDescriptionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class ParsedJobRequirement(BaseModel):
    name: str
    category: Literal["skill", "qualification", "experience", "responsibility"]
    priority: Literal["required", "preferred", "optional"]
    minimum_years: float | None = None
    maximum_years: float | None = None
    original_text: str | None = None


class JobDescriptionResponse(BaseModel):
    job_title: str | None
    requirements: list[ParsedJobRequirement]
    responsibilities: list[str]
    optional_responsibilities: list[str] = Field(default_factory=list)
    warnings: list[str]


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=1000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    message: str
    created_at: datetime


class ExperienceReport(BaseModel):
    required_years: float | None
    candidate_years: float | None
    summary: str
    required_max_years: float | None = None
    original_requirement: str | None = None


class ScoringCriterion(BaseModel):
    name: str
    weight: float
    effective_weight: float
    coverage: float
    points: float
    detail: str


class RequirementEvidence(BaseModel):
    name: str
    category: Literal["skill", "qualification", "experience"]
    priority: Literal["required", "preferred", "optional"]
    status: Literal["matched", "partially_supported", "missing", "uncertain", "not_applicable"]
    evidence_type: Literal[
        "demonstrated", "explicitly_listed", "partial", "uncertain", "missing"
    ] | None = None
    evidence: str | None
    section: str | None
    reason: str = "Reason not available for this saved analysis."
    confidence: Literal["high", "medium", "low"] = "low"
    minimum_years: float | None = None
    maximum_years: float | None = None
    original_text: str | None = None


class AIRecommendation(BaseModel):
    recommendation_type: Literal["wording", "keyword", "gap"] = "wording"
    original_resume_text_reference: str | None = None
    suggestion: str
    explanation: str = "Review this saved suggestion against the original resume."
    evidence_quote: str
    introduces_new_claim: bool | None = None


class AnalysisReport(BaseModel):
    score: int | None
    required_skills: list[str]
    preferred_skills: list[str]
    matched_skills: list[str]
    partial_skills: list[str]
    missing_skills: list[str]
    uncertain_skills: list[str]
    experience: ExperienceReport
    required_qualifications: list[str]
    preferred_qualifications: list[str]
    matched_qualifications: list[str]
    missing_qualifications: list[str]
    uncertain_qualifications: list[str]
    requirements: list[RequirementEvidence]
    relevant_experience: list[str]
    improvements: list[str]
    criteria: list[ScoringCriterion]
    scoring_note: str
    job_title: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    optional_responsibilities: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    plain_text: str
    analysis_id: str | None = None
    created_at: str | None = None
    ai_recommendations: list[AIRecommendation] = Field(default_factory=list)
    ai_status: Literal["not_configured", "not_requested", "available", "unavailable"] = (
        "not_configured"
    )


class AnalysisHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    report: AnalysisReport

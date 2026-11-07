from __future__ import annotations

from typing import Any, Literal, TypedDict

from backend.resumeiq.services.job_parser import (
    ParsedExperienceRequirement,
    parse_job_description,
)
from resume_analyzer.analyzer import (
    analyze_resume as _analyze_resume,
)
from resume_analyzer.analyzer import (
    candidate_experience,
)

_CREDIT = {
    "matched": 1.0,
    "partially_supported": 0.5,
    "missing": 0.0,
    "uncertain": 0.0,
}

RequirementStatus = Literal[
    "matched", "partially_supported", "missing", "uncertain", "not_applicable"
]
RequirementPriority = Literal["required", "preferred", "optional"]
Confidence = Literal["high", "medium", "low"]
EvidenceType = Literal["demonstrated", "explicitly_listed", "partial", "uncertain", "missing"]


class _Requirement(TypedDict):
    name: str
    category: Literal["skill", "qualification", "experience"]
    priority: RequirementPriority
    status: RequirementStatus
    evidence_type: EvidenceType | None
    evidence: str | None
    section: str | None
    reason: str
    confidence: Confidence
    minimum_years: float | None
    maximum_years: float | None
    original_text: str | None


class _Criterion(TypedDict):
    name: str
    weight: int
    effective_weight: float
    coverage: float
    points: float
    detail: str


def _experience_requirement(
    data: dict[str, Any],
    parsed_requirement: ParsedExperienceRequirement,
    candidate_evidence: str | None,
) -> _Requirement:
    candidate = data["experience"]["candidate_years"]
    minimum = parsed_requirement["minimum_years"]
    maximum = parsed_requirement["maximum_years"]
    priority: RequirementPriority = parsed_requirement["priority"]
    if minimum == 0:
        status: RequirementStatus = "not_applicable"
        evidence_type: EvidenceType | None = None
        reason = (
            "The range has no minimum; its upper bound is not an exact requirement "
            "or a duration to claim."
        )
        confidence: Confidence = "high"
    elif candidate is None:
        status: RequirementStatus = "uncertain"
        evidence_type = "uncertain"
        reason = "No explicit total in years was found; role dates are not used to infer duration."
        confidence: Confidence = "low"
    elif candidate >= minimum:
        status = "matched"
        evidence_type = "demonstrated"
        reason = (
            "The resume explicitly states experience meeting the minimum; the range "
            "maximum is not treated as an exact requirement."
        )
        confidence = "high"
    elif candidate > 0:
        status = "partially_supported"
        evidence_type = "partial"
        reason = "The resume states some experience, but less than the stated minimum."
        confidence = "high"
    else:
        status = "missing"
        evidence_type = "missing"
        reason = "The resume explicitly states no experience against a positive minimum."
        confidence = "medium"
    return {
        "name": parsed_requirement["name"],
        "category": "experience",
        "priority": priority,
        "status": status,
        "evidence_type": evidence_type,
        "evidence": candidate_evidence if status != "not_applicable" else None,
        "section": "experience" if candidate_evidence else None,
        "reason": reason,
        "confidence": confidence,
        "minimum_years": minimum,
        "maximum_years": maximum,
        "original_text": parsed_requirement["original_text"],
    }


def _score_requirements(
    requirements: list[_Requirement],
) -> tuple[int | None, list[_Criterion]]:
    scoreable = [
        item
        for item in requirements
        if item["priority"] != "optional" and item["status"] != "not_applicable"
    ]
    if not scoreable:
        return None, []
    total_weight = sum(2 if item["priority"] == "required" else 1 for item in scoreable)
    criteria: list[_Criterion] = []
    for item in scoreable:
        weight = 2 if item["priority"] == "required" else 1
        effective_weight = weight / total_weight
        credit = _CREDIT[item["status"]]
        criteria.append(
            {
                "name": item["name"],
                "weight": weight,
                "effective_weight": effective_weight,
                "coverage": credit,
                "points": 100 * effective_weight * credit,
                "detail": (
                    f"{item['priority'].title()} requirement: "
                    f"{item['status'].replace('_', ' ')}"
                    + (
                        "; uncertain evidence receives no score credit"
                        if item["status"] == "uncertain"
                        else ""
                    )
                ),
            }
        )
    score = int(sum(item["points"] for item in criteria) + 0.5)
    return max(0, min(100, score)), criteria


def _plain_text(data: dict[str, Any]) -> str:
    score = (
        f"Transparent match score: {data['score']} / 100"
        if data["score"] is not None
        else "Match score: Unable to calculate"
    )
    lines = [
        "RESUME MATCH ANALYSIS",
        score,
        "This deterministic document comparison is not a hiring probability or guarantee.",
        "",
        "REQUIREMENTS",
    ]
    for item in data["requirements"]:
        evidence = f" Evidence: {item['evidence']}" if item["evidence"] else ""
        evidence_type = (
            f"; evidence type: {item['evidence_type'].replace('_', ' ')}"
            if item["evidence_type"]
            else ""
        )
        lines.append(
            f"- {item['name']} ({item['priority']}, {item['status']}{evidence_type}): "
            f"{item['reason']}{evidence}"
        )
    lines.extend(("", "RELEVANT RESUME EVIDENCE"))
    lines.extend(f"- {snippet}" for snippet in data["relevant_experience"])
    lines.extend(("", "ROLE RESPONSIBILITIES (NOT CANDIDATE EVIDENCE)"))
    lines.extend(f"- {item}" for item in data["responsibilities"])
    lines.extend(f"- Optional: {item}" for item in data["optional_responsibilities"])
    lines.extend(("", "SUGGESTED NEXT STEPS"))
    lines.extend(f"- {suggestion}" for suggestion in data["improvements"])
    lines.extend(("", "SCORING BREAKDOWN"))
    if data["criteria"]:
        lines.extend(
            f"- {item['name']}: weight {item['weight']}, {item['points']:.1f} points "
            f"({item['coverage']:.0%} credit)"
            for item in data["criteria"]
        )
    else:
        lines.append(
            "No scoreable requirements were detected, so no meaningful score "
            "could be calculated; optional requirements and zero-minimum "
            "experience ranges do not contribute."
        )
    return "\n".join(lines) + "\n"


def _improvements(
    requirements: list[_Requirement],
) -> list[str]:
    suggestions: list[str] = []
    for item in requirements:
        if item["priority"] == "optional" or item["status"] == "not_applicable":
            continue
        if item["status"] == "missing":
            if item["category"] == "experience":
                maximum = item["maximum_years"]
                minimum = item["minimum_years"]
                maximum_note = (
                    f" The listed maximum of {maximum:g} years is not a target to claim."
                    if maximum is not None and minimum is not None and maximum > minimum
                    else ""
                )
                suggestions.append(
                    "If you have relevant professional, internship, training, or "
                    "project experience, describe its type and actual duration "
                    f"accurately; do not claim unsupported years.{maximum_note}"
                )
            elif item["category"] == "qualification":
                if item["name"].startswith("Relevant coursework"):
                    course_field = item["name"].partition(" in ")[2]
                    suggestion = (
                        f"If completed, list coursework in {course_field or 'the relevant field'} "
                        "under Education; otherwise, do not imply it."
                    )
                else:
                    suggestion = (
                        f"If you hold {item['name']}, list the exact credential and "
                        "field under Education or Certifications; otherwise, do not "
                        "imply that you hold it."
                    )
                suggestions.append(suggestion)
            else:
                suggestions.append(
                    f"If you have a real project, course, internship, or work example "
                    f"supporting {item['name']}, describe what you did; otherwise, "
                    "leave it unclaimed."
                )
        elif item["status"] == "uncertain":
            if item["category"] == "experience":
                maximum = item["maximum_years"]
                minimum = item["minimum_years"]
                maximum_note = (
                    f" The listed maximum of {maximum:g} years is not a target to claim."
                    if maximum is not None and minimum is not None and maximum > minimum
                    else ""
                )
                suggestions.append(
                    "No total experience duration is stated. If useful, describe "
                    "relevant professional, internship, training, or project experience "
                    f"with its actual duration.{maximum_note}"
                )
            else:
                suggestions.append(
                    f"The resume mentions {item['name']} without enough context; if accurate, "
                    "add a specific project, education, internship, or work example."
                )
        elif item["status"] == "partially_supported":
            suggestions.append(
                f"Clarify the existing evidence for {item['name']} with a specific, "
                "truthful example."
            )
    if not suggestions:
        suggestions.append(
            "No additional evidence-backed improvement was identified; keep claims "
            "accurate and change the resume only when you can support the change."
        )
    return suggestions


def analyze_resume(resume_text: str, job_description: str) -> dict[str, Any]:
    data = _analyze_resume(resume_text, job_description)
    parsed_job = parse_job_description(job_description)
    parsed_names: dict[tuple[str, str], RequirementPriority] = {
        (item["category"], item["name"]): item["priority"]
        for item in parsed_job["requirements"]
        if item["category"] in {"skill", "qualification"}
    }
    requirements: list[_Requirement] = []
    raw_requirements: list[dict[str, Any]] = data["requirements"]
    for item in raw_requirements:
        priority = parsed_names.get((item["category"], item["name"]))
        if priority is None:
            continue
        requirements.append(
            {
                "name": item["name"],
                "category": item["category"],
                "priority": priority,
                "status": item["status"],
                "evidence_type": item["evidence_type"],
                "evidence": item["evidence"],
                "section": item["section"],
                "reason": "",
                "confidence": "low",
                "minimum_years": None,
                "maximum_years": None,
                "original_text": None,
            }
        )
    data["requirements"] = requirements

    for field, category, priority in (
        ("required_skills", "skill", "required"),
        ("preferred_skills", "skill", "preferred"),
        ("required_qualifications", "qualification", "required"),
        ("preferred_qualifications", "qualification", "preferred"),
    ):
        data[field] = [
            item["name"]
            for item in parsed_job["requirements"]
            if item["category"] == category and item["priority"] == priority
        ]
    for field, status in (
        ("matched_skills", "matched"),
        ("partial_skills", "partially_supported"),
        ("missing_skills", "missing"),
        ("uncertain_skills", "uncertain"),
    ):
        data[field] = [
            item["name"]
            for item in requirements
            if item["category"] == "skill" and item["status"] == status
        ]
    data["matched_qualifications"] = [
        item["name"]
        for item in requirements
        if item["category"] == "qualification" and item["status"] == "matched"
    ]
    data["missing_qualifications"] = [
        item["name"]
        for item in requirements
        if item["category"] == "qualification"
        and item["priority"] == "required"
        and item["status"] == "missing"
    ]
    data["uncertain_qualifications"] = [
        item["name"]
        for item in requirements
        if item["category"] == "qualification" and item["status"] == "uncertain"
    ]

    for item in requirements:
        if item["evidence_type"] == "demonstrated":
            item["reason"] = "The resume includes contextual evidence supporting this requirement."
            item["confidence"] = "high"
        elif item["evidence_type"] == "explicitly_listed":
            section_name = item["section"].replace("_", " ") if item["section"] else "skills"
            item["reason"] = (
                f"The skill is explicitly listed in the resume's {section_name} section. "
                "This supports a basic skill match but does not establish proficiency, "
                "duration, or project usage."
            )
            item["confidence"] = "medium"
        elif item["status"] == "partially_supported":
            item["reason"] = (
                "Related evidence exists, but the resume describes it as limited or developing."
            )
            item["confidence"] = "medium"
        elif item["status"] == "uncertain":
            item["reason"] = (
                "The item appears without enough contextual evidence to confirm it."
            )
            item["confidence"] = "low"
        elif item["status"] == "not_applicable":
            item["reason"] = "This requirement is informational and is not scored."
            item["confidence"] = "high"
        else:
            item["reason"] = "No supporting evidence was found in the extracted resume text."
            item["confidence"] = "medium"

    candidate_years, candidate_evidence = candidate_experience(resume_text)
    data["experience"]["candidate_years"] = candidate_years
    for parsed_requirement in parsed_job["requirements"]:
        if parsed_requirement["category"] == "experience":
            requirements.append(
                _experience_requirement(data, parsed_requirement, candidate_evidence)
            )
    experience_requirements = [item for item in requirements if item["category"] == "experience"]
    required_years = [
        item["minimum_years"]
        for item in experience_requirements
        if item["priority"] == "required" and item["minimum_years"] is not None
    ]
    preferred_ranges = [
        item for item in experience_requirements if item["priority"] == "preferred"
    ]
    candidate_years = data["experience"]["candidate_years"]
    data["experience"]["required_years"] = max(required_years) if required_years else None
    matched_required_range = next(
        (
            item
            for item in experience_requirements
            if item["priority"] == "required"
            and item["minimum_years"] == data["experience"]["required_years"]
        ),
        None,
    )
    data["experience"]["required_max_years"] = (
        matched_required_range["maximum_years"] if matched_required_range else None
    )
    data["experience"]["original_requirement"] = (
        matched_required_range["original_text"] if matched_required_range else None
    )
    if required_years:
        years = max(required_years)
        range_name = (
            matched_required_range["name"] if matched_required_range else f"{years:g} years"
        )
        is_range = range_name != f"{years:g} years of experience"
        if years == 0:
            data["experience"]["summary"] = (
                f"The job description accepts {range_name}; zero is the minimum, not a "
                "request to claim the upper bound."
            )
        elif is_range:
            data["experience"]["summary"] = (
                f"The job description lists {range_name}; the minimum is {years:g} years, "
            )
        else:
            data["experience"]["summary"] = (
                f"The job description asks for at least {years:g} years of experience."
            )
        if candidate_years is None:
            data["experience"]["summary"] += (
                " No explicit total in years was found in the resume; dates and role "
                "duration are not inferred."
            )
        else:
            data["experience"]["summary"] += (
                f" The resume explicitly states {candidate_years:g} years."
            )
    elif preferred_ranges:
        preferred_range = max(preferred_ranges, key=lambda item: item["minimum_years"] or 0)
        years = preferred_range["minimum_years"] or 0.0
        if candidate_years is None:
            data["experience"]["summary"] = (
                f"The job description lists {preferred_range['name']} as preferred; "
                "No explicit total in years was found in the resume; dates and role "
                "duration are not inferred."
            )
        else:
            data["experience"]["summary"] = (
                f"The job description lists {preferred_range['name']} as preferred; "
                f"the resume explicitly states {candidate_years:g} years."
            )
    else:
        data["experience"]["summary"] = (
            "The job description does not state a detectable minimum number of years. "
            "No experience score was applied."
        )
    data["improvements"] = _improvements(requirements)
    data["score"], data["criteria"] = _score_requirements(requirements)
    data["job_title"] = parsed_job["job_title"]
    data["responsibilities"] = parsed_job["responsibilities"]
    data["optional_responsibilities"] = parsed_job["optional_responsibilities"]
    data["warnings"] = list(parsed_job["warnings"])
    data["scoring_note"] = (
        "Each required requirement has weight 2 and each preferred requirement has "
        "weight 1. Matched requirements receive full credit, partially supported "
        "requirements receive half credit, and missing or uncertain requirements "
        "receive no credit. Explicitly optional items and experience ranges with a "
        "zero-year minimum are reported but not scored. Duplicate requirement names "
        "are counted once. The score is 100 × weighted credits / total weight, "
        "rounded to a whole number. No score is calculated when no scoreable "
        "requirements are detected. This is not a hiring probability or guarantee."
    )
    data["plain_text"] = _plain_text(data)
    return data


__all__ = ["analyze_resume"]

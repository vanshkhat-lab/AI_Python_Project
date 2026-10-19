from __future__ import annotations

from typing import Any, Literal, TypedDict

from backend.resumeiq.services.job_parser import parse_job_description
from resume_analyzer.analyzer import analyze_resume as _analyze_resume

_CREDIT = {
    "matched": 1.0,
    "partially_supported": 0.5,
    "missing": 0.0,
    "uncertain": 0.0,
}

RequirementStatus = Literal[
    "matched", "partially_supported", "missing", "uncertain"
]
RequirementPriority = Literal["required", "preferred"]
Confidence = Literal["high", "medium", "low"]


class _Requirement(TypedDict):
    name: str
    category: Literal["skill", "qualification", "experience"]
    priority: RequirementPriority
    status: RequirementStatus
    evidence: str | None
    section: str | None
    reason: str
    confidence: Confidence


class _Criterion(TypedDict):
    name: str
    weight: int
    effective_weight: float
    coverage: float
    points: float
    detail: str


def _experience_requirement(
    data: dict[str, Any],
    resume_text: str,
    required: float,
    priority: RequirementPriority,
) -> _Requirement:
    candidate = data["experience"]["candidate_years"]
    evidence = next(
        (
            sentence.strip()
            for sentence in resume_text.splitlines()
            if "year" in sentence.lower()
            and any(character.isdigit() for character in sentence)
        ),
        None,
    )
    if candidate is None:
        status: RequirementStatus = "uncertain"
        reason = (
            "No explicit total in years was found; role dates are not used to infer duration."
        )
        confidence: Confidence = "low"
    elif candidate >= required:
        status = "matched"
        reason = "The resume explicitly states at least the required years of experience."
        confidence = "high"
    elif candidate > 0:
        status = "partially_supported"
        reason = "The resume states some experience, but less than the stated requirement."
        confidence = "high"
    else:
        status = "missing"
        reason = "No qualifying explicit experience duration was found."
        confidence = "medium"
    return {
        "name": f"{required:g} years of experience",
        "category": "experience",
        "priority": priority,
        "status": status,
        "evidence": evidence[:350] if evidence else None,
        "section": "experience" if evidence else None,
        "reason": reason,
        "confidence": confidence,
    }


def _score_requirements(
    requirements: list[_Requirement],
) -> tuple[int | None, list[_Criterion]]:
    if not requirements:
        return None, []
    total_weight = sum(
        2 if item["priority"] == "required" else 1 for item in requirements
    )
    criteria: list[_Criterion] = []
    for item in requirements:
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
        lines.append(
            f"- {item['name']} ({item['priority']}, {item['status']}): "
            f"{item['reason']}{evidence}"
        )
    lines.extend(("", "RELEVANT RESUME EVIDENCE"))
    lines.extend(f"- {snippet}" for snippet in data["relevant_experience"])
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
            "No reliable requirements were detected, so no meaningful score could be calculated."
        )
    return "\n".join(lines) + "\n"


def _improvements(requirements: list[_Requirement]) -> list[str]:
    suggestions: list[str] = []
    for item in requirements:
        if item["status"] == "missing":
            suggestions.append(
                f"If accurate, describe evidence for {item['name']}; otherwise, do not "
                "add it as a claimed qualification or skill."
            )
        elif item["status"] == "uncertain":
            suggestions.append(
                f"Add context for {item['name']} only if you can support it with a real "
                "project, education, or work example."
            )
        elif item["status"] == "partially_supported":
            suggestions.append(
                f"Clarify the existing evidence for {item['name']} with a specific, "
                "truthful example."
            )
    if not suggestions:
        suggestions.append(
            "Keep the matching evidence specific and verify every claim before "
            "tailoring the resume."
        )
    return suggestions


def analyze_resume(resume_text: str, job_description: str) -> dict[str, Any]:
    data = _analyze_resume(resume_text, job_description)
    parsed_job = parse_job_description(job_description)
    parsed_names: dict[tuple[str, str], RequirementPriority] = {
        (item["category"], item["name"]): item["priority"]
        for item in parsed_job["requirements"]
        if item["category"] != "experience"
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
                "evidence": item["evidence"],
                "section": item["section"],
                "reason": "",
                "confidence": "low",
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
        if item["status"] == "matched":
            item["reason"] = (
                "The resume includes contextual evidence supporting this requirement."
            )
            item["confidence"] = "high"
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
        else:
            item["reason"] = (
                "No supporting evidence was found in the extracted resume text."
            )
            item["confidence"] = "medium"

    for parsed_requirement in parsed_job["requirements"]:
        if parsed_requirement["category"] == "experience":
            years = float(parsed_requirement["name"].split(" ", 1)[0])
            requirements.append(
                _experience_requirement(
                    data, resume_text, years, parsed_requirement["priority"]
                )
            )
    experience_requirements = [
        item for item in requirements if item["category"] == "experience"
    ]
    required_years = [
        float(item["name"].split(" ", 1)[0])
        for item in experience_requirements
        if item["priority"] == "required"
    ]
    preferred_years = [
        float(item["name"].split(" ", 1)[0])
        for item in experience_requirements
        if item["priority"] == "preferred"
    ]
    candidate_years = data["experience"]["candidate_years"]
    data["experience"]["required_years"] = max(required_years) if required_years else None
    if required_years:
        years = max(required_years)
        if candidate_years is None:
            data["experience"]["summary"] = (
                f"The job description asks for {years:g} years of experience. "
                "No explicit total in years was found in the resume; dates and role "
                "duration are not inferred."
            )
        else:
            data["experience"]["summary"] = (
                f"The job description asks for {years:g} years; the resume "
                f"explicitly states {candidate_years:g} years."
            )
    elif preferred_years:
        years = max(preferred_years)
        if candidate_years is None:
            data["experience"]["summary"] = (
                f"The job description lists {years:g} years of experience as preferred. "
                "No explicit total in years was found in the resume; dates and role "
                "duration are not inferred."
            )
        else:
            data["experience"]["summary"] = (
                f"The job description lists {years:g} years of experience as preferred; "
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
    data["warnings"] = list(parsed_job["warnings"])
    data["scoring_note"] = (
        "Each required requirement has weight 2 and each preferred requirement has "
        "weight 1. Matched requirements receive full credit, partially supported "
        "requirements receive half credit, and missing or uncertain requirements "
        "receive no credit. The score is 100 × weighted credits / total weight, "
        "rounded to a whole number. No score is calculated when no reliable "
        "requirements are detected. This is not a hiring probability or guarantee."
    )
    data["plain_text"] = _plain_text(data)
    return data


__all__ = ["analyze_resume"]

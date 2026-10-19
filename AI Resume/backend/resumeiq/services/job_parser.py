from __future__ import annotations

import re
from typing import Literal, TypedDict

from resume_analyzer.analyzer import (
    PREFERRED_MARKER,
    QUALIFICATIONS,
    REQUIRED_MARKER,
    SKILL_ALIASES,
    YEAR_PATTERNS,
    priority_for_requirement,
    term_pattern,
)

_TITLE_WORDS = re.compile(
    r"\b(engineer|developer|analyst|designer|manager|scientist|specialist|"
    r"consultant|architect|coordinator|director|administrator|technician)\b",
    re.IGNORECASE,
)
_NOT_REQUIRED_MARKER = re.compile(
    r"\b(?:not required|not mandatory|not essential|not needed|optional)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_HEADING = re.compile(
    r"^\s*(responsibilities|what you('ll| will) do|duties)\s*:?\s*$",
    re.IGNORECASE,
)
_SECTION_HEADING = re.compile(
    r"^\s*(requirements|qualifications|skills|experience|what you('ll| will) do|"
    r"responsibilities|duties|preferred|nice to have)\s*:?\s*$",
    re.IGNORECASE,
)
_EXPERIENCE_SECTION_HEADING = re.compile(
    r"^\s*(?:work\s+|professional\s+|relevant\s+)?experience"
    r"(?:\s+(?:required|preferred|requirements?|qualifications))?\s*:?\s*$",
    re.IGNORECASE,
)
_OTHER_SECTION_HEADING = re.compile(
    r"^\s*(requirements|qualifications|skills|education|responsibilities|duties|"
    r"preferred|nice to have)\s*:?\s*$",
    re.IGNORECASE,
)
_YEARS_COUNT = re.compile(
    r"\b(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


class ParsedRequirement(TypedDict):
    name: str
    category: Literal["skill", "qualification", "experience"]
    priority: Literal["required", "preferred"]


class ParsedJobDescription(TypedDict):
    job_title: str | None
    requirements: list[ParsedRequirement]
    responsibilities: list[str]
    warnings: list[str]


def _only_explicitly_optional(text: str, terms: tuple[str, ...]) -> bool:
    matching_segments = [
        segment
        for line in text.splitlines()
        for clause in re.split(r"[;.!?]+", line)
        for segment in re.split(
            r",+|\b(?:and|but|whereas|while)\b", clause, flags=re.IGNORECASE
        )
        if any(term_pattern(term).search(segment) for term in terms)
    ]
    has_explicitly_optional = any(
        _NOT_REQUIRED_MARKER.search(segment) for segment in matching_segments
    )
    has_positive_requirement = any(
        PREFERRED_MARKER.search(segment)
        or (
            REQUIRED_MARKER.search(segment)
            and not _NOT_REQUIRED_MARKER.search(segment)
        )
        for segment in matching_segments
    )
    return has_explicitly_optional and not has_positive_requirement


def parse_job_description(text: str) -> ParsedJobDescription:
    lines = [line.strip(" \t-*•") for line in text.splitlines() if line.strip()]
    first_line = lines[0].strip("# :") if lines else ""
    job_title = (
        first_line
        if len(first_line) <= 100 and _TITLE_WORDS.search(first_line)
        else None
    )
    requirements: list[ParsedRequirement] = []
    for name, aliases in SKILL_ALIASES.items():
        terms = (name, *aliases)
        if (
            any(term_pattern(term).search(text) for term in terms)
            and not _only_explicitly_optional(text, terms)
        ):
            requirements.append(
                {
                    "name": name,
                    "category": "skill",
                    "priority": priority_for_requirement(text, (name, *aliases)),
                }
            )
    for name, aliases in QUALIFICATIONS.items():
        terms = (name, *aliases)
        if (
            any(term_pattern(term).search(text) for term in terms)
            and not _only_explicitly_optional(text, terms)
        ):
            requirements.append(
                {
                    "name": name,
                    "category": "qualification",
                    "priority": priority_for_requirement(text, (name, *aliases)),
                }
            )
    years_by_priority: dict[str, list[float]] = {"required": [], "preferred": []}
    in_experience_section = False
    for line in text.splitlines() or [text]:
        if _EXPERIENCE_SECTION_HEADING.match(line):
            in_experience_section = True
        elif _OTHER_SECTION_HEADING.match(line):
            in_experience_section = False
        for clause in re.split(r"[;.!?]+", line):
            if _NOT_REQUIRED_MARKER.search(clause) and not PREFERRED_MARKER.search(clause):
                continue
            values = [
                float(match.group("years"))
                for pattern in YEAR_PATTERNS
                for match in pattern.finditer(clause)
            ]
            if re.search(r"\bexperience\b", clause, re.IGNORECASE) or in_experience_section:
                values.extend(
                    float(match.group("years"))
                    for match in _YEARS_COUNT.finditer(clause)
                )
            values = list(dict.fromkeys(values))
            if not values:
                continue
            priority = (
                "preferred"
                if PREFERRED_MARKER.search(clause)
                else "required"
            )
            if REQUIRED_MARKER.search(clause):
                priority = "required"
            years_by_priority[priority].extend(values)
    for priority, years in years_by_priority.items():
        if years:
            maximum = max(years)
            requirements.append(
                {
                    "name": f"{maximum:g} years of experience",
                    "category": "experience",
                    "priority": priority,
                }
            )

    responsibilities: list[str] = []
    collecting = False
    for line in lines:
        if _RESPONSIBILITY_HEADING.match(line):
            collecting = True
            continue
        if _SECTION_HEADING.match(line):
            collecting = False
        elif collecting and len(line) > 8:
            responsibilities.append(line[:350])
        if len(responsibilities) == 10:
            break

    warnings: list[str] = []
    if not job_title:
        warnings.append("A job title could not be identified reliably.")
    if not requirements:
        warnings.append(
            "No reliable skills, qualifications, or experience requirements were detected."
        )
    if len(text.strip()) < 80:
        warnings.append("This job description is unusually short.")
    return {
        "job_title": job_title,
        "requirements": requirements,
        "responsibilities": responsibilities,
        "warnings": warnings,
    }

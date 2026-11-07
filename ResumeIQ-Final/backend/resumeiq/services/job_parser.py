from __future__ import annotations

import re
from typing import Literal, TypedDict

from resume_analyzer.analyzer import (
    PREFERRED_MARKER,
    REQUIRED_MARKER,
    SKILL_ALIASES,
    detect_skills,
    qualification_names,
    qualification_terms,
    term_pattern,
)

RequirementPriority = Literal["required", "preferred", "optional"]
RequirementCategory = Literal["skill", "qualification", "experience", "responsibility"]

_TITLE_WORDS = re.compile(
    r"\b(engineer|developer|analyst|designer|manager|scientist|specialist|"
    r"consultant|architect|coordinator|director|administrator|technician)\b",
    re.IGNORECASE,
)
_NOT_REQUIRED_MARKER = re.compile(
    r"\b(?:not required|not mandatory|not essential|not needed|optional)\b",
    re.IGNORECASE,
)
_OPTIONAL_MARKER = re.compile(r"\b(?:optional|desirable|discretionary)\b", re.IGNORECASE)
_EXPERIENCE_YEARS = re.compile(
    r"\b(?:(?P<minimum>\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*"
    r"(?P<maximum>\d+(?:\.\d+)?)|"
    r"between\s+(?P<between_minimum>\d+(?:\.\d+)?)\s+and\s+"
    r"(?P<between_maximum>\d+(?:\.\d+)?)|"
    r"up\s+to\s+(?P<upper>\d+(?:\.\d+)?)|"
    r"(?P<exact>\d+(?:\.\d+)?)(?P<plus>\+)?)\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_SPLIT_REQUIREMENT = re.compile(
    r"[;!?]+|\.(?=\s+[A-Z])|,+|\b(?:and|but|whereas|while)\b",
    re.IGNORECASE,
)


class ParsedOtherRequirement(TypedDict):
    name: str
    category: Literal["skill", "qualification", "responsibility"]
    priority: RequirementPriority


class ParsedExperienceRequirement(TypedDict):
    name: str
    category: Literal["experience"]
    priority: RequirementPriority
    minimum_years: float
    maximum_years: float | None
    original_text: str


ParsedRequirement = ParsedOtherRequirement | ParsedExperienceRequirement


class ParsedJobDescription(TypedDict):
    job_title: str | None
    requirements: list[ParsedRequirement]
    responsibilities: list[str]
    optional_responsibilities: list[str]
    warnings: list[str]


def _clean_line(line: str) -> str:
    return re.sub(r"^\s*(?:#+\s*|[-*•]\s*)+", "", line).strip()


def _priority(text: str, inherited: RequirementPriority | None) -> RequirementPriority:
    if _NOT_REQUIRED_MARKER.search(text):
        return "optional"
    if PREFERRED_MARKER.search(text):
        return "preferred"
    if _OPTIONAL_MARKER.search(text):
        return "optional"
    if REQUIRED_MARKER.search(text):
        return "required"
    return inherited or "required"


def _heading_context(
    heading: str,
) -> tuple[str, RequirementPriority | None] | None:
    normalized = heading.strip().lower().replace("’", "'")
    normalized = re.sub(r"[\s:：]+$", "", normalized)
    normalized = re.sub(r"[\s-]+", " ", normalized)
    if not normalized:
        return None

    priority: RequirementPriority | None = None
    if re.search(r"\b(?:preferred|preferably|desired|nice to have|bonus)\b", normalized):
        priority = "preferred"
    elif re.search(r"\b(?:optional|desirable)\b", normalized):
        priority = "optional"
    elif re.search(r"\b(?:required|mandatory|essential|minimum|must have)\b", normalized):
        priority = "required"

    if re.fullmatch(
        r"(?:(?:role|job|position)\s+)?(?:overview|summary|about(?: the role)?)",
        normalized,
    ):
        return "overview", priority
    if re.fullmatch(
        r"(?:(?:required|preferred|optional|desirable|desired)\s+)?"
        r"(?:(?:key|main|primary|core|job)\s+)?(?:responsibilities|duties|capabilities|"
        r"what you(?:'ll| will) do|what you(?:'re| are) responsible for|"
        r"role responsibilities)",
        normalized,
    ):
        return "responsibilities", priority or "required"
    if re.fullmatch(
        r"(?:(?:work|professional|relevant)\s+)?experience"
        r"(?:\s+(?:required|preferred|requirements?|qualifications?))?"
        r"|(?:required|preferred|optional|desired)\s+"
        r"(?:(?:work|professional|relevant)\s+)?experience",
        normalized,
    ):
        return "experience", priority or "required"
    if re.fullmatch(
        r"(?:(?:work|professional|relevant)\s+)?experience(?:\s+requirements?)?",
        normalized,
    ):
        return "experience", priority or "required"
    if re.fullmatch(
        r"(?:(?:required|preferred|optional|desirable|desired|nice to have)\s+)?"
        r"(?:(?:technical|core|key)\s+)?(?:skills?|competencies)"
        r"(?:\s+(?:required|preferred|desired|and requirements?))?",
        normalized,
    ):
        return "skills", priority or "required"
    if re.fullmatch(
        r"(?:(?:required|preferred|optional|desirable|desired|nice to have)\s+)?"
        r"(?:(?:minimum|key|education|academic)\s+)?"
        r"(?:qualifications?(?:\s+and\s+education)?|"
        r"education(?:\s+and\s+qualifications?)?|certifications?)"
        r"(?:\s+(?:required|preferred|desired))?",
        normalized,
    ):
        return "qualifications", priority or "required"
    if re.fullmatch(
        r"(?:(?:required|preferred|optional|desirable|desired)"
        r"(?:\s+or\s+(?:optional|desirable|preferred|desired))?\s+)?"
        r"(?:requirements?|minimum requirements)",
        normalized,
    ):
        return "general", priority or "required"
    if re.fullmatch(r"(?:preferred|optional|desirable|nice to have)", normalized):
        return "general", priority or ("optional" if normalized == "optional" else "preferred")
    return None


def _read_lines(
    text: str,
) -> list[tuple[str, str, RequirementPriority | None]]:
    lines: list[tuple[str, str, RequirementPriority | None]] = []
    section = "general"
    section_priority: RequirementPriority | None = None
    for raw_line in text.splitlines() or [text]:
        line = _clean_line(raw_line)
        if not line:
            continue
        heading = line
        content = ""
        if ":" in line:
            possible_heading, possible_content = line.split(":", 1)
            if _heading_context(possible_heading):
                heading, content = possible_heading, possible_content.strip()
        context = _heading_context(heading)
        if context:
            section, section_priority = context
            if not content:
                continue
            line = content
        lines.append((line, section, section_priority))
    return lines


def _line_priorities(
    line: str,
    terms: tuple[str, ...],
    section: str,
    section_priority: RequirementPriority | None,
) -> set[RequirementPriority]:
    priorities: set[RequirementPriority] = set()
    if section == "responsibilities":
        return priorities
    if section == "overview" and not (
        PREFERRED_MARKER.search(line)
        or REQUIRED_MARKER.search(line)
        or _OPTIONAL_MARKER.search(line)
        or _NOT_REQUIRED_MARKER.search(line)
    ):
        return priorities
    if section in {"skills", "qualifications"}:
        allowed = True
    elif section == "experience":
        allowed = True
    elif section in {"general", "overview"}:
        allowed = True
    else:
        allowed = False
    if not allowed:
        return priorities

    for segment in _SPLIT_REQUIREMENT.split(line):
        if any(term_pattern(term).search(segment) for term in terms):
            priorities.add(_priority(segment, section_priority))
    return priorities


def _resolve_priority(priorities: set[RequirementPriority]) -> RequirementPriority:
    if "required" in priorities:
        return "required"
    if "preferred" in priorities:
        return "preferred"
    return "optional"


def _only_not_required(text: str, terms: tuple[str, ...]) -> bool:
    has_negative = False
    has_positive = False
    for line in text.splitlines() or [text]:
        for segment in _SPLIT_REQUIREMENT.split(line):
            if not any(term_pattern(term).search(segment) for term in terms):
                continue
            if _NOT_REQUIRED_MARKER.search(segment):
                has_negative = True
            elif PREFERRED_MARKER.search(segment) or REQUIRED_MARKER.search(segment):
                has_positive = True
    return has_negative and not has_positive


def _generic_certification_is_redundant(text: str, qualifications: list[str]) -> bool:
    specific_qualifications = [
        name for name in qualifications if name != "Professional certification"
    ]
    certification_segments = [
        segment
        for line in text.splitlines()
        for segment in _SPLIT_REQUIREMENT.split(line)
        if term_pattern("certification").search(segment)
    ]
    return bool(certification_segments) and all(
        any(
            any(term_pattern(term).search(segment) for term in qualification_terms(name))
            for name in specific_qualifications
        )
        for segment in certification_segments
    )


def _year_requirement(
    match: re.Match[str], text: str, priority: RequirementPriority
) -> ParsedExperienceRequirement:
    if match.group("minimum") is not None:
        minimum = float(match.group("minimum"))
        maximum = float(match.group("maximum"))
        years = f"{minimum:g}-{maximum:g}"
    elif match.group("between_minimum") is not None:
        minimum = float(match.group("between_minimum"))
        maximum = float(match.group("between_maximum"))
        years = f"{minimum:g}-{maximum:g}"
    elif match.group("upper") is not None:
        minimum = 0.0
        maximum = float(match.group("upper"))
        years = f"0-{maximum:g}"
    else:
        minimum = float(match.group("exact"))
        maximum = None if match.group("plus") else minimum
        years = f"{minimum:g}{'+' if match.group('plus') else ''}"
    return {
        "name": f"{years} years of experience",
        "category": "experience",
        "priority": priority,
        "minimum_years": minimum,
        "maximum_years": maximum,
        "original_text": text.strip(),
    }


def parse_job_description(text: str) -> ParsedJobDescription:
    lines = _read_lines(text)
    first_line = _clean_line(text.splitlines()[0]).strip("# :") if text.splitlines() else ""
    job_title = first_line if len(first_line) <= 100 and _TITLE_WORDS.search(first_line) else None

    requirements: list[ParsedRequirement] = []
    detected_skills = set(detect_skills(text))
    for name, aliases in SKILL_ALIASES.items():
        if name not in detected_skills:
            continue
        terms = (name, *aliases)
        if _only_not_required(text, terms):
            continue
        priorities: set[RequirementPriority] = {
            priority
            for line, section, section_priority in lines
            for priority in _line_priorities(line, terms, section, section_priority)
        }
        if priorities:
            requirements.append(
                {
                    "name": name,
                    "category": "skill",
                    "priority": _resolve_priority(priorities),
                }
            )

    detected_qualifications = qualification_names(text)
    if "Professional certification" in detected_qualifications and (
        _generic_certification_is_redundant(text, detected_qualifications)
    ):
        detected_qualifications.remove("Professional certification")
    for name in detected_qualifications:
        terms = qualification_terms(name)
        if _only_not_required(text, terms):
            continue
        priorities: set[RequirementPriority] = {
            priority
            for line, section, section_priority in lines
            for priority in _line_priorities(line, terms, section, section_priority)
            if section in {"qualifications", "general", "experience", "overview"}
        }
        if priorities:
            requirements.append(
                {
                    "name": name,
                    "category": "qualification",
                    "priority": _resolve_priority(priorities),
                }
            )

    for line, section, section_priority in lines:
        for clause in re.split(r"[;.!?]+", line):
            has_experience_context = (
                section == "experience"
                or re.search(r"\bexperience\b", clause, re.IGNORECASE) is not None
            )
            if not has_experience_context:
                continue
            for match in _EXPERIENCE_YEARS.finditer(clause):
                priority = _priority(clause, section_priority)
                requirements.append(_year_requirement(match, clause, priority))

    responsibilities: list[str] = []
    optional_responsibilities: list[str] = []
    for line, section, section_priority in lines:
        if section != "responsibilities" or len(line) <= 8:
            continue
        destination = (
            optional_responsibilities
            if _priority(line, section_priority) == "optional"
            else responsibilities
        )
        if line not in destination:
            destination.append(line[:350])
        requirements.append(
            {
                "name": line[:350],
                "category": "responsibility",
                "priority": _priority(line, section_priority),
            }
        )

    unique_requirements: dict[tuple[str, str, str], ParsedRequirement] = {}
    priority_rank = {"optional": 0, "preferred": 1, "required": 2}
    for item in requirements:
        identity = (
            item["category"],
            item["name"].casefold(),
            item.get("original_text", "").casefold()
            if item["category"] == "responsibility"
            else "",
        )
        existing = unique_requirements.get(identity)
        if (
            existing is None
            or priority_rank[item["priority"]] > priority_rank[existing["priority"]]
        ):
            unique_requirements[identity] = item
    requirements = list(unique_requirements.values())

    warnings: list[str] = []
    if not job_title:
        warnings.append("A job title could not be identified reliably.")
    if not any(item["category"] != "responsibility" for item in requirements):
        warnings.append(
            "No reliable skills, qualifications, or experience requirements were detected."
        )
    if len(text.strip()) < 80:
        warnings.append("This job description is unusually short.")
    return {
        "job_title": job_title,
        "requirements": requirements,
        "responsibilities": responsibilities[:10],
        "optional_responsibilities": optional_responsibilities[:10],
        "warnings": warnings,
    }

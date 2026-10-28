from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

RequirementStatus = Literal[
    "matched", "partially_supported", "missing", "uncertain"
]
RequirementCategory = Literal["skill", "qualification"]
RequirementPriority = Literal["required", "preferred"]


class EvidenceRequirement(TypedDict):
    name: str
    category: RequirementCategory
    status: RequirementStatus
    evidence: str | None
    section: str | None


class ScoredRequirement(EvidenceRequirement):
    priority: RequirementPriority


class ScoreComponent(TypedDict):
    name: str
    weight: float
    coverage: float
    detail: str
    effective_weight: float
    points: float

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "SQL": ("sql",),
    "C#": ("c#", "c sharp"),
    "C++": ("c++",),
    "Rust": ("rust",),
    "HTML": ("html",),
    "CSS": ("css",),
    "React": ("react", "react.js"),
    "Angular": ("angular",),
    "Vue": ("vue", "vue.js"),
    "Node.js": ("node.js", "nodejs"),
    "Flask": ("flask",),
    "Django": ("django",),
    "FastAPI": ("fastapi", "fast api"),
    "AWS": ("amazon web services",),
    "Azure": ("microsoft azure",),
    "Google Cloud": ("gcp", "google cloud platform"),
    "Docker": ("docker",),
    "Kubernetes": ("k8s",),
    "Git": ("git",),
    "Linux": ("linux",),
    "CI/CD": ("continuous integration", "continuous deployment"),
    "Machine Learning": ("ml", "machine-learning"),
    "Deep Learning": ("deep neural networks",),
    "Data Analysis": ("data analytics", "analyzing data"),
    "Data Visualization": ("data viz",),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Natural Language Processing": ("nlp",),
    "Generative AI": ("genai", "generative artificial intelligence"),
    "REST API": ("restful api", "rest apis"),
    "GraphQL": ("graphql",),
    "Microservices": ("micro-services",),
    "Agile": ("agile methodology",),
    "Scrum": ("scrum",),
    "Project Management": ("project planning",),
    "Communication": ("verbal communication", "written communication"),
    "Leadership": ("team leadership",),
    "Excel": ("microsoft excel",),
    "Data Cleaning": ("cleaning data",),
    "PostgreSQL": ("postgres",),
    "Scikit-learn": ("sklearn", "scikit learn"),
    "Power BI": ("powerbi",),
    "Tableau": ("tableau",),
    "Cybersecurity": ("information security", "security engineering"),
    "Testing": ("unit testing", "automated testing", "test automation"),
}

QUALIFICATIONS: dict[str, tuple[str, ...]] = {
    "Bachelor's degree": (
        "bachelor's degree",
        "bachelor’s degree",
        "bachelor degree",
        "bachelor of science",
        "bachelor of engineering",
        "b.s.",
        "b.e.",
        "beng",
        "b.tech",
    ),
    "Master's degree": (
        "master's degree",
        "master’s degree",
        "master degree",
        "master of science",
        "master of engineering",
        "m.s.",
        "m.e.",
        "meng",
        "m.tech",
    ),
    "PhD": ("ph.d.", "phd", "doctorate"),
    "Associate degree": ("associate degree", "associate's degree", "associate’s degree"),
    "Diploma": ("diploma",),
    "Professional certification": ("certification",),
    "PMP": ("pmp", "project management professional"),
    "CPA": ("cpa", "certified public accountant"),
}
_DEGREE_FIELD_PATTERN = re.compile(
    r"\b(?P<level>"
    r"bachelor(?:['’]s)?|bachelors|master(?:['’]s)?|masters|"
    r"associate(?:['’]s)?|"
    r"b\.?\s*e\.?|b\.?\s*tech\.?|b\.?\s*eng\.?|b\.?\s*s\.?|"
    r"m\.?\s*e\.?|m\.?\s*tech\.?|m\.?\s*eng\.?|m\.?\s*s\.?"
    r")"
    r"(?:\s+of\s+(?:science|engineering|arts|technology))?"
    r"(?:\s+degree)?"
    r"(?:\s+(?:in|with\s+(?:a\s+)?major\s+in|majoring\s+in)\s+|"
    r"\s*[-,:]\s*|\s*\(\s*|\s+)"
    r"(?P<field>(?!(?:is|degree|required|preferred|desired|mandatory|essential|optional)\b)"
    r"[a-z][a-z0-9&/ -]*?)"
    r"(?=\s+(?:is\s+)?(?:required|preferred|desired|mandatory|essential)|"
    r"\s+or\s+(?:a\s+)?(?:related|equivalent)|[,.;:\n)]|$)",
    re.IGNORECASE,
)

PARTIAL_EVIDENCE = (
    "familiar with",
    "exposure to",
    "learning",
    "currently studying",
    "beginner",
    "basic knowledge",
    "interested in",
)
SKILL_USE_CONTEXT = re.compile(
    r"\b(?:"
    r"build|built|building|develop(?:ed|ing)?|implement(?:ed|ing)?|"
    r"design(?:ed|ing)?|maintain(?:ed|ing)?|creat(?:ed|ing)?|"
    r"use|used|using|writ(?:e|es|ten|ing)|program(?:med|ming)?|"
    r"deploy(?:ed|ing)?|test(?:ed|ing)?|analyz(?:e|ed|ing)|"
    r"automat(?:e|ed|ing)|optimiz(?:e|ed|ing)|integrat(?:e|ed|ing)|"
    r"configur(?:e|ed|ing)|manag(?:e|ed|ing)|support(?:ed|ing)?|"
    r"deliver(?:ed|ing)?|lead|led|leading|appl(?:y|ied|ying)|"
    r"leverag(?:e|ed|ing)|utiliz(?:e|ed|ing)|quer(?:y|ied|ying)|"
    r"process(?:ed|ing)?|migrat(?:e|ed|ing)|architect(?:ed|ing)?|"
    r"troubleshoot(?:ed|ing)?|evaluat(?:e|ed|ing)|orchestrat(?:e|ed|ing)"
    r")\b",
    re.IGNORECASE,
)
NEGATIVE_SKILL_PREFIX = re.compile(
    r"\b(?:"
    r"no\s+(?:(?:prior|professional)\s+)?"
    r"(?:experience|knowledge|proficiency|skills?|exposure|background)"
    r"\s+(?:with|in|using|to)?|"
    r"without\s+(?:(?:prior)\s+)?"
    r"(?:experience|knowledge|proficiency|skills?|exposure)"
    r"\s+(?:with|in|using|to)?|"
    r"not\s+(?:experienced|proficient|skilled|familiar|trained|comfortable)"
    r"\s+(?:with|in|using)?|"
    r"never\s+(?:used|worked\s+with|applied)|"
    r"lack(?:s|ed)?\s+(?:of\s+)?"
    r"(?:experience|knowledge|proficiency|skills?|exposure)"
    r"\s+(?:with|in|using|to)?"
    r")\s*$",
    re.IGNORECASE,
)
COMPONENT_WEIGHTS = {"Skills": 0.70, "Experience": 0.20, "Qualifications": 0.10}
YEAR_PATTERNS = (
    re.compile(
        r"\b(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)"
        r"\s+(?:of\s+)?(?:relevant\s+)?(?:professional\s+)?experience\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexperience\s+of\s+(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        re.IGNORECASE,
    ),
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
PREFERRED_MARKER = re.compile(
    r"\b(preferred|preferably|desired|nice[\s-]+to[\s-]+have|bonus|desirable|"
    r"a\s+plus|beneficial|would\s+be\s+an?\s+advantage)\b",
    re.IGNORECASE,
)
NOT_REQUIRED_MARKER = re.compile(
    r"\b(?:not required|not mandatory|not essential|not needed|optional)\b",
    re.IGNORECASE,
)
REQUIRED_MARKER = re.compile(
    r"\b(required|must[\s-]+have|mandatory|minimum|essential|"
    r"need(?:ed)?|shall\s+have)\b",
    re.IGNORECASE,
)
RESUME_SECTIONS: dict[str, tuple[str, ...]] = {
    "experience": (
        "experience",
        "employment",
        "work experience",
        "professional experience",
        "work history",
        "career history",
    ),
    "projects": ("projects", "personal projects", "selected projects"),
    "education": ("education", "academic background"),
    "skills": ("skills", "technical skills", "core competencies"),
    "certifications": ("certifications", "licenses", "licences"),
}


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def term_pattern(term: str) -> re.Pattern[str]:
    return _term_pattern(term)


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(_term_pattern(term).search(text) for term in terms)


def _detected_skills(text: str) -> list[str]:
    return [
        skill
        for skill, aliases in SKILL_ALIASES.items()
        if _contains_term(text, (skill, *aliases))
    ]


def _year_values(text: str) -> list[float]:
    values: list[float] = []
    for pattern in YEAR_PATTERNS:
        values.extend(float(match.group("years")) for match in pattern.finditer(text))
    return values


def _required_year_values(text: str) -> list[float]:
    values: list[float] = []
    for clause in re.split(r"[;.!?\n]+", text):
        if PREFERRED_MARKER.search(clause) or NOT_REQUIRED_MARKER.search(clause):
            continue
        for pattern in YEAR_PATTERNS:
            values.extend(
                float(match.group("years")) for match in pattern.finditer(clause)
            )
    return values


def _qualifications(text: str) -> list[str]:
    qualifications = [
        name
        for name, aliases in QUALIFICATIONS.items()
        if _contains_term(text, (name, *aliases))
    ]
    degree_fields: dict[str, list[str]] = {}
    for match in _DEGREE_FIELD_PATTERN.finditer(text):
        degree_level = match.group("level").lower()
        qualification = (
            "Bachelor's degree"
            if degree_level.startswith("bachelor") or degree_level.startswith("b.")
            else "Associate degree"
            if degree_level.startswith("associate")
            else "Master's degree"
        )
        field = " ".join(match.group("field").split()).strip(" -")
        if field:
            degree_fields.setdefault(qualification, []).append(field)

    for qualification, fields in degree_fields.items():
        if qualification in qualifications:
            qualifications.remove(qualification)
        qualifications.extend(
            f"{qualification} in {field}" for field in dict.fromkeys(fields)
        )
    return qualifications


def qualification_names(text: str) -> list[str]:
    return _qualifications(text)


def qualification_terms(qualification: str) -> tuple[str, ...]:
    base, separator, field = qualification.partition(" in ")
    terms = (base, *QUALIFICATIONS.get(base, ()))
    return (*terms, field) if separator else terms


def _skill_evidence(text: str, skill: str) -> tuple[bool, bool, bool]:
    terms = (skill, *SKILL_ALIASES[skill])
    found = False
    has_partial_evidence = False
    has_contextual_evidence = False
    for sentence in SENTENCE_SPLIT.split(text):
        for term in terms:
            for match in _term_pattern(term).finditer(sentence):
                prefix = sentence[max(0, match.start() - 100) : match.start()]
                if NEGATIVE_SKILL_PREFIX.search(prefix):
                    continue
                found = True
                context = sentence[
                    max(0, match.start() - 80) : min(len(sentence), match.end() + 40)
                ]
                if not _contains_term(context, PARTIAL_EVIDENCE):
                    if any(
                        len(
                            re.findall(
                                r"\b[\w+#./-]+\b",
                                sentence[
                                    min(action.end(), match.end()) : max(
                                        action.start(), match.start()
                                    )
                                ],
                            )
                        )
                        <= 8
                        for action in SKILL_USE_CONTEXT.finditer(sentence)
                    ):
                        has_contextual_evidence = True
                else:
                    has_partial_evidence = True
    return (
        found,
        has_partial_evidence and not has_contextual_evidence,
        has_contextual_evidence,
    )


def _evidence_snippets(resume_text: str, required_skills: list[str]) -> list[str]:
    snippets: list[str] = []
    for sentence in SENTENCE_SPLIT.split(resume_text):
        cleaned = " ".join(sentence.split())
        if len(cleaned) < 20:
            continue
        contains_skill = any(
            found and (partial or contextual)
            for skill in required_skills
            for found, partial, contextual in [_skill_evidence(cleaned, skill)]
        )
        contains_experience = bool(_year_values(cleaned)) or _contains_term(
            cleaned, ("engineer", "developer", "manager", "analyst")
        )
        if (contains_skill or contains_experience) and cleaned not in snippets:
            snippets.append(cleaned[:350])
        if len(snippets) == 5:
            break
    return snippets


def _priority_for_requirement(
    text: str, terms: tuple[str, ...]
) -> Literal["required", "preferred"]:
    priorities: set[str] = set()
    section_priority: str | None = None
    for line in text.splitlines():
        if not _contains_term(line, terms):
            if PREFERRED_MARKER.search(line):
                section_priority = "preferred"
            elif REQUIRED_MARKER.search(line):
                section_priority = "required"
            continue
        if PREFERRED_MARKER.match(line):
            section_priority = "preferred"
        elif REQUIRED_MARKER.match(line):
            section_priority = "required"
        for clause in re.split(r"[;.!?]+", line):
            for segment in re.split(
                r",+|\b(?:and|but|whereas|while)\b",
                clause,
                flags=re.IGNORECASE,
            ):
                if not _contains_term(segment, terms):
                    continue
                if PREFERRED_MARKER.search(segment):
                    priorities.add("preferred")
                elif REQUIRED_MARKER.search(segment):
                    priorities.add("required")
                elif section_priority:
                    priorities.add(section_priority)
                else:
                    priorities.add("required")
    if "required" in priorities:
        return "required"
    return "preferred" if priorities else "required"


def priority_for_requirement(
    text: str, terms: tuple[str, ...]
) -> Literal["required", "preferred"]:
    return _priority_for_requirement(text, terms)


def _section_for_heading(line: str) -> str | None:
    heading = re.sub(r"^[\s#>*\-]+|[\s:*]+$", "", line.lower())
    for section, names in RESUME_SECTIONS.items():
        if heading in names:
            return section
    return None


def _resume_sentences(resume_text: str) -> list[tuple[str, str]]:
    sentences: list[tuple[str, str]] = []
    current_section = "other"
    for line in resume_text.splitlines():
        cleaned_line = " ".join(line.split())
        if not cleaned_line:
            continue
        inline_heading = re.match(
            r"^(experience|employment|work history|career history|projects|"
            r"personal projects|selected projects|education|academic background|"
            r"skills|technical skills|core competencies|certifications|licenses|"
            r"licences)\s*:\s*(.+)$",
            cleaned_line,
            re.IGNORECASE,
        )
        if inline_heading:
            inline_section = _section_for_heading(inline_heading.group(1))
            if inline_section is not None:
                current_section = inline_section
            cleaned_line = inline_heading.group(2)
        heading_section = _section_for_heading(cleaned_line)
        if heading_section:
            current_section = heading_section
            continue
        for sentence in SENTENCE_SPLIT.split(cleaned_line):
            cleaned_sentence = " ".join(sentence.split())
            if cleaned_sentence:
                sentences.append((cleaned_sentence, current_section))
    if not sentences:
        sentences.extend(
            (" ".join(sentence.split()), "other")
            for sentence in SENTENCE_SPLIT.split(resume_text)
            if sentence.strip()
        )
    return sentences


def _skill_requirement(
    skill: str, resume_sentences: list[tuple[str, str]]
) -> EvidenceRequirement:
    best: EvidenceRequirement | None = None
    rank: dict[RequirementStatus, int] = {
        "uncertain": 1,
        "partially_supported": 2,
        "matched": 3,
    }
    for sentence, section in resume_sentences:
        found, partial, contextual = _skill_evidence(sentence, skill)
        if found:
            if partial:
                status: RequirementStatus = "partially_supported"
            elif contextual:
                status = "matched"
            else:
                status = "uncertain"
            candidate: EvidenceRequirement = {
                "name": skill,
                "category": "skill",
                "status": status,
                "evidence": sentence[:350],
                "section": section,
            }
            if best is None or rank[status] > rank[best["status"]]:
                best = candidate
            if status == "matched":
                break
    if best is not None:
        return best
    return {
        "name": skill,
        "category": "skill",
        "status": "missing",
        "evidence": None,
        "section": None,
    }


def _qualification_requirement(
    qualification: str, resume_sentences: list[tuple[str, str]]
) -> EvidenceRequirement:
    base, separator, field = qualification.partition(" in ")
    degree_terms = (base, *QUALIFICATIONS.get(base, ()))
    best: EvidenceRequirement | None = None
    for sentence, section in resume_sentences:
        has_qualification = (
            _contains_term(sentence, degree_terms)
            and (not separator or _contains_term(sentence, (field,)))
        )
        if has_qualification:
            status: RequirementStatus = (
                "matched" if section in {"education", "certifications"} else "uncertain"
            )
            candidate: EvidenceRequirement = {
                "name": qualification,
                "category": "qualification",
                "status": status,
                "evidence": sentence[:350],
                "section": section,
            }
            if best is None or status == "matched":
                best = candidate
            if status == "matched":
                break
    if best is not None:
        return best
    return {
        "name": qualification,
        "category": "qualification",
        "status": "missing",
        "evidence": None,
        "section": None,
    }


def _score(
    matched_skills: list[str],
    partial_skills: list[str],
    missing_skills: list[str],
    required_years: float | None,
    candidate_years: float | None,
    matched_qualifications: list[str],
    required_qualifications: list[str],
) -> tuple[int, list[ScoreComponent]]:
    components: list[ScoreComponent] = []
    if matched_skills or partial_skills or missing_skills:
        skill_coverage = (
            len(matched_skills) + 0.5 * len(partial_skills)
        ) / len(matched_skills + partial_skills + missing_skills)
        components.append(
            {
                "name": "Skills",
                "weight": COMPONENT_WEIGHTS["Skills"],
                "coverage": skill_coverage,
                "effective_weight": 0.0,
                "points": 0.0,
                "detail": (
                    f"{len(matched_skills)} evidenced, {len(partial_skills)} "
                    f"partial, {len(missing_skills)} not found"
                ),
            }
        )
    if required_years is not None:
        experience_coverage = (
            min(candidate_years / required_years, 1.0)
            if candidate_years is not None and required_years > 0
            else 0.0
        )
        components.append(
            {
                "name": "Experience",
                "weight": COMPONENT_WEIGHTS["Experience"],
                "coverage": experience_coverage,
                "effective_weight": 0.0,
                "points": 0.0,
                "detail": (
                    f"{candidate_years:g} stated years vs. {required_years:g} required"
                    if candidate_years is not None
                    else f"{required_years:g} years required; no explicit year total found"
                ),
            }
        )
    if required_qualifications:
        qualification_coverage = len(matched_qualifications) / len(
            required_qualifications
        )
        components.append(
            {
                "name": "Qualifications",
                "weight": COMPONENT_WEIGHTS["Qualifications"],
                "coverage": qualification_coverage,
                "effective_weight": 0.0,
                "points": 0.0,
                "detail": (
                    f"{len(matched_qualifications)} of "
                    f"{len(required_qualifications)} qualifications found"
                ),
            }
        )

    total_weight = sum(component["weight"] for component in components)
    if not components:
        return 0, []

    for component in components:
        component["effective_weight"] = component["weight"] / total_weight
        component["points"] = (
            component["coverage"] * component["effective_weight"] * 100
        )
    return round(sum(component["points"] for component in components)), components


def _plain_text(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "RESUME MATCH ANALYSIS",
        f"Transparent match score: {report['score']} / 100",
        "This score compares detectable evidence in the documents; it is not a "
        "prediction or guarantee of employability.",
        "",
        "MATCHED SKILLS",
        ", ".join(report["matched_skills"]) or "None detected",
        "",
        "PARTIAL / INSUFFICIENTLY EVIDENCED SKILLS",
        ", ".join(report["partial_skills"]) or "None detected",
        "",
        "SKILLS NOT FOUND",
        ", ".join(report["missing_skills"]) or "None detected",
        "",
        "SKILLS WITH UNCERTAIN EVIDENCE",
        ", ".join(report["uncertain_skills"]) or "None detected",
        "",
        "PREFERRED SKILLS (NOT INCLUDED IN THE REQUIRED MATCH SCORE)",
        ", ".join(report["preferred_skills"]) or "None detected",
        "",
        "EXPERIENCE",
        report["experience"]["summary"],
        "",
        "QUALIFICATIONS",
        ", ".join(report["matched_qualifications"]) or "None detected",
        "Missing: "
        + (", ".join(report["missing_qualifications"]) or "None detected"),
        "Preferred: "
        + (", ".join(report["preferred_qualifications"]) or "None detected"),
        "",
        "RELEVANT RESUME EVIDENCE",
    ]
    lines.extend(f"- {snippet}" for snippet in report["relevant_experience"])
    lines.extend(("", "SUGGESTED NEXT STEPS"))
    lines.extend(f"- {suggestion}" for suggestion in report["improvements"])
    lines.extend(("", "SCORING BREAKDOWN"))
    if report["criteria"]:
        for component in report["criteria"]:
            lines.append(
                f"- {component['name']}: {component['points']:.1f} points "
                f"({component['coverage']:.0%} coverage; "
                f"{component['effective_weight']:.0%} effective weight)"
            )
    else:
        lines.append(
            "No supported criteria were detected; no meaningful score could be calculated."
        )
    return "\n".join(lines) + "\n"


def analyze_resume(resume_text: str, job_description: str) -> dict[str, Any]:
    """Compare explicit resume evidence to detectable job requirements."""
    if not resume_text.strip() or not job_description.strip():
        raise ValueError("Resume and job description text must both be non-empty.")

    detected_skills = _detected_skills(job_description)
    preferred_skills = [
        skill
        for skill in detected_skills
        if _priority_for_requirement(
            job_description, (skill, *SKILL_ALIASES[skill])
        )
        == "preferred"
    ]
    required_skills = [
        skill for skill in detected_skills if skill not in preferred_skills
    ]
    resume_sentences = _resume_sentences(resume_text)
    skill_requirements: list[ScoredRequirement] = [
        {
            **_skill_requirement(skill, resume_sentences),
            "priority": "preferred" if skill in preferred_skills else "required",
        }
        for skill in detected_skills
    ]
    matched_skills = [
        item["name"]
        for item in skill_requirements
        if item["status"] == "matched"
    ]
    partial_skills = [
        item["name"]
        for item in skill_requirements
        if item["status"] == "partially_supported"
    ]
    missing_skills = [
        item["name"]
        for item in skill_requirements
        if item["status"] == "missing"
    ]
    uncertain_skills = [
        item["name"]
        for item in skill_requirements
        if item["status"] == "uncertain"
    ]

    required_year_values = _required_year_values(job_description)
    candidate_year_values = _year_values(resume_text)
    required_years = max(required_year_values) if required_year_values else None
    candidate_years = max(candidate_year_values) if candidate_year_values else None
    detected_qualifications = qualification_names(job_description)
    preferred_qualifications = [
        qualification
        for qualification in detected_qualifications
        if _priority_for_requirement(
            job_description, qualification_terms(qualification)
        )
        == "preferred"
    ]
    required_qualifications = [
        qualification
        for qualification in detected_qualifications
        if qualification not in preferred_qualifications
    ]
    qualification_requirements: list[ScoredRequirement] = [
        {
            **_qualification_requirement(qualification, resume_sentences),
            "priority": (
                "preferred"
                if qualification in preferred_qualifications
                else "required"
            ),
        }
        for qualification in detected_qualifications
    ]
    matched_qualifications = [
        item["name"]
        for item in qualification_requirements
        if item["priority"] == "required" and item["status"] == "matched"
    ]
    uncertain_qualifications = [
        item["name"]
        for item in qualification_requirements
        if item["status"] == "uncertain"
    ]
    required_skill_requirements = [
        item for item in skill_requirements if item["priority"] == "required"
    ]

    score, criteria = _score(
        [
            item["name"]
            for item in required_skill_requirements
            if item["status"] == "matched"
        ],
        [
            item["name"]
            for item in required_skill_requirements
            if item["status"] == "partially_supported"
        ],
        [
            item["name"]
            for item in required_skill_requirements
            if item["status"] in {"missing", "uncertain"}
        ],
        required_years,
        candidate_years,
        matched_qualifications,
        required_qualifications,
    )
    if required_years is None:
        experience_summary = (
            "The job description does not state a detectable minimum number of years. "
            "No experience score was applied."
        )
    elif candidate_years is None:
        experience_summary = (
            f"The job description asks for {required_years:g} years of experience. "
            "No explicit total in years was found in the resume; dates and role "
            "duration are not inferred."
        )
    else:
        experience_summary = (
            f"The job description asks for {required_years:g} years; the resume "
            f"explicitly states {candidate_years:g} years."
        )

    improvements: list[str] = []
    for skill in missing_skills:
        improvements.append(
            f"If your experience supports it, add {skill} using a specific, truthful "
            "example; otherwise do not add it as a claimed skill."
        )
    for skill in uncertain_skills:
        improvements.append(
            f"Add an evidence-backed example of {skill}; it currently appears only "
            "in a skills listing or without clear supporting context."
        )
    for skill in partial_skills:
        improvements.append(
            f"Strengthen the evidence for {skill} with a concrete task, project, "
            "or result you can substantiate."
        )
    if required_years is not None and candidate_years is None:
        improvements.append(
            "If accurate, make role dates or total relevant experience clearer; "
            "the analysis does not infer duration from dates."
        )
    if not improvements:
        improvements.append(
            "Keep the matching evidence specific and measurable, and verify every "
            "claim before tailoring the resume."
        )

    report: dict[str, Any] = {
        "score": score,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "matched_skills": matched_skills,
        "partial_skills": partial_skills,
        "missing_skills": missing_skills,
        "uncertain_skills": uncertain_skills,
        "experience": {
            "required_years": required_years,
            "candidate_years": candidate_years,
            "summary": experience_summary,
        },
        "required_qualifications": required_qualifications,
        "preferred_qualifications": preferred_qualifications,
        "matched_qualifications": matched_qualifications,
        "missing_qualifications": [
            item["name"]
            for item in qualification_requirements
            if item["priority"] == "required" and item["status"] == "missing"
        ],
        "uncertain_qualifications": uncertain_qualifications,
        "requirements": skill_requirements + qualification_requirements,
        "relevant_experience": _evidence_snippets(resume_text, detected_skills),
        "improvements": improvements,
        "criteria": criteria,
        "scoring_note": (
            "Skills contribute 70%, experience 20%, and qualifications 10%. "
            "Only categories detectable in the job description are scored; "
            "their weights are proportionally renormalized. Partial skill evidence "
            "counts as half. The score is a document comparison, not a hiring "
            "recommendation."
        ),
    }
    report["plain_text"] = _plain_text(report)
    return report

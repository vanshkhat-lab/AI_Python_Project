from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from backend.resumeiq.services.ai import get_recommendations


def fake_openai_module(output: dict):
    class FakeResponses:
        def create(self, **_kwargs):
            return SimpleNamespace(output_text=json.dumps(output))

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == "test-key"
            self.responses = FakeResponses()

    return SimpleNamespace(OpenAI=FakeClient)


def test_ai_recommendations_are_optional_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    suggestions, status = get_recommendations(
        "Built Python services.", {"matched_skills": [], "partial_skills": [], "missing_skills": []}
    )

    assert suggestions == []
    assert status == "not_configured"


def test_ai_provider_error_returns_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", None)

    suggestions, status = get_recommendations(
        "Built Python services.", {"matched_skills": [], "partial_skills": [], "missing_skills": []}
    )

    assert suggestions == []
    assert status == "unavailable"


def test_ai_accepts_only_exact_resume_quotes_and_supported_terms(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(
        sys.modules,
        "openai",
        fake_openai_module(
            {
                "items": [
                    {
                        "recommendation_type": "wording",
                        "original_resume_text_reference": "Built Python services.",
                        "suggestion": "Emphasize Python services in your bullet.",
                        "explanation": "Clarify the Python services in the cited wording.",
                        "evidence_quote": "Built Python services.",
                        "introduces_new_claim": False,
                    },
                    {
                        "recommendation_type": "wording",
                        "original_resume_text_reference": "Built Python services.",
                        "suggestion": "Emphasize Python Kubernetes services.",
                        "explanation": "Clarify the Python services in the cited wording.",
                        "evidence_quote": "Built Python services.",
                        "introduces_new_claim": False,
                    },
                    {
                        "recommendation_type": "wording",
                        "original_resume_text_reference": None,
                        "suggestion": "Mention Python services.",
                        "explanation": "Clarify the Python services in the cited wording.",
                        "evidence_quote": "Python services built many products.",
                        "introduces_new_claim": False,
                    },
                    {
                        "recommendation_type": "wording",
                        "original_resume_text_reference": "Built Python services.",
                        "suggestion": "Emphasize Python services in your bullet.",
                        "explanation": "This increases sales by 20 percent.",
                        "evidence_quote": "Built Python services.",
                        "introduces_new_claim": False,
                    },
                    {
                        "recommendation_type": "wording",
                        "original_resume_text_reference": "Built Python services.",
                        "suggestion": "Emphasize Python services in your bullet.",
                        "explanation": "Clarify the Python services in the cited wording.",
                        "evidence_quote": "Built Python services.",
                        "introduces_new_claim": True,
                    },
                ]
            }
        ),
    )

    suggestions, status = get_recommendations(
        "Built Python services. Completed Kubernetes certification.",
        {"matched_skills": ["Python"], "partial_skills": [], "missing_skills": []},
    )

    assert status == "available"
    assert suggestions == [
        {
            "recommendation_type": "wording",
            "original_resume_text_reference": "Built Python services.",
            "suggestion": "Emphasize Python services in your bullet.",
            "explanation": "Clarify the Python services in the cited wording.",
            "evidence_quote": "Built Python services.",
            "introduces_new_claim": False,
        }
    ]

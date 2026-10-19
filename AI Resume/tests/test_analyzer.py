import unittest

from resume_analyzer.analyzer import analyze_resume


class AnalyzeResumeTests(unittest.TestCase):
    def test_matches_missing_partial_skills_and_stated_experience(self):
        resume = (
            "Software engineer with 4 years of experience. "
            "Built Python services and used SQL to report results. "
            "Familiar with Docker."
        )
        job = (
            "Seeking 3 years of experience. Required: Python, SQL, Docker, "
            "Kubernetes, and AWS. Bachelor's degree preferred."
        )

        report = analyze_resume(resume, job)

        self.assertEqual(report["matched_skills"], ["Python", "SQL"])
        self.assertEqual(report["partial_skills"], ["Docker"])
        self.assertEqual(report["missing_skills"], ["AWS", "Kubernetes"])
        self.assertEqual(report["experience"]["required_years"], 3)
        self.assertEqual(report["experience"]["candidate_years"], 4)
        self.assertEqual(report["preferred_qualifications"], ["Bachelor's degree"])
        self.assertEqual(report["missing_qualifications"], [])
        self.assertGreater(report["score"], 0)
        self.assertIn("not a hiring", report["scoring_note"])

    def test_partial_only_and_renormalized_weights(self):
        report = analyze_resume(
            "Currently studying machine learning.",
            "Machine learning experience is required.",
        )

        self.assertEqual(report["partial_skills"], ["Machine Learning"])
        self.assertEqual(report["score"], 50)
        self.assertEqual(report["criteria"][0]["effective_weight"], 1.0)

    def test_no_detectable_criteria_has_no_meaningful_score(self):
        report = analyze_resume(
            "I enjoy solving difficult problems.",
            "We are looking for a curious and motivated person.",
        )

        self.assertEqual(report["score"], 0)
        self.assertEqual(report["criteria"], [])
        self.assertIn("No supported criteria", report["plain_text"])

    def test_empty_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze_resume("  ", "Python")

    def test_resume_does_not_get_credit_from_a_skill_in_an_unrelated_word(self):
        report = analyze_resume("The candidate is a great communicator.", "C++")

        self.assertEqual(report["missing_skills"], ["C++"])

    def test_negative_skill_claim_does_not_count_as_evidence(self):
        report = analyze_resume("I have no experience with AWS.", "AWS")

        self.assertEqual(report["missing_skills"], ["AWS"])
        self.assertEqual(report["relevant_experience"], [])

    def test_strong_evidence_overrides_a_partial_mention(self):
        report = analyze_resume(
            "Currently learning Python. Built and maintained Python services.",
            "Python is required.",
        )

        self.assertEqual(report["matched_skills"], ["Python"])
        self.assertEqual(report["partial_skills"], [])

    def test_preferred_skills_are_separate_and_do_not_reduce_required_score(self):
        report = analyze_resume(
            "Built Python services.",
            "Python is required; Docker is preferred.",
        )

        self.assertEqual(report["required_skills"], ["Python"])
        self.assertEqual(report["preferred_skills"], ["Docker"])
        self.assertEqual(report["matched_skills"], ["Python"])
        self.assertEqual(report["missing_skills"], ["Docker"])
        self.assertEqual(report["score"], 100)

    def test_preferred_section_heading_applies_to_following_requirement(self):
        report = analyze_resume(
            "Built Python applications.",
            "Required skills:\nPython\nPreferred skills:\nDocker",
        )

        self.assertEqual(report["required_skills"], ["Python"])
        self.assertEqual(report["preferred_skills"], ["Docker"])

    def test_inline_mixed_priorities_are_not_applied_to_the_wrong_skill(self):
        report = analyze_resume(
            "Built Python services.",
            "Python required, Docker preferred.",
        )

        self.assertEqual(report["required_skills"], ["Python"])
        self.assertEqual(report["preferred_skills"], ["Docker"])

    def test_preferred_requirement_does_not_hide_required_years(self):
        report = analyze_resume(
            "Python developer with 4 years of experience.",
            "Required: Python and 3 years of experience. Preferred: Docker.",
        )

        self.assertEqual(report["experience"]["required_years"], 3)
        self.assertEqual(report["experience"]["candidate_years"], 4)
        self.assertEqual(
            [criterion["name"] for criterion in report["criteria"]],
            ["Skills", "Experience"],
        )

    def test_resume_sections_and_uncertain_skills_are_preserved(self):
        report = analyze_resume(
            "SKILLS\nPython\n\nPROJECTS\nBuilt and tested a Python API.",
            "Python is required.",
        )

        requirement = report["requirements"][0]
        self.assertEqual(requirement["status"], "matched")
        self.assertEqual(requirement["section"], "projects")
        self.assertIn("Python API", requirement["evidence"])

        skills_only = analyze_resume("SKILLS\nPython", "Python is required.")
        self.assertEqual(skills_only["uncertain_skills"], ["Python"])
        self.assertEqual(skills_only["requirements"][0]["status"], "uncertain")

    def test_evidence_quote_is_always_from_the_resume_text(self):
        resume = "EXPERIENCE\nMaintained Python services for customers."
        report = analyze_resume(resume, "Python is required.")

        evidence = report["requirements"][0]["evidence"]
        self.assertIn(evidence, resume)


if __name__ == "__main__":
    unittest.main()

# backend/tests/test_tailor.py
#
# Tests for the AI pipeline logic in tailor.py.
#
# We test three things independently:
#
#   1. _clean_summary — strips model output artifacts like <think> blocks,
#      preamble sentences, and wrapping quotes.
#
#   2. _find_violations — detects when the AI mentions a technology that
#      appears in the job description but NOT in the candidate's skill set.
#      This is the hallucination check — the most important logic in the project.
#
#   3. tailor_resume — the confirmed_summary fast path, which should assemble
#      a TailoredResumeOutput directly without ever calling the AI.
#
# The AI is never called in these tests. The confirmed_summary path avoids it
# entirely, and for the helper functions we're just testing Python logic.

import pytest
from unittest.mock import patch

from schemas.resume import BaseResume, ExperienceEntry, SkillCategory
from tailor import _clean_summary, _find_violations, tailor_resume


# ---------------------------------------------------------------------------
# Shared test fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def base_resume():
    """
    A minimal but valid BaseResume.

    Why a fixture? Several tests need a resume object. Defining it once here
    and injecting it as a parameter means we don't repeat ourselves, and if
    the schema changes, there's only one place to update.
    """
    return BaseResume(
        summary="An experienced engineer.",
        experience=[
            ExperienceEntry(
                company="TechCorp",
                title="Software Engineer",
                bullets=["Built REST APIs"],
            )
        ],
        skills=[
            SkillCategory(category="Languages", entries=["Python", "JavaScript"]),
        ],
    )


# ---------------------------------------------------------------------------
# _clean_summary — model artifact stripping
# ---------------------------------------------------------------------------

class TestCleanSummary:
    def test_strips_think_blocks(self):
        """
        Some models (like Qwen3) wrap their reasoning in <think>...</think>
        before the final answer. This should be stripped entirely.
        """
        raw = "<think>Let me reason through this carefully.</think>\nA professional summary."
        assert _clean_summary(raw) == "A professional summary."

    def test_strips_multiline_think_block(self):
        """The <think> block can span multiple lines — re.DOTALL handles this."""
        raw = "<think>\nLine 1\nLine 2\n</think>\nThe actual summary."
        assert _clean_summary(raw) == "The actual summary."

    def test_strips_preamble(self):
        """
        Models often prefix the answer with a meta-sentence like
        "Here is a professional summary:". That line should be removed.
        """
        raw = "Here is a professional summary:\n\nA great engineer with Python skills."
        result = _clean_summary(raw)
        assert not result.startswith("Here is")
        assert "great engineer" in result

    def test_strips_wrapping_double_quotes(self):
        """Some models wrap the entire summary in straight or curly quotes."""
        raw = '"A great engineer with Python skills."'
        result = _clean_summary(raw)
        assert not result.startswith('"')
        assert not result.endswith('"')

    def test_plain_text_is_unchanged(self):
        """A clean summary with no artifacts should pass through untouched."""
        raw = "A plain summary with no artifacts."
        assert _clean_summary(raw) == "A plain summary with no artifacts."


# ---------------------------------------------------------------------------
# _find_violations — hallucination detection
# ---------------------------------------------------------------------------

class TestFindViolations:
    def test_clean_summary_has_no_violations(self, base_resume):
        """
        A summary that only mentions skills the candidate actually has should
        return an empty list — nothing to flag.
        """
        summary = "An experienced Python developer with JavaScript expertise."
        job = "Looking for a Python or JavaScript engineer."
        violations = _find_violations(summary, base_resume, job)
        assert violations == []

    def test_hallucinated_skill_is_flagged(self, base_resume):
        """
        If the AI mentions Angular — which appears in the job description but
        NOT in the candidate's skill list — it should appear in the violations.

        This is the core scenario the hallucination check was built for: the
        model "borrows" a technology from the job description to make the
        candidate seem more relevant, when in fact they don't have that skill.
        """
        summary = "An experienced Python and Angular developer."
        job = "Looking for a Python and Angular engineer."
        violations = _find_violations(summary, base_resume, job)
        assert "Angular" in violations

    def test_skill_absent_from_job_description_is_not_flagged(self, base_resume):
        """
        A capitalised word that doesn't appear in the job description should
        never be flagged. We only care about tokens the model borrowed from
        the job posting, not tokens it invented from nowhere.
        """
        summary = "An experienced Python developer."
        job = "We need a Backend engineer to work on infrastructure."
        # "Python" is not mentioned in the job description, so it can't be
        # a "borrowed" hallucination. No violations expected.
        violations = _find_violations(summary, base_resume, job)
        assert violations == []

    def test_skill_in_resume_and_job_description_is_not_flagged(self, base_resume):
        """
        If a skill appears in BOTH the job description and the candidate's
        resume, it is not a hallucination — the candidate actually has it.
        """
        summary = "An experienced Python developer."
        job = "We need a Python engineer."
        violations = _find_violations(summary, base_resume, job)
        assert violations == []


# ---------------------------------------------------------------------------
# tailor_resume — confirmed_summary fast path
# ---------------------------------------------------------------------------

class TestTailorResumeFastPath:
    def test_confirmed_summary_skips_ai(self, base_resume):
        """
        When confirmed_summary is provided, the function must return immediately
        without calling the AI client.

        We verify this by patching get_client and asserting it was never called.
        If the AI path were reached by mistake, get_client() would be called and
        the test would fail.
        """
        with patch("tailor.get_client") as mock_get_client:
            tailor_resume(base_resume, "any job description", confirmed_summary="Approved summary.")
            mock_get_client.assert_not_called()

    def test_confirmed_summary_is_used_verbatim(self, base_resume):
        """The output summary must be exactly the string the caller passed in."""
        result = tailor_resume(base_resume, "any job", confirmed_summary="Approved summary.")
        assert result.summary == "Approved summary."

    def test_confirmed_summary_passes_through_experience(self, base_resume):
        """Experience entries must be taken verbatim from the base resume."""
        result = tailor_resume(base_resume, "any job", confirmed_summary="Approved.")
        assert result.experience == base_resume.experience

    def test_confirmed_summary_passes_through_skills(self, base_resume):
        """Skills must be taken verbatim from the base resume."""
        result = tailor_resume(base_resume, "any job", confirmed_summary="Approved.")
        assert result.skills == base_resume.skills

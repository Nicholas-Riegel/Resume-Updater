# backend/tests/test_schemas.py
#
# Tests for the Pydantic schemas in schemas/resume.py.
#
# Pydantic validates data when you create a model instance. These tests check:
#   - Valid data parses without errors and the fields contain what we expect.
#   - Missing required fields raise a ValidationError.
#   - Wrong types raise a ValidationError.
#
# We don't test every possible bad input — just enough to confirm the schema
# is wired up correctly and would catch a badly formed base_resume.json.

import pytest
from pydantic import ValidationError

from schemas.resume import BaseResume, TailoredResumeOutput, ExperienceEntry, SkillCategory


# ---------------------------------------------------------------------------
# Minimal valid data — reused across multiple tests
# ---------------------------------------------------------------------------

VALID_EXPERIENCE = [
    {
        "company": "Acme Corp",
        "title": "Software Engineer",
        "bullets": ["Built APIs", "Fixed bugs"],
    }
]

VALID_SKILLS = [
    {"category": "Languages", "entries": ["Python", "JavaScript"]}
]


# ---------------------------------------------------------------------------
# ExperienceEntry
# ---------------------------------------------------------------------------

class TestExperienceEntry:
    def test_required_fields_only(self):
        """company, title, and bullets are required; the rest are optional."""
        entry = ExperienceEntry(company="Acme", title="Engineer", bullets=["Did things"])
        assert entry.company == "Acme"
        assert entry.location is None
        assert entry.start_date is None

    def test_optional_fields_accepted(self):
        entry = ExperienceEntry(
            company="Acme",
            title="Engineer",
            location="Remote",
            start_date="Jan 2023",
            end_date="Present",
            bullets=["Did things"],
        )
        assert entry.location == "Remote"
        assert entry.start_date == "Jan 2023"

    def test_missing_company_raises(self):
        with pytest.raises(ValidationError):
            ExperienceEntry(title="Engineer", bullets=["Did things"])

    def test_missing_bullets_raises(self):
        with pytest.raises(ValidationError):
            ExperienceEntry(company="Acme", title="Engineer")

    def test_bullets_must_be_list(self):
        with pytest.raises(ValidationError):
            ExperienceEntry(company="Acme", title="Engineer", bullets="not a list")


# ---------------------------------------------------------------------------
# SkillCategory
# ---------------------------------------------------------------------------

class TestSkillCategory:
    def test_valid_data_parses(self):
        cat = SkillCategory(category="Languages", entries=["Python", "Go"])
        assert cat.category == "Languages"
        assert "Python" in cat.entries

    def test_missing_category_raises(self):
        with pytest.raises(ValidationError):
            SkillCategory(entries=["Python"])

    def test_missing_entries_raises(self):
        with pytest.raises(ValidationError):
            SkillCategory(category="Languages")


# ---------------------------------------------------------------------------
# BaseResume
# ---------------------------------------------------------------------------

class TestBaseResume:
    def test_valid_data_parses(self):
        """A fully populated BaseResume should parse without errors."""
        resume = BaseResume(experience=VALID_EXPERIENCE, skills=VALID_SKILLS)
        assert resume.experience[0].company == "Acme Corp"
        assert resume.skills[0].category == "Languages"

    def test_summary_defaults_to_none(self):
        """summary is Optional — it should be None when omitted."""
        resume = BaseResume(experience=VALID_EXPERIENCE, skills=VALID_SKILLS)
        assert resume.summary is None

    def test_summary_is_accepted(self):
        resume = BaseResume(
            summary="A great engineer.",
            experience=VALID_EXPERIENCE,
            skills=VALID_SKILLS,
        )
        assert resume.summary == "A great engineer."

    def test_missing_experience_raises(self):
        """experience is required — omitting it should raise ValidationError."""
        with pytest.raises(ValidationError):
            BaseResume(skills=VALID_SKILLS)

    def test_missing_skills_raises(self):
        """skills is required — omitting it should raise ValidationError."""
        with pytest.raises(ValidationError):
            BaseResume(experience=VALID_EXPERIENCE)

    def test_wrong_type_for_experience_raises(self):
        """experience must be a list — passing a string should raise ValidationError."""
        with pytest.raises(ValidationError):
            BaseResume(experience="not a list", skills=VALID_SKILLS)


# ---------------------------------------------------------------------------
# TailoredResumeOutput
# ---------------------------------------------------------------------------

class TestTailoredResumeOutput:
    def test_valid_data_parses(self):
        output = TailoredResumeOutput(
            summary="Tailored summary.",
            experience=VALID_EXPERIENCE,
            skills=VALID_SKILLS,
        )
        assert output.summary == "Tailored summary."
        assert len(output.experience) == 1
        assert len(output.skills) == 1

    def test_summary_defaults_to_none(self):
        output = TailoredResumeOutput(experience=VALID_EXPERIENCE, skills=VALID_SKILLS)
        assert output.summary is None

    def test_missing_experience_raises(self):
        with pytest.raises(ValidationError):
            TailoredResumeOutput(summary="Summary.", skills=VALID_SKILLS)

    def test_missing_skills_raises(self):
        with pytest.raises(ValidationError):
            TailoredResumeOutput(summary="Summary.", experience=VALID_EXPERIENCE)

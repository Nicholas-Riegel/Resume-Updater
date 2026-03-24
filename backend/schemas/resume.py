# Pydantic is a Python library for defining data structures with automatic validation.
# We import BaseModel (the base class for all our schemas) and Optional
# (to mark fields that don't have to be present).
from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------------------------
# Building blocks — these smaller models get composed into the full resume
# ---------------------------------------------------------------------------

class SkillCategory(BaseModel):
    # Represents one row in the skills section, e.g.:
    # { "category": "Languages", "entries": ["Python", "JavaScript"] }
    # In the template: {{ cat.category }}: {{ cat.entries | join(", ") }}
    # NOTE: field is named 'entries' not 'items' — 'items' clashes with the
    # built-in dict.items() method, which breaks Jinja2 attribute lookup.
    category: str
    entries: list[str]


class ExperienceEntry(BaseModel):
    company: str                     # e.g. "Acme Corp"
    title: str                       # e.g. "Software Engineer"
    start_date: Optional[str] = None # stored as a plain string (e.g. "Jan 2021") — omit to hide dates on the resume
    end_date: Optional[str] = None   # e.g. "Mar 2023" or "Present" — omit to hide dates on the resume
    # Dates are strings, not date objects — resume formats vary too much to parse reliably.
    bullets: list[str]               # the bullet points describing what you did in this role

# ---------------------------------------------------------------------------
# Top-level schemas
# ---------------------------------------------------------------------------

class BaseResume(BaseModel):
    """
    The complete, unmodified resume — loaded from base_resume.json.
    This is the single source of truth. The AI reads from it but never writes to it.
    """
    summary: Optional[str] = None    # a short professional summary — not everyone has one
    experience: list[ExperienceEntry]
    skills: list[SkillCategory]      # categorised, e.g. [{category: "Languages", items: [...]}]


class TailoredExperienceEntry(BaseModel):
    """
    One experience entry as rewritten by the AI.
    Kept as a separate type from ExperienceEntry so we can add
    AI-specific validation rules here later (e.g. checking that the
    company name actually exists in the base resume).
    """
    company: str
    title: str
    start_date: Optional[str] = None  # mirrors ExperienceEntry — optional so dates can be hidden
    end_date: Optional[str] = None
    bullets: list[str]               # reworded/reordered bullets — no new facts allowed


class TailoredResumeOutput(BaseModel):
    """
    The full output returned by the AI after tailoring.
    Mirrors BaseResume in structure, but is a separate type so it can be
    validated independently before it touches the document generator.
    """
    summary: Optional[str] = None    # AI may write or refine a summary for the specific job
    skills: list[SkillCategory]      # AI may reorder categories/items to prioritise what the job asks for
    experience: list[TailoredExperienceEntry]
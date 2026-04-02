# backend/tests/test_api.py
#
# Tests for the FastAPI endpoints in main.py.
#
# We use FastAPI's TestClient to send HTTP requests without running a live server.
# TestClient works by calling the ASGI app directly inside the same process —
# no network, no ports, just function calls. This makes the tests fast and
# self-contained.
#
# All calls to tailor_resume() are mocked so Ollama doesn't need to be running.
# The document generator (generate_resume_docx) is NOT mocked — it runs for
# real, so /generate tests confirm the full pipeline from "confirmed summary"
# to a valid .docx file.
#
# Note: the `reset_rate_limiter` fixture in tests/conftest.py runs automatically
# before each test (autouse=True) to prevent the 6/minute rate limit from
# interfering between tests.

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from schemas.resume import TailoredResumeOutput, ExperienceEntry, SkillCategory


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_tailored_output(summary: str = "A tailored summary.") -> TailoredResumeOutput:
    """
    Return a minimal TailoredResumeOutput to use as the mock return value for
    tailor_resume(). We need a real object (not a MagicMock) because the app
    passes it to generate_resume_docx(), which accesses actual fields on it.
    """
    return TailoredResumeOutput(
        summary=summary,
        experience=[
            ExperienceEntry(
                company="Mock Corp",
                title="Engineer",
                bullets=["Did things"],
            )
        ],
        skills=[SkillCategory(category="Languages", entries=["Python"])],
    )


# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """
    Create a TestClient for the duration of each test.

    TestClient wraps the FastAPI app in a requests-compatible interface.
    It handles the ASGI event loop internally, so we don't need async tests.
    """
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /preview
# ---------------------------------------------------------------------------

class TestPreview:
    def test_valid_job_description_returns_200(self, client):
        """A valid job description should return 200 and a JSON body."""
        with patch("main.tailor_resume", return_value=make_tailored_output()):
            response = client.post("/preview", data={"job_description": "We need a Python engineer."})
        assert response.status_code == 200

    def test_response_contains_summary_key(self, client):
        """The JSON body must have a 'summary' key."""
        with patch("main.tailor_resume", return_value=make_tailored_output()):
            response = client.post("/preview", data={"job_description": "We need a Python engineer."})
        assert "summary" in response.json()

    def test_summary_is_a_non_empty_string(self, client):
        """The summary value should be a non-empty string."""
        with patch("main.tailor_resume", return_value=make_tailored_output("Great engineer.")):
            response = client.post("/preview", data={"job_description": "Python role."})
        body = response.json()
        assert isinstance(body["summary"], str)
        assert len(body["summary"]) > 0

    def test_missing_job_description_returns_422(self, client):
        """
        Sending a POST with no form data should return 422 Unprocessable Entity.

        FastAPI validates required Form fields automatically and returns 422
        when they're missing — we don't need to write any validation code for this.
        """
        response = client.post("/preview", data={})
        assert response.status_code == 422

    def test_blank_job_description_returns_422(self, client):
        """
        A whitespace-only job description is caught by our explicit check in
        main.py and returned as 422.
        """
        response = client.post("/preview", data={"job_description": "   "})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

# The MIME type that Word documents use — we check the Content-Type header to
# confirm the response is a .docx file and not, say, a JSON error body.
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class TestGenerate:
    def test_valid_request_returns_200(self, client):
        """A valid job description and confirmed summary should return 200."""
        with patch("main.tailor_resume", return_value=make_tailored_output()):
            response = client.post(
                "/generate",
                data={
                    "job_description": "We need a Python engineer.",
                    "summary": "A confirmed summary.",
                },
            )
        assert response.status_code == 200

    def test_response_is_docx(self, client):
        """The Content-Type header should identify the response as a .docx file."""
        with patch("main.tailor_resume", return_value=make_tailored_output()):
            response = client.post(
                "/generate",
                data={
                    "job_description": "We need a Python engineer.",
                    "summary": "A confirmed summary.",
                },
            )
        assert response.headers["content-type"] == DOCX_CONTENT_TYPE

    def test_confirmed_summary_is_passed_to_tailor(self, client):
        """
        When a summary is provided, main.py should call tailor_resume() with
        confirmed_summary set to that exact string.

        This matters because tailor_resume() fast-paths when confirmed_summary
        is set — it skips the AI and assembles the output directly. If main.py
        wasn't passing the confirmed_summary through, the AI would be called
        again unnecessarily, potentially producing a different (or wrong) result.
        """
        with patch("main.tailor_resume", return_value=make_tailored_output()) as mock:
            client.post(
                "/generate",
                data={
                    "job_description": "Python role.",
                    "summary": "Pre-approved summary.",
                },
            )
        # call_args unpacks as (positional_args, keyword_args)
        _, kwargs = mock.call_args
        assert kwargs.get("confirmed_summary") == "Pre-approved summary."

    def test_missing_job_description_returns_422(self, client):
        """Omitting job_description entirely should return 422."""
        response = client.post("/generate", data={"summary": "A summary."})
        assert response.status_code == 422

    def test_blank_job_description_returns_422(self, client):
        """A whitespace-only job description should be rejected with 422."""
        response = client.post(
            "/generate",
            data={"job_description": "   ", "summary": "A summary."},
        )
        assert response.status_code == 422

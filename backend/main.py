# The FastAPI application.
#
# Exposes two endpoints:
#   POST /preview
#     - accepts a job description as a form field
#     - calls the AI to generate a tailored summary
#     - returns {"summary": "..."} as JSON (no document built)
#
#   POST /generate
#     - accepts a job description and an optional pre-approved summary
#     - if summary is provided, skips the AI and builds the DOCX directly
#     - if summary is absent, runs the full AI pipeline first
#     - returns the tailored resume as a .docx file download
#
# Run with:
#   uvicorn main:app --reload --port 8000

import json
import tempfile
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from schemas.resume import BaseResume
from tailor import tailor_resume
from generate_docx import generate_resume_docx

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
# get_remote_address pulls the caller's IP from the request, which slowapi
# uses to track and enforce per-IP request limits.
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Resume Tailoring API")

# Attach the rate limiter to the app so it can intercept requests.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS — allow requests from the Chrome extension and local dev tools
# ---------------------------------------------------------------------------
# Why is CORS needed? Browsers (and Chrome extensions) block cross-origin
# requests by default. Without this middleware, the extension would be silently
# refused when it tries to POST to localhost:8000.
#
# "chrome-extension://*" covers any installed version of our extension.
# "http://localhost" / "http://127.0.0.1" cover manual testing in the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
    ],
    # CORSMiddleware does exact string matching on allow_origins — wildcards
    # don't work there. allow_origin_regex accepts a regex pattern instead,
    # which is the correct way to allow any chrome-extension:// origin.
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Base resume — loaded once at startup
# ---------------------------------------------------------------------------
# We load and validate the base resume when the server starts rather than on
# every request — the file doesn't change while the server is running, so
# there's no reason to re-read it each time.
_DATA_PATH = Path(__file__).parent / "data" / "base_resume.json"

with open(_DATA_PATH) as f:
    _BASE_RESUME = BaseResume(**json.load(f))

# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/generate")
@limiter.limit("6/minute")
async def generate(
    request: Request,
    job_description: str = Form(...),
    summary: str | None = Form(None),  # optional: pre-approved summary from Stage 1
):
    """
    Stage 2 of the two-stage popup UX — also works standalone (e.g. curl tests).

    If `summary` is provided (the user reviewed it in Stage 1 via /preview),
    we pass it straight to tailor_resume() as confirmed_summary — so the AI
    is bypassed entirely and the DOCX contains exactly the text the user approved.

    If `summary` is absent (e.g. a direct curl call without Stage 1), we run
    the full AI pipeline as normal for backward compatibility.

    `summary: str | None = Form(None)` tells FastAPI this is an optional form
    field — it's fine if the caller doesn't include it.
    """
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="job_description is required.")

    try:
        # Pass confirmed_summary only if a non-empty summary was provided.
        # `summary or None` converts an empty string to None — treating it the
        # same as a missing field so we don't accidentally build a blank document.
        result = tailor_resume(_BASE_RESUME, job_description, confirmed_summary=summary or None)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    tmp.close()
    output_path = Path(tmp.name)

    generate_resume_docx(result, output_path)

    filename = f"resume_{date.today()}.docx"

    from starlette.background import BackgroundTask
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        background=BackgroundTask(output_path.unlink),
    )

@app.post("/preview")
@limiter.limit("6/minute")   # same rate limit as /generate
async def preview(request: Request, job_description: str = Form(...)):
    """
    Stage 1 of the two-stage popup UX.

    Runs the full AI pipeline and returns just the generated summary as JSON
    — so the user can read and optionally edit it in the popup before the
    DOCX is created. No document is built here.

    Returns: {"summary": "<AI-generated summary text>"}
    """
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="job_description is required.")

    try:
        result = tailor_resume(_BASE_RESUME, job_description)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # FastAPI automatically serialises a plain dict to a JSON response.
    return {"summary": result.summary}
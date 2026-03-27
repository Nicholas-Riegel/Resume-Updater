# The FastAPI application.
#
# Exposes one endpoint:
#   POST /generate
#     - accepts a job description as a form field
#     - loads the base resume from disk
#     - calls the AI to tailor the summary
#     - generates a DOCX file
#     - returns it as a file download
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
@limiter.limit("6/minute")   # at most 6 tailoring requests per minute per IP
async def generate(request: Request, job_description: str = Form(...)):
    """
    Accept a job description, tailor the resume, and return a DOCX file.

    `request` must be the first argument because slowapi needs access to the
    raw request object to read the caller's IP for rate limiting. FastAPI
    injects it automatically.

    `job_description: str = Form(...)` tells FastAPI to read a form field
    called `job_description` from the POST body. The `...` means it's required
    — FastAPI will return a 422 error automatically if it's missing.
    """
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="job_description is required.")

    # Run the AI pipeline
    try:
        result = tailor_resume(_BASE_RESUME, job_description)
    except RuntimeError as e:
        # tailor_resume raises RuntimeError if all retries are exhausted
        raise HTTPException(status_code=502, detail=str(e))

    # Write the DOCX to a temporary file.
    # NamedTemporaryFile with delete=False creates a file that persists after
    # the `with` block closes — FastAPI's FileResponse needs it to still exist
    # when it streams the bytes back to the caller.
    # We clean it up manually using a BackgroundTask (see below).
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    tmp.close()
    output_path = Path(tmp.name)

    generate_resume_docx(result, output_path)

    # Build a clean filename: resume_YYYY-MM-DD.docx
    filename = f"resume_{date.today()}.docx"

    # FileResponse streams the file back to the caller as a download.
    # background= is a FastAPI hook that runs after the response is sent —
    # we use it to delete the temp file once it's no longer needed.
    from starlette.background import BackgroundTask
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        background=BackgroundTask(output_path.unlink),
    )
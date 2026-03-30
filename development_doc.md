# AI Resume Tailoring — Development Checklist

---

## About This Project

A Chrome extension + Python backend that lets you click a button on any job listing and automatically download a tailored resume. The extension scrapes the job description, sends it to a local FastAPI server, which uses an AI model (Ollama, running locally) to reword and reorder your existing resume to match the job — then generates a formatted DOCX or PDF file that downloads directly in the browser.

**Core rule:** The AI never invents experience. It can only reword and reorder what's already in your base resume. All AI output is validated before it touches the document.

**Stack at a glance:**
- **Backend:** Python, FastAPI, Pydantic
- **AI:** Ollama (local, no cost) — switchable to OpenAI if needed
- **Document output:** DOCX via `docxtpl`, or PDF via `WeasyPrint`
- **Frontend:** Chrome Extension (Manifest V3)

---

## How We're Working

- **This is a learning project.** A lot of this stack is new. Explanations matter as much as the code.
- **Step by step.** Before any code is written, I'll explain what we're about to do and why. No code gets written without your go-ahead.
- **You do the hands-on steps.** You create the files, folders, and run the installs yourself. I provide the exact commands and code.
- **Code is written to be readable.** Every file will be well-commented — not just *what* the code does, but *why* it's written that way.
- **One phase at a time.** We complete and verify each phase before moving to the next.

---

## Phase 0: Schema Design

Define the data structures for the resume and the AI output before writing any other code.

### Setup

- [x] Create the project folder structure:

  ```
  Resume Updater/
  ├── backend/
  │   ├── schemas/
  │   │   └── resume.py
  │   ├── data/
  │   │   └── base_resume.json
  │   └── requirements.txt
  ├── .env
  ├── .gitignore
  ├── planning_doc.md
  └── development_doc.md
  ```

  ```bash
  mkdir -p backend/schemas backend/data
  touch backend/schemas/__init__.py
  touch backend/schemas/resume.py
  touch backend/data/base_resume.json
  touch backend/requirements.txt
  touch .env
  touch .gitignore
  ```

- [x] Create and activate a Python virtual environment:

  ```bash
  cd backend
  python3 -m venv .venv
  source .venv/bin/activate
  cd ..
  ```

- [x] Create `backend/requirements.txt` with all project dependencies:

  ```
  # Core backend
  fastapi
  uvicorn            # runs the FastAPI development server
  pydantic
  python-dotenv      # loads .env file for API keys and config

  # Document generation
  docxtpl            # DOCX templating (Jinja2 on top of python-docx)
  weasyprint         # HTML → PDF rendering

  # AI
  openai             # works with both OpenAI and Ollama (same SDK, different base URL)
  ```

  > `python-multipart` and `slowapi` will be added in Phase 3 when the API endpoint is built.

- [x] Install all dependencies:

  ```bash
  cd backend
  source .venv/bin/activate
  pip install -r requirements.txt
  cd ..
  ```

- [x] Create `.gitignore` (in the root `Resume Updater/` folder) to prevent secrets and junk from being committed:

  ```
  backend/.venv/
  .env
  __pycache__/
  *.pyc
  .DS_Store
  ```

- [x] Add a placeholder to `.env` in the project root (you'll fill in real values when needed):

  ```
  # AI provider: "ollama" (default, local) or "openai"
  AI_PROVIDER=ollama

  # Only needed if AI_PROVIDER=openai
  OPENAI_API_KEY=
  ```

### Schemas

- [x] Write `BaseResume` Pydantic schema in `backend/schemas/resume.py` (name, contact, summary, experience, skills, education)
- [x] Write `TailoredResumeOutput` Pydantic schema in the same file (mirrors `BaseResume`; represents AI output only)

### Sample data

- [x] Populate `backend/data/base_resume.json` with realistic sample data matching the `BaseResume` schema

### Verification

- [x] Write a temporary `backend/verify_schema.py` that loads `base_resume.json` and parses it with `BaseResume` — confirm it runs without errors
- [x] Delete `verify_schema.py` once passing

---

## Phase 1: Document Generation Prototypes

Two approaches to generating the resume document are prototyped using **static** sample data (from `base_resume.json`). The goal is to evaluate output quality before any AI is involved — so you're not debugging formatting and AI at the same time.

The two approaches are:
- **DOCX** via `docxtpl` — editable Word document, ATS-friendly
- **HTML → PDF** via `WeasyPrint` — precise layout control

At the end of this phase you'll pick a primary format (or decide to support both) before moving to Phase 2.

---

### Setup

- [x] Create a `backend/templates/` folder to hold all document templates:

  ```bash
  mkdir -p backend/templates
  ```

- [x] Create a `backend/output/` folder where generated files will be saved during development, and gitignore it so test files are never committed:

  ```bash
  mkdir -p backend/output
  echo "backend/output/" >> .gitignore
  ```

---

### Prototype A — DOCX via `docxtpl`

`docxtpl` uses a real `.docx` file as its template. You place Jinja2-style placeholders (like `{{ name }}`) directly inside the Word document, then fill them in from Python. The result is a proper `.docx` — editable, ATS-compatible, and looks exactly like your template.

- [x] Create the Word template `backend/templates/resume_template.docx`:

  Open Word (or Google Docs → *Download as .docx*) and design a clean, single-column resume with these sections in this order:
  - **Header** — `{{ name }}` and contact details (`{{ contact.email }}`, `{{ contact.phone }}`, etc.)
  - **Summary** — `{{ summary }}`
  - **Experience** — a `{% for job in experience %}` loop with each job's title, company, dates, and a nested `{% for bullet in job.bullets %}` loop
  - **Skills** — `{% for skill in skills %}` loop (or a joined string)
  - **Education** — `{% for edu in education %}` loop

  Save it as `backend/templates/resume_template.docx`.

  > **Why a real `.docx` as the template?** `docxtpl` works by unzipping the `.docx` (which is just a ZIP of XML files), finding your Jinja2 tags in the XML, swapping them for real data, and rezipping it. The template *must* be a real `.docx` — you control all fonts, spacing, and margins inside Word; Python only handles the data substitution.

  > **ATS compatibility:** Keep it strictly single-column. No text boxes, no tables used for layout, no important content inside Word headers/footers, no inline images. Section headings like "Experience", "Education", and "Skills" should appear as plain paragraph text, not inside decorative elements.

- [x] Write `backend/generate_docx.py`:

- [x] Run the script and verify the output:

  ```bash
  cd backend
  source .venv/bin/activate
  python generate_docx.py
  cd ..
  ```

  Open `backend/output/resume_sample.docx` and check:
  - All placeholder data is filled in (name, contact, each job, skills, education)
  - No raw Jinja2 tags are visible (e.g. `{{ name }}`) — if you see one, the placeholder name in the template doesn't match the key name in the JSON
  - Formatting looks clean and the layout is as you designed

---

### Prototype B — HTML → PDF via `WeasyPrint`

`WeasyPrint` converts an HTML + CSS string to a PDF entirely in Python — no browser required. You write a Jinja2 HTML template, render it into a plain HTML string with Python's `jinja2` library, then hand that string to WeasyPrint to produce the PDF.

- [x] ~~Create `backend/templates/resume_template.html`~~ — **Skipped.** DOCX was chosen as the primary format after Prototype A succeeded. PDF output is not editable and has worse ATS compatibility.

  Design this as a clean, single-page resume. Key things to include:
  - A CSS `@page` rule to set paper size (`size: Letter`) and margins
  - Section headings for Experience, Skills, Education as styled `<h2>` tags
  - A `{% for job in experience %}` loop for experience entries, and a nested `{% for bullet in job.bullets %}` loop for the bullet points
  - Print-friendly typography — use system fonts (e.g. `font-family: Georgia, serif`) so no internet connection is needed to render

  > **Why HTML → PDF?** This gives you exact pixel-level control over layout, padding, and spacing via CSS — far more precise than styling a Word document. The tradeoff: the output is a fixed PDF, not an editable `.docx`.

- [x] ~~Write `backend/generate_pdf.py`~~ — **Skipped.** See above.

---

### Decision Point

- [x] Review both outputs side by side and decide on the primary format:

  > **Decision:** DOCX only. PDF output is not editable and performs worse with ATS systems. Prototype B was skipped — Prototype A was sufficient to confirm the approach.

---

## Phase 2: Template Polish

**Approach revised:** Rather than styling a `.docx` template in LibreOffice, this phase was completed by rewriting `generate_docx.py` to build the document **fully programmatically** using `python-docx` directly. All fonts, spacing, colors, section headers, bullet indentation, and borders are set in Python code. No separate template file is needed.

### Goals for this phase *(all met via `python-docx`)*
- Name displayed large and bold at the top
- Contact details on a single line, readable
- Section headings (EXPERIENCE, SKILLS, EDUCATION) bold and visually distinct
- Each job entry: title bold, company and date range cleanly formatted
- Bullet points rendered as actual list items
- Skills as a comma-separated line (not a blob)
- Special characters (e.g. `&`) rendering correctly
- Output looks submission-ready when opened in LibreOffice

### Steps

- [x] ~~Fix skills rendering in the template~~ — **Done programmatically.** The `SkillCategory` schema (`{ category: str, entries: list[str] }`) is used. Each category renders as a paragraph with a bold label run followed by `", ".join(cat["entries"])`. No Jinja2 filter needed.

- [x] ~~Fix `&` character escaping~~ — **Not needed.** `python-docx` handles all XML escaping internally; Jinja2 filters are no longer in the pipeline.

- [x] ~~Style the template in LibreOffice~~ — **Done programmatically in `generate_docx.py`:**
  - Font: Calibri, 10pt body / 9.5pt for secondary lines (company, dates, contact)
  - Colors: near-black `#1A1A1A` for body text, dark gray `#555555` for secondary lines
  - Section headers: bold text + thin light-gray bottom border (raw OOXML `w:pBdr`)
  - Bullet points: en-dash character, hanging indent (0.25" left, −0.18" first-line)
  - Paragraph spacing: 3pt after body, 2pt after bullets, 10pt after contact block
  - Page margins: 0.75" all round
  - Header (name, title, citizenship, contact line) hardcoded in the script

- [x] ~~Save the template as `resume_template.docx`~~ — **N/A.** Document is built fully in Python; no template file is used.

- [x] Re-run `generate_docx.py` and open the output — **Done. Output confirmed as professional-looking and ready to move forward.**

  ```bash
  cd backend
  source .venv/bin/activate
  python generate_docx.py
  cd ..
  ```

---

## Phase 3: AI Integration

This phase connects the AI model to the resume schema. The goal is a function that takes a job description and a base resume, calls the AI, and returns a `TailoredResumeOutput` object — ready to hand straight to the document generator.

No API endpoint yet. No Chrome extension. Just the AI pipeline on its own, tested directly in Python.

**v1 approach — summary-only tailoring:**

The AI's only job is to write a tailored summary paragraph. Everything else (experience, bullets, skills) is taken verbatim from the base resume. This keeps the AI task simple, works reliably on small local models, and eliminates any risk of dropped content.

```
base_resume.json
    ↓
build_prompt(base_resume, job_description)    ← prompts.py
    ↓
AI model (Ollama or OpenAI)                   ← ai_client.py
    ↓
plain summary string
    ↓
TailoredResumeOutput(                         ← assembled in tailor.py
    summary  = ai_summary,
    skills   = base_resume.skills,            ← passed through unchanged
    experience = base_resume.experience,      ← passed through unchanged
)
    ↓
TailoredResumeOutput object                   ← ready for generate_docx.py
```

---

### Setup

The `openai` SDK is already installed from Phase 0. No new packages are needed for this phase.

Make sure Ollama is running before you test:

```bash
ollama serve
```

And pull the model you want to use if you haven't already:

```bash
ollama pull llama3.2
```

> **Why `llama3.2`?** It's a capable model that runs well locally and supports JSON output reliably. You can swap in any other Ollama model by changing `OLLAMA_MODEL` in `.env` — no other code changes needed.

---

### Step 1 — AI provider abstraction (`backend/ai_client.py`)

This file creates a single `get_client()` function that returns a configured OpenAI SDK client pointing at either Ollama or the real OpenAI API — based on the `AI_PROVIDER` value in `.env`. Everything else in the codebase calls `get_client()` and never worries about which provider is active.

- [x] Add the following to `.env`:

  ```
  # AI provider: "ollama" (default, local) or "openai"
  AI_PROVIDER=ollama

  # Ollama settings
  OLLAMA_BASE_URL=http://localhost:11434/v1
  OLLAMA_MODEL=llama3.2

  # Only needed if AI_PROVIDER=openai
  OPENAI_API_KEY=
  OPENAI_MODEL=gpt-4o
  ```

- [x] Create `backend/ai_client.py`:

---

### Step 2 — Prompt builder (`backend/prompts.py`)

This file contains one function: `build_prompt()`. It takes the validated base resume and an untrusted job description, applies sanitization to the job description, and returns the system and user messages to send to the AI.

The two messages serve different purposes:
- **System message:** instructions to the AI (what it's allowed to do, what format to return)
- **User message:** data for the AI to work with (the resume and job description)

This separation matters — models treat system instructions as higher authority than user content.

- [x] Create `backend/prompts.py`:

---

### Step 3 — AI tailor function (`backend/tailor.py`)

This file ties everything together. It calls the AI, extracts the JSON from the response, parses it with Pydantic, and retries if anything goes wrong. The function returns a validated `TailoredResumeOutput` — or raises an exception if it fails after all retries.

- [x] Create `backend/tailor.py`:

---

### Step 4 — Test the pipeline

Before building the API endpoint, verify the AI pipeline works end-to-end: feed it a real job description and confirm you get back a valid, sensible `TailoredResumeOutput`.

- [x] Create `backend/test_tailor.py`:

- [x] Run the test and check the output:

  ```bash
  cd backend
  source .venv/bin/activate
  python test_tailor.py
  cd ..
  ```

  What you're looking for:
  - No Python errors or tracebacks
  - The output is a JSON object with `summary`, `skills`, and `experience` keys
  - The `summary` is a coherent 2–3 sentence paragraph tailored to the job description
  - The `skills` and `experience` sections are identical to `base_resume.json` — untouched
  - No invented roles, dates, or technologies

---

### Step 5 — Revise for v1 summary-only approach

Steps 2 and 3 built `prompts.py` and `tailor.py` for a full-resume rewrite. We're now simplifying to summary-only for v1. Both files need to be updated.

**`prompts.py`** — ask the AI for a plain summary string only (no JSON):

- [x] Replace the contents of `backend/prompts.py` with:

**`tailor.py`** — receive the plain summary string and assemble the full output from the base resume:

- [x] Replace the contents of `backend/tailor.py` with:

- [x] Re-run `python test_tailory.py` and verify:
  - The `summary` field is a new, job-relevant paragraph (not the original from `base_resume.json`)
  - The `experience` and `skills` sections are identical to `base_resume.json` — all 4 roles, all bullets, all categories

- [x] Delete `test_tailor.py` once you're satisfied the pipeline is working.

---

### ~~Step 6 — Verify the OpenAI provider path~~ — **Skipped.** OpenAI API requires a paid account (separate from ChatGPT). Ollama is confirmed working and is the default for all development. The provider switch in `ai_client.py` is straightforward — this step can be revisited if OpenAI access becomes available later. The test script is preserved below for reference.

<details>
<summary>Test script (for future reference)</summary>

```python
# backend/test_openai.py
#
# Temporary smoke-test for the OpenAI provider path.
# Delete this file once the test passes.

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas.resume import BaseResume
from tailor import tailor_resume

data_path = Path(__file__).parent / "data" / "base_resume.json"
with open(data_path) as f:
    raw = json.load(f)
resume = BaseResume(**raw)

job_description = """
We're looking for a software engineer with experience in Python and web development.
You'll build internal tools and APIs, collaborate closely with product and design,
and contribute to a culture of technical excellence. Strong communication skills
and the ability to work independently are essential.
"""

print("Calling OpenAI API...")
result = tailor_resume(resume, job_description)

print("\n--- Tailored Summary ---")
print(result.summary)

print(f"\n--- Experience entries: {len(result.experience)} (expected 4) ---")
for job in result.experience:
    print(f"  • {job.title} @ {job.company}")

print(f"\n--- Skill categories: {len(result.skills)} ---")
for cat in result.skills:
    print(f"  • {cat.category}")

print("\nDone.")
```

To run: set `AI_PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`, then `python backend/test_openai.py`. Revert `.env` to `ollama` after.

</details>

---

## Phase 4: FastAPI Endpoint

**Goal:** Expose the AI pipeline as an HTTP API so the Chrome extension (Phase 5) can send a job description and receive a tailored DOCX file in return.

By the end of this phase:
- A single endpoint — `POST /generate` — accepts a job description and returns a downloadable `.docx` file
- The full pipeline runs end-to-end: job description in → AI summary → assembled resume → DOCX → browser download
- The server is running locally and can be called with `curl` to verify it works before any extension code is written

### New packages needed

Two extra packages are required for Phase 4 that weren't needed before:

| Package | Why |
|---|---|
| `python-multipart` | Required by FastAPI to parse `multipart/form-data` requests (how we'll send the job description from the extension) |
| `slowapi` | Rate limiting — prevents the endpoint from being hammered while the server is running on your local machine |

- [x] Add both to `backend/requirements.txt`:

  Open `backend/requirements.txt` and add a new section at the bottom:

  ```
  # API / server
  python-multipart   # required by FastAPI to parse form data
  slowapi            # rate limiting for the /generate endpoint
  ```

- [x] Install them:

  ```bash
  cd backend
  source .venv/bin/activate
  pip install python-multipart slowapi
  cd ..
  ```

---

### Step 1 — Refactor `generate_docx.py` into a callable function

Right now `generate_docx.py` is a **standalone script** — it runs top-to-bottom when you call `python generate_docx.py`, pulling data from `base_resume.json` and hardcoding the output path. That's fine for prototyping, but the FastAPI endpoint needs to call it as a **function** — passing in a `TailoredResumeOutput` object and getting a file path back.

This step rewrites `generate_docx.py` so:
- All the document-building logic is wrapped in a function `generate_resume_docx(resume, output_path)`
- A small `if __name__ == "__main__":` block at the bottom preserves the old standalone behaviour (so you can still run `python generate_docx.py` manually to check the output)

- [x] Rewrite `backend/generate_docx.py` to wrap the document logic in a function:

  The current file builds the document in a big top-level block. The change is:
  1. Add `from schemas.resume import TailoredResumeOutput` to the imports (instead of `BaseResume`)
  2. Wrap all the document-building code in `def generate_resume_docx(resume: TailoredResumeOutput, output_path: Path) -> Path:`
  3. Replace all hardcoded field references (e.g. `resume.experience`) with references to the `resume` parameter
  4. Have the function `return output_path` after saving
  5. Move the data loading + `generate_resume_docx(...)` call into an `if __name__ == "__main__":` block at the bottom

- [x] Verify the refactor didn't break anything by running the standalone mode:

  ```bash
  cd backend
  source .venv/bin/activate
  python generate_docx.py
  cd ..
  ```

  Open `backend/output/resume_sample.docx` — it should look exactly the same as before.

---

### Step 2 — Write `main.py`

`main.py` is the FastAPI application. It defines the server, the CORS rules, the rate limiter, and the single `POST /generate` endpoint.

**How the endpoint works:**

```
POST /generate
  ├── receives: job_description (form field, plain text)
  ├── loads:    base_resume.json from disk
  ├── calls:    tailor_resume(resume, job_description)   → TailoredResumeOutput
  ├── calls:    generate_resume_docx(result, tmp_path)   → .docx file
  └── returns:  FileResponse (browser downloads the file)
```

Why form data (not JSON)? The Chrome extension will send a simple HTML form-style POST — one field, plain text. This is simpler and more reliable from a browser extension than sending a JSON body.

Why load `base_resume.json` from disk on every request? For now this is fine — the file is small and local. Phase 5 may revisit this if we want the user to upload their own resume from the extension.

- [x] Create `backend/main.py` (note: `request` parameter requires `: Request` type annotation for slowapi to work — added `Request` to the `fastapi` import and typed the parameter):

---

### Step 3 — Run the server and test with `curl`

- [x] Start the development server:

  ```bash
  cd backend
  source .venv/bin/activate
  uvicorn main:app --reload --port 8000
  ```

  > `--reload` means the server restarts automatically whenever you save a `.py` file. Useful during development — no need to stop and restart manually. Leave this terminal running.

  You should see output like:
  ```
  INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  INFO:     Started reloader process
  ```

- [x] In a **second terminal**, send a test request with `curl`:

  ```bash
  curl -X POST http://localhost:8000/generate \
    -F "job_description=We're hiring a software engineer with Python experience. You'll build internal APIs and collaborate with product teams." \
    --output test_resume.docx
  ```

  > `-F` sends a form field. `--output` saves the response body to a file instead of printing it to the terminal.

  Verify:
  - `curl` exits without an error
  - `test_resume.docx` appears in your current directory
  - Opening it shows a properly formatted resume with a new tailored summary

- [x] Delete the test file once confirmed:

  ```bash
  rm test_resume.docx
  ```

- [x] Stop the server (`CTRL+C` in the first terminal).

---

### Step 4 — Verify CORS headers

The Chrome extension will be refused if the CORS headers aren't set correctly. We can check them now with `curl` before writing any extension code — simulating the preflight check a browser sends before a cross-origin POST.

- [x] Start the server again if it's not running:

  ```bash
  cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000
  ```

- [x] In a second terminal, send a CORS preflight (`OPTIONS`) request:

  ```bash
  curl -i -X OPTIONS http://localhost:8000/generate \
    -H "Origin: chrome-extension://fake-extension-id" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type"
  ```

  > `-i` shows the response headers. A browser sends this `OPTIONS` request automatically before any cross-origin POST — if the server doesn't respond with the right `Access-Control-Allow-*` headers, the actual POST is blocked.

  Look for these headers in the response:
  ```
  access-control-allow-origin: chrome-extension://fake-extension-id
  access-control-allow-methods: POST
  access-control-allow-headers: Content-Type
  ```

  If they're present, CORS is configured correctly.

  > **Note:** `CORSMiddleware` does exact string matching on `allow_origins` — `"chrome-extension://*"` does not work as a wildcard there. The fix is to use `allow_origin_regex=r"chrome-extension://.*"` instead, which is how the code is written in `main.py`.

---

## Phase 5: Chrome Extension

**Goal:** A Manifest V3 Chrome extension that lets the user click a button from any job listing, scrape the job description, send it to the backend, and trigger a DOCX download — all in one action.

By the end of this phase:
- The extension is installed in Chrome (unpacked, developer mode)
- Clicking the toolbar icon opens a small popup showing the scraped job description
- The user clicks "Generate Resume" and the tailored DOCX downloads automatically

### How the extension works

A Chrome Manifest V3 extension has three parts:

| Part | File | What it does |
|---|---|---|
| Manifest | `manifest.json` | Declares permissions, files, and metadata |
| Content script | `content.js` | Runs inside the job listing page — reads the DOM and extracts text |
| Popup | `popup.html` + `popup.js` | The small window that appears when you click the extension icon — shows the scraped text and has the "Generate" button |

**Message flow:**

```
User clicks extension icon
  → popup.html opens
  → popup.js sends a message to content.js: "get job description"
  → content.js reads the page DOM and replies with the text
  → popup.js shows the text in a <textarea> for review
  → user clicks "Generate Resume"
  → popup.js POSTs to http://localhost:8000/generate
  → backend returns a DOCX file
  → popup.js triggers a browser download
```

Why a content script? The popup runs in its own isolated context — it can't read the job listing page's DOM directly. The content script is injected into the page, so it *can* read the DOM. The popup and content script communicate by passing messages through Chrome's `chrome.runtime.sendMessage` / `chrome.tabs.sendMessage` API.

---

### New folder structure

All extension files live in a new top-level folder:

```
extension/
  manifest.json     ← declares the extension
  popup.html        ← the popup's HTML structure
  popup.js          ← popup logic: scrape, display, submit
  content.js        ← injected into the page; reads the job description
  icon.png          ← toolbar icon (any 128×128 PNG)
```

---

### Step 1 — Create the extension folder and manifest

The manifest is the extension's configuration file. It tells Chrome what permissions the extension needs, which files to use, and how it should behave.

- [x] Create the `extension/` folder at the project root (alongside `backend/`).

- [x] Create `extension/manifest.json`:

  What each field means:
  - `manifest_version: 3` — required for all new Chrome extensions (MV3 is the current standard)
  - `action` — defines the toolbar button; `default_popup` is the HTML file that opens when you click it
  - `content_scripts` — injects `content.js` into every tab (`*://*/*` = all URLs); this is what lets us read the page's job description text
  - `host_permissions` — grants the extension permission to make requests to `localhost:8000` (the backend) and to inject content scripts into any page

---

### Step 2 — Write the content script

`content.js` runs inside the job listing page. Its only job is to listen for a message from the popup and reply with the job description text.

For v1, we use a simple heuristic: find the largest block of text on the page. This won't be perfect for every site, but it works well enough for LinkedIn, Indeed, and most job boards without needing site-specific selectors.

- [x] Create `extension/content.js`:

---

### Step 3 — Write the popup

The popup is what the user sees when they click the extension icon. It has:
- A `<textarea>` showing the scraped job description (editable, in case Chrome scraped the wrong text)
- A "Generate Resume" button
- A status message showing progress or errors

- [x] Create `extension/popup.html`:

- [x] Create `extension/popup.js`:

---

### Step 4 — Add a toolbar icon

The extension needs a PNG icon to show in the Chrome toolbar. Any square image works.

- [x] Add a 128×128 PNG named `icon.png` to the `extension/` folder.

  The simplest option: save any square PNG you like (a coloured square, a letter, anything) as `extension/icon.png`. Chrome will resize it as needed.

  If you don't have one handy, you can generate one quickly with Python — run this from the project root:

  ```bash
  cd backend && source .venv/bin/activate && cd ..
  python3 -c "
  from PIL import Image, ImageDraw
  img = Image.new('RGB', (128, 128), color='#1a73e8')
  d = ImageDraw.Draw(img)
  d.text((42, 44), 'RT', fill='white')
  img.save('../extension/icon.png')
  print('icon.png created')
  "
  ```

  > This requires Pillow. If it's not installed: `pip install Pillow` in the venv. Or just drag any PNG into the folder and rename it.

  Then update `manifest.json` to reference the icon:

  ```json
  "icons": {
    "128": "icon.png"
  },
  "action": {
    "default_popup": "popup.html",
    "default_title": "Resume Tailor",
    "default_icon": "icon.png"
  }
  ```

---

### Step 5 — Load the extension in Chrome

Chrome can load an extension directly from a local folder without publishing it to the Web Store — this is called "loading unpacked".

- [x] Open Chrome and go to `chrome://extensions`
- [x] Enable **Developer mode** (toggle in the top-right corner)
- [x] Click **Load unpacked**
- [x] Select the `extension/` folder
- [x] The "Resume Tailor" extension should appear with your icon in the toolbar

  If you don't see the icon in the toolbar, click the puzzle-piece icon (Extensions menu) and pin it.

---

### Step 6 — Test end-to-end

- [x] Start the backend server:

  ```bash
  cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000
  ```

- [x] Open a job listing in Chrome (LinkedIn, Indeed, or any job board).

- [x] Click the Resume Tailor icon in the toolbar.

- [x] The popup should open with the job description pre-filled in the text area.

- [x] Click **Generate Resume**.

- [x] A `resume_YYYY-MM-DD.docx` file should download automatically.

- [x] Open the DOCX and verify:
  - The summary is tailored to the job description
  - The experience and skills sections look correct
  - The formatting is intact

  What could go wrong and how to fix it:
  - **Popup shows "Could not scrape this page"** — the content script didn't inject. Reload the tab, then try again. On some sites Chrome delays injection.
  - **Textarea shows too much text / wrong text** — the heuristic picked the wrong element. Edit the text manually in the popup before clicking Generate. Step 7 adds site-specific selectors to fix this properly.
  - **"Error: Failed to fetch"** — the backend isn't running. Start the uvicorn server.
  - **"Server error 429"** — rate limit hit (6 requests/minute). Wait a moment and try again.

---

### Step 7 — Improve the scraper for key job sites *(optional but recommended)*

The heuristic in Step 2 works on most pages but can grab navigation menus or sidebars instead of the job description. Adding site-specific selectors for the most common job boards makes it reliable.

- [x] Update `extension/content.js` to try known selectors before falling back to the heuristic:

  After saving, go to `chrome://extensions` and click the **reload** button on Resume Tailor to pick up the change.

---

## Phase 6: Extension UI Polish

**Goal:** Improve the visual appearance and usability of the Chrome extension popup.

[x] Give the popup a clean, modern design with better typography, spacing, and colors
[x] Choose a good background color and font for the popup (e.g. light background with dark text, or dark mode)
[x] Style the "Generate Resume" button to make it more prominent and clickable

---

## Phase 7: Resume Document Improvements

**Goal:** Improve the visual output and formatting of the generated DOCX resume.

[x] Need line above the professional summary section to separate it from the header (name + contact)
[x] Add "Professional Summary" or "Summary" above the summary paragraph, whichever the agent prefers
[x] Use round bullets for the bullet points indstead of the dashes we're currently using
[x] descriptions of the professional development sections should be in bullet points
[x] PhD - Philosophy should be indented as a bullet

---

## Bug Fixes & v1 Completion

[x] AI summary hallucinated skills not in the resume (e.g. Angular) — fixed by computing the intersection of resume skills and the job description in Python (`_skills_relevant_to_job()` in `prompts.py`), so the model is only ever told about skills the candidate actually has that are relevant to the role
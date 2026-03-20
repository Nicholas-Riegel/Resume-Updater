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

*Coming after Phase 0 is complete.*

---

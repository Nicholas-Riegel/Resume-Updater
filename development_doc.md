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

  ```python
  # backend/generate_docx.py
  #
  # Prototype script — Phase 1.
  # Generates a DOCX resume from static sample data to verify the template works.
  # This is not production code; it will be replaced by the full pipeline in Phase 3.

  import json
  from pathlib import Path
  from docxtpl import DocxTemplate
  from schemas.resume import BaseResume

  # ---------------------------------------------------------------------------
  # Load and validate the base resume data
  # ---------------------------------------------------------------------------
  data_path = Path(__file__).parent / "data" / "base_resume.json"
  with open(data_path) as f:
      raw = json.load(f)

  # Parse through Pydantic to confirm the data matches our schema.
  # .model_dump() converts the validated Pydantic model back into a plain dict,
  # which is what docxtpl expects as its template context.
  resume = BaseResume(**raw).model_dump()

  # ---------------------------------------------------------------------------
  # Fill the template
  # ---------------------------------------------------------------------------
  template_path = Path(__file__).parent / "templates" / "resume_template.docx"
  doc = DocxTemplate(template_path)

  # render() walks every Jinja2 placeholder in the .docx XML and replaces it
  # with the matching value from our dict. Any key in `resume` becomes a
  # variable you can reference in the template as {{ key }}.
  doc.render(resume)

  # ---------------------------------------------------------------------------
  # Save the output
  # ---------------------------------------------------------------------------
  output_path = Path(__file__).parent / "output" / "resume_sample.docx"
  doc.save(output_path)
  print(f"DOCX saved to {output_path}")
  ```

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

  ```python
  # backend/generate_pdf.py
  #
  # Prototype script — Phase 1.
  # Generates a PDF resume from static sample data using WeasyPrint.

  import json
  from pathlib import Path
  from jinja2 import Environment, FileSystemLoader
  from weasyprint import HTML
  from schemas.resume import BaseResume

  # ---------------------------------------------------------------------------
  # Load and validate the base resume data
  # ---------------------------------------------------------------------------
  data_path = Path(__file__).parent / "data" / "base_resume.json"
  with open(data_path) as f:
      raw = json.load(f)

  resume = BaseResume(**raw).model_dump()

  # ---------------------------------------------------------------------------
  # Render the Jinja2 HTML template into a plain HTML string
  # ---------------------------------------------------------------------------
  templates_dir = Path(__file__).parent / "templates"

  # FileSystemLoader tells Jinja2 where to look for template files.
  # Environment is the Jinja2 rendering engine that processes the template.
  env = Environment(loader=FileSystemLoader(str(templates_dir)))
  template = env.get_template("resume_template.html")

  # render() fills in all {{ variable }} placeholders and processes {% for %}
  # loops, producing a complete HTML string ready for WeasyPrint.
  html_string = template.render(**resume)

  # ---------------------------------------------------------------------------
  # Convert HTML string → PDF file
  # ---------------------------------------------------------------------------
  output_path = Path(__file__).parent / "output" / "resume_sample.pdf"

  # base_url tells WeasyPrint where to resolve relative paths (e.g. for any
  # linked CSS files). Pointing it at the templates directory keeps things tidy.
  HTML(string=html_string, base_url=str(templates_dir)).write_pdf(str(output_path))
  print(f"PDF saved to {output_path}")
  ```

- [x] ~~Run the script and verify the output~~ — **Skipped.** See above.

---

### Decision Point

- [x] Review both outputs side by side and decide on the primary format:

  > **Decision:** DOCX only. PDF output is not editable and performs worse with ATS systems. Prototype B was skipped — Prototype A was sufficient to confirm the approach.

---

## Phase 2: Template Polish

The functional template from Phase 1 is plain, unstyled text. This phase makes it look like a real professional resume by applying formatting directly in LibreOffice. The key principle: **style the template, not the data** — all formatting lives in the `.docx` file; Python only fills in the values.

### Goals for this phase
- Name displayed large and bold at the top
- Contact details on a single line, readable
- Section headings (EXPERIENCE, SKILLS, EDUCATION) bold and visually distinct
- Each job entry: title bold, company and date range cleanly formatted
- Bullet points rendered as actual list items
- Skills as a comma-separated line (not a blob)
- Special characters (e.g. `&`) rendering correctly
- Output looks submission-ready when opened in LibreOffice

### Steps

- [ ] Fix skills rendering in the template — replace the `{% for skill in skills %}` loop with:

  ```
  {{ skills | join(', ') }}
  ```

  > **Why:** The loop puts each skill on its own text run with no separator, producing a blob. `join(', ')` turns the list into a single comma-separated string in one text run — clean and readable.

- [ ] Fix `&` character escaping — anywhere a field might contain `&` (e.g. education degree names), append the `| e` filter:

  ```
  {{ edu.degree | e }}
  ```

  > **Why:** DOCX files are XML internally, and `&` is a reserved character in XML. Without escaping it gets silently dropped. The `| e` filter tells Jinja2 to escape it as `&amp;`, which renders correctly as `&` in the final document.

- [ ] Style the template in LibreOffice:

  Open `backend/templates/resume_template.docx` and apply the following formatting. Remember to **turn off AutoCorrect** (Tools → AutoCorrect Options → uncheck everything) before editing.

  **Name line** (`{{ name }}`):
  - Font size: 20–24pt
  - Bold

  **Contact line** (`{{ contact.email }}` etc.):
  - Condense onto fewer lines, or use ` | ` as a separator between fields
  - Font size: 10pt

  **Summary** (`{{ summary }}`):
  - Font size: 10–11pt
  - Add a small paragraph space above it

  **Section headings** (SKILLS, EXPERIENCE, EDUCATION):
  - Bold, 11–12pt
  - All caps (or just type them in caps — don't use Word's "all caps" character formatting, as it can confuse some ATS parsers)
  - Add a top border or spacing above to visually separate sections

  **Job title** (`{{ job.title }}`):
  - Bold, 11pt

  **Company and date** (`{{ job.company }}` and `{{ job.start_date }} - {{ job.end_date }}`):
  - Regular weight, 10–11pt
  - Can be on the same line separated by a space or `|`

  **Bullet points** (`{{ bullet }}`):
  - Apply LibreOffice's built-in **List Bullet** paragraph style to the bullet line inside the loop
  - Font size: 10–11pt

  **Education entries** (`{{ edu.institution }}`, `{{ edu.degree | e }}`):
  - Institution bold, degree regular weight

- [ ] Save the template as `resume_template.docx` (Word 2007-365 format, not ODF)

- [ ] Re-run `generate_docx.py` and open the output:

  ```bash
  cd backend
  source .venv/bin/activate
  python generate_docx.py
  cd ..
  ```

  Verify:
  - Looks like a professional resume
  - No raw placeholders visible
  - Skills appear as a comma-separated line
  - `&` characters render correctly
  - Bullet points are actual list items, not plain text

---

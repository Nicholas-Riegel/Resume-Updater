# Resume Tailor

A Chrome extension + Python backend that tailors your resume to any job listing with a few clicks. No copy/paste, no manual formatting, no AI hallucination of fake experience.

![Flow: Scrape → Review → Generate → Review → Download](https://SWAP IN REAL SCREENSHOT GIF)

---

## What it does

1. You navigate to any job listing in Chrome and click the extension icon
2. Click **Scrape Job Description** — the extension pulls the job description from the page
3. Review and edit the scraped text if needed (e.g. if the page had navigation noise)
4. Click **Generate Summary** — the backend sends your base resume + job description to a local AI, which writes a tailored professional summary
5. Review and edit the AI-generated summary
6. Click **Create Document** — the backend combines your approved summary with your base resume and produces a formatted `.docx` file
7. The file downloads automatically, ready to submit

At every step you remain in control. You see exactly what the AI was given, and you approve what goes into the document before it's built.

---

## Architecture

```
Chrome Extension (Manifest V3)
  content.js     — injected into every tab; scrapes job description on request
  popup.html/js  — 6-stage interactive UI; manages the full flow

        ↕  HTTP (localhost:8000)

FastAPI Backend
  POST /preview  — generates AI summary, returns JSON
  POST /generate — builds and returns the .docx file

        ↕

Ollama (local AI)
  llama3.2 (default) — runs entirely on your machine; no API key, no cost
```

The AI **only writes the professional summary**. Experience, job titles, dates, companies, and skills are taken verbatim from your base resume JSON — the AI cannot invent or modify them. All output is validated against a Pydantic schema before a document is ever generated.

---

## Tech stack

| Layer | Technology |
|---|---|
| Browser extension | Chrome Manifest V3 |
| Backend | FastAPI + Uvicorn |
| AI integration | OpenAI Python SDK → Ollama (local) |
| Schema validation | Pydantic |
| Document generation | `python-docx` (programmatic — no templates) |
| Rate limiting | SlowAPI |

---

## Project structure

```
backend/
  main.py            — FastAPI app; /preview and /generate endpoints
  tailor.py          — AI pipeline; hallucination checking; retry logic
  generate_docx.py   — builds the .docx from validated resume data
  prompts.py         — prompt construction
  ai_client.py       — OpenAI SDK configured to point at Ollama
  requirements.txt
  data/
    base_resume.json — your resume (the single source of truth)
  schemas/
    resume.py        — Pydantic models for input and AI output validation
  output/            — generated .docx files land here

extension/
  manifest.json
  content.js         — scrapes job description from active tab
  popup.html         — extension popup UI
  popup.js           — stage machine; all button/API logic
```

---

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Google Chrome

### 1. Pull the AI model

```bash
ollama pull llama3.2
```

### 2. Set up the Python backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your resume

Edit `backend/data/base_resume.json` with your own details. This is the single source of truth — the AI never modifies it, only reads from it.

### 4. Start the backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### 5. Load the Chrome extension

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select the `extension/` folder
4. The Resume Tailor icon will appear in your toolbar

---

## How the AI pipeline works

When you click **Generate Summary**, the backend:

1. Loads your base resume from JSON
2. Sanitizes the job description (prompt injection mitigation)
3. Sends a structured prompt to Ollama asking it to write a tailored summary — constrained to facts present in the base resume
4. Validates the response against a Pydantic schema
5. Runs a hallucination check: if the summary mentions companies, dates, or titles not in your base resume, the AI is retried with corrective feedback (up to 3 attempts)
6. Strips common model artifacts (`<think>` blocks, preamble sentences, wrapping quotes)
7. Returns the clean summary as JSON

When you click **Create Document**, the approved summary is sent directly to the document builder — the AI is bypassed entirely.

---

## Key design decisions

**AI handles only the summary.** The riskiest thing an AI can do on a resume is invent experience. By restricting the AI to one output field — the professional summary — and validating everything else against your base resume, hallucination risk is confined and detectable.

**Confirmed-summary fast path.** Once you've approved the summary in the popup, `/generate` skips the AI entirely. The document is built from your verified inputs only.

**Stage machine UI.** The popup is built around a `setStage(n)` function. Every UI state — which buttons are visible, what's enabled — is defined in one place. This makes the flow easy to reason about and extend.

**Local AI by default.** Using Ollama means zero API cost, no internet dependency, and no data leaving your machine. The backend uses the OpenAI Python SDK pointed at `http://localhost:11434/v1`, so switching to a cloud model is a one-line config change.

---

## Configuration

The model and Ollama URL can be changed in `backend/ai_client.py`. The rate limit (default: 6 requests/minute) can be adjusted in `backend/main.py`.

---

## License

MIT

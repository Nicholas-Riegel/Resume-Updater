# backend/tailor.py
#
# Core AI tailoring function.
#
# v1 approach: the AI only rewrites the summary. Experience, bullets, and
# skills are taken verbatim from the base resume — the AI never touches them.
# This makes the pipeline simple and reliable on any model.

import re

from schemas.resume import BaseResume, TailoredResumeOutput
from ai_client import get_client
from prompts import build_prompt

# Compiled patterns used to clean up common model output artifacts
_THINK_TAG = re.compile(r"<think>.*?</think>", re.DOTALL)
# A leading preamble like "Here is a concise professional summary:\n\n"
_PREAMBLE = re.compile(r'^[^"\n]{10,150}:\s*\n+', re.DOTALL)
# Wrapping curly or straight quotes around the entire summary
_WRAPPING_QUOTES = re.compile(r'^[\u201c"\'](.*?)[\u201d"\'\s]*$', re.DOTALL)

MAX_RETRIES = 3  # how many times to retry before giving up


def _clean_summary(raw: str) -> str:
    """
    Strip common model output artifacts from a raw summary string.

    1. <think>...</think> blocks — used by qwen3-style "thinking" models to
       show their reasoning before the answer. Never belongs in a resume.
    2. Leading preamble sentence — models often prefix the answer with a
       meta-comment like "Here is a concise professional summary:\n\n".
       We detect and remove any line that ends with a colon followed by
       newlines at the start of the response.
    3. Wrapping quotes — some models wrap the summary in " " or \" \".
    """
    # 1. Strip thinking blocks
    text = _THINK_TAG.sub("", raw).strip()

    # 2. Strip leading preamble (e.g. "Here is a professional summary:\n\n")
    text = _PREAMBLE.sub("", text).strip()

    # 3. Strip wrapping quote characters (straight or curly, single or double)
    m = _WRAPPING_QUOTES.match(text)
    if m:
        text = m.group(1).strip()

    return text


def _normalize(token: str) -> str:
    """
    Strip all non-alphanumeric characters and lowercase a token.

    This lets us match "TailwindCSS" against "Tailwind CSS" — both normalise
    to "tailwindcss" — so formatting differences don't cause false positives.
    """
    return re.sub(r"[^a-z0-9]", "", token.lower())


# Common English words that appear capitalised in job titles and sentences
# but are not technologies or skills. These should never be flagged as
# hallucinations even if they appear in both the job description and summary.
_NON_SKILL_WORDS: set[str] = {
    "software", "engineer", "engineering", "developer", "development",
    "frontend", "backend", "fullstack", "fullstack", "web", "mobile",
    "senior", "junior", "lead", "staff", "principal", "associate",
    "strong", "proven", "skilled", "proficient", "experienced",
    "high", "highly", "team", "quality", "clean", "scalable", "efficient",
    "best", "practices", "focus", "track", "record", "ability", "skills",
    "work", "working", "environment", "ensuring", "deliver", "delivering",
}


def _find_violations(summary: str, resume: BaseResume, job_description: str) -> list[str]:
    """
    Return any capitalised tokens that appear in both the summary and the job
    description but are NOT in the candidate's resume skills.

    These are hallucinated technologies — the model borrowed them from the job
    description rather than the candidate's actual skill set. We check for them
    in Python rather than relying on the model to self-police, because small
    local models cannot reliably follow a "don't mention X" rule.

    Tokens are normalised (lowercase, non-alphanumeric stripped) before
    comparison so that "TailwindCSS" matches "Tailwind CSS", etc.
    We only flag capitalised tokens (3+ chars) to avoid false positives on
    ordinary lowercase words, and we skip common job-title / sentence words.
    """
    # Build a flat set of normalised tokens from the candidate's resume skills.
    allowed_tokens: set[str] = set()
    for category in resume.skills:
        for entry in category.entries:
            for token in re.split(r"[\s/&()+,.\-]+", entry):
                if len(token) >= 3:
                    allowed_tokens.add(_normalize(token))

    # Normalised tokens that appear in the job description.
    job_tokens: set[str] = set()
    for token in re.split(r"[\s/&()+,.\-]+", job_description):
        if len(token) >= 3:
            job_tokens.add(_normalize(token))

    # Find capitalised tokens in the summary that came from the job description
    # but are not in the candidate's verified skill set or the exclusion list.
    violations: set[str] = set()
    for token in re.split(r"[\s/&()+,.\-]+", summary):
        normalised = _normalize(token)
        if (
            len(token) >= 3
            and token[0].isupper()
            and normalised in job_tokens
            and normalised not in allowed_tokens
            and normalised not in _NON_SKILL_WORDS
        ):
            violations.add(token)

    return list(violations)


def tailor_resume(
    resume: BaseResume,
    job_description: str,
    confirmed_summary: str | None = None,   # Stage 2 fast-path: skip the AI
) -> TailoredResumeOutput:
    """
    Given a validated BaseResume and a raw job description string, call the AI
    to generate a tailored summary, then assemble and return a TailoredResumeOutput
    with the AI summary and all other fields copied unchanged from the base resume.

    If confirmed_summary is provided (the user already reviewed it in the popup),
    the AI is skipped entirely and the output is assembled directly — guaranteeing
    the DOCX contains exactly the text the user approved.

    On each attempt we validate the summary with _find_violations(). If the model
    hallucinated skills from the job description, we append its bad output and a
    specific correction to the message history so it knows exactly what to fix on
    the next attempt — much more effective than re-sending the same prompt.

    Raises RuntimeError if the AI fails to return a clean summary after MAX_RETRIES.
    """
    # Stage 2 fast-path: the user already reviewed and approved a summary in
    # the popup, so there's no need to call the AI again. We assemble the
    # TailoredResumeOutput directly, guaranteeing the DOCX contains exactly
    # the text the user saw — no surprises.
    if confirmed_summary is not None:
        return TailoredResumeOutput(
            summary    = confirmed_summary,
            skills     = resume.skills,
            experience = resume.experience,
        )

    client, model = get_client()
    system_msg, user_msg = build_prompt(resume, job_description)

    # We build the message list once and append to it on violation retries.
    # The model sees its previous bad output plus a concrete correction, which
    # is far more effective than simply re-sending the original prompt.
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ]

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"AI call attempt {attempt}/{MAX_RETRIES}...")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                # temperature=0 makes the model deterministic — same input always
                # produces the same output. Good for structured tasks like this.
                temperature=0,
            )

            # Strip <think>...</think> blocks (qwen3-style thinking models),
            # then strip surrounding whitespace.
            raw = response.choices[0].message.content
            summary = _clean_summary(raw)

            if not summary:
                raise ValueError("AI returned an empty summary.")

            # Post-generation validation: reject summaries that mention
            # technologies the candidate doesn't have.
            violations = _find_violations(summary, resume, job_description)
            if violations:
                violation_str = ", ".join(violations)
                print(f"Attempt {attempt}: hallucinated skills detected — {violation_str}. Retrying with correction...")
                # Add the bad output and a targeted correction to the history.
                # The model now knows exactly what it got wrong.
                messages.append({"role": "assistant", "content": summary})
                messages.append({"role": "user", "content": (
                    f"Your summary incorrectly mentioned: {violation_str}. "
                    f"None of these are in the candidate's skill set. "
                    f"Please rewrite the summary without mentioning any of them."
                )})
                raise ValueError(f"Hallucinated skills: {violation_str}")

            print("AI returned valid output.")
            print(f"--- AI RAW OUTPUT ---\n{summary}\n--- END AI OUTPUT ---")

            # Assemble the full TailoredResumeOutput:
            # - summary comes from the AI
            # - skills and experience are passed through directly from the base
            #   resume — no conversion needed since TailoredResumeOutput now uses
            #   the same ExperienceEntry and SkillCategory types as BaseResume.
            return TailoredResumeOutput(
                summary    = summary,
                skills     = resume.skills,
                experience = resume.experience,
            )

        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")

    raise RuntimeError(
        f"AI failed to return a valid summary after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
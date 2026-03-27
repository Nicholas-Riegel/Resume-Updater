# backend/tailor.py
#
# Core AI tailoring function.
#
# v1 approach: the AI only rewrites the summary. Experience, bullets, and
# skills are taken verbatim from the base resume — the AI never touches them.
# This makes the pipeline simple and reliable on any model.

from schemas.resume import BaseResume, TailoredResumeOutput
from ai_client import get_client
from prompts import build_prompt

MAX_RETRIES = 3  # how many times to retry before giving up


def tailor_resume(resume: BaseResume, job_description: str) -> TailoredResumeOutput:
    """
    Given a validated BaseResume and a raw job description string, call the AI
    to generate a tailored summary, then assemble and return a TailoredResumeOutput
    with the AI summary and all other fields copied unchanged from the base resume.

    Raises RuntimeError if the AI fails to return usable output after MAX_RETRIES.
    """
    client, model = get_client()
    system_msg, user_msg = build_prompt(resume, job_description)

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"AI call attempt {attempt}/{MAX_RETRIES}...")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_msg},
                ],
                # temperature=0 makes the model deterministic — same input always
                # produces the same output. Good for structured tasks like this.
                temperature=0,
            )

            # The AI returns a plain text summary — just strip whitespace.
            # No JSON parsing needed; we're not asking for a JSON blob anymore.
            summary = response.choices[0].message.content.strip()

            if not summary:
                raise ValueError("AI returned an empty summary.")

            print("AI returned valid output.")

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
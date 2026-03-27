# backend/test_tailor.py
#
# Temporary smoke-test for the full AI pipeline.
# Verifies that the schema cleanup (removing TailoredExperienceEntry) didn't
# break anything — the output should be identical to before.
#
# Delete this file once the test passes.

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas.resume import BaseResume
from tailor import tailor_resume

# Load the base resume
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

print("Calling AI...")
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

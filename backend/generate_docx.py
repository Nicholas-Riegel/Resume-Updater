# Prototype script — Phase 1.
# Generates a DOCX resume from static sample data to verify the template works.
# This is not production code; it will be replaced by the full pipeline in Phase 3.

import json
from pathlib import Path
from docxtpl import DocxTemplate
from jinja2 import Environment
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
#
# trim_blocks=True  — removes the newline that follows a {% %} block tag,
#                     preventing blank lines between loop iterations.
# lstrip_blocks=True — strips leading whitespace/tabs before {% %} tags,
#                      so indenting tags in the template doesn't add spaces.
jinja_env = Environment(trim_blocks=True, lstrip_blocks=True)
doc.render(resume, jinja_env=jinja_env)

# ---------------------------------------------------------------------------
# Save the output
# ---------------------------------------------------------------------------
output_path = Path(__file__).parent / "output" / "resume_sample.docx"
doc.save(output_path)
print(f"DOCX saved to {output_path}")
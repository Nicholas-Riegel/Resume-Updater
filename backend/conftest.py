# backend/conftest.py
#
# Root conftest for the backend test suite.
#
# pytest looks for conftest.py files as it collects tests. This one sits at
# the backend/ level, so it runs before any test file under backend/tests/.
#
# Its only job is to add backend/ itself to sys.path, so that all test files
# can write plain imports like:
#
#   from schemas.resume import BaseResume
#   from tailor import tailor_resume
#
# without needing relative imports or sys.path manipulation inside each file.

import sys
from pathlib import Path

# Path(__file__).parent is the backend/ directory — the folder that holds
# all the modules the tests need to import.
sys.path.insert(0, str(Path(__file__).parent))

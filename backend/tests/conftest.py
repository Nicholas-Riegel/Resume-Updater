# backend/tests/conftest.py
#
# Fixtures that are automatically available to every test in this folder.
#
# pytest discovers conftest.py files automatically — anything defined here
# with @pytest.fixture is usable in any test file without importing it.

import pytest
from slowapi import Limiter
from slowapi.util import get_remote_address

import main  # noqa: E402  (imported after sys.path is set by backend/conftest.py)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Replace the app's rate limiter with a fresh instance before each test.

    Why this is needed:
    The API uses slowapi to enforce a 6-requests-per-minute limit per IP.
    All TestClient requests use the same fake IP ("testclient"), so the counter
    accumulates across tests. Without this fixture, the 7th test that hits a
    rate-limited endpoint would receive a 429 Too Many Requests error instead
    of the expected response.

    How it works:
    FastAPI's SlowAPIMiddleware reads the limiter from request.app.state.limiter
    on every request. Replacing that with a brand-new Limiter instance gives it
    an empty in-memory counter, effectively resetting the clock for each test.
    The original limiter is restored after the test finishes.
    """
    main.app.state.limiter = Limiter(key_func=get_remote_address)
    yield
    # Restore the original limiter so later tests start in a known state.
    main.app.state.limiter = main.limiter

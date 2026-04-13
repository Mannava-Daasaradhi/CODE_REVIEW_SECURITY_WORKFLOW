import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app as _app

    @pytest.fixture(scope="module")
    def client():
        """
        TestClient wrapped in a `with` block so FastAPI's lifespan runs,
        initialising app.state.env before any test makes a request.
        Scoped to module so the Environment singleton is shared within a test file.
        """
        with TestClient(_app) as c:
            yield c

except ImportError:
    # app.main is not present in CLI-only deployments; route tests will be skipped.
    pass

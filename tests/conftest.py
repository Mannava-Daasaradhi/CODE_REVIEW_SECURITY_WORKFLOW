import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """
    TestClient wrapped in a `with` block so FastAPI's lifespan runs,
    initialising app.state.env before any test makes a request.
    Scoped to module so the Environment singleton is shared within a test file.
    """
    with TestClient(app) as c:
        yield c

import pytest


@pytest.fixture
def sample_findings():
    return {
        "bugs": [
            {
                "line": 4,
                "severity": "CRITICAL",
                "confidence": 90,
                "fix": "change n+=1 to n-=1",
                "description": "Infinite loop",
            }
        ],
        "security": [
            {
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "confidence": 80,
                "fix": "use parameterized queries",
                "description": "User input in query",
            }
        ],
        "summary": "Test summary",
        "score": 42,
        "thinking": "Test thinking",
    }


@pytest.fixture
def sample_code():
    return "def foo(x):\n    return x + 1"


@pytest.fixture
def sample_raw_response():
    return (
        "THINKING:\nTest reasoning\n\n"
        "BUGS:\n- Line 4: [CRITICAL] Infinite loop | Confidence: 90% | Fix: change n+=1 to n-=1\n\n"
        "SECURITY:\nNone found\n\n"
        "SUMMARY:\nTest summary\n\n"
        "SCORE: 42"
    )

"""
Grader tests.

The most important tests here are the determinism tests.
If ANY grader returns different scores for identical inputs, the submission is invalid.
"""

import pytest

from app.graders.task1_grader import Task1Grader
from app.graders.task2_grader import Task2Grader
from app.graders.task3_grader import Task3Grader
from app.models.action import Action, Finding


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def task1():
    return Task1Grader()

@pytest.fixture
def task2():
    return Task2Grader()

@pytest.fixture
def task3():
    return Task3Grader()


# ── Task 1: Bug Detection ─────────────────────────────────────────────────────

def test_task1_perfect_score(task1):
    action = Action(flagged_lines=[2])
    gt = {"bug_lines": [2]}
    assert task1.grade(action, gt) == 1.0


def test_task1_no_findings(task1):
    action = Action(flagged_lines=[])
    gt = {"bug_lines": [2]}
    assert task1.grade(action, gt) == 0.0


def test_task1_partial_score(task1):
    action = Action(flagged_lines=[2])
    gt = {"bug_lines": [2, 5]}
    assert task1.grade(action, gt) == pytest.approx(0.5)


def test_task1_spam_penalty(task1):
    action = Action(flagged_lines=[1, 2, 3, 4, 5, 6, 7])
    gt = {"bug_lines": [2]}
    score = task1.grade(action, gt)
    # Recall = 1.0, penalty = -0.1 → 0.9
    assert score == pytest.approx(0.9)


def test_task1_floor_at_zero(task1):
    action = Action(flagged_lines=[1, 2, 3, 4, 5, 6, 7])
    gt = {"bug_lines": [99]}  # None correct → recall=0.0, penalty=-0.1, floored to 0.0
    score = task1.grade(action, gt)
    assert score == pytest.approx(0.0)


def test_task1_empty_ground_truth_correct(task1):
    action = Action(flagged_lines=[])
    gt = {"bug_lines": []}
    assert task1.grade(action, gt) == 1.0


def test_task1_empty_ground_truth_wrong(task1):
    action = Action(flagged_lines=[1])
    gt = {"bug_lines": []}
    assert task1.grade(action, gt) == 0.0


def test_task1_determinism(task1):
    action = Action(flagged_lines=[2, 5])
    gt = {"bug_lines": [2, 5, 8]}
    scores = {task1.grade(action, gt) for _ in range(100)}
    assert len(scores) == 1, f"Task1 grader is non-deterministic: got scores {scores}"


# ── Task 2: OWASP Vulnerability Detection ────────────────────────────────────

def test_task2_all_found(task2):
    action = Action(findings=[
        Finding(type="sql_injection", description="SQL injection on line 2"),
        Finding(type="hardcoded_secret", description="API key hardcoded"),
    ])
    gt = {"vuln_types": ["sql_injection", "hardcoded_secret"]}
    assert task2.grade(action, gt) == pytest.approx(1.0)


def test_task2_partial(task2):
    action = Action(findings=[
        Finding(type="sql_injection", description="SQL injection found"),
    ])
    gt = {"vuln_types": ["sql_injection", "hardcoded_secret"]}
    assert task2.grade(action, gt) == pytest.approx(0.5)


def test_task2_none_found(task2):
    action = Action(findings=[])
    gt = {"vuln_types": ["sql_injection"]}
    assert task2.grade(action, gt) == 0.0


def test_task2_case_insensitive(task2):
    action = Action(findings=[
        Finding(type="SQL_INJECTION", description="Found it"),
    ])
    gt = {"vuln_types": ["sql_injection"]}
    assert task2.grade(action, gt) == pytest.approx(1.0)


def test_task2_false_positive_penalty(task2):
    # 1 correct, 10 false positives against 1 ground truth vuln
    # matched=1, score=1.0, false_positives=10, fp_threshold=2, excess_fps=10-2=8, penalty=-0.4 → 0.6
    action = Action(findings=[
        Finding(type="sql_injection", description="correct"),
        *[Finding(type=f"fake_vuln_{i}", description="wrong") for i in range(10)],
    ])
    gt = {"vuln_types": ["sql_injection"]}
    score = task2.grade(action, gt)
    assert score == pytest.approx(0.6)


def test_task2_determinism(task2):
    action = Action(findings=[Finding(type="sql_injection", description="test")])
    gt = {"vuln_types": ["sql_injection", "xss"]}
    scores = {task2.grade(action, gt) for _ in range(100)}
    assert len(scores) == 1, f"Task2 grader is non-deterministic: got scores {scores}"


# ── Task 3: Composite PR Review ───────────────────────────────────────────────

def test_task3_perfect_score(task3):
    action = Action(
        flagged_lines=[3],
        findings=[Finding(type="sql_injection", description="SQL injection on line 3")],
        review_text="Line 3 contains a critical sql_injection security vulnerability. Must use parameterized queries.",
    )
    gt = {"bug_lines": [3], "vuln_types": ["sql_injection"]}
    score = task3.grade(action, gt)
    assert score == pytest.approx(1.0)


def test_task3_review_quality_all_criteria(task3):
    action = Action(
        flagged_lines=[],
        findings=[],
        review_text="Line 2 contains a high severity security vulnerability. Must fix immediately.",
    )
    gt = {"bug_lines": [], "vuln_types": []}
    score = task3.grade(action, gt)
    # bug=1.0, security=1.0, review_quality=1.0 → 0.4 + 0.4 + 0.2 = 1.0
    assert score == pytest.approx(1.0)


def test_task3_review_quality_no_criteria(task3):
    action = Action(flagged_lines=[], findings=[], review_text="looks fine")
    gt = {"bug_lines": [], "vuln_types": []}
    score = task3.grade(action, gt)
    # bug=1.0, security=1.0, review_quality=0.0 → 0.4 + 0.4 + 0.0 = 0.8
    assert score == pytest.approx(0.8)


def test_task3_empty_review_text(task3):
    action = Action(flagged_lines=[], findings=[], review_text="")
    gt = {"bug_lines": [], "vuln_types": []}
    score = task3.grade(action, gt)
    assert score == pytest.approx(0.8)


def test_task3_composite_weights(task3):
    # bug=1.0, security=0.0, quality=0.0 → 0.4
    action = Action(flagged_lines=[2], findings=[], review_text="")
    gt = {"bug_lines": [2], "vuln_types": ["sql_injection"]}
    score = task3.grade(action, gt)
    assert score == pytest.approx(0.4)


def test_task3_score_bounded(task3):
    action = Action(
        flagged_lines=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        findings=[Finding(type=f"fake_{i}", description="x") for i in range(20)],
        review_text="critical high medium low line 1 L2 must should recommend bug security",
    )
    gt = {"bug_lines": [2], "vuln_types": ["sql_injection"]}
    score = task3.grade(action, gt)
    assert 0.0 <= score <= 1.0


def test_task3_determinism(task3):
    action = Action(
        flagged_lines=[2],
        findings=[Finding(type="sql_injection", description="Found it")],
        review_text="Line 2 has a critical security vulnerability. Must fix.",
    )
    gt = {"bug_lines": [2], "vuln_types": ["sql_injection"]}
    scores = {task3.grade(action, gt) for _ in range(100)}
    assert len(scores) == 1, f"Task3 grader is non-deterministic: got scores {scores}"

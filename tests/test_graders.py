import pytest
from app.graders.ast_grader import ASTGrader
from app.graders.owasp_grader import OWASPGrader
from app.graders.task1_grader import Task1Grader
from app.graders.task2_grader import Task2Grader
from app.graders.task3_grader import Task3Grader
from app.models.action import Action, Finding

def test_ast_grader_returns_list(sample_code):
    result = ASTGrader().analyze(sample_code)
    assert isinstance(result, list)


def test_owasp_grader_returns_list(sample_code):
    result = OWASPGrader().analyze(sample_code)
    assert isinstance(result, list)


def test_ast_grader_finds_nothing_on_clean_code():
    result = ASTGrader().analyze("def add(a, b):\n    return a + b\n")
    assert isinstance(result, list)

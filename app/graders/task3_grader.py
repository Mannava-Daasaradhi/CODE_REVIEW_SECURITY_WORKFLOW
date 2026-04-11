import re

from app.graders.base_grader import BaseGrader
from app.graders.task1_grader import Task1Grader
from app.graders.task2_grader import Task2Grader


_SEVERITY_PATTERN = re.compile(r"\b(critical|high|medium|low)\b", re.IGNORECASE)
_LINE_REF_PATTERN = re.compile(r"(line\s+\d+|L\d+)", re.IGNORECASE)
_ACTIONABLE_PATTERN = re.compile(r"\b(should|must|recommend|suggest|consider)\b", re.IGNORECASE)
_CATEGORY_PATTERN = re.compile(r"\b(bug|security|vulnerability|style|performance)\b", re.IGNORECASE)

BUG_WEIGHT = 0.4
SECURITY_WEIGHT = 0.4
REVIEW_QUALITY_WEIGHT = 0.2


class Task3Grader(BaseGrader):
    """
    Hard difficulty: PR review composite grader.

    Combines three sub-scores:
        - Bug detection (40%): Task1Grader logic on flagged_lines
        - Security findings (40%): Task2Grader logic on findings
        - Review quality (20%): Keyword/structure rubric on review_text

    Review quality rubric (each criterion = 0.25):
        +0.25  Contains severity label: critical|high|medium|low
        +0.25  Contains line reference: "line N" or "LN"
        +0.25  Contains actionable language: should|must|recommend|suggest|consider
        +0.25  Contains category label: bug|security|vulnerability|style|performance

    Final = 0.4 * bug_score + 0.4 * security_score + 0.2 * review_quality_score
    """

    def __init__(self) -> None:
        self._task1 = Task1Grader()
        self._task2 = Task2Grader()

    def grade(self, action, ground_truth: dict) -> float:
        bug_score = self._task1.grade(action, ground_truth)
        security_score = self._task2.grade(action, ground_truth)
        review_quality_score = self._score_review_quality(action.review_text)

        final = (
            BUG_WEIGHT * bug_score
            + SECURITY_WEIGHT * security_score
            + REVIEW_QUALITY_WEIGHT * review_quality_score
        )
        return round(max(0.0, min(1.0, final)), 4)

    def _score_review_quality(self, review_text: str) -> float:
        if not review_text:
            return 0.0

        criteria_met = 0
        if _SEVERITY_PATTERN.search(review_text):
            criteria_met += 1
        if _LINE_REF_PATTERN.search(review_text):
            criteria_met += 1
        if _ACTIONABLE_PATTERN.search(review_text):
            criteria_met += 1
        if _CATEGORY_PATTERN.search(review_text):
            criteria_met += 1

        return criteria_met * 0.25

    def get_sub_scores(self, action, ground_truth: dict) -> dict:
        """
        Returns individual sub-scores for inclusion in StepResult.info.
        Used for debugging and transparency — never exposes ground truth.
        """
        return {
            "bug_score": self._task1.grade(action, ground_truth),
            "security_score": self._task2.grade(action, ground_truth),
            "review_quality_score": self._score_review_quality(action.review_text),
        }

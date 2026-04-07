from app.graders.base_grader import BaseGrader
from app.models.action import Action


class Task1Grader(BaseGrader):
    """
    Easy difficulty: Bug line detection.

    Scores the agent's flagged_lines against ground_truth["bug_lines"].
    Uses recall-based scoring with a spam penalty.

    Scoring:
        score = len(correct_flags ∩ ground_truth_bugs) / len(ground_truth_bugs)
        penalty = -0.1 if len(flagged_lines) > 3 * len(ground_truth_bugs)
        final = max(0.0, score + penalty)
    """

    def grade(self, action: Action, ground_truth: dict) -> float:
        bug_lines: list[int] = ground_truth.get("bug_lines", [])

        if not bug_lines:
            # No bugs in ground truth — correct answer is to flag nothing
            return 1.0 if not action.flagged_lines else 0.0

        flagged = set(action.flagged_lines)
        correct = set(bug_lines)

        recall = len(flagged & correct) / len(correct)

        # Spam penalty: agent flagged more than 3x the number of real bugs
        penalty = -0.1 if len(flagged) > 3 * len(correct) else 0.0

        return max(0.0, recall + penalty)

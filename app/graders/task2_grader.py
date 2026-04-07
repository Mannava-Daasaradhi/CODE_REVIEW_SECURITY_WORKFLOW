from app.graders.base_grader import BaseGrader
from app.models.action import Action


class Task2Grader(BaseGrader):
    """
    Medium difficulty: OWASP vulnerability detection.

    Scores the agent's findings against ground_truth["vuln_types"].
    Partial credit per matched vulnerability type. Case-insensitive substring match.

    Scoring:
        matched = number of ground_truth vuln_types covered by at least one finding
        score = matched / len(ground_truth["vuln_types"])
        false_positives = len(findings) - matched
        penalty = -0.05 per FP beyond 2 * len(ground_truth["vuln_types"])
        final = max(0.0, score + penalty)
    """

    def grade(self, action: Action, ground_truth: dict) -> float:
        vuln_types: list[str] = ground_truth.get("vuln_types", [])

        if not vuln_types:
            return 1.0 if not action.findings else 0.0

        # Normalize ground truth types for matching
        normalized_gt = [v.lower().replace("-", "_").replace(" ", "_") for v in vuln_types]

        # For each ground truth vuln, check if any finding covers it
        matched = 0
        for gt_type in normalized_gt:
            for finding in action.findings:
                agent_type = finding.type.lower().replace("-", "_").replace(" ", "_")
                if gt_type in agent_type or agent_type in gt_type:
                    matched += 1
                    break

        score = matched / len(normalized_gt)

        # False positive penalty
        false_positives = max(0, len(action.findings) - matched)
        fp_threshold = 2 * len(normalized_gt)
        excess_fps = max(0, false_positives - fp_threshold)
        penalty = -0.05 * excess_fps

        return max(0.0, score + penalty)

from abc import ABC, abstractmethod
from app.models.action import Action


class BaseGrader(ABC):
    """
    Abstract base for all graders.

    CONTRACT (enforced by architecture, not by Python runtime):
    - grade() must be pure: no side effects, no external calls, no randomness
    - grade() must be deterministic: same (action, ground_truth) always returns same float
    - grade() must NEVER call any LLM — doing so causes disqualification
    - grade() must NEVER call exec() or eval() on any code content
    - Return value is always a float in [0.0, 1.0]
    """

    @abstractmethod
    def grade(self, action: Action, ground_truth: dict) -> float:
        """
        Score the agent's action against the episode ground truth.

        Args:
            action: The validated Action submitted by the agent
            ground_truth: The episode's answer key (loaded server-side, never sent to agent)

        Returns:
            float in [0.0, 1.0]
        """
        ...

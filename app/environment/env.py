from loguru import logger

from app.environment.episode_loader import Episode, EpisodeLoader, EpisodeNotFoundError
from app.graders.task1_grader import Task1Grader
from app.graders.task2_grader import Task2Grader
from app.graders.task3_grader import Task3Grader
from app.models.action import Action
from app.models.observation import Observation
from app.models.reward import StepResult
from app.models.state import EnvironmentState


class EnvironmentNotInitializedError(Exception):
    pass


_GRADERS = {
    "easy": Task1Grader(),
    "medium": Task2Grader(),
    "hard": Task3Grader(),
}


class Environment:
    """
    Core OpenEnv environment.

    Exposes reset(), step(), and state() matching the OpenEnv specification.
    One instance is created at app startup and shared across requests (singleton via lifespan).

    State is intentionally minimal — this is a single-turn environment.
    Each reset() loads a new episode; each step() grades and closes it.
    """

    def __init__(self, episode_loader: EpisodeLoader) -> None:
        self._loader = episode_loader
        self._current_episode: Episode | None = None
        self._step_count: int = 0
        self._last_reward: float | None = None

    def reset(self, task_difficulty: str | None = None) -> Observation:
        """
        Load a new episode and return the initial Observation.
        Ground truth is stored internally — never returned to the caller.
        """
        try:
            episode = self._loader.get_episode(task_difficulty)
        except EpisodeNotFoundError as e:
            logger.error(f"reset() failed: {e}")
            raise

        self._current_episode = episode
        self._step_count = 0
        self._last_reward = None

        logger.info(f"reset() -> task_id={episode.task_id} difficulty={episode.difficulty}")

        return Observation(
            task_id=episode.task_id,
            difficulty=episode.difficulty,
            code_snippet=episode.code_snippet,
            instructions=episode.instructions,
        )

    def step(self, action: Action) -> StepResult:
        """
        Grade the agent's action and return a StepResult.
        Raises EnvironmentNotInitializedError if reset() has not been called.
        done is always True — one episode = one interaction turn.
        """
        if self._current_episode is None:
            raise EnvironmentNotInitializedError(
                "step() called before reset(). Call POST /reset first."
            )

        episode = self._current_episode
        grader = _GRADERS[episode.difficulty]

        reward = grader.grade(action, episode.ground_truth)
        self._last_reward = reward
        self._step_count += 1

        # Build info dict with sub-scores if available (Task 3)
        info: dict = {"difficulty": episode.difficulty}
        if hasattr(grader, "get_sub_scores"):
            info.update(grader.get_sub_scores(action, episode.ground_truth))

        logger.info(
            f"step() -> task_id={episode.task_id} reward={reward:.4f} info={info}"
        )

        observation = Observation(
            task_id=episode.task_id,
            difficulty=episode.difficulty,
            code_snippet=episode.code_snippet,
            instructions=episode.instructions,
        )

        return StepResult(
            observation=observation,
            reward=reward,
            done=True,
            info=info,
        )

    def state(self) -> EnvironmentState:
        """
        Return current internal state for debugging.
        Never exposes ground truth.
        """
        return EnvironmentState(
            initialized=self._current_episode is not None,
            current_task_id=self._current_episode.task_id if self._current_episode else None,
            difficulty=self._current_episode.difficulty if self._current_episode else None,
            step_count=self._step_count,
            last_reward=self._last_reward,
        )

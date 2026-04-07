import json
from pathlib import Path
from dataclasses import dataclass

from loguru import logger

from app.config import settings


DIFFICULTY_MAP = {
    "easy": "task1_episodes.json",
    "medium": "task2_episodes.json",
    "hard": "task3_episodes.json",
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

# FIX: config-driven data dir — resolves from cwd(), not file-relative path
DATA_DIR = Path(settings.tasks_data_dir)


class EpisodeNotFoundError(Exception):
    pass


@dataclass
class Episode:
    task_id: str
    difficulty: str
    code_snippet: str
    instructions: str
    ground_truth: dict  # Never exposed to agents — internal use by graders only


class EpisodeLoader:
    """
    Loads task episodes from JSON files in data/tasks/.
    Manages episode cycling per difficulty tier.

    When difficulty=None, cycles deterministically through easy → medium → hard → easy ...
    using a counter (not random selection).
    When difficulty is specified, cycles through that tier's episodes sequentially.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._episodes: dict[str, list[dict]] = {}
        # Per-difficulty sequential cycling indices
        self._indices: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        # FIX: round-robin index for difficulty=None path — cycles easy→medium→hard
        self._round_robin_index: int = 0
        self._load_all()

    def _load_all(self) -> None:
        for difficulty, filename in DIFFICULTY_MAP.items():
            path = DATA_DIR / filename
            if not path.exists():
                logger.warning(
                    f"Episode file not found: {path}. "
                    f"Difficulty '{difficulty}' will return no episodes."
                )
                self._episodes[difficulty] = []
                continue
            with open(path, "r", encoding="utf-8") as f:
                self._episodes[difficulty] = json.load(f)
            logger.info(
                f"Loaded {len(self._episodes[difficulty])} episodes for difficulty='{difficulty}'"
            )

    def get_episode(self, difficulty: str | None = None) -> Episode:
        """
        Returns the next episode for the given difficulty (round-robin within tier).
        If difficulty is None, cycles through tiers in order: easy → medium → hard → easy ...
        Raises EpisodeNotFoundError if no episodes exist for the resolved difficulty.
        """
        if difficulty is None:
            # FIX: true round-robin over difficulty tiers — not random choice
            resolved = self._next_round_robin_difficulty()
        else:
            resolved = difficulty.lower()
            if resolved not in DIFFICULTY_MAP:
                raise EpisodeNotFoundError(
                    f"Unknown difficulty: '{difficulty}'. Must be easy, medium, or hard."
                )

        episodes = self._episodes.get(resolved, [])
        if not episodes:
            raise EpisodeNotFoundError(
                f"No episodes loaded for difficulty='{resolved}'."
            )

        idx = self._indices[resolved] % len(episodes)
        self._indices[resolved] += 1
        episode_dict = episodes[idx]

        # FIX: guard against malformed JSON episodes — raise meaningful error instead of KeyError
        return self._build_episode(episode_dict, resolved)

    def _next_round_robin_difficulty(self) -> str:
        """
        Cycles through DIFFICULTY_ORDER, skipping tiers with no episodes.
        Raises EpisodeNotFoundError if no tier has any episodes.
        """
        for _ in range(len(DIFFICULTY_ORDER)):
            candidate = DIFFICULTY_ORDER[self._round_robin_index % len(DIFFICULTY_ORDER)]
            self._round_robin_index += 1
            if self._episodes.get(candidate):
                return candidate

        raise EpisodeNotFoundError("No episodes loaded for any difficulty.")

    @staticmethod
    def _build_episode(episode_dict: dict, resolved_difficulty: str) -> Episode:
        """
        Constructs an Episode from a raw dict. Raises EpisodeNotFoundError on missing fields.
        """
        required = ("task_id", "difficulty", "code_snippet", "instructions", "ground_truth")
        missing = [k for k in required if k not in episode_dict]
        if missing:
            raise EpisodeNotFoundError(
                f"Episode in difficulty='{resolved_difficulty}' is missing required fields: {missing}"
            )
        return Episode(
            task_id=episode_dict["task_id"],
            difficulty=episode_dict["difficulty"],
            code_snippet=episode_dict["code_snippet"],
            instructions=episode_dict["instructions"],
            ground_truth=episode_dict["ground_truth"],
        )

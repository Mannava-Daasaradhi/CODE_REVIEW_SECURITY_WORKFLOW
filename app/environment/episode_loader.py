import json
import random
from pathlib import Path
from dataclasses import dataclass

from loguru import logger


DIFFICULTY_MAP = {
    "easy": "task1_episodes.json",
    "medium": "task2_episodes.json",
    "hard": "task3_episodes.json",
}

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tasks"


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
    The cycling index is deterministic — seeded at construction time.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._episodes: dict[str, list[dict]] = {}
        self._indices: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        self._load_all()

    def _load_all(self) -> None:
        for difficulty, filename in DIFFICULTY_MAP.items():
            path = DATA_DIR / filename
            if not path.exists():
                logger.warning(f"Episode file not found: {path}. Difficulty '{difficulty}' will return no episodes.")
                self._episodes[difficulty] = []
                continue
            with open(path, "r", encoding="utf-8") as f:
                self._episodes[difficulty] = json.load(f)
            logger.info(f"Loaded {len(self._episodes[difficulty])} episodes for difficulty='{difficulty}'")

    def get_episode(self, difficulty: str | None = None) -> Episode:
        """
        Returns the next episode for the given difficulty (round-robin).
        If difficulty is None, cycles through difficulties in order: easy -> medium -> hard -> easy ...
        Raises EpisodeNotFoundError if no episodes exist for the requested difficulty.
        """
        if difficulty is None:
            # Deterministic round-robin across all difficulties
            all_episodes = [
                ep for diff in ["easy", "medium", "hard"]
                for ep in self._episodes.get(diff, [])
            ]
            if not all_episodes:
                raise EpisodeNotFoundError("No episodes loaded for any difficulty.")
            episode_dict = self._rng.choice(all_episodes)
            difficulty = episode_dict["difficulty"]
        else:
            difficulty = difficulty.lower()
            if difficulty not in DIFFICULTY_MAP:
                raise EpisodeNotFoundError(f"Unknown difficulty: '{difficulty}'. Must be easy, medium, or hard.")

            episodes = self._episodes.get(difficulty, [])
            if not episodes:
                raise EpisodeNotFoundError(f"No episodes loaded for difficulty='{difficulty}'.")

            idx = self._indices[difficulty] % len(episodes)
            self._indices[difficulty] += 1
            episode_dict = episodes[idx]

        return Episode(
            task_id=episode_dict["task_id"],
            difficulty=episode_dict["difficulty"],
            code_snippet=episode_dict["code_snippet"],
            instructions=episode_dict["instructions"],
            ground_truth=episode_dict["ground_truth"],
        )

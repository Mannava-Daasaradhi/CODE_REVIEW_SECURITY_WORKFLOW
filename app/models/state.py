from pydantic import BaseModel


class EnvironmentState(BaseModel):
    """
    Returned by GET /state for debugging and inspection.
    Never contains ground truth.
    """
    initialized: bool
    current_task_id: str | None
    difficulty: str | None
    step_count: int
    last_reward: float | None

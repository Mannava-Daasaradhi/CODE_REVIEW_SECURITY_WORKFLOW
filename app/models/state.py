from pydantic import BaseModel


class EnvironmentState(BaseModel):
    initialized: bool
    current_task_id: str | None
    difficulty: str | None
    step_count: int
    last_reward: float | None

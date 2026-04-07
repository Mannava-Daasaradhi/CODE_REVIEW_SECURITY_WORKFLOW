from pydantic import BaseModel, Field
from app.models.observation import Observation


class StepResult(BaseModel):
    """
    Returned by POST /step after the grader scores the agent's Action.
    `done` is always True — one episode = one interaction turn.
    `info` contains sub-scores for debugging; never contains ground truth.
    """
    observation: Observation
    reward: float = Field(..., ge=0.0, le=1.0)
    done: bool
    info: dict

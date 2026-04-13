from pydantic import BaseModel, Field

from app.models.observation import Observation


class StepResult(BaseModel):
    observation: Observation
    reward: float = Field(ge=0.0, le=1.0)
    done: bool
    info: dict

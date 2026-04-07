from fastapi import APIRouter, HTTPException, Request

from app.environment.env import EnvironmentNotInitializedError
from app.models.action import Action
from app.models.reward import StepResult

router = APIRouter()


@router.post("/step", response_model=StepResult)
async def step(request: Request, action: Action) -> StepResult:
    """
    Submit the agent's analysis of the current episode.

    Body: Action { flagged_lines, findings, review_text }
    All fields are optional — graders award partial credit for what is provided.

    Returns StepResult { observation, reward, done, info }.
    done is always True — episodes are single-turn.
    """
    env = request.app.state.env
    try:
        return env.step(action)
    except EnvironmentNotInitializedError as e:
        raise HTTPException(status_code=400, detail=str(e))

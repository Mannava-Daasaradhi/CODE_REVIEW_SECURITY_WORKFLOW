from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.environment.episode_loader import EpisodeNotFoundError
from app.models.observation import Observation

router = APIRouter()


class ResetRequest(BaseModel):
    task_difficulty: str | None = None


@router.post("/reset", response_model=Observation)
async def reset(request: Request, body: ResetRequest = ResetRequest()) -> Observation:
    """
    Start a new episode.

    Optional body: { "task_difficulty": "easy" | "medium" | "hard" }
    Omit or pass null to cycle through difficulties round-robin.
    """
    env = request.app.state.env
    try:
        return await env.reset(body.task_difficulty)  # FIX: await — env.reset() is now async
    except EpisodeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

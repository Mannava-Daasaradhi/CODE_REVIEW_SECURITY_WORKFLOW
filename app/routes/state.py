from fastapi import APIRouter, Request

from app.models.state import EnvironmentState

router = APIRouter()


@router.get("/state", response_model=EnvironmentState)
async def state(request: Request) -> EnvironmentState:
    """
    Return current environment state for debugging and inspection.
    Does not expose ground truth.
    """
    return request.app.state.env.state()

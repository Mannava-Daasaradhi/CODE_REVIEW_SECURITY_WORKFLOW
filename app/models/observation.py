from pydantic import BaseModel


class Observation(BaseModel):
    """
    Returned to the agent by POST /reset and POST /step.
    Never contains ground truth — that is server-side only.
    """
    task_id: str
    difficulty: str  # "easy" | "medium" | "hard"
    code_snippet: str
    instructions: str

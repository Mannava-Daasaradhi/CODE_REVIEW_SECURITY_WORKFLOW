from pydantic import BaseModel


class Observation(BaseModel):
    task_id: str
    difficulty: str
    code_snippet: str
    instructions: str

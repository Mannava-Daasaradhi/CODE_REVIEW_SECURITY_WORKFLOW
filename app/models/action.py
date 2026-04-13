from pydantic import BaseModel, Field


class Finding(BaseModel):
    type: str
    description: str


class Action(BaseModel):
    flagged_lines: list[int] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    review_text: str = ""

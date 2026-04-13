from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str


class Action(BaseModel):
    model_config = ConfigDict(strict=True)

    flagged_lines: list[int]
    findings: list[Finding]
    review_text: str
from pydantic import BaseModel, Field


class Finding(BaseModel):
    type: str
    description: str


class Action(BaseModel):
    flagged_lines: list[int] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    review_text: str = ""

from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str
    description: str = ""


class Action(BaseModel):
    model_config = ConfigDict(strict=True)

    flagged_lines: list[int] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    review_text: str = ""

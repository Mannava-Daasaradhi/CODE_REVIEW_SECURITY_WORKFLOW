from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str


class Action(BaseModel):
    model_config = ConfigDict(strict=True)

    flagged_lines: list[int]
    findings: list[Finding]
    review_text: str

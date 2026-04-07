from pydantic import BaseModel, Field


class Finding(BaseModel):
    type: str = Field(..., description="Vulnerability type, e.g. 'sql_injection', 'hardcoded_secret'")
    description: str = Field(..., description="Human-readable description of the finding")


class Action(BaseModel):
    """
    The structured output submitted by an AI agent to POST /step.

    All fields are optional — graders award partial credit for what is provided.
    Task 1 graders score flagged_lines only.
    Task 2 graders score findings only.
    Task 3 graders score all three fields in a weighted composite.
    """
    flagged_lines: list[int] = Field(
        default_factory=list,
        description="Line numbers (1-indexed) where bugs were detected"
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="Structured vulnerability findings"
    )
    review_text: str = Field(
        default="",
        description="Free-form code review text (scored in Task 3 only)"
    )

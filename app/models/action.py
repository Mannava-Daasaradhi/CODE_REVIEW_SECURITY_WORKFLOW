from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(strict=True)  # FIX: strict mode at route boundary

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
    model_config = ConfigDict(strict=True)  # FIX: strict mode — rejects unexpected field types

    flagged_lines: list[int] = Field(
        default_factory=list,
        description="Line numbers (1-indexed, ge=1) where bugs were detected",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="Structured vulnerability findings",
    )
    review_text: str = Field(
        default="",
        description="Free-form code review text (scored in Task 3 only)",
    )

    # FIX: validate that all flagged line numbers are >= 1 (1-indexed, no zero or negative)
    @classmethod
    def model_post_init(cls, __context) -> None:
        pass  # validation handled via validator below

    from pydantic import field_validator

    @field_validator("flagged_lines")
    @classmethod
    def lines_must_be_positive(cls, v: list[int]) -> list[int]:
        invalid = [n for n in v if n < 1]
        if invalid:
            raise ValueError(f"flagged_lines must be 1-indexed (≥1). Invalid values: {invalid}")
        return v

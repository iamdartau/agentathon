from typing import Any
from pydantic import BaseModel


class RunRequest(BaseModel):
    reviews: list[dict] | None = None
    query: str | None = None
    context: dict[str, Any] = {}


class RunResponse(BaseModel):
    status: str
    use_case_id: str = "18"
    result: dict[str, Any]
    agents_used: list[str]
    trace_id: str
    runtime_seconds: float
    sample_mode: bool

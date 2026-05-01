from pydantic import BaseModel, Field


class SessionInitResponse(BaseModel):
    session_id: str
    workspace_context: dict | None


class TranscribeResponse(BaseModel):
    transcript: str
    duration_ms: int = 0
    language: str = "en"


class InterpretRequest(BaseModel):
    session_id: str
    transcript: str


class InterpretResponse(BaseModel):
    requires_clarification: bool = False
    operations: list[dict] | None = None
    clarification_questions: list[dict] | None = None


class ClarifyRequest(BaseModel):
    session_id: str
    answers: dict[str, str]


class ExecuteRequest(BaseModel):
    session_id: str
    operation_ids: list[str]
    edits: dict[str, dict] | None = None


class ExecuteResponse(BaseModel):
    results: list[dict]

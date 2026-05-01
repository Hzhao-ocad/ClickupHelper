import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import InterpretRequest, ClarifyRequest
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/interpret")
async def interpret_transcript(request: Request, body: InterpretRequest):
    session_service = request.app.state.session_service
    settings = request.app.state.settings
    session = session_service.get_session(body.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session expired or invalid. Please refresh the page.")

    if not settings.deepseek_api_key:
        raise HTTPException(status_code=500, detail="DeepSeek API key is not configured.")

    llm = LLMService(settings)
    result = llm.interpret(
        transcript=body.transcript,
        workspace_context=session.workspace_context,
        conversation_history=session.conversation_history,
    )

    if not result.get("requires_clarification"):
        ops = result.get("operations", [])
        session_service.store_operations(body.session_id, ops)
        # Save this interaction in history
        session_service.append_history(body.session_id, {
            "role": "user",
            "content": body.transcript,
        })
        session_service.append_history(body.session_id, {
            "role": "assistant",
            "content": f"Produced {len(ops)} operations: {[op['type'] for op in ops]}",
        })

    return result


@router.post("/clarify")
async def clarify_request(request: Request, body: ClarifyRequest):
    session_service = request.app.state.session_service
    settings = request.app.state.settings
    session = session_service.get_session(body.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session expired or invalid. Please refresh the page.")

    if not settings.deepseek_api_key:
        raise HTTPException(status_code=500, detail="DeepSeek API key is not configured.")

    # Build the user's clarification answers as a follow-up message
    answers_text = "Here are my clarifications:\n" + "\n".join(
        f"- {q}: {a}" for q, a in body.answers.items()
    )

    session_service.append_history(body.session_id, {
        "role": "assistant",
        "content": "I asked for clarifications.",
    })
    session_service.append_history(body.session_id, {
        "role": "user",
        "content": answers_text,
    })

    llm = LLMService(settings)
    result = llm.interpret(
        transcript=answers_text,
        workspace_context=session.workspace_context,
        conversation_history=session.conversation_history,
    )

    if not result.get("requires_clarification"):
        ops = result.get("operations", [])
        session_service.store_operations(body.session_id, ops)

    return result

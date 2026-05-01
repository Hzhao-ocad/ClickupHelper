import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import ExecuteRequest
from app.services.clickup_service import ClickUpService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute")
async def execute_operations(request: Request, body: ExecuteRequest):
    session_service = request.app.state.session_service
    settings = request.app.state.settings
    session = session_service.get_session(body.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session expired or invalid. Please refresh the page.")

    if not settings.clickup_api_token:
        raise HTTPException(status_code=500, detail="ClickUp API token is not configured.")

    # Apply edits
    if body.edits:
        for op_id, edits in body.edits.items():
            session_service.update_operation(body.session_id, op_id, edits)

    # Get operations
    ops = session_service.get_operations(body.session_id, body.operation_ids)
    if not ops:
        raise HTTPException(status_code=400, detail="No operations found to execute.")

    # Execute
    cu = ClickUpService(
        api_token=settings.clickup_api_token,
        rate_limit_delay_ms=settings.clickup_rate_limit_delay_ms,
    )
    try:
        results = await cu.execute_batch(ops)
        return {"results": results}
    finally:
        await cu.close()

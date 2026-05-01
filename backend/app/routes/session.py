import logging

from fastapi import APIRouter, HTTPException, Request

from app.services.clickup_service import ClickUpService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/session/init")
async def init_session(request: Request):
    session_service = request.app.state.session_service
    settings = request.app.state.settings

    session = session_service.create_session()

    if settings.clickup_api_token:
        try:
            cu = ClickUpService(
                api_token=settings.clickup_api_token,
                rate_limit_delay_ms=settings.clickup_rate_limit_delay_ms,
            )
            context = await cu.fetch_workspace_context()
            session.workspace_context = context
            await cu.close()
        except Exception as e:
            logger.exception("Failed to fetch ClickUp workspace context")
            session.workspace_context = {"error": str(e), "team": None, "spaces": [], "members": []}
    else:
        session.workspace_context = {"team": None, "spaces": [], "members": []}

    return {
        "session_id": session.session_id,
        "workspace_context": session.workspace_context,
    }

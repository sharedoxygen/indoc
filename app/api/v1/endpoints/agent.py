"""
Autonomous research agent endpoints.

Exposes inDoc's ReAct agent: give it a goal and it will plan, search, read, and
re-plan over the user's accessible documents until it can answer - returning
both the answer and its full reasoning trace.
"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStepSchema
from app.services.agent.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentRunResponse:
    """
    Run the autonomous research agent toward a goal.

    The agent reasons step by step, choosing tools (list / search / read) over
    the caller's access-controlled documents, and returns a grounded answer
    together with the full thought -> action -> observation trace.
    """
    agent = AgentService(db, current_user)
    document_ids = (
        [str(doc_id) for doc_id in request.document_ids]
        if request.document_ids
        else None
    )

    logger.info(
        f"Agent run started by user={current_user.id} goal={request.goal[:80]!r}"
    )
    result = await agent.run(
        goal=request.goal,
        document_ids=document_ids,
        max_steps=request.max_steps,
    )

    return AgentRunResponse(
        goal=result.goal,
        final_answer=result.final_answer,
        steps=[
            AgentStepSchema(
                step=s.step,
                thought=s.thought,
                action=s.action,
                action_input=s.action_input,
                observation=s.observation,
            )
            for s in result.steps
        ],
        iterations=result.iterations,
        stopped_reason=result.stopped_reason,
        tools_available=result.tools_available,
    )


@router.post("/stream")
async def stream_agent(
    request: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Run the agent and stream each reasoning step as a Server-Sent Event as it
    happens, so a UI can show the agent thinking in real time.

    Event stream (one JSON object per `data:` line):
      {"type": "start",  "goal", "tools_available"}
      {"type": "step",   "step", "thought", "action", "action_input", "observation"}
      {"type": "final",  "final_answer", "iterations", "stopped_reason"}
    """
    agent = AgentService(db, current_user)
    document_ids = (
        [str(doc_id) for doc_id in request.document_ids]
        if request.document_ids
        else None
    )

    async def event_source():
        try:
            async for event in agent.run_stream(
                goal=request.goal,
                document_ids=document_ids,
                max_steps=request.max_steps,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:  # surface failures to the client, don't hang
            logger.error(f"Agent stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

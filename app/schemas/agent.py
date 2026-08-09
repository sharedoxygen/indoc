"""
Schemas for the autonomous research agent API.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Request to run the autonomous agent toward a goal."""
    goal: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The research goal or question for the agent to work on.",
    )
    document_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional documents to focus on. If omitted, the agent may "
        "search across everything the user can access.",
    )
    max_steps: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Maximum reason/act cycles before the agent must answer.",
    )


class AgentStepSchema(BaseModel):
    """One step of the agent's reasoning trace."""
    step: int
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: str


class AgentRunResponse(BaseModel):
    """The agent's answer plus its full, auditable reasoning trace."""
    goal: str
    final_answer: str
    steps: List[AgentStepSchema]
    iterations: int
    stopped_reason: str
    tools_available: List[str]

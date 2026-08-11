"""
Autonomous research agent for inDoc.

This is a genuine ReAct-style agent loop: given a goal, the LLM plans, chooses
a tool, observes the result, and re-plans - iterating until it can answer or a
step budget is reached. Unlike single-shot RAG, the model decides *what to do
next* at every step. Every tool call is scope-enforced, so the agent can reason
autonomously over a regulated document library without ever seeing data the
requesting user isn't authorized to access.

The full reasoning trace (thought -> action -> observation for each step) is
returned to the caller, so the agent's work is transparent and auditable rather
than a black box.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.user import User
from app.services.agent.tools import AgentTools, ToolError
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Reasoning steps should be deterministic and factual, not creative.
PLANNER_TEMPERATURE = 0.1
MAX_OBSERVATION_CHARS = 1800
DEFAULT_MAX_STEPS = 6
HARD_MAX_STEPS = 12

# LLMService returns this prose when every provider fails. Treat as outage, not a brief.
_LLM_UNAVAILABLE_MARKERS = (
    "ai service is temporarily unavailable",
    "all llm providers failed",
)


@dataclass
class AgentStep:
    """A single reason -> act -> observe cycle."""
    step: int
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: str


@dataclass
class AgentResult:
    """The outcome of an agent run, including its full reasoning trace."""
    goal: str
    final_answer: str
    steps: List[AgentStep] = field(default_factory=list)
    iterations: int = 0
    stopped_reason: str = "completed"
    tools_available: List[str] = field(default_factory=list)


class AgentService:
    """Runs the autonomous research loop over a user's accessible documents."""

    def __init__(self, db, user: User, llm_service: Optional[LLMService] = None):
        self.db = db
        self.user = user
        self.llm = llm_service or LLMService()
        self.tools = AgentTools(db, user, llm_service=self.llm)

    async def run(
        self,
        goal: str,
        document_ids: Optional[List[str]] = None,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> AgentResult:
        """Execute the agent loop toward `goal` and return the result + trace.

        This is a thin collector over `run_stream`, so the batch and streaming
        paths share exactly one implementation of the reasoning loop.
        """
        result = AgentResult(
            goal=goal,
            final_answer="",
            tools_available=self.tools.tool_names(),
        )
        async for event in self.run_stream(goal, document_ids, max_steps):
            if event["type"] == "step":
                result.steps.append(
                    AgentStep(
                        step=event["step"],
                        thought=event["thought"],
                        action=event["action"],
                        action_input=event["action_input"],
                        observation=event["observation"],
                    )
                )
            elif event["type"] == "final":
                result.final_answer = event["final_answer"]
                result.iterations = event["iterations"]
                result.stopped_reason = event["stopped_reason"]
        return result

    async def run_stream(
        self,
        goal: str,
        document_ids: Optional[List[str]] = None,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        """Run the agent loop, yielding an event per reasoning step as it happens.

        Event shapes:
          {"type": "start",  "goal", "tools_available"}
          {"type": "planning", "step"}  # LLM deciding next action
          {"type": "tool_start", "step", "thought", "action", "action_input"}
          {"type": "step",   "step", "thought", "action", "action_input", "observation"}
          {"type": "final",  "final_answer", "iterations", "stopped_reason"}

        Mid-step events let the UI show planning vs tool execution in real time.
        """
        max_steps = max(1, min(int(max_steps or DEFAULT_MAX_STEPS), HARD_MAX_STEPS))
        yield {
            "type": "start",
            "goal": goal,
            "tools_available": self.tools.tool_names(),
        }

        scratchpad: List[AgentStep] = []
        seen_actions: set = set()

        for step_num in range(1, max_steps + 1):
            yield {"type": "planning", "step": step_num}
            decision = await self._plan(goal, scratchpad, document_ids)
            thought = decision.get("thought", "")
            action = decision.get("action", "")
            action_input = decision.get("action_input") or {}

            if decision.get("stopped_reason") == "llm_unavailable":
                message = (
                    action_input.get("answer")
                    or "The AI service is unavailable. Check Ollama and the configured model."
                )
                yield {"type": "error", "message": message}
                return

            # Terminal action: the agent believes it can answer.
            if action == "finish":
                final_answer = (
                    action_input.get("answer")
                    or decision.get("final_answer")
                    or "The agent finished without producing an answer."
                )
                yield {
                    "type": "final",
                    "final_answer": final_answer,
                    "iterations": step_num - 1,
                    "stopped_reason": decision.get("stopped_reason") or "completed",
                }
                return

            yield {
                "type": "tool_start",
                "step": step_num,
                "thought": thought,
                "action": action,
                "action_input": action_input,
            }

            # Loop guard: if the agent repeats the exact same action, don't
            # waste the budget re-running it.
            action_signature = f"{action}:{json.dumps(action_input, sort_keys=True, default=str)}"
            if action_signature in seen_actions:
                logger.info("Agent repeated an action; nudging it to change course.")
                observation = (
                    "You already performed this exact action. Do not repeat it - "
                    "either try something different or finish with an answer."
                )
            else:
                seen_actions.add(action_signature)
                observation = await self._act(action, action_input)

            step = AgentStep(
                step=step_num,
                thought=thought,
                action=action or "(no action)",
                action_input=action_input,
                observation=observation,
            )
            scratchpad.append(step)
            yield {
                "type": "step",
                "step": step.step,
                "thought": step.thought,
                "action": step.action,
                "action_input": step.action_input,
                "observation": step.observation,
            }

        # Budget exhausted without an explicit finish - synthesize a final
        # answer from everything gathered so far rather than returning nothing.
        final_answer = await self._synthesize(goal, scratchpad)
        if self._looks_like_llm_outage(final_answer):
            yield {
                "type": "error",
                "message": (final_answer or "").strip()
                or "The AI service is unavailable. Check Ollama and the configured model.",
            }
            return
        yield {
            "type": "final",
            "final_answer": final_answer,
            "iterations": max_steps,
            "stopped_reason": "max_steps_reached",
        }

    # --- Planning ---------------------------------------------------------

    async def _plan(
        self,
        goal: str,
        scratchpad: List[AgentStep],
        document_ids: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Ask the LLM for the next action as a single JSON object."""
        prompt = self._build_planner_prompt(goal, scratchpad, document_ids)
        raw = await self.llm.generate_response(
            prompt=prompt,
            max_tokens=800,
            temperature=PLANNER_TEMPERATURE,
            raw=True,
        )
        if self._looks_like_llm_outage(raw):
            return self._llm_unavailable_decision(raw)

        decision = self._parse_decision(raw)
        if decision is not None:
            return decision

        # One corrective retry: models sometimes wrap or narrate the JSON.
        retry = await self.llm.generate_response(
            prompt=prompt
            + "\n\nYour previous reply was not valid JSON. Reply with ONLY a "
            "single JSON object and nothing else.",
            max_tokens=800,
            temperature=0.0,
            raw=True,
        )
        if self._looks_like_llm_outage(retry):
            return self._llm_unavailable_decision(retry)

        decision = self._parse_decision(retry)
        if decision is not None:
            return decision

        # Prefer synthesizing from gathered evidence over an empty abort.
        # Empty/unparseable plans after LIST were producing BRIEF·PARTIAL with
        # "The agent could not complete the task." despite usable observations.
        if scratchpad:
            logger.warning(
                "Agent planner failed to return JSON after %d step(s); synthesizing.",
                len(scratchpad),
            )
            answer = (await self._synthesize(goal, scratchpad) or "").strip()
            if self._looks_like_llm_outage(answer):
                return self._llm_unavailable_decision(answer)
            return {
                "thought": "Could not produce a structured next action; synthesizing from evidence.",
                "action": "finish",
                "action_input": {
                    "answer": answer
                    or "Evidence was gathered, but a final structured answer could not be produced."
                },
                "stopped_reason": "planning_failed",
            }

        prose = (retry or raw or "").strip()
        return {
            "thought": "Could not produce a structured action; answering directly.",
            "action": "finish",
            "action_input": {
                "answer": prose or "The agent could not complete the task."
            },
            "stopped_reason": "planning_failed",
        }

    @staticmethod
    def _looks_like_llm_outage(text: Optional[str]) -> bool:
        if not text:
            return False
        lower = text.lower()
        return any(marker in lower for marker in _LLM_UNAVAILABLE_MARKERS)

    @staticmethod
    def _llm_unavailable_decision(detail: str) -> Dict[str, Any]:
        return {
            "thought": "LLM provider unavailable.",
            "action": "finish",
            "action_input": {
                "answer": (detail or "").strip()
                or "The AI service is unavailable. Check that Ollama is running and a chat model is installed."
            },
            "stopped_reason": "llm_unavailable",
        }

    def _build_planner_prompt(
        self,
        goal: str,
        scratchpad: List[AgentStep],
        document_ids: Optional[List[str]],
    ) -> str:
        tool_lines = []
        for tool in self.tools.describe():
            schema = tool["input_schema"]
            schema_str = json.dumps(schema) if schema else "{}"
            tool_lines.append(
                f'- "{tool["name"]}": {tool["description"]} '
                f"Input: {schema_str}"
            )
        tools_block = "\n".join(tool_lines)

        history_block = self._render_scratchpad(scratchpad)
        scope_note = ""
        if document_ids:
            scope_note = (
                "\nThe user has pre-selected these document ids as the focus: "
                + ", ".join(str(d) for d in document_ids)
                + "\n"
            )

        return f"""You are inDoc's autonomous research agent. You work toward the user's \
goal by reasoning step by step and using tools over the user's PRIVATE, \
access-controlled document library. You can only ever see documents the user \
is authorized to access. Never invent document contents or facts - if you did \
not read it via a tool, you do not know it.

AVAILABLE TOOLS:
{tools_block}

RULES:
1. Respond with EXACTLY ONE JSON object and nothing else - no prose, no markdown fences.
2. The JSON must have keys: "thought" (your reasoning), "action" (one tool name), \
and "action_input" (an object matching that tool's input).
3. Take one action at a time. Read observations before deciding the next step.
4. When you have enough grounded evidence, use the "finish" action with a clear, \
cited answer that references the documents you used.
5. Prefer to search or list first, then read the specific documents that matter.

GOAL:
{goal}
{scope_note}
{history_block}

Respond now with the next single JSON action."""

    def _render_scratchpad(self, scratchpad: List[AgentStep]) -> str:
        if not scratchpad:
            return "No steps taken yet. This is your first action."
        blocks = ["Work so far:"]
        for s in scratchpad:
            blocks.append(
                f"Step {s.step}:\n"
                f"  Thought: {s.thought}\n"
                f"  Action: {s.action} {json.dumps(s.action_input, default=str)}\n"
                f"  Observation: {s.observation}"
            )
        return "\n".join(blocks)

    # --- Acting -----------------------------------------------------------

    async def _act(self, action: str, action_input: Dict[str, Any]) -> str:
        """Execute a tool and return a bounded text observation."""
        try:
            observation = await self.tools.execute(action, action_input)
        except ToolError as e:
            return f"Tool error: {e}"
        except Exception as e:  # never let a tool crash the loop
            logger.error(f"Agent tool '{action}' failed: {e}", exc_info=True)
            return f"Tool '{action}' failed unexpectedly: {e}"

        if observation and len(observation) > MAX_OBSERVATION_CHARS:
            observation = observation[:MAX_OBSERVATION_CHARS] + "... (truncated)"
        return observation

    async def _synthesize(self, goal: str, scratchpad: List[AgentStep]) -> str:
        """Force a final grounded answer when the step budget runs out."""
        history_block = self._render_scratchpad(scratchpad)
        prompt = f"""You are inDoc's research agent. You have run out of research \
steps. Using ONLY the evidence you already gathered below, write the best \
grounded answer you can to the goal. If the evidence is insufficient, say so \
plainly rather than guessing.

GOAL:
{goal}

{history_block}

Write the final answer now."""
        return await self.llm.generate_response(
            prompt=prompt, max_tokens=1200, temperature=0.2, raw=True
        )

    # --- Parsing ----------------------------------------------------------

    def _parse_decision(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract a decision JSON object from a possibly-noisy LLM reply."""
        if not raw:
            return None
        candidate = self._extract_json_object(raw)
        if candidate is None:
            return None
        try:
            data = json.loads(candidate)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict) or "action" not in data:
            return None
        # Normalize: action_input must be a dict.
        if not isinstance(data.get("action_input"), dict):
            data["action_input"] = {}
        return data

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        """Find the first balanced {...} JSON object in text, tolerating fences."""
        # Strip common code-fence wrappers first.
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            return fence.group(1)

        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        return None

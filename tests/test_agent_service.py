"""
Tests for the autonomous research agent (ReAct loop).

These tests drive the agent with a scripted LLM so we can verify the real
behaviour that makes it agentic - multi-step planning, tool execution, observing
results, and terminating with a grounded answer - without needing a live model
or search backend.
"""
import json

import pytest

from app.services.agent.agent_service import AgentService, AgentResult


class ScriptedLLM:
    """A fake LLMService that returns a predetermined sequence of replies."""

    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    async def generate_response(self, prompt, **kwargs):
        self.calls.append(prompt)
        if self._replies:
            return self._replies.pop(0)
        # Default terminal answer if the script runs out.
        return json.dumps({
            "thought": "done",
            "action": "finish",
            "action_input": {"answer": "fallback answer"},
        })


class FakeTools:
    """Records tool calls and returns canned observations."""

    def __init__(self):
        self.executed = []

    def tool_names(self):
        return ["list_documents", "search_documents", "read_document", "finish"]

    def describe(self):
        return [
            {"name": "search_documents", "description": "search", "input_schema": {}},
            {"name": "read_document", "description": "read", "input_schema": {}},
            {"name": "finish", "description": "finish", "input_schema": {}},
        ]

    async def execute(self, action, action_input):
        self.executed.append((action, action_input))
        if action == "search_documents":
            return "Top 1 result: id=doc-1 title=Q3 Report score=0.9"
        if action == "read_document":
            return "Content of 'Q3 Report': Revenue grew 18% year over year."
        return "ok"


def _make_agent(replies):
    agent = AgentService.__new__(AgentService)  # bypass real __init__
    agent.db = None
    agent.user = None
    agent.llm = ScriptedLLM(replies)
    agent.tools = FakeTools()
    return agent


@pytest.mark.asyncio
async def test_agent_runs_multi_step_then_finishes():
    """Agent should search, then read, then finish - a real 2-tool plan."""
    replies = [
        json.dumps({
            "thought": "I should find the relevant report first.",
            "action": "search_documents",
            "action_input": {"query": "Q3 revenue"},
        }),
        json.dumps({
            "thought": "Found it. Now read the report for the exact figure.",
            "action": "read_document",
            "action_input": {"document_id": "doc-1"},
        }),
        json.dumps({
            "thought": "I have the figure and can answer.",
            "action": "finish",
            "action_input": {"answer": "Revenue grew 18% YoY per the Q3 Report."},
        }),
    ]
    agent = _make_agent(replies)

    result: AgentResult = await agent.run(goal="What was Q3 revenue growth?", max_steps=6)

    assert result.stopped_reason == "completed"
    assert "18%" in result.final_answer
    # Two tools were actually executed before finishing.
    assert [a for a, _ in agent.tools.executed] == ["search_documents", "read_document"]
    # The trace records both acting steps.
    assert len(result.steps) == 2
    assert result.steps[0].action == "search_documents"
    assert result.steps[1].action == "read_document"
    assert result.iterations == 2


@pytest.mark.asyncio
async def test_agent_parses_json_in_code_fences():
    """The planner must tolerate models that wrap JSON in markdown fences."""
    replies = [
        "Sure! Here is my plan:\n```json\n"
        + json.dumps({
            "thought": "answer directly",
            "action": "finish",
            "action_input": {"answer": "42"},
        })
        + "\n```",
    ]
    agent = _make_agent(replies)

    result = await agent.run(goal="What is the answer?", max_steps=3)

    assert result.final_answer == "42"
    assert result.stopped_reason == "completed"


@pytest.mark.asyncio
async def test_agent_synthesizes_when_budget_exhausted():
    """If the agent never finishes, it must synthesize rather than return empty."""
    # Every step searches; it never chooses finish.
    search_reply = json.dumps({
        "thought": "keep searching",
        "action": "search_documents",
        "action_input": {"query": "anything"},
    })
    # Provide enough search replies for the budget, then a synthesis answer.
    replies = [search_reply, search_reply, "Synthesized final answer from evidence."]
    agent = _make_agent(replies)

    result = await agent.run(goal="Open ended question", max_steps=2)

    assert result.stopped_reason == "max_steps_reached"
    assert result.final_answer == "Synthesized final answer from evidence."
    assert result.iterations == 2


@pytest.mark.asyncio
async def test_agent_stream_emits_events_in_order():
    """run_stream must emit start -> step -> final so a UI can render live."""
    replies = [
        json.dumps({
            "thought": "look it up",
            "action": "search_documents",
            "action_input": {"query": "x"},
        }),
        json.dumps({
            "thought": "answer",
            "action": "finish",
            "action_input": {"answer": "the answer"},
        }),
    ]
    agent = _make_agent(replies)

    events = [ev async for ev in agent.run_stream(goal="q", max_steps=4)]

    assert events[0]["type"] == "start"
    assert events[0]["tools_available"]
    step_events = [e for e in events if e["type"] == "step"]
    assert len(step_events) == 1
    assert step_events[0]["action"] == "search_documents"
    assert events[-1]["type"] == "final"
    assert events[-1]["final_answer"] == "the answer"
    assert events[-1]["stopped_reason"] == "completed"


@pytest.mark.asyncio
async def test_agent_detects_repeated_action():
    """Repeating the identical action should be blocked, not executed twice."""
    same_search = json.dumps({
        "thought": "search again",
        "action": "search_documents",
        "action_input": {"query": "same"},
    })
    finish = json.dumps({
        "thought": "ok answer",
        "action": "finish",
        "action_input": {"answer": "done"},
    })
    agent = _make_agent([same_search, same_search, finish])

    result = await agent.run(goal="test loop guard", max_steps=6)

    # The tool executed only once despite the model asking twice.
    assert agent.tools.executed.count(("search_documents", {"query": "same"})) == 1
    # The second step recorded the loop-guard observation.
    assert "already performed" in result.steps[1].observation.lower()

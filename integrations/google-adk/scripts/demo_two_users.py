#!/usr/bin/env python3
"""
Two-user demo: the same question asked as the inDoc manager and as the analyst.

    python scripts/demo_two_users.py --mode local
    python scripts/demo_two_users.py --mode deployed --resource projects/.../reasoningEngines/ID

Tokens are read from the files named by INDOC_MANAGER_TOKEN_FILE and
INDOC_ANALYST_TOKEN_FILE (minted by scripts/run_demo.sh) and are never printed
or written. Writes a Markdown report and exits non-zero if a check fails.
"""
import argparse
import asyncio
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

QUESTION = "What are the termination terms in our vendor contracts?"
APP_NAME = "indoc_research_agent"
SESSION_TTL = "3600s"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
RESTRICTED_MARKERS = ["Halvorsen", "Brightline", "ninety (90)", "fifteen percent"]
USERS = [
    ("manager", "manager.demo@example.com", "INDOC_MANAGER_TOKEN_FILE"),
    ("analyst", "analyst.demo@example.com", "INDOC_ANALYST_TOKEN_FILE"),
]


@dataclass
class Transcript:
    label: str
    email: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, str]] = field(default_factory=list)
    answer: str = ""


def _read_token(env_var: str) -> str:
    path = os.environ.get(env_var)
    if not path:
        raise SystemExit(f"{env_var} is not set")
    return Path(path).read_text().strip()


def _record_part(transcript: Transcript, part: Dict[str, Any]) -> None:
    if part.get("function_call"):
        call = part["function_call"]
        transcript.tool_calls.append({"name": call.get("name"), "args": call.get("args") or {}})
    elif part.get("function_response"):
        response = part["function_response"]
        transcript.tool_results.append({"name": response.get("name"), "text": _response_text(response)})
    elif part.get("text") and not part.get("thought"):
        transcript.answer += part["text"]


def _response_text(function_response: Dict[str, Any]) -> str:
    payload = function_response.get("response") or {}
    content = payload.get("content") or payload.get("result", {}).get("content") or []
    texts = [block.get("text", "") for block in content if isinstance(block, dict)]
    return "\n".join(texts) if texts else str(payload)


async def run_local(question: str) -> List[Transcript]:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from indoc_agent.agent import TOKEN_STATE_KEY, root_agent

    sessions = InMemorySessionService()
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=sessions)
    transcripts = []
    for label, email, token_env in USERS:
        transcript = Transcript(label, email)
        session = await sessions.create_session(
            app_name=APP_NAME, user_id=email, state={TOKEN_STATE_KEY: _read_token(token_env)}
        )
        message = types.Content(role="user", parts=[types.Part(text=question)])
        async for event in runner.run_async(user_id=email, session_id=session.id, new_message=message):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    _record_part(transcript, part.model_dump(exclude_none=True))
        transcripts.append(transcript)
    return transcripts


async def run_deployed(question: str, resource: str, project: str, region: str) -> List[Transcript]:
    import vertexai

    from indoc_agent.agent import TOKEN_STATE_KEY

    client = vertexai.Client(project=project, location=region)
    remote = client.agent_engines.get(name=resource)
    transcripts = []
    for label, email, token_env in USERS:
        transcript = Transcript(label, email)
        session = await remote.async_create_session(
            user_id=email, state={TOKEN_STATE_KEY: _read_token(token_env)}, ttl=SESSION_TTL
        )
        try:
            async for event in remote.async_stream_query(user_id=email, session_id=session["id"], message=question):
                for part in (event.get("content") or {}).get("parts") or []:
                    _record_part(transcript, part)
        finally:
            await remote.async_delete_session(user_id=email, session_id=session["id"])
        transcripts.append(transcript)
    return transcripts


def evaluate(manager: Transcript, analyst: Transcript) -> List[Dict[str, Any]]:
    manager_search_ids = {
        doc_id
        for result in manager.tool_results
        if result["name"] == "search_documents"
        for doc_id in UUID_RE.findall(result["text"])
    }
    cited = sorted(set(UUID_RE.findall(manager.answer)) & manager_search_ids)
    analyst_seen = analyst.answer + "\n".join(r["text"] for r in analyst.tool_results)
    leaked_ids = sorted(doc_id for doc_id in manager_search_ids if doc_id in analyst_seen)
    leaked_markers = [m for m in RESTRICTED_MARKERS if m.lower() in analyst_seen.lower()]
    return [
        {
            "check": "Manager answer cites restricted documents by id",
            "passed": bool(cited),
            "evidence": ", ".join(cited) or "no cited ids",
        },
        {
            "check": "Analyst received no restricted ids or contract text",
            "passed": not leaked_ids and not leaked_markers,
            "evidence": ", ".join(leaked_ids + leaked_markers) or "none",
        },
        {
            "check": "Both users' agents searched inDoc",
            "passed": all(any(c["name"] == "search_documents" for c in t.tool_calls) for t in (manager, analyst)),
            "evidence": "; ".join(f"{t.label}: {len(t.tool_calls)} tool call(s)" for t in (manager, analyst)),
        },
    ]


def render_report(args, transcripts: List[Transcript], checks: List[Dict[str, Any]], started: datetime) -> str:
    import google.adk

    lines = [
        "# inDoc + Gemini ADK connector: two-user demo results",
        "",
        f"- Run started (UTC): {started.isoformat(timespec='seconds')}",
        f"- Mode: {args.mode}",
        f"- Google Cloud project / region: {args.project} / {args.region}",
        f"- Model: {os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}",
        f"- ADK version: {google.adk.__version__}",
        f"- MCP endpoint host: {urlparse(os.environ.get('INDOC_MCP_URL', '')).netloc}",
    ]
    if args.resource:
        lines.append(f"- Agent Runtime resource: `{args.resource}`")
    lines += ["", f"Question asked by both users: **{args.question}**", "", "## Checks", ""]
    lines += ["| Check | Result | Evidence |", "|---|---|---|"]
    lines += [f"| {c['check']} | {'PASS' if c['passed'] else 'FAIL'} | {c['evidence']} |" for c in checks]
    for t in transcripts:
        lines += ["", f"## {t.label.capitalize()} ({t.email})", "", "Tool calls:", ""]
        lines += [f"- `{c['name']}` {c['args']}" for c in t.tool_calls] or ["- none"]
        lines += ["", "Answer:", "", t.answer.strip() or "_(no answer)_"]
    lines += ["", "Tokens are short-lived, per user, and not recorded here. Demo data is synthetic.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--mode", choices=["local", "deployed"], required=True)
    parser.add_argument("--resource", help="Agent Runtime resource name (deployed mode)")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.environ.get("GOOGLE_CLOUD_LOCATION"))
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--output", default="DEMO_RESULTS.md")
    args = parser.parse_args()
    if args.mode == "deployed" and not args.resource:
        parser.error("--resource is required in deployed mode")

    started = datetime.now(timezone.utc)
    if args.mode == "local":
        transcripts = asyncio.run(run_local(args.question))
    else:
        transcripts = asyncio.run(run_deployed(args.question, args.resource, args.project, args.region))

    checks = evaluate(*transcripts)
    report = render_report(args, transcripts, checks, started)
    Path(args.output).write_text(report)
    print(report)
    sys.exit(0 if all(c["passed"] for c in checks) else 1)


if __name__ == "__main__":
    main()

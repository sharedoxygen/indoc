# inDoc research agent on Google ADK (via MCP)

A Gemini agent built with Google's Agent Development Kit that answers questions
over a self-hosted inDoc library through inDoc's MCP server. Each request
carries the end user's own inDoc token, so inDoc's existing RBAC/ABAC decides
what the agent can see. Two users asking the same question get different,
cited answers.

```
User ── question ──▶ ADK LlmAgent (Gemini 2.5 Flash, Vertex AI, us-central1)
                       │ McpToolset, Streamable HTTP
                       │ Authorization: Bearer <user's inDoc MCP token>
                       ▼
             ngrok edge (only /mcp passes)
                       ▼
             indoc-mcp container (127.0.0.1:8010)
               host check → token check → per-user rate limit
               AgentTools(db, user): same scope rules as inside inDoc
               one AuditLog row per tool call
                       ▼
             Postgres / Elasticsearch / Qdrant on inDoc infrastructure
```

## Components

| Path | Purpose |
|---|---|
| `app/mcp_server/` | MCP server (official `mcp` SDK 1.30, FastMCP, stateless Streamable HTTP, JSON responses). Tools: `search_documents`, `read_document`, `list_documents`. |
| `Dockerfile.mcp`, `requirements-mcp.txt` | Server image. Separate from the main app because the MCP SDK needs `anyio>=4.5`, which inDoc's FastAPI 0.104 pin excludes. |
| `tools/seed_mcp_demo.py` | Synthetic demo users and documents (idempotent; `--purge` to remove). |
| `deploy/ngrok/indoc-mcp-policy.yml` | Edge policy: everything except `/mcp` gets 404. |
| `integrations/google-adk/indoc_agent/` | The ADK agent (`root_agent`), its runtime `requirements.txt`, and scaling config. |
| `integrations/google-adk/scripts/` | `run_demo.sh` (mints tokens, runs the demo) and `demo_two_users.py` (report + checks). |

## Identity and access

- The agent never sees passwords. An operator mints a **read-scoped MCP token**
  per user: `make mcp-token EMAIL=...`. It is an inDoc JWT with its own type
  (`mcp`) and scope (`mcp:read`), capped at 60 minutes. The MCP server rejects
  ordinary inDoc session tokens, refresh tokens, expired or over-long tokens,
  and inactive users.
- The token is placed in the ADK session state (`indoc_access_token`) and sent
  on every MCP request by `header_provider`. A `before_agent_callback` refuses to
  start a turn if the token is missing or within 2 minutes of expiry, because a
  401 during MCP tool discovery would fail the turn before the model runs.
- Why a pasted token rather than ADK's OAuth flow: inDoc's login is a password
  form, not an OAuth authorization server. (ADK's own OAuth-during-discovery gap,
  google/adk-python#3331, was fixed in ADK 1.24.) Phase 4 replaces this with
  Gemini Enterprise sign-in mapped to an inDoc user.

Demo access model (inDoc rules, unchanged):

| User | Role | Sees |
|---|---|---|
| `manager.demo@example.com` | Manager | own 3 RESTRICTED finance docs, plus the analyst's 3 docs |
| `analyst.demo@example.com` | Analyst, reports to the manager | only their own 3 INTERNAL docs |

## Data residency (accurate statement)

- Documents stay in inDoc. Only tool outputs leave: search snippets (300
  characters each, up to 15 per search) and document excerpts (up to 4,000
  characters per read). The agent is instructed to read at most two documents.
- Those excerpts, the question, and the answer are processed by Gemini on the
  **regional** `us-central1` endpoint (never `global`, which gives no residency
  guarantee) and are stored by Agent Platform Sessions as session events.
- The demo creates sessions with a 1-hour TTL and deletes them when it finishes.
  The default TTL is 365 days.
- The user's MCP token is stored in session state for the life of the session.
  It expires within 60 minutes and only grants read access to that user's scope.
- Prompt and response capture in traces stays off
  (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` is the deploy default).

## Audit

Every executed tool call writes one `AuditLog` row: user, role, manager,
`action=mcp_tool_call`, tool, query or document id, outcome (`ok`,
`no_results`, `not_available`, `invalid_input`, `error`), result size, status,
latency, client IP, and `X-Indoc-Client`. Tokens and document text are never
stored. If the audit write fails, the tool output is withheld. Requests
rejected at the HTTP layer (401, 421, 429) never execute a tool and are logged
by the server, not audited, because `AuditLog` requires a known user.

## Run it

Prerequisites: inDoc data services up (Postgres, Redis, Elasticsearch, Qdrant),
Docker, the `indoc` conda env, `gcloud auth application-default login`, and the
Agent Platform API enabled on the project.

```bash
make mcp-up            # build + start indoc-mcp on 127.0.0.1:8010
make mcp-test          # 33 server tests (inside the image)
make mcp-seed          # demo users + 6 documents, indexed
cp integrations/google-adk/indoc_agent/.env.example integrations/google-adk/indoc_agent/.env
make adk-test          # agent unit tests
make adk-demo-local    # two-user demo; writes integrations/google-adk/DEMO_RESULTS.md
make mcp-tunnel        # foreground: public https://research.sharedoxygen.com/mcp
make adk-deploy        # Agent Runtime (min instances 0, max 2)
make adk-demo-deployed RESOURCE=projects/<n>/locations/us-central1/reasoningEngines/<id>
```

The demo exits non-zero unless: the manager's answer cites restricted
documents by id, the analyst's answer and tool results contain no restricted
ids or contract text, and both agents searched inDoc.

## Known limitations

- Rate limiting is in-memory, so it is per process; run one worker.
- The deployed agent depends on the tunnel being up. If another ngrok agent
  claims the same hostname, ngrok refuses to start (`ERR_NGROK_334`).
- `gemini-2.5-flash` is used because it is the Flash model this project can
  call on the `us-central1` regional endpoint today; newer Flash models are
  listed as GA but returned 404 there.
- Search filters by scope after ranking, so on very large libraries a user's
  in-scope documents can be crowded out of the top results (no data leak).

## Rollback

1. `make mcp-down` and stop the tunnel. The main inDoc API is untouched.
2. Delete the Agent Runtime deployment in the console, or with
   `client.agent_engines.delete(name=...)`.
3. `make mcp-purge` removes demo data (audit rows are retained).
4. Revert the branch. No database migration was added.

"""
inDoc MCP server: a read-only Model Context Protocol endpoint over the
platform's scope-enforced agent tools, for external agents such as Google ADK.

Modules that import the `mcp` SDK (server) run only in the `indoc-mcp`
container; `auth`, `settings`, and `mint_token` also run in the main app env.
"""

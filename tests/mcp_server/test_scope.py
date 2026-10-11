"""Per-user scope over MCP: the same call returns different data for manager vs analyst."""

import pytest

pytest.importorskip("mcp")

from .helpers import call_tool, result_text  # noqa: E402


async def test_manager_reads_restricted_contract(mcp_url, world):
    doc_id = world.finance_doc_ids["vendor_contract"]
    result = await call_tool(
        mcp_url, world.tokens["manager"], "read_document", {"document_id": doc_id}
    )
    assert not result.isError
    assert "ninety (90) days" in result_text(result)


async def test_analyst_cannot_read_restricted_contract(mcp_url, world):
    doc_id = world.finance_doc_ids["vendor_contract"]
    result = await call_tool(
        mcp_url, world.tokens["analyst"], "read_document", {"document_id": doc_id}
    )
    text = result_text(result)
    assert not result.isError
    assert "is not available to you" in text
    assert "ninety" not in text


async def test_search_is_scoped(mcp_url, world):
    vendor_id = world.finance_doc_ids["vendor_contract"]
    manager = result_text(
        await call_tool(
            mcp_url,
            world.tokens["manager"],
            "search_documents",
            {"query": "termination"},
        )
    )
    analyst = result_text(
        await call_tool(
            mcp_url,
            world.tokens["analyst"],
            "search_documents",
            {"query": "termination"},
        )
    )
    assert vendor_id in manager
    assert vendor_id not in analyst
    assert "Halvorsen" not in analyst
    assert analyst.startswith("No documents matched")


async def test_list_is_scoped(mcp_url, world):
    manager = result_text(
        await call_tool(mcp_url, world.tokens["manager"], "list_documents", {})
    )
    analyst = result_text(
        await call_tool(mcp_url, world.tokens["analyst"], "list_documents", {})
    )

    for doc_id in [*world.finance_doc_ids.values(), *world.general_doc_ids.values()]:
        assert doc_id in manager
    for doc_id in world.general_doc_ids.values():
        assert doc_id in analyst
    for doc_id in world.finance_doc_ids.values():
        assert doc_id not in analyst


async def test_analyst_reads_own_document(mcp_url, world):
    doc_id = world.general_doc_ids["travel"]
    result = await call_tool(
        mcp_url, world.tokens["analyst"], "read_document", {"document_id": doc_id}
    )
    assert "fourteen days" in result_text(result)


async def test_invalid_document_id_is_a_tool_error(mcp_url, world):
    result = await call_tool(
        mcp_url,
        world.tokens["manager"],
        "read_document",
        {"document_id": "../etc/passwd"},
    )
    assert result.isError
    assert "uuid" in result_text(result)

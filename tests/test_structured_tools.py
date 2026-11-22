import json
from pathlib import Path

import pytest

from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401


@pytest.mark.anyio
async def test_structured_tool_adapters_over_stdio():
    async with mcp_server_client(
        Path(__file__).with_name("structured_cli.py")
    ) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        assert set(tools["lookup"].input_schema["properties"]) == {"query"}

        invalid = await session.call_tool(
            "lookup", {"query": {"name": "Ada", "limit": 0}}
        )
        assert invalid.is_error
        assert "limit" in invalid.content[0].text

        rejected = await session.call_tool(
            "lookup", {"query": {"name": " ", "limit": 2}}
        )
        assert rejected.is_error
        assert "Could not adapt tool arguments" in rejected.content[0].text

        broken = await session.call_tool("broken", {})
        assert broken.is_error
        assert "Could not serialize the tool result" in broken.content[0].text

        result = await session.call_tool(
            "lookup", {"query": {"name": "Ada", "limit": 2}}
        )
        assert not result.is_error
        assert result.structured_content == {"matched": ["ADA"], "limit": 2}
        assert json.loads(result.content[0].text) == result.structured_content

        plain = await session.call_tool("status", {})
        assert plain.content[0].text == "Directory online"
        assert plain.structured_content is None

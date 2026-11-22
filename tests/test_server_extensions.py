import json
from pathlib import Path

import anyio
import pytest
from mcp import types

from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401

SUMMARY = "inventory://projects/summary"
ALPHA = "inventory://projects/alpha"


@pytest.mark.anyio
async def test_resources_and_tool_completion_over_stdio():
    updated = anyio.Event()

    async def receive(message):
        if isinstance(message, types.ResourceUpdatedNotification):
            assert str(message.params.uri) == SUMMARY
            updated.set()

    script = Path(__file__).with_name("resources_cli.py")
    async with mcp_server_client(script, message_handler=receive) as session:
        assert session.server_capabilities.resources is not None
        assert {tool.name for tool in (await session.list_tools()).tools} == {
            "projects_publish",
            "status",
        }
        [resource] = (await session.list_resources()).resources
        assert str(resource.uri) == SUMMARY
        [template] = (await session.list_resource_templates()).resource_templates
        assert template.uri_template == "inventory://projects/{project}"
        assert (
            json.loads((await session.read_resource(ALPHA)).contents[0].text) == "draft"
        )

        failed = await session.call_tool("projects_publish", {"project": "missing"})
        assert failed.is_error
        assert not updated.is_set()

        published = await session.call_tool("projects_publish", {"project": "alpha"})
        assert published.content[0].text == "Published"
        with anyio.fail_after(2):
            await updated.wait()
        assert (
            json.loads((await session.read_resource(ALPHA)).contents[0].text)
            == "published"
        )

        status = await session.call_tool("status", {})
        assert not status.is_error
        assert status.content[0].text == "Online"

        summary = json.loads((await session.read_resource(SUMMARY)).contents[0].text)
        assert summary["projects"] == {"alpha": "published"}
        audit = summary["audit"]
        assert [entry["tool"] for entry in audit] == [
            "projects_publish",
            "projects_publish",
            "status",
        ]
        assert [entry["failed"] for entry in audit] == [True, False, False]
        assert audit[0]["path"] == ["projects", "publish"]
        assert all(entry["has_request_id"] and entry["seconds"] >= 0 for entry in audit)


@pytest.mark.anyio
async def test_default_server_advertises_only_tools():
    script = Path(__file__).with_name("basic_cli.py")
    async with mcp_server_client(script) as session:
        assert session.server_capabilities.tools is not None
        assert session.server_capabilities.resources is None

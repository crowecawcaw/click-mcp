from pathlib import Path

import pytest

from tests.test_mcp_server import anyio_backend, mcp_server_client  # noqa: F401


@pytest.mark.anyio
async def test_execution_errors_keep_mcp_session_alive():
    async with mcp_server_client(Path(__file__).with_name("error_cli.py")) as session:
        invalid = await session.call_tool("select", {"mode": "invalid"})
        assert invalid.is_error
        assert "invalid" in invalid.content[0].text.lower()

        for kind, expected in {
            "expected": "exit code 1): The requested record is unavailable",
            "abort": "Command aborted (exit code 1)",
            "click-exit": "Command exited with code 7\nRerun after refreshing the cache",
            "system-exit": "Command exited with code 9",
            "unexpected": "Command failed unexpectedly",
        }.items():
            result = await session.call_tool("fail", {"kind": kind})
            assert result.is_error, kind
            message = result.content[0].text
            assert expected in message
            assert "private" not in message
            assert "Traceback" not in message

        for kind in ("success-exit", "return-int"):
            result = await session.call_tool("fail", {"kind": kind})
            assert not result.is_error
            assert result.content[0].text == "Finished"

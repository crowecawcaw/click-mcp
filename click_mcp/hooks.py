"""Extension callbacks for MCP servers and tool invocations."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server


@dataclass(frozen=True)
class ToolCompletion:
    """Outcome and timing for a tool invocation handled by click-mcp."""

    tool_name: str
    command_path: tuple[str, ...]
    context: ServerRequestContext
    is_error: bool
    duration_seconds: float


ConfigureServer = Callable[[Server[dict[str, Any]]], None]
ToolCompletionHook = Callable[[ToolCompletion], Awaitable[None]]

"""
Scanner for Click commands to convert them to MCP tools.
"""

import re
from dataclasses import dataclass
from typing import Any

import click
import mcp.types as types

from .decorator import get_mcp_metadata

_original_paths: dict[str, str] = {}


@dataclass
class ToolRoute:
    tool: types.Tool
    path: tuple[str, ...]
    commands: tuple[click.Command, ...]


def sanitize_tool_name(name: str) -> str:
    """
    Sanitize a tool name to conform to the regex pattern [a-zA-Z][a-zA-Z0-9_]*
    """
    sanitized = name.replace(".", "_")

    if sanitized and not re.match(r"^[a-zA-Z]", sanitized):
        sanitized = "tool_" + sanitized

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)

    return sanitized


def get_original_path(sanitized_name: str) -> str:
    """Get the original command path from a sanitized tool name."""
    return _original_paths.get(sanitized_name, sanitized_name)


def scan_click_command(
    command: click.Group, *, include_hidden: bool = False
) -> list[types.Tool]:
    """Scan a Click group and return the exposed MCP tools."""
    routes = scan_tool_routes(command, include_hidden=include_hidden)
    _original_paths.update(
        (name, ".".join(route.path)) for name, route in routes.items()
    )
    return [route.tool for route in routes.values()]


def scan_tool_routes(
    command: click.Group,
    include_all_commands: bool = True,
    *,
    include_hidden: bool = False,
) -> dict[str, ToolRoute]:
    """Build a tool table with the Click path and parameters for each tool."""
    routes: dict[str, ToolRoute] = {}
    root_has_params = any(param.name != "help" for param in command.params)

    def scan_group(
        group: click.Group,
        path: tuple[str, ...],
        tool_path: tuple[str, ...],
        commands: tuple[click.Command, ...],
        parent_ctx: click.Context | None = None,
    ) -> None:
        context_class = getattr(group, "context_class", click.Context)
        with context_class(group, parent=parent_ctx, info_name=group.name) as ctx:
            for name in group.list_commands(ctx):
                cmd = group.get_command(ctx, name)
                if not cmd or getattr(cmd, "_is_mcp_command", False):
                    continue

                if cmd.hidden and not include_hidden:
                    continue

                command_path = (*path, name)
                metadata = get_mcp_metadata(".".join(command_path))
                if not metadata:
                    metadata = get_mcp_metadata(name)
                if metadata.get("include") is False:
                    continue

                names = (*tool_path, metadata.get("name", name))
                command_chain = (*commands, cmd)
                if isinstance(cmd, click.Group):
                    scan_group(cmd, command_path, names, command_chain, ctx)
                    continue
                if not metadata.get("include", include_all_commands):
                    continue

                if root_has_params and not path:
                    names = (command.name or "root", *names)
                tool_name = sanitize_tool_name("_".join(names))
                if tool_name in routes:
                    previous = ".".join(routes[tool_name].path)
                    current = ".".join(command_path)
                    raise ValueError(
                        f"Commands {previous!r} and {current!r} both map to {tool_name!r}"
                    )
                tool = _create_tool(tool_name, cmd, command_chain, metadata)
                routes[tool_name] = ToolRoute(tool, command_path, command_chain)

    scan_group(command, (), (), (command,))
    return routes


def _create_tool(
    tool_name: str,
    cmd: click.Command,
    commands: tuple[click.Command, ...],
    metadata: dict[str, Any],
) -> types.Tool:
    properties: dict[str, dict[str, Any]] = {}
    required: set[str] = set()
    for command in commands:
        for param in command.params:
            if param.name and (schema := _get_parameter_info(param)) is not None:
                properties[param.name] = schema
                if param.required:
                    required.add(param.name)

    input_schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        input_schema["required"] = sorted(required)

    return types.Tool(
        name=tool_name,
        description=cmd.help or cmd.short_help or "",
        input_schema=input_schema,
        annotations=metadata.get("annotations"),
    )


def _get_parameter_info(param: click.Parameter) -> dict[str, Any] | None:
    """Extract parameter information from a Click parameter."""
    if getattr(param, "hidden", False) or not param.name:
        return None

    # Determine parameter type
    param_type = "string"  # Default type
    if isinstance(param.type, click.types.IntParamType):
        param_type = "integer"
    elif isinstance(param.type, click.types.FloatParamType):
        param_type = "number"
    elif isinstance(param.type, click.types.BoolParamType):
        param_type = "boolean"

    # Create parameter info (this represents the schema for a single property)
    # According to JSON Schema draft 2020-12, properties should have type directly
    param_data: dict[str, Any] = {
        "type": param_type,
    }

    # Add description if available
    help_text = getattr(param, "help", "")
    if help_text:
        param_data["description"] = help_text

    # Handle choices if present (for click.Choice type)
    if hasattr(param.type, "choices") and param.type.choices is not None:
        if isinstance(param.type.choices, (list, tuple)):
            param_data["enum"] = list(param.type.choices)

    # Add default if available and not callable
    # Filter out Click's Sentinel.UNSET and other non-JSON-serializable defaults
    default = getattr(param, "default", None)
    if default is not None and not callable(default):
        # Only include JSON-serializable defaults (str, int, float, bool, list, dict, None)
        if isinstance(default, (str, int, float, bool, list, dict, type(None))):
            param_data["default"] = default

    return param_data

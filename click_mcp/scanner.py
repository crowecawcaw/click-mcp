"""
Scanner for Click commands to convert them to MCP tools.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import click
import mcp.types as types

from .adapter import ToolAdapter
from .compat import (
    is_exposed_parameter,
    is_group,
    parameter_arity,
    parameter_value_schema,
)
from .decorator import CommandMetadata, get_mcp_metadata

_original_paths: dict[str, str] = {}


@dataclass
class ToolRoute:
    tool: types.Tool
    path: tuple[str, ...]
    commands: tuple[click.Command, ...]
    adapter: ToolAdapter | None = None


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
    strict_arguments: bool = False,
    command_metadata: CommandMetadata | None = None,
) -> dict[str, ToolRoute]:
    """Build a tool table with the Click path and parameters for each tool."""
    routes: dict[str, ToolRoute] = {}
    scoped_metadata = (
        {
            tuple(key.split(".")) if isinstance(key, str) else key: value
            for key, value in command_metadata.items()
        }
        if command_metadata is not None
        else None
    )
    root_has_params = any(
        param.name != "help" and is_exposed_parameter(param) for param in command.params
    )

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
                metadata: Mapping[str, Any]
                if scoped_metadata is None:
                    metadata = get_mcp_metadata(
                        ".".join(command_path)
                    ) or get_mcp_metadata(name)
                else:
                    metadata = scoped_metadata.get(command_path, {})
                if metadata.get("include") is False:
                    continue

                names = (*tool_path, metadata.get("name", name))
                command_chain = (*commands, cmd)
                if is_group(cmd):
                    scan_group(cmd, command_path, names, command_chain, ctx)  # type: ignore[arg-type]
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
                adapter = metadata.get("adapter")
                tool = _create_tool(
                    tool_name, cmd, command_chain, metadata, adapter, strict_arguments
                )
                routes[tool_name] = ToolRoute(
                    tool, command_path, command_chain, adapter
                )

    scan_group(command, (), (), (command,))
    return routes


def _create_tool(
    tool_name: str,
    cmd: click.Command,
    commands: tuple[click.Command, ...],
    metadata: Mapping[str, Any],
    adapter: ToolAdapter | None,
    strict_arguments: bool,
) -> types.Tool:
    properties: dict[str, dict[str, Any]] = {}
    required: set[str] = set()
    for command in commands:
        for param in command.params:
            if param.name and (schema := _get_parameter_info(param)) is not None:
                if param.name in properties:
                    raise ValueError(
                        f"Tool {tool_name!r} binds parameter {param.name!r} more than once"
                    )
                properties[param.name] = schema
                if param.required:
                    required.add(param.name)

    input_schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        input_schema["required"] = sorted(required)
    if strict_arguments:
        input_schema["additionalProperties"] = False

    return types.Tool(
        name=tool_name,
        description=cmd.help or cmd.short_help or "",
        input_schema=(
            adapter.input_schema
            if adapter is not None and adapter.input_schema is not None
            else input_schema
        ),
        annotations=metadata.get("annotations"),
    )


def _get_parameter_info(param: click.Parameter) -> dict[str, Any] | None:
    """Extract parameter information from a Click parameter."""
    if not is_exposed_parameter(param) or not param.name:
        return None

    nargs, multiple = parameter_arity(param)
    param_data = parameter_value_schema(param)
    if multiple:
        param_data = {"type": "array", "items": param_data}
    if param.required and (multiple or nargs == -1):
        param_data["minItems"] = 1
    if help_text := getattr(param, "help", None):
        param_data["description"] = help_text

    default = getattr(param, "default", None)
    if isinstance(default, Enum) and getattr(param, "type_descriptor", None):
        default = str(default.value)
    if isinstance(default, tuple) and (multiple or nargs != 1):
        default = list(default)
    if isinstance(default, (str, int, float, bool, list, dict)):
        param_data["default"] = default

    return param_data

"""
Scanner for Click commands to convert them to MCP tools.
"""

from typing import Any, Dict, List, Optional

import click
import mcp.types as types

from .decorator import get_mcp_metadata


def scan_click_command(command: click.Group, parent_path: str = "") -> List[types.Tool]:
    """
    Scan a Click command and convert it to MCP tools.

    Args:
        command: A Click command or group.
        parent_path: The parent path for nested commands.

    Returns:
        A list of MCP Tool objects.
    """
    tools: List[types.Tool] = []
    ctx = click.Context(command)
    command_info = command.to_info_dict(ctx)

    if not isinstance(command, click.Group):
        return tools

    for name, cmd_info in command_info.get("commands", {}).items():
        # Skip excluded commands
        metadata = get_mcp_metadata(name)
        if metadata.get("include") is False:
            continue

        # Determine command path
        custom_name = metadata.get("name", name)
        cmd_path = f"{parent_path}{custom_name}" if parent_path else custom_name

        if "commands" in cmd_info:
            # Handle subgroup
            cmd = command.get_command(ctx, name)
            if isinstance(cmd, click.Group):
                group_name = metadata.get("name", name)
                group_path = (
                    f"{parent_path}{group_name}." if parent_path else f"{group_name}."
                )
                tools.extend(scan_click_command(cmd, group_path))
        else:
            # Handle command
            tools.append(_convert_command_info_to_tool(cmd_info, cmd_path))

    return tools


def _convert_command_info_to_tool(
    command_info: Dict[str, Any], name: str
) -> types.Tool:
    """Convert a Click command info dict to an MCP tool."""
    description = command_info.get("help") or command_info.get("short_help") or ""

    parameters: Dict[str, Dict[str, Any]] = {}
    for param_info in command_info.get("params", []):
        param_name = param_info.get("name")
        if param_name:
            param_data = _get_parameter_info_from_dict(param_info)
            if param_data:
                parameters[param_name] = param_data

    return types.Tool(
        name=name,
        description=description,
        inputSchema=parameters,
    )


def _get_parameter_info_from_dict(
    param_info: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Extract parameter information from a Click parameter info dict."""
    if param_info.get("hidden", False) or not param_info.get("name"):
        return None

    # Determine parameter type
    param_type = "string"  # Default type
    type_info = param_info.get("type", {})
    if isinstance(type_info, dict):
        type_name = type_info.get("name")
        if type_name in {"integer", "float", "boolean"}:
            param_type = (
                "integer"
                if type_name == "integer"
                else "number" if type_name == "float" else "boolean"
            )

    # Create schema object
    schema = {"type": param_type}
    if "choices" in param_info:
        schema["enum"] = param_info["choices"]

    # Create parameter info
    param_data = {
        "description": param_info.get("help", ""),
        "required": param_info.get("required", False),
        "schema": schema,
    }

    # Add default if available and not callable
    default = param_info.get("default")
    if default is not None and not callable(default):
        param_data["default"] = default

    return param_data

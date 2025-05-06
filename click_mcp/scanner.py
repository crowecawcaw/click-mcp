"""
Scanner for Click commands to convert them to MCP tools.
"""

from typing import Any, Dict, List, Optional

import click
import mcp.types as types

from .decorator import get_mcp_metadata

# Dictionary to store positional arguments for each tool
_tool_positional_args: Dict[str, List[str]] = {}

# Dictionary to store mapping between sanitized tool names and original paths
_original_paths: Dict[str, str] = {}


def sanitize_tool_name(name: str) -> str:
    """
    Sanitize a tool name to conform to the regex pattern [a-zA-Z][a-zA-Z0-9_]*
    """
    import re

    sanitized = name.replace(".", "_")

    if sanitized and not re.match(r"^[a-zA-Z]", sanitized):
        sanitized = "tool_" + sanitized

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)

    return sanitized


def get_original_path(sanitized_name: str) -> str:
    """Get the original command path from a sanitized tool name."""
    return _original_paths.get(sanitized_name, sanitized_name)


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
                # Use underscore for path separator in sanitized paths
                group_path = (
                    f"{parent_path}{group_name}." if parent_path else f"{group_name}."
                )
                tools.extend(scan_click_command(cmd, group_path))
        else:
            # Handle command
            cmd = command.get_command(ctx, name)
            if cmd is not None:
                # Sanitize the command path to conform to the regex pattern
                sanitized_cmd_path = sanitize_tool_name(cmd_path)
                # Store the mapping between sanitized name and original path
                _original_paths[sanitized_cmd_path] = cmd_path

                tool, positional_args = _convert_command_to_tool(
                    cmd, cmd_info, sanitized_cmd_path
                )
                tools.append(tool)
                # Store positional arguments in the global dictionary
                if positional_args:
                    _tool_positional_args[tool.name] = positional_args

    return tools


def get_positional_args(tool_name: str) -> List[str]:
    return _tool_positional_args.get(tool_name, [])


def _convert_command_to_tool(
    command: click.Command, command_info: Dict[str, Any], name: str
) -> tuple[types.Tool, List[str]]:
    """
    Convert a Click command to an MCP tool.

    Returns:
        A tuple of (Tool, positional_args_list)
    """
    description = command_info.get("help") or command_info.get("short_help") or ""

    properties: Dict[str, Dict[str, Any]] = {}
    required_params: List[str] = []
    positional_order: List[str] = []

    # Process parameters
    for param in command.params:
        param_name = param.name
        if param_name:
            # Check if this is a positional argument (not an option)
            is_positional = isinstance(param, click.Argument)

            param_data = _get_parameter_info(param)
            if param_data:
                properties[param_name] = param_data
                if param_data.get("required", False):
                    required_params.append(param_name)

                # Track positional arguments in order
                if is_positional:
                    positional_order.append(param_name)

    # Construct the final input schema according to JSON Schema / MCP spec
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required_params:
        input_schema["required"] = sorted(required_params)  # Sort for consistent output

    tool = types.Tool(
        name=name,
        description=description,
        inputSchema=input_schema,
    )

    return tool, positional_order


def _get_parameter_info(param: click.Parameter) -> Optional[Dict[str, Any]]:
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

    # Create schema object
    schema: Dict[str, Any] = {"type": param_type}

    # Handle choices if present
    if hasattr(param, "choices") and param.choices is not None:
        if isinstance(param.choices, (list, tuple)):
            schema["enum"] = list(param.choices)

    # Create parameter info (this represents the schema for a single property)
    param_data = {
        "description": getattr(param, "help", ""),
        "schema": schema,
    }

    # Add 'required' flag separately for collecting at the top level
    is_required = getattr(param, "required", False)
    if is_required:
        param_data["required"] = True  # Keep track for the loop above

    # Add default if available and not callable
    default = getattr(param, "default", None)
    if default is not None and not callable(default):
        param_data["default"] = default

    return param_data

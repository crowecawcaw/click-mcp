"""
Scanner for converting Click commands to MCP tools.
"""

from typing import Dict, Any, List, Optional

import click

from .decorator import get_mcp_metadata


def scan_click_command(command, parent_path: str = "") -> List[Dict[str, Any]]:
    """
    Scan a Click command or group and convert it to MCP tools.

    Args:
        command: A Click command or group.
        parent_path: Path of parent commands (for nested commands).

    Returns:
        A list of MCP tool definitions.
    """
    tools = []

    if isinstance(command, click.Group):
        group_metadata = get_mcp_metadata(command.name)
        include_all_commands = group_metadata.get("include_all_commands", True)

        for name, cmd in command.commands.items():  # pylint: disable=too-many-branches
            # Skip MCP commands
            if name == "mcp" or name.endswith("-mcp") or name == "start-mcp":
                continue

            # Build command path
            if parent_path:
                cmd_path = f"{parent_path}.{name}"
            else:
                cmd_path = name

            # Check if command should be included
            should_include = _should_include_command(cmd, include_all_commands)
            if not should_include:
                continue

            # Get custom name if specified
            custom_name = _get_custom_command_name(cmd)
            if custom_name:
                if parent_path:
                    tool_name = f"{parent_path}.{custom_name}"
                else:
                    tool_name = custom_name
            else:
                tool_name = cmd_path

            # Handle nested groups
            if isinstance(cmd, click.Group):
                # Add the group itself as a tool if it has a custom name
                if custom_name:
                    group_tool = _create_tool_from_command(cmd, tool_name)
                    tools.append(group_tool)

                    # Set new parent path for nested commands
                    if parent_path:
                        new_parent_path = f"{parent_path}.{custom_name}"
                    else:
                        new_parent_path = custom_name
                else:
                    new_parent_path = cmd_path

                # Add nested commands
                tools.extend(scan_click_command(cmd, new_parent_path))
            else:
                # Create tool for command
                tool = _create_tool_from_command(cmd, tool_name)
                tools.append(tool)

    return tools


def _should_include_command(command, default_include: bool) -> bool:
    """Determine if a command should be included in MCP tools."""
    cmd_metadata = get_mcp_metadata(command.name)

    # If command has explicit include/exclude setting, use that
    if "include" in cmd_metadata:
        return cmd_metadata["include"]

    # For Click commands with callback, check if the callback has metadata
    if hasattr(command, "callback") and hasattr(command.callback, "_mcp_metadata"):
        # pylint: disable=protected-access
        metadata = command.callback._mcp_metadata
        if "include" in metadata:
            return metadata["include"]

    # Otherwise use the default from the parent group
    return default_include


def _get_custom_command_name(command) -> Optional[str]:
    """Get custom name for a command if specified."""
    # First check command metadata
    cmd_metadata = get_mcp_metadata(command.name)
    if "name" in cmd_metadata:
        return cmd_metadata["name"]

    # Then check callback metadata
    if hasattr(command, "callback") and hasattr(command.callback, "_mcp_metadata"):
        # pylint: disable=protected-access
        metadata = command.callback._mcp_metadata
        if "name" in metadata:
            return metadata["name"]

    return None


def _create_tool_from_command(command, name: str) -> Dict[str, Any]:
    """Create an MCP tool definition from a Click command."""
    description = command.help

    if not description:
        description = f"Execute the {name} command"

    tool = {
        "name": name,
        "description": description,
        "parameters": _get_parameters_from_command(command),
    }

    return tool


def _get_parameters_from_command(command) -> Dict[str, Any]:
    """Extract parameters from a Click command."""
    parameters = {}

    for param in command.params:
        # Skip hidden MCP parameters
        if param.name == "_mcp_register" and param.hidden:
            continue

        # Get parameter description
        if hasattr(param, "help"):
            description = param.help or f"Parameter {param.name}"
        else:
            description = f"Parameter {param.name}"

        param_def = {
            "type": _get_param_type(param),
            "description": description,
        }

        # Add required flag
        if param.required:
            param_def["required"] = True

        # Add default value if present
        if param.default is not None and param.default != ():
            param_def["default"] = param.default

        # Add enum values for choices
        if (
            hasattr(param, "type")
            and hasattr(param.type, "choices")
            and param.type.choices
        ):
            param_def["enum"] = list(param.type.choices)

        parameters[param.name] = param_def

    return parameters


def _get_param_type(param) -> str:
    """Determine the MCP parameter type from a Click parameter."""
    if hasattr(param, "is_flag") and param.is_flag:
        return "boolean"
    if hasattr(param, "type"):
        if param.type.name == "integer":
            return "integer"
        if param.type.name == "float":
            return "number"
        if param.type.name == "boolean":
            return "boolean"

    return "string"

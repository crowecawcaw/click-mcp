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

# Dictionary to store parent command information for hierarchical tools
_parent_commands: Dict[str, click.Command] = {}

# Dictionary to store child command names for hierarchical tools
_child_command_names: Dict[str, str] = {}

# Dictionary to store command path components for robust execution
_command_path_components: Dict[str, List[str]] = {}

# Dictionary to store child command references for hierarchical tools
_child_commands: Dict[str, click.Command] = {}


def get_parent_command(tool_name: str) -> Optional[click.Command]:
    """Get the parent command for a hierarchical tool."""
    return _parent_commands.get(tool_name)


def get_child_command_name(tool_name: str) -> Optional[str]:
    """Get the child command name for a hierarchical tool."""
    return _child_command_names.get(tool_name)


def get_command_path_components(tool_name: str) -> List[str]:
    """Get the command path components for execution (e.g., ['users', 'list'])."""
    return _command_path_components.get(tool_name, [tool_name])


def get_child_command(tool_name: str) -> Optional[click.Command]:
    """Get the child command reference for a hierarchical tool."""
    return _child_commands.get(tool_name)


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


def scan_click_command(
    command: click.Group, 
    path_segments: Optional[List[str]] = None,
    parent_command: Optional[click.Command] = None
) -> List[types.Tool]:
    """
    Scan a Click command and convert it to MCP tools.

    Args:
        command: A Click command or group.
        path_segments: List of path segments (e.g., ['users', 'list']).
        parent_command: The parent command for hierarchical tools.

    Returns:
        A list of MCP Tool objects.
    """
    if path_segments is None:
        path_segments = []

    tools = []
    ctx = click.Context(command)

    for name, cmd_info in command.to_info_dict(ctx).get("commands", {}).items():
        cmd = command.get_command(ctx, name)
        if not cmd:
            continue
            
        if _should_skip_command(name, cmd):
            continue

        # Get custom name from metadata
        metadata = get_mcp_metadata(name)
        custom_name = metadata.get("name", name)

        current_path = path_segments + [custom_name]

        should_create_hierarchical = _should_create_hierarchical_tools(command, path_segments)
        tools.extend(_create_tools_for_command(
            command, cmd, cmd_info, custom_name, 
            should_create_hierarchical, current_path, parent_command
        ))

    return tools


def _should_create_hierarchical_tools(command: click.Group, path_segments: List[str]) -> bool:
    is_root_group = len(path_segments) == 0
    has_meaningful_params = any(param.name != "help" for param in command.params)
    # Both conditions must be true: root level AND has meaningful parameters
    return is_root_group and has_meaningful_params


def _should_skip_command(name: str, cmd: Optional[click.Command] = None) -> bool:
    metadata = get_mcp_metadata(name)
    if metadata.get("include") is False:
        return True
    
    # Skip MCP commands using attribute check
    if cmd and getattr(cmd, '_is_mcp_command', False):
        return True
        
    return False



def _create_tools_for_command(
    parent_cmd: click.Group,
    cmd: click.Command,
    cmd_info: Dict[str, Any],
    name: str,
    should_create_hierarchical: bool,
    current_path: List[str],
    parent_command: Optional[click.Command] = None
) -> List[types.Tool]:
    
    if "commands" in cmd_info:
        return scan_click_command(cmd, current_path, parent_cmd)
    
    elif should_create_hierarchical and len(current_path) == 1:
        tool_name = sanitize_tool_name("_".join([parent_cmd.name or "root"] + current_path))
        original_path = current_path[0]
        return [_create_tool(cmd, cmd_info, tool_name, original_path, parent_cmd, [original_path])]
    
    else:
        tool_name = sanitize_tool_name("_".join(current_path))
        original_path = ".".join(current_path)
        return [_create_tool(cmd, cmd_info, tool_name, original_path, None, current_path)]


def _create_tool(
    cmd: click.Command, 
    cmd_info: Dict[str, Any], 
    tool_name: str, 
    original_path: str = None,
    parent_cmd: Optional[click.Group] = None,
    path_components: Optional[List[str]] = None
) -> types.Tool:
    if original_path is None:
        original_path = tool_name
    
    _original_paths[tool_name] = original_path
    
    if path_components:
        _command_path_components[tool_name] = path_components
    else:
        # For hierarchical tools, path components are just the child command
        # For simple tools, it's just the tool name
        _command_path_components[tool_name] = [original_path]
    
    # Store parent command if this is a hierarchical tool
    if parent_cmd is not None:
        _parent_commands[tool_name] = parent_cmd
        # For hierarchical tools, the original_path is the child command name
        _child_command_names[tool_name] = original_path
        # Store the actual child command reference for robust lookup
        _child_commands[tool_name] = cmd
    
    # Build the tool description
    description = cmd_info.get("help") or cmd_info.get("short_help") or ""

    properties: Dict[str, Dict[str, Any]] = {}
    required_params: List[str] = []
    positional_order: List[str] = []

    # First, add parent parameters if this is a hierarchical tool
    if parent_cmd:
        for param in parent_cmd.params:
            param_name = param.name
            if param_name:
                param_data = _get_parameter_info(param)
                if param_data:
                    properties[param_name] = param_data
                    if param_data.get("required", False):
                        required_params.append(param_name)

    # Then, add command parameters
    for param in cmd.params:
        param_name = param.name
        if param_name:
            # Check if this is a positional argument (not an option)
            is_positional = isinstance(param, click.Argument)

            param_data = _get_parameter_info(param)
            if param_data:
                properties[param_name] = param_data
                if param_data.get("required", False):
                    required_params.append(param_name)

                # Track positional arguments in order (only from the main command)
                if is_positional:
                    positional_order.append(param_name)

    # Construct the final input schema according to JSON Schema / MCP spec
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required_params:
        input_schema["required"] = sorted(required_params)  # Sort for consistent output

    # Create the tool
    tool = types.Tool(
        name=tool_name,
        description=description,
        inputSchema=input_schema,
    )
    
    # Store positional argument order if any
    if positional_order:
        _tool_positional_args[tool.name] = positional_order
    
    return tool


def get_positional_args(tool_name: str) -> List[str]:
    return _tool_positional_args.get(tool_name, [])


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

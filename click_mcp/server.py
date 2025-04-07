"""
MCP server implementation for Click applications.
"""

import json
import sys
import io
import contextlib
from typing import Dict, Any

from .scanner import scan_click_command
from .decorator import get_mcp_metadata


class MCPServer:  # pylint: disable=too-few-public-methods
    """MCP server for Click applications."""

    def __init__(self, cli_group):
        """
        Initialize the MCP server.

        Args:
            cli_group: A Click group to expose as MCP tools.
        """
        self.cli_group = cli_group
        self.tools = scan_click_command(cli_group)
        self.tool_map = {tool["name"]: tool for tool in self.tools}

    def run(self):
        """Run the MCP server with stdio transport."""
        self._send_response(
            {"type": "server_info", "version": "1.0", "tools": self.tools}
        )

        for line in sys.stdin:
            try:
                request = json.loads(line)

                if request["type"] == "invoke":
                    self._handle_invoke(request)
                else:
                    self._send_error(f"Unknown request type: {request['type']}")
            except json.JSONDecodeError:
                self._send_error("Invalid JSON request")
            except Exception as e:  # pylint: disable=broad-except
                self._send_error(f"Error processing request: {str(e)}")

    def _handle_invoke(self, request):
        try:
            tool_name = request["tool"]
            parameters = request.get("parameters", {})

            if tool_name not in self.tool_map:
                self._send_error(f"Unknown tool: {tool_name}")
                return

            result = self._execute_command(tool_name, parameters)

            self._send_response(
                {"type": "invoke_response", "id": request.get("id"), "result": result}
            )
        except Exception as e:  # pylint: disable=broad-except
            self._send_error(f"Error invoking tool {request.get('tool')}: {str(e)}")

    def _execute_command(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        # pylint: disable=too-many-locals,too-many-branches
        # Parse the tool name to get the command path
        command_path = tool_name.split(".")

        # Find the command in the CLI group
        command = self._find_command(self.cli_group, command_path)

        # Build command arguments
        args = []
        positional_args = []

        # Separate options and arguments
        option_names = set()
        argument_names = set()

        for param in command.params:
            if hasattr(param, "opts"):  # It's an option
                option_names.add(param.name)
            else:  # It's an argument
                argument_names.add(param.name)

        # Process options
        for param_name, param_value in parameters.items():
            if param_name in option_names:
                param = next(p for p in command.params if p.name == param_name)

                # Handle boolean flags
                if hasattr(param, "is_flag") and param.is_flag:
                    if param_value:
                        args.append(f"--{param_name}")
                # Handle regular options
                else:
                    args.append(f"--{param_name}")
                    args.append(str(param_value))
            elif param_name in argument_names:
                # Store arguments separately to add them in the correct order
                positional_args.append((param_name, param_value))

        # Add positional arguments in the correct order
        for param in command.params:
            if param.name in argument_names:
                for arg_name, arg_value in positional_args:
                    if arg_name == param.name:
                        args.append(str(arg_value))

        # Capture the command output
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                # Create a new context and invoke the command
                ctx = command.make_context(command.name, args)
                command.invoke(ctx)
            except Exception as e:  # pylint: disable=broad-except
                raise ValueError(f"Command execution failed: {str(e)}") from e

        # Return the captured output
        return {"output": output.getvalue().rstrip()}

    def _find_command(self, group, path):
        """Find a command in a group by path."""
        if not path:
            return group

        current = path[0]
        remaining = path[1:]

        # Try to find the command by name
        if current in group.commands:
            cmd = group.commands[current]
        else:
            # Try to find a command with a custom name
            cmd = None
            for cmd_name, command in group.commands.items():
                # Check command metadata
                metadata = get_mcp_metadata(cmd_name)
                if metadata.get("name") == current:
                    cmd = command
                    break

                # Check callback metadata
                if hasattr(command, "callback") and hasattr(
                    command.callback, "_mcp_metadata"
                ):
                    # pylint: disable=protected-access
                    callback_metadata = command.callback._mcp_metadata
                    if callback_metadata.get("name") == current:
                        cmd = command
                        break

            if cmd is None:
                raise ValueError(f"Command not found: {current}")

        # If there are more path segments, the command must be a group
        if remaining and not hasattr(cmd, "commands"):
            raise ValueError(f"'{current}' is not a command group")

        # If this is the last segment, return the command
        if not remaining:
            return cmd

        # Otherwise, continue searching in the subgroup
        return self._find_command(cmd, remaining)

    def _send_response(self, response: Dict[str, Any]):
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _send_error(self, message: str):
        self._send_response({"type": "error", "message": message})

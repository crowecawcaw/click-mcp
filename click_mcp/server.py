"""
MCP server implementation for Click applications using the MCP library.
"""

import asyncio
import contextlib
import io
from typing import Any, Dict, List, Optional

import click
import mcp.types as types
from mcp.server import stdio
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server

from . import __version__
from .scanner import scan_tool_routes


class MCPServer:
    """MCP server for Click applications."""

    def __init__(
        self,
        cli_group: click.Group,
        server_name: str = "click-mcp",
        include_all_commands: bool = True,
    ):
        """
        Initialize the MCP server.

        Args:
            cli_group: A Click group to expose as MCP tools.
            server_name: The name of the MCP server.
            include_all_commands: Expose commands by default.
        """
        self.cli_group = cli_group
        self.server_name = server_name
        self.routes = scan_tool_routes(cli_group, include_all_commands)
        self.click_tools = [route.tool for route in self.routes.values()]
        self.tool_map = {tool.name: tool for tool in self.click_tools}
        self.server: Server[dict[str, Any]] = Server(
            server_name,
            version=__version__,
            on_list_tools=self._handle_list_tools,
            on_call_tool=self._handle_call_tool,
            get_tool_input_schema=self._get_tool_input_schema,
        )

    def _get_tool_input_schema(self, name: str) -> dict[str, Any] | None:
        tool = self.tool_map.get(name)
        return tool.input_schema if tool else None

    def run(self) -> None:
        """Run the MCP server with stdio transport."""
        asyncio.run(self._run_server())

    async def _run_server(self) -> None:
        """Run the MCP server asynchronously."""
        async with stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def _handle_list_tools(
        self, _ctx: ServerRequestContext, _params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=self.click_tools)

    async def _handle_call_tool(
        self, _ctx: ServerRequestContext, params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        try:
            if params.name not in self.tool_map:
                raise ValueError(f"Unknown tool: {params.name}")
            result = self._execute_command(params.name, params.arguments or {})
        except ValueError as exc:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(exc))],
                is_error=True,
            )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result["output"])]
        )

    def _execute_command(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        command_args = self._prepare_command_arguments(tool_name, parameters)
        return self._run_click_command(command_args)

    def _prepare_command_arguments(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> list[str]:
        route = self.routes[tool_name]
        args = []
        for index, command in enumerate(route.commands):
            if index:
                args.append(route.path[index - 1])
            positionals = [
                param.name
                for param in command.params
                if isinstance(param, click.Argument) and param.name is not None
            ]
            args.extend(
                self._convert_parameters_to_args(
                    parameters, positionals, command.params
                )
            )
        return args

    def _run_click_command(self, args: List[str]) -> Dict[str, Any]:
        """Execute the Click command with prepared arguments."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                # Use Click's main() method which handles parent-child execution naturally
                self.cli_group.main(args=args, standalone_mode=False)
            except Exception as e:
                raise ValueError(f"Command execution failed: {str(e)}") from e

        return {"output": output.getvalue().rstrip()}

    def _convert_parameters_to_args(
        self,
        parameters: Dict[str, Any],
        positional_order: List[str],
        param_definitions: Optional[List[click.Parameter]] = None,
    ) -> List[str]:
        """Convert parameters to CLI arguments."""
        args = []

        # Add positional arguments in order
        for param_name in positional_order:
            if param_name in parameters:
                args.append(str(parameters[param_name]))

        if param_definitions is None:
            for name, value in parameters.items():
                if name not in positional_order:
                    self._add_option_arg(
                        args, name, value, is_bool=isinstance(value, bool)
                    )
            return args

        options: list[str] = []
        for param in param_definitions:
            if (
                not isinstance(param, click.Option)
                or param.hidden
                or param.name not in parameters
            ):
                continue
            value = parameters[param.name]
            option = next(
                (opt for opt in param.opts if opt.startswith("--")), param.opts[0]
            )
            if param.is_bool_flag:
                if value:
                    options.append(option)
                elif param.secondary_opts:
                    options.append(param.secondary_opts[0])
            elif param.is_flag:
                if value == param.flag_value:
                    options.append(option)
            elif option.startswith("--"):
                options.append(f"{option}={value}")
            else:
                options.extend([option, str(value)])

        if any(arg.startswith("-") for arg in args):
            return [*options, "--", *args]
        return [*args, *options]

    def _add_option_arg(
        self, args: List[str], param_name: str, value: Any, is_bool: bool
    ) -> None:
        """Add an option argument to the args list."""
        if is_bool:
            if value:
                args.append(f"--{param_name.replace('_', '-')}")
        else:
            args.extend([f"--{param_name.replace('_', '-')}", str(value)])

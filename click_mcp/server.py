"""
MCP server implementation for Click applications using the MCP library.
"""

import asyncio
import contextlib
import io
import json
from typing import Any, Dict, List, Optional

import click
import mcp.types as types
from jsonschema import SchemaError, ValidationError, validate
from mcp.server import stdio
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server

from . import __version__
from .compat import invoke_command, is_exposed_parameter
from .scanner import ToolRoute, scan_tool_routes


class _ToolExecutionError(ValueError):
    """An execution failure whose message is safe to send to the MCP client."""


class MCPServer:
    """MCP server for Click applications."""

    def __init__(
        self,
        cli_group: click.Group,
        server_name: str = "click-mcp",
        include_all_commands: bool = True,
        *,
        include_hidden: bool = False,
    ):
        """
        Initialize the MCP server.

        Args:
            cli_group: A Click group to expose as MCP tools.
            server_name: The name of the MCP server.
            include_all_commands: Expose commands by default.
            include_hidden: Whether hidden commands and groups can be exposed.
        """
        self.cli_group = cli_group
        self.server_name = server_name
        self.routes = scan_tool_routes(
            cli_group, include_all_commands, include_hidden=include_hidden
        )
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
            route = self.routes.get(params.name)
            if route is None:
                raise _ToolExecutionError(f"Unknown tool: {params.name}")
            return self._call_route(route, params.arguments or {})
        except _ToolExecutionError as exc:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(exc))],
                is_error=True,
            )

    def _call_route(
        self, route: ToolRoute, arguments: dict[str, Any]
    ) -> types.CallToolResult:
        adapter = route.adapter
        if adapter is not None and adapter.input_schema is not None:
            try:
                validate(arguments, route.tool.input_schema)
            except ValidationError as exc:
                raise _ToolExecutionError(
                    f"Invalid tool arguments at {exc.json_path}: failed {exc.validator} validation"
                ) from exc
            except SchemaError as exc:
                raise _ToolExecutionError("Invalid tool input schema") from exc
        if adapter is not None and adapter.adapt_arguments is not None:
            try:
                arguments = adapter.adapt_arguments(arguments)
                if not isinstance(arguments, dict):
                    raise TypeError("Expected a dictionary of CLI parameter values")
            except Exception as exc:
                raise _ToolExecutionError(
                    "Could not adapt tool arguments for CLI invocation"
                ) from exc

        result = self._execute_command(route.tool.name, arguments)
        text = result["output"]
        structured_content = None
        if adapter is not None and adapter.adapt_result is not None:
            try:
                adapted = adapter.adapt_result(result["return_value"])
                if not isinstance(adapted, dict):
                    raise TypeError("Expected a JSON object")
                text = json.dumps(adapted, allow_nan=False)
                structured_content = json.loads(text)
            except Exception as exc:
                raise _ToolExecutionError(
                    "Could not serialize the tool result as a JSON object"
                ) from exc

        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structured_content=structured_content,
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
                if param.param_type_name == "argument"
                and param.name is not None
                and is_exposed_parameter(param)
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
        errors = io.StringIO()
        return_value = None
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                # Invoke Click directly so an Exit remains distinguishable from
                # an integer callback return value.
                return_value = invoke_command(self.cli_group, args)
        except click.UsageError as exc:
            raise _ToolExecutionError(
                f"Invalid command arguments (exit code {exc.exit_code}): {exc.format_message()}"
            ) from exc
        except click.ClickException as exc:
            raise _ToolExecutionError(
                self._with_stderr(
                    f"Command failed (exit code {exc.exit_code}): {exc.format_message()}",
                    errors,
                )
            ) from exc
        except (click.Abort, EOFError, KeyboardInterrupt) as exc:
            raise _ToolExecutionError(
                self._with_stderr("Command aborted (exit code 1)", errors)
            ) from exc
        except (click.exceptions.Exit, SystemExit) as exc:
            code = exc.exit_code if isinstance(exc, click.exceptions.Exit) else exc.code
            if code is not None and code != 0:
                if isinstance(code, int):
                    status = f"Command exited with code {code}"
                else:
                    status = "Command exited with code 1"
                raise _ToolExecutionError(self._with_stderr(status, errors)) from exc
        except Exception as exc:
            raise _ToolExecutionError("Command failed unexpectedly") from exc

        return {"output": output.getvalue().rstrip(), "return_value": return_value}

    @staticmethod
    def _with_stderr(message: str, errors: io.StringIO) -> str:
        stderr = errors.getvalue().strip()
        return f"{message}\n{stderr}" if stderr else message

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
                param.param_type_name != "option"
                or not is_exposed_parameter(param)
                or param.name not in parameters
            ):
                continue
            value = parameters[param.name]
            option_param: Any = param
            option = next(
                (opt for opt in param.opts if opt.startswith("--")), param.opts[0]
            )
            if option_param.is_bool_flag:
                if value:
                    options.append(option)
                elif param.secondary_opts:
                    options.append(param.secondary_opts[0])
            elif option_param.is_flag:
                if value == option_param.flag_value:
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

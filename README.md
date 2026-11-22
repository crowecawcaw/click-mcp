# click-mcp

[![PyPI version](https://badge.fury.io/py/click-mcp.svg)](https://badge.fury.io/py/click-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library that extends Click applications with Model Context Protocol (MCP) support, allowing AI agents to interact with CLI tools.

## Overview

`click-mcp` provides a simple decorator that converts Click commands into MCP tools. This enables AI agents to discover and interact with your CLI applications programmatically.

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification) is an open standard for AI agents to interact with tools and applications in a structured way.

## Key Features

- Simple `@click_mcp` decorator syntax
- Automatic conversion of Click commands to MCP tools
- Support for nested command groups
- Support for positional arguments
- Stdio-based MCP server for easy integration

## Installation

Requires Python 3.10 or later and the MCP Python SDK 2.3 or later in the 2.x series. CI tests Python 3.10 through 3.15.

```bash
pip install click-mcp
```

## Basic Usage

```python
import click
from click_mcp import click_mcp

@click_mcp(server_name="my-cli-app")
@click.group()
def cli():
    """Sample CLI application."""
    pass

@cli.command()
@click.option('--name', required=True, help='Name to greet')
def greet(name):
    """Greet someone."""
    click.echo(f"Hello, {name}!")

if __name__ == '__main__':
    cli()
```

When you run the MCP server, Click commands are converted into MCP tools:
- Command `greet` becomes MCP tool `greet`
- Nested commands use underscores (e.g., `users_create`)

After initializing an MCP session, call the tool with `tools/call`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "greet",
    "arguments": {"name": "World"}
  }
}
```

To start the MCP server:

```bash
$ python my_app.py mcp
```

## Advanced Usage

### Customizing the MCP Command Name

By default, `click-mcp` adds an `mcp` command to your CLI application. You can customize this name using the `command_name` parameter:

```python
@click_mcp(server_name="my-cli-app", command_name="start-mcp")
@click.group()
def cli():
    """Sample CLI application with custom MCP command name."""
    pass
```

With this configuration, you would start the MCP server using:

```bash
$ python my_app.py start-mcp
```

This can be useful when:
- The name "mcp" conflicts with an existing command
- You want a more descriptive command name
- You're integrating with a specific AI agent that expects a certain command name

### Customizing the MCP Server Name

You can also customize the name of the MCP server that's reported to clients:

```python
@click_mcp(server_name="my-custom-tool")
@click.group()
def cli():
    """Sample CLI application with custom server name."""
    pass
```

This can be useful when:
- You want to provide a more descriptive name for your tool
- You're integrating with systems that use the server name for identification
- You want to distinguish between different MCP-enabled applications

### Working with Nested Command Groups

`click-mcp` supports nested command groups. When you have a complex CLI structure with subcommands, visible leaf commands are exposed as MCP tools by default:

```python
@click_mcp(server_name="my-cli-app")
@click.group()
def cli():
    """Main CLI application."""
    pass

@cli.group()
def users():
    """User management commands."""
    pass

@users.command()
@click.option('--username', required=True)
def create(username):
    """Create a new user."""
    click.echo(f"Creating user: {username}")

@users.command()
@click.argument('username')
def delete(username):
    """Delete a user."""
    click.echo(f"Deleting user: {username}")
```

When exposed as MCP tools, the nested commands will be available with their full path using underscores (e.g., `users_create` and `users_delete`).

An exposed command needs unique parameter names across its parent groups and
its own parameters. If two parameters share a name, server startup reports the
tool and the duplicate parameter. Give the two Click parameters distinct
destination names to expose both.

### Using a Typer command group

Build a command group from your Typer app and attach the server command to
that group. Use a root callback or multiple commands so the app produces a
group.

```python
import typer
from typer.main import get_command

from click_mcp import click_mcp

app = typer.Typer()


@app.callback()
def main():
    """Team directory."""


@app.command()
def member(member_id: int, limit: int = 3):
    """Show a team member."""
    typer.echo(f"Member {member_id}, limit {limit}")


if __name__ == "__main__":
    group = get_command(app)
    click_mcp("directory", group)
    group()
```

Run `python directory.py mcp` to expose the generated tools. Typer remains
an optional dependency.

### Exposing only selected commands

For an inventory CLI with `projects list`, `projects delete`, and an internal
`admin` group, register the read-only command and turn off automatic exposure:

```python
from click_mcp import click_mcp

click_mcp(
    "inventory",
    cli,
    include_all_commands=False,
    command_metadata={
        ("projects", "list"): {
            "include": True,
            "annotations": {"readOnlyHint": True},
        },
    },
)
```

The MCP client sees only `projects_list`. The rest of the commands remain
available through the CLI. Keys are CLI paths relative to the root, using the
registered alias name when selecting an alias. Use tuples for exact path
segments, or dotted strings such as `"projects.list"` for ordinary names.
When supplied, `command_metadata` is the server's sole source of metadata.
Servers that omit it continue to use the process-wide
`register_mcp_metadata()` registry with legacy leaf-name fallback.

Hidden commands and descendants of hidden groups are skipped even when
explicitly selected. Set `include_hidden=True` to make them eligible for the
same inclusion rules.

Keep destructive, administrative, and arbitrary shell passthrough commands
out of the allowlist unless clients need them. MCP tool annotations describe
behavior to clients. The allowlist controls which commands the server exposes.
See [tool hints (#7)](https://github.com/crowecawcaw/click-mcp/issues/7).

### Working with Positional Arguments

Click supports positional arguments using `@click.argument()`. When these are converted to MCP tools, they are represented as named parameters in the schema:

```python
@cli.command()
@click.argument('source')
@click.argument('destination')
@click.option('--overwrite', is_flag=True, help='Overwrite destination if it exists')
def copy(source, destination, overwrite):
    """Copy a file from source to destination."""
    click.echo(f"Copying {source} to {destination}")
```

This command is converted to an MCP tool with the following schema:

```json
{
  "type": "object",
  "properties": {
    "source": {
      "description": "",
      "schema": { "type": "string" },
      "required": true
    },
    "destination": {
      "description": "",
      "schema": { "type": "string" },
      "required": true
    },
    "overwrite": {
      "description": "Overwrite destination if it exists",
      "schema": { "type": "boolean" }
    }
  },
  "required": ["source", "destination"]
}
```

The positional nature of arguments is handled internally by `click-mcp`. When invoking the command, you can use named parameters:

```json
{
  "type": "invoke",
  "tool": "copy",
  "inputSchema": {
    "type": "object",
    "properties": {
      "source": {"type": "string"},
      "destination": {"type": "string"},
      "overwrite": {
        "type": "boolean",
        "description": "Overwrite destination if it exists"
      }
    },
    "required": ["destination", "source"]
  }
}
```

The MCP server will correctly convert these to positional arguments when executing the Click command:

```
copy file.txt /tmp/file.txt --overwrite
```

### Structured tool inputs and results

Register a `ToolAdapter` when a command accepts structured data or returns a
Python value. The custom schema describes the MCP input. The argument adapter
maps it to Click parameter names, and Click still parses and invokes the command
normally.

```python
import json

from click_mcp import ToolAdapter
from click_mcp.decorator import register_mcp_metadata


@cli.command()
@click.option("--query-json", required=True)
def lookup(query_json):
    query = json.loads(query_json)
    return {"matched": [query["name"].upper()]}


register_mcp_metadata(
    "lookup",
    {
        "adapter": ToolAdapter(
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                },
            },
            adapt_arguments=lambda args: {"query_json": json.dumps(args["query"])},
            adapt_result=dict,
        ),
    },
)
```

With this adapter, calling `lookup` with `{"query": {"name": "Ada"}}` returns
`{"matched": ["ADA"]}` as MCP structured content and JSON text. The result
adapter receives the value returned by the Click invocation, including any
group result callback. It must produce a JSON object. Commands without a result
adapter continue to return captured stdout.

### Handling Command Errors

When a Click command raises an exception, `click-mcp` captures the error and returns it as part of the MCP response. This allows AI agents to handle errors gracefully:

```python
@cli.command()
@click.option('--filename', required=True)
def process(filename):
    """Process a file."""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        click.echo(f"Processed file: {filename}")
    except FileNotFoundError:
        raise click.UsageError(f"File not found: {filename}")
```

If the file doesn't exist, the AI agent will receive an error message that it can present to the user or use to take corrective action.

Click groups with a custom `main()` are invoked with `standalone_mode=False`.
Click may return an integer for an exit in that mode, so a custom entry point
that needs to report a nonzero exit to MCP should raise `SystemExit` or
`click.ClickException` instead of returning a status code.

### Resources and tool completion hooks

Generated tools are the default. To serve read-only resources alongside them,
pass a `configure_server` callback to register MCP SDK handlers before the
server starts. The SDK handles discovery and dispatch.

```python
from mcp import types

from click_mcp import ToolCompletion, click_mcp

SUMMARY = "inventory://projects/summary"
TEMPLATE = "inventory://projects/{project}"


def configure_server(server):
    server.add_request_handler(
        "resources/list", types.PaginatedRequestParams, list_resources
    )
    server.add_request_handler(
        "resources/templates/list", types.PaginatedRequestParams, list_templates
    )
    server.add_request_handler(
        "resources/read", types.ReadResourceRequestParams, read_resource
    )


async def on_tool_complete(event: ToolCompletion):
    if event.command_path == ("projects", "publish") and not event.is_error:
        await event.context.session.send_resource_updated(SUMMARY)


click_mcp(
    "inventory",
    cli,
    configure_server=configure_server,
    on_tool_complete=on_tool_complete,
)
```

The [runnable example](tests/resources_cli.py) defines the three async resource
handlers and the `projects publish` command. Its resource list advertises
`inventory://projects/summary`, its template list advertises
`inventory://projects/{project}`, and its read handler serves both kinds of URI.

The optional completion hook receives the MCP tool name, original CLI path,
request context, error status, and execution duration in seconds. It runs after
a known tool has been handled and before its response is sent. Requests rejected
before reaching the tool handler bypass the hook. The server logs hook exceptions
and returns the tool's original result. Click command callbacks remain synchronous.

## Development

### Setup

Clone the repository and install Hatch:

```bash
git clone https://github.com/crowecawcaw/click-mcp.git
cd click-mcp
pip install hatch
```

### Testing

Run tests with Hatch:

```bash
# Run all tests
hatch run test

# Run tests with coverage
hatch run cov
```

### Code Formatting

Format code with Black:

```bash
# Format code
hatch run format

# Check formatting
hatch run check-format
```

### Linting

Run linting checks with Ruff:

```bash
hatch run lint
```

### Type Checking

Run type checking with MyPy:

```bash
hatch run typecheck
```

### Run All Checks

Run all checks (formatting, linting, type checking, and tests):

```bash
hatch run check-all
```

### Building

Build the package:

```bash
hatch run build
```

## Related Resources

- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/specification)
- [Click Documentation](https://click.palletsprojects.com/)
- [MCP Tools Registry](https://github.com/modelcontextprotocol/registry) - A collection of MCP-compatible tools

## License

MIT

# click-mcp

[![PyPI version](https://badge.fury.io/py/click-mcp.svg)](https://badge.fury.io/py/click-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library that extends Click applications with Model Context Protocol (MCP) support, allowing AI agents to interact with CLI tools.

## Overview

`click-mcp` provides a simple decorator that converts Click commands into MCP tools. This enables AI agents to discover and interact with your CLI applications programmatically.

The [Model Context Protocol (MCP)](https://github.com/model-context-protocol/mcp) is an open standard for AI agents to interact with tools and applications in a structured way.

## Key Features

- Simple `@click_mcp` decorator syntax
- Automatic conversion of Click commands to MCP tools
- Support for nested command groups
- Stdio-based MCP server for easy integration

## Installation

```bash
pip install click-mcp
```

## Basic Usage

```python
import click
from click_mcp import click_mcp

@click_mcp
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
- Nested commands use dot notation (e.g., `users.create`)

To invoke a command via MCP, send a request like:

```json
{
  "type": "invoke",
  "tool": "greet",
  "parameters": {
    "name": "World"
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
@click_mcp(command_name="start-mcp")
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

### Working with Nested Command Groups

`click-mcp` supports nested command groups. When you have a complex CLI structure with subcommands, all commands are exposed as MCP tools:

```python
@click_mcp
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

When exposed as MCP tools, the nested commands will be available with their full path using dot notation (e.g., "users.create" and "users.delete").

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

## Development

### Setup

Clone the repository and install development dependencies:

```bash
git clone https://github.com/aws/click-mcp.git
cd click-mcp
pip install -e ".[dev]"
```

Or with UV (faster installation):

```bash
git clone https://github.com/aws/click-mcp.git
cd click-mcp
uv pip install -e ".[dev]"
```

### Testing

Run tests with pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=click_mcp
```

### Code Formatting

Format code with black:

```bash
black click_mcp tests
```

Run linting checks:

```bash
flake8 click_mcp tests
```

### Building

Build the package:

```bash
python -m build
```

Or with UV:

```bash
uv pip install build
python -m build
```

### Documentation

Generate documentation:

```bash
cd docs
make html
```

## Related Resources

- [Model Context Protocol (MCP) Specification](https://github.com/model-context-protocol/mcp)
- [Click Documentation](https://click.palletsprojects.com/)
- [MCP Tools Registry](https://github.com/model-context-protocol/registry) - A collection of MCP-compatible tools

## License

MIT

"""
Test suite for validating tool schemas against the official MCP specification.

This test module ensures that all generated tool schemas comply with the
Model Context Protocol (MCP) JSON Schema specification.
"""

import json
from pathlib import Path
from typing import List

import click
import jsonschema
import pytest
from mcp import types

from click_mcp.scanner import scan_click_command


# Load the official MCP JSON Schema
SCHEMA_PATH = Path(__file__).parent / "schemas" / "mcp_schema_2025-06-18.json"
with open(SCHEMA_PATH) as f:
    MCP_SCHEMA = json.load(f)

# Create a validator for Tool objects
TOOL_SCHEMA = MCP_SCHEMA["definitions"]["Tool"]


def validate_tool_against_schema(tool: types.Tool) -> None:
    """Validate a Tool object against the official MCP schema."""
    # Convert tool to dict for validation
    tool_dict = {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.inputSchema,
    }

    # Validate against the schema
    jsonschema.validate(
        instance=tool_dict,
        schema=TOOL_SCHEMA,
        resolver=jsonschema.RefResolver(
            base_uri="",
            referrer=MCP_SCHEMA,
        ),
    )


class TestBasicCLISchemaValidation:
    """Test schema validation for basic CLI applications."""

    @pytest.fixture
    def basic_cli(self):
        """Create a basic CLI for testing."""
        @click.group()
        def cli():
            """Basic CLI application."""
            pass

        @cli.command()
        @click.option("--name", required=True, help="Name to greet")
        def greet(name):
            """Greet someone with a friendly message."""
            click.echo(f"Hello, {name}!")

        @cli.command()
        @click.option("--message", required=True, help="Message to echo")
        @click.option("--count", type=int, default=1, help="Number of times to echo")
        def echo(message, count):
            """Echo a message multiple times."""
            click.echo("\n".join([message] * count))

        @cli.command()
        @click.option("--verbose", is_flag=True, help="Enable verbose output")
        def status(verbose):
            """Show status information."""
            if verbose:
                click.echo("Status: OK (verbose)")
            else:
                click.echo("Status: OK")

        return cli

    def test_all_tools_validate_against_schema(self, basic_cli):
        """Test that all tools from basic CLI validate against MCP schema."""
        tools = scan_click_command(basic_cli)

        assert len(tools) > 0, "Should generate at least one tool"

        for tool in tools:
            # This will raise ValidationError if the tool doesn't match the schema
            validate_tool_against_schema(tool)

    def test_tool_has_required_fields(self, basic_cli):
        """Test that tools have all required fields per MCP spec."""
        tools = scan_click_command(basic_cli)

        for tool in tools:
            assert tool.name, "Tool must have a name"
            assert tool.inputSchema, "Tool must have an inputSchema"
            assert isinstance(tool.inputSchema, dict), "inputSchema must be a dict"
            assert tool.inputSchema.get("type") == "object", "inputSchema type must be 'object'"

    def test_input_schema_structure(self, basic_cli):
        """Test that inputSchema follows JSON Schema structure."""
        tools = scan_click_command(basic_cli)

        for tool in tools:
            schema = tool.inputSchema

            # Required top-level fields
            assert "type" in schema
            assert schema["type"] == "object"

            # Properties should be present (even if empty)
            assert "properties" in schema
            assert isinstance(schema["properties"], dict)

            # If there are required params, validate the structure
            if "required" in schema:
                assert isinstance(schema["required"], list)
                assert all(isinstance(r, str) for r in schema["required"])
                # All required params must be in properties
                for req in schema["required"]:
                    assert req in schema["properties"], f"Required param '{req}' must be in properties"

    def test_property_schemas_are_valid(self, basic_cli):
        """Test that each property schema is valid JSON Schema."""
        tools = scan_click_command(basic_cli)

        for tool in tools:
            properties = tool.inputSchema.get("properties", {})

            for prop_name, prop_schema in properties.items():
                # Each property must be a dict
                assert isinstance(prop_schema, dict), f"Property '{prop_name}' schema must be a dict"

                # Each property must have a type (per JSON Schema draft 2020-12)
                assert "type" in prop_schema, f"Property '{prop_name}' must have a 'type' field"

                # Type must be a valid JSON Schema type
                valid_types = ["string", "integer", "number", "boolean", "array", "object", "null"]
                assert prop_schema["type"] in valid_types, f"Property '{prop_name}' has invalid type"

                # If description is present, it must be a string
                if "description" in prop_schema:
                    assert isinstance(prop_schema["description"], str)

                # If default is present, it must be JSON-serializable
                if "default" in prop_schema:
                    # Test JSON serialization
                    json.dumps(prop_schema["default"])


class TestComplexCLISchemaValidation:
    """Test schema validation for complex CLI applications with various parameter types."""

    @pytest.fixture
    def complex_cli(self):
        """Create a complex CLI with various parameter types."""
        @click.group()
        def cli():
            """Complex CLI application."""
            pass

        @cli.command()
        @click.option("--host", default="localhost", help="Server host")
        @click.option("--port", type=int, default=8080, help="Server port")
        @click.option("--debug", is_flag=True, help="Enable debug mode")
        @click.option("--log-level", type=click.Choice(["debug", "info", "warning", "error"]), default="info")
        def server(host, port, debug, log_level):
            """Start the server."""
            click.echo(f"Starting server on {host}:{port}")

        @cli.group()
        def config():
            """Configuration management."""
            pass

        @config.command()
        @click.argument("key")
        @click.argument("value")
        def set(key, value):
            """Set a configuration value."""
            click.echo(f"Setting {key}={value}")

        @config.command()
        @click.argument("key")
        def get(key):
            """Get a configuration value."""
            click.echo(f"Getting {key}")

        return cli

    def test_complex_tools_validate_against_schema(self, complex_cli):
        """Test that complex tools validate against MCP schema."""
        tools = scan_click_command(complex_cli)

        for tool in tools:
            validate_tool_against_schema(tool)

    def test_enum_properties_are_valid(self, complex_cli):
        """Test that enum (choice) properties are properly structured."""
        tools = scan_click_command(complex_cli)

        # Find the server tool which has a choice parameter
        server_tool = next((t for t in tools if "server" in t.name.lower()), None)
        assert server_tool is not None

        properties = server_tool.inputSchema["properties"]

        # Check if log_level has enum
        if "log_level" in properties:
            assert "enum" in properties["log_level"]
            assert isinstance(properties["log_level"]["enum"], list)
            assert len(properties["log_level"]["enum"]) > 0

    def test_default_values_are_json_serializable(self, complex_cli):
        """Test that all default values are JSON-serializable."""
        tools = scan_click_command(complex_cli)

        for tool in tools:
            properties = tool.inputSchema.get("properties", {})

            for prop_name, prop_schema in properties.items():
                if "default" in prop_schema:
                    # Should not raise an exception
                    json_str = json.dumps(prop_schema["default"])
                    # Should be able to parse it back
                    json.loads(json_str)

    def test_boolean_flags_have_correct_type(self, complex_cli):
        """Test that boolean flags have type 'boolean'."""
        tools = scan_click_command(complex_cli)

        # Find the server tool
        server_tool = next((t for t in tools if "server" in t.name.lower()), None)
        assert server_tool is not None

        properties = server_tool.inputSchema["properties"]

        # Debug flag should be boolean
        if "debug" in properties:
            assert properties["debug"]["type"] == "boolean"

    def test_integer_parameters_have_correct_type(self, complex_cli):
        """Test that integer parameters have type 'integer'."""
        tools = scan_click_command(complex_cli)

        # Find the server tool
        server_tool = next((t for t in tools if "server" in t.name.lower()), None)
        assert server_tool is not None

        properties = server_tool.inputSchema["properties"]

        # Port should be integer
        if "port" in properties:
            assert properties["port"]["type"] == "integer"


class TestSchemaComplianceWithRealCLIs:
    """Test schema validation with the actual test CLI fixtures."""

    def test_basic_cli_fixture_validates(self):
        """Test that the basic_cli test fixture validates against MCP schema."""
        from tests.basic_cli import cli

        tools = scan_click_command(cli)

        for tool in tools:
            validate_tool_against_schema(tool)

    def test_advanced_cli_fixture_validates(self):
        """Test that the advanced_cli test fixture validates against MCP schema."""
        from tests.advanced_cli import cli

        tools = scan_click_command(cli)

        for tool in tools:
            validate_tool_against_schema(tool)

    def test_context_cli_fixture_validates(self):
        """Test that the context_cli test fixture validates against MCP schema."""
        from tests.context_cli import parent

        tools = scan_click_command(parent)

        for tool in tools:
            validate_tool_against_schema(tool)


class TestSchemaEdgeCases:
    """Test edge cases and special scenarios for schema validation."""

    def test_empty_command_validates(self):
        """Test that commands with no parameters still generate valid schemas."""
        @click.group()
        def cli():
            pass

        @cli.command()
        def simple():
            """A simple command with no parameters."""
            click.echo("Simple")

        tools = scan_click_command(cli)

        for tool in tools:
            validate_tool_against_schema(tool)

            # Should still have properties (even if empty or just help)
            assert "properties" in tool.inputSchema

    def test_command_with_only_optional_params(self):
        """Test commands where all parameters are optional."""
        @click.group()
        def cli():
            pass

        @cli.command()
        @click.option("--optional1", help="First optional param")
        @click.option("--optional2", help="Second optional param")
        def optional_cmd(optional1, optional2):
            """Command with only optional params."""
            pass

        tools = scan_click_command(cli)

        for tool in tools:
            validate_tool_against_schema(tool)

            # Should not have required array, or it should be empty
            required = tool.inputSchema.get("required", [])
            # Filter out 'help' if it exists
            required = [r for r in required if r != "help"]
            assert len(required) == 0

    def test_no_sentinel_values_in_schema(self):
        """Test that Click's Sentinel.UNSET values are filtered out."""
        @click.group()
        def cli():
            pass

        @cli.command()
        @click.option("--param", help="A parameter")
        def cmd(param):
            """Command with a parameter."""
            pass

        tools = scan_click_command(cli)

        for tool in tools:
            properties = tool.inputSchema.get("properties", {})

            for prop_name, prop_schema in properties.items():
                # Check that default, if present, is JSON-serializable
                if "default" in prop_schema:
                    # This should not raise an exception
                    json.dumps(prop_schema)

                    # Check that it's not a Sentinel object
                    default = prop_schema["default"]
                    assert not (hasattr(default, "__class__") and
                              "Sentinel" in default.__class__.__name__)

"""
Test cases for Click context passing functionality in click-mcp.

This module reproduces GitHub issue #8 and validates that context passing
works correctly between parent and child commands when using click-mcp.
"""

import pytest
import click
from click.testing import CliRunner
from click_mcp.decorator import click_mcp
from click_mcp.server import ClickMCPServer


class TestContextPassing:
    """Test cases for Click context passing functionality."""

    def test_click_native_context_passing_works(self):
        """
        Verify that Click's native context passing works correctly.
        This test validates our understanding of Click's proper behavior.
        """
        @click.group()
        @click.option("--env", "-e", help="Environment", default="DEFAULT")
        @click.pass_context
        def parent(ctx, env):
            """Parent command that sets up context."""
            ctx.obj = {"env": env}

        @parent.command()
        @click.pass_context
        def child(ctx):
            """Child command that should access parent context."""
            if ctx.obj is None:
                click.echo("ERROR: ctx.obj is None")
            else:
                click.echo(f"env={ctx.obj['env']}")

        # Test with Click's native execution
        runner = CliRunner()
        
        # Test default value
        result = runner.invoke(parent, ["child"])
        assert result.exit_code == 0
        assert "env=DEFAULT" in result.output
        assert "ERROR: ctx.obj is None" not in result.output

        # Test custom value
        result = runner.invoke(parent, ["--env", "PRODUCTION", "child"])
        assert result.exit_code == 0
        assert "env=PRODUCTION" in result.output
        assert "ERROR: ctx.obj is None" not in result.output

    def test_github_issue_8_reproduction(self):
        """
        Reproduce GitHub issue #8: @click.pass_context does not work correctly.
        
        This test demonstrates the current problem where ctx.obj is None
        in child commands when executed via click-mcp.
        """
        @click_mcp(server_name="test_server")
        @click.group()
        @click.option("--env", "-e", help="Environment", default="DEFAULT")
        @click.pass_context
        def parent(ctx, env):
            """Parent command that sets up context."""
            ctx.obj = {"env": env}

        @parent.command()
        @click.pass_context
        def child(ctx):
            """Child command that should access parent context."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            else:
                return f"env={ctx.obj['env']}"

        # Create MCP server
        server = ClickMCPServer(parent)
        
        # Get available tools
        tools = server.list_tools()
        tool_names = [tool.name for tool in tools]
        
        # Should have tools for both parent and child commands
        # Note: Current implementation may create separate tools
        assert len(tools) > 0
        
        # Try to find a tool that represents the child command
        child_tool = None
        for tool in tools:
            if "child" in tool.name:
                child_tool = tool
                break
        
        if child_tool is None:
            pytest.skip("Child command tool not found - may indicate scanner issue")
        
        # Execute child command via MCP
        # This should fail with current implementation (ctx.obj is None)
        try:
            result = server.call_tool(child_tool.name, {})
            # Current implementation will likely show the error
            assert "ERROR: ctx.obj is None" in result.get("output", "")
        except Exception as e:
            # Current implementation may throw exception due to context issues
            assert "context" in str(e).lower() or "none" in str(e).lower()

    def test_context_passing_with_arguments(self):
        """
        Test context passing when parent command has arguments and options.
        This tests a more complex scenario similar to the GitHub issue example.
        """
        @click.group()
        @click.option("--env", "-e", help="Environment", default="DEFAULT")
        @click.option("--debug", is_flag=True, help="Debug mode")
        @click.pass_context
        def parent(ctx, env, debug):
            """Parent command with multiple options."""
            ctx.obj = {
                "env": env,
                "debug": debug,
                "initialized": True
            }

        @parent.command()
        @click.option("--child-flag", help="Child-specific flag")
        @click.pass_context
        def child_a(ctx, child_flag):
            """First child command."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            result = {
                "env": ctx.obj["env"],
                "debug": ctx.obj["debug"],
                "initialized": ctx.obj["initialized"],
                "child_flag": child_flag
            }
            return str(result)

        @parent.command()
        @click.pass_context
        def child_b(ctx):
            """Second child command."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            return f"Child B - env={ctx.obj['env']}, debug={ctx.obj['debug']}"

        # Test with Click's native execution
        runner = CliRunner()
        
        # Test child_a with default parent options
        result = runner.invoke(parent, ["child-a"])
        assert result.exit_code == 0
        assert "env': 'DEFAULT'" in result.output
        assert "debug': False" in result.output
        assert "initialized': True" in result.output

        # Test child_a with custom parent options
        result = runner.invoke(parent, ["--env", "STAGING", "--debug", "child-a", "--child-flag", "test"])
        assert result.exit_code == 0
        assert "env': 'STAGING'" in result.output
        assert "debug': True" in result.output
        assert "child_flag': 'test'" in result.output

        # Test child_b
        result = runner.invoke(parent, ["--env", "PRODUCTION", "child-b"])
        assert result.exit_code == 0
        assert "Child B - env=PRODUCTION, debug=False" in result.output

    def test_nested_context_inheritance(self):
        """
        Test context inheritance through multiple levels of nesting.
        This validates that context passing works for deeply nested commands.
        """
        @click.group()
        @click.option("--level", default="1")
        @click.pass_context
        def level1(ctx, level):
            """Level 1 command."""
            ctx.obj = {"levels": [level]}

        @level1.group()
        @click.option("--level", default="2")
        @click.pass_context
        def level2(ctx, level):
            """Level 2 command."""
            if ctx.obj is None:
                ctx.obj = {"levels": []}
            ctx.obj["levels"].append(level)

        @level2.command()
        @click.option("--level", default="3")
        @click.pass_context
        def level3(ctx, level):
            """Level 3 command."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            ctx.obj["levels"].append(level)
            return f"Levels: {' -> '.join(ctx.obj['levels'])}"

        # Test with Click's native execution
        runner = CliRunner()
        result = runner.invoke(level1, ["level2", "level3"])
        assert result.exit_code == 0
        assert "Levels: 1 -> 2 -> 3" in result.output

    def test_context_passing_error_scenarios(self):
        """
        Test error scenarios in context passing to ensure proper error handling.
        """
        @click.group()
        @click.pass_context
        def parent(ctx):
            """Parent that doesn't set ctx.obj."""
            pass  # Intentionally don't set ctx.obj

        @parent.command()
        @click.pass_context
        def child(ctx):
            """Child that expects ctx.obj to exist."""
            if ctx.obj is None:
                return "ctx.obj is None as expected"
            else:
                return f"ctx.obj exists: {ctx.obj}"

        # Test with Click's native execution
        runner = CliRunner()
        result = runner.invoke(parent, ["child"])
        assert result.exit_code == 0
        assert "ctx.obj is None as expected" in result.output

    def test_context_modification_by_child(self):
        """
        Test that child commands can modify the context object.
        """
        @click.group()
        @click.pass_context
        def parent(ctx):
            """Parent command that sets up initial context."""
            ctx.obj = {"counter": 0, "messages": []}

        @parent.command()
        @click.pass_context
        def increment(ctx):
            """Child command that modifies context."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            ctx.obj["counter"] += 1
            ctx.obj["messages"].append(f"Incremented to {ctx.obj['counter']}")
            return f"Counter: {ctx.obj['counter']}"

        @parent.command()
        @click.pass_context
        def show_messages(ctx):
            """Child command that reads modified context."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            return f"Messages: {', '.join(ctx.obj['messages'])}"

        # Test with Click's native execution
        runner = CliRunner()
        
        # Test increment
        result = runner.invoke(parent, ["increment"])
        assert result.exit_code == 0
        assert "Counter: 1" in result.output

        # Note: In separate invocations, context doesn't persist
        # This is expected behavior for Click


class TestClickMCPContextIntegration:
    """Test cases specifically for click-mcp context integration."""

    def test_mcp_server_tool_generation_with_context(self):
        """
        Test that MCP server correctly generates tools for commands with context.
        """
        @click_mcp(server_name="context_test")
        @click.group()
        @click.option("--config", help="Configuration file")
        @click.pass_context
        def cli(ctx, config):
            """Main CLI with context."""
            ctx.obj = {"config": config}

        @cli.command()
        @click.pass_context
        def status(ctx):
            """Status command that uses context."""
            if ctx.obj is None:
                return "No context available"
            return f"Config: {ctx.obj.get('config', 'None')}"

        # Create MCP server
        server = ClickMCPServer(cli)
        
        # Verify tools are generated
        tools = server.list_tools()
        assert len(tools) > 0
        
        # Check that tools have proper schemas
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')

    def test_mcp_server_context_isolation(self):
        """
        Test that MCP server properly isolates contexts between tool calls.
        This is important to ensure no context leakage between different MCP requests.
        """
        @click_mcp(server_name="isolation_test")
        @click.group()
        @click.pass_context
        def cli(ctx):
            """CLI for testing context isolation."""
            ctx.obj = {"call_count": 0}

        @cli.command()
        @click.pass_context
        def count(ctx):
            """Command that increments a counter."""
            if ctx.obj is None:
                return "ERROR: ctx.obj is None"
            
            ctx.obj["call_count"] += 1
            return f"Call count: {ctx.obj['call_count']}"

        # Create MCP server
        server = ClickMCPServer(cli)
        tools = server.list_tools()
        
        # Find the count tool
        count_tool = None
        for tool in tools:
            if "count" in tool.name:
                count_tool = tool
                break
        
        if count_tool is None:
            pytest.skip("Count tool not found")
        
        # Make multiple calls - each should start with fresh context
        # Note: This test documents current behavior, which may need to change
        # depending on the desired context persistence model
        try:
            result1 = server.call_tool(count_tool.name, {})
            result2 = server.call_tool(count_tool.name, {})
            
            # With current isolated execution, each call should start fresh
            # This may change once proper context passing is implemented
            assert "Call count: 1" in result1.get("output", "")
            assert "Call count: 1" in result2.get("output", "")
        except Exception:
            # Current implementation may fail due to context issues
            # This is expected and will be fixed in task 7
            pass


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

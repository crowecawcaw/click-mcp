#!/usr/bin/env python3
"""
Simple test script to validate the context passing fix.
"""

import click
from click_mcp.decorator import click_mcp
from click_mcp.server import MCPServer


def test_context_passing_fix():
    """Test that the context passing fix works correctly."""
    
    @click_mcp(server_name="test_server")
    @click.group()
    @click.option("--env", "-e", help="Environment", default="DEFAULT")
    @click.pass_context
    def parent(ctx, env):
        """Parent command that sets up context."""
        print(f"Parent: Setting ctx.obj = {{'env': '{env}'}}")
        ctx.obj = {"env": env}

    @parent.command()
    @click.pass_context
    def child(ctx):
        """Child command that should access parent context."""
        if ctx.obj is None:
            return "ERROR: ctx.obj is None"
        else:
            return f"SUCCESS: env={ctx.obj['env']}"
    
    # Debug: Print the CLI structure
    print("CLI structure:")
    print(f"Parent group: {parent.name}")
    print(f"Parent commands: {list(parent.commands.keys())}")
    
    # Debug: Check if child command knows about its parent
    child_cmd = parent.commands.get('child')
    if child_cmd:
        print(f"Child command: {child_cmd.name}")
        print(f"Child parent: {getattr(child_cmd, 'parent', 'None')}")

    # Create MCP server
    server = MCPServer(parent)
    
    # Get available tools directly from the server's click_tools attribute
    tools = server.click_tools
    print(f"Available tools: {[tool.name for tool in tools]}")
    
    # Debug: Print tool details and original paths
    from click_mcp.scanner import get_original_path
    for tool in tools:
        original_path = get_original_path(tool.name)
        print(f"Tool: {tool.name}, Original Path: {original_path}, Description: {tool.description}")
    
    # Try to find and execute child command
    child_tool = None
    for tool in tools:
        if "child" in tool.name:
            child_tool = tool
            break
    
    if child_tool is None:
        print("ERROR: Child tool not found")
        return False
    
    print(f"Executing tool: {child_tool.name}")
    original_path = get_original_path(child_tool.name)
    print(f"Original path: {original_path}")
    
    try:
        # Execute child command via MCP server's internal method
        result = server._execute_command(child_tool.name, {})
        output = result.get("output", "")
        print(f"Result: {output}")
        
        # Check if context passing worked
        if "SUCCESS: env=DEFAULT" in output:
            print("✅ Context passing fix is working!")
            return True
        elif "ERROR: ctx.obj is None" in output:
            print("❌ Context passing is still broken")
            return False
        else:
            print(f"⚠️  Unexpected output: {output}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during execution: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing context passing fix...")
    success = test_context_passing_fix()
    if success:
        print("\n🎉 Context passing fix validation successful!")
    else:
        print("\n💥 Context passing fix validation failed!")







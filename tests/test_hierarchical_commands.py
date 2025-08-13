"""
Integration tests for hierarchical command execution with Click context passing.

These tests verify that parent command context (ctx.obj) is properly passed
to child commands when executed through the MCP server using hierarchical tools.
"""

import pytest
from pathlib import Path
from .test_mcp_server import mcp_server_client


@pytest.fixture
async def context_mcp_session(request):
    """Fixture that provides an MCP server context for the context CLI."""
    script_path = Path(__file__).parent / "context_cli.py"
    async with mcp_server_client(script_path, "mcp") as session:
        yield session


@pytest.mark.anyio
async def test_hierarchical_context_passing_child_a(context_mcp_session):
    """
    Test that parent command context is properly passed to child command A.
    
    Verifies: parent --env PRODUCTION child-a
    Expected: Child A should have access to ctx.obj with env="PRODUCTION"
    The hierarchical implementation properly passes parent context to child commands.
    """
    session = context_mcp_session
    
    # List available tools
    result = await session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # Verify the child-a command is available with hierarchical naming
    assert "parent_child_a" in tool_names
    
    # Execute the parent_child_a command with parent env option
    # This now works because the hierarchical implementation includes parent parameters
    result = await session.call_tool(
        "parent_child_a",
        {"env": "PRODUCTION"}
    )
    
    output = result.content[0].text
    
    # The fix: The hierarchical implementation properly executes the full command chain
    # and passes parent context to child commands
    assert "Parent: Setting env=PRODUCTION" in output, f"Expected parent execution output, but got: {output}"
    assert "Child A: Using env=PRODUCTION" in output, f"Expected child to use parent context, but got: {output}"


@pytest.mark.anyio
async def test_hierarchical_context_passing_child_b(context_mcp_session):
    """
    Test that parent command context is properly passed to child command B with parameters.
    
    Verifies: parent --env STAGING child-b --child-flag test
    Expected: Child B should have access to ctx.obj with env="STAGING"
    The hierarchical implementation properly passes parent context to child commands.
    """
    session = context_mcp_session
    
    # List available tools
    result = await session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # Verify the child-b command is available with hierarchical naming
    assert "parent_child_b" in tool_names
    
    # Execute the parent_child_b command with parent env option and child flag
    # This now works because the hierarchical implementation includes both parent and child parameters
    result = await session.call_tool(
        "parent_child_b",
        {"env": "STAGING", "child_flag": "test"}
    )
    
    output = result.content[0].text
    
    # The fix: The hierarchical implementation properly executes the full command chain
    # and passes parent context to child commands
    assert "Parent: Setting env=STAGING" in output, f"Expected parent execution output, but got: {output}"
    assert "Child B: Using env=STAGING" in output, f"Expected child to use parent context and child flag, but got: {output}"


@pytest.mark.anyio
async def test_hierarchical_context_passing_child_c(context_mcp_session):
    """
    Test that parent command context is properly passed to child command C with positional args.
    
    Verifies: parent --env DEVELOPMENT child-c "hello world"
    Expected: Child C should have access to ctx.obj with env="DEVELOPMENT"
    The hierarchical implementation properly passes parent context to child commands.
    """
    session = context_mcp_session
    
    # List available tools
    result = await session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # Verify the child-c command is available with hierarchical naming
    assert "parent_child_c" in tool_names
    
    # Execute the parent_child_c command with parent env option and message argument
    # This now works because the hierarchical implementation includes both parent and child parameters
    result = await session.call_tool(
        "parent_child_c",
        {"env": "DEVELOPMENT", "message": "hello world"}
    )
    
    output = result.content[0].text
    
    # The fix: The hierarchical implementation properly executes the full command chain
    # and passes parent context to child commands
    assert "Parent: Setting env=DEVELOPMENT" in output, f"Expected parent execution output, but got: {output}"
    assert "Child C: Message 'hello world' in env=DEVELOPMENT" in output, f"Expected child to use parent context and child argument, but got: {output}"


@pytest.mark.anyio
async def test_hierarchical_context_with_default_values(context_mcp_session):
    """
    Test that hierarchical commands work with default parent parameter values.
    
    Verifies: parent child-a (using default env="DEFAULT")
    Expected: Child A should have access to ctx.obj with env="DEFAULT"
    The hierarchical implementation properly sets up parent context with defaults.
    """
    session = context_mcp_session
    
    # Execute the parent_child_a command without specifying env (should use default)
    # This simulates: parent child-a
    result = await session.call_tool(
        "parent_child_a",
        {}  # No parameters, should use default env="DEFAULT"
    )
    
    output = result.content[0].text
    
    # The fix: The hierarchical implementation properly sets up parent context with defaults
    assert "Parent: Setting env=DEFAULT" in output, f"Expected parent to use default env, but got: {output}"
    assert "Child A: Using env=DEFAULT" in output, f"Expected child to access parent context with default env, but got: {output}"


@pytest.mark.anyio
async def test_child_command_works_standalone(context_mcp_session):
    """
    Test that demonstrates how the hierarchical approach provides both parent and child parameters.
    
    The hierarchical tools include all necessary parameters, so there's no need for
    "standalone" child commands - the hierarchical tools are self-contained.
    """
    session = context_mcp_session
    
    # Execute parent_child_c with both parent and child parameters
    result = await session.call_tool(
        "parent_child_c",
        {"env": "TEST", "message": "hello world"}
    )
    
    output = result.content[0].text
    
    # The hierarchical approach provides complete functionality
    assert "Parent: Setting env=TEST" in output, f"Expected parent execution, but got: {output}"
    assert "Child C: Message 'hello world' in env=TEST" in output, f"Expected child to have full context, but got: {output}"


@pytest.mark.anyio
async def test_verify_tools_are_discovered(context_mcp_session):
    """
    Verify that all the expected tools are discovered by the MCP server.
    """
    session = context_mcp_session
    
    result = await session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]
    
    # With the hierarchical fix, tools now have hierarchical names
    # that include the parent command name
    expected_tools = [
        "parent_child_a", 
        "parent_child_b",
        "parent_child_c",
        # Nested tools should also be present
        "users_create",
        "users_delete", 
        "users_permissions_grant",
        "users_permissions_revoke",
        "projects_create_project",
        # Note: MCP command is intentionally not exposed as a tool
    ]
    
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found in {tool_names}"


@pytest.mark.anyio
async def test_deeply_nested_context_passing_level_2(context_mcp_session):
    """
    Test that context is properly passed through 2 levels of nesting.
    
    Note: users_create only includes parameters from the final command (create),
    not from parent groups. Parent context is passed through Click's mechanism.
    """
    session = context_mcp_session
    
    result = await session.call_tool(
        "users_create",
        {
            "username": "alice",
            "role": "admin"
        }
    )
    
    output = result.content[0].text
    
    # Verify all levels of context are passed through Click's mechanism
    # Parent and users groups use their default values
    assert "Parent: Setting env=DEFAULT" in output  # Default parent context
    assert "Users: database=main, timeout=30, env=DEFAULT" in output  # Default users context
    assert "Create: user=alice, role=admin, db=main, timeout=30, env=DEFAULT, debug=False" in output


@pytest.mark.anyio
async def test_deeply_nested_context_passing_level_3(context_mcp_session):
    """
    Test that context is properly passed through 3 levels of nesting.
    
    Note: users_permissions_grant only includes parameters from the final command (grant),
    not from parent groups. Parent context is passed through Click's mechanism.
    """
    session = context_mcp_session
    
    result = await session.call_tool(
        "users_permissions_grant",
        {
            "username": "bob",
            "permission": "read",
            "expires": "2024-12-31"
        }
    )
    
    output = result.content[0].text
    
    # Verify all 3 levels of context are passed through Click's mechanism
    # All parent groups use their default values
    assert "Parent: Setting env=DEFAULT" in output  # Default parent context
    assert "Users: database=main, timeout=30, env=DEFAULT" in output  # Default users context
    assert "Permissions: scope=global, audit=True, db=main, env=DEFAULT" in output  # Default permissions context
    assert "Grant: user=bob, perm=read, expires=2024-12-31" in output
    assert "Context: env=DEFAULT, debug=False, config=None" in output
    assert "Database: db=main, timeout=30" in output
    assert "Permissions: scope=global, audit=True" in output


@pytest.mark.anyio
async def test_deeply_nested_revoke_command(context_mcp_session):
    """
    Test the revoke command at 3 levels of nesting with different parameters.
    """
    session = context_mcp_session
    
    result = await session.call_tool(
        "users_permissions_revoke",
        {
            "username": "charlie",
            "permission": "write",
            "reason": "security_review"
        }
    )
    
    output = result.content[0].text
    
    # Verify context passing through all levels (using defaults for parent levels)
    assert "Parent: Setting env=DEFAULT" in output
    assert "Users: database=main" in output  # default database
    assert "Permissions: scope=global, audit=True" in output  # default permissions
    assert "Revoke: user=charlie, perm=write, reason=security_review" in output
    assert "Context: env=DEFAULT, db=main, scope=global, audit=True" in output


@pytest.mark.anyio
async def test_different_nested_group_projects(context_mcp_session):
    """
    Test a different nested group (projects) to ensure the pattern works across multiple groups.
    """
    session = context_mcp_session
    
    result = await session.call_tool(
        "projects_create_project",
        {
            "name": "new-service",
            "template": "microservice"
        }
    )
    
    output = result.content[0].text
    
    # Verify context passing for different nested group (using defaults for parent)
    assert "Parent: Setting env=DEFAULT, debug=False, config=None" in output
    assert "Projects: workspace=default, version=None, env=DEFAULT, debug=False" in output
    assert "CreateProject: name=new-service, template=microservice" in output
    assert "Context: workspace=default, version=None, env=DEFAULT, config=None" in output


@pytest.mark.anyio
async def test_nested_commands_with_defaults(context_mcp_session):
    """
    Test that nested commands work properly with default values at each level.
    """
    session = context_mcp_session
    
    # Test with minimal parameters, relying on defaults
    result = await session.call_tool(
        "users_create",
        {
            "username": "testuser"
            # Using defaults: env=DEFAULT, debug=False, config=None, database=main, timeout=30, role=user
        }
    )
    
    output = result.content[0].text
    
    # Verify defaults are properly applied at each level
    assert "Parent: Setting env=DEFAULT, debug=False, config=None" in output
    assert "Users: database=main, timeout=30, env=DEFAULT" in output
    assert "Create: user=testuser, role=user, db=main, timeout=30, env=DEFAULT, debug=False" in output
    
@pytest.mark.anyio
async def test_custom_mcp_command_name_excluded():
    """
    Test that custom MCP command names are also properly excluded from tools.
    """
    from .custom_mcp_name_cli import parent as custom_parent
    from click_mcp.scanner import scan_click_command
    
    tools = scan_click_command(custom_parent)
    tool_names = [tool.name for tool in tools]
    
    # Verify expected tools are present
    expected_tools = [
        "parent_child_a",
        "parent_regular_command"
    ]
    
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found in {tool_names}"
    
    # Verify that the custom MCP command name is NOT exposed as a tool
    assert "start-server" not in tool_names, f"Custom MCP command 'start-server' should not be exposed as a tool, but found in {tool_names}"
    assert "start_server" not in tool_names, f"Custom MCP command 'start_server' should not be exposed as a tool, but found in {tool_names}"
    
    # Also verify the default MCP name is not there
    assert "mcp" not in tool_names, f"Default MCP command should not be exposed as a tool, but found in {tool_names}"

"""
Tests for parameter processing in the MCP server.
"""

import pytest
from click_mcp.server import MCPServer
from tests.basic_cli import cli
from tests.context_cli import parent


class TestParameterProcessing:
    """Test parameter processing for both regular and hierarchical commands."""

    @pytest.fixture
    def basic_server(self):
        """Create MCP server with basic CLI."""
        return MCPServer(cli, "test-server")

    @pytest.fixture
    def context_server(self):
        """Create MCP server with context CLI."""
        return MCPServer(parent, "test-server")

    def test_regular_command_with_boolean_flags(self, basic_server):
        """Test regular command parameter processing with boolean flags."""
        args = basic_server._convert_parameters_to_args({
            'message': 'hello world',
            'count': 3
        }, [])
        
        # Both are options in the basic CLI
        expected = ['--message', 'hello world', '--count', '3']
        assert args == expected

    def test_regular_command_with_false_boolean(self, basic_server):
        """Test that false boolean flags are not included."""
        # Using a hypothetical boolean flag for testing
        args = basic_server._convert_parameters_to_args(
            {'message': 'hello world', 'count': 2, 'verbose': False},
            [],  # no positional args
            None
        )
        
        # False boolean should not appear in args
        expected = ['--message', 'hello world', '--count', '2']
        assert args == expected

    def test_regular_command_missing_optional_params(self, basic_server):
        """Test regular command with only required parameters."""
        args = basic_server._convert_parameters_to_args({
            'name': 'Alice'
        }, [])
        
        # name is an option in basic CLI, not positional
        expected = ['--name', 'Alice']
        assert args == expected

    def test_regular_command_with_all_params(self, basic_server):
        """Test regular command with all parameters provided."""
        # Using a hypothetical formal flag for testing
        args = basic_server._convert_parameters_to_args(
            {'name': 'Alice', 'formal': True},
            [],  # no positional args
            None
        )
        
        expected = ['--name', 'Alice', '--formal']
        assert args == expected

    def test_hierarchical_command_parent_only_params(self, context_server):
        """Test hierarchical command with only parent parameters."""
        args = context_server._prepare_hierarchical_arguments('parent_child_a', {
            'env': 'PRODUCTION'
        })
        
        # Should include parent param, then child command name
        expected = ['--env', 'PRODUCTION', 'child-a']
        assert args == expected

    def test_hierarchical_command_child_only_params(self, context_server):
        """Test hierarchical command with only child parameters."""
        args = context_server._prepare_hierarchical_arguments('parent_child_b', {
            'child_flag': 'test-value'
        })
        
        # Should include child command name, then child params
        expected = ['child-b', '--child-flag', 'test-value']
        assert args == expected

    def test_hierarchical_command_mixed_params(self, context_server):
        """Test hierarchical command with both parent and child parameters."""
        args = context_server._prepare_hierarchical_arguments('parent_child_b', {
            'env': 'STAGING',
            'child_flag': 'test-value'
        })
        
        # Should include parent params, child command, then child params
        expected = ['--env', 'STAGING', 'child-b', '--child-flag', 'test-value']
        assert args == expected

    def test_hierarchical_command_with_positional_args(self, context_server):
        """Test hierarchical command with positional arguments."""
        args = context_server._prepare_hierarchical_arguments('parent_child_c', {
            'env': 'TEST',
            'message': 'positional-test'
        })
        
        # Should include parent params, child command, then positional args
        expected = ['--env', 'TEST', 'child-c', 'positional-test']
        assert args == expected

    def test_parameter_name_conversion(self, basic_server):
        """Test that parameter names are converted from underscores to dashes."""
        # This test assumes we have a command with underscore parameters
        # Using the unified function directly to test name conversion
        args = basic_server._convert_parameters_to_args(
            {'test_param': 'value', 'another_flag': True},
            [],  # no positional args
            None  # no param definitions, use fallback
        )
        
        expected = ['--test-param', 'value', '--another-flag']
        assert args == expected

    def test_positional_args_ordering(self, basic_server):
        """Test that positional arguments maintain correct order."""
        # Test with echo command which has message as positional
        args = basic_server._convert_parameters_to_args(
            {'message': 'test', 'count': 2, 'uppercase': True},
            ['message'],  # message is positional
            None
        )
        
        # Positional args should come first, then options
        expected = ['test', '--count', '2', '--uppercase']
        assert args == expected

    def test_empty_parameters(self, basic_server):
        """Test handling of empty parameter dictionary."""
        args = basic_server._convert_parameters_to_args({}, [])
        
        # Should return empty list for no parameters
        assert args == []

    def test_parameter_filtering_in_hierarchical(self, context_server):
        """Test that parameters are correctly filtered between parent and child."""
        # This tests the internal filtering logic
        args = context_server._prepare_hierarchical_arguments('parent_child_a', {
            'env': 'PRODUCTION',
            'nonexistent_param': 'should_be_ignored'
        })
        
        # Should only include valid parent parameters
        expected = ['--env', 'PRODUCTION', 'child-a']
        assert args == expected

    def test_string_conversion(self, basic_server):
        """Test that non-string values are converted to strings."""
        args = basic_server._convert_parameters_to_args(
            {'count': 42, 'rate': 3.14, 'enabled': True},
            ['count'],  # count is positional
            None
        )
        
        # All values should be converted to strings
        expected = ['42', '--rate', '3.14', '--enabled']
        assert args == expected

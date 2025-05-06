"""
Tests for path sanitization and restoration functionality.
"""

import pytest

from click_mcp.scanner import _original_paths, get_original_path, sanitize_tool_name


@pytest.fixture
def clear_original_paths():
    """Clear the original paths mapping before each test."""
    _original_paths.clear()
    yield
    _original_paths.clear()  # Clean up after test


def test_simple_path_sanitization(clear_original_paths):
    """Test sanitization of simple paths."""
    # Store mapping manually since sanitize_tool_name doesn't do it anymore
    original = "command.subcommand"
    sanitized = sanitize_tool_name(original)
    _original_paths[sanitized] = original

    assert sanitized == "command_subcommand"
    assert get_original_path(sanitized) == original


def test_path_with_existing_underscores(clear_original_paths):
    """Test sanitization of paths that already contain underscores."""
    # Store mapping manually
    original = "command.sub_command.action"
    sanitized = sanitize_tool_name(original)
    _original_paths[sanitized] = original

    assert sanitized == "command_sub_command_action"
    assert get_original_path(sanitized) == original


def test_path_with_special_characters(clear_original_paths):
    """Test sanitization of paths with special characters."""
    # Store mapping manually
    original = "command.sub-command.action!"
    sanitized = sanitize_tool_name(original)
    _original_paths[sanitized] = original

    assert sanitized == "command_sub_command_action_"
    assert get_original_path(sanitized) == original


def test_path_starting_with_number(clear_original_paths):
    """Test sanitization of paths that start with a number."""
    # Store mapping manually
    original = "1command.subcommand"
    sanitized = sanitize_tool_name(original)
    _original_paths[sanitized] = original

    assert sanitized == "tool_1command_subcommand"
    assert get_original_path(sanitized) == original


def test_fallback_to_sanitized_name(clear_original_paths):
    """
    Test that get_original_path falls back to the sanitized name if no mapping exists.
    """
    sanitized = "unknown_command"
    assert get_original_path(sanitized) == sanitized


def test_multiple_sanitizations(clear_original_paths):
    """Test that multiple sanitizations work correctly."""
    # First path
    original1 = "command.subcommand"
    sanitized1 = sanitize_tool_name(original1)
    _original_paths[sanitized1] = original1

    # Second path
    original2 = "another.sub_command"
    sanitized2 = sanitize_tool_name(original2)
    _original_paths[sanitized2] = original2

    assert sanitized1 == "command_subcommand"
    assert get_original_path(sanitized1) == original1

    assert sanitized2 == "another_sub_command"
    assert get_original_path(sanitized2) == original2


def test_scan_click_command_mapping():
    """Test that scan_click_command correctly maps sanitized names to original paths."""
    import click

    from click_mcp.scanner import scan_click_command

    # Create a simple Click command group with nested commands
    @click.group()
    def cli():
        pass

    @cli.command()
    def simple():
        pass

    @cli.group()
    def nested():
        pass

    @nested.command()
    def command():
        pass

    @nested.command(name="with-dash")
    def with_dash():
        pass

    @nested.command(name="under_score")
    def under_score():
        pass

    # Clear the mapping before scanning
    _original_paths.clear()

    # Scan the command group
    scan_click_command(cli)

    # Check that the mapping contains the expected entries
    assert "simple" in _original_paths.values()
    assert "nested.command" in _original_paths.values()
    assert "nested.with-dash" in _original_paths.values()
    assert "nested.under_score" in _original_paths.values()

    # Check that the sanitized names map to the correct original paths
    for sanitized, original in _original_paths.items():
        if original == "nested.with-dash":
            assert sanitized == "nested_with_dash"
        elif original == "nested.under_score":
            assert sanitized == "nested_under_score"
        elif original == "nested.command":
            assert sanitized == "nested_command"

"""
click-mcp: Add MCP support to Click applications.
"""

from importlib.metadata import PackageNotFoundError, version

from .adapter import ToolAdapter
from .decorator import click_mcp
from .hooks import ToolCompletion

try:
    __version__ = version("click-mcp")
except PackageNotFoundError:
    # Package is not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+unknown"

__all__ = ["click_mcp", "ToolAdapter", "ToolCompletion", "__version__"]

"""Opt-in structured input and output for generated tools."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolAdapter:
    """Translate MCP tool data at the boundary of a normal CLI invocation.

    The input schema replaces the generated schema when supplied. The input
    adapter returns values keyed by Click parameter name for normal CLI parsing.
    The result adapter receives the command return value and produces a JSON
    object for MCP structured content.
    """

    input_schema: dict[str, Any] | None = None
    adapt_arguments: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    adapt_result: Callable[[Any], dict[str, Any]] | None = None

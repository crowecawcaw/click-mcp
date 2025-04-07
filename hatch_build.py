"""
Custom build hook for Hatch to run tests and linting before building.
"""
import os
import subprocess
import sys
from typing import Any, Dict


def run_command(cmd: str) -> int:
    """Run a command and return its exit code."""
    print(f"Running: {cmd}")
    return subprocess.call(cmd, shell=True)


def build_hook(directory: str, **_: Dict[str, Any]) -> None:
    """
    Run tests and linting before building.
    
    This hook is called by Hatch before building the package.
    """
    print("Running pre-build checks...")
    
    # Format code with black
    if run_command("hatch run lint:format") != 0:
        sys.exit("Code formatting failed")
    
    # Run linting checks
    if run_command("hatch run lint:check") != 0:
        sys.exit("Linting failed")
    
    # Run tests
    if run_command("hatch run test:cov") != 0:
        sys.exit("Tests failed")
    
    print("All pre-build checks passed!")

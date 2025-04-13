"""
Setup script for click-mcp.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="click-mcp",
    version="0.1.0",
    author="Stephen Crowe",
    description="Extend Click applications with Model Context Protocol (MCP) support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/crowecawcaw/click-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=7.0",
    ],
)

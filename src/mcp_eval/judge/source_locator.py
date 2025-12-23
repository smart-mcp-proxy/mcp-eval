"""Source locator for finding tool definitions in mcpproxy-go source.

This module provides utilities to locate tool definitions in the mcpproxy-go
codebase, enabling AI agents to make precise edits to tool descriptions.
"""

import os
import re
from pathlib import Path
from typing import Optional

from mcp_eval.judge.models import SourceLocation


# Default path to mcpproxy-go source, configurable via environment variable
MCPPROXY_SOURCE_PATH = os.getenv("MCPPROXY_SOURCE_PATH", "../mcpproxy-go")


def get_mcpproxy_source_path() -> Path:
    """Get the configured mcpproxy-go source path.

    Returns:
        Path to mcpproxy-go source directory.
    """
    return Path(MCPPROXY_SOURCE_PATH).resolve()


def is_source_accessible() -> bool:
    """Check if mcpproxy-go source is accessible.

    Returns:
        True if source directory exists and is readable.
    """
    source_path = get_mcpproxy_source_path()
    return source_path.exists() and source_path.is_dir()


def find_tool_definition(tool_name: str) -> Optional[SourceLocation]:
    """Locate a tool definition in mcpproxy-go source code.

    Searches for tool registration patterns in Go source files to find
    where a specific tool is defined.

    Args:
        tool_name: Full MCP tool name, e.g., "mcp__mcpproxy__retrieve_tools"

    Returns:
        SourceLocation with file path and line number if found, None otherwise.
    """
    source_path = get_mcpproxy_source_path()

    if not is_source_accessible():
        return SourceLocation(
            file_path="",
            line_number=None,
            accessible=False,
            search_pattern=tool_name,
        )

    # Extract the tool function name from MCP tool name
    # e.g., "mcp__mcpproxy__retrieve_tools" -> "retrieve_tools"
    parts = tool_name.split("__")
    if len(parts) >= 3:
        tool_function = parts[-1]  # Last part is usually the function name
    else:
        tool_function = tool_name

    # Search patterns for Go tool definitions
    search_patterns = [
        # Pattern for tool name in struct definition
        rf'Name:\s*["\'].*{re.escape(tool_function)}["\']',
        # Pattern for tool description
        rf'Description:\s*["\'].*{re.escape(tool_function)}',
        # Pattern for function definition
        rf'func.*{re.escape(tool_function.title().replace("_", ""))}',
        # Pattern for const or var with tool name
        rf'(const|var)\s+.*{re.escape(tool_function)}.*=',
    ]

    # Search in common locations for tool definitions
    search_dirs = [
        source_path / "internal" / "tools",
        source_path / "internal" / "mcp",
        source_path / "pkg" / "tools",
        source_path / "cmd",
        source_path,
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Search all Go files
        for go_file in search_dir.rglob("*.go"):
            result = _search_file_for_tool(go_file, search_patterns, tool_function, source_path)
            if result:
                return result

    # Tool not found but source is accessible
    return SourceLocation(
        file_path="",
        line_number=None,
        accessible=True,
        search_pattern=tool_function,
    )


def _search_file_for_tool(
    file_path: Path,
    patterns: list[str],
    tool_function: str,
    source_root: Path,
) -> Optional[SourceLocation]:
    """Search a single file for tool definition patterns.

    Args:
        file_path: Path to Go source file.
        patterns: List of regex patterns to search for.
        tool_function: Tool function name for reference.
        source_root: Root path of mcpproxy-go source.

    Returns:
        SourceLocation if found, None otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for pattern in patterns:
            for line_num, line in enumerate(lines, start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    relative_path = str(file_path.relative_to(source_root))
                    return SourceLocation(
                        file_path=relative_path,
                        line_number=line_num,
                        accessible=True,
                        search_pattern=tool_function,
                    )
    except (OSError, UnicodeDecodeError):
        pass

    return None


def validate_source_location(location: SourceLocation) -> bool:
    """Validate that a source location is still accurate.

    Args:
        location: SourceLocation to validate.

    Returns:
        True if file exists and is readable at the specified path.
    """
    if not location.accessible or not location.file_path:
        return False

    source_path = get_mcpproxy_source_path()
    file_path = source_path / location.file_path

    return file_path.exists() and file_path.is_file()


def get_source_context(location: SourceLocation, context_lines: int = 5) -> Optional[str]:
    """Get source code context around a location.

    Args:
        location: SourceLocation to get context for.
        context_lines: Number of lines before and after to include.

    Returns:
        Source code snippet with context, or None if not accessible.
    """
    if not validate_source_location(location) or location.line_number is None:
        return None

    source_path = get_mcpproxy_source_path()
    file_path = source_path / location.file_path

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        start = max(0, location.line_number - 1 - context_lines)
        end = min(len(lines), location.line_number + context_lines)

        context_lines_list = []
        for i in range(start, end):
            line_num = i + 1
            prefix = ">>> " if line_num == location.line_number else "    "
            context_lines_list.append(f"{prefix}{line_num:4d} | {lines[i]}")

        return "\n".join(context_lines_list)
    except (OSError, UnicodeDecodeError):
        return None

"""MCP Evaluation Utility - A tool for evaluating MCP server effectiveness."""

from mcp_eval.summary_models import (
    ScenarioExecutionSummary,
    ScenarioStatus,
    TestRunSummary,
)

__version__ = "0.1.0"
__author__ = "Claude Code Assistant"
__description__ = "Command-line utility to evaluate MCP servers and tools effectiveness"

__all__ = [
    "ScenarioExecutionSummary",
    "ScenarioStatus",
    "TestRunSummary",
]
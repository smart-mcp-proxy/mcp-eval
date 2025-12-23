"""Judge Agent module for TextGrad-style feedback loop analysis.

This module provides LLM-based analysis of baseline and comparison reports
to identify improvement opportunities for MCP tool descriptions.
"""

from mcp_eval.judge.models import (
    AnalysisType,
    ImprovementAspect,
    ImprovementPriority,
    SuggestionStatus,
    SourceLocation,
    EvidenceItem,
    ImprovementSuggestion,
    JudgeAssessment,
    ToolStateSnapshot,
    FeedbackLoopIteration,
)
from mcp_eval.judge.agent import JudgeAgent
from mcp_eval.judge.source_locator import find_tool_definition
from mcp_eval.judge.reporter import save_assessment_json, generate_markdown_report

__all__ = [
    # Enums
    "AnalysisType",
    "ImprovementAspect",
    "ImprovementPriority",
    "SuggestionStatus",
    # Models
    "SourceLocation",
    "EvidenceItem",
    "ImprovementSuggestion",
    "JudgeAssessment",
    "ToolStateSnapshot",
    "FeedbackLoopIteration",
    # Agent
    "JudgeAgent",
    # Source locator
    "find_tool_definition",
    # Reporter
    "save_assessment_json",
    "generate_markdown_report",
]

"""Data models for aggregated test summary reports.

This module defines Pydantic models for collecting and validating scenario execution
metadata during multi-scenario test runs.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ScenarioStatus(str, Enum):
    """Execution outcome classification for individual scenarios."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    RECORDED = "RECORDED"
    ERROR = "ERROR"


class ScenarioExecutionSummary(BaseModel):
    """Metadata for one scenario execution, displayed as a single row in summary report."""

    scenario_name: str = Field(..., min_length=1, description="Scenario filename without extension")
    scenario_path: str = Field(..., min_length=1, description="Relative path from scenarios/ root")
    user_intent: str = Field(default="", description="Short description of user goal")
    status: ScenarioStatus = Field(..., description="Execution outcome")
    tool_count: int = Field(..., ge=0, description="Number of MCP tools invoked")
    duration_seconds: float = Field(..., gt=0.0, description="Execution time in seconds")
    detailed_report_path: str = Field(..., pattern=r".*\.html$", description="Relative path to detailed HTML report")
    similarity_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Trajectory similarity score if comparison performed"
    )


class TestRunSummary(BaseModel):
    """Aggregated data for entire multi-scenario test run."""

    test_run_timestamp: datetime = Field(..., description="When test run started")
    total_scenarios: int = Field(..., gt=0, description="Total number of scenarios executed")
    passed_count: int = Field(..., ge=0, description="Count of PASSED scenarios")
    failed_count: int = Field(..., ge=0, description="Count of FAILED scenarios")
    recorded_count: int = Field(..., ge=0, description="Count of RECORDED scenarios")
    error_count: int = Field(..., ge=0, description="Count of ERROR scenarios")
    scenario_summaries: List[ScenarioExecutionSummary] = Field(..., min_length=1, description="Ordered list of scenario results")
    mcp_config_path: Optional[str] = Field(default=None, description="Path to MCP servers config file if specified")
    git_hash: Optional[str] = Field(default=None, min_length=8, max_length=8, description="Git commit hash (8 characters)")

    @field_validator("total_scenarios")
    @classmethod
    def total_matches_summaries(cls, v: int, info) -> int:
        """Validate total_scenarios equals length of scenario_summaries."""
        data = info.data
        if "scenario_summaries" in data and v != len(data["scenario_summaries"]):
            raise ValueError("total_scenarios must equal len(scenario_summaries)")
        return v

    @model_validator(mode='after')
    def counts_sum_to_total(self) -> 'TestRunSummary':
        """Validate status counts sum to total_scenarios."""
        total = self.passed_count + self.failed_count + self.recorded_count + self.error_count
        if total != self.total_scenarios:
            raise ValueError(
                f"Status counts ({total}) must sum to total_scenarios ({self.total_scenarios})"
            )
        return self

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        return (self.passed_count / self.total_scenarios) * 100 if self.total_scenarios > 0 else 0.0

    @property
    def total_duration(self) -> float:
        """Calculate total execution time across all scenarios."""
        return sum(s.duration_seconds for s in self.scenario_summaries)


class ToolSummary(BaseModel):
    """Minimal tool call summary for compact reports.

    Used in CompactSummary to represent a single tool call without
    full details, keeping token count under 500 for AI agent consumption.
    """

    name: str = Field(..., max_length=40, description="Tool name (truncated to 40 chars)")
    status: str = Field(..., pattern=r"^(OK|ERROR|TIMEOUT)$", description="Execution status")

    def format_line(self, prefix: str = "[AGENT]") -> str:
        """Format as single line for compact report.

        Args:
            prefix: Badge prefix, e.g., "[AGENT]" or "[CTRL]"

        Returns:
            Formatted line like "[AGENT] tool_name -> OK"
        """
        return f"{prefix} {self.name} -> {self.status}"


class CompactSummary(BaseModel):
    """Token-efficient summary report for AI agent consumption.

    Designed to be under 500 tokens for typical scenarios, parseable
    by AI agents, with clear visual distinction between control and
    agent tool calls.

    Format:
        # Scenario: <name>
        Status: PASSED | Score: 0.95

        ## Tool Calls
        [AGENT] mcp__mcpproxy__upstream_servers(add) -> OK
        [CTRL] api_v1_servers_id_unquarantine(server) -> OK

        ## Errors
        None
    """

    scenario_name: str = Field(..., description="Scenario name")
    status: str = Field(..., pattern=r"^(PASSED|FAILED|ERROR)$", description="Overall status")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Trajectory similarity score")
    agent_tools: List[ToolSummary] = Field(default_factory=list, description="Agent MCP tool calls")
    control_tools: List[ToolSummary] = Field(default_factory=list, description="Control MCP tool calls")
    errors: List[str] = Field(default_factory=list, description="Error messages (truncated to 100 chars)")

    @field_validator("errors")
    @classmethod
    def truncate_errors(cls, v: List[str]) -> List[str]:
        """Truncate error messages to 100 characters."""
        return [e[:100] + "..." if len(e) > 100 else e for e in v]

    def to_text(self) -> str:
        """Generate compact text report.

        Returns:
            Multi-line text suitable for AI agent parsing,
            designed to be under 500 tokens.
        """
        lines = [
            f"# Scenario: {self.scenario_name}",
            f"Status: {self.status} | Score: {self.similarity_score:.2f}",
            "",
            "## Tool Calls",
        ]

        if not self.agent_tools and not self.control_tools:
            lines.append("None")
        else:
            for tool in self.agent_tools:
                lines.append(tool.format_line("[AGENT]"))
            for tool in self.control_tools:
                lines.append(tool.format_line("[CTRL]"))

        lines.append("")
        lines.append("## Errors")
        if not self.errors:
            lines.append("None")
        else:
            for error in self.errors:
                lines.append(f"- {error}")

        return "\n".join(lines)

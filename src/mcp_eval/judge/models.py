"""Pydantic models for Judge Agent with TextGrad-style feedback loop.

This module defines data models for:
- Judge assessments (analysis results)
- Improvement suggestions (proposed changes to tool descriptions)
- Evidence items (supporting data for suggestions)
- Source locations (mcpproxy-go file references)
- Tool state snapshots (versioning and rollback)
- Feedback loop iterations (tracking improvement cycles)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisType(str, Enum):
    """Type of judge analysis performed."""

    BASELINE = "baseline"  # Analyzing a baseline trajectory for optimality
    COMPARISON = "comparison"  # Analyzing comparison report for divergence causes


class ImprovementAspect(str, Enum):
    """Aspect of tool definition being improved."""

    DESCRIPTION = "description"  # Main tool description
    PARAMETER_DESCRIPTION = "parameter_description"  # Description of a specific parameter
    EXAMPLE_VALUES = "example_values"  # Example values in documentation
    RETURN_SCHEMA = "return_schema"  # Return type documentation
    ERROR_MESSAGES = "error_messages"  # Error message clarity


class ImprovementPriority(str, Enum):
    """Priority level for improvement suggestions."""

    CRITICAL = "critical"  # Blocking multiple scenarios, immediate fix needed
    HIGH = "high"  # Significant score impact, should fix soon
    MEDIUM = "medium"  # Moderate improvement, schedule for next iteration
    LOW = "low"  # Minor refinement, nice to have


class SuggestionStatus(str, Enum):
    """Workflow status for improvement suggestions."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved by human/agent, ready to apply
    REJECTED = "rejected"  # Rejected, won't be applied
    APPLIED = "applied"  # Applied to mcpproxy source
    ROLLED_BACK = "rolled_back"  # Applied then reverted


class SourceLocation(BaseModel):
    """Location of tool definition in mcpproxy-go source code.

    Enables AI agents to locate and edit tool definitions directly.
    """

    file_path: str = Field(..., description="Relative path from mcpproxy-go root")
    line_number: Optional[int] = Field(default=None, ge=1, description="Line number where definition starts")
    accessible: bool = Field(..., description="Whether file exists and is readable")
    search_pattern: Optional[str] = Field(default=None, description="Pattern used to locate definition")


class EvidenceItem(BaseModel):
    """Supporting data from evaluation that justifies a suggestion.

    Captures specific invocations where tool behavior was suboptimal.
    """

    scenario_name: str = Field(..., min_length=1, description="Name of scenario providing evidence")
    invocation_index: int = Field(..., ge=0, description="Which tool call (0-indexed)")
    expected_behavior: str = Field(..., min_length=1, description="What was expected")
    actual_behavior: str = Field(..., min_length=1, description="What actually happened")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Score for this invocation")
    tool_call_details: Dict[str, Any] = Field(..., description="Full tool call data (name, input, output)")


class ImprovementSuggestion(BaseModel):
    """Specific proposed change to a tool definition.

    The 'gradient' in TextGrad terminology - represents feedback for
    improving tool descriptions to achieve better agent behavior.
    """

    id: str = Field(..., pattern=r"^judge_[a-z0-9]+_sug_\d+$", description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    tool_name: str = Field(..., min_length=1, description="Full MCP tool name, e.g., mcp__mcpproxy__retrieve_tools")
    aspect: ImprovementAspect = Field(..., description="Which aspect of tool to improve")
    parameter_name: Optional[str] = Field(default=None, description="If aspect targets specific parameter")
    source_location: Optional[SourceLocation] = Field(default=None, description="File location in mcpproxy-go source")
    current_value: str = Field(..., min_length=1, description="Current tool description/config")
    proposed_value: str = Field(..., min_length=1, description="Improved description/config")
    rationale: str = Field(..., min_length=50, description="Explanation of why change improves behavior")
    chain_of_thought: Optional[List[str]] = Field(default=None, description="Step-by-step reasoning")
    priority: ImprovementPriority = Field(..., description="Urgency of the improvement")
    expected_score_improvement: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Estimated score delta"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in suggestion")
    evidence: List[EvidenceItem] = Field(..., min_length=1, description="Supporting data")
    affected_scenarios: Optional[List[str]] = Field(default=None, description="List of scenarios this would impact")
    status: SuggestionStatus = Field(default=SuggestionStatus.PENDING, description="Workflow status")
    applied_at: Optional[datetime] = Field(default=None, description="When suggestion was applied")
    reviewer_notes: Optional[str] = Field(default=None, description="Human reviewer comments")

    @field_validator("proposed_value")
    @classmethod
    def proposed_differs_from_current(cls, v: str, info) -> str:
        """Ensure proposed value is different from current."""
        if "current_value" in info.data and v == info.data["current_value"]:
            raise ValueError("proposed_value must differ from current_value")
        return v


class JudgeAssessment(BaseModel):
    """Complete analysis for one scenario.

    Generated by JudgeAgent after analyzing a baseline or comparison report.
    Contains root cause analysis and improvement suggestions.
    """

    id: str = Field(..., pattern=r"^judge_[a-z0-9]+$", description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of analysis")
    scenario_name: str = Field(..., min_length=1, description="Name of analyzed scenario")
    analysis_type: AnalysisType = Field(..., description="Type of analysis performed")
    source_report_path: str = Field(..., min_length=1, description="Path to input report")
    original_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Similarity score if comparison"
    )
    root_cause_analysis: str = Field(..., min_length=100, description="Detailed explanation of issues found")
    failure_patterns: Optional[List[str]] = Field(default=None, description="Categorized patterns identified")
    improvement_suggestions: List[ImprovementSuggestion] = Field(
        default_factory=list, description="List of suggested changes"
    )
    judge_model: str = Field(..., min_length=1, description="LLM model used for analysis")
    judge_prompt_version: str = Field(default="v1.0", description="Version of prompt template used")
    duration_seconds: float = Field(..., gt=0.0, description="Time taken for analysis")

    @model_validator(mode="after")
    def validate_comparison_has_score(self) -> "JudgeAssessment":
        """Ensure comparison analyses have original_score."""
        if self.analysis_type == AnalysisType.COMPARISON and self.original_score is None:
            raise ValueError("original_score is required for comparison analysis")
        return self


class ToolStateSnapshot(BaseModel):
    """Snapshot of tool configuration for versioning and rollback.

    Captures tool state before/after improvements are applied.
    """

    tool_name: str = Field(..., min_length=1, description="Full MCP tool name")
    snapshot_at: datetime = Field(default_factory=datetime.utcnow, description="When snapshot was taken")
    description: str = Field(..., min_length=1, description="Tool description at snapshot time")
    parameters: Dict[str, Any] = Field(..., description="Parameter definitions")
    return_schema: Optional[Dict[str, Any]] = Field(default=None, description="Return type schema if applicable")
    source_file: Optional[str] = Field(default=None, description="mcpproxy-go source file")
    git_hash: Optional[str] = Field(default=None, min_length=7, max_length=40, description="Git commit hash")


class FeedbackLoopIteration(BaseModel):
    """Tracks one iteration of the feedback loop.

    Records before/after state for measuring improvement efficacy.
    """

    iteration_id: str = Field(..., pattern=r"^iter_\d{8}_\d{6}$", description="Unique identifier")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When iteration began")
    completed_at: Optional[datetime] = Field(default=None, description="When iteration finished")
    before_snapshot: ToolStateSnapshot = Field(..., description="Tool state before changes")
    before_scores: Dict[str, float] = Field(..., description="Scenario scores before (name -> score)")
    applied_suggestions: List[str] = Field(..., description="List of suggestion IDs applied")
    after_snapshot: Optional[ToolStateSnapshot] = Field(default=None, description="Tool state after changes")
    after_scores: Optional[Dict[str, float]] = Field(default=None, description="Scenario scores after")
    score_delta: Optional[float] = Field(default=None, description="Average improvement")
    success: bool = Field(default=False, description="Whether iteration improved scores")

    @model_validator(mode="after")
    def validate_completion(self) -> "FeedbackLoopIteration":
        """If completed, ensure after state is populated."""
        if self.completed_at is not None:
            if self.after_snapshot is None:
                raise ValueError("after_snapshot required when iteration is completed")
            if self.after_scores is None:
                raise ValueError("after_scores required when iteration is completed")
        return self

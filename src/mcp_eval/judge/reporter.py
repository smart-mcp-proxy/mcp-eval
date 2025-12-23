"""Reporter module for Judge Agent output.

This module provides functions to save JudgeAssessment results in
JSON and Markdown formats for both AI agent and human consumption.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp_eval.judge.models import (
    ImprovementPriority,
    ImprovementSuggestion,
    JudgeAssessment,
)


# Default output directories
DEFAULT_ASSESSMENTS_DIR = ".judge/assessments"
DEFAULT_REPORTS_DIR = "reports"


def ensure_directories() -> tuple[Path, Path]:
    """Ensure output directories exist.

    Returns:
        Tuple of (assessments_dir, reports_dir) paths.
    """
    assessments_dir = Path(DEFAULT_ASSESSMENTS_DIR)
    reports_dir = Path(DEFAULT_REPORTS_DIR)

    assessments_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    return assessments_dir, reports_dir


def save_assessment_json(
    assessment: JudgeAssessment,
    output_dir: Optional[Path] = None,
) -> Path:
    """Save JudgeAssessment to JSON file.

    Args:
        assessment: JudgeAssessment to save.
        output_dir: Optional output directory. Defaults to .judge/assessments/.

    Returns:
        Path to saved JSON file.
    """
    if output_dir is None:
        output_dir, _ = ensure_directories()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{assessment.id}.json"

    # Convert to dict with datetime serialization
    assessment_dict = assessment.model_dump(mode="json")

    with open(output_file, "w") as f:
        json.dump(assessment_dict, f, indent=2, default=str)

    return output_file


def generate_markdown_report(
    assessment: JudgeAssessment,
    output_dir: Optional[Path] = None,
) -> Path:
    """Generate Markdown report for human review.

    Args:
        assessment: JudgeAssessment to convert to Markdown.
        output_dir: Optional output directory. Defaults to reports/.

    Returns:
        Path to saved Markdown file.
    """
    if output_dir is None:
        _, output_dir = ensure_directories()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"judge_summary_{assessment.scenario_name}_{timestamp}.md"

    markdown = _build_markdown_content(assessment)

    with open(output_file, "w") as f:
        f.write(markdown)

    return output_file


def _build_markdown_content(assessment: JudgeAssessment) -> str:
    """Build Markdown content from JudgeAssessment.

    Args:
        assessment: JudgeAssessment to convert.

    Returns:
        Markdown string.
    """
    lines = [
        f"# Judge Assessment: {assessment.scenario_name}",
        "",
    ]

    # Header metadata
    score_text = f"{assessment.original_score:.2f}" if assessment.original_score is not None else "N/A"
    status = "FAIL" if assessment.original_score is not None and assessment.original_score < 0.8 else "PASS"

    lines.extend([
        f"**Score**: {score_text} ({status}) | **Analysis Time**: {assessment.duration_seconds:.1f}s | **Type**: {assessment.analysis_type.value}",
        "",
        f"**Model**: {assessment.judge_model} | **Prompt Version**: {assessment.judge_prompt_version}",
        "",
        "---",
        "",
    ])

    # Root Cause Analysis
    lines.extend([
        "## Root Cause",
        "",
        assessment.root_cause_analysis,
        "",
    ])

    # Failure Patterns
    if assessment.failure_patterns:
        lines.extend([
            "## Failure Patterns",
            "",
        ])
        for pattern in assessment.failure_patterns:
            lines.append(f"1. {pattern}")
        lines.append("")

    # Improvement Suggestions
    lines.extend([
        "## Improvement Suggestions",
        "",
    ])

    if not assessment.improvement_suggestions:
        lines.append("_No suggestions generated. Trajectory may already be optimal._")
    else:
        for i, suggestion in enumerate(assessment.improvement_suggestions, 1):
            lines.extend(_format_suggestion_markdown(suggestion, i))

    # Footer
    lines.extend([
        "",
        "---",
        "",
        f"_Generated at {assessment.created_at.isoformat()} by mcp-eval judge_",
    ])

    return "\n".join(lines)


def _format_suggestion_markdown(suggestion: ImprovementSuggestion, index: int) -> list[str]:
    """Format a single suggestion as Markdown.

    Args:
        suggestion: ImprovementSuggestion to format.
        index: Suggestion number.

    Returns:
        List of Markdown lines.
    """
    priority_emoji = {
        ImprovementPriority.CRITICAL: "🔴",
        ImprovementPriority.HIGH: "🟠",
        ImprovementPriority.MEDIUM: "🟡",
        ImprovementPriority.LOW: "🟢",
    }

    emoji = priority_emoji.get(suggestion.priority, "⚪")
    confidence_pct = int(suggestion.confidence * 100)

    lines = [
        f"### {index}. {suggestion.tool_name} ({emoji} {suggestion.priority.value.upper()}, {confidence_pct}% confidence)",
        "",
        f"**Aspect**: {suggestion.aspect.value}",
    ]

    if suggestion.source_location and suggestion.source_location.file_path:
        loc = suggestion.source_location
        line_info = f":{loc.line_number}" if loc.line_number else ""
        accessible = "✓" if loc.accessible else "✗"
        lines.append(f"**Source**: `{loc.file_path}{line_info}` ({accessible} accessible)")

    if suggestion.expected_score_improvement:
        lines.append(f"**Expected Improvement**: +{suggestion.expected_score_improvement:.2f}")

    lines.extend([
        "",
        "**Current**:",
        f"> {suggestion.current_value}",
        "",
        "**Proposed**:",
        f"> {suggestion.proposed_value}",
        "",
        "**Rationale**:",
        suggestion.rationale,
        "",
    ])

    # Chain of thought
    if suggestion.chain_of_thought:
        lines.extend([
            "**Reasoning**:",
        ])
        for step in suggestion.chain_of_thought:
            lines.append(f"- {step}")
        lines.append("")

    # Evidence
    if suggestion.evidence:
        lines.extend([
            "**Evidence**:",
        ])
        for ev in suggestion.evidence:
            lines.append(f"- Invocation {ev.invocation_index}: Expected \"{ev.expected_behavior}\", got \"{ev.actual_behavior}\" (score: {ev.similarity_score:.2f})")
        lines.append("")

    # Affected scenarios
    if suggestion.affected_scenarios:
        lines.append(f"**Also affects**: {', '.join(suggestion.affected_scenarios)}")
        lines.append("")

    return lines


def generate_batch_summary_markdown(
    assessments: list[JudgeAssessment],
    output_dir: Optional[Path] = None,
) -> Path:
    """Generate summary Markdown for multiple assessments.

    Args:
        assessments: List of JudgeAssessments to summarize.
        output_dir: Optional output directory.

    Returns:
        Path to saved Markdown file.
    """
    if output_dir is None:
        _, output_dir = ensure_directories()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"judge_batch_summary_{timestamp}.md"

    lines = [
        "# Judge Batch Analysis Summary",
        "",
        f"**Total Scenarios**: {len(assessments)}",
        f"**Generated**: {datetime.now().isoformat()}",
        "",
        "---",
        "",
        "## Summary by Priority",
        "",
    ]

    # Count suggestions by priority
    priority_counts = {p: 0 for p in ImprovementPriority}
    total_suggestions = 0

    for assessment in assessments:
        for sug in assessment.improvement_suggestions:
            priority_counts[sug.priority] += 1
            total_suggestions += 1

    lines.extend([
        f"| Priority | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {priority_counts[ImprovementPriority.CRITICAL]} |",
        f"| 🟠 High | {priority_counts[ImprovementPriority.HIGH]} |",
        f"| 🟡 Medium | {priority_counts[ImprovementPriority.MEDIUM]} |",
        f"| 🟢 Low | {priority_counts[ImprovementPriority.LOW]} |",
        f"| **Total** | **{total_suggestions}** |",
        "",
        "---",
        "",
        "## Scenarios",
        "",
    ])

    # List scenarios
    for assessment in assessments:
        score_text = f"{assessment.original_score:.2f}" if assessment.original_score else "N/A"
        sug_count = len(assessment.improvement_suggestions)
        lines.append(f"- **{assessment.scenario_name}** (score: {score_text}) - {sug_count} suggestions")

    lines.extend([
        "",
        "---",
        "",
        "## All Suggestions",
        "",
    ])

    # Group suggestions by tool
    tools: dict[str, list[tuple[JudgeAssessment, ImprovementSuggestion]]] = {}
    for assessment in assessments:
        for sug in assessment.improvement_suggestions:
            if sug.tool_name not in tools:
                tools[sug.tool_name] = []
            tools[sug.tool_name].append((assessment, sug))

    for tool_name, suggestions in sorted(tools.items()):
        lines.extend([
            f"### {tool_name}",
            "",
        ])
        for assessment, sug in suggestions:
            priority_emoji = {
                ImprovementPriority.CRITICAL: "🔴",
                ImprovementPriority.HIGH: "🟠",
                ImprovementPriority.MEDIUM: "🟡",
                ImprovementPriority.LOW: "🟢",
            }
            emoji = priority_emoji.get(sug.priority, "⚪")
            lines.append(f"- {emoji} [{assessment.scenario_name}] {sug.aspect.value}: {sug.rationale[:80]}...")
        lines.append("")

    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    return output_file

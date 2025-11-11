# Data Model: Aggregated Test Reports

**Feature**: 004-aggregated-test-reports
**Date**: 2025-11-11

## Overview

This document defines the data structures for aggregated test summary reports. Models represent in-memory data collected during multi-scenario test runs and passed to HTML report generation functions.

## Core Entities

### ScenarioExecutionSummary

Represents minimal metadata for one scenario execution, displayed as a single row in the summary report table.

**Purpose**: Lightweight data structure collected after each scenario completes

**Fields**:
- `scenario_name: str` - Scenario filename without extension (e.g., "add_simple_server")
- `scenario_path: str` - Relative path from scenarios/ root including subdirectories (e.g., "tool_management/add_simple_server")
- `user_intent: str` - Short description of what user wanted to accomplish (from YAML `user_intent` field)
- `status: ScenarioStatus` - Execution outcome enum: PASSED, FAILED, RECORDED, ERROR
- `tool_count: int` - Number of MCP tools invoked during execution
- `duration_seconds: float` - Execution time in seconds with decimal precision
- `detailed_report_path: str` - Relative file path to detailed HTML report (e.g., "add_simple_server_baseline_20251111_143147.html")
- `similarity_score: Optional[float]` - Trajectory similarity score (0.0-1.0) if comparison was performed, None if recorded

**Validation Rules**:
- `scenario_name` must not be empty
- `tool_count` must be ≥0
- `duration_seconds` must be >0.0
- `similarity_score` must be between 0.0 and 1.0 if present
- `detailed_report_path` must end with ".html"

**Relationships**:
- Child of `TestRunSummary` (many summaries per test run)
- No persistence - transient in-memory structure

---

### TestRunSummary

Represents aggregated data for entire multi-scenario test run, containing collection of scenario summaries and overall statistics.

**Purpose**: Top-level data structure passed to summary HTML generator

**Fields**:
- `test_run_timestamp: datetime` - When test run started (ISO-8601 format)
- `total_scenarios: int` - Total number of scenarios executed
- `passed_count: int` - Count of scenarios with status=PASSED
- `failed_count: int` - Count of scenarios with status=FAILED
- `recorded_count: int` - Count of scenarios with status=RECORDED
- `error_count: int` - Count of scenarios with status=ERROR
- `scenario_summaries: List[ScenarioExecutionSummary]` - Ordered list of scenario results
- `mcp_config_path: Optional[str]` - Path to MCP servers config file used (if specified)
- `git_hash: Optional[str]` - Git commit hash at time of test run (8 characters)

**Derived Fields** (calculated properties, not stored):
- `pass_rate: float` - `passed_count / total_scenarios` (percentage)
- `total_duration: float` - Sum of all `scenario_summaries[*].duration_seconds`

**Validation Rules**:
- `total_scenarios` must equal `len(scenario_summaries)`
- `passed_count + failed_count + recorded_count + error_count` must equal `total_scenarios`
- All counts must be ≥0
- `scenario_summaries` must not be empty (cannot generate summary for 0 scenarios)

**Relationships**:
- Parent of multiple `ScenarioExecutionSummary` instances
- No persistence - transient structure created by CLI, consumed by HTML generator

---

### ScenarioStatus (Enum)

Execution outcome classification for individual scenarios.

**Purpose**: Type-safe status values with consistent string representations

**Values**:
- `PASSED` - Scenario execution matched baseline with similarity score ≥ threshold
- `FAILED` - Scenario execution didn't match baseline or had assertion failures
- `RECORDED` - New baseline recorded (no existing baseline to compare against)
- `ERROR` - Scenario crashed with exception before completing execution

**String Representation**: Enum value names (e.g., "PASSED") used in HTML badges

**Color Mapping** (for HTML rendering):
- `PASSED` → `#28a745` (green)
- `FAILED` → `#dc3545` (red)
- `RECORDED` → `#007bff` (blue)
- `ERROR` → `#ffc107` (yellow)

---

## Data Flow

```
CLI Test Command
      ↓
Execute Scenario 1 → Create ScenarioExecutionSummary → Append to summaries list
Execute Scenario 2 → Create ScenarioExecutionSummary → Append to summaries list
Execute Scenario N → Create ScenarioExecutionSummary → Append to summaries list
      ↓
Calculate aggregate counts (passed/failed/recorded/error)
      ↓
Create TestRunSummary(scenario_summaries=summaries, counts=...)
      ↓
Pass TestRunSummary to generate_summary_report()
      ↓
Render HTML string with table rows from scenario_summaries
      ↓
Write HTML to reports/test_summary_TIMESTAMP.html
```

## Implementation Notes

### Pydantic Models

Implement as Pydantic `BaseModel` subclasses for:
- Automatic validation (field types, ranges, constraints)
- JSON serialization support (for future export features)
- Clear error messages when invalid data provided
- IDE autocomplete and type checking

Example:
```python
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from typing import List, Optional

class ScenarioStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    RECORDED = "RECORDED"
    ERROR = "ERROR"

class ScenarioExecutionSummary(BaseModel):
    scenario_name: str = Field(..., min_length=1)
    scenario_path: str = Field(..., min_length=1)
    user_intent: str = Field(default="")
    status: ScenarioStatus
    tool_count: int = Field(..., ge=0)
    duration_seconds: float = Field(..., gt=0.0)
    detailed_report_path: str = Field(..., pattern=r".*\.html$")
    similarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class TestRunSummary(BaseModel):
    test_run_timestamp: datetime
    total_scenarios: int = Field(..., gt=0)
    passed_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    recorded_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    scenario_summaries: List[ScenarioExecutionSummary] = Field(..., min_items=1)
    mcp_config_path: Optional[str] = None
    git_hash: Optional[str] = Field(default=None, max_length=8, min_length=8)

    @validator("total_scenarios")
    def total_matches_summaries(cls, v, values):
        if "scenario_summaries" in values and v != len(values["scenario_summaries"]):
            raise ValueError("total_scenarios must equal len(scenario_summaries)")
        return v

    @validator("passed_count")
    def counts_sum_to_total(cls, v, values):
        if "total_scenarios" in values:
            total = values.get("passed_count", 0) + values.get("failed_count", 0) + \
                    values.get("recorded_count", 0) + values.get("error_count", 0)
            if total != values["total_scenarios"]:
                raise ValueError("Status counts must sum to total_scenarios")
        return v

    @property
    def pass_rate(self) -> float:
        return (self.passed_count / self.total_scenarios) * 100 if self.total_scenarios > 0 else 0.0

    @property
    def total_duration(self) -> float:
        return sum(s.duration_seconds for s in self.scenario_summaries)
```

### Data Collection in CLI

Location: `src/mcp_eval/cli.py`

```python
# In test() command:
summaries: List[ScenarioExecutionSummary] = []

for scenario_file in scenario_files:
    # Execute scenario...
    result = execute_scenario(scenario_file)

    # Collect metadata
    summary = ScenarioExecutionSummary(
        scenario_name=scenario_file.stem,
        scenario_path=str(scenario_file.relative_to(scenarios_dir)),
        user_intent=scenario_yaml["user_intent"],
        status=result.status,
        tool_count=result.tool_call_count,
        duration_seconds=result.duration,
        detailed_report_path=result.html_report_filename,
        similarity_score=result.similarity_score
    )
    summaries.append(summary)

# After all scenarios complete
test_run = TestRunSummary(
    test_run_timestamp=run_start_time,
    total_scenarios=len(summaries),
    passed_count=sum(1 for s in summaries if s.status == ScenarioStatus.PASSED),
    failed_count=sum(1 for s in summaries if s.status == ScenarioStatus.FAILED),
    recorded_count=sum(1 for s in summaries if s.status == ScenarioStatus.RECORDED),
    error_count=sum(1 for s in summaries if s.status == ScenarioStatus.ERROR),
    scenario_summaries=summaries,
    mcp_config_path=mcp_config,
    git_hash=get_git_hash()
)

# Generate summary report
from mcp_eval.html_reporter import generate_summary_report
summary_html = generate_summary_report(test_run)
```

## Edge Cases

1. **Empty Intent**: If scenario YAML missing `user_intent`, use empty string (valid per model)
2. **Zero Tools**: Scenario with no tool calls has `tool_count=0` (valid, may indicate AI agent failure)
3. **Very Long Names**: Scenario names >100 chars truncated in HTML with tooltip (rendering concern, not data model)
4. **Duplicate Names**: Disambiguated by `scenario_path` including subdirectory
5. **Missing Similarity Score**: `similarity_score=None` for RECORDED status (no baseline comparison)
6. **Negative Duration**: Validation prevents this - `duration_seconds` must be >0.0

## Future Extensions

- **Tags**: Add `tags: List[str]` to `ScenarioExecutionSummary` for filtering
- **Error Details**: Add `error_message: Optional[str]` for ERROR status context
- **Baseline Metadata**: Add `baseline_timestamp: Optional[datetime]` for comparison tracking
- **Test Suite Name**: Add `suite_name: Optional[str]` to `TestRunSummary` for organization

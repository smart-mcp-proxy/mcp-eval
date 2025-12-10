# Data Model: Fix Trajectory Comparison Algorithm

**Feature**: 006-fix-comparison-algorithm
**Date**: 2025-11-11
**Status**: Complete

## Overview

This document defines the data structures and entities for the trajectory comparison algorithm enhancements. All models use Python Pydantic for validation and are stored as JSON/YAML files.

## Core Entities

### 1. Scenario Configuration (Extended)

**Source**: scenarios/*.yaml
**Format**: YAML
**Purpose**: Define test scenarios with optional similarity threshold configuration

```python
class ScenarioConfig(BaseModel):
    """Extended scenario configuration with similarity threshold."""
    enabled: bool = True
    name: str
    description: str
    config_file: str
    user_intent: str
    expected_trajectory: List[ExpectedToolCall]
    success_criteria: List[str]
    tags: List[str] = []
    similarity_threshold: Optional[float] = 0.8  # NEW FIELD

    @field_validator('similarity_threshold')
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> float:
        """Validate threshold is in valid range."""
        if v is None:
            return 0.8
        if not (0.0 <= v <= 1.0):
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v
```

**Example YAML**:
```yaml
name: "Debug Tool Search"
description: "User searches for email tools with debug explanations"
similarity_threshold: 0.6  # Optional: more lenient for search queries
user_intent: "Search for email tools and explain the scoring"
expected_trajectory:
  - action: "search_tools"
    tool: "mcp__mcpproxy__retrieve_tools"
    args:
      query: "email"
      debug: true
```

**Relationships**:
- One-to-one with Baseline Execution (baselines/{scenario}_baseline/)
- Validated against during baseline recording

---

### 2. Baseline Validation Result (New)

**Source**: Generated during `mcp-eval record`
**Format**: In-memory, logged to console
**Purpose**: Report divergence between recorded baseline and expected trajectory

```python
class BaselineValidationResult(BaseModel):
    """Result of validating baseline against expected trajectory."""
    scenario_name: str
    overall_similarity: float  # 0.0-1.0
    validation_status: Literal["EXACT_MATCH", "MINOR_DIVERGENCE", "MAJOR_DIVERGENCE"]
    tool_call_comparisons: List[ToolCallComparison]
    warnings: List[str]
    timestamp: datetime

    @property
    def has_warnings(self) -> bool:
        """Check if validation found divergences."""
        return self.overall_similarity < 0.8
```

**Validation Status Rules**:
- `EXACT_MATCH`: overall_similarity == 1.0
- `MINOR_DIVERGENCE`: 0.8 <= overall_similarity < 1.0 (warning)
- `MAJOR_DIVERGENCE`: overall_similarity < 0.8 (strong warning)

**Example Console Output**:
```
⚠️  Baseline Validation Warning for "Debug Tool Search"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Similarity: 0.65 (MAJOR_DIVERGENCE)

Invocation 1: mcp__mcpproxy__retrieve_tools
  Expected: {"query": "email", "debug": true}
  Recorded: {"query": "email tools send receive manage messages", "debug": true, "limit": 10}

  Parameter Differences:
    • query: 0.40 similarity (expected: "email", recorded: "email tools send receive...")
    • debug: 1.00 similarity (exact match)
    • limit: missing in expected, present in recorded

⚠️  Recommendation: Review baseline divergence. Consider:
    1. Updating expected_trajectory in YAML to match recorded behavior
    2. Re-recording baseline if AI agent behavior is incorrect
    3. Adjusting scenario user_intent to be more specific
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 3. Tool Call Comparison (Enhanced)

**Source**: Generated during similarity calculations
**Format**: Python dataclass / Pydantic model
**Purpose**: Detailed parameter-level similarity breakdown

```python
class ParameterComparison(BaseModel):
    """Comparison of a single parameter between two tool calls."""
    parameter_name: str
    expected_value: Optional[Any]
    actual_value: Optional[Any]
    similarity_score: float  # 0.0-1.0
    comparison_method: Literal["exact", "jaccard", "cosine", "missing"]
    weight: float = 1.0  # Parameter importance weight

    @property
    def is_exact_match(self) -> bool:
        return self.similarity_score == 1.0

    @property
    def is_missing(self) -> bool:
        return self.expected_value is None or self.actual_value is None


class ToolCallComparison(BaseModel):
    """Detailed comparison between expected and actual tool calls."""
    invocation_number: int
    tool_name_expected: str
    tool_name_actual: str
    tool_name_match: bool
    parameter_comparisons: List[ParameterComparison]
    overall_similarity: float
    weighted_similarity: float  # Considering parameter weights

    @property
    def critical_params_match(self) -> bool:
        """Check if high-weight params (tool_name, query) match well."""
        critical = [p for p in self.parameter_comparisons if p.weight > 1.0]
        if not critical:
            return True
        return all(p.similarity_score >= 0.8 for p in critical)
```

**Parameter Weight Definitions**:
- `tool_name`: 2.0 (critical - wrong tool is major failure)
- `query`: 1.5 (important - query semantics matter)
- `operation`: 1.5 (important - affects behavior)
- `debug`, `limit`, `include_stats`: 1.0 (standard - optional parameters)
- All others: 1.0 (default weight)

---

### 4. Similarity Calculation Config (New)

**Source**: Hardcoded defaults, overridable per scenario
**Format**: Python config class
**Purpose**: Configure similarity algorithm behavior

```python
class SimilarityConfig(BaseModel):
    """Configuration for similarity calculations."""
    # Algorithm weights
    key_similarity_weight: float = 0.3
    value_similarity_weight: float = 0.7

    # Parameter-specific weights
    parameter_weights: Dict[str, float] = {
        "tool_name": 2.0,
        "query": 1.5,
        "operation": 1.5,
        "default": 1.0
    }

    # Missing parameter handling
    missing_param_score: float = 0.5  # Partial match, not complete failure

    # String comparison
    min_word_overlap_threshold: float = 0.3

    def get_parameter_weight(self, param_name: str) -> float:
        """Get weight for specific parameter."""
        return self.parameter_weights.get(param_name, self.parameter_weights["default"])
```

---

### 5. HTML Diff Configuration (New)

**Source**: Internal configuration
**Format**: Python config class
**Purpose**: Control HTML diff generation behavior

```python
class HtmlDiffConfig(BaseModel):
    """Configuration for HTML diff generation."""
    normalize_whitespace: bool = True
    normalize_dict_keys: bool = True  # Sort keys alphabetically
    normalize_json_format: bool = True  # Use consistent JSON formatting
    show_line_numbers: bool = True
    context_lines: int = 3  # Lines of context around differences

    # Character-level diff control
    enable_character_diff: bool = True
    highlight_whole_words: bool = False  # If True, highlight entire words not chars

    # Color scheme
    added_bg_color: str = "#c6f6d5"     # Green
    removed_bg_color: str = "#fed7d7"   # Red
    modified_bg_color: str = "#fef5e7"  # Yellow
    unchanged_bg_color: str = "#f8f9fa" # Gray
```

---

## Data Flow Diagrams

### Baseline Recording with Validation

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Load Scenario YAML                                       │
│    ├─ Parse expected_trajectory                             │
│    ├─ Parse similarity_threshold (default 0.8)              │
│    └─ Store for later validation                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Execute Dialog with AI Agent                             │
│    ├─ AI Agent makes tool calls                             │
│    ├─ Record to detailed_log.json                           │
│    └─ Generate tool_calls_summary                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Baseline Validation (NEW)                                │
│    ├─ Load expected_trajectory from scenario YAML           │
│    ├─ Load tool_calls_summary from execution                │
│    ├─ Calculate similarity for each tool call:              │
│    │  ├─ Tool name match (exact)                            │
│    │  ├─ Parameter key similarity (Jaccard)                 │
│    │  └─ Parameter value similarity (weighted)              │
│    ├─ Generate BaselineValidationResult                     │
│    └─ Display warnings if similarity < 0.8                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Save Baseline Files                                      │
│    ├─ baselines/{scenario}_baseline/detailed_log.json       │
│    ├─ baselines/{scenario}_baseline/trajectory.txt          │
│    └─ reports/{scenario}_baseline_{timestamp}.html          │
└─────────────────────────────────────────────────────────────┘
```

### Comparison with Configurable Threshold

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Load Scenario + Baseline                                 │
│    ├─ Parse similarity_threshold from YAML (NEW)            │
│    ├─ Load baseline detailed_log.json                       │
│    └─ Extract baseline tool_calls_summary                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Execute Current Run                                      │
│    └─ Generate current tool_calls_summary                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Similarity Calculation (ENHANCED)                        │
│    ├─ Use configured threshold for pass/fail                │
│    ├─ Calculate per-invocation similarity                   │
│    ├─ Apply parameter weighting                             │
│    ├─ Generate ToolCallComparison objects                   │
│    └─ Produce overall similarity score                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pass/Fail Determination                                  │
│    ├─ Compare: overall_similarity >= threshold              │
│    ├─ Status: PASS if true, FAIL if false                   │
│    └─ Include threshold in comparison result                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Generate Reports                                         │
│    ├─ comparison_results/{scenario}_comparison.json         │
│    │  └─ Include configured threshold                       │
│    └─ reports/{scenario}_comparison_{timestamp}.html        │
│       ├─ Normalized diff (no false highlights)              │
│       ├─ Show configured threshold                          │
│       └─ Per-parameter similarity breakdown                 │
└─────────────────────────────────────────────────────────────┘
```

## State Transitions

### Baseline Validation Status

```
┌──────────────┐
│ NOT_EXECUTED │
└──────┬───────┘
       │ Execute baseline recording
       ▼
┌──────────────┐
│  VALIDATING  │
└──────┬───────┘
       │ Calculate similarity
       ▼
       ┌─────────────────────┐
       │ similarity == 1.0?  │
       └┬───────────────────┬┘
        │ Yes               │ No
        ▼                   ▼
┌──────────────┐    ┌─────────────────────────┐
│ EXACT_MATCH  │    │ similarity >= 0.8?      │
└──────────────┘    └┬───────────────────────┬┘
                     │ Yes                   │ No
                     ▼                       ▼
             ┌─────────────────┐    ┌──────────────────┐
             │MINOR_DIVERGENCE │    │ MAJOR_DIVERGENCE │
             └─────────────────┘    └──────────────────┘
                     │                       │
                     └───────────┬───────────┘
                                 │ Display warnings
                                 ▼
                         ┌──────────────┐
                         │   RECORDED   │
                         └──────────────┘
```

## File Structure Changes

### Before (Current)

```
baselines/debug_tool_search_baseline/
├── detailed_log.json         # Contains expected_trajectory as metadata only
└── trajectory.txt             # Human-readable, not validated

scenarios/debug_tool_search.yaml  # expected_trajectory never compared
```

### After (With Validation)

```
baselines/debug_tool_search_baseline/
├── detailed_log.json         # Contains expected_trajectory + validation_result (NEW)
└── trajectory.txt             # Unchanged

scenarios/debug_tool_search.yaml  # similarity_threshold: 0.6 (NEW FIELD)
```

**detailed_log.json Schema Extension**:
```json
{
  "scenario": "Debug Tool Search",
  "expected_trajectory": [...],
  "tool_calls_summary": [...],
  "baseline_validation": {              // NEW SECTION
    "overall_similarity": 0.65,
    "validation_status": "MAJOR_DIVERGENCE",
    "warnings": [
      "Tool call 1: query parameter diverged (0.40 similarity)"
    ],
    "validated_at": "2025-11-11T15:55:22Z"
  }
}
```

## Validation Rules

### Baseline Recording

1. **MUST validate** tool_calls_summary against expected_trajectory
2. **MUST display warnings** if overall_similarity < 0.8
3. **MUST NOT block** recording (warnings only)
4. **MUST save** validation result in detailed_log.json

### Comparison Evaluation

1. **MUST load** threshold from scenario YAML (default 0.8)
2. **MUST compare** current execution vs baseline (NOT vs expected_trajectory)
3. **MUST apply** threshold for pass/fail determination
4. **MUST display** configured threshold in console and HTML reports

### HTML Diff Generation

1. **MUST normalize** dictionary keys (alphabetical order)
2. **MUST normalize** JSON formatting (consistent indentation)
3. **MUST NOT highlight** visually identical strings
4. **MUST distinguish** between added (green), removed (red), and modified (yellow) content

## Implementation Notes

- All Pydantic models go in existing files (no new modules)
- Validation logic in scenario_runner.py (post-execution hook)
- Enhanced similarity calculation in similarity.py (extend existing functions)
- HTML normalization in html_reporter.py (pre-processing before difflib)
- Threshold handling in evaluator.py (pass threshold to comparison logic)

## Backward Compatibility

✅ **Existing baselines remain valid** - validation is optional metadata
✅ **Existing scenarios work unchanged** - similarity_threshold defaults to 0.8
✅ **Existing reports still render** - no schema-breaking changes
✅ **CLI commands unchanged** - no new required arguments

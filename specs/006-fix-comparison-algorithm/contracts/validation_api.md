# Baseline Validation API Contract

**Module**: `src/mcp_eval/scenario_runner.py` (new validation functions)
**Purpose**: Validate recorded baselines against expected trajectories

## Public Functions

### validate_baseline_against_expected

Validate recorded baseline matches expected trajectory from scenario YAML.

**Signature**:
```python
def validate_baseline_against_expected(
    scenario_name: str,
    expected_trajectory: List[Dict[str, Any]],
    actual_tool_calls: List[Dict[str, Any]],
    threshold: float = 0.8
) -> BaselineValidationResult:
    """Validate baseline execution against expected trajectory.

    Called after baseline recording completes. Compares tool_calls_summary
    (actual execution) against expected_trajectory (scenario YAML).

    Args:
        scenario_name: Name of the scenario
        expected_trajectory: List of expected tool calls from YAML
        actual_tool_calls: List of actual tool calls from execution
        threshold: Warning threshold (default 0.8)

    Returns:
        BaselineValidationResult with warnings if similarity < threshold

    Examples:
        >>> expected = [{"tool": "mcp__mcpproxy__retrieve_tools",
        ...              "args": {"query": "email", "debug": true}}]
        >>> actual = [{"tool_name": "mcp__mcpproxy__retrieve_tools",
        ...            "tool_input": {"query": "email tools", "debug": true, "limit": 10}}]
        >>> result = validate_baseline_against_expected("test", expected, actual)
        >>> result.validation_status
        'MAJOR_DIVERGENCE'  # similarity 0.65 < 0.8
        >>> len(result.warnings)
        1
    """
```

**Validation Steps**:
1. Check tool call count matches (warn if different)
2. For each tool call pair:
   - Convert expected format to tool call format
   - Calculate similarity using similarity.py
   - Store ToolCallComparison result
3. Calculate overall_similarity (average of all comparisons)
4. Determine validation_status based on threshold
5. Generate warnings for divergent parameters

**Validation Status**:
- `EXACT_MATCH`: overall_similarity == 1.0
- `MINOR_DIVERGENCE`: 0.8 <= overall_similarity < 1.0 (info warning)
- `MAJOR_DIVERGENCE`: overall_similarity < 0.8 (strong warning)

---

### display_validation_warnings

Display validation warnings to console using rich formatting.

**Signature**:
```python
def display_validation_warnings(
    result: BaselineValidationResult,
    verbose: bool = False
) -> None:
    """Display baseline validation warnings to console.

    Args:
        result: Validation result to display
        verbose: If True, show detailed parameter comparisons

    Output:
        Rich-formatted console output with:
        - Warning header with overall similarity
        - Per-invocation comparison details
        - Parameter-level differences (if verbose)
        - Recommendations for next steps
    """
```

**Console Output Format**:
```
⚠️  Baseline Validation Warning for "Debug Tool Search"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Similarity: 0.65 (MAJOR_DIVERGENCE)

Invocation 1: mcp__mcpproxy__retrieve_tools
  Expected: {"query": "email", "debug": true}
  Recorded: {"query": "email tools send receive manage messages",
             "debug": true, "limit": 10}

  Parameter Differences:
    • query: 0.40 similarity
      - Expected: "email"
      - Recorded: "email tools send receive manage messages"
    • debug: 1.00 similarity (exact match)
    • limit: missing in expected, present in recorded

⚠️  Recommendation: Review baseline divergence. Consider:
    1. Updating expected_trajectory in YAML to match recorded
    2. Re-recording baseline if AI behavior is incorrect
    3. Adjusting scenario user_intent to be more specific
```

---

## Data Models

### BaselineValidationResult

```python
@dataclass
class BaselineValidationResult:
    """Result of baseline validation."""
    scenario_name: str
    overall_similarity: float
    validation_status: Literal["EXACT_MATCH", "MINOR_DIVERGENCE", "MAJOR_DIVERGENCE"]
    tool_call_comparisons: List[ToolCallComparison]
    warnings: List[str]
    timestamp: datetime

    @property
    def has_warnings(self) -> bool:
        return self.overall_similarity < 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_name": self.scenario_name,
            "overall_similarity": self.overall_similarity,
            "validation_status": self.validation_status,
            "tool_call_comparisons": [c.to_dict() for c in self.tool_call_comparisons],
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }
```

### ToolCallComparison

```python
@dataclass
class ToolCallComparison:
    """Comparison between expected and actual tool call."""
    invocation_number: int
    tool_name_expected: str
    tool_name_actual: str
    tool_name_match: bool
    parameter_comparisons: List[ParameterComparison]
    overall_similarity: float
    weighted_similarity: float

    @property
    def has_divergence(self) -> bool:
        return self.overall_similarity < 0.8
```

---

## Integration Points

### scenario_runner.py Integration

```python
class FailureAwareScenarioRunner:
    async def execute_scenario(self, scenario_path, mode="evaluation"):
        # ... existing execution code ...

        # NEW: Validate baseline after recording
        if mode == "baseline":
            validation_result = validate_baseline_against_expected(
                scenario_name=scenario_data["name"],
                expected_trajectory=scenario_data["expected_trajectory"],
                actual_tool_calls=execution_log["tool_calls_summary"],
                threshold=scenario_data.get("similarity_threshold", 0.8)
            )

            # Save validation result in detailed_log.json
            execution_log["baseline_validation"] = validation_result.to_dict()

            # Display warnings to console
            if validation_result.has_warnings:
                display_validation_warnings(validation_result, verbose=True)

        return success, execution_log
```

### CLI Integration (cli.py)

```python
@cli.command()
@click.option('--scenario', required=True)
def record(scenario):
    """Record baseline with validation."""
    # ... existing code ...

    runner = FailureAwareScenarioRunner(...)
    success, execution_data = await runner.execute_scenario(scenario, mode="baseline")

    # Validation happens inside runner, warnings displayed automatically
    # Continue with normal baseline saving
```

---

## Error Handling

**Expected Trajectory Format Issues**:
- Missing `tool` field → skip validation for that call, log warning
- Missing `args` field → treat as empty dict
- Invalid YAML syntax → raise ValueError with clear message

**Execution Log Issues**:
- Missing `tool_calls_summary` → cannot validate, log error
- Empty tool calls list → warn if expected_trajectory not empty
- Malformed tool call dict → skip and log warning

**Never Block Recording**:
- Validation errors should log warnings but never prevent baseline from being saved
- Principle: Baseline becomes source of truth even if it diverges

---

## Performance Guarantees

- Validation time: <5s for typical scenario (1-10 tool calls)
- Memory usage: O(n*m) where n = tool calls, m = avg parameters per call
- No external dependencies
- Deterministic output (same inputs → same warnings)

---

## Testing Requirements

**Unit Tests**:
- Exact match scenario → no warnings
- Minor divergence (0.85 similarity) → info warning
- Major divergence (0.60 similarity) → strong warning
- Tool count mismatch → specific warning
- Missing expected_trajectory → graceful handling

**Integration Tests**:
- Full baseline recording flow with validation
- Warnings displayed to console correctly
- Validation result saved in detailed_log.json
- Baseline still saves despite warnings

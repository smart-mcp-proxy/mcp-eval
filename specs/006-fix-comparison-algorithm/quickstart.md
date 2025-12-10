# Quickstart: Fix Trajectory Comparison Algorithm

**Feature**: 006-fix-comparison-algorithm
**Date**: 2025-11-11
**For**: Developers implementing the trajectory comparison fixes

## Overview

This guide provides step-by-step instructions for implementing the baseline validation, improved similarity scoring, HTML diff normalization, and configurable thresholds.

## Implementation Checklist

### Phase 1: Similarity Algorithm Enhancements (P1 - User Story 2)

**File**: `src/mcp_eval/similarity.py`

- [ ] Add `SimilarityConfig` dataclass with parameter weights
- [ ] Add `normalize_parameters()` function for dict normalization
- [ ] Add `calculate_parameter_similarity()` for individual param comparison
- [ ] Enhance `calculate_tool_call_similarity()` with weighting logic
- [ ] Add parameter weight definitions (tool_name: 2.0, query: 1.5, etc.)
- [ ] Implement missing parameter handling (score 0.5 instead of 0.0)
- [ ] Add docstrings with examples for all public functions

**Test**: `tests/test_similarity.py` (20 test cases)
- [ ] Test identical calls → 1.0 score
- [ ] Test semantic equivalent queries → >= 0.9
- [ ] Test extra optional params → >= 0.8
- [ ] Test missing params → 0.5-0.7
- [ ] Test different tool names → 0.0
- [ ] Test nested JSON objects
- [ ] Test Unicode/special characters

**Success Criteria**: All similarity tests pass, debug_tool_search achieves >= 0.8 score

---

### Phase 2: Baseline Validation (P1 - User Story 1)

**File**: `src/mcp_eval/scenario_runner.py`

- [ ] Add `BaselineValidationResult` dataclass
- [ ] Add `ToolCallComparison` dataclass
- [ ] Add `validate_baseline_against_expected()` function
- [ ] Add `display_validation_warnings()` function with rich formatting
- [ ] Integrate validation into `FailureAwareScenarioRunner.execute_scenario()`
- [ ] Save validation result in detailed_log.json under "baseline_validation" key
- [ ] Add console output for warnings (⚠️ symbol, color-coded)

**Test**: `tests/test_baseline_validation.py` (15 test cases)
- [ ] Test exact match → EXACT_MATCH status, no warnings
- [ ] Test minor divergence → MINOR_DIVERGENCE, info warning
- [ ] Test major divergence → MAJOR_DIVERGENCE, strong warning
- [ ] Test tool count mismatch → specific warning
- [ ] Test missing expected_trajectory → graceful handling
- [ ] Test validation result saved in JSON
- [ ] Test warnings display with rich formatting

**Success Criteria**: Baseline recording shows warnings for debug_tool_search divergence

---

### Phase 3: HTML Diff Normalization (P2 - User Story 3)

**File**: `src/mcp_eval/html_reporter.py`

- [ ] Add `HtmlDiffConfig` dataclass
- [ ] Add `normalize_tool_call_content()` function
- [ ] Add `remove_false_highlights()` function
- [ ] Update `generate_normalized_dialog_diff()` to use normalization
- [ ] Add JSON parsing with fallback to AST literal_eval
- [ ] Implement key sorting and consistent JSON formatting
- [ ] Update HTML generation to use normalized content
- [ ] Test with debug_tool_search HTML report

**Test**: `tests/test_html_diff.py` (10 test cases)
- [ ] Test identical dicts different order → no highlights
- [ ] Test Python vs JSON format → no highlights
- [ ] Test actually different values → correct highlights
- [ ] Test nested objects → proper normalization
- [ ] Test malformed JSON → graceful fallback
- [ ] Visual regression test (compare rendered HTML)

**Success Criteria**: debug_tool_search HTML report shows no false yellow highlights

---

### Phase 4: Configurable Thresholds (P3 - User Story 4)

**Files**:
- Scenario schema: Extend pydantic model
- `src/mcp_eval/cli.py`: Pass threshold to evaluator
- `src/mcp_eval/evaluator.py`: Use threshold in pass/fail logic

**Changes**:
- [ ] Add `similarity_threshold: Optional[float] = 0.8` to scenario pydantic model
- [ ] Add threshold validation: 0.0 <= threshold <= 1.0
- [ ] Update `TrajectoryEvaluator.compare_executions()` to accept threshold param
- [ ] Update pass/fail determination to use configured threshold
- [ ] Display threshold in console output
- [ ] Display threshold in HTML comparison reports
- [ ] Update scenarios/debug_tool_search.yaml with `similarity_threshold: 0.6`

**Test**: `tests/test_threshold_config.py` (5+ test cases)
- [ ] Test default threshold (0.8)
- [ ] Test custom threshold from YAML
- [ ] Test threshold validation (reject invalid values)
- [ ] Test pass/fail at threshold boundary
- [ ] Test threshold displayed in reports

**Success Criteria**: debug_tool_search passes with threshold 0.6 configured

---

## Development Workflow

### Step 1: Set Up Test Environment

```bash
# Ensure you're on the feature branch
git checkout 006-fix-comparison-algorithm

# Create test fixtures directory
mkdir -p tests/fixtures

# Copy debug_tool_search files for testing
cp baselines/debug_tool_search_baseline/detailed_log.json tests/fixtures/
cp scenarios/debug_tool_search.yaml tests/fixtures/
```

### Step 2: Implement Phase by Phase

**Recommended Order**:
1. Phase 1 (Similarity) - Foundation for everything else
2. Phase 2 (Validation) - Catches baseline issues early
3. Phase 3 (HTML Diff) - Improves report quality
4. Phase 4 (Thresholds) - Enables flexible testing

**After Each Phase**:
```bash
# Run tests for the phase
pytest tests/test_similarity.py -v        # Phase 1
pytest tests/test_baseline_validation.py -v  # Phase 2
pytest tests/test_html_diff.py -v         # Phase 3
pytest tests/test_threshold_config.py -v  # Phase 4

# Run full test suite
pytest tests/ -v

# Verify with actual scenario
mcp-eval record --scenario scenarios/debug_tool_search.yaml  # Phases 1-2
mcp-eval compare --scenario scenarios/debug_tool_search.yaml \
  --baseline baselines/debug_tool_search_baseline/  # Phases 1-4
```

### Step 3: Manual Verification

**Verify Baseline Validation** (Phase 2):
```bash
# Record baseline - should show warnings
mcp-eval record --scenario scenarios/debug_tool_search.yaml

# Expected output:
# ⚠️  Baseline Validation Warning for "Debug Tool Search"
# Overall Similarity: 0.65 (MAJOR_DIVERGENCE)
# [... parameter differences ...]
```

**Verify HTML Diff** (Phase 3):
```bash
# Generate comparison report
mcp-eval compare --scenario scenarios/debug_tool_search.yaml \
  --baseline baselines/debug_tool_search_baseline/

# Open generated HTML report
open reports/debug_tool_search_comparison_*.html

# Verify:
# ✓ No yellow highlights on identical "include_stats" text
# ✓ Real differences still highlighted correctly
# ✓ Dialog turn sequence clear and readable
```

**Verify Threshold Configuration** (Phase 4):
```bash
# Update debug_tool_search.yaml to add:
# similarity_threshold: 0.6

# Run comparison again
mcp-eval compare --scenario scenarios/debug_tool_search.yaml \
  --baseline baselines/debug_tool_search_baseline/

# Expected output:
# ✅ PASS (similarity: 0.65, threshold: 0.6)
```

---

## Testing Strategy

### Unit Tests (50+ total)

Create test files with fixtures:

```python
# tests/test_similarity.py
import pytest
from mcp_eval.similarity import calculate_tool_call_similarity

def test_identical_calls():
    call1 = {
        "tool_name": "mcp__mcpproxy__retrieve_tools",
        "tool_input": {"query": "email", "debug": True}
    }
    call2 = call1.copy()
    assert calculate_tool_call_similarity(call1, call2) == 1.0

def test_semantic_equivalent_queries():
    call1 = {
        "tool_name": "mcp__mcpproxy__retrieve_tools",
        "tool_input": {"query": "email"}
    }
    call2 = {
        "tool_name": "mcp__mcpproxy__retrieve_tools",
        "tool_input": {"query": "email tools"}
    }
    similarity = calculate_tool_call_similarity(call1, call2)
    assert similarity >= 0.9  # High similarity for semantic equivalence

# ... 48 more tests ...
```

### Integration Tests

```bash
# Test full baseline recording flow
pytest tests/test_integration_baseline_recording.py -v

# Test full comparison flow
pytest tests/test_integration_comparison.py -v

# Test HTML report generation end-to-end
pytest tests/test_integration_html_reports.py -v
```

### Manual Acceptance Testing

Use the acceptance scenarios from spec.md:

**User Story 1 (Baseline Validation)**:
- [ ] Run record with debug_tool_search → warnings displayed
- [ ] Verify warnings show parameter differences
- [ ] Check detailed_log.json contains validation result

**User Story 2 (Similarity Scoring)**:
- [ ] Compare identical calls → score 1.0
- [ ] Compare semantic equivalent → score >= 0.9
- [ ] Compare with extra params → score >= 0.8

**User Story 3 (HTML Diff)**:
- [ ] Generate report with identical params → no false highlights
- [ ] Generate report with different values → correct highlights

**User Story 4 (Thresholds)**:
- [ ] Set threshold 1.0 → 0.95 fails
- [ ] Set threshold 0.8 → 0.85 passes
- [ ] Set threshold 0.6 → 0.65 passes

---

## Common Issues & Troubleshooting

### Issue: Similarity score still low after fixes

**Diagnosis**:
```python
# Add debug logging to similarity.py
def calculate_tool_call_similarity(call1, call2, config=None):
    print(f"Comparing tool calls:")
    print(f"  Call 1: {call1}")
    print(f"  Call 2: {call2}")
    # ... calculation ...
    print(f"  Final similarity: {similarity}")
    return similarity
```

**Solution**:
- Check parameter weights are applied correctly
- Verify normalization is working (print normalized dicts)
- Ensure missing params score 0.5, not 0.0

### Issue: False highlights still appearing in HTML

**Diagnosis**:
```bash
# Check normalized output
python -c "from mcp_eval.html_reporter import normalize_tool_call_content; \
  print(normalize_tool_call_content(\"{'debug': True, 'query': 'email'}\"))"
```

**Solution**:
- Verify JSON sorting is working (keys alphabetical)
- Check boolean conversion (True → true)
- Ensure consistent indentation (2 spaces)

### Issue: Baseline validation not showing warnings

**Diagnosis**:
```python
# Check if validation is being called
# Add breakpoint in scenario_runner.py:execute_scenario()
if mode == "baseline":
    print("Validation hook reached")  # Should print during record
```

**Solution**:
- Verify mode parameter is "baseline" not "evaluation"
- Check expected_trajectory is loaded from YAML correctly
- Ensure tool_calls_summary exists in execution_log

---

## Performance Benchmarks

**Target Performance** (from Technical Context):
- Baseline validation: <5s per scenario ✅
- Similarity calculation: <1s per tool call ✅
- HTML report generation: <5s for 20+ turns ✅

**Measure Performance**:
```python
import time

start = time.time()
result = validate_baseline_against_expected(...)
elapsed = time.time() - start
assert elapsed < 5.0, f"Validation took {elapsed}s, exceeds 5s limit"
```

---

## Documentation Updates

After implementation:

- [ ] Update CLAUDE.md with new validation workflow
- [ ] Update README.md with threshold configuration examples
- [ ] Add docstrings to all new public functions
- [ ] Update constitution if any architectural changes
- [ ] Create migration guide for existing baselines

---

## Definition of Done

✅ All 50+ unit tests pass
✅ debug_tool_search scenario passes with threshold 0.6
✅ Baseline recording shows validation warnings
✅ HTML reports have no false highlights
✅ Constitution check still passes (no violations)
✅ Performance benchmarks met
✅ Code reviewed and approved
✅ Documentation updated

---

## Next Steps After Implementation

1. Run `/speckit.tasks` to generate tasks.md
2. Follow tasks.md for detailed implementation steps
3. Create PR with spec.md, plan.md, and implementation
4. Update baselines if needed after approval

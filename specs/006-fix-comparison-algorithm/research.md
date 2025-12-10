# Research: Fix Trajectory Comparison Algorithm

**Feature**: 006-fix-comparison-algorithm
**Date**: 2025-11-11
**Status**: Complete

## Overview

This document consolidates research findings for fixing the trajectory comparison algorithm. All technical unknowns from the plan's Technical Context section have been resolved through codebase analysis.

## Research Questions Addressed

### 1. How does difflib generate HTML diffs and why is it producing false highlights?

**Investigation**:
- Reviewed Python's `difflib.HtmlDiff` class documentation and source code
- Analyzed current HTML report generation in `html_reporter.py`
- Examined the debug_tool_search HTML report showing false highlights

**Findings**:
- `difflib.HtmlDiff.make_table()` performs character-level diffing using `difflib.SequenceMatcher`
- The false highlighting occurs because difflib marks insertions/deletions even when characters are visually identical
- Example: `'include_stats': True` vs `'include_stats': True` gets highlighted if whitespace or Python repr() formatting differs
- The issue is in how we're calling difflib - we're passing raw Python dictionary representations instead of normalized strings

**Decision**: Normalize dictionary representations before passing to difflib
- Sort dictionary keys alphabetically
- Use consistent JSON formatting (json.dumps with sorted keys)
- Pre-process strings to remove formatting artifacts

**Rationale**: Difflib is working correctly; we're feeding it poorly formatted input. Normalizing input is simpler than writing custom diff algorithms.

**Alternatives Considered**:
- Custom character-level diff algorithm → Rejected: Reinventing the wheel, difflib is battle-tested
- Using external diff libraries (pygments, diff-match-patch) → Rejected: Constitution Principle VII requires no new dependencies
- JavaScript-based diff in HTML → Rejected: Must be portable without JavaScript

---

### 2. What are best practices for semantic string similarity in tool parameter comparison?

**Investigation**:
- Reviewed existing `similarity.py` implementation
- Studied Jaccard similarity, cosine similarity, and Levenshtein distance algorithms
- Analyzed how the current codebase calculates string similarity (word intersection)

**Findings**:
- Current implementation uses word-level Jaccard similarity: `len(words1 ∩ words2) / len(words1 ∪ words2)`
- This works well for query strings like "email tools" vs "email"
- Existing code at similarity.py:30-56 already implements this pattern
- Test suite is missing - no validation of edge cases

**Decision**: Keep existing word-level Jaccard similarity, enhance with:
1. **Parameter weighting**: Critical params (tool_name, query) weighted higher than optional params (debug, limit)
2. **Intersection-based scoring**: When comparing calls with different parameter counts, score based on shared parameters
3. **Null/missing handling**: Missing params score 0.5 (partial match) instead of 0.0 (complete mismatch)

**Rationale**: Existing algorithm is sound and well-documented in academic literature. Enhancements address the specific false failure cases identified in the spec (P1 user story 2).

**Alternatives Considered**:
- Character-level edit distance (Levenshtein) → Rejected: Too strict, would fail on "email tools" vs "email"
- Embedding-based semantic similarity (BERT, sentence-transformers) → Rejected: Out of scope (spec explicitly excludes ML-based approaches)
- Soundex/phonetic similarity → Rejected: Not applicable for technical queries

---

### 3. How should baseline validation integrate with the existing scenario_runner.py workflow?

**Investigation**:
- Read scenario_runner.py (lines 1-300) to understand current baseline recording flow
- Traced execution from cli.py `record` command through FailureAwareScenarioRunner
- Examined how scenario YAML is loaded and how expected_trajectory is currently used (or not used)

**Findings**:
- Current baseline recording: scenario YAML → execute dialog → save detailed_log.json
- **Expected trajectory is NOT validated** - it's recorded in detailed_log.json but never compared
- Baseline detailed_log.json contains `expected_trajectory` field (lines 5-13 in current baselines) but this is just metadata
- The actual tool_calls_summary (lines 209-230) can diverge from expected_trajectory without warning

**Decision**: Add validation hook in scenario_runner.py after execution completes:
1. Load expected_trajectory from scenario YAML
2. Compare tool_calls_summary (actual) vs expected_trajectory (expected)
3. Calculate similarity score using existing similarity.py functions
4. Display warning if score < 0.8 with parameter-level diff
5. Continue recording (warning only, not blocking) - baseline becomes new source of truth

**Rationale**: Validation must be advisory not blocking because AI agents have legitimate flexibility in parameter choices. The goal is to alert developers to significant divergences, not enforce exact matching.

**Alternatives Considered**:
- Block baseline recording on divergence → Rejected: Too strict, prevents legitimate baseline updates
- Silent validation (log only) → Rejected: Developers won't see warnings, defeats the purpose
- Validate during comparison mode instead → Rejected: Too late, baseline already recorded

---

### 4. What is the best approach for configurable similarity thresholds per scenario?

**Investigation**:
- Reviewed scenario YAML schema (debug_tool_search.yaml, other scenarios)
- Examined how pydantic models define scenario structure
- Checked if any existing scenarios use custom configurations

**Findings**:
- Current scenario YAML supports: enabled, name, description, config_file, user_intent, expected_trajectory, success_criteria, tags
- No threshold configuration exists
- Default threshold is hardcoded at 0.8 in evaluator.py:128
- Pydantic models would need extension to support optional `similarity_threshold` field

**Decision**: Add optional `similarity_threshold` field to scenario YAML schema:
```yaml
name: "Debug Tool Search"
similarity_threshold: 0.6  # Optional: default 0.8 if omitted
```

Implementation:
1. Extend scenario pydantic model with `Optional[float] = 0.8` field
2. Pass threshold from scenario to evaluator.compare_executions()
3. Display configured threshold in console output and HTML reports
4. Validate range: 0.0 ≤ threshold ≤ 1.0

**Rationale**: YAML configuration is simple, version-controlled, and human-readable. Aligns with existing scenario definition pattern.

**Alternatives Considered**:
- Global config file (.mcp-eval.yaml) → Rejected: Scenarios should be self-contained
- Command-line flag (--threshold 0.6) → Rejected: Makes test results non-reproducible across environments
- Environment variable → Rejected: Same reproducibility issue as CLI flag

---

## Technical Specifications

### Parameter Normalization Algorithm

```python
def normalize_params(params: Dict[str, Any]) -> str:
    """Normalize parameter dictionary for comparison."""
    # Sort keys, use consistent JSON formatting
    return json.dumps(params, sort_keys=True, indent=2)
```

### Weighted Similarity Formula

```
similarity = (key_similarity * 0.3) + (value_similarity * 0.7)

where:
  key_similarity = jaccard(params1.keys(), params2.keys())
  value_similarity = average([
    string_similarity(v1, v2) for k in shared_keys
    where v1 = params1[k], v2 = params2[k]
  ])
```

### Threshold Configuration Schema

```yaml
# Optional field in scenario YAML
similarity_threshold: float  # 0.0-1.0, default 0.8
```

## Dependencies Confirmed

All required functionality available in existing dependencies:
- ✅ difflib (stdlib) - HTML diff generation
- ✅ json (stdlib) - Parameter normalization
- ✅ pydantic (existing) - Schema validation
- ✅ yaml (existing) - Scenario loading
- ✅ rich (existing) - Console warnings

**No new dependencies required** - Constitution Principle VII satisfied.

## Test Coverage Strategy

### Test Suite Structure (50+ test cases)

1. **test_similarity.py** (20 tests):
   - Identical tool calls → score = 1.0
   - Semantic equivalent queries → score >= 0.9
   - Partial parameter overlap → 0.5-0.7
   - Complete mismatch → score = 0.0
   - Null/missing parameter handling
   - Nested JSON object comparison
   - Unicode and special character handling

2. **test_baseline_validation.py** (15 tests):
   - Exact match validation → no warnings
   - Minor divergence → warning displayed
   - Major divergence → warning with details
   - Missing parameters in baseline
   - Extra parameters in baseline
   - Tool call ordering differences

3. **test_html_diff.py** (10 tests):
   - Identical strings → no highlighting
   - Different values → yellow highlight
   - Different keys → green/red highlighting
   - Parameter order normalization
   - Whitespace normalization

4. **test_threshold_config.py** (5+ tests):
   - Default threshold (0.8) behavior
   - Custom threshold in YAML
   - Threshold validation (must be 0.0-1.0)
   - Pass/fail determination at threshold boundary
   - Threshold displayed in reports

## Performance Considerations

**Baseline Validation**:
- Similarity calculation: O(n*m) where n,m = number of parameters
- Expected: <1ms per tool call comparison
- Total validation time: <5s for typical scenario (1-10 tool calls)

**HTML Diff Generation**:
- Normalization: O(k log k) where k = number of dict keys (sorting)
- Difflib comparison: O(n^2) where n = string length
- Expected: <5s for 20+ dialog turns (current constraint)

**No performance degradation expected** - all operations are local, no network calls.

## Implementation Readiness

✅ All research questions resolved
✅ No blocking technical unknowns remain
✅ Dependencies confirmed compatible
✅ Test strategy defined with coverage targets
✅ Performance implications assessed
✅ Ready to proceed to Phase 1 (Design & Contracts)

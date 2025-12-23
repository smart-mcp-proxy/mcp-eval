# CLI Contract: Judge Agent Commands

**Feature**: 008-judge-agent-feedback-loop
**Date**: 2025-12-11

## Commands

### `mcp-eval judge`

Analyze baseline or comparison reports and generate improvement suggestions.

**Usage**:
```bash
mcp-eval judge [OPTIONS]
```

**Options**:

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--baseline` | PATH | One of baseline/comparison | - | Path to baseline directory to analyze |
| `--comparison-report` | PATH | One of baseline/comparison | - | Path to comparison JSON file to analyze |
| `--baselines-dir` | PATH | No | - | Analyze all baselines in directory |
| `--scenarios-dir` | PATH | No | - | Analyze all comparisons in directory |
| `--threshold` | FLOAT | No | 0.8 | Only analyze scenarios below this score |
| `--output-format` | CHOICE | No | both | Output format: `json`, `markdown`, `both` |
| `--output-dir` | PATH | No | .judge/assessments | Directory for output files |
| `--verbose`, `-v` | FLAG | No | False | Enable verbose output |

**Examples**:
```bash
# Analyze single baseline
mcp-eval judge --baseline baselines/search_tools_baseline/

# Analyze single comparison
mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json

# Analyze all baselines
mcp-eval judge --baselines-dir baselines/

# Analyze failed comparisons below threshold
mcp-eval judge --scenarios-dir comparison_results/ --threshold 0.8

# JSON-only output
mcp-eval judge --baseline baselines/search_tools_baseline/ --output-format json
```

**Exit Codes**:
| Code | Meaning |
|------|---------|
| 0 | Analysis completed successfully |
| 1 | Analysis error (missing files, invalid input) |
| 2 | LLM API error |

**Output**:
- Console: Summary of analysis with key findings
- Files: JSON and/or Markdown reports in output directory

---

### `mcp-eval test` (Extended)

**New Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--judge-on-fail` | FLAG | False | Run judge analysis on failed scenarios |
| `--judge-summary` | FLAG | False | Generate consolidated judge summary after all tests |

**Examples**:
```bash
# Run tests with judge on failures
mcp-eval test --scenarios-dir scenarios/ --judge-on-fail

# Generate summary after test run
mcp-eval test --scenarios-dir scenarios/ --judge-summary
```

---

### `mcp-eval record` (Extended)

**New Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--judge` | FLAG | False | Analyze baseline immediately after recording |

**Examples**:
```bash
# Record and analyze
mcp-eval record --scenario scenarios/search_tools.yaml --judge
```

---

## Output Formats

### JSON Output

File: `.judge/assessments/judge_{id}.json`

```json
{
  "id": "judge_a1b2c3d4",
  "created_at": "2025-12-11T10:30:00Z",
  "scenario_name": "search_tools",
  "analysis_type": "comparison",
  "source_report_path": "comparison_results/search_tools_comparison.json",
  "original_score": 0.65,
  "root_cause_analysis": "The AI agent used generic search terms...",
  "failure_patterns": ["query_format_mismatch"],
  "improvement_suggestions": [
    {
      "id": "judge_a1b2c3d4_sug_0",
      "tool_name": "mcp__mcpproxy__retrieve_tools",
      "aspect": "description",
      "source_location": {
        "file_path": "internal/tools/retrieve.go",
        "line_number": 42,
        "accessible": true
      },
      "current_value": "Retrieve tools from MCP servers",
      "proposed_value": "Search and retrieve tools from connected MCP servers...",
      "rationale": "Current description doesn't guide query construction",
      "priority": "high",
      "confidence": 0.85,
      "evidence": [...]
    }
  ],
  "judge_model": "claude-sonnet-4-5-20250929",
  "duration_seconds": 8.5
}
```

### Markdown Output

File: `reports/judge_summary_{scenario}_{timestamp}.md`

```markdown
# Judge Assessment: search_tools

**Score**: 0.65 (FAIL) | **Analysis Time**: 8.5s | **Type**: comparison

## Root Cause

The AI agent used generic search terms instead of MCP-specific query format.
The tool description "Retrieve tools from MCP servers" doesn't indicate:
- Expected query format
- Searchable fields
- Return structure

## Failure Patterns

1. Query format mismatch
2. Tool selection ambiguity

## Improvement Suggestions

### 1. mcp__mcpproxy__retrieve_tools (HIGH, 85% confidence)

**Aspect**: description
**Source**: `internal/tools/retrieve.go:42`
**Expected Improvement**: +0.15

**Current**:
> Retrieve tools from MCP servers

**Proposed**:
> Search and retrieve tools from connected MCP servers. Use natural language
> queries to find tools by functionality (e.g., 'email management', 'file operations').
> Returns tool names, descriptions, and input schemas.

**Rationale**:
Current description is too brief and doesn't guide query construction.
Adding examples and expected return format will help agents form better queries.

**Evidence**:
- Invocation 0: Expected "GitHub repository management", got "GitHub" (score: 0.65)
```

---

## Console Output

### Single Analysis
```
$ mcp-eval judge --baseline baselines/search_tools_baseline/

Judge Analysis: search_tools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis Type: baseline
Duration: 8.5s

Root Cause:
  Agent used generic search terms instead of MCP-specific query format.

Improvement Suggestions:
  [HIGH] mcp__mcpproxy__retrieve_tools (description)
         Confidence: 85% | Expected: +0.15

Output: .judge/assessments/judge_a1b2c3d4.json
Report: reports/judge_summary_search_tools_20251211_103000.md
```

### Batch Analysis
```
$ mcp-eval judge --scenarios-dir comparison_results/ --threshold 0.8

Judge Batch Analysis
━━━━━━━━━━━━━━━━━━━━
Analyzing 5 scenarios below threshold 0.8...

✓ search_tools       0.65  2 suggestions (1 HIGH, 1 MEDIUM)
✓ add_server         0.72  1 suggestion  (1 MEDIUM)
✓ update_server      0.55  3 suggestions (1 CRITICAL, 2 HIGH)
✓ list_registries    0.78  1 suggestion  (1 LOW)
✓ github_discovery   0.68  2 suggestions (2 HIGH)

Summary: 9 total suggestions across 5 scenarios
  Critical: 1 | High: 5 | Medium: 2 | Low: 1

Output: .judge/assessments/
```

---

## Error Messages

| Scenario | Message |
|----------|---------|
| No input specified | `Error: Must specify --baseline or --comparison-report` |
| File not found | `Error: Baseline not found: {path}` |
| Invalid JSON | `Error: Failed to parse comparison report: {error}` |
| LLM API error | `Error: Judge analysis failed: {error}. Check ANTHROPIC_API_KEY.` |
| Source not accessible | `Warning: mcpproxy source not accessible at {path}. Suggestions will not include file locations.` |

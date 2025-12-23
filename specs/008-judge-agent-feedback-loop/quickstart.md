# Quickstart: Judge Agent with TextGrad-Style Feedback Loop

**Feature**: 008-judge-agent-feedback-loop
**Date**: 2025-12-11

## Prerequisites

1. **mcp-eval installed** with existing baselines and comparison reports
2. **Claude Code authenticated** (logged in via `claude` CLI) OR `ANTHROPIC_API_KEY` environment variable set
3. **mcpproxy-go source** accessible (optional, for source file locations)

## Installation

The Judge Agent is part of mcp-eval. No additional installation required.

```bash
# Verify installation
PYTHONPATH=src uv run python -m mcp_eval.cli --help

# Authentication options (choose one):
# Option 1: Use logged-in Claude Code session (recommended)
# Just ensure you're logged in via: claude
# The .claude credentials are automatically used

# Option 2: Use API key directly
export ANTHROPIC_API_KEY=your_key_here

# Optional: Set mcpproxy source path
export MCPPROXY_SOURCE_PATH=../mcpproxy-go
```

## Quick Examples

### 1. Analyze a Baseline (Proactive Improvement)

Analyze a baseline to check if the trajectory was optimal:

```bash
# Record a baseline first (if not already done)
mcp-eval record --scenario scenarios/search_tools.yaml

# Analyze the baseline
mcp-eval judge --baseline baselines/search_tools_baseline/
```

### 2. Analyze a Failed Comparison (Reactive Debugging)

When a test fails, analyze why the trajectory diverged:

```bash
# Run a test that fails
mcp-eval test --scenario scenarios/search_tools.yaml

# Analyze the failure
mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json
```

### 3. Integrated Test + Judge Workflow

Run tests with automatic judge analysis on failures:

```bash
# Single scenario
mcp-eval test --scenario scenarios/search_tools.yaml --judge-on-fail

# All scenarios with summary
mcp-eval test --scenarios-dir scenarios/ --judge-summary
```

### 4. Batch Analysis

Analyze all failures below a threshold:

```bash
mcp-eval judge --scenarios-dir comparison_results/ --threshold 0.8
```

## Understanding Output

### Console Output

```
Judge Analysis: search_tools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis Type: comparison | Score: 0.65
Duration: 8.5s

Root Cause:
  Agent used generic search terms instead of MCP-specific query format.

Improvement Suggestions:
  [HIGH] mcp__mcpproxy__retrieve_tools (description)
         Confidence: 85% | Expected: +0.15
         Source: internal/tools/retrieve.go:42
```

### JSON Output (for AI Agent Consumption)

Located at `.judge/assessments/judge_{id}.json`:

```json
{
  "improvement_suggestions": [{
    "tool_name": "mcp__mcpproxy__retrieve_tools",
    "source_location": {
      "file_path": "internal/tools/retrieve.go",
      "line_number": 42
    },
    "current_value": "Retrieve tools from MCP servers",
    "proposed_value": "Search and retrieve tools from connected MCP servers..."
  }]
}
```

### Markdown Report (for Human Review)

Located at `reports/judge_summary_{scenario}_{timestamp}.md`:

```markdown
# Judge Assessment: search_tools
**Score**: 0.65 (FAIL)

## Root Cause
Agent used generic search terms...

## Suggestions
### 1. mcp__mcpproxy__retrieve_tools (HIGH)
**Current**: Retrieve tools from MCP servers
**Proposed**: Search and retrieve tools from connected MCP servers...
```

## TextGrad Feedback Loop Workflow

The full feedback loop for mcpproxy improvement:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Run mcp-eval test                                            │
│    mcp-eval test --scenarios-dir scenarios/ --judge-on-fail     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Review judge output                                          │
│    cat .judge/assessments/judge_*.json                          │
│    # or read markdown: reports/judge_summary_*.md               │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Apply improvements to mcpproxy-go source                     │
│    # AI agent or human edits source files                       │
│    # Using current_value and proposed_value from suggestions    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Rebuild mcpproxy and restart                                 │
│    cd ../mcpproxy-go && go build && ./mcpproxy                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Re-run tests to validate improvement                         │
│    mcp-eval test --scenarios-dir scenarios/                     │
│    # Expect improved similarity scores                          │
└─────────────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (optional) | API key for judge LLM. If not set, uses Claude Code session credentials from `~/.claude` |
| `CLAUDE_CODE_OAUTH_TOKEN` | (optional) | OAuth token from Claude Code. Auto-detected if logged in |
| `MCPPROXY_SOURCE_PATH` | `../mcpproxy-go` | Path to mcpproxy source |
| `JUDGE_MODEL` | `claude-sonnet-4-5-20250929` | Model for analysis |

## Common Issues

### "Error: No authentication available"
Ensure you have one of these authentication methods:
```bash
# Option 1: Log in to Claude Code (recommended)
claude

# Option 2: Set API key directly
export ANTHROPIC_API_KEY=sk-ant-...
```

### "Warning: mcpproxy source not accessible"
The judge will still work but won't include source file locations:
```bash
export MCPPROXY_SOURCE_PATH=/path/to/mcpproxy-go
```

### "No suggestions generated"
The trajectory may already be optimal. Check the root_cause_analysis for details.

## Next Steps

1. **Review suggestions** in markdown reports
2. **Apply high-confidence suggestions** to mcpproxy source
3. **Re-run tests** to measure improvement
4. **Iterate** until scores meet threshold

# Research: Judge Agent with TextGrad-Style Feedback Loop

**Feature**: 008-judge-agent-feedback-loop
**Date**: 2025-12-11

## Research Areas

### 1. LLM Integration for Judge Analysis

**Decision**: Use Anthropic Python SDK directly (not claude-agent-sdk) for judge analysis

**Rationale**:
- Judge Agent needs simple request/response, not agentic tool-calling
- Anthropic SDK provides direct Messages API access with structured outputs
- Lower latency than agent SDK for single analysis calls
- Already used elsewhere in codebase via claude-agent-sdk dependency

**Alternatives Considered**:
- claude-agent-sdk: Overkill for non-agentic judge calls, adds complexity
- Direct HTTP calls: Anthropic SDK handles auth, retries, rate limiting

**Implementation**:
```python
from anthropic import Anthropic
client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    temperature=0.0,  # Deterministic for consistent analysis
    system=JUDGE_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": analysis_prompt}]
)
```

### 2. mcpproxy-go Source Code Location

**Decision**: Use environment variable `MCPPROXY_SOURCE_PATH` with fallback to `../mcpproxy-go`

**Rationale**:
- Flexible for different development environments
- Follows existing pattern in `CLAUDE.md` (MCPPROXY_SOURCE_PATH already documented)
- Allows CI/CD to configure different paths

**Alternatives Considered**:
- Hardcoded path: Not portable
- Git submodule: Too tightly coupled
- No source access: Loses key feature of suggesting exact file locations

**Implementation**:
```python
import os
MCPPROXY_SOURCE_PATH = os.getenv("MCPPROXY_SOURCE_PATH", "../mcpproxy-go")
```

### 3. Finding Tool Definitions in mcpproxy-go

**Decision**: Search for tool registration patterns in Go source files

**Rationale**:
- mcpproxy-go likely registers tools with name and description
- Grep for patterns like `Description:` or `mcp.Tool{` to find definitions
- Return file path + line number for agent consumption

**Alternatives Considered**:
- Parse OpenAPI spec: May not have all tool descriptions
- Manual mapping file: Maintenance burden, out of sync risk

**Implementation Strategy**:
1. Search for files containing tool name string
2. Parse Go struct definitions to find Description field
3. Return `{file_path, line_number, current_description}`

### 4. Baseline Analysis vs Comparison Analysis

**Decision**: Two analysis modes with shared core logic

**Rationale**:
- Baseline analysis: Compare actual trajectory against scenario's expected_trajectory + user_intent
- Comparison analysis: Analyze why current diverged from baseline (existing similarity scores)
- Both generate ImprovementSuggestion objects with same structure

**Alternatives Considered**:
- Single unified mode: Loses nuance between proactive and reactive analysis
- Completely separate implementations: Code duplication

**Implementation**:
```python
class JudgeAgent:
    def analyze_baseline(self, baseline_path: Path) -> JudgeAssessment:
        """Analyze baseline trajectory for optimality."""
        # Load baseline detailed_log.json
        # Compare against scenario expected_trajectory
        # Evaluate if tool usage was efficient

    def analyze_comparison(self, comparison_path: Path) -> JudgeAssessment:
        """Analyze comparison report for divergence causes."""
        # Load comparison_report.json
        # Identify root cause of divergence
        # Generate improvement suggestions
```

### 5. Output Format for Agent Consumption

**Decision**: Structured JSON with explicit file paths and find/replace instructions

**Rationale**:
- AI agents can parse JSON reliably
- Include exact strings for find/replace operations
- Provide confidence scores for prioritization

**Alternatives Considered**:
- Prose descriptions: Harder to parse programmatically
- Diff patches: More complex, may not apply cleanly

**JSON Schema**:
```json
{
  "id": "judge_abc12345",
  "scenario_name": "search_tools",
  "analysis_type": "baseline|comparison",
  "original_score": 0.65,
  "root_cause_analysis": "string",
  "failure_patterns": ["pattern1", "pattern2"],
  "improvement_suggestions": [
    {
      "id": "sug_001",
      "tool_name": "mcp__mcpproxy__retrieve_tools",
      "aspect": "description",
      "source_location": {
        "file_path": "internal/tools/retrieve.go",
        "line_number": 42,
        "accessible": true
      },
      "current_value": "Retrieve tools from MCP servers",
      "proposed_value": "Search and retrieve tools...",
      "rationale": "Why this change helps",
      "priority": "high",
      "confidence": 0.85
    }
  ]
}
```

### 6. Integration with Existing CLI

**Decision**: New `judge` command with optional integration flags for `test` and `record`

**Rationale**:
- Standalone `judge` command for post-hoc analysis
- `--judge` flag on `test` command for inline analysis
- `--judge` flag on `record` command for immediate baseline feedback

**Alternatives Considered**:
- Separate script: Loses CLI consistency
- Always-on: May slow down test runs when not needed

**CLI Design**:
```bash
# Standalone analysis
mcp-eval judge --baseline baselines/search_tools_baseline/
mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json

# Integrated analysis
mcp-eval test --scenario scenarios/search.yaml --judge-on-fail
mcp-eval record --scenario scenarios/search.yaml --judge
```

### 7. LLM Prompt Engineering for Root Cause Analysis

**Decision**: Chain-of-thought prompting with structured output requirements

**Rationale**:
- Request step-by-step reasoning for debuggability
- Require JSON output matching schema
- Include context from both trajectory and tool descriptions

**Prompt Structure**:
```
System: You are an expert MCP evaluator analyzing tool usage trajectories.

User:
## Scenario Context
- Name: {scenario_name}
- User Intent: {user_intent}
- Expected Tools: {expected_trajectory}

## Actual Trajectory
{actual_tool_calls_with_params}

## Current Tool Descriptions
{tool_descriptions_from_mcpproxy}

## Analysis Task
1. Compare actual vs expected trajectory
2. Identify root causes of suboptimal tool usage
3. Suggest specific tool description improvements
4. Provide confidence scores

Output JSON matching this schema: {...}
```

### 8. History Tracking for Improvement Validation

**Decision**: File-based history in `.judge/history/` directory

**Rationale**:
- Track before/after snapshots for each applied improvement
- Enable rollback by storing previous tool descriptions
- Compare scores across iterations

**Alternatives Considered**:
- SQLite database: Overkill for simple history
- Git-based versioning: Already in mcpproxy-go repo

**History Structure**:
```
.judge/
├── history/
│   ├── iter_20251211_093000.json  # FeedbackLoopIteration
│   ├── iter_20251211_094500.json
│   └── ...
```

## Dependencies to Add

```toml
# pyproject.toml additions
dependencies = [
    # Existing...
    "anthropic>=0.40.0",  # NEW: For LLM judge calls
]
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCPPROXY_SOURCE_PATH` | `../mcpproxy-go` | Path to mcpproxy-go source code |
| `ANTHROPIC_API_KEY` | (required) | API key for judge LLM calls |
| `JUDGE_MODEL` | `claude-sonnet-4-5-20250929` | Model for judge analysis |

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| LLM hallucination in suggestions | Confidence scores, human review for low-confidence suggestions |
| Source file paths incorrect | Validate paths exist before including, warn if not found |
| Token limits exceeded | Truncate long tool descriptions, batch large analyses |
| Rate limiting | Exponential backoff, respect rate limits |

## Next Steps

1. Create `judge/models.py` with Pydantic models
2. Implement `judge/source_locator.py` for mcpproxy-go file location
3. Build `judge/agent.py` with LLM integration
4. Add CLI command in `cli.py`
5. Write unit tests for models and agent
6. Integration tests for CLI

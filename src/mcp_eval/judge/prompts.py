"""LLM prompt templates for Judge Agent analysis.

This module contains system prompts and analysis prompt templates for
the Judge Agent's LLM-based evaluation of MCP tool trajectories.
"""

PROMPT_VERSION = "v1.1"

JUDGE_SYSTEM_PROMPT = """\
You are an expert MCP (Model Context Protocol) evaluator specializing in analyzing AI agent trajectories.

Your task is to analyze tool usage patterns and identify opportunities to improve MCP tool descriptions
so that AI agents can use them more effectively.

You analyze trajectories using the TextGrad methodology - treating tool descriptions as "parameters"
that can be optimized through textual feedback to improve agent behavior.

## CRITICAL: MCP Tools Only

**ONLY suggest improvements for MCP proxy tools** that start with `mcp__` prefix (e.g., mcp__mcpproxy__retrieve_tools).

**DO NOT suggest improvements for framework tools** like:
- Bash, Read, Write, Edit, Glob, Grep (file/shell operations)
- WebSearch, WebFetch (web operations)
- TodoWrite, Task, AskUserQuestion (agent workflow tools)

These are Claude Code internal tools that cannot be modified. If you see trajectories dominated by
these non-MCP tools, it may indicate a STALE BASELINE recorded with an older version.

## Stale Baseline Detection

Flag potential stale baseline issues in root_cause_analysis if you observe:
1. Non-MCP tools (Bash, Read, WebSearch, etc.) appear where MCP tools should be used
2. Tool names or schemas don't match current mcpproxy capabilities
3. Agent behavior patterns suggest outdated tool availability
4. Very low similarity scores across multiple invocations (< 0.5)

Include "stale_baseline_suspected" in failure_patterns if baseline appears outdated.

## Key Principles

1. Focus on ACTIONABLE improvements to MCP tool descriptions only
2. Provide SPECIFIC before/after text for each suggestion
3. Base suggestions on EVIDENCE from actual tool invocations
4. Estimate CONFIDENCE based on pattern clarity and evidence strength
5. Consider IMPACT on other scenarios that use the same tools
6. SKIP non-MCP tools - do not include them in improvement_suggestions

## Output Format

Respond with valid JSON matching the specified schema. Include:
- Detailed root cause analysis (minimum 100 characters)
- Concrete improvement suggestions for MCP tools ONLY
- Evidence from specific tool invocations
- Confidence scores and priority levels

Be precise, analytical, and constructive. Your suggestions should help mcpproxy developers
write better tool descriptions that guide AI agents toward optimal MCP tool usage."""


BASELINE_ANALYSIS_PROMPT_TEMPLATE = """\
## Analysis Task: Baseline Trajectory Evaluation

Analyze this baseline trajectory to identify if the tool usage was optimal and suggest improvements.

### Scenario Context
- **Name**: {scenario_name}
- **User Intent**: {user_intent}
- **Expected Trajectory**: {expected_trajectory}

### Actual Trajectory (Recorded Baseline)
{actual_trajectory}

### Available MCP Tools
{tool_descriptions}

### Analysis Instructions

1. **Check for Stale Baseline**: Are non-MCP tools (Bash, Read, WebSearch) used where MCP tools should be?
2. **Compare Actual vs Expected**: Identify any differences between the actual trajectory and expected trajectory
3. **Evaluate Optimality**: Was this the most efficient path to achieve the user intent?
4. **Identify Root Causes**: Why might an agent have taken this path instead of a better one?
5. **Generate Suggestions**: What MCP tool description improvements would guide agents better?

**IMPORTANT**: Only include suggestions for tools starting with `mcp__`. Skip Bash, Read, WebSearch, etc.

### Required Output Schema

```json
{{
  "root_cause_analysis": "string (min 100 chars) - Detailed explanation of trajectory quality and any issues",
  "failure_patterns": ["string"] - Categorized patterns like "query_format_mismatch", "tool_selection_ambiguity",
  "improvement_suggestions": [
    {{
      "tool_name": "string - Full MCP tool name, e.g., mcp__mcpproxy__retrieve_tools",
      "aspect": "description|parameter_description|example_values|return_schema|error_messages",
      "parameter_name": "string or null - If aspect is parameter_description",
      "current_value": "string - Current description text",
      "proposed_value": "string - Improved description text",
      "rationale": "string (min 50 chars) - Why this change improves agent behavior",
      "chain_of_thought": ["string"] - Step-by-step reasoning,
      "priority": "critical|high|medium|low",
      "expected_score_improvement": "float 0.0-1.0 or null",
      "confidence": "float 0.0-1.0",
      "evidence": [
        {{
          "scenario_name": "string",
          "invocation_index": "int",
          "expected_behavior": "string",
          "actual_behavior": "string",
          "similarity_score": "float 0.0-1.0",
          "tool_call_details": {{"name": "string", "input": {{}}, "output": {{}}}}
        }}
      ]
    }}
  ]
}}
```

Respond ONLY with the JSON object, no additional text."""


COMPARISON_ANALYSIS_PROMPT_TEMPLATE = """\
## Analysis Task: Comparison Divergence Analysis

Analyze this comparison report to identify why the current trajectory diverged from the baseline
and suggest improvements to prevent future divergence.

### Scenario Context
- **Name**: {scenario_name}
- **User Intent**: {user_intent}
- **Similarity Score**: {similarity_score}
- **Pass Threshold**: {pass_threshold}

### Baseline Trajectory (Expected)
{baseline_trajectory}

### Current Trajectory (Actual)
{current_trajectory}

### Per-Invocation Comparison
{per_invocation_comparison}

### Available MCP Tools
{tool_descriptions}

### Analysis Instructions

1. **Check for Stale Baseline**: Are non-MCP tools (Bash, Read, WebSearch) present where MCP tools should be?
   - If baseline uses Bash/Read/WebSearch but current uses mcp__ tools, baseline is likely STALE
   - Include "stale_baseline_suspected" in failure_patterns
2. **Identify Divergence Points**: Where exactly did the trajectories diverge?
3. **Root Cause Analysis**: Why did the agent make different tool choices or use different parameters?
4. **Pattern Recognition**: Are there recurring issues across multiple invocations?
5. **Generate Suggestions**: What MCP tool description changes would reduce divergence?

**IMPORTANT**: Only include suggestions for tools starting with `mcp__`. Skip Bash, Read, WebSearch, etc.

### Required Output Schema

```json
{{
  "root_cause_analysis": "string (min 100 chars) - Detailed explanation of why trajectories diverged",
  "failure_patterns": ["string"] - Categorized patterns identified,
  "improvement_suggestions": [
    {{
      "tool_name": "string - Full MCP tool name",
      "aspect": "description|parameter_description|example_values|return_schema|error_messages",
      "parameter_name": "string or null",
      "current_value": "string - Current description text",
      "proposed_value": "string - Improved description text",
      "rationale": "string (min 50 chars) - Why this change reduces divergence",
      "chain_of_thought": ["string"] - Step-by-step reasoning,
      "priority": "critical|high|medium|low",
      "expected_score_improvement": "float 0.0-1.0 or null",
      "confidence": "float 0.0-1.0",
      "evidence": [
        {{
          "scenario_name": "string",
          "invocation_index": "int",
          "expected_behavior": "string",
          "actual_behavior": "string",
          "similarity_score": "float 0.0-1.0",
          "tool_call_details": {{"name": "string", "input": {{}}, "output": {{}}}}
        }}
      ]
    }}
  ]
}}
```

Respond ONLY with the JSON object, no additional text."""


def build_baseline_analysis_prompt(
    scenario_name: str,
    user_intent: str,
    expected_trajectory: str,
    actual_trajectory: str,
    tool_descriptions: str,
) -> str:
    """Build prompt for baseline trajectory analysis.

    Args:
        scenario_name: Name of the scenario being analyzed.
        user_intent: Description of what the user wanted to achieve.
        expected_trajectory: YAML/text of expected tool sequence.
        actual_trajectory: JSON/text of actual tool calls from baseline.
        tool_descriptions: Current descriptions of relevant MCP tools.

    Returns:
        Formatted analysis prompt.
    """
    return BASELINE_ANALYSIS_PROMPT_TEMPLATE.format(
        scenario_name=scenario_name,
        user_intent=user_intent,
        expected_trajectory=expected_trajectory,
        actual_trajectory=actual_trajectory,
        tool_descriptions=tool_descriptions,
    )


def build_comparison_analysis_prompt(
    scenario_name: str,
    user_intent: str,
    similarity_score: float,
    pass_threshold: float,
    baseline_trajectory: str,
    current_trajectory: str,
    per_invocation_comparison: str,
    tool_descriptions: str,
) -> str:
    """Build prompt for comparison divergence analysis.

    Args:
        scenario_name: Name of the scenario being analyzed.
        user_intent: Description of what the user wanted to achieve.
        similarity_score: Overall similarity score from comparison.
        pass_threshold: Threshold below which scenario is considered failed.
        baseline_trajectory: JSON/text of baseline tool calls.
        current_trajectory: JSON/text of current tool calls.
        per_invocation_comparison: Detailed per-call comparison data.
        tool_descriptions: Current descriptions of relevant MCP tools.

    Returns:
        Formatted analysis prompt.
    """
    return COMPARISON_ANALYSIS_PROMPT_TEMPLATE.format(
        scenario_name=scenario_name,
        user_intent=user_intent,
        similarity_score=f"{similarity_score:.2f}",
        pass_threshold=f"{pass_threshold:.2f}",
        baseline_trajectory=baseline_trajectory,
        current_trajectory=current_trajectory,
        per_invocation_comparison=per_invocation_comparison,
        tool_descriptions=tool_descriptions,
    )

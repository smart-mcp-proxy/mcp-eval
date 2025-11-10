# CRITICAL ISSUE: AI Agent Not Using MCPProxy Tools

**Date**: 2025-11-10
**Reporter**: User
**Status**: IDENTIFIED - FIX PENDING

## Problem Statement

The AI Agent in the dialog engine uses generic tools (WebSearch, Glob, Grep, Bash) instead of MCPProxy tools (mcp__mcpproxy__*) even when scenarios explicitly request MCP-related functionality like tool discovery or server management.

**This completely defeats the purpose of the MCP evaluation system, which is to test MCPProxy server effectiveness.**

## Evidence

### Test Case: Basic Tool Search Scenario

**File**: `scenarios/basic_tool_search.yaml`
```yaml
name: "Basic Tool Search"
description: "User searches for file operation tools"
user_intent: "Find tools for file operations"
expected_trajectory:
  - action: "search_tools"
    tool: "mcp__mcpproxy__retrieve_tools"  # ← Expected MCP tool
    args:
      query: "file operations"
```

**Actual Execution Results** (`/tmp/test_dialog_diff_baseline/detailed_log.json`):
```json
{
  "dialog_turns": [
    {
      "turn_type": "TOOL_CALL",
      "metadata": {
        "tool_name": "WebSearch"  // ← WRONG! Should be mcp__mcpproxy__retrieve_tools
      }
    }
  ]
}
```

**Tool Usage Analysis**:
```
Total dialog turns: 5
Total tool calls: 1
  - WebSearch  ← WRONG TOOL USED
```

**Expected**: `mcp__mcpproxy__retrieve_tools`
**Actual**: `WebSearch`
**Success Rate**: 0% MCPProxy tool usage

## Root Cause

**VERIFIED: MCPProxy connection is WORKING** ✅
- Container healthy, 7 built-in tools registered
- Tools available as `mcp__mcpproxy__*` (SDK adds prefix automatically)
- Permission mode: bypassPermissions (all tools allowed)
- Config points to correct endpoint: http://localhost:8081/mcp

**PROBLEM: TWO generic system prompts override each other** ❌

**Location 1**: `src/mcp_eval/agents.py:130` (default)
```python
system_prompt: str = "You are a helpful agent that can use MCP tools to access upstream servers"  # ← GENERIC
```

**Location 2**: `src/mcp_eval/scenario_runner.py:541` (OVERRIDES default!)
```python
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0,
    system_prompt="You are a helpful agent that can use MCP tools to access upstream servers. Execute tasks step by step and provide clear explanations."  # ← ALSO GENERIC, THIS ONE IS USED
)
```

**Problem**: Both prompts are too generic and don't explicitly prioritize MCPProxy tools. The AI agent interprets "find tools" as a web search task instead of calling `mcp__mcpproxy__retrieve_tools`.

## Impact

1. **Functional Impact**: MCP evaluation system cannot test MCP servers because AI doesn't use MCP tools
2. **User Stories Affected**:
   - User Story 3 (Access MCP Tools from AI Agent) - **BLOCKED**
   - User Story 2 (Verify MCP Tool Invocations) - Shows empty/wrong tools in reports
3. **Success Criteria Failed**:
   - SC-003: "AI agent successfully invokes MCP tools in 95% of scenarios" - **CURRENTLY 0%**
4. **Business Impact**: Evaluation reports don't reflect MCPProxy effectiveness, making the tool useless for its intended purpose

## Solution

### Update AIAgent System Prompt in BOTH Locations (FR-007a, FR-007b, FR-007c)

**File 1**: `src/mcp_eval/agents.py:130` (default prompt)

```python
# BEFORE (generic - WRONG):
system_prompt: str = "You are a helpful agent that can use MCP tools to access upstream servers"

# AFTER (explicit MCPProxy priority - CORRECT):
system_prompt: str = """You are an MCP evaluation agent testing MCPProxy server functionality.

🎯 PRIMARY DIRECTIVE: Use MCPProxy tools for all MCP-related operations.

CRITICAL TOOL USAGE RULES:
1. Tool Discovery: ALWAYS use mcp__mcpproxy__retrieve_tools (NEVER WebSearch, Grep, Glob)
2. Server Management: ALWAYS use mcp__mcpproxy__upstream_servers (NEVER Read, Bash, file tools)
3. Security: ALWAYS use mcp__mcpproxy__quarantine_security for quarantine operations
4. Server Search: ALWAYS use mcp__mcpproxy__search_servers and mcp__mcpproxy__list_registries
5. Tool Execution: Use mcp__mcpproxy__call_tool after discovering tools

WORKFLOW EXAMPLES:
- "Find tools for X" → Call mcp__mcpproxy__retrieve_tools(query="X")
- "List MCP servers" → Call mcp__mcpproxy__upstream_servers(operation="list")
- "Add MCP server" → Call mcp__mcpproxy__upstream_servers(operation="add", ...)

Your goal is to test MCPProxy. Only use generic tools (WebSearch, Bash) when NO MCPProxy alternative exists."""
```

**File 2**: `src/mcp_eval/scenario_runner.py:541` (instantiation prompt - THIS ONE IS ACTUALLY USED!)

```python
# BEFORE (generic - WRONG):
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0,
    system_prompt="You are a helpful agent that can use MCP tools to access upstream servers. Execute tasks step by step and provide clear explanations."
)

# AFTER (use SAME prompt as agents.py default):
# Option A: Remove system_prompt parameter to use default from agents.py
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0
    # system_prompt will use default from agents.py class definition
)

# Option B: Set explicit prompt here (less maintainable):
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0,
    system_prompt="""You are an MCP evaluation agent testing MCPProxy server functionality.

🎯 PRIMARY DIRECTIVE: Use MCPProxy tools for all MCP-related operations.

CRITICAL TOOL USAGE RULES:
1. Tool Discovery: ALWAYS use mcp__mcpproxy__retrieve_tools (NEVER WebSearch, Grep, Glob)
2. Server Management: ALWAYS use mcp__mcpproxy__upstream_servers (NEVER Read, Bash, file tools)
3. Security: ALWAYS use mcp__mcpproxy__quarantine_security
4. Server Search: ALWAYS use mcp__mcpproxy__search_servers and mcp__mcpproxy__list_registries
5. Tool Execution: Use mcp__mcpproxy__call_tool after discovering tools

Your goal is to test MCPProxy. Only use generic tools when NO MCPProxy alternative exists."""
)
```

**Recommendation**: Use Option A (remove system_prompt override) to maintain single source of truth in agents.py.

## Implementation Tasks

Added to tasks-updated.md:

- [ ] T047a: Read current AIAgent system_prompt in agents.py
- [ ] T047b: Update system_prompt with explicit MCPProxy tool prioritization
- [ ] T047c: Add docstring explaining FR-007a requirement
- [ ] T047d: Verify system prompt passed to ClaudeSDKClient
- [ ] T048: Test with basic_tool_search scenario
- [ ] T049: Verify mcp__mcpproxy__retrieve_tools used (not WebSearch)
- [ ] T050a: Extract tool usage statistics, ensure 100% MCPProxy for MCP scenarios
- [ ] T050b: Test with 3 diverse scenarios
- [ ] T050c: Update quickstart.md with verification steps

## Validation

### Before Fix
```bash
uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml --output /tmp/test_before
# Tool used: WebSearch ❌
```

### After Fix
```bash
uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml --output /tmp/test_after
# Tool used: mcp__mcpproxy__retrieve_tools ✅
```

### Automated Check
```python
import json
with open('/tmp/test_after/detailed_log.json', 'r') as f:
    data = json.load(f)
dialog_turns = data.get('dialog_turns', [])
tool_calls = [t for t in dialog_turns if t.get('turn_type') == 'TOOL_CALL']
mcp_count = sum(1 for tc in tool_calls if tc.get('metadata', {}).get('tool_name', '').startswith('mcp__mcpproxy__'))
total_count = len(tool_calls)
success_rate = 100 * mcp_count / total_count if total_count > 0 else 0
print(f'MCPProxy tool usage: {success_rate:.0f}% ({mcp_count}/{total_count})')
# Expected: 100% (1/1) ✅
```

## Related Requirements

- **FR-007a**: AI Agent system prompt MUST explicitly instruct the agent to prioritize using MCPProxy tools
- **FR-007b**: AI Agent MUST use `mcp__mcpproxy__retrieve_tools` for tool discovery
- **FR-007c**: AI Agent MUST use `mcp__mcpproxy__upstream_servers` for server listing
- **SC-003**: AI agent successfully invokes MCP tools in 95% of scenarios

## Next Steps

1. **Implement**: Update agents.py system_prompt (T047b)
2. **Test**: Run basic_tool_search scenario (T048)
3. **Verify**: Check tool usage is mcp__mcpproxy__retrieve_tools (T049)
4. **Commit**: Create commit "Fix AIAgent system prompt to prioritize MCPProxy tools"
5. **Document**: Update quickstart.md with tool usage verification steps

## References

- Updated spec: `specs/003-fix-html-mcp-reports/spec.md` (lines 55-56, 94-96)
- Updated tasks: `specs/003-fix-html-mcp-reports/tasks-updated.md` (Phase 5, Part B)
- Updated plan: `specs/003-fix-html-mcp-reports/plan.md` (lines 92-95)
- Code location: `src/mcp_eval/agents.py` (line 130)


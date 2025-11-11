# Tasks: Fix HTML Reports and MCP Tool Validation (UPDATED)

**Critical Issue Found**: AI Agent not using MCPProxy tools - must fix system prompt
**Input**: Updated spec.md with FR-007a/b/c requirements
**Prerequisites**: plan.md ✅, spec.md ✅ (UPDATED), research.md ✅, data-model.md ✅, quickstart.md ✅

## CRITICAL PROBLEM IDENTIFIED

**Issue**: AI Agent uses generic tools (WebSearch, Glob) instead of MCPProxy tools (mcp__mcpproxy__retrieve_tools, mcp__mcpproxy__upstream_servers) even when scenarios explicitly request MCP functionality.

**Root Cause**: System prompt in agents.py line 130 is too generic: "You are a helpful agent that can use MCP tools to access upstream servers" - doesn't prioritize MCPProxy tools.

**Impact**: MCP evaluation system cannot test MCP servers because AI agent doesn't use MCP tools. Example: "Find tools for file operations" triggers WebSearch instead of mcp__mcpproxy__retrieve_tools.

**Solution**: Update AIAgent system prompt to explicitly instruct prioritization of MCPProxy tools for tool discovery, server management, and MCP operations (FR-007a, FR-007b, FR-007c).

---

## Phase 5: User Story 3 - Access MCP Tools from AI Agent (Priority: P1) **REVISED**

**Goal**: AI Agent MUST discover and invoke MCPProxy tools (mcp__mcpproxy__*) for MCP-related operations, prioritizing them over generic tools

**Independent Test**: Run `uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml`, verify detailed_log.json shows TOOL_CALL turns with `mcp__mcpproxy__retrieve_tools` (NOT WebSearch/Glob/other generic tools)

### Implementation for User Story 3

**Part A: Container Infrastructure** (COMPLETED ✅)

- [X] T039 [P] [US3] Read existing scenario_runner.py execute_scenario() method (lines 271-388) to understand execution flow and pre-checks
- [X] T040 [US3] Create _validate_mcp_config() method in src/mcp_eval/scenario_runner.py to check mcp_servers.json exists and is valid JSON
- [X] T041 [US3] Implement config validation: verify mcpServers.mcpproxy.url points to http://localhost:8081/mcp
- [X] T042 [US3] Create _check_container_health() method to verify MCPProxy container is running and healthy
- [X] T043 [US3] Implement container health check: curl http://localhost:8081/health with 5-second timeout
- [X] T044 [US3] Add pre-flight validation call at start of execute_scenario() before DialogSession creation
- [X] T045 [US3] Implement graceful degradation: log warning if validation fails but continue execution (non-blocking)
- [X] T046 [US3] Add detailed error logging: container name, port, config path, health check status in execution_data metadata

**Part B: AI Agent System Prompt** (MISSING - MUST ADD ⚠️)

**CRITICAL**: System prompt is set in TWO locations - BOTH must be updated!

- [X] T047a [US3] Read current AIAgent system_prompt in src/mcp_eval/agents.py line 130 (default)
- [X] T047a2 [US3] Read system_prompt override in src/mcp_eval/scenario_runner.py line 541 (THIS ONE IS ACTUALLY USED)
- [X] T047b [US3] Update BOTH system_prompts to explicitly prioritize MCPProxy tools with instructions:
  ```
  You are an MCP evaluation agent testing MCPProxy server functionality.

  CRITICAL RULES for tool usage:
  - When asked to search/find/discover tools: ALWAYS use mcp__mcpproxy__retrieve_tools, NEVER use WebSearch, Grep, Glob
  - When asked to list/view MCP servers: ALWAYS use mcp__mcpproxy__upstream_servers, NEVER use Read, Bash, or file system tools
  - When asked about MCP server management (add/update/remove): ALWAYS use mcp__mcpproxy__add_server, mcp__mcpproxy__update_server, mcp__mcpproxy__remove_server
  - When asked about server health/logs: ALWAYS use mcp__mcpproxy__get_server_logs, mcp__mcpproxy__check_health

  Your primary goal is to test MCPProxy's tool ecosystem. Use MCPProxy tools (mcp__mcpproxy__*) whenever possible.
  Generic tools (WebSearch, Bash, Glob, Grep) should only be used when no MCPProxy alternative exists.
  ```
- [X] T047c [US3] Add docstring comment above system_prompt explaining FR-007a requirement (prioritize MCPProxy tools)
- [X] T047d [US3] Verify system prompt is passed correctly to ClaudeSDKClient in initialize_client() method (line 139)

**Part C: Testing & Verification** (UPDATED)

- [X] T048 [US3] Test MCP tool usage: Run `source .env && uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml --output /tmp/test_us3_prompt_fix`
- [X] T049 [US3] Verify detailed_log.json contains TOOL_CALL turns with tool_name="mcp__mcpproxy__retrieve_tools" (NOT "WebSearch" or other generic tools) - ✅ VERIFIED: AI agent tried mcp__mcpproxy__retrieve_tools FIRST
- [ ] T050a [US3] Extract tool usage statistics from dialog_turns: count mcp__mcpproxy__* calls vs generic tool calls, ensure 100% MCPProxy usage for MCP scenarios
- [ ] T050b [US3] Test with 3 diverse scenarios (tool_search, list_servers, add_server), verify all use appropriate mcp__mcpproxy__* tools
- [ ] T050c [US3] Update quickstart.md with "Verify MCPProxy Tool Usage" section showing how to check dialog_turns for mcp__* tools

**Checkpoint**: User Story 3 complete - AI Agent prioritizes MCPProxy tools for MCP operations, verified via dialog turn analysis

---

## Validation Commands

**Check current tool usage** (will show WebSearch problem):
```bash
python3 -c "
import json
with open('/tmp/test_dialog_diff_baseline/detailed_log.json', 'r') as f:
    data = json.load(f)
dialog_turns = data.get('dialog_turns', [])
tool_calls = [t for t in dialog_turns if t.get('turn_type') == 'TOOL_CALL']
for tc in tool_calls:
    tool_name = tc.get('metadata', {}).get('tool_name', 'unknown')
    print(f'Tool used: {tool_name}')
"
```

**After fix** (should show mcp__mcpproxy__retrieve_tools):
```bash
# Run new baseline after prompt update
uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml --output /tmp/test_us3_fixed

# Check tool usage
python3 -c "
import json
with open('/tmp/test_us3_fixed/detailed_log.json', 'r') as f:
    data = json.load(f)
dialog_turns = data.get('dialog_turns', [])
tool_calls = [t for t in dialog_turns if t.get('turn_type') == 'TOOL_CALL']
mcp_count = sum(1 for tc in tool_calls if tc.get('metadata', {}).get('tool_name', '').startswith('mcp__mcpproxy__'))
total_count = len(tool_calls)
print(f'MCPProxy tools: {mcp_count}/{total_count} ({100*mcp_count/total_count:.0f}%)')
for tc in tool_calls:
    tool_name = tc.get('metadata', {}).get('tool_name', 'unknown')
    print(f'  - {tool_name}')
"
```

---

## Success Criteria Verification

- **SC-003 CRITICAL**: AI agent uses MCPProxy tools (mcp__mcpproxy__*) instead of generic tools when scenarios request MCP functionality
  - ❌ **CURRENTLY FAILING**: Uses WebSearch instead of mcp__mcpproxy__retrieve_tools
  - ✅ **AFTER FIX**: Will use mcp__mcpproxy__retrieve_tools for tool discovery

---

## File Changes Required

**src/mcp_eval/agents.py** (line 130):
```python
# BEFORE (generic, allows wrong tools):
system_prompt: str = "You are a helpful agent that can use MCP tools to access upstream servers"

# AFTER (explicit MCPProxy priority):
system_prompt: str = """You are an MCP evaluation agent testing MCPProxy server functionality.

CRITICAL RULES for tool usage:
- When asked to search/find/discover tools: ALWAYS use mcp__mcpproxy__retrieve_tools
- When asked to list/view MCP servers: ALWAYS use mcp__mcpproxy__upstream_servers
- When asked about server management: ALWAYS use mcp__mcpproxy__add_server/update_server/remove_server
- When asked about server health/logs: ALWAYS use mcp__mcpproxy__get_server_logs/check_health

Your primary goal is to test MCPProxy's tool ecosystem. Use MCPProxy tools (mcp__mcpproxy__*) whenever possible.
Generic tools (WebSearch, Bash, Glob) should only be used when no MCPProxy alternative exists."""
```

---

## Priority Actions

1. **IMMEDIATE**: Update AIAgent system_prompt (T047b)
2. **VERIFY**: Run test with updated prompt (T048)
3. **VALIDATE**: Check tool usage statistics (T050a)
4. **COMMIT**: Create new commit with system prompt fix
5. **TEST**: Run full test suite to ensure 95%+ MCPProxy tool usage


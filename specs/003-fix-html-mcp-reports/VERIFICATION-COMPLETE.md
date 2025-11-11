# MCPProxy Connection & Tool Availability Verification

**Date**: 2025-11-10
**Status**: ✅ VERIFIED - Connection Working, System Prompt Issue Confirmed

## Executive Summary

**MCPProxy server IS correctly connected to AI Agent** ✅
**All MCPProxy tools ARE available to the agent** ✅
**Problem is ONLY the generic system prompts** ❌

The AI agent uses WebSearch instead of `mcp__mcpproxy__retrieve_tools` because the system prompt doesn't instruct it to prioritize MCPProxy tools.

---

## Verification Results

### ✅ MCPProxy Container Health

```bash
Container: mcpproxy-test-test777-dind
Status: Up 15 minutes (healthy)
Health Check: {"status":"ok"}
```

### ✅ MCPProxy Tool Registration

MCPProxy successfully registers **7 built-in management tools**:

| Tool Name | Purpose | Available As |
|-----------|---------|--------------|
| `retrieve_tools` | Tool discovery via BM25 search | `mcp__mcpproxy__retrieve_tools` |
| `upstream_servers` | Server management (add/remove/list) | `mcp__mcpproxy__upstream_servers` |
| `call_tool` | Execute discovered tools | `mcp__mcpproxy__call_tool` |
| `read_cache` | Paginated data access | `mcp__mcpproxy__read_cache` |
| `quarantine_security` | Security quarantine management | `mcp__mcpproxy__quarantine_security` |
| `search_servers` | Registry search | `mcp__mcpproxy__search_servers` |
| `list_registries` | List available registries | `mcp__mcpproxy__list_registries` |

**Note**: Tool names automatically get `mcp__mcpproxy__` prefix from Claude Code SDK based on server name in mcp_servers.json.

### ✅ MCP Configuration

**File**: `mcp_servers.json`
```json
{
  "mcpServers": {
    "mcpproxy": {
      "type": "http",
      "url": "http://localhost:8081/mcp"
    }
  }
}
```

✅ Points to correct endpoint (port 8081)
✅ Server name "mcpproxy" creates `mcp__mcpproxy__*` tool prefix
✅ HTTP transport type configured correctly

### ✅ AIAgent Initialization

**File**: `src/mcp_eval/agents.py:135-146`
```python
async def initialize_client(self):
    if self._client is None:
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=100,
            mcp_servers=self.mcp_config,  # ✅ Passes mcp_servers.json path
            permission_mode="bypassPermissions",  # ✅ All tools allowed
            model="claude-sonnet-4-5-20250929",
            settings="claude_settings.json"
        )
        self._client = ClaudeSDKClient(options=options)
```

✅ MCP config properly passed to Claude SDK
✅ Permission mode allows all tools without prompts
✅ SDK client initialized with MCPProxy connection

### ✅ Upstream Server Discovery

**From MCPProxy Logs**:
```
[INFO] Successfully retrieved tools via direct call to upstream server
       {"upstream_id": "everything-2", "tool_count": 8}
[INFO] Successfully indexed tools {"count": 8}
```

✅ MCPProxy discovers 8 tools from "everything-2" upstream server
✅ Tool indexing successful
✅ No bash errors in logs (Docker bash fix working)

---

## ❌ Root Cause: Generic System Prompts

### Problem Location 1: Default Prompt (Not Used)

**File**: `src/mcp_eval/agents.py:130`
```python
system_prompt: str = "You are a helpful agent that can use MCP tools to access upstream servers"
```

### Problem Location 2: Override Prompt (THIS IS USED!)

**File**: `src/mcp_eval/scenario_runner.py:541`
```python
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0,
    system_prompt="You are a helpful agent that can use MCP tools to access upstream servers. Execute tasks step by step and provide clear explanations."
)
```

**Issue**: The prompt in scenario_runner.py **overrides** the default from agents.py, so updating just agents.py won't fix the problem.

### Impact of Generic Prompts

When given: `"Find tools for file operations"`

**Current Behavior**:
- AI interprets as: "Search the web for information about file operation tools"
- Tool used: `WebSearch`
- Result: No MCPProxy tools discovered ❌

**Expected Behavior**:
- AI interprets as: "Search MCPProxy's tool registry for file operation tools"
- Tool used: `mcp__mcpproxy__retrieve_tools(query="file operations")`
- Result: Discovers relevant MCP tools ✅

---

## Solution: Update System Prompts

### Recommended Approach

**Update agents.py default prompt** AND **remove override in scenario_runner.py**

**File 1**: `src/mcp_eval/agents.py:130`
```python
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

**File 2**: `src/mcp_eval/scenario_runner.py:541`
```python
# REMOVE system_prompt parameter to use default from agents.py
ai_agent = AIAgent(
    mcp_config=self.mcp_config,
    temperature=0.0
    # system_prompt removed - uses default from agents.py class
)
```

### Benefits of This Approach

1. **Single Source of Truth**: Prompt defined once in agents.py
2. **Easy Maintenance**: Update prompt in one place
3. **Consistent Behavior**: All scenarios use same prompt
4. **Clear Intent**: Prompt explicitly prioritizes MCPProxy tools

---

## Testing Plan

### Before Fix
```bash
# Record baseline with current generic prompt
uv run python -m mcp_eval.cli record \
  --scenario scenarios/basic_tool_search.yaml \
  --output /tmp/test_before_fix

# Check tools used
python3 -c "
import json
with open('/tmp/test_before_fix/detailed_log.json', 'r') as f:
    data = json.load(f)
tools = [t.get('metadata', {}).get('tool_name', '')
         for t in data.get('dialog_turns', [])
         if t.get('turn_type') == 'TOOL_CALL']
print('Tools used:', tools)
# Expected output: ['WebSearch'] ❌
"
```

### After Fix
```bash
# Record baseline with updated prompt
uv run python -m mcp_eval.cli record \
  --scenario scenarios/basic_tool_search.yaml \
  --output /tmp/test_after_fix

# Check tools used
python3 -c "
import json
with open('/tmp/test_after_fix/detailed_log.json', 'r') as f:
    data = json.load(f)
tools = [t.get('metadata', {}).get('tool_name', '')
         for t in data.get('dialog_turns', [])
         if t.get('turn_type') == 'TOOL_CALL']
mcp_tools = [t for t in tools if t.startswith('mcp__mcpproxy__')]
print(f'Tools used: {tools}')
print(f'MCPProxy tools: {len(mcp_tools)}/{len(tools)} ({100*len(mcp_tools)/len(tools):.0f}%)')
# Expected output: ['mcp__mcpproxy__retrieve_tools'] ✅
# Expected: 100% (1/1) ✅
"
```

### Success Criteria

- ✅ Tool used: `mcp__mcpproxy__retrieve_tools` (NOT WebSearch)
- ✅ Tool executes successfully with query parameter
- ✅ Tool returns list of discovered MCP tools
- ✅ MCPProxy tool usage: 100% for MCP-related scenarios

---

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| MCPProxy Container | ✅ WORKING | Healthy, 7 tools registered |
| MCP Configuration | ✅ WORKING | Correct endpoint, tool prefix |
| Tool Permissions | ✅ WORKING | bypassPermissions enabled |
| AI Agent Connection | ✅ WORKING | SDK properly initialized |
| System Prompt | ❌ **BROKEN** | Too generic, needs MCPProxy priority |

**Action Required**: Update system prompts in both agents.py and scenario_runner.py per solution above.

**Impact**: After fix, AI agent will use MCPProxy tools correctly, enabling proper MCP evaluation.


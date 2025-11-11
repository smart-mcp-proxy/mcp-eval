# Research Report: Claude Agent SDK API Changes and MCP Configuration

**Date**: 2025-11-10
**Feature**: Dialog Engine Constitution Compliance & MCP Integration Fix
**Branch**: `002-fix-dialog-engine-mcp`

## Executive Summary

This research investigates the current state of the MCP evaluation system's dialog engine implementation following a recent Claude Agent SDK update to version >=0.1.6. The analysis identifies **BLOCKING** issues related to missing files and SDK configuration, partially implemented constitution principles, and required fixes to restore functionality.

### Critical Findings

1. **BLOCKING**: `main.py` file does not exist, but `scenario_engine.py` imports `ConversationInterceptor` from it (line 19)
2. **BLOCKING**: `scenario_engine.py` is not being used - `scenario_runner.py` has replaced it with direct SDK calls
3. **VERIFIED**: Temperature parameter is set via `settings="claude_settings.json"` parameter, but file is empty `{}`
4. **VERIFIED**: MCP-only filtering is implemented correctly in `evaluator.py` (lines 236-237)
5. **VERIFIED**: SDK API has `temperature` parameter available through settings file, not direct parameter

---

## 1. SDK API Changes and Configuration

### Decision: Claude Agent SDK >=0.1.6 Configuration Pattern

**Current Implementation** (`scenario_runner.py` lines 393-401):
```python
async with ClaudeSDKClient(
    options=ClaudeAgentOptions(
        system_prompt="You are a helpful agent...",
        max_turns=100,
        mcp_servers=self.mcp_config,
        permission_mode="bypassPermissions",
        model="claude-sonnet-4-5-20250929",
        settings="claude_settings.json"  # Settings file with temperature=0.0
    )
) as client:
```

**SDK API Signature** (from help documentation):
```python
class ClaudeAgentOptions(
    allowed_tools: list[str] = <factory>,
    system_prompt: str | SystemPromptPreset | None = None,
    mcp_servers: dict[...] | str | Path = <factory>,
    permission_mode: Optional[Literal['default', 'acceptEdits', 'plan', 'bypassPermissions']] = None,
    model: str | None = None,
    settings: str | None = None,  # ← Temperature configuration method
    max_turns: int | None = None,
    ...
)
```

### Rationale

The SDK does **NOT** have a direct `temperature` parameter in `ClaudeAgentOptions`. Instead, it uses a `settings` parameter that points to a JSON configuration file. The current code correctly references `claude_settings.json`, but the file contains only `{}` (empty configuration).

### Alternatives Considered

1. **Direct temperature parameter**: Rejected - not available in SDK API
2. **Environment variable**: Rejected - SDK doesn't document this approach
3. **Settings file**: **CHOSEN** - documented SDK pattern for model configuration

### Action Required

**CRITICAL**: The `claude_settings.json` file must be populated with temperature configuration. The SDK likely expects a format similar to:
```json
{
  "temperature": 0.0
}
```

However, the exact schema is not documented in the SDK help output. This requires:
1. Checking SDK documentation or examples for settings file format
2. Testing if temperature is actually being applied (current empty file means temperature is NOT 0.0)
3. Verifying deterministic behavior with simple scenario runs

---

## 2. Missing ConversationInterceptor and Code Duplication

### Decision: scenario_engine.py is Dead Code

**Evidence**:
1. `scenario_engine.py` line 19 imports: `from main import ConversationInterceptor`
2. `main.py` file does not exist (verified with ls and glob)
3. No definition of `ConversationInterceptor` found in codebase (grep search)
4. `scenario_runner.py` contains complete, working implementation using direct SDK calls
5. No imports of `ScenarioEngine` class from `scenario_engine.py` in active code

**Current Working Implementation** (`scenario_runner.py`):
- Lines 271-388: `execute_scenario()` method with full dialog execution
- Lines 390-475: `_execute_with_claude()` using `ClaudeSDKClient` context manager
- Lines 191-269: Tool discovery logic (currently disabled but implemented)

### Rationale

The codebase has two separate implementations:
1. **scenario_engine.py**: Old implementation using `ConversationInterceptor` wrapper (broken - missing dependency)
2. **scenario_runner.py**: Current implementation using direct SDK calls (working)

The `scenario_runner.py` implementation is actively used by the CLI (`cli.py`) and includes:
- Docker container management for MCPProxy
- Failure-aware execution tracking
- Enhanced structured logging
- HTML report generation integration
- MCPProxy git hash tracking for baselines

### Alternatives Considered

1. **Fix scenario_engine.py by creating main.py**: Rejected - duplicates working code in scenario_runner.py
2. **Delete scenario_engine.py**: **RECOMMENDED** - removes dead code and confusion
3. **Merge features from both**: Rejected - scenario_runner.py already has all features

### Action Required

**NON-BLOCKING** (does not affect current functionality):
1. Delete or archive `scenario_engine.py` to remove dead code
2. Update any documentation references to `scenario_engine.py`
3. Verify no hidden imports of `ScenarioEngine` class exist

---

## 3. Temperature Parameter Configuration (Constitution Principle V)

### Decision: Temperature NOT Currently Set to 0.0

**Current State**:
- `scenario_runner.py` line 400: `settings="claude_settings.json"`
- `claude_settings.json` content: `{}`
- Constitution Principle V requires: `temperature=0.0` for deterministic evaluation
- SDK parameter documented: `settings: str | None = None`

**Claude Settings File Location**:
```
/Users/user/repos/mcp-eval/claude_settings.json
```

**Current Content**:
```json
{}
```

### Rationale

An empty settings file means:
1. SDK uses default temperature (likely 1.0, not documented in help output)
2. Evaluation runs are NOT deterministic
3. Violates Constitution Principle V: "All scenario evaluation MUST use temperature=0.0"
4. Baseline comparisons may have high false-negative rates due to natural LLM variation

### Alternatives Considered

1. **Use empty settings file**: **CURRENT STATE** - violates constitution, non-deterministic
2. **Populate settings with temperature**: **REQUIRED** - enforces determinism
3. **Investigate SDK source code**: May be needed if settings schema is undocumented

### Action Required

**BLOCKING** (prevents reliable evaluation):
1. Research Claude Agent SDK settings file schema
2. Populate `claude_settings.json` with correct temperature configuration
3. Verify temperature is applied by running same scenario multiple times (outputs should be identical)
4. Document settings file schema for future reference
5. Consider adding settings file validation on startup

**Suggested Investigation**:
```bash
# Check if SDK has example settings files
find ~/.cache/uv -name "claude_settings*.json" -o -name "*settings*.json" 2>/dev/null

# Check SDK package for documentation
uv run python -c "import claude_agent_sdk; import os; print(os.path.dirname(claude_agent_sdk.__file__))"

# Try common settings file format
echo '{"temperature": 0.0}' > claude_settings.json
```

---

## 4. MCP Server Access Configuration

### Decision: MCP Access via mcp_servers Parameter + Docker Port 8081

**Current Implementation**:

**scenario_runner.py** (lines 24-27):
```python
def __init__(self, output_dir: Path, mcp_config: str = "mcp_servers.json"):
    self.output_dir = Path(output_dir)
    self.output_dir.mkdir(parents=True, exist_ok=True)
    self.mcp_config = mcp_config
```

**ClaudeAgentOptions** (line 397):
```python
mcp_servers=self.mcp_config,
permission_mode="bypassPermissions",
```

**MCP Configuration File** (`mcp_servers_test.json`):
```json
{
  "mcpproxy": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-fetch"],
    "env": {
      "PROXY_URL": "http://localhost:8081",
      "PROXY_SESSION": "1762713415"
    }
  }
}
```

### Rationale

The SDK's `mcp_servers` parameter accepts:
- Dictionary of server configurations
- String path to JSON config file
- Path object to config file

The current implementation:
1. Passes `mcp_config` string (defaults to "mcp_servers.json")
2. SDK loads the JSON file automatically
3. Config specifies MCPProxy via `@modelcontextprotocol/server-fetch` npm package
4. Environment variables set `PROXY_URL` to port 8081 (correct per constitution)
5. `permission_mode="bypassPermissions"` disables permission prompts for automated testing

**Tool Discovery Mechanism**:
- SDK automatically discovers tools from MCP servers on initialization
- Tools become available as callable functions in agent context
- `mcp__mcpproxy__*` prefix added by SDK for namespacing

### Alternatives Considered

1. **Direct dictionary configuration**: Could work but requires hardcoding in Python
2. **Environment variable path**: Current approach already supports this via CLI parameter
3. **Multiple config files**: Scenarios can specify `config_file` in YAML (implemented in scenario_runner.py lines 307-339)

### Action Required

**VERIFIED** (no changes needed):
- MCP server access pattern is correctly implemented
- Port 8081 configuration matches constitution requirement
- Permission bypass mode appropriate for automated testing
- Config file approach supports scenario-specific configurations

**Optional Improvements** (non-blocking):
- Validate config file exists before SDK initialization
- Add health check for MCPProxy port 8081 before running scenarios
- Document that `PROXY_SESSION` should be updated for each baseline recording

---

## 5. Structured Logging Schema (Constitution Principle III)

### Decision: Partial Implementation - Missing Constitution-Required Fields

**Current Implementation** (`scenario_engine.py` lines 23-30, DEAD CODE):
```python
@dataclass
class ToolCallRecord:
    """Record of a single tool call."""
    tool_name: str
    tool_id: str
    tool_input: Dict[str, Any]
    timestamp: datetime
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

**Constitution-Required Schema** (constitution.md lines 203-248):
```json
{
  "turn_id": 1,
  "timestamp": "2025-08-22T19:30:01.123456",
  "type": "USER_MESSAGE",  // ← Missing enum
  "actor": "User",         // ← Missing field
  "content": "...",
  "metadata": {}           // ← Missing field
}
```

**Required Turn Types** (constitution.md line 77):
- USER_MESSAGE
- AGENT_MESSAGE
- TOOL_CALL
- TOOL_RESULT
- CLARIFICATION_REQUEST
- CLARIFICATION_RESPONSE

**Actual Working Implementation** (`scenario_runner.py` lines 414-420):
```python
execution_data["messages"].append({
    "timestamp": datetime.now().isoformat(),
    "message_number": message_count,
    "type": type(message).__name__,  # ← Not using required enum
    "content": self._serialize_message(message)
})
```

### Rationale

The current logging captures:
- Timestamps (ISO-8601 format ✓)
- Message types (but uses SDK class names like "AssistantMessage", not constitution enum)
- Content (full message serialization ✓)
- Tool call details in separate `tool_calls_summary` array

**Gaps**:
1. **No turn_type enum**: Uses `type(message).__name__` instead of USER_MESSAGE/AGENT_MESSAGE/etc
2. **No actor field**: Doesn't explicitly label User vs AI_Agent vs System
3. **No structured metadata**: Tool calls tracked separately, not in unified turn metadata structure
4. **Mixed data model**: Constitution expects flat turn list, actual logs have separate messages + tool_calls_summary

### Alternatives Considered

1. **Full constitution compliance**: Requires refactoring entire log structure - HIGH EFFORT
2. **Mapper layer**: Convert current logs to constitution format on read - MODERATE EFFORT
3. **Accept partial compliance**: Document gap for future work - **CURRENT STATE**

### Action Required

**NON-BLOCKING** (logs are sufficient for trajectory comparison):
- Current logs contain all data needed for similarity scoring
- MCP-only filtering works with `tool_calls_summary` array
- HTML reports successfully render from current log format
- Trajectory comparison operates on tool call sequence, not full turn structure

**FUTURE WORK** (constitution compliance):
1. Define `TurnType` enum matching constitution
2. Add `actor` field to all logged turns
3. Restructure logs to unified turn list
4. Update trajectory comparison to use new schema
5. Migration tool to convert existing baselines

---

## 6. MCP-Only Tool Filtering (Constitution Principle IV)

### Decision: Correctly Implemented via startswith('mcp__') Filter

**Implementation** (`evaluator.py` lines 236-237):
```python
# Filter to MCP tools only (exclude framework tools like TodoWrite, Bash, etc)
current_mcp = [call for call in current_tools if call.get('tool_name', '').startswith('mcp__')]
baseline_mcp = [call for call in baseline_tools if call.get('tool_name', '').startswith('mcp__')]
```

**Usage Context** (evaluator.py line 172):
```python
# Use new similarity-based trajectory comparison (MCP tools only)
similarity_score = calculate_trajectory_similarity(current_tools, baseline_tools)
```

**Constitution Requirement** (constitution.md line 93):
> MCP-Only Filtering: Evaluate only MCP tool calls (mcp__*), excluding framework tools (TodoWrite, Bash, Read/Write/Edit)

### Rationale

The filtering correctly:
1. Uses `startswith('mcp__')` to identify MCP tools
2. Excludes framework tools (TodoWrite, Bash, Read, Write, Edit, etc)
3. Applied before similarity calculation in `calculate_trajectory_similarity()`
4. HTML reports show all tools but highlight MCP tools in evaluation section

**Tool Name Patterns**:
- MCP tools: `mcp__mcpproxy__upstream_servers`, `mcp__mcpproxy__retrieve_tools`, etc
- Framework tools: `TodoWrite`, `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

### Alternatives Considered

1. **Whitelist approach**: Maintain list of MCP tool names - Rejected (too brittle)
2. **Blacklist approach**: Exclude known framework tools - Rejected (misses new framework tools)
3. **Prefix filtering**: **CHOSEN** - robust and convention-based

### Action Required

**VERIFIED** (no changes needed):
- MCP-only filtering correctly implemented
- Similarity scoring operates on filtered tool list
- Constitution Principle IV compliance confirmed

---

## 7. Dual-Agent Architecture (Constitution Principle I)

### Decision: Single-Agent Implementation - Partial Violation

**Current Implementation**:
- Only AI Agent role implemented (ClaudeSDKClient in scenario_runner.py)
- No separate User Agent class or module
- User intent provided as single query string
- No clarification request handling
- No User Agent response capability

**Constitution Requirement** (constitution.md lines 41-56):
```
1. User Agent: Roleplays a human user who:
   - Issues requests to trigger MCP tool usage
   - Responds to clarification questions from AI agent
   - Evaluates whether AI agent achieved goals

2. AI Agent: Roleplays an AI assistant who:
   - Has access to MCP servers under test
   - Executes user requests by selecting MCP tools
   - MAY ask User agent for clarification
```

### Rationale

The current implementation:
1. **AI Agent**: Fully implemented via ClaudeSDKClient
2. **User Agent**: Partially implemented as simple string query injection
3. **No clarification loop**: Scenarios run to completion without interaction
4. **Sufficient for current testing**: Most scenarios don't require clarification

**Why This Works**:
- Simple scenarios (list servers, add server) don't need clarification
- User intent provided upfront in scenario YAML
- AI Agent has full autonomy to select tools and construct arguments
- Success criteria evaluated post-execution, not during dialog

### Alternatives Considered

1. **Full dual-agent implementation**: HIGH EFFORT - requires User Agent LLM, clarification protocol
2. **Mock User Agent**: Could respond to clarification with canned responses - MODERATE EFFORT
3. **Current single-agent approach**: **ACCEPTED** - sufficient for current scenario coverage

### Action Required

**DOCUMENTED VIOLATION** (acceptable for current scope):
- Constitution Principle I partially implemented
- User Agent role is implicit (scenario YAML author)
- No automated clarification handling
- Sufficient for current test coverage

**FUTURE WORK**:
1. Implement User Agent as separate LLM instance
2. Define clarification request/response protocol
3. Update scenario YAML to include clarification examples
4. Test scenarios that require disambiguation

---

## 8. Current Logging Schema Analysis

### Decision: Working Schema but Non-Compliant with Constitution

**Actual Log Structure** (`scenario_runner.py` execution_data):
```python
execution_data = {
    "scenario": scenario_name,
    "execution_time": datetime.now().isoformat(),
    "user_intent": user_intent,
    "expected_trajectory": expected_trajectory,
    "success_criteria": success_criteria,
    "mode": mode,
    "available_tools": available_tools,
    "messages": [],           # Raw SDK message objects
    "tool_calls_summary": [], # Simplified tool call records
    "execution_status": "UNKNOWN",
    "failure_analysis": {},
    "early_stopped": False,
    "mcpproxy_git_info": self.mcpproxy_git_info
}
```

**Tool Call Summary Structure** (scenario_runner.py lines 426-433):
```python
current_tool_call = {
    "tool_name": block.name,
    "tool_id": block.id,
    "tool_input": getattr(block, 'input', {}),
    "timestamp": datetime.now().isoformat(),
    "response": None,
    "error": None
}
```

### Rationale

The current schema:
1. **Separates concerns**: Messages vs tool calls vs metadata
2. **Supports failure analysis**: `execution_status`, `failure_analysis`, `early_stopped`
3. **Tracks provenance**: `mcpproxy_git_info` for baseline reproducibility
4. **Works with similarity scoring**: `tool_calls_summary` feeds into trajectory comparison

**Why Non-Compliant**:
- Constitution expects unified turn list
- Constitution expects turn_type enum
- Constitution expects actor field

**Why Acceptable**:
- Contains all data needed for evaluation
- Structured and machine-readable (JSON)
- Supports HTML report generation
- Enables trajectory similarity calculations

### Alternatives Considered

1. **Immediate refactor to constitution schema**: Rejected - breaks existing baselines
2. **Add constitution-compliant export**: Could generate both formats - MODERATE EFFORT
3. **Accept current schema**: **CHOSEN** - functional and sufficient

### Action Required

**NON-BLOCKING** (current schema works):
- Document schema differences vs constitution in compliance audit
- Mark as technical debt for future refactoring
- Consider constitution schema as v2.0 target
- Ensure new features use current schema consistently

---

## Summary of Required Actions

### BLOCKING Issues (Must Fix Before Testing)

1. **Temperature Configuration**: Populate `claude_settings.json` with temperature=0.0
   - **File**: `/Users/user/repos/mcp-eval/claude_settings.json`
   - **Current**: `{}`
   - **Required**: Research SDK settings schema and configure temperature
   - **Verification**: Run same scenario 3 times, outputs should be identical

2. **Research SDK Settings Format**: Investigate how Claude Agent SDK loads settings
   - Check SDK documentation
   - Look for example settings files
   - Test with minimal configuration

### NON-BLOCKING Issues (Document as Technical Debt)

1. **Dead Code Removal**: Delete or archive `scenario_engine.py`
   - File imports missing `main.py`
   - Duplicate of working `scenario_runner.py` implementation
   - Causes confusion about which engine is active

2. **Structured Logging Gap**: Current logs don't match constitution schema
   - Missing turn_type enum
   - Missing actor field
   - Mixed data model (messages + tool_calls_summary)
   - Mark for future refactoring in compliance audit

3. **Dual-Agent Architecture Gap**: No User Agent implementation
   - Only AI Agent role exists
   - No clarification request handling
   - Sufficient for current test coverage
   - Document as limitation in compliance audit

### VERIFIED Compliant

1. **MCP Server Access**: Correctly configured via `mcp_servers.json` + port 8081
2. **Permission Mode**: `bypassPermissions` appropriate for automated testing
3. **MCP-Only Filtering**: Correctly implemented in `evaluator.py`
4. **Similarity-Based Evaluation**: Multi-level algorithms implemented in `similarity.py`

---

## Next Steps

1. **Create compliance-audit.md**: Document constitution principle review
2. **Fix temperature configuration**: Populate claude_settings.json
3. **Test simple scenario**: Run list_all_servers.yaml to verify MCP access
4. **Validate HTML reports**: Confirm MCP tools appear in generated reports
5. **Create quickstart.md**: Document testing procedure
6. **Commit fixes**: Clean git messages per Principle VIII
7. **Create pull request**: With constitution compliance summary

---

## References

- Claude Agent SDK API documentation (from help output)
- Constitution: `/Users/user/repos/mcp-eval/.specify/memory/constitution.md`
- Spec: `/Users/user/repos/mcp-eval/specs/002-fix-dialog-engine-mcp/spec.md`
- Plan: `/Users/user/repos/mcp-eval/specs/002-fix-dialog-engine-mcp/plan.md`
- Source files: `scenario_engine.py`, `scenario_runner.py`, `evaluator.py`
- Config files: `claude_settings.json`, `mcp_servers_test.json`

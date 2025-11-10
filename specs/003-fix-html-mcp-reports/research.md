# Research: HTML Reports and MCP Tool Validation

**Feature**: 003-fix-html-mcp-reports
**Date**: 2025-11-10
**Status**: Completed

## Executive Summary

This research documents technical decisions for fixing empty HTML reports and enabling MCP tool access in the dockerized MCPProxy environment. The key findings are:

1. **Dialog Turns Rendering**: HTML reporter must read `dialog_turns` field from detailed_log.json
2. **MCPProxy Container Shell**: Alpine Linux base image lacks `/bin/bash` by default
3. **Diff Visualization**: Side-by-side comparison with color-coded turn differences
4. **Tool Access**: AI Agent requires properly configured MCP servers config pointing to port 8081

## Research Questions & Findings

### Q1: How should dialog turns be rendered in HTML reports?

**Decision**: Extract dialog turns from `detailed_log.json` and render chronologically with visual styling by turn type.

**Research Findings**:

- Current `html_reporter.py` reads `messages` and `tool_calls_summary` fields from detailed_log.json
- New dialog engine populates `dialog_turns` field with structured DialogTurn objects (Constitution Principle III)
- Each DialogTurn contains: `turn_id`, `timestamp`, `turn_type`, `actor`, `content`, `metadata`
- Turn types: USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE
- Actors: User, AI_Agent, System

**Rendering Approach**:

1. Check if `detailed_log.json` has non-empty `dialog_turns` field
2. If present, render dialog turns in chronological order (sorted by turn_id)
3. Visual styling by turn type:
   - USER_MESSAGE: Blue left border, user icon
   - AGENT_MESSAGE: Green left border, agent icon
   - TOOL_CALL: Orange left border, tool icon, expandable details
   - TOOL_RESULT: Nested under TOOL_CALL, shows success/error status
4. If `dialog_turns` is empty or missing, fall back to legacy `messages` rendering
5. Display metadata: timestamp, actor, turn type badge

**Code Location**: `src/mcp_eval/html_reporter.py` - modify `_generate_conversation_html()` method

**Data Flow**:
```
scenario_runner.py (DialogSession.execute)
  → execution_data["dialog_turns"] = session_result.get("turns", [])
  → detailed_log.json written by save_execution_results()
  → html_reporter.py reads detailed_log.json
  → _generate_conversation_html() renders dialog_turns
```

**References**:
- Existing: Line 405-496 in html_reporter.py (_generate_conversation_html)
- Dialog models: src/mcp_eval/dialog_models.py (DialogTurn structure)
- Constitution Principle III: Structured Dialog Logging

---

### Q2: What is causing "/bin/bash missing" error in MCPProxy container?

**Decision**: Add bash package to Alpine Linux base image in Dockerfile.

**Research Findings**:

- MCPProxy container uses `alpine:3.19` base image (testing/docker/Dockerfile line 1)
- Alpine Linux uses `/bin/sh` (ash shell) by default, not bash
- Current Dockerfile installs: `ca-certificates tzdata curl jq docker docker-compose sudo` (line 4)
- Entrypoint script uses `/bin/sh` and is compatible (line 1 of entrypoint.sh)
- Error likely occurs when upstream server processes expect `/bin/bash` for script execution

**Root Cause**: Upstream server configurations or MCPProxy subprocess invocations may use `#!/bin/bash` shebang or execute bash-specific commands.

**Solution**: Add `bash` to Alpine package installation line in Dockerfile:

```dockerfile
RUN apk add --no-cache ca-certificates tzdata curl jq docker docker-compose sudo bash
```

**Alternative Considered**: Change base image to `ubuntu:22.04` - REJECTED because:
- Increases image size (100MB+ vs 5MB Alpine)
- Adds unnecessary complexity for single package dependency
- Alpine is standard for containerized Go applications

**Testing Strategy**:
1. Rebuild Docker image with bash installed
2. Run scenario that triggers upstream server connections
3. Check container logs for bash-related errors
4. Verify MCP tool invocations succeed

**Code Location**: `testing/docker/Dockerfile` line 4

**Impact**: Minimal - adds ~1-2MB to image size, no breaking changes

---

### Q3: How should trajectory differences be visualized in comparison reports?

**Decision**: Side-by-side dialog turn display with diff highlighting for added/removed/modified turns.

**Research Findings**:

- Current comparison HTML uses side-by-side layout (line 1270-1289 in html_reporter.py)
- Shows current vs baseline execution in two columns
- No turn-by-turn diff visualization currently implemented
- Tool invocation comparison exists (per_invocation_results) but not dialog turn comparison

**Diff Visualization Approach**:

1. **Color Coding**:
   - Green highlight: Turns present in current but not in baseline (ADDED)
   - Red highlight: Turns present in baseline but not in current (REMOVED)
   - Yellow highlight: Turns present in both but with different content (MODIFIED)
   - No highlight: Turns match exactly

2. **Matching Algorithm**:
   - Match by turn sequence position first
   - If turn types differ at position, mark as MODIFIED
   - If current has extra turns after baseline ends, mark as ADDED
   - If baseline has turns after current ends, mark as REMOVED

3. **Content Comparison**:
   - Tool calls: Compare tool_name and tool_input (use existing similarity scoring)
   - Messages: Simple string equality check
   - Tool results: Compare success/error status

4. **Visual Presentation**:
   - Add diff badge to turn header (ADDED/REMOVED/MODIFIED/MATCH)
   - Use border color to indicate diff type
   - Show content differences inline for MODIFIED turns

**Implementation Complexity**: Medium - requires turn alignment algorithm and additional CSS styling

**Alternative Considered**: Unified diff view (like git diff) - REJECTED because side-by-side is more intuitive for reviewing conversation flows

**Code Location**:
- New method: `_generate_comparison_dialog_turns_html()` in html_reporter.py
- Modify: `_generate_comparison_conversation_html()` to call new method
- Add CSS: Diff highlighting styles in `_get_embedded_styles()`

**Testing Strategy**:
1. Create baseline with 5 turns
2. Create evaluation run with 7 turns (2 added, 1 modified)
3. Generate comparison report
4. Verify diff highlights visible and accurate

---

### Q4: How to ensure AI Agent can access MCP tools from dockerized MCPProxy?

**Decision**: Verify MCP servers configuration points to correct port and container is healthy before scenario execution.

**Research Findings**:

- AI Agent uses `claude-agent-sdk` with MCP configuration (agents.py line 136-146)
- MCP config specified in `mcp_config` parameter (default: "mcp_servers.json")
- Docker container exposes MCPProxy on port 8081 (docker-compose.yml line 8)
- Container health check exists but only for internal port 8080 (line 33-36)

**Current Configuration Flow**:
```
scenario_runner.py __init__
  → self.mcp_config = "mcp_servers.json"
  → AIAgent(mcp_config=self.mcp_config)
  → ClaudeSDKClient(mcp_servers=self.mcp_config)
```

**Verification Requirements**:

1. **Config File Validation**:
   - Check `mcp_servers.json` exists
   - Verify MCPProxy endpoint is `http://localhost:8081/mcp` (not 8080)
   - Validate JSON schema

2. **Container Health Check**:
   - Execute Docker ps command to verify container running
   - Check container name matches expected: `mcpproxy-test-test777-dind`
   - Verify port mapping: 8081:8080
   - Curl health endpoint: `http://localhost:8081/health`

3. **Tool Discovery Test**:
   - Optional pre-flight check to list available tools
   - Log discovered tool count for debugging
   - Graceful degradation if discovery fails (per current implementation in scenario_runner.py line 349-355)

**Error Scenarios**:

- Container not running → Restart container before scenario execution
- Wrong port in config → Update mcp_servers.json
- Network connectivity issues → Log detailed error and fail fast
- Invalid API key → Detect early and report (already handled in _has_api_key_error)

**Implementation Location**:
- Pre-run validation: Add to `execute_scenario()` before dialog session creation
- Container health check: Reuse existing `_restart_mcpproxy_docker()` verification logic (line 169-182)
- Config validation: New method `_validate_mcp_config()` in scenario_runner.py

**Testing Strategy**:
1. Start container with correct config pointing to port 8081
2. Run scenario that invokes MCP tools
3. Verify dialog_turns show successful TOOL_CALL and TOOL_RESULT
4. Check detailed_log.json for `is_error: false` in tool results

---

## Technical Constraints

### Existing Dependencies (from pyproject.toml)
- Python: >=3.11.1
- claude-agent-sdk: >=0.1.6
- click: >=8.2.1
- pydantic: >=2.11.7
- pyyaml: >=6.0.2
- rich: >=14.1.0
- python-dotenv: >=1.0.0

### Docker Environment
- Base image: alpine:3.19
- User: mcpproxy (non-root)
- Exposed ports: 8081 (external) → 8080 (internal)
- Volumes: Config, logs, data, Docker socket
- Health check: curl localhost:8080/health every 10s

### File Structure
```
src/mcp_eval/
├── html_reporter.py       # HTML report generation
├── dialog_models.py       # DialogTurn, TurnType, Actor
├── dialog_session.py      # DialogSession orchestrator
├── agents.py              # UserAgent, AIAgent
├── scenario_runner.py     # Scenario execution engine
└── evaluator.py           # Trajectory comparison

testing/docker/
├── Dockerfile             # Alpine + MCPProxy binary
├── docker-compose.yml     # Service definition
├── entrypoint.sh          # Container startup script
└── config-template.json   # MCPProxy configuration
```

## Best Practices Identified

### HTML Report Generation
1. **Progressive Enhancement**: Check for `dialog_turns` first, fall back to legacy `messages`
2. **Performance**: Limit rendered turns to reasonable count (200 max per Constitution success criteria)
3. **Accessibility**: Use semantic HTML, clear visual indicators, keyboard navigation for expandable sections
4. **Responsive Design**: Existing styles support mobile breakpoints (line 1456-1468)

### Diff Visualization
1. **Clarity**: Use consistent color scheme across all diff types
2. **Context**: Show surrounding context for modified turns (previous/next turn)
3. **Filtering**: Allow hiding unchanged turns to focus on differences
4. **Legend**: Include diff type legend at top of comparison section

### Docker Container Management
1. **Idempotency**: Container restart script should handle already-stopped state
2. **Health Validation**: Wait for health endpoint before declaring ready
3. **Error Reporting**: Log container output to help debug startup failures
4. **State Isolation**: Fresh container per test run ensures reproducibility

### MCP Tool Access
1. **Early Validation**: Check configuration before starting expensive dialog session
2. **Graceful Degradation**: Tool discovery failure should not block scenario execution (already implemented)
3. **Detailed Logging**: Log MCP connection attempts and tool invocations
4. **Timeout Handling**: Set reasonable timeouts for MCP calls (handled by claude-agent-sdk)

## Open Questions for Implementation

### Q1: Should dialog turn rendering be configurable?
**Options**:
- A) Always show all turns (simple, current approach)
- B) Collapsible turn groups (e.g., collapse consecutive agent messages)
- C) Filter by turn type (checkboxes to show/hide USER_MESSAGE, TOOL_CALL, etc.)

**Recommendation**: Start with Option A for MVP, add filtering controls (Option C) in future iteration

### Q2: How to handle very long dialog sessions (>200 turns)?
**Options**:
- A) Pagination (show 50 turns per page)
- B) Virtual scrolling (render only visible turns)
- C) Hard limit with warning (show first 200, warn if truncated)

**Recommendation**: Option C per Constitution Principle - performance optimization for >200 turns is out of scope

### Q3: Should MCPProxy container reset be automatic or manual?
**Options**:
- A) Auto-reset before each scenario execution (slow but deterministic)
- B) Manual reset via CLI flag `--reset-container` (fast but requires discipline)
- C) Reset only when config changes (hybrid approach)

**Recommendation**: Option C - reset when `config_file` specified or explicit flag passed (already partially implemented in scenario_runner.py line 332-343)

### Q4: How to display turn metadata in HTML?
**Options**:
- A) Show all metadata in expandable details section
- B) Show selective metadata as badges (is_error, tool_name, etc.)
- C) Tooltip on hover with full metadata JSON

**Recommendation**: Option B for key metadata (tool names, error status), Option C for complete metadata

## Recommendations

### Immediate Actions (Phase 1: Design)
1. Create data model documentation for DialogTurn → HTML rendering flow
2. Design HTML mockup for dialog turn display with turn type styling
3. Specify diff visualization color scheme and matching algorithm
4. Document MCPProxy validation requirements

### Implementation Priorities (Phase 2: Tasks)
1. **P0 (Blocker)**: Fix Dockerfile to include bash package
2. **P0 (Blocker)**: Add dialog_turns rendering to html_reporter.py
3. **P1 (Critical)**: Implement MCP config validation before execution
4. **P1 (Critical)**: Add turn-by-turn diff visualization to comparison reports
5. **P2 (Important)**: Add filtering controls for tool type display
6. **P3 (Nice-to-have)**: Metadata tooltip display on hover

### Testing Strategy
1. **Unit Tests**: DialogTurn serialization, HTML rendering logic
2. **Integration Tests**: Full scenario execution with dialog turns
3. **Regression Tests**: Verify backward compatibility with legacy messages format
4. **Container Tests**: Docker build and health check verification

## References

- Constitution Principle I: Dual-Agent Dialog Engine Architecture
- Constitution Principle III: Structured Dialog Logging
- Feature Spec: /Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/spec.md
- Existing HTML Reporter: /Users/user/repos/mcp-eval/src/mcp_eval/html_reporter.py
- Dialog Models: /Users/user/repos/mcp-eval/src/mcp_eval/dialog_models.py
- MCPProxy Dockerfile: /Users/user/repos/mcp-eval/testing/docker/Dockerfile

# Testing Quickstart: Dialog Engine Fix Validation

**Purpose**: Step-by-step validation procedure for verifying dialog engine constitution compliance and MCP integration fixes.

**Date**: 2025-11-10
**Feature Branch**: 002-fix-dialog-engine-mcp

---

## Prerequisites

### Required Software
- Python 3.11+ with uv package manager
- Docker Desktop (for MCPProxy container)
- jq (for JSON log analysis): `brew install jq` (macOS) or `apt-get install jq` (Linux)

### Required Configuration
- MCPProxy docker container running on port 8081
- Claude Agent SDK updated to >=0.1.6
- Environment variables set in .env file (must be sourced before running commands)
- CLAUDE_CODE_OAUTH_TOKEN configured in .env for authentication

### Initial Setup
```bash
# Verify uv installed
uv --version

# Sync dependencies
cd /path/to/mcp-eval
uv sync

# Source environment variables (REQUIRED before all commands)
source .env

# Verify required environment variables
if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then echo "✓ CLAUDE_CODE_OAUTH_TOKEN loaded"; fi
if [ -n "$MCPPROXY_SOURCE_PATH" ]; then echo "✓ MCPPROXY_SOURCE_PATH loaded"; fi
```

**IMPORTANT**: All test commands in this guide assume you have run `source .env` first to load environment variables, especially CLAUDE_CODE_OAUTH_TOKEN.

---

## Step 1: Verify Docker Container

### 1.1 Check MCPProxy Status
```bash
docker ps --filter "name=mcpproxy" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output**:
```
NAMES                           STATUS          PORTS
mcpproxy-test-test777-dind     Up 2 minutes    0.0.0.0:8081->8080/tcp
```

### 1.2 Test Health Endpoint
```bash
curl -f http://localhost:8081/health || echo "MCPProxy not ready"
```

**Expected Output**: HTTP 200 or health status JSON

### 1.3 Reset Container State (Required Before Each Test)
```bash
./testing/reset-mcpproxy.sh
```

**Expected Output**: Container restarted with fresh state

**Troubleshooting**:
- If container not running: `cd testing/docker && TEST_SESSION=test777-dind docker compose up -d`
- If port conflict: Check nothing else using 8081 with `lsof -i :8081`
- If health check fails: Check docker logs with `docker logs mcpproxy-test-test777-dind --tail 20`

---

## Step 2: Verify Temperature Configuration

### 2.1 Check Settings File Exists
```bash
cat claude_settings.json
```

**Expected Content**:
```json
{
  "temperature": 0.0
}
```

**If empty `{}`**: CRITICAL BLOCKER - Temperature not set, evaluation will be non-deterministic

### 2.2 Verify MCP Configuration
```bash
cat mcp_servers.json | grep -E 'url|8081'
```

**Expected Output**: URL pointing to `http://localhost:8081/mcp`

---

## Step 3: Run Simple Scenario

### 3.1 Execute Test Scenario
```bash
PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/list_all_servers.yaml
```

**Expected Output**:
```
🧪 Running 1 scenarios

list_all_servers               PASS   1.00

✅ 1 passed, 0 recorded, 0 failed
```

### 3.2 Check for SDK Errors
```bash
# Check for deprecation warnings in output
# Should see no warnings about deprecated methods or incorrect parameters
```

**Red Flags**:
- `DeprecationWarning: ...` - SDK API usage outdated
- `AttributeError: 'ClaudeSDKClient' has no attribute '...'` - Incorrect SDK method
- `ConnectionRefusedError: [Errno 61] Connection refused` - MCPProxy not accessible
- `PermissionError: ...` - MCP permission mode incorrect

---

## Step 4: Verify HTML Report Generation

### 4.1 Find Generated Report
```bash
ls -lt reports/ | head -5
```

**Expected Output**: HTML file with timestamp, e.g., `list_all_servers_baseline_20251110_143052.html`

### 4.2 Open Report in Browser
```bash
# macOS
open reports/list_all_servers_*.html

# Linux
xdg-open reports/list_all_servers_*.html

# Windows
start reports/list_all_servers_*.html
```

### 4.3 Visual Inspection Checklist

**Check for MCP Tool Invocations**:
- [ ] Conversation section shows "TOOL_CALL: mcp__mcpproxy__upstream_servers"
- [ ] Tool call arguments are visible
- [ ] Tool result content is displayed (not just "undefined")

**Check for Expandable Details**:
- [ ] Click tool call section - should expand showing full input/output JSON
- [ ] Response payloads are not truncated or empty
- [ ] No JavaScript errors in browser console (F12)

**Check for MCP-Only Filtering**:
- [ ] Trajectory evaluation section shows only mcp__* tools
- [ ] Framework tools (TodoWrite, Bash, Read/Write) excluded from similarity scoring
- [ ] Conversation logs show all tools, but evaluation focuses on MCP tools

**Check for Similarity Scores** (if comparing against baseline):
- [ ] Similarity badges display (0.0-1.0 range)
- [ ] Visual color coding (green=high similarity, yellow=medium, red=low)
- [ ] Per-invocation similarity breakdown visible

---

## Step 5: Validate Structured Logs

### 5.1 Check Detailed Log File Exists
```bash
ls -lh baselines/list_all_servers_baseline/list_all_servers_baseline/detailed_log.json
```

**Expected Output**: JSON file with size >1KB (contains conversation data)

### 5.2 Extract Tool Call Records
```bash
cat baselines/list_all_servers_baseline/list_all_servers_baseline/detailed_log.json | jq '.messages[] | select(.type == "TOOL_CALL")'
```

**Expected Output** (example):
```json
{
  "timestamp": "2025-11-10T14:30:52.123456",
  "type": "TOOL_CALL",
  "data": {
    "tool_name": "mcp__mcpproxy__upstream_servers",
    "tool_id": "toolu_abc123def456",
    "tool_input": {},
    "tool_block": { ... }
  }
}
```

### 5.3 Verify Required Fields
```bash
cat baselines/list_all_servers_baseline/list_all_servers_baseline/detailed_log.json | jq '.messages[] | select(.type == "TOOL_CALL") | {timestamp, type, tool_name: .data.tool_name}'
```

**Required Fields**:
- `timestamp` (ISO-8601 with microseconds)
- `type` (e.g., "TOOL_CALL", "TOOL_RESULT")
- `data.tool_name` (MCP tool name)
- `data.tool_input` (arguments passed)

**Constitution Compliance Check**:
- ⚠️ Missing `actor` field (User vs AI_Agent) - documented as technical debt
- ⚠️ Missing turn_type enum - documented as technical debt
- ✅ timestamp present
- ✅ tool_name and tool_input captured
- ✅ metadata available in tool_block

---

## Step 6: Test Determinism (Temperature=0.0)

### 6.1 Run Same Scenario Three Times
```bash
for i in {1..3}; do
  echo "Run $i:"
  ./testing/reset-mcpproxy.sh > /dev/null 2>&1
  PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/list_all_servers.yaml 2>&1 | grep -E 'PASS|FAIL|RECORDED'
done
```

**Expected Output**:
```
Run 1:
list_all_servers               PASS   1.00
Run 2:
list_all_servers               PASS   1.00
Run 3:
list_all_servers               PASS   1.00
```

### 6.2 Compare Tool Call Arguments Across Runs
```bash
# Extract tool inputs from 3 consecutive runs and compare
# Should be identical if temperature=0.0 working correctly
```

**Non-Determinism Indicators**:
- Different tool arguments (e.g., query wording varies)
- Different tool selection order
- Variable similarity scores on identical scenarios

**If non-deterministic**: Check `claude_settings.json` contains `"temperature": 0.0`

---

## Step 7: Verify Git Status (Constitution Principle VIII)

### 7.1 Check Uncommitted Files
```bash
git status --short
```

**Expected Output**: Modified files from SDK update visible

### 7.2 Stage Changes
```bash
git add -u  # Stage all tracked modified files
```

### 7.3 Verify No Unintended Changes Staged
```bash
git diff --cached --name-only
```

**Review Checklist**:
- [ ] No test data or baseline files accidentally staged
- [ ] No .env or secrets files staged
- [ ] Only necessary code fixes staged

---

## Success Criteria Checklist

### Constitution Compliance
- [ ] ✅ MCPProxy accessible on port 8081 (Principle VI)
- [ ] ✅ Temperature=0.0 set in claude_settings.json (Principle V)
- [ ] ✅ MCP-only filtering active in evaluator.py (Principle IV)
- [ ] ✅ Path-independent configuration via env vars (Principle VII)
- [ ] ⚠️ Structured logging partial (Principle III) - documented as tech debt
- [ ] ⚠️ Dual-agent architecture partial (Principle I) - documented as tech debt
- [ ] ❌ Dialog engine modularity (Principle II) - out of scope, deferred
- [ ] ⏳ Git commit hygiene (Principle VIII) - pending commit

### Functional Validation
- [ ] Scenario executes without SDK API errors
- [ ] HTML report generated with MCP tool calls visible
- [ ] Structured logs contain tool call records with required fields
- [ ] Deterministic output across 3 runs (same tool calls, same args)
- [ ] No deprecation warnings in console output
- [ ] MCP tools successfully invoked (not "permission denied")

### Readiness for Commit
- [ ] All tests passing
- [ ] Constitution compliance documented
- [ ] Git status shows only intended changes
- [ ] Ready to commit with clean message (no AI attribution)

---

## Troubleshooting Guide

### Issue: "Connection refused to port 8081"
**Solution**:
1. Check Docker container running: `docker ps | grep mcpproxy`
2. Restart container: `cd testing/docker && TEST_SESSION=test777-dind docker compose restart`
3. Check port mapping: Container port 8080 should map to host 8081

### Issue: "No module named 'claude_agent_sdk'"
**Solution**:
1. Verify dependency installed: `uv pip list | grep claude-agent-sdk`
2. Reinstall: `uv sync`
3. Check pyproject.toml has `claude-agent-sdk>=0.1.6`

### Issue: "Temperature not affecting determinism"
**Solution**:
1. Verify settings file syntax: `cat claude_settings.json | jq .`
2. Check SDK reads file: Add debug print in scenario_runner.py
3. Confirm ClaudeAgentOptions uses settings parameter

### Issue: "HTML report shows no tool calls"
**Solution**:
1. Check MCP server accessibility: `curl http://localhost:8081/health`
2. Verify mcp_servers.json points to correct port
3. Check permission_mode is "bypassPermissions" not "prompt"
4. Review scenario YAML has expected_trajectory with MCP tools

### Issue: "Git shows too many uncommitted files"
**Solution**:
1. Review what changed: `git status`
2. Unstage unwanted files: `git reset HEAD <file>`
3. Use .gitignore for generated reports/logs if not already ignored

---

## Next Steps After Validation

Once all success criteria pass:

1. **Create constitution compliance summary** for PR description
2. **Write clean commit message** (no AI attribution)
3. **Commit changes**: `git commit -m "Fix dialog engine MCP access and SDK compatibility"`
4. **Push branch**: `git push origin 002-fix-dialog-engine-mcp`
5. **Create pull request** with:
   - Constitution compliance summary
   - SDK API changes addressed
   - Test results (3/3 scenarios passing)
   - Link to compliance-audit.md

**PR Description Template**:
```markdown
## Summary
Fix dialog engine constitution compliance and MCP integration after Claude Agent SDK update to >=0.1.6.

## Constitution Compliance
- ✅ Principle V: Temperature=0.0 configured in claude_settings.json
- ✅ Principle VI: MCPProxy Docker connectivity verified
- ✅ Principle IV: MCP-only filtering confirmed in evaluator.py
- ⚠️ Principle III: Structured logging partial (tech debt documented)
- ⚠️ Principle I: Dual-agent architecture partial (tech debt documented)

## Changes
- Populated claude_settings.json with temperature configuration
- [Other fixes as needed]

## Testing
- 3/3 test scenarios passing with deterministic output
- HTML reports generated successfully
- MCP tool invocations verified in structured logs

See compliance-audit.md for detailed analysis.
```

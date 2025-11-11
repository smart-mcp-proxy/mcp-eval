# Quickstart: Testing HTML Reports and MCP Tool Access

**Feature**: 003-fix-html-mcp-reports
**Date**: 2025-11-10
**Audience**: Developers implementing or testing this feature

## Overview

This guide provides step-by-step instructions for:
1. Setting up the MCPProxy Docker environment
2. Running test scenarios to verify HTML report generation
3. Verifying dialog turns are displaying correctly
4. Testing MCP tool access from AI agent

## Prerequisites

**Required**:
- Docker Desktop installed and running
- Python 3.11+ with uv package manager
- Anthropic API key configured
- MCPProxy source code at `../mcpproxy-go` (or set `MCPPROXY_SOURCE_PATH`)

**Environment Variables**:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
export MCPPROXY_SOURCE_PATH="../mcpproxy-go"  # Optional, defaults to this
export TEST_SESSION="test777-dind"            # Optional, defaults to this
export TEST_PORT="8081"                       # Optional, defaults to this
```

**Repository Structure**:
```
mcp-eval/
├── src/mcp_eval/           # Source code
├── scenarios/              # Test scenarios
├── baselines/              # Reference baselines
├── testing/docker/         # Docker configuration
├── mcp_servers.json        # MCP configuration (must point to port 8081)
└── claude_settings.json    # Claude settings (temperature=0.0)
```

---

## Step 1: MCPProxy Docker Reset Procedure

**Purpose**: Ensure clean container state before running scenarios.

### Why Reset is Critical

Per CLAUDE.md MCPProxy Docker Container Requirements:
- MCPProxy maintains internal state (tool cache, upstream connections)
- State can contaminate test results and affect reproducibility
- Fresh container ensures consistent baseline conditions

### Reset Commands

```bash
# Navigate to docker directory
cd testing/docker

# Stop existing container
TEST_SESSION=test777-dind docker compose down

# Start fresh container
TEST_SESSION=test777-dind docker compose up -d

# Wait for container to be ready
sleep 5

# Verify container is running
docker ps --filter "name=mcpproxy" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output**:
```
NAMES                          STATUS              PORTS
mcpproxy-test-test777-dind     Up 5 seconds        0.0.0.0:8081->8080/tcp
```

### Health Check Verification

```bash
# Check container health
curl -f http://localhost:8081/health || echo "MCPProxy not ready"

# Check container logs for errors
docker logs mcpproxy-test-test777-dind --tail 20

# Verify MCPProxy is responding
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

**Expected Health Check Response**:
```json
{"status": "ok", "version": "..."}
```

---

## Step 2: Verify MCP Configuration

**Purpose**: Ensure mcp_servers.json points to correct port.

### Check Configuration File

```bash
# From project root
cat mcp_servers.json
```

**Required Configuration**:
```json
{
  "mcpServers": {
    "mcpproxy": {
      "url": "http://localhost:8081/mcp",
      "transport": "stdio"
    }
  }
}
```

**Common Mistakes**:
- ❌ Port 8080 (internal port) - will fail
- ❌ Port 8082 (wrong port) - connection refused
- ✅ Port 8081 (correct external port mapping)

### Validate Configuration

```bash
# Check if port 8081 is in config
grep "8081" mcp_servers.json || echo "ERROR: Wrong port in config"

# Verify config is valid JSON
python -m json.tool mcp_servers.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

---

## Step 2b: Verify MCP Pre-Flight Validation (NEW)

**Purpose**: Confirm automated MCP validation is working before running scenarios.

### What is Pre-Flight Validation?

As of feature 003-fix-html-mcp-reports, mcp-eval now includes **automated pre-flight validation** that runs before every scenario execution:

1. **Config Validation**: Checks if `mcp_servers.json` exists, is valid JSON, and points to port 8081
2. **Container Health Check**: Verifies MCPProxy Docker container is running and healthy
3. **Graceful Degradation**: Logs warnings but continues execution (non-blocking)

### Test Pre-Flight Validation

```bash
# Run any scenario to see validation output
uv run mcp-eval record --scenario scenarios/tool_management/list_all_servers.yaml
```

**Expected Output** (before scenario execution):
```
🔍 Running pre-flight validation...
✓ MCP config valid
✓ MCPProxy container healthy
```

**If Validation Fails** (warnings shown):
```
🔍 Running pre-flight validation...
⚠️  MCP config validation failed: MCPProxy URL should point to port 8081, found: http://localhost:8080/mcp
✓ MCPProxy container healthy
⚠️  Pre-flight validation issues detected, continuing with execution...
```

### Manual Validation Commands

You can also validate manually using Python:

```python
# From Python REPL or script
from mcp_eval.scenario_runner import FailureAwareScenarioRunner
from pathlib import Path

runner = FailureAwareScenarioRunner(
    output_dir=Path("test_output"),
    mcp_config="mcp_servers.json"
)

# Test config validation
config_valid, config_msg = runner._validate_mcp_config()
print(f"Config valid: {config_valid}")
if not config_valid:
    print(f"  Error: {config_msg}")

# Test container health
container_healthy, health_msg = runner._check_container_health()
print(f"Container healthy: {container_healthy}")
if not container_healthy:
    print(f"  Error: {health_msg}")
```

### Check Validation Results in Logs

After running a scenario, validation results are saved in `detailed_log.json`:

```bash
# View validation results
cat baselines/scenario_name/detailed_log.json | \
  jq '.mcp_validation'
```

**Expected Structure**:
```json
{
  "timestamp": "2025-11-10T16:30:00.123456",
  "config_valid": true,
  "container_healthy": true,
  "config_path": "/Users/user/repos/mcp-eval/mcp_servers.json",
  "container_name": "mcpproxy-test-test777-dind",
  "health_endpoint": "http://localhost:8081/health",
  "warnings": [],
  "config_message": "",
  "health_message": "MCPProxy healthy"
}
```

### Common Validation Failures

**1. Config File Not Found**:
```
⚠️  MCP config validation failed: Config file not found: mcp_servers.json
```
**Solution**: Ensure `mcp_servers.json` exists in project root

**2. Wrong Port in Config**:
```
⚠️  MCP config validation failed: MCPProxy URL should point to port 8081, found: http://localhost:8080/mcp
```
**Solution**: Update `mcp_servers.json` to use port 8081

**3. Container Not Running**:
```
⚠️  MCPProxy container health check failed: MCPProxy container not running
```
**Solution**: Start container with `cd testing/docker && TEST_SESSION=test777-dind docker compose up -d`

**4. Container Unhealthy**:
```
⚠️  MCPProxy container health check failed: Health check failed: Connection refused
```
**Solution**: Check container logs with `docker logs mcpproxy-test-test777-dind --tail 20`

---

## Step 3: Run Test Scenario

**Purpose**: Execute scenario to generate HTML report with dialog turns.

### Choose Test Scenario

**Simple Scenario** (recommended for initial testing):
```bash
# List available tools scenario
SCENARIO="scenarios/tool_management/list_all_servers.yaml"
```

**Complex Scenario** (for full feature testing):
```bash
# Add server with security check
SCENARIO="scenarios/security/add_server_with_security_check.yaml"
```

### Record Baseline

```bash
# From project root
uv run mcp-eval record --scenario "$SCENARIO"
```

**Expected Console Output**:
```
🚀 Executing scenario: list_all_servers
📋 List All Servers
🎯 Intent: List all configured upstream servers in MCPProxy
📊 Expected tools: 1

💬 Starting dialog session: session_a1b2c3d4
🎯 User intent: List all configured upstream servers in MCPProxy

👤 User: List all configured upstream servers in MCPProxy...
🤖 Agent: I'll query the MCPProxy to list all servers...
🔧 Tool Call: mcp__mcpproxy__upstream_servers
✅ Tool Success

💾 Results saved to baselines/tool_management/list_all_servers_baseline
```

### Verify Output Files

```bash
# Check baseline directory created
ls -la baselines/tool_management/list_all_servers_baseline/

# Should contain:
# - detailed_log.json
# - trajectory.txt
# - report.html (generated by html_reporter)
```

---

## Step 4: Verify Dialog Turns in HTML Report

**Purpose**: Confirm dialog turns are rendering correctly in HTML.

### Open HTML Report

```bash
# Find the generated HTML report
REPORT=$(find baselines/tool_management/list_all_servers_baseline -name "*.html" | head -1)

# Open in browser (macOS)
open "$REPORT"

# Or copy path to clipboard
echo "$REPORT" | pbcopy
```

### Visual Inspection Checklist

**Header Section**:
- ✅ Scenario name displays correctly
- ✅ User intent shown in blue box
- ✅ MCPProxy git hash visible (8 characters)
- ✅ Status badge shows SUCCESS (green)

**Conversation Timeline**:
- ✅ Turn 1: USER_MESSAGE with blue left border
  - Contains user intent text
  - Shows timestamp
  - Has user icon (👤)

- ✅ Turn 2: AGENT_MESSAGE with green left border
  - Contains agent response
  - Shows timestamp
  - Has agent icon (🤖)

- ✅ Turn 3: TOOL_CALL with orange left border
  - Tool name visible (e.g., mcp__mcpproxy__upstream_servers)
  - Parameter preview shown
  - Has expand icon (▶)
  - Click to expand shows:
    - Tool Input JSON (syntax highlighted)
    - Tool Response (formatted)

- ✅ Statistics section shows:
  - Tool call count
  - Message count
  - Execution status

**Empty Report Issues** (if dialog turns not showing):
- ❌ Check detailed_log.json has `dialog_turns` field
- ❌ Verify dialog_turns array is not empty
- ❌ Check HTML reporter code reads dialog_turns
- ❌ Inspect browser console for JavaScript errors

### Inspect Detailed Log

```bash
# Check if dialog_turns field exists
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '.dialog_turns | length'

# Should output: number > 0 (e.g., 4)

# View first dialog turn
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '.dialog_turns[0]'
```

**Expected Dialog Turn Structure**:
```json
{
  "turn_id": 1,
  "timestamp": "2025-11-10T14:32:15.123456",
  "turn_type": "USER_MESSAGE",
  "actor": "User",
  "content": "List all configured upstream servers in MCPProxy",
  "metadata": {
    "scenario_intent": "List all configured upstream servers in MCPProxy",
    "is_clarification_response": false
  }
}
```

---

## Step 5: Test MCP Tool Access

**Purpose**: Verify AI agent can discover and invoke MCP tools.

### Check Tool Discovery

```bash
# Search for tool discovery in detailed log
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '.available_tools'
```

**Expected Output**:
```json
{
  "discovery_method": "skipped",
  "note": "Tool discovery disabled to avoid connection issues",
  "discovered_at": "2025-11-10T14:32:14.000000",
  "tools": []
}
```

**Note**: Tool discovery currently skipped by design (scenario_runner.py line 349-355) to avoid connection issues. This is metadata-only and doesn't affect tool invocation.

### Verify MCP Tool Invocations

```bash
# Count MCP tool calls in dialog turns
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '[.dialog_turns[] | select(.turn_type == "TOOL_CALL" and .metadata.is_mcp_tool == true)] | length'

# Should output: 1 or more

# List all invoked MCP tools
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '[.dialog_turns[] | select(.turn_type == "TOOL_CALL" and .metadata.is_mcp_tool == true) | .metadata.tool_name]'
```

**Expected Output**:
```json
[
  "mcp__mcpproxy__upstream_servers"
]
```

### Check for Tool Errors

```bash
# Find any tool errors
cat baselines/tool_management/list_all_servers_baseline/detailed_log.json | \
  jq '[.dialog_turns[] | select(.turn_type == "TOOL_RESULT" and .metadata.is_error == true)]'

# Should output: [] (empty array for successful execution)
```

**If Tool Errors Found**:
1. Check MCPProxy container logs: `docker logs mcpproxy-test-test777-dind --tail 50`
2. Verify port mapping: `docker port mcpproxy-test-test777-dind`
3. Test MCPProxy endpoint: `curl -f http://localhost:8081/health`
4. Check MCP config: `cat mcp_servers.json | jq .mcpServers.mcpproxy.url`

---

## Step 6: Test Comparison Report

**Purpose**: Verify side-by-side comparison with similarity scores.

### Run Evaluation Against Baseline

```bash
# Compare current execution against baseline
uv run mcp-eval compare \
  --scenario "$SCENARIO" \
  --baseline baselines/tool_management/list_all_servers_baseline
```

**Expected Output**:
```
🚀 Executing scenario: list_all_servers
...
📊 Comparison Results:
  Overall Score: 1.000
  Trajectory Score: 1.000
  Status: PASS

💾 Comparison report saved to comparison_results/tool_management/list_all_servers_comparison.json
📊 HTML report generated: reports/list_all_servers_comparison_20251110_143215.html
```

### Verify Comparison HTML

```bash
# Open comparison report
COMP_REPORT=$(find reports -name "*list_all_servers_comparison*.html" | head -1)
open "$COMP_REPORT"
```

**Visual Inspection Checklist**:

**Header Section**:
- ✅ Shows both current and baseline git hashes
- ✅ Status badges for both executions
- ✅ Comparison summary with overall score

**Per-Invocation Analysis**:
- ✅ Each tool invocation has similarity score
- ✅ Score badge color-coded:
  - Green: ≥0.8 (good)
  - Yellow: 0.5-0.8 (warning)
  - Red: <0.5 (bad)
- ✅ Shows matched tool names
- ✅ Similarity calculation visible

**Dialog Turn Comparison** (NEW):
- ✅ Side-by-side diff view of conversations
- ✅ Color-coded changes:
  - 🟢 Green background: Added turns
  - 🔴 Red background: Removed turns
  - 🟡 Yellow background: Modified turns
  - ⚪ Gray background: Unchanged turns
- ✅ Character-level diff highlighting within modified turns
- ✅ Interactive filter controls:
  - Filter by change type (Added/Removed/Modified/Unchanged)
  - Shows count for each category
  - Checkboxes to show/hide specific types
- ✅ Summary statistics displayed (e.g., "21 Added, 0 Removed, 5 Modified")

**Side-by-Side Execution Comparison**:
- ✅ Left column: Current execution
- ✅ Right column: Baseline
- ✅ Dialog turns aligned by sequence
- ✅ Tool filter controls at top:
  - Show TodoWrite calls (checkbox)
  - Show non-MCP tools (checkbox)

---

## Step 7: Test Error Scenarios

**Purpose**: Verify error handling and reporting.

### Test Container Not Running

```bash
# Stop MCPProxy container
cd testing/docker
TEST_SESSION=test777-dind docker compose down

# Try to run scenario
uv run mcp-eval record --scenario scenarios/tool_management/list_all_servers.yaml

# Expected: Should detect container not running and report error
```

**Expected Error**:
```
❌ MCPProxy container not running
Run: cd testing/docker && TEST_SESSION=test777-dind docker compose up -d
```

### Test Wrong Port Configuration

```bash
# Backup config
cp mcp_servers.json mcp_servers.json.backup

# Change to wrong port
sed -i.tmp 's/8081/8080/g' mcp_servers.json

# Run scenario
uv run mcp-eval record --scenario scenarios/tool_management/list_all_servers.yaml

# Expected: Connection errors in tool invocations

# Restore config
mv mcp_servers.json.backup mcp_servers.json
rm mcp_servers.json.tmp
```

### Test Missing API Key

```bash
# Temporarily unset API key
unset ANTHROPIC_API_KEY

# Run scenario
uv run mcp-eval record --scenario scenarios/tool_management/list_all_servers.yaml

# Expected: API key error detected and reported

# Restore API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

---

## Debugging Tips

### Dialog Turns Not Showing

**Check 1: Verify dialog_turns populated**
```bash
cat baselines/scenario_name/detailed_log.json | jq '.dialog_turns | length'
# Should be > 0
```

**Check 2: Verify HTML reporter reads dialog_turns**
```bash
grep "dialog_turns" src/mcp_eval/html_reporter.py
# Should have code to read this field
```

**Check 3: Check browser console**
```javascript
// Open browser developer tools (F12)
// Check for JavaScript errors
// Verify HTML elements exist:
document.querySelectorAll('.message').length  // Should be > 0
```

### MCP Tools Not Accessible

**Check 1: Container health**
```bash
docker ps --filter "name=mcpproxy"
docker logs mcpproxy-test-test777-dind --tail 20
curl http://localhost:8081/health
```

**Check 2: Port mapping**
```bash
docker port mcpproxy-test-test777-dind
# Should show: 8080/tcp -> 0.0.0.0:8081
```

**Check 3: MCP config**
```bash
cat mcp_servers.json | jq .
# Verify URL is http://localhost:8081/mcp
```

**Check 4: Agent initialization**
```bash
# Check if AI agent initialized properly
cat baselines/scenario_name/detailed_log.json | \
  jq '.dialog_session_status'
# Should be "SUCCESS" or show error
```

### Similarity Scores Missing

**Check 1: Comparison result structure**
```bash
cat comparison_results/scenario_name.json | \
  jq '.per_invocation_results'
# Should have array of invocation results
```

**Check 2: MCP tool filtering**
```bash
# Verify only MCP tools scored
cat comparison_results/scenario_name.json | \
  jq '.per_invocation_results[] | select(.actual_tools[0].name | startswith("mcp__"))'
```

**Check 3: HTML rendering**
```bash
# Check if similarity badges rendered
grep "similarity-badge" reports/scenario_comparison.html
```

---

## Common Issues and Solutions

### Issue: Empty HTML Report

**Symptoms**: HTML report loads but shows no conversation turns

**Diagnosis**:
```bash
# Check if detailed_log.json has data
cat baselines/scenario_name/detailed_log.json | jq '.dialog_turns | length'
```

**Solutions**:
1. If length = 0: Dialog session failed, check execution logs
2. If length > 0: HTML reporter not reading dialog_turns, verify implementation
3. If file missing: Scenario execution failed before saving results

### Issue: Container Fails to Start

**Symptoms**: `docker compose up -d` fails or container exits immediately

**Diagnosis**:
```bash
docker logs mcpproxy-test-test777-dind
```

**Common Causes**:
- Missing mcpproxy binary: Build MCPProxy first (`cd ../mcpproxy-go && make build`)
- Permission issues: Check Docker socket permissions
- Port conflict: Another process using port 8081
- Config file invalid: Validate config-template.json syntax

**Solutions**:
```bash
# Check if mcpproxy binary exists
ls -la testing/docker/mcpproxy

# Check port availability
lsof -i :8081

# Validate config
jq . testing/docker/config-template.json
```

### Issue: Tool Invocations Fail

**Symptoms**: TOOL_RESULT shows is_error: true

**Diagnosis**:
```bash
# Check error messages
cat baselines/scenario_name/detailed_log.json | \
  jq '.dialog_turns[] | select(.turn_type == "TOOL_RESULT" and .metadata.is_error == true) | .content'
```

**Common Causes**:
- MCPProxy not ready: Increase wait time after container start
- Wrong endpoint: Verify mcp_servers.json URL
- API key invalid: Check ANTHROPIC_API_KEY
- Upstream server error: Check MCPProxy logs

**Solutions**:
```bash
# Wait longer for MCPProxy
sleep 10 && curl http://localhost:8081/health

# Test MCP endpoint directly
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Check MCPProxy upstream connections
docker exec mcpproxy-test-test777-dind cat /app/logs/main.log
```

---

## Quick Reference

### Essential Commands

```bash
# Reset MCPProxy container
cd testing/docker && TEST_SESSION=test777-dind docker compose down && docker compose up -d && cd -

# Record baseline
uv run mcp-eval record --scenario scenarios/path/to/scenario.yaml

# Compare against baseline
uv run mcp-eval compare --scenario scenarios/path/to/scenario.yaml --baseline baselines/path/to/baseline

# Check dialog turns
cat baselines/scenario_name/detailed_log.json | jq '.dialog_turns | length'

# View HTML report
open reports/scenario_name_*.html

# Check container health
docker ps --filter "name=mcpproxy" && curl http://localhost:8081/health
```

### File Locations

```
baselines/scenario_name/
  ├── detailed_log.json       # Execution data with dialog_turns
  ├── trajectory.txt          # Human-readable summary
  └── report.html             # HTML report (if generated)

reports/
  └── scenario_comparison_*.html  # Comparison reports

comparison_results/
  └── scenario_name.json      # Similarity scores and diff

testing/docker/
  ├── Dockerfile              # Container definition
  ├── docker-compose.yml      # Service configuration
  ├── config-template.json    # MCPProxy config
  └── logs/                   # MCPProxy logs
```

### Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key"           # Required
export MCPPROXY_SOURCE_PATH="../mcpproxy-go"      # Optional
export TEST_SESSION="test777-dind"                # Optional
export TEST_PORT="8081"                           # Optional
export MCP_SERVERS_CONFIG="./mcp_servers.json"    # Optional
```

---

## Next Steps

After verifying basic functionality:

1. **Run Full Test Suite**:
   ```bash
   uv run mcp-eval test --scenarios-dir scenarios/
   ```

2. **Generate Aggregate Reports**:
   ```bash
   uv run mcp-eval batch --scenarios scenarios/ --output reports/batch_results
   ```

3. **Review Constitution Compliance**:
   - Check Principle I: Dual-agent architecture working
   - Check Principle III: Structured logging complete
   - Check Principle VI: Docker isolation effective

4. **Test Edge Cases**:
   - Very long dialog sessions (>50 turns)
   - Multiple tool failures
   - Clarification requests
   - Different scenario types

---

## References

- Feature Spec: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/spec.md`
- Data Model: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/data-model.md`
- Research: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/research.md`
- Constitution: `/Users/user/repos/mcp-eval/.specify/memory/constitution.md`
- CLAUDE.md: `/Users/user/repos/mcp-eval/CLAUDE.md`

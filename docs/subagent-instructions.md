# MCP Testing Subagent Instructions

## Purpose
You are an MCP testing subagent. Your job is to run evaluation scenarios after MCP proxy code updates and identify broken tools.

## Core Responsibilities

### 1. Run Evaluation Pipeline
Execute the full evaluation pipeline after each MCP proxy update:

```bash
# Run all scenarios and compare with baselines
python full_eval.py --scenarios scenarios/ --output results/post_update_test --baselines baselines/

# Or run batch comparison only
python batch_compare.py --scenarios scenarios/ --baselines baselines/ --output reports/post_update/
```

### 2. Identify Broken Tools
Look for these indicators of broken tools:

**🔴 Critical Issues:**
- Tool calls return errors (`"is_error": true`)
- Tool calls timeout or fail completely
- Server connection failures
- Tool responses changed dramatically (score < 0.3)

**🟡 Warning Signs:**
- Tool trajectory scores dropped significantly (> 0.2 decrease)
- Success criteria no longer met
- Tool parameters changed unexpectedly
- New tools appeared/disappeared from server

### 3. Decision Matrix

| Overall Score | Trajectory Score | Action |
|---------------|------------------|---------|
| < 0.3 | Any | 🔴 **BROKEN** - Immediate investigation needed |
| 0.3 - 0.6 | < 0.5 | 🟡 **DEGRADED** - Review changes, may need baseline update |
| 0.6 - 0.8 | > 0.5 | 🟢 **ACCEPTABLE** - Monitor, consider baseline update |
| > 0.8 | > 0.7 | ✅ **GOOD** - All working correctly |

### 4. Report Generation
Always generate a status report in this format:

```markdown
# MCP Proxy Update Test Report

## Summary
- **Update Date**: YYYY-MM-DD
- **Scenarios Tested**: X/X passed
- **Overall Status**: GOOD/DEGRADED/BROKEN

## Critical Issues
- [Tool Name]: [Issue description]
- [Server Name]: [Connection/response problems]

## Degraded Performance
- [Scenario Name]: Score dropped from X.XX to X.XX
- [Reason]: [Tool behavior changed]

## Recommendations
- [ ] Update baseline for scenario X
- [ ] Investigate server Y connection issues
- [ ] Review tool Z parameter changes
```

---

# Setup Guide for MCP Testing Subagent

## Prerequisites
- Python 3.8+ with uv package manager
- Access to MCP proxy at `http://localhost:8080/mcp`
- Claude Code SDK credentials configured

## Installation

1. **Clone the evaluation project**:
```bash
git clone <repository-url>
cd claude-agent-project
```

2. **Install dependencies**:
```bash
uv sync
```

3. **Configure MCP connection**:
Edit `mcp_servers.json`:
```json
{
  "mcpServers": {
    "mcpproxy": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

## Daily Testing Workflow

### Step 1: Backup Current Baselines
```bash
# Create dated backup
cp -r baselines/ baselines_backup_$(date +%Y%m%d)/
```

### Step 2: Run Post-Update Tests
```bash
# Full evaluation pipeline
python full_eval.py \
  --scenarios scenarios/ \
  --output results/test_$(date +%Y%m%d_%H%M%S) \
  --baselines baselines/
```

### Step 3: Analyze Results
```bash
# Check the comprehensive report
cat results/test_*/comprehensive_evaluation_report.json | jq '.summary'

# Review individual scenario results
ls results/test_*/reports/
```

### Step 4: Update Baselines (if needed)
```bash
# Only update baselines for scenarios that are working correctly
# but have changed behavior patterns

# Example: Update specific scenario baseline
python mcp-eval.py record \
  --scenario scenarios/search_tools.yaml \
  --output baselines/search_tools_baseline_new

# Replace old baseline
mv baselines/search_tools_baseline baselines/search_tools_baseline_old
mv baselines/search_tools_baseline_new baselines/search_tools_baseline
```

## Automation with Cron

Add to crontab for daily testing:
```bash
# Run MCP tests daily at 9 AM after proxy updates
0 9 * * * cd /path/to/claude-agent-project && python full_eval.py --scenarios scenarios/ --output results/daily_$(date +%Y%m%d) --baselines baselines/ > logs/daily_test.log 2>&1
```

## Alert Thresholds

Configure alerts for:
- **Overall pass rate < 50%**: Critical infrastructure issue
- **Individual scenario score < 0.3**: Specific tool broken
- **Server connection failures**: Network/configuration problem
- **New error patterns**: Code regression introduced

## Quick Commands Reference

```bash
# Test single scenario
python mcp-eval.py record --scenario scenarios/search_tools.yaml --output test_run/

# Compare with baseline
python mcp-eval.py compare --scenario scenarios/search_tools.yaml --baseline baselines/search_tools_baseline/ --output comparison.json

# Batch test all scenarios
python batch_compare.py --scenarios scenarios/ --baselines baselines/ --output reports/batch/

# Full pipeline with new baselines
python full_eval.py --scenarios scenarios/ --output results/full_test --create-baselines
```

## Troubleshooting

**Common Issues:**
- **"No module named claude_code_sdk"**: Run `uv sync` to install dependencies
- **MCP connection timeout**: Check if proxy is running at `http://localhost:8080/mcp`
- **Permission denied errors**: Verify MCP server permissions in configuration
- **Tool not found errors**: Server may be down or tools changed after update

**Debug Commands:**
```bash
# Test MCP connection directly
curl http://localhost:8080/mcp/health

# Check proxy server status
python -c "from claude_code_sdk import ClaudeSDKClient; print('SDK working')"

# Verbose scenario execution
python mcp-eval.py record --scenario scenarios/search_tools.yaml --output debug_run/ --verbose
```
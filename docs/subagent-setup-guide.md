# MCP Testing Subagent Setup Guide

## Quick Setup (5 minutes)

### 1. Prerequisites
- Python 3.8+ with `uv`
- MCP proxy running at `localhost:8080/mcp`  
- Claude SDK credentials

### 2. Install
```bash
git clone <this-repo>
cd claude-agent-project
uv sync
```

### 3. Configure MCP
Create/edit `mcp_servers.json`:
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

### 4. Test Connection
```bash
# Quick health check
curl http://localhost:8080/mcp/health

# Test SDK
python -c "from claude_code_sdk import ClaudeSDKClient; print('✅ SDK works')"
```

### 5. Run First Test
```bash
# Test single scenario
python mcp-eval.py record --scenario scenarios/search_tools.yaml --output test_run/

# Should see: ✅ Scenario completed successfully
```

## Daily Workflow

### Morning Routine (after MCP updates)
```bash
# 1. Backup baselines
cp -r baselines/ baselines_backup_$(date +%Y%m%d)/

# 2. Run all tests  
python batch_compare.py --scenarios scenarios/ --baselines baselines/ --output reports/daily/

# 3. Check results
cat reports/daily/*/summary.json | jq '.overall_score'
```

### Read Results
- `< 0.5` → Something broken, investigate
- `> 0.8` → All good
- `0.5-0.8` → Some issues, review

### Fix Problems  
```bash
# See what failed
ls reports/daily/*/trajectory.txt

# Re-record if tool behavior changed (not broken)
python mcp-eval.py record --scenario scenarios/broken_one.yaml --output baselines/broken_one_baseline_new/
```

## Automation
Add to crontab:
```bash
# Test daily at 9 AM after updates
0 9 * * * cd /path/to/project && python batch_compare.py --scenarios scenarios/ --baselines baselines/ --output reports/$(date +%Y%m%d) > logs/daily.log
```

## Troubleshooting
- **"Connection refused"** → MCP proxy not running
- **"Tool not found"** → Server may be down after update  
- **"Permission denied"** → Check MCP server config
- **All scenarios fail** → SDK/proxy connection issue

## Pro Tips
- Keep baselines backed up before updates
- Only update baselines for working (not broken) scenarios
- Use verbose mode (`--verbose`) for debugging
- Check `comprehensive_evaluation_report.json` for detailed analysis

Total setup time: ~5 minutes if MCP proxy already running.
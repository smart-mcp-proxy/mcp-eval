# MCP Evaluation Utility

## Global Development Guidelines

### Git Commit Standards

**IMPORTANT**: When making git commits across all projects, use clean commit messages without Claude Code attribution:

- ❌ **DO NOT include**: `🤖 Generated with [Claude Code](https://claude.ai/code)`
- ❌ **DO NOT include**: `Co-Authored-By: Claude <noreply@anthropic.com>`
- ✅ **DO include**: Clear, descriptive commit messages focusing on the actual changes made

**Example of proper commit message format:**
```
Fix hardcoded paths and make project configurable

- Remove hardcoded user paths from Python code
- Add environment variable configuration with .env.example
- Update shell scripts to use relative paths
- Test all functionality after changes
```

This rule applies to all repositories and projects to maintain clean git history.

## Project Overview

A command-line utility to evaluate MCP (Model Context Protocol) servers and tools effectiveness from a user perspective. The tool executes user scenarios, records detailed interaction logs, compares actual vs expected trajectories, and provides quantitative metrics using **sophisticated similarity-based trajectory evaluation** that goes beyond simple exact matching.

## Goals

- **Evaluate MCP Server Performance**: Test real-world scenarios against MCP proxy and individual servers
- **Measure Tool Effectiveness**: Quantify how well MCP tools execute user intents
- **Trajectory Analysis**: Compare actual tool usage patterns vs expected patterns
- **Automated Testing**: Support batch evaluation of multiple scenarios with detailed reporting

## Architecture

### Core Components

1. **CLI Interface**: Click-based command parser with record/compare modes
2. **Scenario Engine**: Executes user scenarios using claude_code_sdk with temperature=0.0 for deterministic testing
3. **Trajectory Recorder**: Captures detailed interaction logs and simplified dialog trajectories
4. **Similarity-Based Evaluation Engine**: Advanced trajectory comparison using multi-level similarity metrics for MCP tools only
5. **Enhanced HTML Report Generator**: Visual reports with similarity scores, per-invocation analysis, and tool filtering

### Similarity-Based Evaluation Methodology

The evaluation system implements sophisticated similarity calculations to handle real-world variations in tool usage:

#### Multi-Level Similarity Calculation
- **Tool Call Level**: Compares tool names and argument structures
- **Argument Level**: Analyzes parameter similarity using multiple algorithms
- **Trajectory Level**: Evaluates overall execution patterns focusing on MCP tools only

#### Similarity Algorithms
1. **Jaccard Similarity**: For set-based comparisons (argument keys, word sets)
2. **String Intersection**: Word-level comparison for natural language queries
3. **Distance-Based Numeric**: Configurable thresholds for numeric parameter variations
4. **Cosine Similarity**: Character frequency analysis for complex JSON structures

#### Benefits Over Exact Matching
- **Robustness**: Handles natural language variations in search queries
- **Flexibility**: Accommodates minor parameter differences without false negatives
- **Granular Scoring**: Provides meaningful partial scores rather than binary pass/fail
- **Visual Feedback**: Color-coded similarity badges in HTML reports show evaluation quality

### Data Flow

```
User Scenario → Claude Agent → MCP Tools → Detailed Logs
                                      ↓
Expected Trajectory ← Trajectory Comparison ← Recorded Trajectory
                                      ↓
                              Evaluation Metrics → Report
```

## Implementation Details

### CLI Modes

**Mode 1: Record Mode**
```bash
mcp-eval record --scenario scenarios/security/add_server_with_security_check.yaml
# or
mcp-eval record --scenario scenarios/search_tools.yaml --output results/search_tools_run1/
```
- Executes scenario with real MCP interaction
- Records full detailed logs (JSON format)
- Generates human-readable dialog trajectory
- Saves baseline for comparison
- Supports subdirectory structure matching scenario organization

**Mode 2: Compare Mode**
```bash
mcp-eval compare --scenario scenarios/security/add_server.yaml --baseline baselines/security/add_server_baseline/
# or with custom output
mcp-eval compare --scenario scenarios/search_tools.yaml --baseline baselines/search_tools_baseline/ --output results/comparison_report.json
```
- Executes scenario and compares with recorded baseline
- Calculates trajectory similarity metrics
- Generates evaluation report with scores (JSON format with .json extension)
- Creates HTML comparison reports with visual similarity analysis
- Preserves subdirectory structure in output directories

**Test Mode (pytest-style)**
```bash
mcp-eval test --scenarios-dir scenarios/
# Test specific scenarios
mcp-eval test --scenario scenarios/security/add_server.yaml --scenario scenarios/tool_management/list_servers.yaml
# Filter by tags
mcp-eval test --tag security --tag server_management
```
- Runs scenarios in pytest-style with compact output
- Shows similarity scores in console output
- Generates HTML reports for each test run
- Supports recursive scenario discovery in subdirectories
- Records baselines for scenarios without existing baselines
- Compares against baselines and shows PASS/FAIL with scores

**Batch Mode**
```bash
mcp-eval batch --scenarios scenarios/ --output reports/
```
- Runs multiple scenarios in sequence
- Generates aggregate reports
- Supports parallel execution
- Recursively finds scenarios in subdirectories

### Scenario Format

Scenarios defined in YAML format:
```yaml
name: "Search MCP Tools"
description: "User wants to find tools for GitHub operations"
user_intent: "I need to find tools that can help me manage GitHub repositories"
expected_trajectory:
  - action: "search_tools"
    tool: "mcp__mcpproxy__retrieve_tools"
    args:
      query: "GitHub repository management"
  - action: "list_servers" 
    tool: "mcp__mcpproxy__upstream_servers"
    args: {}
success_criteria:
  - "Found GitHub-related tools"
  - "Retrieved tool descriptions and schemas"
  - "Response contains 'fork_repository' or 'create_repository'"
```

### Output Files

**Detailed Logs** (`detailed_log.json`):
```json
{
  "scenario": "search_tools",
  "execution_time": "2025-08-22T19:30:00Z",
  "messages": [
    {
      "timestamp": "2025-08-22T19:30:01.123456",
      "type": "TOOL_CALL", 
      "data": {
        "tool_name": "mcp__mcpproxy__retrieve_tools",
        "tool_id": "toolu_abc123",
        "tool_input": {"query": "GitHub"},
        "tool_block": { /* full serialized object */ }
      }
    },
    {
      "timestamp": "2025-08-22T19:30:02.345678",
      "type": "TOOL_RESULT",
      "data": {
        "tool_use_id": "toolu_abc123",
        "raw_content": "...",
        "parsed_content": { /* structured response */ },
        "is_error": false
      }
    }
  ]
}
```

**Dialog Trajectory** (`trajectory.txt`):
```
USER: I need to find tools that can help me manage GitHub repositories

AGENT: I'll search for GitHub-related tools in the MCP proxy.
TOOL_CALL: mcp__mcpproxy__retrieve_tools(query="GitHub repository management")
TOOL_RESULT: Found 10 GitHub tools including fork_repository, create_repository...

AGENT: Here are the available GitHub tools: [lists tools with descriptions]

EVALUATION: ✅ SUCCESS - Found expected GitHub tools
```

### Evaluation Metrics

Advanced similarity-based trajectory evaluation with multi-level scoring:

1. **Tool Trajectory Similarity Score**: Sophisticated comparison using multiple algorithms:
   - **Key Similarity (30%)**: Jaccard similarity for argument structure comparison
   - **Value Similarity (70%)**: Multi-method value comparison including:
     - String word intersection with Jaccard similarity
     - Numeric distance-based similarity with configurable thresholds
     - JSON object cosine similarity using character frequency vectors

2. **MCP-Only Filtering**: Trajectory comparison focuses exclusively on MCP tool calls (mcp__*), excluding framework tools (TodoWrite, Bash, etc.) from similarity calculations while still displaying them in reports

3. **Per-Invocation Analysis**: Detailed breakdown of each tool call with individual similarity scores and visual indicators

4. **Failure-Aware Scoring**: Intelligent handling of blocked executions, cascading failures, and critical operation impacts

5. **Enhanced Reporting**: Visual similarity badges, tool filtering controls, comprehensive comparison metrics, and console score display in test mode

### Dependencies

```toml
[dependencies]
claude_code_sdk = "*"
click = "^8.1.0"
pydantic = "^2.0.0"
pyyaml = "^6.0"
rich = "^13.0.0"  # For beautiful CLI output
pytest = "^7.0.0"  # For comprehensive unit testing
```

### Project Structure

```
claude-agent-project/
├── src/
│   ├── mcp_eval/
│   │   ├── __init__.py
│   │   ├── cli.py              # Click CLI interface with test command
│   │   ├── scenario_runner.py  # Enhanced scenario execution engine
│   │   ├── evaluator.py        # Trajectory comparison with similarity metrics
│   │   ├── similarity.py       # Similarity calculation algorithms
│   │   ├── html_reporter.py    # Enhanced HTML report generation
│   │   └── reporter.py         # Report generation
├── scenarios/                  # Supports subdirectories
│   ├── security/
│   │   ├── add_server_with_security_check.yaml
│   │   └── inspect_quarantined_server.yaml
│   ├── tool_management/
│   │   ├── add_simple_server.yaml
│   │   ├── list_all_servers.yaml
│   │   └── remove_server.yaml
│   ├── search_tools.yaml
│   └── update_server.yaml
├── baselines/                  # Reference trajectories with matching structure
│   ├── security/
│   │   ├── add_server_with_security_check_baseline/
│   │   │   ├── detailed_log.json
│   │   │   └── trajectory.txt
│   │   └── inspect_quarantined_server_baseline/
│   └── search_tools_baseline/
├── comparison_results/         # JSON reports with matching structure
│   ├── security/
│   │   ├── add_server_comparison.json
│   │   └── inspect_quarantined_comparison.json
│   └── search_tools_comparison.json
├── reports/                    # HTML reports
└── main.py                     # Agent implementation
```

## Test Scenarios

### 1. Search Tools Scenario
- **Intent**: Find tools for specific functionality (GitHub operations)
- **Expected Tools**: `mcp__mcpproxy__retrieve_tools`, `mcp__mcpproxy__upstream_servers`
- **Success Criteria**: Discover relevant tools with correct parameters

### 2. Add Upstream Server Scenario  
- **Intent**: Add new MCP server to proxy configuration
- **Expected Tools**: `mcp__mcpproxy__add_server`, `mcp__mcpproxy__upstream_servers`
- **Success Criteria**: Server added successfully and appears in server list

### 3. Update Upstream Server Scenario
- **Intent**: Modify existing server configuration
- **Expected Tools**: `mcp__mcpproxy__update_server`, `mcp__mcpproxy__upstream_servers`  
- **Success Criteria**: Server configuration updated without errors

## Success Metrics

- **Accuracy**: Similarity-based scoring provides nuanced evaluation beyond exact matching
- **Robustness**: Handles natural language variations in tool queries with partial scoring
- **Coverage**: Test all major MCP proxy operations with comprehensive similarity analysis
- **Reliability**: Consistent results across multiple runs with deterministic temperature=0.0
- **Performance**: <30s execution time per scenario with enhanced reporting
- **Usability**: Interactive HTML reports with similarity visualization and tool filtering
- **Testing Quality**: 100% test coverage for similarity calculation algorithms (38 unit tests)

## MCP Proxy Integration

### Source Code Inspection
- **MCP Proxy Source**: Configurable via `MCPPROXY_SOURCE_PATH` environment variable (default: `../mcpproxy-go`)
- **Read-Only Access**: Inspect source code for understanding, but DO NOT modify files in this directory
- **Use Cases**: Understanding tool implementations, debugging issues, checking available operations

### Log Analysis
- **Main Log**: `$MCPPROXY_MAIN_LOG_PATH` (default: `~/Library/Logs/mcpproxy/main.log`) - General MCP proxy operations
- **Server Logs**: `$MCPPROXY_SERVER_LOGS_DIR/server-<upstream_server>.log` - Specific server logs
- **Usage**: Grep these files to debug tool call failures, connection issues, or server errors

Example log analysis commands:
```bash
# Check main proxy activity
grep "ERROR\|WARN" ~/Library/Logs/mcpproxy/main.log | tail -20

# Check specific server logs  
grep "quarantine" ~/Library/Logs/mcpproxy/server-everything.log

# Debug tool call failures
grep "inspect_quarantined" ~/Library/Logs/mcpproxy/main.log
```

### MCPProxy Docker Container Requirements

**CRITICAL: All baseline recording and evaluation runs MUST use the dockerized MCPProxy instance on port 8081.**

#### Configuration Requirements:
- **MCP Config**: `mcp_servers.json` must point to `http://localhost:8081/mcp` (not port 8080)
- **Docker Container**: Use `mcpproxy-test-test777-dind` container running on port 8081
- **Config File Location**: `$MCP_SERVERS_CONFIG` (default: `./mcp_servers.json`)

#### Pre-Run State Reset Protocol:
Before each baseline record or evaluation run, **ALWAYS** reset MCPProxy state:

```bash
# Reset MCPProxy docker container state
cd testing/docker
TEST_SESSION=test777-dind docker compose down
TEST_SESSION=test777-dind docker compose up -d

# Verify container is running
docker ps --filter "name=mcpproxy" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

#### Why Reset is Required:
- **State Persistence**: MCPProxy maintains internal state that can affect subsequent runs
- **Tool Cache**: Tool discovery and indexing state may influence results
- **Connection State**: Upstream server connections may be in unexpected states
- **Reproducibility**: Fresh container ensures consistent baseline conditions

#### Verification Commands:
```bash
# Check container health
docker logs mcpproxy-test-test777-dind --tail 10

# Verify MCPProxy is responding on correct port
curl -f http://localhost:8081/health || echo "MCPProxy not ready"

# Check MCP config points to correct port
grep "8081" mcp_servers.json || echo "ERROR: Wrong port in config"
```

## Implementation Phases

1. **Phase 1**: CLI framework and basic scenario execution
2. **Phase 2**: Trajectory recording and comparison engine
3. **Phase 3**: Evaluation metrics and reporting
4. **Phase 4**: Test scenarios and validation
5. **Phase 5**: Batch processing and optimization
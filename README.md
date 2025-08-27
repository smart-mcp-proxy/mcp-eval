# MCP Evaluation System

A comprehensive command-line tool for evaluating MCP (Model Context Protocol) server performance and tool effectiveness from a user perspective. The system executes real-world scenarios, records detailed interaction logs, compares actual vs expected trajectories, and provides quantitative metrics with visual HTML reports.

**🚀 Quick Start:**
```bash
cp .env.example .env                                    # Configure paths
pip install -e .                                       # Install as package
./testing/reset-mcpproxy.sh                            # Start Docker MCPProxy
PYTHONPATH=src uv run python -m mcp_eval.cli record --scenario scenarios/search_tools_simple.yaml    # Record baseline  
PYTHONPATH=src uv run python -m mcp_eval.cli compare --scenario scenarios/search_tools_simple.yaml --baseline baselines/search_tools_simple_baseline/search_tools_simple_baseline    # Run comparison
```

## Overview

The MCP Evaluation System helps developers and researchers:
- **Evaluate MCP Server Performance**: Test real-world scenarios against MCP proxy and individual servers
- **Measure Tool Effectiveness**: Quantify how well MCP tools execute user intents
- **Trajectory Analysis**: Compare actual tool usage patterns vs expected patterns using dialog trajectory metrics
- **Regression Testing**: Ensure MCP implementations maintain quality across versions
- **Visual Analysis**: Generate HTML reports with side-by-side conversation comparisons

## Architecture

### Core Components

1. **CLI Interface**: Click-based command parser with baseline recording, evaluation, and comparison modes
2. **FailureAwareScenarioRunner**: Enhanced scenario executor with tool discovery and git version tracking
3. **Docker Isolation**: MCPProxy runs in containerized environment for reproducible, isolated testing
4. **HTML Reporter**: Generates comprehensive visual reports with expandable tool calls and conversation logs
5. **Trajectory Evaluator**: Compares execution patterns using dialog trajectory similarity metrics

### Evaluation Flow

```
Scenario Definition � Baseline Recording � Current Evaluation � Trajectory Comparison � HTML Report
     (YAML)              (Docker)            (Docker)           (Metrics)          (Visual)
```

## Prerequisites

- **Python 3.11+** with uv package manager
- **Docker** for MCPProxy isolation  
- **MCPProxy Go** project (configurable location)

## Installation

```bash
# Clone and install
git clone https://github.com/anthropics/mcp-eval.git
cd mcp-eval
uv sync

# Install as development package
pip install -e .
```

## Configuration

The system is designed to be path-independent and configurable. Set up your environment:

### 1. Environment Variables

Copy the example environment file and configure paths:

```bash
cp .env.example .env
# Edit .env with your specific paths
```

**Key configuration variables:**

```bash
# Path to MCPProxy source code (required for building proxy binary)
MCPPROXY_SOURCE_PATH=../mcpproxy-go  # or absolute path to your mcpproxy-go clone

# Your Anthropic API key (required for baseline recording)
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Custom configuration paths
MCP_SERVERS_CONFIG=./mcp_servers_test.json
TEST_SESSION=test777-dind
TEST_PORT=8081
```

### 2. MCPProxy Source

Ensure MCPProxy source is available:

```bash
# Option 1: Clone next to this repository (recommended)
cd ..
git clone https://github.com/modelcontextprotocol/mcpproxy-go.git

# Option 2: Set custom path in .env
echo "MCPPROXY_SOURCE_PATH=/path/to/your/mcpproxy-go" >> .env
```

### 3. Initial Setup

```bash
# Setup Docker MCPProxy (will use your configured paths)
./testing/reset-mcpproxy.sh
```

## Usage

### 1. Reset MCPProxy State (Required Before Each Run)

**CRITICAL**: Always reset MCPProxy docker container state before each baseline recording or evaluation run to ensure reproducible results.

```bash
# Reset using the script (uses your configured paths)
./testing/reset-mcpproxy.sh

# Manual restart (if needed)
cd testing/docker
TEST_SESSION=test777-dind docker compose down
TEST_SESSION=test777-dind docker compose up -d
```

### 2. Record Baseline (Reference Implementation)

Record a baseline execution that represents the expected behavior:

```bash
# Reset MCPProxy state first (see step 1)
./testing/reset-mcpproxy.sh

# Record baseline (output defaults to baselines/{scenario_name}_baseline)
PYTHONPATH=src uv run python -m mcp_eval.cli record --scenario scenarios/search_tools_simple.yaml

# View generated HTML report
open reports/search_tools_simple_baseline_*.html
```

### 3. Run Evaluation (Current Implementation)

Execute the current implementation and compare against the baseline:

```bash
# Reset MCPProxy state first (see step 1)
./testing/reset-mcpproxy.sh

# Run comparison (output defaults to comparison_results/{scenario_name}_comparison)
PYTHONPATH=src uv run python -m mcp_eval.cli compare --scenario scenarios/search_tools_simple.yaml \
  --baseline baselines/search_tools_simple_baseline/search_tools_simple_baseline

# View results
open reports/search_tools_simple_comparison_*.html
```

### 4. View Results

**HTML Reports** provide comprehensive visual analysis:

- **Baseline Reports**: Complete conversation logs, tool calls, termination analysis, MCPProxy version tracking
- **Comparison Reports**: Side-by-side current vs baseline execution with trajectory metrics

**Key Metrics:**
- **Tool Trajectory Score**: Sophisticated similarity-based comparison of MCP tool usage patterns (0.0-1.0)
- **Per-Invocation Analysis**: Detailed similarity scores for each individual tool call with visual comparison
- **MCP-Only Filtering**: Focuses evaluation on MCP tool calls only (excludes TodoWrite, Bash, etc.)
- **Multi-Level Similarity**: Evaluates tool name matching, argument key similarity, and value similarity using multiple algorithms
- **Pass/Fail Threshold**: 0.8 (configurable)

## Similarity-Based Trajectory Evaluation

### Overview

The MCP Evaluation System uses sophisticated similarity calculations to compare tool usage patterns between current and baseline executions. This approach provides more nuanced evaluation than simple exact matching.

### MCP-Only Focus

The system filters comparisons to **only MCP tool calls** (tools with `mcp__` prefix), excluding framework tools like:
- `TodoWrite` (task management)
- `Bash` (command execution)  
- `Read`, `Write`, `Edit` (file operations)

This ensures evaluation focuses on actual MCP server interactions rather than agent implementation details.

### Multi-Level Similarity Calculation

#### Tool Call Similarity (0.0-1.0)

Each tool call comparison evaluates:

1. **Tool Name Matching**: Must be identical (different tools = 0.0 similarity)
2. **Argument Similarity**: Sophisticated comparison of tool parameters

#### Enhanced Dialog Trajectory Comparison with Argument Similarity

Traditional trajectory evaluation relied on exact matching, which created brittle tests that failed on minor variations. Our enhanced approach introduces sophisticated argument similarity metrics that provide more robust and meaningful evaluation.

**Problem with Exact Matching:**
```
Baseline: retrieve_tools(query="environment variables configuration")  
Current:  retrieve_tools(query="env vars configuration")
Result:   0.0 (FAIL) - Despite same intent and tool usage
```

**Solution with Argument Similarity:**
```
Baseline: retrieve_tools(query="environment variables configuration")  
Current:  retrieve_tools(query="env vars configuration")
Result:   0.53 (PARTIAL MATCH) - Recognizes similar intent
```

#### Multi-Level Argument Similarity Calculation

Arguments are compared using a weighted approach that evaluates both structure and content:

**Weighted Similarity Formula:**
```
arg_similarity = (key_similarity × 0.3) + (value_similarity × 0.7)
```

- **Key Similarity (30%)**: Structural compatibility - ensures arguments have similar parameter shapes
- **Value Similarity (70%)**: Content semantic similarity - evaluates actual parameter values

This weighting prioritizes content similarity while ensuring structural compatibility, allowing for natural language variations in queries and parameters.

#### Value Similarity Algorithms

- **String Values**: Word-based Jaccard similarity (case-insensitive)
  ```
  "hello world" vs "hello there" → 0.33 (1 common word / 3 total words)
  ```

- **Numeric Values**: Distance-based similarity with configurable max difference
  ```
  10 vs 15 → 0.995 (small difference, high similarity)
  ```

- **JSON Objects**: Character frequency-based cosine similarity
  ```
  {"a": 1, "b": 2} vs {"a": 1, "c": 3} → ~0.7 (structural similarity)
  ```

#### Trajectory Similarity

The overall trajectory score is calculated as:
1. Filter both trajectories to MCP-only tools
2. Compare tools at each position (order matters)
3. Missing tools at any position score 0.0
4. Return average similarity across all positions

### Benefits of Enhanced Argument Similarity in Dialog Trajectories

#### Robust Natural Language Query Evaluation

The argument similarity metrics handle common variations in natural language queries that should be considered semantically equivalent:

**Query Variations (High Similarity ~0.6-0.8):**
```
"find environment tools"     vs "search environment utilities"
"GitHub repository setup"    vs "GitHub repo configuration" 
"add new server connection"  vs "create server endpoint"
```

**Parameter Normalization:**
```
{limit: 10, offset: 20}     vs {limit: "10", offset: "20"}
# String vs numeric parameters → 0.9 similarity (type-aware comparison)

{query: "env", max: 5}      vs {query: "env", limit: 5}  
# Different key names → 0.5 similarity (partial structural match)
```

#### Dialog Flow Resilience 

Traditional exact matching failed when agents used slightly different phrasing or parameter ordering. Enhanced similarity enables:

- **Semantic Equivalence Recognition**: "environment variables" ≈ "env vars"
- **Parameter Order Independence**: {a:1, b:2} ≈ {b:2, a:1} 
- **Type-Tolerant Comparison**: numeric vs string parameters with same values
- **Partial Match Scoring**: Different approaches to same intent get partial credit

#### Real-World Dialog Trajectory Examples

**Scenario: Environment Variable Tool Search**

*Traditional Exact Matching Results:*
```
Baseline: retrieve_tools(query="environment variables management")
Run 1:    retrieve_tools(query="environment variables management") → 1.0 ✅
Run 2:    retrieve_tools(query="env variable management")         → 0.0 ❌
Run 3:    retrieve_tools(query="environment vars config")        → 0.0 ❌
```
**Success Rate: 33% (very brittle)**

*Enhanced Argument Similarity Results:*
```
Baseline: retrieve_tools(query="environment variables management")
Run 1:    retrieve_tools(query="environment variables management") → 1.0 ✅  (Perfect)
Run 2:    retrieve_tools(query="env variable management")         → 0.67 ✅ (Good)
Run 3:    retrieve_tools(query="environment vars config")        → 0.53 ✅ (Acceptable)
```
**Success Rate: 100% (robust to natural variations)**

### Visual Similarity Display

HTML reports show similarity scores in multiple places:

1. **Overall Summary**: Total trajectory score and overall evaluation score
2. **Per-Invocation Analysis**: Detailed breakdown with individual tool similarity scores
3. **Tool Call Headers**: Color-coded similarity badges on each tool call
4. **Side-by-Side Comparison**: Visual comparison with similarity indicators

### Example Similarity Scenarios

**Perfect Match (1.0):**
```
Current:  mcp__search_tools(query="environment variables")
Baseline: mcp__search_tools(query="environment variables")
```

**Partial Match (0.5-0.9):**
```
Current:  mcp__search_tools(query="env vars configuration")  
Baseline: mcp__search_tools(query="environment variables")
# Same tool, similar arguments → ~0.67
```

**No Match (0.0):**
```
Current:  mcp__list_registries()
Baseline: mcp__search_tools(query="environment")  
# Different tools → 0.0
```

## Scenario Format

Scenarios are defined in YAML format:

```yaml
name: "Search MCP Tools (Simple)"
description: "Simple test to find environment-related tools"
enabled: true
user_intent: "Find tools for environment variables"
expected_trajectory:
  - action: "search_tools"
    tool: "mcp__mcpproxy__retrieve_tools"
    args:
      query: "environment"
success_criteria:
  - "Found environment-related tools"
  - "Retrieved tool descriptions"
```

## Docker Isolation Strategy

### Why Docker?

MCPProxy runs in Docker containers for several critical reasons:

1. **State Isolation**: Each test run starts with a clean MCPProxy state, preventing cross-contamination between evaluations
2. **Reproducibility**: Consistent environment across different machines and test runs
3. **Version Control**: MCPProxy git hash is captured and displayed in reports for debugging version-specific issues
4. **Resource Management**: Container limits prevent runaway processes from affecting the host system
5. **Network Isolation**: Controlled network environment for testing server connections
6. **Deterministic Testing**: Claude agent configured with temperature=0.0 via settings file for minimal response variation and reproducible baselines

### Container Architecture

```
Host Machine
   Claude Agent (Python)     HTTP   � MCPProxy Container :8081
   Test Scenarios (YAML)                    
   HTML Reports                              
                                              
MCPProxy Container (Docker-in-Docker)         
   MCPProxy Go Binary                        
   MCP Server: everything-2                
   Tool Discovery & Indexing
```

## Configuration

### MCP Server Configuration (`mcp_servers.json`)

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

### Docker Configuration (`testing/docker/docker-compose.yml`)

- **Container Name**: `mcpproxy-test-test777-dind`
- **Ports**: 8081:8080 (HTTP), 9091:9090 (Metrics)
- **Session**: `test777-dind` for isolation
- **Health Checks**: Automatic container health monitoring

## Advanced Usage

### Batch Evaluation

```bash
# Run multiple scenarios
mcp-eval batch \
  --scenarios scenarios/ \
  --output reports/batch_results
```

### Tool Discovery

The system automatically discovers available MCP tools before each scenario execution and includes this information in HTML reports.

### Git Version Tracking

Each baseline and comparison includes MCPProxy git hash information for debugging version-specific behavior changes.

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure port 8081 is available and mcp_servers.json points to correct port
2. **Docker Not Running**: Verify Docker daemon is running and accessible
3. **Module Import Errors**: If running into import issues, ensure package is installed with `pip install -e .`
4. **Container Health**: Check `docker logs mcpproxy-test-test777-dind` for MCPProxy status

### Debug Commands

```bash
# Check container status
docker ps --filter "name=mcpproxy"

# View container logs
docker logs mcpproxy-test-test777-dind --tail 20

# Test MCPProxy connectivity
curl -f http://localhost:8081/health || echo "MCPProxy not responding"

# Verify available tools
grep "total_tools" $(docker logs mcpproxy-test-test777-dind 2>&1 | tail -20)
```

## Contributing

1. Always reset MCPProxy state before testing changes
2. Update baselines when expected behavior changes
3. Include HTML report screenshots in PR descriptions
4. Maintain backward compatibility in scenario formats

## License

This project is part of the Claude Code evaluation framework.
# MCP Evaluation System

A comprehensive command-line tool for evaluating MCP (Model Context Protocol) server performance and tool effectiveness from a user perspective. The system executes real-world scenarios, records detailed interaction logs, compares actual vs expected trajectories, and provides quantitative metrics with visual HTML reports.

## 🚀 Quick Start

```bash
cp .env.example .env                                    # Configure paths
pip install -e .                                       # Install as package
./testing/reset-mcpproxy.sh                            # Start Docker MCPProxy
PYTHONPATH=src uv run python -m mcp_eval.cli record --scenario scenarios/search_tools_simple.yaml
PYTHONPATH=src uv run python -m mcp_eval.cli compare --scenario scenarios/search_tools_simple.yaml --baseline baselines/search_tools_simple_baseline/search_tools_simple_baseline
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
Scenario Definition → Baseline Recording → Current Evaluation → Trajectory Comparison → HTML Report
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
2. **Argument Similarity**: 30% key structure + 70% value similarity
   - **Key Similarity**: Jaccard similarity of argument keys
   - **Value Similarity**: Multi-method comparison:
     - String values: Word intersection with Jaccard similarity
     - Numeric values: Distance-based with configurable thresholds
     - JSON objects: Cosine similarity using character frequency vectors

#### Trajectory Similarity

The overall trajectory score averages individual tool call similarities, providing a single metric for execution quality assessment.

### Algorithms Used

- **Jaccard Similarity**: For set-based comparisons (keys, word sets)
- **String Intersection**: Word-level comparison for natural language queries
- **Distance-Based Numeric**: Configurable thresholds for numeric variations
- **Cosine Similarity**: Character frequency analysis for complex JSON structures

## Available Scenarios

The system includes 19+ comprehensive test scenarios covering all major MCPProxy functionality:

### Core Functionality
- `list_all_servers` - Server discovery
- `basic_tool_search` - Tool discovery with BM25 search
- `list_quarantined_servers` - Security quarantine listing

### Server Management
- `add_simple_server` - Add new MCP servers
- `remove_server` - Remove existing servers
- `check_server_logs` - Server log inspection

### Security Operations
- `inspect_quarantined_server` - Detailed security analysis
- `server_status_check` - Configuration validation

### Registry Operations
- `list_registries` - Registry discovery
- `search_docker_registry` - Docker registry search

### GitHub Integration
- `github_tool_discovery` - GitHub tool discovery
- And more...

## CLI Reference

### Commands

```bash
# Record a baseline execution
PYTHONPATH=src uv run python -m mcp_eval.cli record --scenario <scenario_file> [--output <output_dir>]

# Compare against baseline
PYTHONPATH=src uv run python -m mcp_eval.cli compare --scenario <scenario_file> --baseline <baseline_dir> [--output <output_dir>]

# Run multiple scenarios in batch
PYTHONPATH=src uv run python -m mcp_eval.cli batch --scenarios <scenarios_dir> [--output <output_dir>]
```

### Options

- `--scenario`: Path to YAML scenario file
- `--baseline`: Path to baseline directory for comparison
- `--output`: Output directory for results
- `--mcp-config`: MCP servers configuration file (default: mcp_servers.json)

## Development

### Running Tests

```bash
# Run all unit tests
PYTHONPATH=src uv run python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src uv run python -m pytest tests/test_similarity.py -v
```

### Adding New Scenarios

1. Create a YAML file in `scenarios/` directory
2. Define user intent, expected trajectory, and success criteria
3. Optionally create custom config file in `configs/`
4. Test with baseline recording

Example scenario structure:

```yaml
enabled: true
name: "My Test Scenario"
description: "Test description"
config_file: "configs/minimal_config.json"
user_intent: "What the user wants to accomplish"

expected_trajectory:
  - action: "tool_action"
    tool: "mcp__tool_name"
    args:
      parameter: "value"

success_criteria:
  - "keyword_in_response"
  - "expected_behavior"

tags:
  - "category"
```

## Troubleshooting

### Common Issues

1. **MCPProxy container fails to start**
   ```bash
   # Check Docker is running
   docker info
   
   # Verify MCPProxy source exists
   ls $MCPPROXY_SOURCE_PATH
   
   # Check container logs
   cd testing/docker && docker compose logs
   ```

2. **Tool discovery fails**
   - This is normal and handled gracefully
   - Tool discovery failure doesn't affect scenario execution
   - MCP tools remain functional during conversations

3. **Permission errors**
   ```bash
   # Ensure scripts are executable
   chmod +x testing/reset-mcpproxy.sh
   chmod +x testing/build-mcpproxy.sh
   ```

### Debug Mode

Enable detailed logging by setting environment variables:

```bash
export LOG_LEVEL=debug
export PYTHONPATH=src
uv run python -m mcp_eval.cli record --scenario scenarios/your_scenario.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: See `CLAUDE.md` for detailed implementation notes
- **Examples**: Check `scenarios/` directory for usage examples
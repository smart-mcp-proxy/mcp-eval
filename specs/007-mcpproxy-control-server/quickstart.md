# Quickstart: MCPProxy Control Server

**Feature**: 007-mcpproxy-control-server

## Overview

This feature adds a control MCP server for the User Role in mcp-eval's dialog engine, enabling richer test scenarios where the simulated user can control mcpproxy state (unquarantine servers, read config, restart, view logs).

**Key Technology**: [FastMCP v2](https://gofastmcp.com) auto-generates the MCP server from mcpproxy's OpenAPI spec - no manual tool definitions needed!

## Prerequisites

1. Python 3.11+
2. Docker running with mcpproxy test container
3. mcpproxy-go repository at `../mcpproxy-go`
4. mcpproxy OpenAPI spec at `../mcpproxy-go/oas/swagger.yaml`

## Quick Setup

```bash
# Install dependencies (includes fastmcp>=2.0.0)
cd /Users/user/repos/mcp-eval
uv sync

# Verify mcpproxy is running
curl http://localhost:8081/healthz

# Run existing scenarios (backward compatible)
uv run mcp-eval test --scenarios scenarios/
```

## How It Works

The control MCP server is **auto-generated from mcpproxy's OpenAPI spec**:

```python
import yaml
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType

# Load mcpproxy's OpenAPI spec
with open("../mcpproxy-go/oas/swagger.yaml") as f:
    spec = yaml.safe_load(f)

# Create HTTP client for mcpproxy REST API
client = httpx.AsyncClient(base_url="http://localhost:8081")

# Auto-generate MCP server from spec
mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=client,
    name="mcpproxy-control",
    route_map_fn=control_route_mapper  # Filters to control endpoints only
)
```

## Using Enhanced Scenarios

### Creating a Scenario with User Control Actions

```yaml
# scenarios/enhanced/unquarantine_flow.yaml
enabled: true
name: "Add Server and Unquarantine"
description: "User adds server, then unquarantines after security check"
user_intent: "Add a new MCP server called 'test-server' using Docker"

expected_trajectory:
  - action: "add_server"
    tool: "mcp__mcpproxy__upstream_servers"
    args:
      operation: "add"
      name: "test-server"

user_control_actions:
  - trigger: "after_quarantine"
    action: "unquarantine_server"
    tool: "api_v1_servers_id_unquarantine"  # Auto-generated tool name
    args:
      id: "test-server"
    expected_result:
      success: true

success_criteria:
  - "test-server"
  - "unquarantined"

tags:
  - "server_management"
  - "quarantine"
```

### Running Enhanced Scenarios

```bash
# Run specific enhanced scenario
uv run mcp-eval test --scenario scenarios/enhanced/unquarantine_flow.yaml

# Run all scenarios including enhanced
uv run mcp-eval test --scenarios scenarios/
```

## Available Control Tools

Tools are **auto-generated** from OpenAPI paths. Tool names follow the pattern:
`/api/v1/path/{param}` → `api_v1_path_param`

| OpenAPI Endpoint | Auto-Generated Tool | Description |
|------------------|---------------------|-------------|
| `GET /api/v1/config` | `api_v1_config` | Read current mcpproxy configuration |
| `GET /api/v1/servers` | `api_v1_servers` | List all servers (filter for quarantined) |
| `POST /api/v1/servers/{id}/restart` | `api_v1_servers_id_restart` | Restart specific server |
| `GET /api/v1/servers/{id}/logs` | `api_v1_servers_id_logs` | Get server log entries |
| `POST /api/v1/servers/{id}/quarantine` | `api_v1_servers_id_quarantine` | Place server in quarantine |
| `POST /api/v1/servers/{id}/unquarantine` | `api_v1_servers_id_unquarantine` | Remove from quarantine |
| `GET /healthz` | `healthz` | Health check |

## Understanding Reports

### HTML Reports

Control server calls are displayed with distinct styling:
- **Blue badge**: Control tool calls `[CTRL]`
- **Green badge**: Agent MCP tool calls `[AGENT]`

### Compact Summary (summary.txt)

Token-efficient format for AI agents:

```text
# Scenario: Add Server and Unquarantine
Status: PASSED | Score: 0.95

## Tool Calls
[AGENT] mcp__mcpproxy__upstream_servers(add) -> OK
[CTRL] api_v1_servers_id_unquarantine(test-server) -> OK

## Errors
None
```

### detailed_log.json

Control calls use distinct types:
- `CONTROL_TOOL_CALL` - User Role invokes control tool
- `CONTROL_TOOL_RESULT` - Control tool result

## Claude Code Skill

When working from mcpproxy-go directory:

```bash
# Build and test mcpproxy changes
# (Invoke mcp-eval skill in Claude Code)

# The skill will:
# 1. Build mcpproxy binary
# 2. Deploy to test Docker container
# 3. Reset container state
# 4. Run mcp-eval scenarios
# 5. Report results
```

## Troubleshooting

### Control server not starting
```bash
# Check mcpproxy REST API is accessible
curl http://localhost:8081/healthz

# Verify API key is set (if required)
echo $MCPPROXY_API_KEY

# Verify OpenAPI spec exists
ls ../mcpproxy-go/oas/swagger.yaml
```

### Trigger not firing
- Ensure trigger type is valid: `after_tool_N`, `after_quarantine`, `on_error`, `before_completion`, `manual`
- Check logs for trigger evaluation messages

### Tool name mismatch
- Tool names are auto-generated from OpenAPI paths
- Use the pattern: `/api/v1/path/{param}` → `api_v1_path_param`
- Check `contracts/control-mcp-tools.yaml` for reference

### Scenario backward compatibility
- Scenarios without `user_control_actions` work unchanged
- No migration required for existing scenarios

## Sources

- [FastMCP v2 Documentation](https://gofastmcp.com/getting-started/welcome)
- [FastMCP OpenAPI Integration](https://gofastmcp.com/integrations/openapi)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)

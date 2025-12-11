# Research: MCPProxy Control Server

**Feature**: 007-mcpproxy-control-server
**Date**: 2025-12-10

## Research Topics

### 1. FastMCP v2 Framework with OpenAPI Integration

**Decision**: Use FastMCP v2 to auto-generate MCP server from mcpproxy's OpenAPI spec

**Rationale**:
- FastMCP v2 can ingest any OpenAPI spec and automatically convert operations into MCP tools
- No manual tool definition required - tools generated on-the-fly from `mcpproxy-go/oas/swagger.yaml`
- Production-ready with auth, testing, and deployment support
- Significantly reduces implementation effort

**Sources**:
- [FastMCP Official Docs](https://gofastmcp.com/getting-started/welcome)
- [FastMCP OpenAPI Integration](https://gofastmcp.com/integrations/openapi)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [FastMCP 2.0 Announcement](https://www.jlowin.dev/blog/fastmcp-2)

**Implementation Pattern**:
```python
import yaml
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Load mcpproxy's OpenAPI spec
with open("../mcpproxy-go/oas/swagger.yaml", "r") as f:
    openapi_spec = yaml.safe_load(f)

# Create HTTP client pointing to mcpproxy REST API
client = httpx.AsyncClient(
    base_url="http://localhost:8081",
    params={"apikey": os.getenv("MCPPROXY_API_KEY", "")}
)

# Generate MCP server from OpenAPI spec - tools created automatically!
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="mcpproxy-control",
    route_maps=[
        # Only expose specific endpoints as tools
        RouteMap(
            methods=["GET", "POST"],
            paths=[
                "/api/v1/config",
                "/api/v1/servers/{id}/restart",
                "/api/v1/servers/{id}/logs",
                "/api/v1/servers/{id}/unquarantine",
                "/api/v1/servers",
                "/healthz"
            ],
            mcp_type=MCPType.TOOL
        )
    ]
)

if __name__ == "__main__":
    mcp.run()
```

**Custom Route Mapping** (for filtering endpoints):
```python
from fastmcp.server.openapi import HTTPRoute, MCPType

def control_route_mapper(route: HTTPRoute, mcp_type: MCPType) -> MCPType | None:
    """Only expose control-relevant endpoints as tools."""
    control_paths = [
        "/api/v1/config",
        "/api/v1/servers",
        "/healthz",
    ]
    control_patterns = [
        "/api/v1/servers/{id}/restart",
        "/api/v1/servers/{id}/logs",
        "/api/v1/servers/{id}/unquarantine",
        "/api/v1/servers/{id}/quarantine",
    ]

    if route.path in control_paths:
        return MCPType.TOOL
    for pattern in control_patterns:
        if pattern.replace("{id}", "") in route.path:
            return MCPType.TOOL
    return MCPType.EXCLUDE  # Don't expose other endpoints

mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="mcpproxy-control",
    route_map_fn=control_route_mapper,
)
```

**Key Advantages over Manual Tool Definition**:
- Tools automatically match API schema - no manual sync needed
- Request/response validation handled by FastMCP
- Tool descriptions extracted from OpenAPI spec
- When mcpproxy API changes, just reload the spec

### 2. MCPProxy REST API Endpoints (from OAS)

**Available Endpoints** (mcpproxy-go/oas/swagger.yaml):

| Operation | Endpoint | Method | FR Requirement |
|-----------|----------|--------|----------------|
| Read Config | `/api/v1/config` | GET | FR-002 |
| Restart Server | `/api/v1/servers/{id}/restart` | POST | FR-002 |
| Get Server Logs | `/api/v1/servers/{id}/logs?tail=N` | GET | FR-002 |
| List Servers | `/api/v1/servers` | GET | FR-002 |
| Quarantine Server | `/api/v1/servers/{id}/quarantine` | POST | FR-002 |
| Unquarantine Server | `/api/v1/servers/{id}/unquarantine` | POST | FR-002 |
| Health Check | `/healthz` | GET | (diagnostic) |

**Authentication**: API key via query parameter `?apikey=<key>`

### 3. Dialog Engine Integration for User Role

**Decision**: Create separate UserAgent MCP client configuration

**Rationale**:
- User Role needs access to control MCP server only
- Agent Role continues using mcpproxy native MCP only
- Clear separation of concerns per FR-006/FR-007
- Reuse existing ClaudeAgentOptions pattern

**Integration Approach**:
```python
# User Role gets control MCP server (auto-generated from OAS)
user_mcp_config = {
    "mcpproxy-control": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mcp_eval.control_server"]
    }
}

# Agent Role keeps existing mcpproxy MCP
agent_mcp_config = existing_mcp_servers_json
```

### 4. Enhanced Scenario YAML Format

**Decision**: Add `user_control_actions` section to scenario YAML

**Rationale**:
- Backward compatible - existing scenarios without this section work unchanged
- Clear separation between agent expected trajectory and user control actions
- Matches existing `expected_trajectory` pattern

**Format**:
```yaml
name: "Unquarantine Flow"
user_intent: "Add and enable a new server"

expected_trajectory:
  - action: "add_server"
    tool: "mcp__mcpproxy__upstream_servers"
    args:
      operation: "add"
      name: "test-server"

user_control_actions:
  - trigger: "after_quarantine"  # When to execute
    action: "unquarantine_server"
    tool: "mcpproxy_control__api_v1_servers_id_unquarantine"  # Auto-generated tool name
    args:
      id: "test-server"
    expected_result:
      success: true
```

**Note**: Tool names are auto-generated from OpenAPI paths by FastMCP (e.g., `api_v1_servers_id_unquarantine`)

### 5. Logging and Report Differentiation

**Decision**: Add CONTROL_TOOL_CALL and CONTROL_TOOL_RESULT turn types

**Rationale**:
- Matches existing TurnType enum pattern
- Clear distinction in logs and reports
- Enables filtering in trajectory comparison

**New TurnTypes**:
```python
class TurnType(str, Enum):
    # Existing
    USER_MESSAGE = "USER_MESSAGE"
    AGENT_MESSAGE = "AGENT_MESSAGE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    # New
    CONTROL_TOOL_CALL = "CONTROL_TOOL_CALL"
    CONTROL_TOOL_RESULT = "CONTROL_TOOL_RESULT"
```

### 6. Compact Summary Report Format

**Decision**: Generate summary.txt with structured token-efficient format

**Rationale**:
- Under 500 tokens for typical scenarios
- Parseable by AI agents
- Clear visual distinction between control and agent calls

**Format**:
```text
# Scenario: Add Server with Unquarantine
Status: PASSED | Score: 0.95

## Tool Calls
[AGENT] mcp__mcpproxy__upstream_servers(add) -> OK
[AGENT] mcp__mcpproxy__retrieve_tools(query) -> OK
[CTRL] api_v1_servers_id_unquarantine(test-server) -> OK

## Errors
None
```

### 7. Claude Code Skill for Development

**Decision**: Create `.claude/commands/mcp-eval.md` skill file

**Rationale**:
- Standard Claude Code skill pattern
- Works from both mcp-eval and mcpproxy-go directories
- Enables streamlined build-test cycle

**Skill Content** (high-level):
```markdown
# MCP-Eval Development Skill

## Build MCPProxy
1. Navigate to mcpproxy-go directory
2. Run `go build -o mcpproxy ./cmd/mcpproxy`
3. Copy binary to Docker test container

## Run Scenarios
1. Reset Docker container state
2. Run `mcp-eval test --scenarios scenarios/`
3. Check reports/ for results

## Quick Commands
- `mcp-eval test --tag security`
- `mcp-eval batch --scenarios scenarios/ --output reports/`
```

## Dependencies to Add

```toml
# pyproject.toml additions
dependencies = [
    # Existing...
    "fastmcp>=2.0.0",     # MCP server framework v2 with OpenAPI support
    "httpx>=0.25.0",      # Async HTTP client (required by FastMCP)
    "pyyaml>=6.0",        # For loading OpenAPI YAML spec
]
```

## Open Questions Resolved

1. **Q**: How to start control MCP server alongside dialog engine?
   **A**: Start as subprocess using FastMCP stdio transport, managed by DialogSession

2. **Q**: How to handle mcpproxy API authentication?
   **A**: Pass API key via httpx client params, read from `MCPPROXY_API_KEY` env var

3. **Q**: How to trigger user control actions at right time?
   **A**: Use `trigger` field in scenario YAML (e.g., "after_quarantine", "after_tool_call")

4. **Q**: How to keep MCP tools in sync with mcpproxy API?
   **A**: FastMCP v2 auto-generates tools from OAS file - just reload spec when API changes

5. **Q**: What are the auto-generated tool names?
   **A**: FastMCP converts paths like `/api/v1/servers/{id}/unquarantine` to tool names like `api_v1_servers_id_unquarantine`

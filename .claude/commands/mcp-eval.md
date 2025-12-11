# MCP-Eval Development Skill

A Claude Code skill for streamlined MCPProxy build-test cycles during development.

## Overview

This skill automates the workflow for building MCPProxy, deploying to a test container, running evaluation scenarios, and reading results.

## Prerequisites

- Docker installed and running
- MCPProxy source code at `../mcpproxy-go` (relative to mcp-eval)
- Test container configured with `TEST_SESSION=test777-dind`

## Commands

### 1. Build MCPProxy Binary

Build the mcpproxy binary from Go source:

```bash
cd ../mcpproxy-go
go build -o mcpproxy ./cmd/mcpproxy
```

### 2. Deploy to Docker Test Container

Copy the built binary to the running test container:

```bash
# Get container ID
CONTAINER_ID=$(docker ps --filter "name=mcpproxy-test" --format "{{.ID}}" | head -1)

# Copy binary
docker cp ../mcpproxy-go/mcpproxy $CONTAINER_ID:/app/mcpproxy

# Restart the container to use new binary
docker restart $CONTAINER_ID
```

### 3. Reset MCPProxy State

Reset the test container to a clean state before running scenarios:

```bash
cd testing/docker
TEST_SESSION=test777-dind docker compose down
TEST_SESSION=test777-dind docker compose up -d

# Wait for container to be ready
sleep 3
docker logs mcpproxy-test-test777-dind --tail 5
```

### 4. Run Evaluation Scenarios

Run all scenarios:
```bash
uv run mcp-eval test --scenarios-dir scenarios/
```

Run specific scenarios:
```bash
uv run mcp-eval test --scenario scenarios/enhanced/unquarantine_flow.yaml
```

Run scenarios with specific tags:
```bash
uv run mcp-eval test --tag security --tag control_actions
```

### 5. Read Compact Summary Reports

After running scenarios, check the summary report:

```bash
# Find latest summary report
ls -lt reports/test_summary_*.html | head -1

# Or read the compact text summary (if generated with --compact-report)
cat reports/summary.txt
```

## Typical Workflow

1. **Make code changes** in mcpproxy-go
2. **Build**: `cd ../mcpproxy-go && go build -o mcpproxy ./cmd/mcpproxy`
3. **Deploy**: Copy binary to test container and restart
4. **Reset**: Reset mcpproxy state
5. **Test**: `uv run mcp-eval test --scenarios-dir scenarios/`
6. **Review**: Check reports for pass/fail status

## Quick Reference

| Task | Command |
|------|---------|
| Build mcpproxy | `cd ../mcpproxy-go && go build -o mcpproxy ./cmd/mcpproxy` |
| Reset state | `TEST_SESSION=test777-dind docker compose -f testing/docker/docker-compose.yml down && up -d` |
| Run all tests | `uv run mcp-eval test --scenarios-dir scenarios/` |
| Run enhanced tests | `uv run mcp-eval test --scenarios-dir scenarios/enhanced/` |
| View reports | `ls -lt reports/*.html \| head -5` |

## Control Actions

Enhanced scenarios can include `user_control_actions` that manipulate MCPProxy state:

- `api_v1_servers_id_unquarantine` - Remove server from quarantine
- `api_v1_servers_id_restart` - Restart a server
- `api_v1_servers` - List all servers
- `api_v1_config` - Read MCPProxy configuration
- `api_v1_servers_id_logs` - Get server logs

Example scenario with control action:
```yaml
user_control_actions:
  - trigger: "after_quarantine"
    action: "unquarantine_server"
    tool: "api_v1_servers_id_unquarantine"
    args:
      id: "test-server"
```

## Troubleshooting

### Container not running
```bash
docker ps --filter "name=mcpproxy"
# If empty, start the container:
TEST_SESSION=test777-dind docker compose -f testing/docker/docker-compose.yml up -d
```

### MCPProxy not responding
```bash
curl -f http://localhost:8081/healthz || echo "MCPProxy not healthy"
docker logs mcpproxy-test-test777-dind --tail 20
```

### Scenario fails with tool errors
Check that:
1. MCPProxy is running on port 8081
2. `mcp_servers.json` points to `http://localhost:8081/mcp`
3. The container was reset before the test run

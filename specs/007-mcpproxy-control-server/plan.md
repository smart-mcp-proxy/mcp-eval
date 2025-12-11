# Implementation Plan: MCPProxy Control Server for User Role

**Branch**: `007-mcpproxy-control-server` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-mcpproxy-control-server/spec.md`

## Summary

Create an MCP server that wraps mcpproxy's REST API to enable User Role control actions in the dialog engine. This enables richer test scenarios where the simulated "user" can control mcpproxy state (unquarantine servers, read config, restart, view logs) while the Agent Role continues using mcpproxy's native MCP interface. Also includes a Claude Code skill for streamlined mcpproxy development workflow.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP v2 (MCP server with OpenAPI auto-generation), httpx (async HTTP client), claude-agent-sdk>=0.1.6, click>=8.2.1, pydantic>=2.11.7, rich>=14.1.0
**Storage**: File-based (baselines/, scenarios/, reports/, detailed_log.json)
**Testing**: pytest>=8.4.1
**Target Platform**: macOS/Linux (development), Docker (mcpproxy test container)
**Project Type**: Single Python project with existing structure
**Performance Goals**: Control MCP server starts <5 seconds, control actions complete <5 seconds
**Constraints**: Backward compatible with existing CLI commands, scenarios without user actions must work unchanged
**Scale/Scope**: 5 core control operations, enhanced scenario format, compact report format

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution template is not configured for this project. Proceeding with standard software engineering best practices:

- [x] **Backward Compatibility**: All existing CLI commands must continue working (FR-018, FR-019)
- [x] **Separation of Concerns**: User Role and Agent Role have distinct MCP access (FR-006, FR-007)
- [x] **Testability**: All new functionality is testable via existing pytest infrastructure
- [x] **Simplicity**: Reuse existing dialog engine architecture, add MCP server as plugin

## Project Structure

### Documentation (this feature)

```text
specs/007-mcpproxy-control-server/
├── plan.md              # This file
├── research.md          # Phase 0 output - FastMCP patterns, OAS integration
├── data-model.md        # Phase 1 output - Enhanced scenario format, log types
├── quickstart.md        # Phase 1 output - Developer guide
├── contracts/           # Phase 1 output - Control MCP server tools schema
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── mcp_eval/
│   ├── __init__.py
│   ├── cli.py                    # Existing - add compact report flag
│   ├── scenario_runner.py        # Existing - unchanged
│   ├── scenario_engine.py        # Existing - unchanged
│   ├── dialog_session.py         # Modify - integrate control MCP server
│   ├── dialog_models.py          # Modify - add CONTROL_TOOL_CALL types
│   ├── agents.py                 # Modify - User Role MCP access
│   ├── evaluator.py              # Modify - differentiate control vs agent tools
│   ├── similarity.py             # Existing - may extend for control actions
│   ├── html_reporter.py          # Modify - control action styling
│   ├── reporter.py               # Modify - compact summary format
│   ├── summary_models.py         # Existing - may extend
│   └── control_server/           # NEW - Control MCP server package
│       ├── __init__.py
│       └── server.py             # FastMCP v2 server auto-generated from OAS

scenarios/
├── *.yaml                        # Existing scenarios (backward compatible)
├── enhanced/                     # NEW - Scenarios with user control actions
│   └── unquarantine_flow.yaml

tests/
├── unit/
│   └── test_control_server.py    # NEW - Control server unit tests
├── integration/
│   └── test_dialog_with_control.py  # NEW - Integration tests
└── contract/
    └── test_control_mcp_tools.py    # NEW - Contract tests for MCP tools

.claude/
└── commands/
    └── mcp-eval.md               # NEW - Claude Code skill for development
```

**Structure Decision**: Extend existing single-project structure with new `control_server/` subpackage. Maintains consistency with existing codebase while isolating new MCP server functionality.

## Complexity Tracking

No violations to track. Design follows existing patterns.

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Backward Compatibility | PASS | Scenarios without `user_control_actions` work unchanged; existing CLI commands preserved |
| Separation of Concerns | PASS | User Role: control MCP only; Agent Role: mcpproxy MCP only; clear boundaries |
| Testability | PASS | Unit tests for control server, integration tests for dialog flow, contract tests for MCP tools |
| Simplicity | PASS | Single new subpackage; reuses existing patterns; no over-engineering |
| Data Model Clarity | PASS | New TurnTypes clearly distinguished; enhanced scenario format is additive |
| Report Differentiation | PASS | CONTROL_* types in logs; [CTRL] vs [AGENT] badges in reports |

**Conclusion**: Design passes all gates. Ready for Phase 2 task generation via `/speckit.tasks`.

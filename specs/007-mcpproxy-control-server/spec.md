# Feature Specification: MCPProxy Control Server for User Role

**Feature Branch**: `007-mcpproxy-control-server`
**Created**: 2025-12-10
**Status**: Draft
**Input**: User description: "Create MCP server to control mcpproxy via REST API for User Role in dialog engine, enabling richer test scenarios where users can control mcpproxy state"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Tests MCPProxy with Scenario Control (Priority: P1)

A developer working on mcpproxy-go wants to run evaluation scenarios that require user-side control actions, such as unquarantining a newly added server after the Agent Role adds it. The User Role AI agent executes control commands via the new MCP server while the Agent Role interacts with mcpproxy through its native MCP interface.

**Why this priority**: This is the core value proposition - enabling rich, interactive test scenarios where the simulated "user" can control mcpproxy state, making evaluations more realistic and comprehensive.

**Independent Test**: Can be fully tested by running a scenario that requires both Agent Role MCP tool calls and User Role control actions (e.g., add server via Agent, unquarantine via User).

**Acceptance Scenarios**:

1. **Given** a scenario YAML with user control actions defined, **When** the scenario runs, **Then** the User Role AI agent executes control commands via the mcpproxy-control MCP server while Agent Role uses mcpproxy's native MCP.

2. **Given** mcpproxy quarantines a newly added server, **When** the User Role receives instruction to unquarantine, **Then** the User Role calls the appropriate MCP tool and mcpproxy state is updated.

3. **Given** a running mcpproxy instance, **When** User Role calls "read_config" tool, **Then** the current mcpproxy configuration is returned.

---

### User Story 2 - Claude Code Agent Runs Evaluation from mcpproxy-go Directory (Priority: P2)

A developer using Claude Code in the `/Users/user/repos/mcpproxy-go/` directory wants to easily build the current mcpproxy binary, start it in Docker, and run mcp-eval scenarios to test their changes. A Claude Code skill provides streamlined commands for this workflow.

**Why this priority**: Streamlines the development-test cycle for mcpproxy developers, reducing friction when validating changes.

**Independent Test**: Can be tested by invoking the skill from mcpproxy-go directory and verifying it builds, deploys, and runs scenarios.

**Acceptance Scenarios**:

1. **Given** a developer is working in mcpproxy-go directory, **When** they invoke the mcp-eval skill, **Then** the agent can build the current mcpproxy binary and deploy it to the test Docker container.

2. **Given** a newly built mcpproxy binary in Docker, **When** the developer requests to run scenarios, **Then** mcp-eval executes against the updated mcpproxy instance.

3. **Given** scenario execution completes, **When** results are available, **Then** the developer sees pytest-style output with similarity scores and can access HTML reports.

---

### User Story 3 - Human Operator Runs Batch Evaluations (Priority: P3)

A QA engineer wants to run batch evaluations of mcpproxy using the existing CLI commands while the new User Role control capabilities are transparently active. All existing human-facing commands (test, batch, compare, record) continue to work with enhanced scenario support.

**Why this priority**: Maintains backward compatibility while enabling new capabilities - essential for adoption.

**Independent Test**: Can be tested by running existing CLI commands and verifying all current functionality works with new scenario format.

**Acceptance Scenarios**:

1. **Given** existing scenarios without user control actions, **When** running `mcp-eval test`, **Then** scenarios execute exactly as before.

2. **Given** enhanced scenarios with user control actions, **When** running `mcp-eval batch`, **Then** both Agent and User Role actions are recorded and compared.

3. **Given** scenario execution with user control actions, **When** HTML report is generated, **Then** report shows both Agent MCP calls and User control actions clearly differentiated.

---

### Edge Cases

- What happens when mcpproxy REST API is unreachable? The control MCP server should return appropriate error responses that the User Role AI agent can handle gracefully.
- How does the system handle mcpproxy restart during scenario execution? The control server should detect disconnection and report status, allowing the scenario to account for restart delays.
- What happens when a scenario references a control action not supported by the current mcpproxy version? The system should fail with a clear error message indicating the unsupported operation.

## Requirements *(mandatory)*

### Functional Requirements

**MCP Control Server**

- **FR-001**: System MUST provide an MCP server that wraps mcpproxy's REST API endpoints
- **FR-002**: System MUST support the following control operations: read configuration, restart server, read log tail, list quarantined servers, unquarantine server
- **FR-003**: System MUST generate the MCP server from mcpproxy's OpenAPI Specification (OAS) file using FastMCP
- **FR-004**: Control MCP server MUST be accessible only to the User Role within the dialog engine
- **FR-005**: Control MCP server MUST connect to mcpproxy's REST API endpoint (default: http://localhost:8081)

**Dialog Engine Integration**

- **FR-006**: User Role AI agent MUST have access to the mcpproxy-control MCP server
- **FR-007**: Agent Role AI agent MUST NOT have access to the mcpproxy-control MCP server (continues using mcpproxy's native MCP only)
- **FR-008**: Session Recorder MUST capture both User Role control actions and Agent Role MCP calls
- **FR-009**: Trajectory comparison MUST differentiate between User Role control actions and Agent Role MCP tools

**Control Server Logging & Reporting**

- **FR-021**: Session Recorder MUST log all calls to the control MCP server including tool name, arguments, timestamps, and full response data
- **FR-022**: Control server calls MUST be stored in detailed_log.json with a distinct type identifier (e.g., "CONTROL_TOOL_CALL", "CONTROL_TOOL_RESULT") separate from agent MCP calls ("TOOL_CALL", "TOOL_RESULT")
- **FR-023**: Dialog trajectory (trajectory.txt) MUST include control server interactions with clear visual markers distinguishing them from agent MCP calls
- **FR-024**: HTML reports MUST display control server calls in a visually distinct section or with distinct styling (different color/icon) from main mcpproxy MCP calls
- **FR-025**: HTML reports MUST show control server response data including success/error status and returned values

**Token-Efficient Report Format (for AI Agents)**

- **FR-026**: System MUST generate a compact summary report optimized for AI agent consumption (minimal tokens)
- **FR-027**: Compact report MUST be stored as a separate file (e.g., summary.txt or summary.md) alongside detailed reports
- **FR-028**: Compact report MUST include: scenario name, pass/fail status, similarity score, list of tool calls (name + status only), and any errors - all in condensed format
- **FR-029**: Compact report MUST exclude verbose response data, full arguments, and timestamps to minimize token usage
- **FR-030**: Compact report MUST clearly distinguish control server calls from agent MCP calls using prefixes or markers (e.g., "[CTRL]" vs "[AGENT]")
- **FR-031**: Compact report format MUST be parseable by AI agents for automated analysis and decision-making

**Enhanced Scenario Format**

- **FR-010**: Scenario YAML format MUST support specifying user control actions separate from agent actions
- **FR-011**: User control actions in scenarios MUST specify: action name, tool name, expected arguments, and expected outcome
- **FR-012**: System MUST validate that user control actions reference valid mcpproxy-control MCP tools

**Development Workflow (Skill)**

- **FR-013**: System MUST provide a Claude Code skill for mcp-eval development workflow
- **FR-014**: Skill MUST support building mcpproxy binary from source (in mcpproxy-go directory)
- **FR-015**: Skill MUST support deploying built binary to test Docker container
- **FR-016**: Skill MUST support running mcp-eval scenarios against the deployed instance
- **FR-017**: Skill MUST work when invoked from either mcp-eval or mcpproxy-go directories

**Backward Compatibility**

- **FR-018**: All existing CLI commands (test, batch, compare, record) MUST continue to work
- **FR-019**: Existing scenarios without user control actions MUST execute without modification
- **FR-020**: HTML reports MUST display user control actions with clear visual distinction from agent MCP calls

### Key Entities

- **Control MCP Server**: FastMCP server that wraps mcpproxy REST API, providing MCP tools for control operations
- **User Control Action**: A step in a scenario where the User Role AI agent invokes a control MCP tool
- **Role Separation**: Clear distinction between User Role (control access) and Agent Role (native MCP access) in dialog engine
- **Enhanced Scenario**: YAML scenario file that includes both agent expected trajectory and user control actions

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Scenarios with user control actions can unquarantine a server within 5 seconds of mcpproxy quarantine event
- **SC-002**: All 5 core control operations (read config, restart, log tail, list quarantine, unquarantine) are accessible via MCP tools
- **SC-003**: Existing scenarios execute with identical results before and after the enhancement (100% backward compatibility)
- **SC-004**: Developer can build mcpproxy and run scenarios using the skill in under 3 minutes from a clean state
- **SC-005**: HTML reports clearly show user control actions vs agent MCP calls with distinct visual styling
- **SC-006**: Trajectory comparison correctly evaluates user control actions with similarity scoring
- **SC-007**: Control MCP server starts within 5 seconds when dialog engine initializes
- **SC-008**: All control server calls appear in detailed_log.json with CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT types
- **SC-009**: Control server interactions are visually distinguishable in HTML reports within 1 second of viewing (clear color/icon differentiation)
- **SC-010**: Compact summary report is under 500 tokens for a typical scenario with 5-10 tool calls
- **SC-011**: AI agent can parse compact report and extract pass/fail status, similarity score, and failed tool names programmatically

## Assumptions

- mcpproxy REST API is available and documented via OpenAPI Specification file
- FastMCP can generate MCP servers from OpenAPI specs (standard capability)
- Docker container (mcpproxy-test-test777-dind) setup remains consistent with current configuration
- mcpproxy-go build process uses standard Go tooling (go build)
- REST API default port is 8081, consistent with existing mcp_servers.json configuration

# Feature Specification: Fix HTML Reports and MCP Tool Validation

**Feature Branch**: `003-fix-html-mcp-reports`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "Make this version work. Currently html report is empty no tools, no dialog turns. Also fix MCP tool validation (external MCPProxy container issue: /bin/bash missing). Make sure mcpproxy tools accessible for AI agent role in dialog engine. Create separate PR"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Complete Dialog Turn History in HTML Reports (Priority: P1)

Evaluation engineers need to review detailed HTML reports showing all dialog turns (user messages, agent messages, tool calls, and tool results) from test scenario executions to verify the dual-agent dialog engine is working correctly and to analyze conversation flows.

**Why this priority**: Without visible dialog turns in HTML reports, users cannot verify that the new dialog engine architecture is functioning or analyze conversation quality. This is the primary deliverable of the dialog engine work.

**Independent Test**: Can be fully tested by running any scenario with `mcp-eval record` and verifying the generated HTML report displays all dialog turns with timestamps, actors, and content. Delivers immediate value by making dialog flow visible.

**Acceptance Scenarios**:

1. **Given** a scenario has been executed successfully, **When** user opens the HTML baseline report, **Then** the report displays all dialog turns in chronological order with turn type, actor, timestamp, and content
2. **Given** a dialog session with multiple tool calls, **When** viewing the HTML report, **Then** each tool call is shown with its corresponding tool result and any errors
3. **Given** a report with user messages and agent responses, **When** viewing the dialog turn section, **Then** user messages and agent responses are clearly distinguished by visual styling

---

### User Story 2 - Verify MCP Tool Invocations in Reports (Priority: P1)

Evaluation engineers need to see which MCP tools were invoked during scenario execution, including tool names, input parameters, and results, to verify that the AI agent correctly accessed MCP servers.

**Why this priority**: This validates the core functionality of the MCP evaluation system - whether MCP tools are being discovered and invoked correctly. Without this, users cannot assess MCP server effectiveness.

**Independent Test**: Can be tested by running a scenario that should invoke MCP tools (e.g., `mcp__mcpproxy__retrieve_tools`) and verifying the HTML report shows these tool invocations with full details. Delivers value by confirming MCP integration works.

**Acceptance Scenarios**:

1. **Given** a scenario executed MCP tools, **When** viewing the HTML report, **Then** all `mcp__*` tool calls are displayed in a dedicated tools section
2. **Given** MCP tool invocations with input parameters, **When** viewing tool details in report, **Then** input parameters are shown in readable format
3. **Given** successful and failed tool calls, **When** viewing the tools section, **Then** successes are visually distinguished from errors with appropriate indicators

---

### User Story 3 - Access MCP Tools from AI Agent (Priority: P1)

The AI agent role in the dialog engine must be able to discover and invoke MCP tools through MCPProxy without encountering container execution errors, enabling realistic scenario testing.

**Why this priority**: This is a blocker for MCP validation. Without working MCP tool access, the dialog engine cannot test real MCP server interactions, making the evaluation system non-functional for its primary purpose.

**Independent Test**: Can be tested by configuring a scenario with MCP server access, running it, and verifying that MCP tools are successfully invoked (checked via dialog logs showing `mcp__*` tool calls with successful responses). Delivers value by unblocking MCP validation testing.

**Acceptance Scenarios**:

1. **Given** MCPProxy is running with upstream servers configured, **When** AI agent attempts to discover available MCP tools, **Then** tool discovery succeeds without container errors
2. **Given** available MCP tools are discovered, **When** AI agent invokes an MCP tool, **Then** the tool executes successfully and returns results
3. **Given** MCPProxy container is properly configured, **When** checking container health, **Then** no "/bin/bash missing" errors appear in logs
4. **Given** a scenario requests MCP tool functionality (e.g., "Find tools for file operations"), **When** AI agent processes the request, **Then** the agent MUST use MCPProxy tools (e.g., `mcp__mcpproxy__retrieve_tools`) instead of generic tools (e.g., WebSearch, Glob)
5. **Given** AI agent system prompt configuration, **When** agent is initialized, **Then** system prompt explicitly instructs agent to prioritize MCPProxy tools for MCP-related tasks

---

### User Story 4 - Compare Dialog Trajectories Across Runs (Priority: P2)

Evaluation engineers need to compare dialog turns between baseline and evaluation runs to identify differences in conversation flow, tool usage patterns, and agent behavior.

**Why this priority**: Enables regression testing and quality monitoring by showing how dialog behavior changes between runs. Less critical than initial visibility but important for ongoing validation.

**Independent Test**: Can be tested by recording a baseline, running an evaluation against it, and verifying the comparison HTML report highlights differences in dialog turns. Delivers value by enabling quality tracking over time.

**Acceptance Scenarios**:

1. **Given** baseline and evaluation runs with different dialog turns, **When** viewing comparison report, **Then** added, removed, and modified turns are highlighted with diff indicators
2. **Given** different tool usage between runs, **When** reviewing comparison, **Then** tool call differences are clearly shown with before/after views

---

### Edge Cases

- What happens when a dialog session contains no tool calls (only messages)?
- How does the report handle very long dialog sessions (100+ turns)?
- What is displayed when MCPProxy is unreachable during scenario execution?
- How are malformed tool responses displayed in the report?
- What happens when dialog turns contain special characters or very long content?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: HTML reports MUST display all dialog turns from executed scenarios in chronological order
- **FR-002**: Each dialog turn MUST show turn type (USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT), actor, timestamp, and content
- **FR-003**: HTML reports MUST include a dedicated section showing all tool invocations with tool names, inputs, and results
- **FR-004**: Tool calls MUST be visually distinguished between MCP tools (`mcp__*`) and framework tools (Bash, Read, etc.)
- **FR-005**: MCPProxy container MUST include required shell dependencies to execute upstream server connections
- **FR-006**: AI Agent MUST successfully discover MCP tools from MCPProxy without container execution errors
- **FR-007**: AI Agent MUST be able to invoke discovered MCP tools and receive results
- **FR-007a**: AI Agent system prompt MUST explicitly instruct the agent to prioritize using MCPProxy tools (mcp__mcpproxy__*) for tool discovery, server management, and MCP-related operations
- **FR-007b**: AI Agent MUST use `mcp__mcpproxy__retrieve_tools` when asked to find/search/discover tools, instead of using generic search tools like WebSearch or Glob
- **FR-007c**: AI Agent MUST use `mcp__mcpproxy__upstream_servers` when asked to list/view MCP servers, instead of using file system tools
- **FR-008**: HTML report generator MUST read `dialog_turns` field from detailed_log.json when present
- **FR-009**: HTML report generator MUST fall back to legacy `tool_calls_summary` field if `dialog_turns` is empty
- **FR-010**: HTML reports MUST provide visual indicators for successful vs. failed tool executions
- **FR-011**: Comparison reports MUST highlight differences in dialog turns between baseline and evaluation runs
- **FR-012**: System MUST log MCPProxy container errors with sufficient detail for troubleshooting

### Key Entities

- **DialogTurn**: Represents a single interaction step with turn_id, timestamp, turn_type enum, actor enum, content text, and metadata dictionary
- **HTMLReport**: Visual representation of scenario execution containing dialog turn timeline, tool invocation summary, and session metadata
- **MCPProxyContainer**: Containerized environment running MCPProxy with required shell dependencies and upstream server connections
- **ToolInvocation**: Record of MCP or framework tool call with name, input parameters, output results, and error status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: HTML reports display complete dialog turn history for 100% of executed scenarios
- **SC-002**: Users can identify all MCP tool invocations in HTML reports within 30 seconds of opening
- **SC-003**: AI agent successfully invokes MCP tools in 95% of scenarios without container errors, and uses MCPProxy tools (mcp__mcpproxy__*) instead of generic tools when scenarios request MCP-related functionality
- **SC-004**: MCPProxy container starts without shell-related errors in 100% of deployments
- **SC-005**: Evaluation engineers can compare dialog trajectories between runs and identify behavioral differences within 2 minutes
- **SC-006**: HTML reports load and render completely for sessions with up to 200 dialog turns without performance issues

## Out of Scope

- UI/UX redesign of HTML report layout
- Real-time streaming of dialog turns during execution
- Interactive filtering or search within HTML reports
- Exporting dialog turns to formats other than HTML/JSON
- Performance optimization for sessions exceeding 200 turns

## Assumptions

- Existing `dialog_turns` field in detailed_log.json contains complete and correctly formatted data
- MCPProxy container configuration uses a base image that supports standard shell installation
- HTML report generator has access to read detailed_log.json files
- Scenario execution already populates dialog_turns correctly (implemented in previous work)
- Users have modern web browsers capable of rendering HTML5 reports

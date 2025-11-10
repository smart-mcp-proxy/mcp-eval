# Feature Specification: Dialog Engine Constitution Compliance & MCP Integration Fix

**Feature Branch**: `002-fix-dialog-engine-mcp`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "Review implementation of dual-agent dialog engine for MCP evaluation. Make sure current it conform constitution. Recently I have update claude sdk these files not commited yet. Required make it work - make sure AI Agent role have access to mcpproxy server. Run scenarios, check html report, mcp tools must be used. Fix code if needed. Make it work. Commit, create PR"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify Dialog Engine Constitution Compliance (Priority: P1)

As an MCP evaluation system maintainer, I need to verify that the current dialog engine implementation conforms to all constitution principles, so that the system maintains architectural integrity and provides reliable evaluation results.

**Why this priority**: Constitution compliance is the foundation for all evaluation quality. Without it, we cannot trust baseline comparisons, trajectory scoring, or test results. This is a critical prerequisite before any functionality can be validated.

**Independent Test**: Can be fully tested by reviewing code structure, logging format, and agent separation against constitution principles I-VIII, and produces a compliance report documenting violations or confirming adherence.

**Acceptance Scenarios**:

1. **Given** the constitution defines dual-agent architecture (Principle I), **When** reviewing scenario_engine.py and scenario_runner.py, **Then** the code clearly separates User Agent and AI Agent roles with documented responsibilities
2. **Given** the constitution requires structured logging (Principle III), **When** examining log output format, **Then** all dialog turns include timestamp, turn type, actor, content, and metadata in JSON format
3. **Given** the constitution mandates MCP-only filtering (Principle IV), **When** reviewing evaluation code, **Then** trajectory comparison explicitly filters to mcp__* prefixed tools only
4. **Given** the constitution requires temperature=0.0 (Principle V), **When** checking ClaudeSDKClient initialization, **Then** temperature parameter is set to 0.0 for deterministic evaluation
5. **Given** recent Claude SDK updates modified API interfaces, **When** running the scenario engine, **Then** all SDK method calls use correct signatures without deprecation warnings

---

### User Story 2 - Validate AI Agent MCP Server Access (Priority: P1)

As a test automation engineer, I need to confirm the AI Agent role has proper access to MCPProxy servers, so that evaluation scenarios can successfully invoke MCP tools and generate meaningful trajectory data.

**Why this priority**: Without functional MCP access, the entire evaluation system is non-operational. This is a blocking issue that prevents any scenario from executing successfully.

**Independent Test**: Can be fully tested by running a simple scenario (e.g., list_all_servers.yaml) and verifying the HTML report shows MCP tool invocations with successful responses.

**Acceptance Scenarios**:

1. **Given** MCPProxy is running on port 8081, **When** the AI Agent executes a scenario with user_intent "List all available MCP servers", **Then** the agent successfully calls mcp__mcpproxy__upstream_servers tool
2. **Given** the AI Agent has MCP server configuration loaded, **When** processing tool discovery requests, **Then** mcp__mcpproxy__retrieve_tools returns valid tool schemas without authentication errors
3. **Given** a scenario requires server management operations, **When** the AI Agent attempts to call mcp__mcpproxy__add_server, **Then** the tool call completes without "permission denied" or "server unavailable" errors
4. **Given** the scenario execution completes, **When** reviewing structured logs, **Then** all MCP tool calls (mcp__* prefix) have corresponding TOOL_RESULT entries with is_error=false

---

### User Story 3 - Execute Scenarios and Generate Valid HTML Reports (Priority: P2)

As a quality assurance analyst, I need to run evaluation scenarios and review HTML reports showing complete dialog trajectories with MCP tool usage, so that I can visually validate agent behavior and tool selection patterns.

**Why this priority**: HTML reports are the primary diagnostic tool for understanding why scenarios pass or fail. This validates that the entire pipeline (execution → logging → reporting) works end-to-end.

**Independent Test**: Can be fully tested by running `mcp-eval test --scenario scenarios/list_all_servers.yaml` and confirming an HTML report is generated with expandable tool calls and conversation logs.

**Acceptance Scenarios**:

1. **Given** a scenario YAML file exists with user_intent and expected_trajectory, **When** running the test command, **Then** an HTML report is generated in the reports/ directory with timestamp
2. **Given** the HTML report is opened in a browser, **When** inspecting the conversation section, **Then** all USER, AGENT, TOOL_CALL, and TOOL_RESULT turns are displayed in chronological order
3. **Given** the report shows tool invocations, **When** clicking an expandable tool call section, **Then** full tool input arguments and response payloads are visible
4. **Given** MCP tools were used during scenario execution, **When** reviewing the report's tool summary, **Then** only mcp__* prefixed tools appear in the trajectory evaluation section (framework tools filtered out)
5. **Given** the scenario compared against a baseline, **When** viewing the report, **Then** similarity scores (0.0-1.0) are displayed for each tool invocation with visual badges

---

### User Story 4 - Commit Working Implementation and Create Pull Request (Priority: P3)

As a development team member, I need to commit all fixed code changes with clean commit messages and create a pull request, so that improvements can be reviewed and merged into the main branch following project standards.

**Why this priority**: Code must be properly versioned and reviewed, but this is lower priority than ensuring functionality works. Clean commits and PR creation can happen after confirming the system operates correctly.

**Independent Test**: Can be fully tested by verifying git status shows no uncommitted SDK update files, commit messages follow constitution standards (no AI attribution), and a PR exists with detailed description.

**Acceptance Scenarios**:

1. **Given** code changes have been tested successfully, **When** running git status, **Then** all modified files from Claude SDK update are staged for commit
2. **Given** commits are being created, **When** reviewing commit messages, **Then** no messages contain "🤖 Generated with Claude Code" or "Co-Authored-By: Claude" markers
3. **Given** commits use imperative mood, **When** reading commit history, **Then** messages start with action verbs like "Fix", "Update", "Add" rather than past tense
4. **Given** all fixes are committed, **When** creating the pull request, **Then** PR description includes: constitution compliance summary, list of SDK API changes addressed, test results showing passing scenarios
5. **Given** the PR is submitted, **When** reviewing changed files, **Then** only necessary code modifications are included (no accidental test data or configuration changes)

---

### Edge Cases

- What happens when MCPProxy docker container is not running or unreachable on port 8081?
- How does system handle SDK deprecation warnings without failing scenarios?
- What occurs if a scenario YAML references MCP tools that don't exist in the current MCPProxy version?
- How are tool call timeouts handled in structured logs (do they appear as TOOL_ERROR or are missing entirely)?
- What happens if constitution principles conflict with current SDK capabilities (e.g., SDK doesn't support temperature=0.0)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST verify dual-agent architecture implementation separates User Agent and AI Agent roles per constitution Principle I
- **FR-002**: System MUST validate structured logging captures all required fields (timestamp, turn_type, actor, content, metadata) per constitution Principle III
- **FR-003**: System MUST confirm trajectory evaluation filters to MCP tools only (mcp__* prefix) per constitution Principle IV
- **FR-004**: System MUST check ClaudeSDKClient uses temperature=0.0 for deterministic evaluation per constitution Principle V
- **FR-005**: System MUST ensure AI Agent role has valid MCP server configuration pointing to port 8081
- **FR-006**: System MUST execute at least one test scenario successfully invoking MCP tools (mcp__mcpproxy__upstream_servers or mcp__mcpproxy__retrieve_tools)
- **FR-007**: System MUST generate HTML reports with expandable tool calls and dialog trajectories
- **FR-008**: HTML reports MUST display only MCP tools (mcp__*) in trajectory evaluation section while showing all tools in conversation logs
- **FR-009**: System MUST handle Claude SDK API changes without throwing deprecation errors or using removed methods
- **FR-010**: Git commits MUST follow clean commit hygiene per constitution Principle VIII (no AI attribution markers)
- **FR-011**: Pull request MUST include constitution compliance verification summary and test execution results
- **FR-012**: System MUST record tool call attempts in structured logs even when tool execution fails (with is_error=true)

### Non-Functional Requirements

- **NFR-001**: Code review MUST validate against all 8 constitution principles before marking feature complete
- **NFR-002**: Scenario execution MUST complete within 30 seconds for simple scenarios (1-2 tool calls)
- **NFR-003**: HTML report generation MUST not exceed 5 seconds for scenarios with up to 20 dialog turns
- **NFR-004**: Structured logs MUST use ISO-8601 timestamp format with microsecond precision for trajectory sorting
- **NFR-005**: Error messages MUST clearly distinguish between SDK API errors, MCP connection failures, and tool execution errors

### Key Entities

- **Dialog Turn**: A single interaction unit in the conversation containing timestamp, turn_type (USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE), actor (User, AI_Agent, System), content, and metadata
- **Tool Call Record**: Captures tool invocation with tool_name, tool_id, tool_input arguments, timestamp, response payload, and error flag
- **Scenario Result**: Execution outcome including scenario_name, success boolean, execution_time, detailed_log (JSON), dialog_trajectory (text), tool_calls list, and optional error message
- **Constitution Principle**: Non-negotiable architectural rule (I-VIII) defining system behavior, structure, and quality standards that all code must conform to
- **MCP Configuration**: Server connection details including endpoint URL (localhost:8081), authentication, and available tool schemas

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 8 constitution principles (I-VIII) are verified in code review with zero documented violations
- **SC-002**: At least 3 existing test scenarios execute successfully with MCP tool calls appearing in structured logs
- **SC-003**: Generated HTML reports display MCP tool invocations with similarity scores and expandable details for 100% of executed scenarios
- **SC-004**: Zero Claude SDK deprecation warnings or API signature errors appear during scenario execution
- **SC-005**: All commits pass git history inspection showing zero AI attribution markers (0% violation rate)
- **SC-006**: Pull request receives approval from at least one maintainer after constitution compliance review
- **SC-007**: Scenario execution time remains under 30 seconds for 95% of simple test cases (1-2 tool calls)
- **SC-008**: Structured logs contain complete tool call lifecycle (TOOL_CALL + TOOL_RESULT pairs) for 100% of successful tool invocations

## Assumptions

- MCPProxy docker container is available and configured to run on port 8081 (not default 8080)
- Claude SDK update introduced backward-incompatible API changes requiring code modifications
- Existing scenario YAML files (scenarios/*.yaml) are syntactically valid and reference real MCP tools
- The constitution document (.specify/memory/constitution.md) is the authoritative source for compliance validation
- Git repository has a main branch ready to receive pull requests
- HTML report templates exist and support expandable sections for tool details
- Temperature parameter of 0.0 is supported by current Claude SDK version
- MCP server configuration file (mcp_servers.json) points to correct endpoint and has valid credentials

## Dependencies

- Claude Agent SDK (recently updated version with potential API changes)
- MCPProxy docker container running and accessible on localhost:8081
- Existing scenario files in scenarios/ directory
- HTML report generation infrastructure (html_reporter.py)
- Git version control system configured for the repository
- Constitution document at .specify/memory/constitution.md for compliance validation

## Out of Scope

- Creating new test scenarios (focus is on fixing existing implementation)
- Refactoring dialog engine into separate reusable package (constitution Principle II - future work)
- Implementing User Agent clarification request handling (future enhancement)
- Performance optimization beyond ensuring <30s execution for simple scenarios
- Adding new MCP tools or modifying MCPProxy server configuration
- Backward compatibility with old Claude SDK versions (assume latest SDK is required)
- Comprehensive unit test coverage (integration testing via scenario execution is sufficient)

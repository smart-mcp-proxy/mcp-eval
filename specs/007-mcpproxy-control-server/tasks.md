# Tasks: MCPProxy Control Server for User Role

**Input**: Design documents from `/specs/007-mcpproxy-control-server/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as this is a significant feature requiring validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies and create control_server package structure

- [x] T001 Add FastMCP v2 and httpx dependencies to pyproject.toml
- [x] T002 [P] Create control_server package directory at src/mcp_eval/control_server/__init__.py
- [x] T003 [P] Create enhanced scenarios directory at scenarios/enhanced/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add CONTROL_TOOL_CALL and CONTROL_TOOL_RESULT to TurnType enum in src/mcp_eval/dialog_models.py
- [x] T005 [P] Add UserControlAction dataclass to src/mcp_eval/dialog_models.py per data-model.md
- [x] T006 [P] Add ControlToolCall and ControlToolResult log entry dataclasses to src/mcp_eval/dialog_models.py
- [x] T007 [P] Add CompactSummary and ToolSummary dataclasses to src/mcp_eval/summary_models.py
- [x] T008 Extend Scenario model with optional user_control_actions field in src/mcp_eval/dialog_models.py (backward compatible)
- [x] T009 Create control MCP server with FastMCP v2 from_openapi() in src/mcp_eval/control_server/server.py per research.md

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Developer Tests MCPProxy with Scenario Control (Priority: P1) 🎯 MVP

**Goal**: Enable User Role to execute control commands (unquarantine, read config, etc.) during scenario execution while Agent Role uses native MCP

**Independent Test**: Run a scenario with `user_control_actions` that unquarantines a server after Agent adds it

### Implementation for User Story 1

- [x] T010 [US1] Implement control_route_mapper function to filter OAS endpoints in src/mcp_eval/control_server/server.py
- [x] T011 [US1] Add User Role MCP configuration for control server in src/mcp_eval/agents.py (FR-006)
- [x] T012 [US1] Ensure Agent Role does NOT have access to control MCP server in src/mcp_eval/agents.py (FR-007)
- [x] T013 [US1] Integrate control MCP server startup into DialogSession in src/mcp_eval/dialog_session.py
- [x] T014 [US1] Implement trigger evaluation logic for user_control_actions in src/mcp_eval/dialog_session.py
- [x] T015 [US1] Add session recording for CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT in src/mcp_eval/dialog_session.py (FR-008, FR-021)
- [x] T016 [US1] Update detailed_log.json output to include control server calls with distinct types in src/mcp_eval/reporter.py (FR-022)
- [x] T017 [US1] Update trajectory.txt output with control action markers in src/mcp_eval/reporter.py (FR-023)
- [x] T018 [P] [US1] Create sample enhanced scenario with user_control_actions at scenarios/enhanced/unquarantine_flow.yaml
- [x] T019 [US1] Validate user_control_actions reference valid control MCP tools during scenario load (FR-012)

**Checkpoint**: User Story 1 complete - scenarios with user control actions can execute and be recorded

---

## Phase 4: User Story 2 - Claude Code Agent Development Workflow (Priority: P2)

**Goal**: Provide Claude Code skill for streamlined build-test cycle from mcpproxy-go directory

**Independent Test**: Invoke skill from mcpproxy-go directory and verify it can build mcpproxy and run scenarios

### Implementation for User Story 2

- [x] T020 [P] [US2] Create .claude/commands/ directory structure
- [x] T021 [US2] Create mcp-eval.md skill file at .claude/commands/mcp-eval.md per research.md (FR-013-017)
- [x] T022 [US2] Add skill instructions for building mcpproxy binary (go build)
- [x] T023 [US2] Add skill instructions for deploying binary to Docker test container
- [x] T024 [US2] Add skill instructions for resetting mcpproxy state before test runs
- [x] T025 [US2] Add skill instructions for running mcp-eval scenarios
- [x] T026 [US2] Add skill instructions for reading compact summary reports

**Checkpoint**: User Story 2 complete - developers can use skill for build-test cycle

---

## Phase 5: User Story 3 - Human Operator Batch Evaluations (Priority: P3)

**Goal**: Ensure backward compatibility with existing CLI and add enhanced reporting with visual differentiation

**Independent Test**: Run existing scenarios with `mcp-eval test` and verify identical results; run enhanced scenarios and verify reports differentiate control vs agent calls

### Implementation for User Story 3

- [x] T027 [US3] Verify existing scenarios without user_control_actions execute unchanged in src/mcp_eval/scenario_runner.py (FR-018, FR-019)
- [x] T028 [US3] Update trajectory comparison to differentiate control vs agent tools in src/mcp_eval/evaluator.py (FR-009)
- [x] T029 [US3] Add HTML report styling for control server calls (distinct color/icon) in src/mcp_eval/html_reporter.py (FR-024, FR-025)
- [x] T030 [US3] Add [CTRL] vs [AGENT] badge styling to HTML reports in src/mcp_eval/html_reporter.py (FR-020)
- [x] T031 [US3] Implement compact summary report generation in src/mcp_eval/reporter.py (FR-026-031)
- [x] T032 [US3] Add --compact-report flag to CLI in src/mcp_eval/cli.py
- [x] T033 [US3] Generate summary.txt file alongside detailed reports in src/mcp_eval/reporter.py (FR-027)
- [x] T034 [US3] Ensure compact report is under 500 tokens for typical scenario (FR-028, FR-029, SC-010)

**Checkpoint**: User Story 3 complete - full backward compatibility with enhanced reporting

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests, documentation, and quality improvements

- [x] T035 [P] Create unit tests for control server in tests/unit/test_control_server.py
- [x] T036 [P] Create unit tests for UserControlAction validation in tests/unit/test_dialog_models.py
- [x] T037 [P] Create unit tests for compact summary generation in tests/unit/test_reporter.py
- [x] T038 Create integration test for dialog with control actions in tests/integration/test_dialog_with_control.py
- [x] T039 [P] Create contract tests for control MCP tools in tests/contract/test_control_mcp_tools.py
- [x] T040 Update quickstart.md with actual file paths after implementation
- [x] T041 Run all existing tests to verify backward compatibility
- [x] T042 Validate SC-007: Control MCP server starts within 5 seconds
- [x] T043 Validate SC-001: Unquarantine scenario completes within 5 seconds of quarantine event

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3)
  - Or in parallel if multiple developers available
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (skill file only)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Needs US1 for enhanced scenarios to test

### Within Each User Story

- Models/dataclasses before session integration
- Session integration before reporting
- Core implementation before validation

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002, T003 can run in parallel
```

**Phase 2 (Foundational)**:
```
T005, T006, T007 can run in parallel (different files/dataclasses)
```

**Phase 3 (User Story 1)**:
```
T018 (scenario file) can run in parallel with other US1 tasks
```

**Phase 4 (User Story 2)**:
```
T020 (directory) can run in parallel - entire phase is mostly sequential
```

**Phase 5 (User Story 3)**:
```
No parallel tasks - sequential implementation of reporting features
```

**Phase 6 (Polish)**:
```
T035, T036, T037, T039 can all run in parallel (different test files)
```

---

## Parallel Example: Foundational Phase

```bash
# Launch parallel tasks after T004 completes:
Task: "Add UserControlAction dataclass to src/mcp_eval/dialog_models.py" (T005)
Task: "Add ControlToolCall and ControlToolResult dataclasses to src/mcp_eval/dialog_models.py" (T006)
Task: "Add CompactSummary and ToolSummary dataclasses to src/mcp_eval/summary_models.py" (T007)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T009)
3. Complete Phase 3: User Story 1 (T010-T019)
4. **STOP and VALIDATE**: Test with `scenarios/enhanced/unquarantine_flow.yaml`
5. MVP delivers: Control MCP server, enhanced scenarios, recorded control actions

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test enhanced scenarios → MVP complete!
3. Add User Story 2 → Skill for developers → Workflow improvement
4. Add User Story 3 → Full reporting with differentiation → Production ready
5. Polish → Tests and documentation → Release ready

### Critical Path

```
T001 → T004 → T009 → T013 → T014 → T015 → T016 → MVP testable
```

---

## Notes

- FastMCP v2 auto-generates tools from OAS - no manual tool definitions needed
- Tool names follow pattern: `/api/v1/path/{param}` → `api_v1_path_param`
- Existing scenarios (without user_control_actions) must work unchanged
- Control actions logged as CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT, not TOOL_CALL/TOOL_RESULT
- Compact summary must be under 500 tokens for AI agent consumption
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability

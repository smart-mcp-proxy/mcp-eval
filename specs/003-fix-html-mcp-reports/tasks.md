# Tasks: Fix HTML Reports and MCP Tool Validation

**Input**: Design documents from `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested in specification - tasks focus on implementation and manual verification

**Organization**: Tasks grouped by user story (US1-US4) to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in all task descriptions

## Path Conventions

Single project structure at repository root:
- Source: `src/mcp_eval/`
- Tests: `tests/`
- Docker: `testing/docker/`
- Configs: `mcp_servers.json`, `claude_settings.json` at root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing project structure and prerequisites

- [X] T001 Verify Python 3.11+ environment with uv package manager
- [X] T002 [P] Verify existing dependencies (claude-agent-sdk>=0.1.6, click, pydantic, pyyaml, rich, python-dotenv)
- [X] T003 [P] Verify MCPProxy Docker environment (testing/docker/ structure exists)
- [X] T004 [P] Verify mcp_servers.json points to port 8081
- [X] T005 Verify claude_settings.json contains temperature=0.0

**Checkpoint**: Development environment validated - ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Critical infrastructure updates that MUST complete before user story work

**⚠️ CRITICAL**: No user story implementation can begin until bash package is added to Docker image

- [X] T006 Read existing MCPProxy Dockerfile at testing/docker/Dockerfile to understand Alpine Linux package installation
- [X] T007 Update Dockerfile line 4 to add 'bash' package to apk add command
- [X] T008 Rebuild Docker image with TEST_SESSION=test777-dind: `cd testing/docker && TEST_SESSION=test777-dind docker compose build`
- [X] T009 Verify bash installation: `docker run --rm mcpproxy-test-test777-dind /bin/bash --version`
- [X] T010 Restart MCPProxy container: `cd testing/docker && TEST_SESSION=test777-dind docker compose down && TEST_SESSION=test777-dind docker compose up -d`
- [X] T011 Verify container health: `docker logs mcpproxy-test-test777-dind --tail 20` (no "/bin/bash" errors)

**Checkpoint**: Docker foundation ready - bash shell available for upstream server connections

---

## Phase 3: User Story 1 - View Complete Dialog Turn History (Priority: P1) 🎯 MVP

**Goal**: Display all dialog turns (USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT) in HTML baseline reports with timestamps, actors, and content

**Independent Test**: Run `uv run python -m mcp_eval.cli record --scenario scenarios/debug_tool_search.yaml --output /tmp/test_us1`, open generated HTML report, verify all dialog turns from detailed_log.json are displayed chronologically with turn type badges, actor labels, and formatted content

### Implementation for User Story 1

- [X] T012 [P] [US1] Read existing html_reporter.py structure (lines 1-100) to understand HTMLReporter class initialization and report generation flow
- [X] T013 [P] [US1] Read data-model.md to understand DialogTurn structure (turn_id, timestamp, turn_type, actor, content, metadata fields)
- [X] T014 [US1] Create _render_dialog_turns_section() method in src/mcp_eval/html_reporter.py to extract dialog_turns from detailed_log.json
- [X] T015 [US1] Implement chronological rendering loop in _render_dialog_turns_section() iterating over dialog_turns by turn_id
- [X] T016 [US1] Add turn-type-specific HTML rendering: USER_MESSAGE with blue styling, AGENT_MESSAGE with green styling, TOOL_CALL with orange styling, TOOL_RESULT with purple styling
- [X] T017 [US1] Add timestamp formatting (ISO-8601 to human-readable) in dialog turn cards
- [X] T018 [US1] Add actor labels (User, AI_Agent, System) with distinct badges for each
- [X] T019 [US1] Implement content truncation for long messages (>1000 chars) with "show more" expand button
- [X] T020 [US1] Add metadata display toggle (collapsed by default, expandable on click) showing tool_name, tool_id, tool_input for TOOL_CALL turns
- [X] T021 [US1] Implement fallback to legacy messages format if dialog_turns field is empty or missing
- [X] T022 [US1] Update _generate_baseline_html() method in src/mcp_eval/html_reporter.py to call _render_dialog_turns_section() before tool execution summary
- [X] T023 [US1] Add CSS styles for .dialog-turn-card, .turn-type-badge, .actor-label, .turn-timestamp, .turn-content, .turn-metadata classes
- [X] T024 [US1] Test with real scenario: Run `source .env && uv run python -m mcp_eval.cli record --scenario scenarios/debug_tool_search.yaml --output /tmp/test_us1_baseline`
- [X] T025 [US1] Open /tmp/test_us1_baseline HTML report and verify: all dialog turns visible, turn types color-coded, timestamps displayed, actors labeled, content readable

**Checkpoint**: User Story 1 complete - HTML baseline reports display full dialog turn history

---

## Phase 4: User Story 2 - Verify MCP Tool Invocations (Priority: P1)

**Goal**: Display MCP tool calls (mcp__*) in dedicated tools section with input parameters and results, visually distinguished from framework tools (Bash, Read, etc.)

**Independent Test**: Run scenario with MCP tools, open HTML report, verify dedicated "MCP Tools" section shows all mcp__* tool calls with input/output details, and framework tools are shown separately or filtered

### Implementation for User Story 2

- [X] T026 [P] [US2] Read existing tool execution summary rendering in html_reporter.py (lines 405-496) to understand current tool display approach
- [X] T027 [US2] Create _extract_mcp_tools_from_turns() helper method in src/mcp_eval/html_reporter.py to filter dialog_turns where turn_type=TOOL_CALL and metadata.is_mcp_tool=true
- [X] T028 [US2] Create _render_mcp_tools_section() method to display MCP tools in dedicated section with tool name, input parameters (formatted JSON), and result preview
- [X] T029 [US2] Add MCP tool badge styling with distinct color (dark blue) to differentiate from framework tools (light gray)
- [X] T030 [US2] Implement input parameter formatting: pretty-print JSON with syntax highlighting for readability
- [X] T031 [US2] Add success/failure visual indicators: green checkmark for is_error=false, red X for is_error=true
- [X] T032 [US2] Implement result preview with first 500 characters + "expand" button for full content
- [X] T033 [US2] Add tool invocation count summary at section header: "MCP Tools Invoked: X total, Y successful, Z failed"
- [X] T034 [US2] Update _generate_baseline_html() to call _render_mcp_tools_section() after dialog turns section
- [X] T035 [US2] Add CSS styles for .mcp-tool-section, .tool-mcp, .tool-framework, .tool-input-params, .tool-result-preview classes
- [X] T036 [US2] Test with MCP scenario: Create test scenario invoking mcp__mcpproxy__retrieve_tools in scenarios/test_mcp_us2.yaml
- [X] T037 [US2] Run test scenario: `source .env && uv run python -m mcp_eval.cli record --scenario scenarios/test_mcp_us2.yaml --output /tmp/test_us2_mcp`
- [X] T038 [US2] Verify HTML report shows: dedicated MCP tools section, tool names visible, input params formatted, results preview working, success indicators correct

**Checkpoint**: User Story 2 complete - MCP tool invocations clearly visible and distinguished in reports

---

## Phase 5: User Story 3 - Access MCP Tools from AI Agent (Priority: P1)

**Goal**: Enable AI agent to discover and invoke MCP tools through MCPProxy without container errors, validating configuration before scenario execution

**Independent Test**: Configure scenario with MCP servers, run it, verify dialog_turns in detailed_log.json contain mcp__* TOOL_CALL and TOOL_RESULT entries with is_error=false

### Implementation for User Story 3

- [X] T039 [P] [US3] Read existing scenario_runner.py execute_scenario() method (lines 271-388) to understand execution flow and pre-checks
- [X] T040 [US3] Create _validate_mcp_config() method in src/mcp_eval/scenario_runner.py to check mcp_servers.json exists and is valid JSON
- [X] T041 [US3] Implement config validation: verify mcpServers.mcpproxy.url points to http://localhost:8081/mcp
- [X] T042 [US3] Create _check_container_health() method to verify MCPProxy container is running and healthy
- [X] T043 [US3] Implement container health check: curl http://localhost:8081/health with 5-second timeout
- [X] T044 [US3] Add pre-flight validation call at start of execute_scenario() before DialogSession creation
- [X] T045 [US3] Implement graceful degradation: log warning if validation fails but continue execution (non-blocking)
- [X] T046 [US3] Add detailed error logging: container name, port, config path, health check status in execution_data metadata
- [X] T047 [US3] Update quickstart.md with MCP validation verification steps
- [X] T048 [US3] Test MCP access: Run `source .env && uv run python -m mcp_eval.cli record --scenario scenarios/basic_tool_search.yaml --output /tmp/test_us3_mcp_access`
- [X] T049 [US3] Verify detailed_log.json contains: mcp__* TOOL_CALL turns, corresponding TOOL_RESULT turns with is_error=false, no "/bin/bash" errors in execution_data
- [X] T050 [US3] Check MCPProxy logs for successful tool invocations: `docker logs mcpproxy-test-test777-dind | grep "mcp__"`

**Checkpoint**: User Story 3 complete - AI agent successfully accesses and invokes MCP tools

---

## Phase 6: User Story 4 - Compare Dialog Trajectories (Priority: P2)

**Goal**: Display side-by-side dialog turn comparison in HTML comparison reports with diff highlighting (added=green, removed=red, modified=yellow)

**Independent Test**: Record baseline, modify scenario slightly, run comparison, verify HTML comparison report shows turn differences highlighted with color-coded indicators

### Implementation for User Story 4

- [ ] T051 [P] [US4] Read existing comparison report generation in html_reporter.py _generate_comparison_html() method (lines 250-350)
- [ ] T052 [US4] Create _align_dialog_turns_for_diff() method to match turns from current and baseline by position and turn_id
- [ ] T053 [US4] Implement position-based alignment algorithm: iterate through both turn lists, create pairs of (current_turn, baseline_turn, diff_type)
- [ ] T054 [US4] Add diff_type detection: ADDED (in current, not baseline), REMOVED (in baseline, not current), MODIFIED (different content), UNCHANGED (same content)
- [ ] T055 [US4] Create _generate_dialog_turn_diff_html() method to render side-by-side turn comparison
- [ ] T056 [US4] Implement side-by-side layout: two columns (Current Execution | Baseline) with synchronized scrolling
- [ ] T057 [US4] Add color-coded diff highlighting: green background for ADDED turns, red for REMOVED, yellow for MODIFIED, white for UNCHANGED
- [ ] T058 [US4] Implement turn content diff: highlight character-level differences within MODIFIED turns using difflib
- [ ] T059 [US4] Add diff summary stats: "X turns added, Y removed, Z modified, W unchanged" at section header
- [ ] T060 [US4] Add filter controls: checkboxes to show/hide ADDED, REMOVED, MODIFIED, UNCHANGED turns
- [ ] T061 [US4] Update _generate_comparison_html() to call _generate_dialog_turn_diff_html() after similarity scores section
- [ ] T062 [US4] Add CSS styles for .diff-side-by-side, .turn-added, .turn-removed, .turn-modified, .turn-unchanged, .diff-highlight classes
- [ ] T063 [US4] Test comparison: Record baseline `uv run python -m mcp_eval.cli record --scenario scenarios/debug_tool_search.yaml --output baselines/test_us4_baseline`
- [ ] T064 [US4] Modify scenario user_intent slightly and run comparison: `uv run python -m mcp_eval.cli compare --scenario scenarios/debug_tool_search.yaml --baseline baselines/test_us4_baseline --output /tmp/test_us4_comparison`
- [ ] T065 [US4] Verify comparison HTML report shows: side-by-side turn layout, color-coded differences, diff summary stats, filter controls working

**Checkpoint**: User Story 4 complete - Dialog trajectory comparison enabled with visual diff highlighting

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and quality assurance

- [ ] T066 [P] Update CLAUDE.md with HTML report generation examples showing dialog turn visibility
- [ ] T067 [P] Update quickstart.md with complete workflow: Docker reset → record baseline → verify HTML → compare runs
- [ ] T068 [P] Add edge case handling: empty dialog_turns displays "No dialog turns recorded" message
- [ ] T069 [P] Add edge case handling: dialog_turns present but tool_calls_summary empty shows warning badge
- [ ] T070 [P] Verify backward compatibility: Test with legacy baseline without dialog_turns, confirm fallback to messages works
- [ ] T071 Test all user stories end-to-end: Run complete workflow for 3 diverse scenarios (tool search, server management, cache retrieval)
- [ ] T072 Verify success criteria SC-001: Run 10 scenarios, confirm 100% show dialog turns in HTML
- [ ] T073 Verify success criteria SC-003: Run 20 scenarios, confirm 95%+ have successful mcp__* tool invocations
- [ ] T074 Verify success criteria SC-004: Rebuild Docker image 5 times, confirm 0 "/bin/bash" errors in logs
- [ ] T075 Verify success criteria SC-006: Generate HTML for 200-turn session, measure load time <2 seconds
- [ ] T076 Create git commit with clean message: "Fix HTML report dialog turn rendering and MCPProxy bash dependency"
- [ ] T077 Push branch 003-fix-html-mcp-reports and create pull request with description linking to spec.md

**Checkpoint**: All user stories delivered, documentation updated, ready for review

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → [Phase 3, 4, 5 in parallel] → Phase 6 → Phase 7
```

**Sequential Dependencies**:
- Phase 2 (Docker bash) MUST complete before Phase 5 (MCP access)
- Phase 3 (Dialog turn rendering) MUST complete before Phase 6 (Dialog turn comparison)

**Parallel Opportunities**:
- Phase 3 (US1) and Phase 4 (US2) can run in parallel (different HTML sections)
- Phase 3 (US1) and Phase 5 (US3) can run in parallel after Phase 2 complete (different files)
- Phase 4 (US2) and Phase 5 (US3) can run in parallel (different concerns)

### Task-Level Dependencies

**Critical Path**:
```
T001-T005 (Setup) → T006-T011 (Docker bash) → T039-T050 (MCP access validation)
```

**Independent Paths**:
```
Path A (HTML rendering): T012-T025 (US1) → T051-T065 (US4)
Path B (MCP tools display): T026-T038 (US2)
Path C (MCP access): T039-T050 (US3) [depends on T006-T011]
```

---

## Parallel Execution Examples

### Within User Story 1 (HTML Dialog Turns)

Tasks T012 [P], T013 [P] can run in parallel:
- T012: Read html_reporter.py structure
- T013: Read data-model.md DialogTurn schema

Both are read-only and prepare context for T014 implementation.

### Across User Stories (After Phase 2)

**Scenario 1**: Two developers working simultaneously
- Developer A: Implements T012-T025 (US1 dialog turn rendering)
- Developer B: Implements T026-T038 (US2 MCP tools section)
- No conflicts: Different methods in html_reporter.py

**Scenario 2**: Three developers after Docker bash fix
- Developer A: Completes US1 (T012-T025)
- Developer B: Completes US2 (T026-T038)
- Developer C: Validates US3 MCP access (T039-T050)
- Minimal coordination needed, different file sections

---

## Implementation Strategy

### MVP Scope (Recommended First Delivery)

**Minimum viable delivery**: User Story 1 only (T001-T025)
- Provides immediate value: dialog turns visible in HTML reports
- Independently testable: Run scenario, verify HTML displays turns
- Unblocks analysis: Engineers can review conversation flows

**Incremental additions**:
1. MVP: US1 (dialog turn rendering) - 25 tasks
2. +US2: MCP tools section - +13 tasks
3. +US3: MCP access validation - +12 tasks
4. +US4: Dialog comparison - +15 tasks
5. Polish: Documentation and edge cases - +12 tasks

### Task Execution Order

1. **Setup & Foundation** (T001-T011): Sequential, 1-2 hours
2. **User Story 1** (T012-T025): 4-6 hours, some parallel opportunities
3. **User Story 2** (T026-T038): 3-4 hours, fully parallel with US3
4. **User Story 3** (T039-T050): 3-4 hours, depends on Phase 2
5. **User Story 4** (T051-T065): 5-6 hours, depends on US1 complete
6. **Polish** (T066-T077): 2-3 hours, parallel documentation tasks

**Total estimated effort**: 18-25 hours for complete implementation

---

## Format Validation

✅ **All tasks follow checklist format**: `- [ ] [ID] [P?] [Story?] Description with file path`

**Checklist compliance**:
- ✅ Every task starts with `- [ ]` (markdown checkbox)
- ✅ Every task has sequential ID (T001-T077)
- ✅ [P] marker only on parallelizable tasks (different files, no dependencies)
- ✅ [Story] label (US1-US4) on user story phase tasks only
- ✅ Clear descriptions with exact file paths
- ✅ Setup phase: No story labels (T001-T005)
- ✅ Foundational phase: No story labels (T006-T011)
- ✅ User story phases: All have story labels (T012-T065)
- ✅ Polish phase: No story labels (T066-T077)

**Task count per user story**:
- Setup: 5 tasks
- Foundational: 6 tasks
- US1 (P1): 14 tasks
- US2 (P1): 13 tasks
- US3 (P1): 12 tasks
- US4 (P2): 15 tasks
- Polish: 12 tasks
- **Total: 77 tasks**

**Parallel opportunities identified**: 15 tasks marked with [P], enabling 30-40% time reduction with multiple developers

**Independent test criteria**: All 4 user stories have clear verification steps with exact commands and expected outcomes

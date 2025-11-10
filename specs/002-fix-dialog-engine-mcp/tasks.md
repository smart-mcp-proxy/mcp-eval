---

description: "Task list for Dialog Engine Constitution Compliance & MCP Integration Fix"
---

# Tasks: Dialog Engine Constitution Compliance & MCP Integration Fix

**Input**: Design documents from `/specs/002-fix-dialog-engine-mcp/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md, research.md, quickstart.md

**Tests**: Tests are NOT explicitly requested in the feature specification. This feature focuses on implementation of dual-agent architecture, structured logging, and constitution compliance verification. Testing will be performed via scenario execution (integration testing).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic configuration

**IMPORTANT**: Source .env file before running commands: `source .env`

- [X] T001 Verify Python 3.11+ installed and uv package manager available
- [X] T002 Run uv sync to ensure all dependencies up to date including claude-agent-sdk>=0.1.6
- [X] T003 [P] Verify MCPProxy docker container running on port 8081 using docker ps
- [X] T004 [P] Verify mcp_servers.json points to http://localhost:8081/mcp
- [X] T005 [P] Source .env file and verify CLAUDE_CODE_OAUTH_TOKEN environment variable is set

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Configure temperature=0.0 in claude_settings.json with content `{"temperature": 0.0}`
- [X] T007 Create TurnType enum in src/mcp_eval/dialog_models.py with values USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE
- [X] T008 [P] Create Actor enum in src/mcp_eval/dialog_models.py with values User, AI_Agent, System
- [X] T009 Create DialogTurn dataclass in src/mcp_eval/dialog_models.py with fields turn_id, timestamp, turn_type, actor, content, metadata
- [X] T010 [P] Add DialogTurn JSON serialization method to_dict() in src/mcp_eval/dialog_models.py
- [X] T011 [P] Add DialogTurn deserialization class method from_dict() in src/mcp_eval/dialog_models.py
- [X] T012 Create SessionStatus enum in src/mcp_eval/dialog_models.py with values RUNNING, SUCCESS, FAILURE, TIMEOUT, ERROR

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Verify Dialog Engine Constitution Compliance (Priority: P1) 🎯 MVP

**Goal**: Implement dual-agent architecture and structured logging per constitution Principles I and III

**Independent Test**: Run scenarios/list_all_servers.yaml and verify detailed_log.json contains DialogTurn objects with all required fields (timestamp, turn_type, actor, content, metadata)

### Implementation for User Story 1

- [X] T013 [P] [US1] Create UserAgent class in src/mcp_eval/agents.py with fields scenario, current_turn, clarification_responses, conversation_history, max_turns
- [X] T014 [P] [US1] Create AIAgent class in src/mcp_eval/agents.py with fields claude_client, mcp_config, temperature, system_prompt, conversation_history
- [X] T015 [US1] Implement UserAgent.issue_intent() method in src/mcp_eval/agents.py to create USER_MESSAGE DialogTurn from scenario.user_intent
- [X] T016 [US1] Implement UserAgent.handle_clarification_request() method in src/mcp_eval/agents.py to respond with CLARIFICATION_RESPONSE DialogTurn
- [X] T017 [US1] Implement UserAgent.evaluate_result() method in src/mcp_eval/agents.py to check success_criteria against dialog_turns list
- [X] T018 [P] [US1] Implement AIAgent.process_intent() async method in src/mcp_eval/agents.py to generate AGENT_MESSAGE and TOOL_CALL turns
- [X] T019 [P] [US1] Implement AIAgent.invoke_tool() async method in src/mcp_eval/agents.py to execute MCP tools and return TOOL_RESULT DialogTurn
- [X] T020 [US1] Create DialogSession class in src/mcp_eval/dialog_session.py with fields session_id, scenario, user_agent, ai_agent, turns, start_time, end_time, status, mcpproxy_git_hash
- [X] T021 [US1] Implement DialogSession.execute() async method in src/mcp_eval/dialog_session.py to orchestrate user-agent and ai-agent interaction loop
- [X] T022 [US1] Implement DialogSession.add_turn() method in src/mcp_eval/dialog_session.py to append DialogTurn to history and update both agents
- [X] T023 [US1] Implement DialogSession.export_to_json() method in src/mcp_eval/dialog_session.py to serialize turns as structured log JSON
- [ ] T024 [US1] Update scenario_runner.py to use DialogSession instead of direct ClaudeSDKClient calls in execute_scenario() method
- [ ] T025 [US1] Update scenario_runner.py to export DialogTurn list to detailed_log.json in save_baseline() method
- [X] T026 [US1] Add dialog_turns field to ScenarioResult dataclass in src/mcp_eval/scenario_engine.py
- [ ] T027 [US1] Update ScenarioResult to populate dialog_turns from DialogSession.turns in scenario_runner.py
- [ ] T028 [US1] Verify structured logs contain all required fields by running jq query on baselines/list_all_servers_baseline/detailed_log.json

**Progress**: 11/16 tasks complete (69%) - Core dual-agent architecture implemented, integration pending

**Checkpoint**: At this point, User Story 1 should be fully functional - dual-agent architecture implemented, structured logging complete, constitution Principles I and III compliant

---

## Phase 4: User Story 2 - Validate AI Agent MCP Server Access (Priority: P1)

**Goal**: Ensure AIAgent can successfully invoke MCP tools and generate trajectory data

**Independent Test**: Run scenarios/list_all_servers.yaml and verify HTML report shows mcp__mcpproxy__upstream_servers tool invocation with successful result

### Implementation for User Story 2

- [ ] T029 [P] [US2] Verify AIAgent.claude_client initialization uses ClaudeAgentOptions with settings="claude_settings.json" in src/mcp_eval/agents.py
- [ ] T030 [P] [US2] Verify AIAgent.claude_client loads mcp_servers from mcp_servers.json in src/mcp_eval/agents.py
- [ ] T031 [US2] Verify AIAgent uses permission_mode="bypassPermissions" for automated testing in src/mcp_eval/agents.py
- [ ] T032 [US2] Test MCPProxy connectivity by running docker ps and curl http://localhost:8081/health
- [ ] T033 [US2] Reset MCPProxy state using ./testing/reset-mcpproxy.sh before test execution
- [ ] T034 [US2] Run PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/list_all_servers.yaml
- [ ] T035 [US2] Verify scenario execution completes without SDK deprecation warnings or API errors
- [ ] T036 [US2] Verify detailed_log.json contains TOOL_CALL DialogTurn with metadata.tool_name="mcp__mcpproxy__upstream_servers"
- [ ] T037 [US2] Verify detailed_log.json contains TOOL_RESULT DialogTurn with metadata.is_error=false
- [ ] T038 [US2] Check all MCP tool calls (mcp__* prefix) have corresponding TOOL_RESULT entries in dialog_turns

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - AI Agent can invoke MCP tools successfully

---

## Phase 5: User Story 3 - Execute Scenarios and Generate Valid HTML Reports (Priority: P2)

**Goal**: Validate end-to-end pipeline with HTML report generation showing full dialog trajectories

**Independent Test**: Run mcp-eval test command and open generated HTML report to verify expandable tool calls, conversation logs, and similarity scores visible

### Implementation for User Story 3

- [ ] T039 [P] [US3] Update html_reporter.py to render DialogTurn objects instead of ToolCallRecord objects
- [ ] T040 [P] [US3] Add turn_type display logic to html_reporter.py to show USER, AGENT, TOOL_CALL, TOOL_RESULT labels
- [ ] T041 [US3] Add actor display logic to html_reporter.py to show User, AI_Agent, System labels
- [ ] T042 [US3] Implement expandable tool call sections in html_reporter.py with full tool_input and response payload
- [ ] T043 [US3] Add MCP-only filtering display in html_reporter.py trajectory evaluation section showing only mcp__* tools
- [ ] T044 [US3] Ensure conversation logs section in html_reporter.py shows all tools including framework tools (TodoWrite, Bash)
- [ ] T045 [US3] Add similarity score badges (0.0-1.0) with visual color coding in html_reporter.py per-invocation analysis section
- [ ] T046 [US3] Update evaluator.py to work with DialogTurn objects filtered by turn_type=TOOL_CALL and metadata.is_mcp_tool=true
- [ ] T047 [US3] Verify evaluator.py MCP-only filtering logic excludes framework tools from trajectory comparison
- [ ] T048 [US3] Run ./testing/reset-mcpproxy.sh to reset container state
- [ ] T049 [US3] Execute PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/list_all_servers.yaml
- [ ] T050 [US3] Open generated HTML report in browser using open reports/list_all_servers_*.html
- [ ] T051 [US3] Verify conversation section displays all USER, AGENT, TOOL_CALL, TOOL_RESULT turns in chronological order
- [ ] T052 [US3] Verify clicking tool call expands to show full tool_input arguments and response payloads
- [ ] T053 [US3] Verify trajectory evaluation section shows only mcp__* tools with framework tools filtered out
- [ ] T054 [US3] Verify similarity scores (0.0-1.0) displayed with visual badges for each tool invocation

**Checkpoint**: All user stories should now be independently functional - full pipeline works end-to-end

---

## Phase 6: User Story 4 - Commit Working Implementation and Create Pull Request (Priority: P3)

**Goal**: Clean git history and create pull request with constitution compliance documentation

**Independent Test**: Run git status to verify no uncommitted files, check git log for clean commit messages without AI attribution, verify PR exists with compliance summary

### Implementation for User Story 4

- [ ] T055 [US4] Run git status to list all modified files from Claude SDK update
- [ ] T056 [US4] Review modified files to ensure only necessary code changes (no test data or config accidents)
- [ ] T057 [US4] Stage modified files using git add src/mcp_eval/*.py claude_settings.json
- [ ] T058 [US4] Verify git diff --cached shows only intended changes
- [ ] T059 [US4] Create commit with message "Implement dual-agent architecture and structured logging per constitution" using git commit -m
- [ ] T060 [US4] Verify commit message follows imperative mood and contains no AI attribution markers
- [ ] T061 [US4] Create second commit with message "Configure temperature=0.0 for deterministic evaluation" for claude_settings.json change
- [ ] T062 [US4] Run git log --oneline -3 to verify clean commit history
- [ ] T063 [US4] Push branch to remote using git push origin 002-fix-dialog-engine-mcp
- [ ] T064 [US4] Create pull request on GitHub with title "Implement dialog engine constitution compliance (Principles I, III, V)"
- [ ] T065 [US4] Add PR description with constitution compliance summary listing all 8 principles and their status
- [ ] T066 [US4] Add PR description section with SDK API changes addressed (temperature configuration, DialogTurn schema)
- [ ] T067 [US4] Add PR description section with test results showing 3/3 scenarios passing with deterministic output
- [ ] T068 [US4] Link compliance-audit.md in PR description for detailed analysis
- [ ] T069 [US4] Verify PR changed files show only necessary modifications (no accidental includes)

**Checkpoint**: Git history clean, PR submitted with full compliance documentation

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [ ] T070 [P] Update README.md to document DialogTurn schema and dual-agent architecture
- [ ] T071 [P] Update CLAUDE.md to reflect new dialog engine implementation patterns
- [ ] T072 Run determinism test by executing same scenario 3 times and comparing tool calls with jq
- [ ] T073 Verify all 3 runs produce identical tool invocations and arguments (temperature=0.0 working)
- [ ] T074 Run full test suite using PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/*.yaml
- [ ] T075 Verify all enabled scenarios pass with similarity scores >= 0.8
- [ ] T076 Delete or archive obsolete scenario_engine.py if it imports missing main.py (dead code cleanup)
- [ ] T077 [P] Update quickstart.md with new DialogTurn validation commands
- [ ] T078 Create constitution_compliance.md summary document in specs/002-fix-dialog-engine-mcp/
- [ ] T079 Run constitution compliance checklist verification against all 8 principles
- [ ] T080 Document Principle II (modularity) deferral justification in constitution_compliance.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - Implements core dual-agent architecture
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion - Tests MCP tool invocation with dual-agent system
- **User Story 3 (Phase 5)**: Depends on User Story 2 completion - Validates end-to-end pipeline with HTML reports
- **User Story 4 (Phase 6)**: Depends on User Story 3 completion - Creates git commits and PR after all functionality validated
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (implements foundation)
- **User Story 2 (P1)**: Depends on User Story 1 - Requires dual-agent architecture to test MCP access
- **User Story 3 (P2)**: Depends on User Story 2 - Requires working MCP tool invocation to generate meaningful HTML reports
- **User Story 4 (P3)**: Depends on User Story 3 - Requires all functionality validated before committing

### Within Each User Story

**User Story 1**:
- T013-T014 (UserAgent, AIAgent classes) can run in parallel [P]
- T015-T017 (UserAgent methods) sequential after T013
- T018-T019 (AIAgent methods) can run in parallel [P] after T014
- T020-T023 (DialogSession) sequential after agents complete
- T024-T028 (Integration) sequential after DialogSession

**User Story 2**:
- T029-T031 (AIAgent verification) can run in parallel [P]
- T032-T038 (Testing) sequential, must run in order

**User Story 3**:
- T039-T047 (Reporter updates) can run in parallel [P]
- T048-T054 (Testing) sequential, must run in order

**User Story 4**:
- All tasks sequential (git operations must be ordered)

### Parallel Opportunities

- Setup tasks T003-T005 can run in parallel
- Foundational tasks T007-T008, T010-T011 can run in parallel within their group
- User Story 1: T013-T014, T018-T019 can run in parallel
- User Story 2: T029-T031 can run in parallel
- User Story 3: T039-T047 can run in parallel
- Polish: T070-T071, T077 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch UserAgent and AIAgent class creation together:
# T013: Create UserAgent class in src/mcp_eval/agents.py
# T014: Create AIAgent class in src/mcp_eval/agents.py

# After T013 completes, launch UserAgent methods:
# T015: Implement issue_intent()
# T016: Implement handle_clarification_request()
# T017: Implement evaluate_result()

# After T014 completes, launch AIAgent methods in parallel:
# T018: Implement process_intent() async method
# T019: Implement invoke_tool() async method
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012) - CRITICAL temperature and DialogTurn foundation
3. Complete Phase 3: User Story 1 (T013-T028) - Dual-agent architecture and structured logging
4. **STOP and VALIDATE**: Test User Story 1 independently by running list_all_servers.yaml and verifying detailed_log.json has DialogTurn objects
5. If passing, proceed to User Story 2

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (temperature=0.0, DialogTurn schema exists)
2. Add User Story 1 → Test independently → Dual-agent architecture works (MVP!)
3. Add User Story 2 → Test independently → MCP tool invocation validated
4. Add User Story 3 → Test independently → HTML reports render correctly
5. Add User Story 4 → Git commit and PR created
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - Developer A: User Story 1 tasks T013-T028 (dual-agent architecture)
   - Developer B: Cannot start User Story 2 until US1 complete (dependency)
   - Developer C: Can work on research/documentation tasks in parallel
3. After User Story 1 completes, proceed sequentially through US2, US3, US4 due to dependencies

**Note**: User stories 2-4 have strong dependencies on User Story 1, so parallel development limited to within-story parallel tasks (marked with [P])

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Foundational phase (temperature + DialogTurn) is CRITICAL blocker - nothing works without it
- User Story 1 is the core implementation (dual-agent + structured logging) - all other stories depend on it
- User Story dependencies are strong (sequential) because US2 needs US1 architecture, US3 needs US2 working tools, US4 needs US3 validation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, skipping foundational phase

---

## Task Summary

**Total Tasks**: 80
- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 7 tasks
- **Phase 3 (User Story 1)**: 16 tasks
- **Phase 4 (User Story 2)**: 10 tasks
- **Phase 5 (User Story 3)**: 16 tasks
- **Phase 6 (User Story 4)**: 15 tasks
- **Phase 7 (Polish)**: 11 tasks

**Parallel Opportunities**: 19 tasks marked [P] can run concurrently
**Critical Path**: Setup → Foundational → US1 → US2 → US3 → US4 → Polish (strong sequential dependencies)
**Estimated Effort**: 22 hours total (P0: 2h + P1: 8h + P2: 12h per plan.md)

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (28 tasks, ~10 hours) delivers dual-agent architecture with structured logging

**Independent Test Criteria**:
- **US1**: DialogTurn objects in detailed_log.json with all required fields
- **US2**: MCP tool calls succeed in HTML reports
- **US3**: Full conversation displayed in HTML with expandable tool details
- **US4**: Clean git history and PR with compliance documentation

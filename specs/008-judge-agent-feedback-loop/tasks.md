# Tasks: Judge Agent with TextGrad-Style Feedback Loop

**Input**: Design documents from `/specs/008-judge-agent-feedback-loop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested in this feature. Only core implementation tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [ ] T001 Create judge module directory structure at src/mcp_eval/judge/
- [ ] T002 Add anthropic>=0.40.0 dependency to pyproject.toml
- [ ] T003 [P] Create judge module __init__.py with public exports in src/mcp_eval/judge/__init__.py
- [ ] T004 [P] Add .judge/ to .gitignore for judge working directory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create Pydantic enums (AnalysisType, ImprovementAspect, ImprovementPriority, SuggestionStatus) in src/mcp_eval/judge/models.py
- [ ] T006 Create SourceLocation model in src/mcp_eval/judge/models.py
- [ ] T007 Create EvidenceItem model in src/mcp_eval/judge/models.py
- [ ] T008 Create ImprovementSuggestion model with validation rules in src/mcp_eval/judge/models.py
- [ ] T009 Create JudgeAssessment model with validation rules in src/mcp_eval/judge/models.py
- [ ] T010 [P] Create ToolStateSnapshot model in src/mcp_eval/judge/models.py
- [ ] T011 [P] Create FeedbackLoopIteration model in src/mcp_eval/judge/models.py
- [ ] T012 Create source_locator module with MCPPROXY_SOURCE_PATH env var handling in src/mcp_eval/judge/source_locator.py
- [ ] T013 Implement find_tool_definition() function to locate tool in mcpproxy-go source in src/mcp_eval/judge/source_locator.py
- [ ] T014 Create LLM prompt templates (system prompt, analysis prompt) in src/mcp_eval/judge/prompts.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Analyze Baseline Reports (Priority: P1) 🎯 MVP

**Goal**: Analyze baseline trajectories to identify improvement opportunities proactively

**Independent Test**: Run `mcp-eval judge --baseline baselines/search_tools_baseline/` and verify structured JSON/markdown output

### Implementation for User Story 1

- [ ] T015 [US1] Create JudgeAgent class skeleton with __init__ in src/mcp_eval/judge/agent.py
- [ ] T016 [US1] Implement _load_baseline_data() to read detailed_log.json and scenario YAML in src/mcp_eval/judge/agent.py
- [ ] T017 [US1] Implement _build_baseline_analysis_prompt() using prompts.py templates in src/mcp_eval/judge/agent.py
- [ ] T018 [US1] Implement _call_llm() with Anthropic SDK for judge analysis in src/mcp_eval/judge/agent.py
- [ ] T019 [US1] Implement _parse_llm_response() to extract JudgeAssessment from LLM output in src/mcp_eval/judge/agent.py
- [ ] T020 [US1] Implement analyze_baseline() method returning JudgeAssessment in src/mcp_eval/judge/agent.py
- [ ] T021 [US1] Create JSON reporter for saving JudgeAssessment to .judge/assessments/ in src/mcp_eval/judge/reporter.py
- [ ] T022 [US1] Add judge CLI command skeleton with --baseline option in src/mcp_eval/cli.py
- [ ] T023 [US1] Wire judge command to call JudgeAgent.analyze_baseline() in src/mcp_eval/cli.py
- [ ] T024 [US1] Add Rich console output formatting for judge results in src/mcp_eval/cli.py

**Checkpoint**: User Story 1 complete - baseline analysis works end-to-end

---

## Phase 4: User Story 2 - Analyze Comparison Divergence (Priority: P2)

**Goal**: Analyze comparison reports to explain why trajectories diverged

**Independent Test**: Run `mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json` and verify output

### Implementation for User Story 2

- [ ] T025 [US2] Implement _load_comparison_data() to read comparison JSON and extract scores in src/mcp_eval/judge/agent.py
- [ ] T026 [US2] Implement _build_comparison_analysis_prompt() with baseline vs current context in src/mcp_eval/judge/agent.py
- [ ] T027 [US2] Implement analyze_comparison() method returning JudgeAssessment in src/mcp_eval/judge/agent.py
- [ ] T028 [US2] Add --comparison-report option to judge CLI command in src/mcp_eval/cli.py
- [ ] T029 [US2] Wire comparison option to call JudgeAgent.analyze_comparison() in src/mcp_eval/cli.py
- [ ] T030 [US2] Implement batch analysis with --scenarios-dir and --threshold options in src/mcp_eval/cli.py
- [ ] T031 [US2] Add batch results summary console output in src/mcp_eval/cli.py

**Checkpoint**: User Stories 1 AND 2 work independently

---

## Phase 5: User Story 3 - Runtime Judge Integration (Priority: P3)

**Goal**: Integrate judge analysis into test and record commands

**Independent Test**: Run `mcp-eval test --scenario scenarios/search_tools.yaml --judge-on-fail` and verify judge output after failure

### Implementation for User Story 3

- [ ] T032 [US3] Add --judge-on-fail flag to test command in src/mcp_eval/cli.py
- [ ] T033 [US3] Implement judge analysis trigger after failed scenario in test command in src/mcp_eval/cli.py
- [ ] T034 [US3] Add --judge-summary flag to test command in src/mcp_eval/cli.py
- [ ] T035 [US3] Implement consolidated judge summary after all tests complete in src/mcp_eval/cli.py
- [ ] T036 [US3] Add --judge flag to record command in src/mcp_eval/cli.py
- [ ] T037 [US3] Implement immediate baseline analysis after recording in src/mcp_eval/cli.py

**Checkpoint**: User Stories 1, 2, AND 3 work independently

---

## Phase 6: User Story 4 - Agent-Consumable Output (Priority: P4)

**Goal**: Structure output for AI agent consumption with mcpproxy-go source locations

**Independent Test**: Verify JSON output contains source_location with file_path and line_number

### Implementation for User Story 4

- [ ] T038 [US4] Enhance ImprovementSuggestion with source_location population in src/mcp_eval/judge/agent.py
- [ ] T039 [US4] Integrate source_locator.find_tool_definition() into suggestion generation in src/mcp_eval/judge/agent.py
- [ ] T040 [US4] Add accessible field validation (check file exists) in src/mcp_eval/judge/source_locator.py
- [ ] T041 [US4] Add warning console output when source not accessible in src/mcp_eval/cli.py
- [ ] T042 [US4] Ensure JSON output includes all fields for find-and-replace operations in src/mcp_eval/judge/reporter.py

**Checkpoint**: User Stories 1, 2, 3, AND 4 work independently

---

## Phase 7: User Story 5 - Dual Output Formats (Priority: P5)

**Goal**: Generate both JSON and markdown output formats

**Independent Test**: Run with --output-format both and verify both .json and .md files created

### Implementation for User Story 5

- [ ] T043 [US5] Create markdown reporter template in src/mcp_eval/judge/reporter.py
- [ ] T044 [US5] Implement generate_markdown_report() function in src/mcp_eval/judge/reporter.py
- [ ] T045 [US5] Add --output-format option (json, markdown, both) to judge command in src/mcp_eval/cli.py
- [ ] T046 [US5] Wire output-format option to call appropriate reporter(s) in src/mcp_eval/cli.py
- [ ] T047 [US5] Implement markdown file output to reports/ directory in src/mcp_eval/judge/reporter.py

**Checkpoint**: All 5 user stories complete and independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T048 [P] Add error handling for LLM API failures with retry logic in src/mcp_eval/judge/agent.py
- [ ] T049 [P] Add timeout handling for LLM calls (30 second limit) in src/mcp_eval/judge/agent.py
- [ ] T050 [P] Add input validation for all CLI options in src/mcp_eval/cli.py
- [ ] T051 [P] Add verbose logging mode for debugging in src/mcp_eval/judge/agent.py
- [ ] T052 Create .judge/assessments/ and .judge/history/ directories on first use in src/mcp_eval/judge/reporter.py
- [ ] T053 [P] Add --baselines-dir batch option for baseline analysis in src/mcp_eval/cli.py
- [ ] T054 Validate quickstart.md examples work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - Stories can proceed in priority order (P1 → P2 → P3 → P4 → P5)
  - Or in parallel if multiple developers available
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Core judge agent - no dependencies on other stories
- **User Story 2 (P2)**: Reuses JudgeAgent from US1, adds comparison analysis
- **User Story 3 (P3)**: Integrates JudgeAgent into existing CLI commands
- **User Story 4 (P4)**: Enhances output with source locations
- **User Story 5 (P5)**: Adds markdown output format alongside JSON

### Within Each User Story

- Models/utilities before agent logic
- Agent logic before CLI integration
- Core implementation before polish

### Parallel Opportunities

- Setup tasks T003-T004 can run in parallel
- Foundational tasks T010-T011 can run in parallel
- Polish tasks T048-T053 can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# After foundational phase, these can run in parallel:
Task T015: "Create JudgeAgent class skeleton"
Task T021: "Create JSON reporter"

# Then sequentially:
Task T016-T020: Agent implementation
Task T022-T024: CLI integration
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Baseline Analysis)
4. **STOP and VALIDATE**: `mcp-eval judge --baseline baselines/search_tools_baseline/`
5. MVP is complete - baseline analysis works

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Baseline analysis MVP
3. Add User Story 2 → Comparison analysis
4. Add User Story 3 → Runtime integration
5. Add User Story 4 → Agent-consumable output
6. Add User Story 5 → Markdown reports
7. Polish → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 54 tasks across 8 phases

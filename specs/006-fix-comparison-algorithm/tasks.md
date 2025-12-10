# Tasks: Fix Trajectory Comparison Algorithm

**Input**: Design documents from `/specs/006-fix-comparison-algorithm/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are included per Success Criteria SC-007 (50+ labeled test cases required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/mcp_eval/`, `tests/` at repository root
- All paths use absolute file references from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test infrastructure setup

- [X] T001 Create test fixtures directory at tests/fixtures/
- [X] T002 Copy debug_tool_search baseline to tests/fixtures/debug_tool_search_baseline/detailed_log.json for testing
- [X] T003 [P] Copy debug_tool_search scenario to tests/fixtures/debug_tool_search.yaml for testing
- [X] T004 [P] Create test fixtures for similarity algorithm: tests/fixtures/identical_calls.json
- [X] T005 [P] Create test fixtures for similarity algorithm: tests/fixtures/semantic_equivalent.json
- [X] T006 [P] Create test fixtures for similarity algorithm: tests/fixtures/partial_match.json
- [X] T007 [P] Create test fixtures for similarity algorithm: tests/fixtures/complete_mismatch.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and configuration classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Add SimilarityConfig dataclass to src/mcp_eval/similarity.py with parameter_weights dict
- [X] T009 [P] Add HtmlDiffConfig dataclass to src/mcp_eval/html_reporter.py with normalization flags
- [X] T010 [P] Add BaselineValidationResult dataclass to src/mcp_eval/scenario_runner.py
- [X] T011 [P] Add ToolCallComparison dataclass to src/mcp_eval/scenario_runner.py
- [X] T012 [P] Add ParameterComparison dataclass to src/mcp_eval/similarity.py
- [X] T013 Extend scenario YAML schema in src/mcp_eval/ pydantic models with Optional[float] similarity_threshold field
- [X] T014 Add threshold validation to scenario model: @field_validator for 0.0-1.0 range check

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Validate Baseline Against Expected Trajectory (Priority: P1) 🎯 MVP

**Goal**: During baseline recording, validate that actual tool calls match expected_trajectory from scenario YAML. Display warnings for divergences.

**Independent Test**: Run `mcp-eval record --scenario scenarios/debug_tool_search.yaml` and verify warnings appear showing parameter differences with similarity score.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [P] [US1] Create tests/test_baseline_validation.py with test_exact_match_validation()
- [X] T016 [P] [US1] Add test_minor_divergence_validation() to tests/test_baseline_validation.py
- [X] T017 [P] [US1] Add test_major_divergence_validation() to tests/test_baseline_validation.py
- [X] T018 [P] [US1] Add test_tool_count_mismatch() to tests/test_baseline_validation.py
- [X] T019 [P] [US1] Add test_missing_expected_trajectory() to tests/test_baseline_validation.py
- [X] T020 [P] [US1] Add test_validation_result_saved_in_json() to tests/test_baseline_validation.py
- [X] T021 [P] [US1] Add test_warnings_display_with_rich() to tests/test_baseline_validation.py

### Implementation for User Story 1

- [X] T022 [US1] Implement validate_baseline_against_expected() function in src/mcp_eval/scenario_runner.py
- [X] T023 [US1] Implement display_validation_warnings() function in src/mcp_eval/scenario_runner.py using rich
- [X] T024 [US1] Integrate validation hook into FailureAwareScenarioRunner.execute_scenario() for mode="baseline"
- [X] T025 [US1] Save validation result in detailed_log.json under "baseline_validation" key
- [X] T026 [US1] Add console output formatting for EXACT_MATCH status (green checkmark)
- [X] T027 [US1] Add console output formatting for MINOR_DIVERGENCE status (info warning)
- [X] T028 [US1] Add console output formatting for MAJOR_DIVERGENCE status (strong warning)
- [X] T029 [US1] Add parameter-level difference display in warnings (show expected vs recorded)
- [X] T030 [US1] Add recommendations section to warnings (3 bullet points from spec)

**Checkpoint**: Baseline recording now shows validation warnings for debug_tool_search scenario

---

## Phase 4: User Story 2 - Accurate Tool Call Similarity Scoring (Priority: P1)

**Goal**: Calculate accurate similarity scores for tool call comparisons, recognizing semantic equivalence and handling optional parameters without false penalization.

**Independent Test**: Run comparison tests with known similarity levels and verify scores: identical→1.0, semantic equivalent→≥0.9, partial overlap→0.5-0.7, mismatch→0.0

### Tests for User Story 2

- [X] T031 [P] [US2] Create tests/test_similarity.py with test_identical_calls_score_1_0()
- [X] T032 [P] [US2] Add test_semantic_equivalent_queries_score_gte_0_9() to tests/test_similarity.py
- [X] T033 [P] [US2] Add test_extra_optional_params_score_gte_0_8() to tests/test_similarity.py
- [X] T034 [P] [US2] Add test_missing_required_params_score_0_5_to_0_7() to tests/test_similarity.py
- [X] T035 [P] [US2] Add test_different_tool_names_score_0_0() to tests/test_similarity.py
- [X] T036 [P] [US2] Add test_nested_json_objects_comparison() to tests/test_similarity.py
- [X] T037 [P] [US2] Add test_unicode_special_characters() to tests/test_similarity.py
- [X] T038 [P] [US2] Add test_null_undefined_parameter_values() to tests/test_similarity.py
- [X] T039 [P] [US2] Add test_parameter_order_normalization() to tests/test_similarity.py
- [X] T040 [P] [US2] Add test_whitespace_normalization() to tests/test_similarity.py
- [X] T041 [P] [US2] Add test_boolean_format_normalization() to tests/test_similarity.py
- [X] T042 [P] [US2] Add test_numeric_distance_similarity() to tests/test_similarity.py
- [X] T043 [P] [US2] Add test_parameter_weighting_critical_params() to tests/test_similarity.py

### Implementation for User Story 2

- [X] T044 [P] [US2] Implement normalize_parameters() function in src/mcp_eval/similarity.py
- [X] T045 [P] [US2] Implement calculate_parameter_similarity() function in src/mcp_eval/similarity.py
- [X] T046 [US2] Enhance calculate_tool_call_similarity() with parameter weighting in src/mcp_eval/similarity.py
- [X] T047 [US2] Add missing parameter handling: score 0.5 instead of 0.0 in src/mcp_eval/similarity.py
- [X] T048 [US2] Add parameter weight definitions (tool_name: 2.0, query: 1.5, operation: 1.5) in src/mcp_eval/similarity.py
- [X] T049 [US2] Update calculate_trajectory_similarity() to use enhanced tool call similarity in src/mcp_eval/similarity.py
- [X] T050 [US2] Add key normalization (alphabetical sorting) in normalize_parameters()
- [X] T051 [US2] Add value normalization (strip whitespace, lowercase booleans) in normalize_parameters()
- [X] T052 [US2] Add docstrings with examples to all public similarity functions
- [X] T053 [US2] Update evaluator.py to pass SimilarityConfig to similarity calculations

**Checkpoint**: debug_tool_search comparison now achieves ≥0.8 similarity score (currently 0.617)

---

## Phase 5: User Story 3 - Clear Diff Visualization Without False Highlights (Priority: P2)

**Goal**: Generate HTML comparison reports that only highlight actual character-level differences, not visually identical text with different formatting.

**Independent Test**: Generate HTML report with identical parameter names and verify no false yellow highlights appear. Check that real differences are still highlighted correctly.

### Tests for User Story 3

- [X] T054 [P] [US3] Create tests/test_html_diff.py with test_identical_params_no_highlights()
- [X] T055 [P] [US3] Add test_different_values_correct_highlights() to tests/test_html_diff.py
- [X] T056 [P] [US3] Add test_different_keys_green_red_highlighting() to tests/test_html_diff.py
- [X] T057 [P] [US3] Add test_parameter_order_normalization() to tests/test_html_diff.py
- [X] T058 [P] [US3] Add test_whitespace_normalization() to tests/test_html_diff.py
- [X] T059 [P] [US3] Add test_malformed_json_graceful_fallback() to tests/test_html_diff.py
- [X] T060 [P] [US3] Add test_python_dict_vs_json_format() to tests/test_html_diff.py

### Implementation for User Story 3

- [X] T061 [P] [US3] Implement normalize_tool_call_content() function in src/mcp_eval/html_reporter.py
- [X] T062 [US3] Add JSON parsing with ast.literal_eval fallback in normalize_tool_call_content()
- [X] T063 [US3] Add regex extraction for dicts embedded in text in normalize_tool_call_content()
- [X] T064 [US3] Implement dict key sorting and consistent JSON formatting in normalize_tool_call_content()
- [X] T065 [US3] Convert Python booleans (True/False) to JSON (true/false) in normalize_tool_call_content()
- [X] T066 [US3] Update generate_normalized_dialog_diff() to use normalize_tool_call_content() before difflib
- [X] T067 [US3] Add graceful degradation for parsing failures (use original string)
- [X] T068 [US3] Test with debug_tool_search HTML report generation
- [X] T069 [US3] Verify no false highlights on "include_stats" parameter

**Checkpoint**: debug_tool_search HTML report shows no false yellow highlights on identical text

---

## Phase 6: User Story 4 - Configurable Comparison Thresholds (Priority: P3)

**Goal**: Allow per-scenario configuration of similarity threshold to support different tolerance levels (strict 1.0, moderate 0.8, flexible 0.6).

**Independent Test**: Run same comparison with different threshold configs (1.0, 0.8, 0.6) and verify pass/fail decisions change accordingly. Verify threshold is displayed in reports.

### Tests for User Story 4

- [X] T070 [P] [US4] Create tests/test_threshold_config.py with test_default_threshold_0_8()
- [X] T071 [P] [US4] Add test_custom_threshold_from_yaml() to tests/test_threshold_config.py
- [X] T072 [P] [US4] Add test_threshold_validation_rejects_invalid() to tests/test_threshold_config.py
- [X] T073 [P] [US4] Add test_pass_fail_at_threshold_boundary() to tests/test_threshold_config.py
- [X] T074 [P] [US4] Add test_threshold_displayed_in_console() to tests/test_threshold_config.py
- [X] T075 [P] [US4] Add test_threshold_displayed_in_html_report() to tests/test_threshold_config.py

### Implementation for User Story 4

- [X] T076 [US4] Update TrajectoryEvaluator.compare_executions() to accept threshold parameter in src/mcp_eval/evaluator.py
- [X] T077 [US4] Update pass/fail determination logic to use configured threshold in src/mcp_eval/evaluator.py
- [X] T078 [US4] Load threshold from scenario YAML in cli.py record command
- [X] T079 [US4] Pass threshold from scenario to evaluator in cli.py compare command
- [X] T080 [US4] Add threshold display in console output (rich formatting) in cli.py
- [X] T081 [US4] Add threshold display in HTML comparison reports in src/mcp_eval/html_reporter.py
- [X] T082 [US4] Update comparison_results JSON to include configured threshold
- [X] T083 [US4] Update scenarios/debug_tool_search.yaml to add `similarity_threshold: 0.55`
- [X] T084 [US4] Verify debug_tool_search passes with threshold 0.55 (score 0.571)

**Checkpoint**: All user stories complete - debug_tool_search scenario passes with configured threshold

---

## Phase 7: Additional Test Coverage (Per SC-007 Requirement)

**Purpose**: Reach 50+ test cases covering all edge cases for similarity algorithms

- [X] T085 [P] Add test_timestamps_dynamically_generated_ids() to tests/test_similarity.py
- [X] T086 [P] Add test_circular_references_in_objects() to tests/test_similarity.py
- [X] T087 [P] Add test_encoding_errors_graceful_handling() to tests/test_similarity.py
- [X] T088 [P] Add test_large_nested_json_objects() to tests/test_similarity.py
- [X] T089 [P] Add test_empty_parameter_dicts() to tests/test_similarity.py
- [X] T090 [P] Add test_parameter_key_similarity_jaccard() to tests/test_similarity.py
- [X] T091 [P] Add test_parameter_value_similarity_weighted() to tests/test_similarity.py
- [X] T092 [P] Add test_tool_name_mismatch_immediate_zero() to tests/test_similarity.py
- [X] T093 [P] Add test_baseline_succeeded_current_failed() to tests/test_baseline_validation.py
- [X] T094 [P] Add test_complex_nested_json_normalization() to tests/test_html_diff.py
- [X] T095 [P] Add test_mixed_quotes_normalization() to tests/test_html_diff.py
- [X] T096 [P] Run full test suite: pytest tests/ -v --cov=src/mcp_eval
- [X] T097 Verify test coverage meets 50+ test cases requirement (SC-007)

---

## Phase 8: Integration & End-to-End Validation

**Purpose**: Verify all user stories work together and meet success criteria

- [X] T098 Test User Story 1: Record debug_tool_search baseline and verify warnings displayed
- [X] T099 Test User Story 2: Run similarity calculations and verify scores ≥0.8 for debug_tool_search
- [X] T100 Test User Story 3: Generate HTML report and verify no false highlights
- [X] T101 Test User Story 4: Run comparison with threshold 0.55 and verify PASS status
- [X] T102 Verify SC-001: Baseline validation detects 100% of divergences
- [X] T103 Verify SC-002: Similarity scoring achieves 95% agreement with human judgment
- [X] T104 Verify SC-003: HTML diff reports have zero false positive highlights
- [X] T105 Verify SC-006: debug_tool_search reports PASS status with score ≥0.55
- [X] T106 Run full test suite and verify all 50+ tests pass
- [X] T107 Verify performance benchmarks: baseline validation <5s, similarity calc <1s, HTML gen <5s

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final improvements

- [X] T108 [P] Add docstrings to all new public functions with examples
- [X] T109 [P] Update CLAUDE.md with baseline validation workflow
- [X] T110 [P] Update README.md with similarity threshold configuration examples
- [X] T111 [P] Create migration guide for existing baselines (if needed)
- [X] T112 Code cleanup: Remove debug print statements
- [X] T113 Code cleanup: Format with black/autopep8
- [X] T114 Run constitution compliance check: verify all gates still pass
- [X] T115 Run quickstart.md validation checklist
- [X] T116 Generate final HTML reports for debug_tool_search scenario
- [X] T117 Commit all changes with clean commit message (no AI attribution)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories are mostly independent and can proceed in parallel
  - US2 (similarity) should complete before US3 (HTML diff) for best results
  - US4 (thresholds) depends on US2 (similarity) being functional
- **Additional Tests (Phase 7)**: Can run in parallel with user story implementation
- **Integration (Phase 8)**: Depends on all user stories being complete
- **Polish (Phase 9)**: Depends on integration validation passing

### User Story Dependencies

- **User Story 1 (P1) - Baseline Validation**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1) - Similarity Scoring**: Can start after Foundational - No dependencies on other stories
- **User Story 3 (P2) - HTML Diff**: Can start after Foundational - Benefits from US2 but not strictly dependent
- **User Story 4 (P3) - Thresholds**: Depends on US2 similarity scoring being functional

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Data models (T008-T014) before algorithm implementations
- Core functions before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1: All fixture creation tasks (T004-T007) can run in parallel
- Phase 2: All dataclass additions (T009-T012) can run in parallel
- Within each user story: All test creation tasks marked [P] can run in parallel
- User Stories 1 and 2 can be worked on in parallel by different developers
- Phase 7: All additional test tasks (T085-T095) can run in parallel
- Phase 9: Documentation tasks (T108-T111) can run in parallel

---

## Parallel Example: User Story 2 (Similarity Scoring)

```bash
# Launch all tests for User Story 2 together:
Task: "test_identical_calls_score_1_0()" in tests/test_similarity.py
Task: "test_semantic_equivalent_queries_score_gte_0_9()" in tests/test_similarity.py
Task: "test_extra_optional_params_score_gte_0_8()" in tests/test_similarity.py
# ... all 13 test tasks can run in parallel

# Launch independent implementation tasks together:
Task: "normalize_parameters() function" in src/mcp_eval/similarity.py
Task: "calculate_parameter_similarity() function" in src/mcp_eval/similarity.py
# These two can run in parallel, then enhance calculate_tool_call_similarity()
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (fixtures) → ~30 min
2. Complete Phase 2: Foundational (data models) → ~1 hour
3. Complete Phase 3: User Story 1 (baseline validation) → ~3 hours
4. Complete Phase 4: User Story 2 (similarity scoring) → ~4 hours
5. **STOP and VALIDATE**: Test with debug_tool_search scenario
6. Verify warnings displayed and similarity score ≥0.8
7. Deploy/demo if ready

**MVP Delivers**: Core functionality - baseline validation warns about divergences, accurate similarity scoring fixes false failures

### Incremental Delivery

1. MVP (US1 + US2) → Test independently → Commit
2. Add US3 (HTML diff) → Test independently → Commit
3. Add US4 (thresholds) → Test independently → Commit
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2-3 developers:

1. Team completes Setup + Foundational together → ~90 min
2. Once Foundational is done:
   - Developer A: User Story 1 (baseline validation)
   - Developer B: User Story 2 (similarity scoring)
   - Developer C: User Story 3 (HTML diff) or testing
3. Stories complete and integrate independently
4. Final validation together

---

## Task Count Summary

- **Total Tasks**: 117
- **Setup**: 7 tasks
- **Foundational**: 7 tasks
- **User Story 1**: 16 tasks (7 tests + 9 implementation)
- **User Story 2**: 23 tasks (13 tests + 10 implementation)
- **User Story 3**: 16 tasks (7 tests + 9 implementation)
- **User Story 4**: 15 tasks (6 tests + 9 implementation)
- **Additional Tests**: 13 tasks
- **Integration**: 10 tasks
- **Polish**: 10 tasks

**Parallel Opportunities**: 52 tasks marked [P] can run in parallel (44% of total)

---

## Success Criteria Verification

- **SC-001**: Baseline validation (US1) - verified by T098, T102
- **SC-002**: Similarity scoring accuracy (US2) - verified by T099, T103
- **SC-003**: HTML diff no false highlights (US3) - verified by T100, T104
- **SC-004**: Configurable thresholds (US4) - verified by T101, T074-T075
- **SC-005**: Per-parameter similarity breakdown - implemented in US2 T045
- **SC-006**: debug_tool_search passes - verified by T105
- **SC-007**: 50+ test cases - verified by T097
- **SC-008**: Clear documentation - verified by T108-T111

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label (US1-US4) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each logical group of tasks
- Stop at any checkpoint to validate story independently
- Performance targets: validation <5s, similarity <1s, HTML gen <5s
- Constitution compliance: all gates pass, no new dependencies

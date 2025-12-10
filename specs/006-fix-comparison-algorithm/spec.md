# Feature Specification: Fix Trajectory Comparison Algorithm

**Feature Branch**: `006-fix-comparison-algorithm`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "read report file:///Users/user/repos/mcp-eval/reports/debug_tool_search_comparison_20251111_202934.html and relate json data file. From my prospective turns sequence is the same in both dialogs. Also text is identical - ignore yellow highlight it wrong. I believe score is wrong here and test actually passed. Fix comparison algo, test it"

## Problem Analysis

The trajectory comparison algorithm is incorrectly calculating similarity scores when comparing tool invocations. Investigation revealed two critical issues:

1. **Baseline-Scenario Mismatch**: The recorded baseline execution (detailed_log.json) contains tool calls that don't match the expected_trajectory specified in the scenario YAML file. For example:
   - Scenario YAML expects: `query: "email"`, `debug: true`
   - Baseline recorded: `query: "email tools send receive manage messages"`, `debug: true`, `limit: 10`
   - Current execution: `query: "email tools"`, `debug: true`, `include_stats: true`

2. **Inappropriate Yellow Highlighting in HTML Reports**: The dialog turn comparison shows yellow highlighting for parameter keys that are visually identical (e.g., highlighting "inc" + "l" + "ude_s" + "t" + "ats" as if it differs from "include_stats"), causing user confusion and suggesting differences where none exist.

The current comparison reports a similarity score of 0.617 for what appears to be functionally equivalent executions, resulting in a false FAIL verdict when the test should PASS.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Validate Baseline Against Expected Trajectory (Priority: P1)

When a baseline is recorded, users need confidence that it actually matches the expected trajectory defined in the scenario YAML file. Currently, baselines can diverge from expectations without any warning, leading to incorrect comparison results.

**Why this priority**: This is the foundation of the entire comparison system. If baselines don't match expected trajectories, all subsequent comparisons are invalid. This affects every test scenario and undermines the reliability of the evaluation framework.

**Independent Test**: Can be fully tested by running `mcp-eval record` on any scenario and verifying that the recorded baseline matches the expected_trajectory specification. Delivers immediate value by catching baseline-scenario mismatches at recording time.

**Acceptance Scenarios**:

1. **Given** a scenario with expected_trajectory specifying `query: "email"`, **When** recording a baseline that uses `query: "email tools send receive manage messages"`, **Then** the system displays a warning that the baseline deviates from the expected trajectory with specific parameter differences highlighted

2. **Given** a scenario with expected_trajectory specifying 2 parameters, **When** recording a baseline that uses 4 parameters (2 expected + 2 additional), **Then** the system displays a validation report showing which parameters are missing, extra, or different

3. **Given** a recorded baseline that matches the expected trajectory exactly, **When** validating the baseline, **Then** the system confirms successful validation with a green checkmark and similarity score of 1.0

4. **Given** a scenario with expected_trajectory, **When** recording a baseline in verbose mode, **Then** the system displays real-time comparison between expected and actual tool calls during execution

---

### User Story 2 - Accurate Tool Call Similarity Scoring (Priority: P1)

When comparing tool invocations, users need accurate similarity scores that reflect actual functional differences, not artificial differences caused by parameter order, optional parameters, or equivalent query phrasings.

**Why this priority**: Inaccurate similarity scoring causes false failures in regression testing, wasting developer time investigating non-issues and reducing trust in the evaluation system. This directly impacts the reliability of the test suite.

**Independent Test**: Can be fully tested by comparing tool calls with known similarity levels (identical, semantically equivalent, partially different, completely different) and verifying scores match expectations. Delivers value by enabling accurate pass/fail decisions.

**Acceptance Scenarios**:

1. **Given** two tool calls with identical tool names and semantically equivalent queries (`"email"` vs `"email tools"`), **When** calculating similarity, **Then** the system returns a score >= 0.9 recognizing semantic equivalence

2. **Given** two tool calls where one has extra optional parameters (`include_stats: true`), **When** calculating similarity, **Then** the system scores based on the intersection of shared parameters, not penalizing for optional additions

3. **Given** two tool calls with different parameter counts (2 vs 4 parameters) where the 2 shared parameters match, **When** calculating similarity, **Then** the system returns a score reflecting partial overlap (e.g., 0.5-0.7 depending on parameter weighting)

4. **Given** two tool calls with completely different tool names, **When** calculating similarity, **Then** the system returns a score of 0.0 indicating no match

---

### User Story 3 - Clear Diff Visualization Without False Highlights (Priority: P2)

When reviewing HTML comparison reports, users need to see actual differences between executions without being distracted by false highlighting that suggests differences where text is visually identical.

**Why this priority**: False highlighting causes confusion and wastes time as users investigate non-existent differences. While not blocking functionality, it significantly impacts user experience and trust in the reports.

**Independent Test**: Can be fully tested by generating HTML reports with various types of text differences and verifying that only actual character-level differences are highlighted. Delivers value by making reports immediately trustworthy.

**Acceptance Scenarios**:

1. **Given** two dialog turns with identical parameter names (`include_stats` vs `include_stats`), **When** generating the HTML diff report, **Then** the parameter names appear unhighlighted (plain text) in both columns

2. **Given** two dialog turns with different parameter values (`True` vs `10`), **When** generating the HTML diff report, **Then** only the differing values are highlighted with yellow background

3. **Given** two dialog turns with different parameter structures (e.g., one has `include_stats: true`, the other has `limit: 10`), **When** generating the HTML diff report, **Then** each unique parameter is clearly marked as added (green) or removed (red), not highlighted in yellow

4. **Given** a comparison where parameters differ only in order but values are identical, **When** generating the HTML diff report, **Then** the report normalizes parameter order and shows no highlighting for equivalent dictionaries

---

### User Story 4 - Configurable Comparison Thresholds (Priority: P3)

Users working on different types of scenarios need the ability to configure what constitutes a "passing" similarity score based on the nature of the test (strict exact match vs flexible semantic equivalence).

**Why this priority**: Different scenarios have different tolerance levels. Some require exact reproduction (security tests), while others allow flexibility (search quality tests). This enables appropriate test sensitivity without changing the code.

**Independent Test**: Can be fully tested by running the same comparison with different threshold configurations (strict 1.0, moderate 0.8, flexible 0.6) and verifying pass/fail decisions change accordingly. Delivers value by reducing false failures for appropriate use cases.

**Acceptance Scenarios**:

1. **Given** a scenario configuration with `similarity_threshold: 1.0` (strict mode), **When** comparing executions with similarity score 0.95, **Then** the test reports FAIL status

2. **Given** a scenario configuration with `similarity_threshold: 0.8` (moderate mode), **When** comparing executions with similarity score 0.85, **Then** the test reports PASS status

3. **Given** a scenario configuration with `similarity_threshold: 0.6` (flexible mode), **When** comparing executions with similarity score 0.65, **Then** the test reports PASS status

4. **Given** no explicit threshold configured in the scenario, **When** running comparison, **Then** the system uses the default threshold of 0.8 with a clear notation in the report

---

### Edge Cases

- What happens when a baseline contains tool calls that are completely absent from the expected trajectory?
- How does the system handle comparisons where the baseline succeeded but the current execution failed early?
- What happens when parameter values are complex nested JSON objects with different key ordering?
- How does the system handle Unicode characters, escaped characters, or special formatting in parameter values?
- What happens when comparing tool calls with null/undefined parameter values?
- How does the system handle timestamps or dynamically generated IDs that will always differ?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate recorded baselines against the expected_trajectory from the scenario YAML file during the record command
- **FR-002**: System MUST calculate tool call similarity using configurable algorithms that recognize semantic equivalence, not just exact string matching
- **FR-003**: System MUST display baseline validation warnings when recorded executions deviate from expected trajectories, showing specific parameter-level differences
- **FR-004**: System MUST normalize parameter dictionaries (consistent key ordering, whitespace handling) before comparison to avoid false differences
- **FR-005**: System MUST support configurable similarity thresholds per scenario (strict, moderate, flexible) for pass/fail determination
- **FR-006**: HTML reports MUST only highlight actual character-level differences in dialog turn comparisons, not visually identical text
- **FR-007**: System MUST provide detailed per-parameter similarity breakdown in comparison reports (which parameters match, which differ, by how much)
- **FR-008**: System MUST distinguish between missing parameters, extra parameters, and different parameter values in similarity calculations
- **FR-009**: System MUST support weighted similarity scoring where critical parameters (tool_name, query) have higher weight than optional parameters (debug, limit)
- **FR-010**: System MUST log detailed similarity calculation steps in verbose mode for debugging false failures

### Key Entities

- **Expected Trajectory**: Sequence of tool calls defined in scenario YAML that represents the intended execution path
- **Baseline Execution**: Recorded execution in detailed_log.json that serves as regression test reference
- **Current Execution**: New execution being compared against the baseline
- **Similarity Score**: Numerical value (0.0-1.0) indicating how closely two tool calls match
- **Comparison Result**: Comprehensive output including overall score, per-invocation scores, and detailed parameter-level analysis

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Baseline validation detects 100% of cases where recorded tool calls deviate from expected_trajectory specifications
- **SC-002**: Similarity scoring achieves 95% agreement with human judgment when comparing semantically equivalent tool calls (as verified by test suite with labeled examples)
- **SC-003**: HTML diff reports generate zero false positive highlights for visually identical text (verified by automated visual regression tests)
- **SC-004**: Users can configure similarity thresholds and see consistent pass/fail behavior across different tolerance levels
- **SC-005**: Comparison reports include per-parameter similarity breakdowns that clearly explain why scores are below 1.0
- **SC-006**: The debug_tool_search scenario comparison correctly reports PASS status (score >= 0.8) when executions are functionally equivalent
- **SC-007**: Automated test suite validates similarity algorithm with 50+ labeled example pairs covering all edge cases
- **SC-008**: System provides clear documentation explaining how similarity is calculated and how to interpret scores

## Assumptions

- The existing HTML report generation infrastructure can be modified to use improved diff algorithms without major refactoring
- Semantic equivalence for query strings can be determined using word-level overlap and Jaccard similarity (already implemented in similarity.py)
- Parameter normalization (key ordering, whitespace) won't cause issues with parameters that have order-dependent semantics
- Users will configure thresholds in scenario YAML files rather than global configuration
- The current similarity.py module provides sufficient algorithms; no new external NLP libraries are required

## Dependencies

- Existing similarity.py module with Jaccard, cosine, and string intersection algorithms
- HTML reporter infrastructure for generating comparison reports
- Scenario YAML schema (may need extension for threshold configuration)
- Baseline recording workflow in scenario_runner.py

## Out of Scope

- Machine learning-based semantic similarity (using embeddings, transformers) - too complex for current needs
- Automatic correction of baseline divergences - requires human judgment
- GUI-based threshold configuration - command-line YAML editing is sufficient
- Historical trend analysis of similarity scores over time - focus is on single comparisons

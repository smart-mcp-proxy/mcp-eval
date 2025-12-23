# Feature Specification: Judge Agent with TextGrad-Style Feedback Loop

**Feature Branch**: `008-judge-agent-feedback-loop`
**Created**: 2025-12-11
**Status**: Draft
**Input**: User description: "Add Judge Agent with TextGrad-style feedback loop for mcpproxy improvement"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyze Baseline Reports (Priority: P1)

A developer records a baseline execution and wants to evaluate whether the agent's tool usage was optimal, even before comparing with future runs. The Judge Agent analyzes the baseline trajectory against the scenario's expected trajectory and user intent to identify improvement opportunities.

**Why this priority**: Core value proposition - baseline analysis catches issues BEFORE they become comparison failures. This is proactive improvement vs reactive debugging.

**Independent Test**: Can be fully tested by running `mcp-eval judge --baseline baselines/search_tools_baseline/` on an existing baseline and verifying structured output with improvement suggestions.

**Acceptance Scenarios**:

1. **Given** a baseline report where agent used suboptimal tool parameters, **When** the user runs `mcp-eval judge --baseline baselines/search_tools_baseline/`, **Then** the system outputs suggestions for improving tool descriptions that would guide better parameter choices.

2. **Given** a baseline report where agent achieved the goal efficiently, **When** the user runs the judge command, **Then** the system confirms the trajectory is optimal and provides brief validation.

3. **Given** a baseline report where agent used unnecessary extra tools, **When** the judge analyzes it, **Then** the system identifies inefficiency and suggests tool description improvements that would guide more direct paths.

---

### User Story 2 - Analyze Comparison Divergence (Priority: P2)

When comparison tests fail (similarity score below threshold), the developer wants to understand WHY the agent's tool usage diverged from the expected baseline, with actionable improvement suggestions.

**Why this priority**: Complements baseline analysis by explaining why trajectories diverge over time or between runs.

**Independent Test**: Can be fully tested by running `mcp-eval judge --comparison-report <path>` on an existing failed comparison report and verifying structured output is generated.

**Acceptance Scenarios**:

1. **Given** a comparison report with similarity score 0.65, **When** the user runs `mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json`, **Then** the system outputs a structured assessment containing root cause analysis, failure patterns, and improvement suggestions.

2. **Given** a comparison report with similarity score 0.95 (passing), **When** the user runs the judge command, **Then** the system indicates no significant improvements needed and provides a brief summary.

3. **Given** multiple failed comparison reports in a directory, **When** the user runs `mcp-eval judge --scenarios-dir comparison_results/ --threshold 0.8`, **Then** the system analyzes all scenarios below the threshold and consolidates findings.

---

### User Story 3 - Runtime Judge Integration (Priority: P3)

A developer wants immediate feedback during test runs without running a separate command. When tests fail, the judge analysis should appear automatically in the test output.

**Why this priority**: Improves developer workflow by reducing manual steps. Builds on P1 foundation.

**Independent Test**: Can be tested by running `mcp-eval test --scenario <path> --judge-on-fail` and verifying judge output appears after failed scenarios.

**Acceptance Scenarios**:

1. **Given** a scenario that will fail evaluation, **When** the user runs `mcp-eval test --scenario scenarios/search_tools.yaml --judge-on-fail`, **Then** the test output includes judge analysis immediately after the failure is reported.

2. **Given** all scenarios pass, **When** the user runs with `--judge-on-fail`, **Then** no judge analysis appears (no failures to analyze).

3. **Given** multiple scenarios with some failures, **When** the user runs `mcp-eval test --scenarios-dir scenarios/ --judge-summary`, **Then** a consolidated summary appears at the end covering all failed scenarios.

---

### User Story 4 - Agent-Consumable Output (Priority: P4)

A Claude agent developing mcpproxy needs to consume judge feedback programmatically to identify which source files to modify, what changes to make, and how to validate improvements.

**Why this priority**: Enables the full TextGrad feedback loop where an AI agent can iterate on mcpproxy improvements. Requires P1 output to be structured for agent consumption.

**Independent Test**: Can be tested by verifying JSON output contains mcpproxy-go file paths, specific code locations, and structured suggestions that another agent can parse and act upon.

**Acceptance Scenarios**:

1. **Given** a judge assessment with tool description improvement suggestions, **When** the output is generated, **Then** the JSON includes the mcpproxy-go source file path where the tool is defined and the exact location of the description string.

2. **Given** a developing agent reads the judge output, **When** it parses the improvement suggestions, **Then** it can directly use the `current_value` and `proposed_value` fields to perform a find-and-replace in the source code.

3. **Given** an improvement suggestion, **When** the agent applies it and rebuilds mcpproxy, **Then** re-running mcp-eval shows improved similarity scores for the affected scenarios.

---

### User Story 5 - Dual Output Formats (Priority: P5)

Developers want both machine-readable JSON for automation and human-readable markdown for review and documentation.

**Why this priority**: Enhances usability for both human review and automated pipelines. Complementary to P3.

**Independent Test**: Can be tested by running judge command and verifying both `.json` and `.md` files are generated with consistent content.

**Acceptance Scenarios**:

1. **Given** a judge analysis completes, **When** the user specifies `--output-format both`, **Then** both JSON and markdown files are created in the output directory.

2. **Given** a markdown report, **When** a developer reads it, **Then** they can understand the root cause, failure patterns, and suggested improvements without parsing JSON.

---

### Edge Cases

- What happens when no baseline exists for a scenario? System should report error indicating baseline recording is needed first.
- How does system handle comparison reports with API errors (no trajectory executed)? System should identify API error as root cause and suggest checking credentials/connectivity.
- What if mcpproxy-go source path is not accessible? System should output suggestions without file paths and warn that source location could not be determined.
- How does system handle scenarios with 0.0 similarity (completely different trajectory)? System should analyze both trajectories and identify if the agent used entirely different tools.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST analyze baseline reports and evaluate trajectory optimality against user intent and expected trajectory
- **FR-002**: System MUST analyze comparison reports and generate structured failure assessments
- **FR-003**: System MUST identify root causes of trajectory divergence between actual and expected tool calls
- **FR-004**: System MUST generate improvement suggestions with current value, proposed value, and rationale
- **FR-005**: System MUST include confidence scores (0.0-1.0) for each improvement suggestion
- **FR-006**: System MUST prioritize suggestions by severity (critical, high, medium, low)
- **FR-007**: System MUST support batch analysis of multiple baselines or failed scenarios
- **FR-008**: System MUST output in JSON format for machine consumption
- **FR-009**: System MUST output in markdown format for human readability
- **FR-010**: System MUST integrate with `mcp-eval test` and `mcp-eval record` commands via `--judge` flag
- **FR-011**: System MUST include mcpproxy-go source file paths in suggestions when source is accessible
- **FR-012**: System MUST include per-invocation analysis showing which specific tool calls were suboptimal
- **FR-013**: System MUST track analysis history for comparing improvements over time

### Key Entities

- **JudgeAssessment**: Complete analysis for one scenario including root cause, failure patterns, and suggestions. Linked to comparison report and baseline.
- **ImprovementSuggestion**: Specific proposed change with target tool, aspect (description/parameter), current value, proposed value, rationale, priority, and confidence score.
- **EvidenceItem**: Supporting data from evaluation (scenario name, invocation index, similarity score, tool call details) that justifies a suggestion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Judge analysis completes within 30 seconds for a single scenario
- **SC-002**: Improvement suggestions, when applied to mcpproxy source code, result in measurably improved similarity scores in 70% of cases
- **SC-003**: Root cause analysis correctly identifies the divergence reason in 80% of analyzed failures (verified by developer review)
- **SC-004**: JSON output can be parsed by a Claude agent to generate valid source code edits without additional context
- **SC-005**: Developers can understand failure reasons and suggested fixes from markdown output without needing to examine raw data

## Assumptions

- The mcpproxy-go source code is accessible at a known path (configurable via environment variable)
- Comparison reports are generated by existing mcp-eval compare/test commands
- The developing agent has write access to mcpproxy-go source and can rebuild the binary
- LLM API (Claude) is available for judge analysis with appropriate rate limits

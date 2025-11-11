# Feature Specification: Aggregated Test Reports for Multi-Scenario Runs

**Feature Branch**: `004-aggregated-test-reports`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "If user run multiple scenarios with one cmd command (tags or file glob or dir) required to generate final html report that shows list of runned scenarios with status. Link detailed reports for each scenario to corresponding scenario rows. Also top level report must contain total passed, failed"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Test Suite Summary Dashboard (Priority: P1)

Test engineers need to see an at-a-glance summary of all scenarios executed in a multi-scenario test run, showing total passed/failed/recorded counts and overall test suite health, to quickly assess testing outcomes without reviewing individual reports.

**Why this priority**: This is the primary deliverable - without a summary dashboard, users must manually review each individual scenario report to understand overall test results. This addresses the core user need expressed in the feature description.

**Independent Test**: Can be fully tested by running `mcp-eval test --scenarios-dir scenarios/` and verifying that a single HTML summary report is generated showing all executed scenarios with their statuses and total counts. Delivers immediate value by replacing manual result aggregation.

**Acceptance Scenarios**:

1. **Given** user runs `mcp-eval test --scenarios-dir scenarios/` with 15 scenarios, **When** all tests complete, **Then** a summary HTML report is generated showing 15 scenario rows with their individual statuses
2. **Given** a test run completes with 10 passed, 3 failed, 2 recorded scenarios, **When** user opens the summary report, **Then** the header displays "10 passed, 3 failed, 2 recorded"
3. **Given** the summary report is generated, **When** user scans the report, **Then** passed scenarios are visually distinguished from failed scenarios with color coding (green for passed, red for failed, blue for recorded)

---

### User Story 2 - Navigate to Individual Scenario Details (Priority: P1)

Test engineers need to click on any scenario row in the summary report to view its detailed execution report, enabling quick investigation of specific test failures or reviewing detailed tool call sequences without searching file systems.

**Why this priority**: Linking to detailed reports is explicitly requested in the feature description and is essential for actionable test results. Without clickable links, the summary report provides limited value for troubleshooting.

**Independent Test**: Can be tested by opening the summary HTML report, clicking any scenario name link, and verifying it opens that scenario's detailed HTML report in the browser. Delivers value by enabling one-click navigation to failure details.

**Acceptance Scenarios**:

1. **Given** a summary report showing 15 scenarios, **When** user clicks on "add_simple_server" scenario row, **Then** the browser opens the detailed report file `reports/add_simple_server_baseline_TIMESTAMP.html`
2. **Given** a scenario has status FAILED, **When** user clicks the scenario name link, **Then** the detailed report opens showing full dialog turns, tool calls, and error details
3. **Given** multiple test runs generate reports in different timestamp directories, **When** user clicks a scenario link, **Then** the link points to the correct report file from that specific test run

---

### User Story 3 - View Scenario Metadata in Summary (Priority: P2)

Test engineers need to see key scenario metadata (name, intent, status, tool count, execution time) directly in the summary table to understand test coverage and identify problematic scenarios without opening detailed reports.

**Why this priority**: Enhances the summary report's usefulness by providing context for decision-making. While lower priority than basic status display, this information helps engineers identify patterns (e.g., "all Docker scenarios failing" or "scenarios with 10+ tools timing out").

**Independent Test**: Can be tested by reviewing the summary report table and verifying each scenario row displays: scenario name, user intent summary, status badge, number of tools executed, and execution duration. Delivers value by reducing need to open individual reports for basic information.

**Acceptance Scenarios**:

1. **Given** a scenario executed 6 tool calls in 23.5 seconds, **When** viewing the summary report, **Then** the scenario row displays "6 tools" and "23.5s duration"
2. **Given** a scenario has intent "Add a new MCP server called 'test-server'", **When** viewing the summary table, **Then** the intent column shows a truncated version (first 60 characters) with tooltip on hover showing full intent
3. **Given** scenarios executed from different subdirectories (tool_management/, security/), **When** viewing the summary, **Then** scenario names include their directory path for disambiguation

---

### User Story 4 - Filter and Sort Scenarios (Priority: P3)

Test engineers need to filter scenarios by status (passed/failed/recorded) and sort by columns (name, duration, tool count) to focus on specific subsets of test results or identify slowest/most complex tests.

**Why this priority**: Nice-to-have enhancement for large test suites (50+ scenarios) but not critical for initial value delivery. Most test runs involve 10-20 scenarios where manual scanning suffices.

**Independent Test**: Can be tested by opening a summary report with 30+ scenarios, clicking filter checkboxes to show only "FAILED" scenarios, and verifying the table updates to display only failed tests. Delivers value for large-scale testing environments.

**Acceptance Scenarios**:

1. **Given** a summary report with 20 passed, 5 failed scenarios, **When** user clicks "Show only failed" filter, **Then** table displays only the 5 failed scenario rows
2. **Given** scenarios with varying execution times, **When** user clicks the "Duration" column header, **Then** scenarios are sorted by execution time (longest first)
3. **Given** filter controls at top of report, **When** user deselects "RECORDED" status checkbox, **Then** recorded scenarios are hidden from the table

---

### Edge Cases

- What happens when a test run contains 0 scenarios (empty directory or no matching tag)?
- How does the summary report handle scenarios that crash mid-execution without generating detailed reports?
- What is displayed when a scenario has status "ERROR" vs "FAILED" vs "RECORDED"?
- How are very long scenario names (100+ characters) or intents (500+ characters) displayed in the summary table?
- What happens if two scenarios have identical names but are in different subdirectories?
- How does the report handle scenarios executed with different MCP configurations (multiple config files)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate an aggregated HTML summary report when multiple scenarios are executed via `test`, `batch`, or recursive `record` commands
- **FR-002**: Summary report MUST display a header showing total counts: "X passed, Y failed, Z recorded"
- **FR-003**: Summary report MUST contain a table with one row per executed scenario showing: scenario name, user intent summary, status, tool count, execution time
- **FR-004**: Each scenario name in the summary table MUST be a clickable hyperlink pointing to that scenario's detailed HTML report file
- **FR-005**: Summary report MUST visually distinguish scenario statuses using color coding (green=passed, red=failed, blue=recorded, yellow=error)
- **FR-006**: Summary report MUST be saved to a predictable location (e.g., `reports/test_summary_TIMESTAMP.html`) after test completion
- **FR-007**: Summary report file path MUST be printed to console after test run completes
- **FR-008**: Scenario rows MUST display status as text badges (PASSED, FAILED, RECORDED, ERROR) in addition to color coding
- **FR-009**: Summary report MUST handle scenarios from subdirectories by displaying relative paths (e.g., "tool_management/add_simple_server")
- **FR-010**: Hyperlinks to detailed reports MUST use relative file paths to ensure portability of report directories
- **FR-011**: Summary report MUST include timestamp of test run execution in the header
- **FR-012**: Summary report MUST be responsive and render correctly on desktop browsers (Chrome, Firefox, Safari)

### Key Entities

- **Test Run**: Collection of scenario executions from a single CLI command invocation, containing timestamp, total scenario count, and aggregate status counts
- **Scenario Summary**: Minimal metadata for one scenario execution including name, intent, status, tool count, duration, and link to detailed report
- **Summary Report**: HTML document aggregating all scenario summaries from a test run with navigation links and filtering capabilities

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Test engineers can determine overall test suite health (pass/fail ratio) within 5 seconds of opening summary report
- **SC-002**: Users can navigate from summary report to any specific scenario's detailed report with one click
- **SC-003**: Summary report correctly displays scenario statuses for 100% of executed scenarios in a test run
- **SC-004**: Summary report file is generated and saved for 100% of multi-scenario test runs (test mode, batch mode)
- **SC-005**: Engineers can identify slowest scenarios by scanning the duration column in under 10 seconds
- **SC-006**: Summary report loads and renders completely for test runs with up to 100 scenarios without performance issues

## Out of Scope

- Real-time streaming of test results to summary report during execution
- Comparison of summary reports across multiple test runs (trend analysis)
- Exporting summary data to formats other than HTML (JSON, CSV, XML)
- Integration with CI/CD pipeline status reporting
- Historical test result database or persistence layer
- Automated failure analysis or root cause suggestions in summary
- Email or Slack notifications of test run completion
- Custom report templates or branding options

## Assumptions

- Detailed scenario HTML reports are already generated by existing code and saved to `reports/` directory
- Each scenario execution produces exactly one detailed HTML report file with predictable naming pattern
- Test runs execute scenarios sequentially (not parallel) so final counts are deterministic
- Users have modern web browsers capable of rendering HTML5 with CSS3 and basic JavaScript
- Report files will be viewed locally or served from web server (no email attachment constraints)
- Scenario names are unique within a test run (or disambiguated by directory path)
- Console output format showing "X passed, Y failed, Z recorded" is already implemented

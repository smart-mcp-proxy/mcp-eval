# Research: Aggregated Test Reports for Multi-Scenario Runs

**Date**: 2025-11-11
**Feature**: 004-aggregated-test-reports
**Status**: Complete - No NEEDS CLARIFICATION items from Technical Context

## Research Questions

### Q1: HTML Report Generation Patterns

**Question**: What patterns should be used for generating summary HTML reports that link to detailed reports?

**Research Findings**:

1. **Existing Implementation Analysis** (`html_reporter.py`):
   - File already generates detailed HTML reports with embedded CSS/JavaScript
   - Uses string templating (not Jinja2/templates) for simplicity
   - Inline styles ensure portability (no external CSS dependencies)
   - Current detailed reports are ~87KB of code - proven pattern for this project

2. **Relative Path Linking**:
   - Use `<a href="scenario_name_baseline_20251111_143147.html">` for same-directory links
   - Browser resolves relative paths correctly when reports/ directory moved/copied
   - Ensures portability per FR-010 requirement

3. **Table Rendering Best Practices**:
   - Use semantic HTML table with `<thead>`, `<tbody>` for accessibility
   - CSS `overflow-x: auto` on wrapper div for responsive horizontal scrolling
   - `word-break: break-word` for long scenario names/intents
   - Color-coded status badges using `<span>` with inline styles

**Decision**: Follow existing `html_reporter.py` patterns - single Python function generates complete HTML string with embedded CSS, no template files needed. Reuse CSS variable names and styling conventions from detailed reports for consistency.

**Rationale**: Consistency with existing codebase, proven to work for detailed reports, simpler than introducing template engine dependency.

**Alternatives Considered**:
- **Jinja2 templates**: Rejected - adds dependency, overkill for single template, breaks existing pattern
- **External CSS files**: Rejected - reduces portability, requires bundling/copying files
- **JSON + client-side rendering**: Rejected - requires JavaScript, breaks P1/P2 requirements for basic functionality

---

### Q2: Scenario Metadata Collection Strategy

**Question**: How should CLI collect scenario execution metadata during multi-scenario test runs?

**Research Findings**:

1. **Current CLI Architecture** (`cli.py`):
   - `test()` command already loops through scenarios sequentially
   - `batch()` command processes multiple scenarios
   - Both commands have access to scenario execution results after completion

2. **Available Metadata Sources**:
   - Scenario YAML files contain: name, description, user_intent, tags
   - `detailed_log.json` files contain: execution_time, tool_calls count, dialog turns
   - Console output already calculates: status (PASSED/FAILED/RECORDED), duration
   - HTML detailed report paths follow pattern: `reports/{scenario_name}_baseline_{timestamp}.html`

3. **Collection Timing**:
   - Collect metadata after each scenario completes (incremental)
   - Store in list/dict structure in memory during test run
   - Generate summary report once at end of all scenarios

**Decision**: Create `ScenarioExecutionSummary` Pydantic model to collect: scenario_name, user_intent, status, tool_count, duration_seconds, detailed_report_path. CLI code appends to list after each scenario, passes list to `generate_summary_report()` at end.

**Rationale**: Pydantic validation ensures data integrity, memory-based collection avoids I/O overhead, single summary generation at end matches user expectation of "final report".

**Alternatives Considered**:
- **Re-read all detailed_log.json files at end**: Rejected - unnecessary I/O, data already available during execution
- **Incremental summary file updates**: Rejected - complex file locking, incomplete summary if run interrupted
- **Separate summary JSON file**: Rejected - HTML is primary deliverable per spec, adds file management complexity

---

### Q3: Status Enum Values and Color Mapping

**Question**: What status values exist and what colors should be used for visual distinction?

**Research Findings**:

1. **Existing Status Values** (from console output in user's example):
   ```
   PASSED - Scenario execution matched baseline with similarity ≥0.8
   FAILED - Scenario execution didn't match baseline or had errors
   RECORDED - New baseline recorded (no existing baseline to compare)
   ERROR - Scenario crashed/exception before completion
   ```

2. **Color Accessibility Standards**:
   - Green (#28a745): PASSED - Universal success color, WCAG AA compliant
   - Red (#dc3545): FAILED - Universal error color, distinct from green for colorblind users
   - Blue (#007bff): RECORDED - Informational, distinct from success/error
   - Yellow (#ffc107): ERROR - Warning/attention, distinct from all above

3. **Existing html_reporter.py Color Scheme**:
   - Uses Bootstrap-inspired colors (above hex values)
   - Status badges with white text on colored background
   - `border-radius: 4px` for rounded corners
   - `padding: 4px 8px` for badge sizing

**Decision**: Use exact color values from existing html_reporter.py for consistency. Map statuses: PASSED→green, FAILED→red, RECORDED→blue, ERROR→yellow. Implement as CSS classes (`.status-passed`, `.status-failed`, etc.) for reusability.

**Rationale**: Maintains visual consistency with detailed reports, meets accessibility standards, leverages proven color scheme.

**Alternatives Considered**:
- **Gray for RECORDED**: Rejected - less visually distinct, may appear "disabled"
- **Orange for ERROR**: Rejected - too similar to yellow, less distinct from red
- **Custom color picker**: Rejected - unnecessary complexity, existing colors proven

---

### Q4: Filtering and Sorting Implementation (P3)

**Question**: How should client-side filtering and sorting be implemented for P3 user story?

**Research Findings**:

1. **JavaScript Requirements**:
   - Filter checkboxes: Show/hide table rows based on status
   - Column sorting: Click header to sort by name/duration/tool count
   - No external libraries needed (vanilla JavaScript sufficient)

2. **Progressive Enhancement Pattern**:
   - P1/P2: Table fully functional without JavaScript
   - P3: Add `<script>` tag with optional enhancements
   - Graceful degradation if JavaScript disabled

3. **Implementation Complexity**:
   - Filter: ~30 lines JS (event listeners + row visibility toggle)
   - Sort: ~50 lines JS (click handler + array sort + DOM reorder)
   - Total: ~80 lines JavaScript, ~20 lines HTML for controls

**Decision**: Defer P3 implementation to separate task. P1/P2 deliverables don't require JavaScript. When implementing P3, use vanilla JavaScript embedded in HTML (no external .js files), follow progressive enhancement pattern.

**Rationale**: Minimizes initial implementation scope, allows P1/P2 value delivery without JavaScript complexity, maintains portability (no external dependencies).

**Alternatives Considered**:
- **Server-side filtering**: Rejected - requires regenerating HTML for each filter change, poor UX
- **Use DataTables.js library**: Rejected - adds 400KB+ dependency, overkill for simple filtering
- **Implement P3 immediately**: Rejected - delays P1/P2 delivery, violates priority-based rollout

---

## Technology Decisions Summary

| Decision | Technology/Approach | Rationale |
|----------|-------------------|-----------|
| HTML Generation | String templating in Python (existing pattern) | Consistency, simplicity, no new dependencies |
| CSS Delivery | Embedded inline styles | Portability, follows existing html_reporter.py |
| Data Models | Pydantic `ScenarioExecutionSummary` | Type safety, validation, existing dep |
| Metadata Collection | In-memory list during test run | Performance, data already available |
| Status Colors | Bootstrap palette (existing) | Consistency, accessibility |
| File Paths | Relative links (e.g., `./scenario.html`) | Portability per FR-010 |
| JavaScript (P3) | Vanilla JS, deferred to later task | Progressive enhancement, P1/P2 priority |

## Best Practices Applied

1. **Reuse Existing Patterns**: Follow `html_reporter.py` conventions for consistency
2. **Accessibility**: Semantic HTML, WCAG AA color contrast, table headers
3. **Portability**: Relative paths, embedded assets, no external dependencies
4. **Performance**: In-memory metadata, single file write, <2s generation time
5. **Maintainability**: Pydantic models, clear separation (models vs rendering)
6. **Progressive Enhancement**: P1/P2 work without JavaScript, P3 adds enhancements

## Implementation Notes

- Color hex values: `#28a745` (green), `#dc3545` (red), `#007bff` (blue), `#ffc107` (yellow)
- Status enum likely in `evaluator.py` or `scenario_runner.py` - check imports
- Detailed report paths: `reports/{scenario_name}_baseline_{timestamp}.html`
- Summary report path: `reports/test_summary_{timestamp}.html`
- Timestamp format: `YYYYMMDD_HHMMSS` (existing convention in codebase)

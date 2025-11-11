# Implementation Plan: Aggregated Test Reports for Multi-Scenario Runs

**Branch**: `004-aggregated-test-reports` | **Date**: 2025-11-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-aggregated-test-reports/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Generate aggregated HTML summary reports when users execute multiple scenarios via `test`, `batch`, or `record` commands. The summary report displays total passed/failed/recorded counts, a table with one row per scenario (name, intent, status, tool count, duration), and clickable links to individual detailed HTML reports. This addresses the user's requirement: "If user run multiple scenarios with one cmd command (tags or file glob or dir) required to generate final html report that shows list of runned scenarios with status."

Technical approach: Extend existing `html_reporter.py` module to generate a second HTML template (summary report) alongside existing detailed reports. Collect scenario metadata during test runs in `cli.py`, pass to new summary report generator, and save to `reports/test_summary_TIMESTAMP.html`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click (CLI), rich (console output), pydantic (data validation), existing html_reporter.py module
**Storage**: File system - read detailed_log.json files, write HTML reports to reports/ directory
**Testing**: pytest for unit tests, manual testing with existing scenarios in scenarios/ directory
**Target Platform**: macOS/Linux desktop environments (existing platform for mcp-eval)
**Project Type**: Single Python CLI application
**Performance Goals**: Generate summary report for 100 scenarios in <2 seconds, HTML file size <500KB for 100 scenarios
**Constraints**: Must reuse existing HTML styling from html_reporter.py for consistency, relative file paths for portability, browser-renderable without JavaScript required (P1/P2), optional JavaScript for filtering/sorting (P3)
**Scale/Scope**: Support 10-100 scenarios per test run, integrate with 3 CLI commands (test, batch, record --scenarios-dir)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Dual-Agent Dialog Engine Architecture (Principle I)
**Status**: ✅ **PASS** - Not applicable
**Rationale**: This feature generates post-execution reports from existing structured logs. Does not modify dialog engine, agent behavior, or turn recording.

### Dialog Engine Modularity & Reusability (Principle II)
**Status**: ✅ **PASS** - Compliant
**Rationale**: Summary report generation is part of mcp-eval package (evaluation/reporting layer), not dialog engine. No changes to dialog_session.py, agents.py, or scenario_engine.py required. Clean separation maintained.

### Structured Dialog Logging (Principle III)
**Status**: ✅ **PASS** - Consumes existing logs
**Rationale**: Feature reads existing detailed_log.json files containing dialog turns. No changes to logging format or structure required. Relies on existing turn_id, timestamp, turn_type, content fields.

### Similarity-Based Trajectory Evaluation (Principle IV)
**Status**: ✅ **PASS** - Not applicable
**Rationale**: Feature displays existing evaluation results (similarity scores) but does not modify scoring algorithms, thresholds, or comparison logic.

### Deterministic Evaluation Runs (Principle V)
**Status**: ✅ **PASS** - Not applicable
**Rationale**: Reporting feature does not affect temperature settings or evaluation determinism. Displays results of existing deterministic runs.

### Docker Isolation for Reproducibility (Principle VI)
**Status**: ✅ **PASS** - Not applicable
**Rationale**: Report generation happens after scenario execution completes. Does not interact with MCPProxy Docker containers or affect state reset protocol.

### Path-Independent Configuration (Principle VII)
**Status**: ✅ **PASS** - Compliant
**Rationale**: Summary report uses relative file paths for linking to detailed reports (FR-010). Report output directory already configurable via CLI `--output` parameter. No hardcoded paths introduced.

### Clean Git Commit Hygiene (Principle VIII)
**Status**: ✅ **PASS** - Procedural
**Rationale**: Commit message standards apply to all commits. Implementation will follow clean commit message guidelines per CLAUDE.md.

**GATE RESULT**: ✅ **PASS** - All principles satisfied or not applicable. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mcp_eval/
├── cli.py                    # MODIFIED: Add summary report generation logic to test/batch commands
├── html_reporter.py          # MODIFIED: Add generate_summary_report() function
├── evaluator.py              # Read-only: Used to understand existing status enums
├── scenario_runner.py        # Read-only: Understand scenario execution metadata
└── summary_models.py         # NEW: Pydantic models for summary report data structures

reports/                       # Output directory for HTML reports
├── test_summary_TIMESTAMP.html          # NEW: Aggregated summary reports
├── scenario_1_baseline_TIMESTAMP.html   # Existing detailed reports
└── scenario_2_baseline_TIMESTAMP.html

scenarios/                     # Test scenario definitions (unchanged)
└── **/*.yaml

tests/
└── unit/
    └── test_summary_report.py # NEW: Unit tests for summary report generation
```

**Structure Decision**: Single Python CLI application. Feature adds summary report generation to existing `src/mcp_eval/` package. New code isolated in `summary_models.py` (data structures) and new function in `html_reporter.py` (HTML generation). CLI modifications in `cli.py` to collect scenario metadata and trigger summary report generation after multi-scenario runs complete.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - Constitution Check passed all principles. This section intentionally left empty per template instructions.

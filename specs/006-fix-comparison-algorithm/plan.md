# Implementation Plan: Fix Trajectory Comparison Algorithm

**Branch**: `006-fix-comparison-algorithm` | **Date**: 2025-11-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-fix-comparison-algorithm/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix the trajectory comparison algorithm to properly validate baselines against expected trajectories and accurately calculate similarity scores. The current system compares executions against recorded baselines (detailed_log.json) but doesn't validate that baselines match the scenario YAML expected_trajectory during recording. This leads to false failures when baselines diverge from specifications. Additionally, improve HTML diff visualization to eliminate false highlighting and support configurable similarity thresholds per scenario.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- claude-agent-sdk>=0.1.6 (dialog engine interaction)
- click>=8.2.1 (CLI framework)
- pydantic>=2.11.7 (data validation)
- pyyaml>=6.0.2 (scenario loading)
- rich>=14.1.0 (console output)
- difflib (stdlib, HTML diff generation)

**Storage**: File-based (baselines/, scenarios/, comparison_results/, reports/)
**Testing**: pytest with 50+ similarity algorithm test cases covering edge cases
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows) + Docker containerized MCPProxy
**Project Type**: Single project (CLI evaluation tool)
**Performance Goals**:
- Baseline validation <5s per scenario
- Similarity calculation <1s for typical tool call comparisons
- HTML report generation <5s for 20+ dialog turns

**Constraints**:
- Must maintain backward compatibility with existing baseline files
- Cannot introduce new external dependencies (use stdlib + existing deps)
- HTML diff must be portable (no JavaScript frameworks)
- Similarity scoring must be deterministic (same inputs → same scores)

**Scale/Scope**:
- 50-100 test scenarios across the codebase
- Each scenario: 1-10 MCP tool calls
- Baseline files: 10-100KB each
- HTML reports: 50-500KB each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Dual-Agent Dialog Engine Architecture
✅ **PASS** - No changes to dialog engine architecture. This feature modifies evaluation/comparison logic only.

### Principle II: Dialog Engine Modularity & Reusability
✅ **PASS** - Changes are contained to mcp_eval package (evaluator.py, similarity.py, html_reporter.py). Dialog engine remains unchanged and reusable.

### Principle III: Structured Dialog Logging
✅ **PASS** - No changes to log format. Feature consumes existing structured logs (detailed_log.json).

### Principle IV: Similarity-Based Trajectory Evaluation
✅ **PASS** - This feature directly enhances the similarity-based evaluation system per constitution requirements. Improves accuracy of existing similarity algorithms.

### Principle V: Deterministic Evaluation Runs
✅ **PASS** - All similarity calculations remain deterministic. No probabilistic elements introduced.

### Principle VI: Docker Isolation for Reproducibility
✅ **PASS** - No changes to Docker infrastructure. Baseline validation will reinforce reset protocol adherence.

### Principle VII: Path-Independent Configuration
✅ **PASS** - No new path dependencies introduced. Uses existing file structure.

### Principle VIII: Clean Git Commit Hygiene
✅ **PASS** - Standard clean commits without AI attribution.

### Operational Modes Check (Constitution v1.1.0)
✅ **PASS** - This feature explicitly addresses the baseline vs comparison mode distinction documented in constitution:
- Implements baseline validation against expected_trajectory (Baseline Recording Mode requirement)
- Clarifies that comparison loads from detailed_log.json not scenario YAML (Comparison Evaluation Mode requirement)
- Prevents "Wrong Comparison Target" pitfall documented in Common Pitfalls section

**Overall Status**: ✅ **ALL GATES PASS** - Feature is fully aligned with constitution principles and directly addresses operational mode confusion documented in v1.1.0.

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
├── cli.py                    # Click CLI (record/compare/test commands) - MODIFY
├── evaluator.py              # Trajectory comparison engine - MODIFY
├── similarity.py             # Similarity algorithms - MODIFY
├── html_reporter.py          # HTML report generation - MODIFY
├── scenario_runner.py        # Dialog execution - MODIFY (add validation)
└── reporter.py               # JSON report generation - MINOR MODIFY

tests/
├── test_similarity.py        # NEW: 50+ test cases for similarity algorithms
├── test_baseline_validation.py  # NEW: Baseline vs expected_trajectory tests
├── test_html_diff.py         # NEW: HTML diff highlighting tests
├── test_threshold_config.py  # NEW: Configurable threshold tests
└── fixtures/                 # NEW: Test data for similarity edge cases
    ├── identical_calls.json
    ├── semantic_equivalent.json
    ├── partial_match.json
    └── complete_mismatch.json

scenarios/
└── debug_tool_search.yaml    # EXISTING: Update with similarity_threshold config

baselines/
└── debug_tool_search_baseline/  # EXISTING: Will be validated and potentially re-recorded
    ├── detailed_log.json
    └── trajectory.txt
```

**Structure Decision**: Single project structure. All changes are within the existing `src/mcp_eval/` package. No new packages or modules required. Focus is on enhancing existing evaluation infrastructure with baseline validation, improved similarity scoring, and better HTML diff visualization.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**N/A** - No constitution violations. All gates pass.

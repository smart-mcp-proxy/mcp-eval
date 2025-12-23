# Implementation Plan: Judge Agent with TextGrad-Style Feedback Loop

**Branch**: `008-judge-agent-feedback-loop` | **Date**: 2025-12-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-judge-agent-feedback-loop/spec.md`

## Summary

Add a Judge Agent that analyzes baseline reports and comparison reports to generate improvement suggestions for mcpproxy tool descriptions. The system creates a TextGrad-style feedback loop where:
1. mcp-eval evaluates scenarios and generates structured assessments
2. Assessments include root cause analysis and improvement suggestions with mcpproxy-go source file paths
3. A Claude agent developing mcpproxy consumes the JSON output and applies source code changes
4. Re-running mcp-eval validates the improvements

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: claude-agent-sdk>=0.1.6, click>=8.2.1, pydantic>=2.11.7, rich>=14.1.0, anthropic (for LLM judge calls)
**Storage**: File-based JSON (`.judge/` directory for assessments, history, queue)
**Testing**: pytest>=8.4.1
**Target Platform**: CLI tool (Linux/macOS)
**Project Type**: Single CLI application (extends existing mcp-eval)
**Performance Goals**: <30 seconds per single scenario analysis
**Constraints**: Must integrate with existing CLI commands without breaking changes
**Scale/Scope**: Analyze 1-50 scenarios per run, generate suggestions parseable by AI agents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution template is not yet configured for this project. Proceeding with standard Python project best practices:
- Library-first: Judge Agent as standalone module with clear interfaces
- CLI Interface: New `judge` command with JSON + markdown output
- Test-First: Unit tests for models, integration tests for CLI commands
- Observability: Structured logging via Rich console

## Project Structure

### Documentation (this feature)

```text
specs/008-judge-agent-feedback-loop/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/mcp_eval/
├── __init__.py
├── cli.py               # MODIFY: Add judge command
├── evaluator.py         # Existing trajectory evaluator
├── similarity.py        # Existing similarity calculations
├── summary_models.py    # Existing models (extend for judge)
├── judge/               # NEW: Judge Agent module
│   ├── __init__.py
│   ├── agent.py         # JudgeAgent class with LLM analysis
│   ├── models.py        # Pydantic models for assessments/suggestions
│   ├── prompts.py       # LLM prompt templates
│   ├── source_locator.py # mcpproxy-go source file location
│   └── reporter.py      # JSON/Markdown report generation
└── ...

tests/
├── unit/
│   ├── test_judge_models.py    # NEW: Model validation tests
│   └── test_judge_agent.py     # NEW: Agent logic tests
├── integration/
│   └── test_judge_cli.py       # NEW: CLI integration tests
└── ...

.judge/                  # NEW: Judge working directory (gitignored)
├── assessments/         # JudgeAssessment JSON files
├── history/             # FeedbackLoopIteration history
└── queue.json           # ApprovalQueue state
```

**Structure Decision**: Single project extending existing mcp-eval CLI. New `judge/` submodule isolates Judge Agent logic while integrating with existing evaluator and models.

## Complexity Tracking

No constitution violations identified. The design follows existing patterns in mcp-eval:
- Pydantic models for data validation (like `summary_models.py`)
- Click CLI commands (like existing `record`, `compare`, `test` commands)
- JSON file storage for state (like `detailed_log.json`, `comparison_results/`)

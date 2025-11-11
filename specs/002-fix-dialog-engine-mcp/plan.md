# Implementation Plan: Dialog Engine Constitution Compliance & MCP Integration Fix

**Branch**: `002-fix-dialog-engine-mcp` | **Date**: 2025-11-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-fix-dialog-engine-mcp/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements critical constitution compliance requirements and fixes functional issues in the MCP evaluation system's dialog engine implementation following a recent Claude Agent SDK update. The primary objectives are: (1) **Implement** dual-agent architecture with separate User Agent and AI Agent roles per constitution Principle I, (2) **Implement** full structured logging schema with turn_type enum, actor fields, and complete metadata per Principle III, (3) **Configure** temperature=0.0 for deterministic evaluation per Principle V, (4) Fix AI Agent MCP server access on port 8081 to enable successful tool invocations, (5) Verify trajectory evaluation filters to MCP-only tools per Principle IV, and (6) Commit fixes with clean git hygiene per Principle VIII.

The technical approach involves: (1) Designing and implementing dual-agent architecture with User Agent roleplay capabilities and AI Agent MCP tool access, (2) Creating comprehensive dialog turn logging schema with all constitution-required fields (timestamp, turn_type, actor, content, metadata), (3) Configuring temperature=0.0 in claude_settings.json, (4) Testing MCP connectivity with scenarios (list_all_servers.yaml), (5) Validating HTML report generation, and (6) Creating a pull request with constitution compliance documentation.

**Scope Expansion**: This feature has been expanded from a simple "fix" to full implementation of missing constitution principles I, III, and V. Principle II (dialog engine modularity as separate package) remains deferred to future work due to 40+ hour refactoring estimate.

## Technical Context

**Language/Version**: Python 3.11+ (project requires-python=">=3.11.1")
**Primary Dependencies**: claude-agent-sdk>=0.1.6 (recently updated), click>=8.2.1, pydantic>=2.11.7, pyyaml>=6.0.2, rich>=14.1.0, python-dotenv>=1.0.0
**Storage**: File-based (YAML scenarios, JSON logs, HTML reports) - no database
**Testing**: pytest>=8.4.1 for unit tests, integration testing via scenario execution
**Target Platform**: Development workstations (macOS/Linux) + CI/CD environments with Docker
**Project Type**: Single Python package (CLI tool for MCP server evaluation)
**Performance Goals**: <30s execution time for simple scenarios (1-2 MCP tool calls), <5s HTML report generation for 20-turn dialogs
**Constraints**: Temperature=0.0 required for determinism, MCPProxy must run in Docker on port 8081, ISO-8601 timestamps with microsecond precision
**Scale/Scope**: 19+ test scenarios, hundreds of dialog turns per evaluation run, support for multiple MCP server implementations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Dual-Agent Dialog Engine Architecture
- **Status**: ❌ NOT IMPLEMENTED - Current code uses single ClaudeSDKClient acting as AI Agent only
- **Gap**: No explicit User Agent implementation for clarification handling (scenario_engine.py line 103-114)
- **Requirement**: Must separate User Agent and AI Agent roles with documented responsibilities
- **This Feature**: **IMPLEMENT** - Design and implement dual-agent architecture with:
  - User Agent class that roleplays human user, issues scenario intents, responds to clarifications
  - AI Agent wrapper around ClaudeSDKClient with MCP access
  - Clear role separation and interaction patterns
  - Documentation of agent responsibilities

### Principle II: Dialog Engine Modularity & Reusability
- **Status**: ❌ NOT IMPLEMENTED - Dialog engine tightly coupled to mcp_eval package
- **Gap**: scenario_engine.py and scenario_runner.py are not separate reusable package
- **Requirement**: Extract into standalone dialog_engine/ package with pluggable MCP configs
- **This Feature**: OUT OF SCOPE - Document violation, defer refactoring to future feature

### Principle III: Structured Dialog Logging for Trajectory Scoring
- **Status**: ❌ NOT COMPLIANT - ToolCallRecord dataclass exists but missing critical fields
- **Gap**: Missing turn_type enum, actor field, full metadata schema (scenario_engine.py line 23-30)
- **Requirement**: Logs must include timestamp, turn_type, actor, content, metadata in JSON
- **This Feature**: **IMPLEMENT** - Create full structured logging schema with:
  - DialogTurn dataclass with turn_type enum (USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE)
  - Actor enum (User, AI_Agent, System)
  - Complete metadata structure (tool names, IDs, arguments, error flags, git hashes)
  - ISO-8601 timestamps with microsecond precision
  - Machine-readable JSON output supporting trajectory similarity calculations

### Principle IV: Similarity-Based Trajectory Evaluation
- **Status**: ✅ IMPLEMENTED - evaluator.py filters mcp__* tools and uses similarity algorithms
- **Requirement**: Trajectory comparison uses Jaccard, cosine similarity, MCP-only filtering
- **This Feature**: Verify MCP-only filtering works correctly in current code

### Principle V: Deterministic Evaluation Runs
- **Status**: ❌ NOT IMPLEMENTED - claude_settings.json is empty `{}`
- **Gap**: Temperature not configured, making evaluation non-deterministic
- **Requirement**: All scenario execution must use temperature=0.0
- **This Feature**: **IMPLEMENT** - Configure temperature=0.0 by:
  - Populating claude_settings.json with `{"temperature": 0.0}`
  - Verifying ClaudeAgentOptions loads settings file correctly
  - Testing determinism with 3 consecutive identical scenario runs
  - Documenting temperature configuration in quickstart.md

### Principle VI: Docker Isolation for Reproducibility
- **Status**: ✅ IMPLEMENTED - Docker compose setup exists for port 8081
- **Requirement**: MCPProxy runs in Docker, reset before each baseline recording
- **This Feature**: Verify Docker container accessibility from scenario runner

### Principle VII: Path-Independent Configuration
- **Status**: ✅ IMPLEMENTED - Environment variables used (MCPPROXY_SOURCE_PATH, etc.)
- **Requirement**: No hardcoded user-specific paths, configurable via env vars
- **This Feature**: No action required - already compliant

### Principle VIII: Clean Git Commit Hygiene
- **Status**: ⏳ PENDING - Recent SDK updates uncommitted
- **Requirement**: No AI attribution markers in commit messages
- **This Feature**: CRITICAL - Commit fixes with clean messages, create PR

**GATE STATUS**: ⚠️ CONDITIONAL PASS - Implementation Required
- **Blocking Issues**: Principles I, III, V must be implemented in this feature
- **Deferred**: Principle II (modularity) remains out of scope (40+ hour refactoring)
- **Justification**: User explicitly requires Principles I, III, V to be fully implemented, not just audited
- **Action**: Proceed to Phase 0/1 with expanded scope including dual-agent design and structured logging schema

## Project Structure

### Documentation (this feature)

```text
specs/002-fix-dialog-engine-mcp/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output - SDK API changes research
├── compliance-audit.md  # Constitution compliance audit report
├── quickstart.md        # Testing and validation quickstart
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mcp_eval/
├── __init__.py
├── cli.py                     # Click CLI - test/record/compare commands
├── scenario_engine.py         # Dialog execution with ClaudeSDKClient
├── scenario_runner.py         # Scenario orchestration and reporting
├── evaluator.py               # Trajectory similarity comparison
├── similarity.py              # Jaccard, cosine, distance algorithms
├── html_reporter.py           # Visual HTML report generation
└── reporter.py                # JSON report generation

scenarios/
├── list_all_servers.yaml      # Simple scenario for testing
├── security/
│   └── *.yaml                 # Security-related scenarios
└── tool_management/
    └── *.yaml                 # Server management scenarios

tests/
└── test_similarity.py         # Unit tests for similarity algorithms

baselines/
└── */                         # Reference execution logs

reports/
└── *.html                     # Generated HTML reports
```

**Structure Decision**: Single Python package structure (Option 1) - This is a CLI tool for evaluating MCP servers, not a web app or mobile application. All evaluation logic lives in src/mcp_eval/ with clear separation between:
- CLI interface (cli.py)
- Dialog execution (scenario_engine.py, scenario_runner.py)
- Evaluation/comparison (evaluator.py, similarity.py)
- Reporting (html_reporter.py, reporter.py)

Test scenarios are stored in scenarios/ directory with subdirectory organization per constitution Principle V.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle II: Dialog Engine Modularity | Current implementation tightly couples dialog engine to mcp_eval package | Refactoring into separate package would require significant architectural changes (estimated 40+ hours including API design, migration, testing, documentation). User approved deferral to future work. Current coupling does not prevent implementing dual-agent architecture, structured logging, or MCP access within existing package structure. |

**Note**: Principles I (Dual-Agent Architecture), III (Structured Logging), and V (Deterministic Evaluation) are NO LONGER violations - they will be fully implemented in this feature per user requirements.

---

## Phase 0: Outline & Research

### Research Questions

1. **Claude Agent SDK API Changes**: What breaking changes were introduced in claude-agent-sdk>=0.1.6 that affect scenario_engine.py?
   - Method signature changes in ClaudeSDKClient
   - ClaudeAgentOptions parameter changes
   - Deprecated methods that need replacement

2. **Temperature Parameter Configuration**: How is temperature=0.0 set in current Claude Agent SDK?
   - Initialization location (ClaudeAgentOptions vs client configuration)
   - Verification method to confirm temperature is applied

3. **MCP Server Access Pattern**: How does AI Agent role get MCP server access in Claude Agent SDK?
   - MCP configuration file loading mechanism
   - Permission modes (bypassPermissions vs prompt-based)
   - Tool discovery and schema retrieval flow

4. **Dual-Agent Architecture Design**: How should User Agent and AI Agent interact?
   - User Agent responsibilities (scenario intent, clarification responses, goal evaluation)
   - AI Agent wrapper design around ClaudeSDKClient
   - Communication protocol between agents
   - Scenario orchestration flow

5. **Structured Logging Schema Design**: What complete schema supports all constitution requirements?
   - DialogTurn dataclass structure with all required fields
   - Turn type enumeration (USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE)
   - Actor enumeration (User, AI_Agent, System)
   - Metadata structure for tools, timestamps, errors, git hashes
   - JSON serialization format

### Research Tasks

1. Review claude-agent-sdk>=0.1.6 changelog and migration guide
2. Examine ClaudeAgentOptions API documentation for temperature parameter
3. Inspect ConversationInterceptor usage in main.py (imported in scenario_engine.py line 19)
4. Analyze existing ToolCallRecord and ScenarioResult dataclasses for missing fields
5. Review evaluator.py mcp__* filtering logic to confirm compliance with Principle IV
6. **NEW**: Design dual-agent architecture pattern (User Agent + AI Agent classes, interaction protocol)
7. **NEW**: Design complete DialogTurn schema with all constitution-required fields
8. **NEW**: Plan integration of structured logging into existing scenario execution flow

**Output**: research.md documenting SDK changes, temperature configuration, MCP access patterns, dual-agent architecture design, and complete logging schema

---

## Phase 1: Design & Contracts

**Prerequisites:** research.md complete

### Compliance Audit Document

Create `compliance-audit.md` documenting:

**Constitution Principle Review**:
- Principle I (Dual-Agent): Current architecture analysis, **implementation plan for User Agent and AI Agent separation**
- Principle II (Modularity): Coupling analysis, refactoring effort estimate, **deferred justification**
- Principle III (Logging): Existing schema vs required schema gap analysis, **implementation plan for full DialogTurn schema**
- Principle IV (Similarity): MCP-only filtering verification (already compliant)
- Principle V (Deterministic): Temperature=0.0 **configuration plan and verification steps**
- Principle VI (Docker): Port 8081 connectivity test results (already compliant)
- Principle VII (Paths): Environment variable usage verification (already compliant)
- Principle VIII (Git): Uncommitted files audit, commit message standards (pending commit)

**Code Locations**:
- scenario_engine.py:103-114 - ClaudeSDKClient initialization (to be refactored for AI Agent)
- scenario_engine.py:23-30 - ToolCallRecord dataclass (to be replaced with DialogTurn)
- scenario_runner.py:24-29 - FailureAwareScenarioRunner init (to integrate dual-agent orchestration)
- evaluator.py - MCP-only filtering logic (already compliant)

**Implementation Priorities**:
- **P0 (Critical)**: Temperature=0.0 configuration (blocks all evaluation)
- **P1 (High)**: Structured logging schema (enables proper trajectory comparison)
- **P2 (High)**: Dual-agent architecture (constitution compliance, enables clarifications)
- **Deferred**: Modularity (separate package refactoring, 40+ hours)

### Testing Quickstart

Create `quickstart.md` with step-by-step validation procedure:

```markdown
# Testing Quickstart: Dialog Engine Fix Validation

## Prerequisites
- MCPProxy docker container running on port 8081
- Python 3.11+ with uv package manager
- Claude Agent SDK updated to >=0.1.6

## Step 1: Verify Docker Container
```bash
docker ps --filter "name=mcpproxy" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl -f http://localhost:8081/health || echo "MCPProxy not ready"
```

## Step 2: Run Simple Scenario
```bash
./testing/reset-mcpproxy.sh
PYTHONPATH=src uv run python -m mcp_eval.cli test --scenario scenarios/list_all_servers.yaml
```

## Step 3: Verify HTML Report
```bash
open reports/list_all_servers_*.html
# Check for:
# - MCP tool calls (mcp__mcpproxy__upstream_servers)
# - Expandable tool details
# - No SDK deprecation errors in logs
```

## Step 4: Validate Structured Logs
```bash
cat baselines/list_all_servers_baseline/detailed_log.json | jq '.messages[] | select(.type == "TOOL_CALL")'
# Verify fields: timestamp, type, tool_name, tool_input, metadata
```

## Success Criteria
- ✅ MCPProxy accessible on port 8081
- ✅ Scenario executes without SDK errors
- ✅ HTML report generated with MCP tool calls
- ✅ Structured logs contain tool call records
```

### Data Models Required

Create `data-model.md` documenting new and updated entities:

#### New Entities

**DialogTurn**:
- Fields: turn_id (int), timestamp (datetime with microseconds), turn_type (enum), actor (enum), content (str), metadata (dict)
- Turn Type Enum: USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE
- Actor Enum: User, AI_Agent, System
- Relationships: Part of DialogSession, references ToolCallRecord for TOOL_CALL turns
- Validation: Timestamp ISO-8601 format, turn_type and actor must be valid enum values
- Serialization: JSON with nested metadata structure

**UserAgent**:
- Fields: scenario (ScenarioConfig), current_turn (int), clarification_responses (list)
- Responsibilities: Issues user intents from scenario, responds to clarifications, evaluates goal achievement
- Methods: issue_intent(), handle_clarification_request(), evaluate_result()
- State: Tracks conversation progress, knows scenario success criteria

**AIAgent**:
- Fields: claude_client (ClaudeSDKClient), mcp_config (str), temperature (float)
- Responsibilities: Executes user requests via MCP tools, asks clarifications when needed
- Methods: process_intent(), invoke_tool(), request_clarification()
- State: Wraps ClaudeSDKClient, has MCP server access

#### Updated Entities

**ToolCallRecord** → Deprecated, replaced by DialogTurn with turn_type=TOOL_CALL
**ScenarioResult** → Add dialog_turns: List[DialogTurn] field

Existing models: ScenarioConfig (from YAML), ConversationInterceptor (from main.py)

### No API Contracts Needed

This is a CLI tool with no REST/GraphQL endpoints. The "contract" is the YAML scenario format (already defined) and structured log JSON schema (requires validation, not creation).

**Output**: compliance-audit.md, quickstart.md

---

## Post-Phase 1: Constitution Re-Check

After completing research and design:

### Principle V: Deterministic Evaluation Runs
- **Updated Status**: ✅ READY TO IMPLEMENT - claude_settings.json schema identified
- **Action**: Populate settings file with `{"temperature": 0.0}`, verify with determinism test

### Principle III: Structured Dialog Logging
- **Updated Status**: 🔨 IMPLEMENTATION IN PROGRESS - DialogTurn schema designed
- **Action**: Implement DialogTurn dataclass, integrate into scenario execution flow, update HTML reporter

### Principle I: Dual-Agent Architecture
- **Updated Status**: 🔨 IMPLEMENTATION IN PROGRESS - UserAgent and AIAgent classes designed
- **Action**: Implement dual-agent classes, update scenario orchestration, add clarification handling

### Principle II: Dialog Engine Modularity
- **Updated Status**: ⏸️ DEFERRED - Separate package refactoring postponed to future feature
- **Action**: Document as accepted technical debt, proceed with in-package implementation

**FINAL GATE**: All CRITICAL blockers must be resolved before proceeding to `/speckit.tasks`

---

## Notes

- **Scope Expanded**: This feature now includes full implementation of constitution Principles I, III, and V, not just fixes
- **Implementation Order**: P0 (Temperature=0.0) → P1 (Structured Logging) → P2 (Dual-Agent Architecture)
- Constitution Principle II (modularity) violation is accepted as technical debt for future resolution (40+ hour refactoring)
- Temperature=0.0 is CRITICAL - scenario execution is meaningless without determinism, must be implemented first
- MCP server access on port 8081 is BLOCKING - no tool calls means no trajectory data
- Dual-agent architecture enables constitution compliance and future clarification request scenarios
- Structured logging enables proper trajectory comparison and debugging
- HTML report generation validates end-to-end pipeline - if reports render, pipeline works
- Git commit hygiene (Principle VIII) is non-negotiable - all commits must be clean
- SDK deprecation warnings must be resolved - cannot ship code using deprecated APIs
- **Estimated Effort**: P0 (2 hours) + P1 (8 hours) + P2 (12 hours) = 22 hours total implementation time

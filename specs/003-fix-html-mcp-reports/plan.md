# Implementation Plan: Fix HTML Reports and MCP Tool Validation

**Branch**: `003-fix-html-mcp-reports` | **Date**: 2025-11-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/spec.md`

## Summary

Fix empty HTML reports by implementing dialog turn rendering from the new dual-agent dialog engine, and resolve MCPProxy container shell dependency issues to enable AI agent MCP tool access. The implementation adds dialog_turns visualization to HTML reports (both baseline and comparison), includes bash package in Alpine Linux container, and validates MCP configuration before scenario execution. This unblocks MCP validation testing and provides complete visibility into conversation flows.

**Technical Approach**: Extend existing `html_reporter.py` to check for `dialog_turns` field in detailed_log.json and render chronologically with turn-type-specific styling (Constitution Principle III). Modify MCPProxy Dockerfile to include bash package. Add pre-flight validation to verify container health and MCP config before executing scenarios. Implement side-by-side dialog turn comparison with diff highlighting for regression testing.

## Technical Context

**Language/Version**: Python 3.11.1
**Primary Dependencies**: claude-agent-sdk (>=0.1.6), click (>=8.2.1), pydantic (>=2.11.7), pyyaml (>=6.0.2), rich (>=14.1.0), python-dotenv (>=1.0.0)
**Storage**: JSON files for baselines and execution logs, HTML files for reports
**Testing**: pytest (>=8.4.1) for unit/integration tests
**Target Platform**: macOS/Linux development machines with Docker Desktop
**Project Type**: Single project (mcp-eval codebase)
**Performance Goals**: <2 seconds to generate HTML report for 200 dialog turns
**Constraints**: Must maintain backward compatibility with legacy messages format, Docker image size increase <5MB
**Scale/Scope**: Handle 200+ dialog turns per session, support batch evaluation across 50+ scenarios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Dual-Agent Dialog Engine Architecture
**Status**: COMPLIANT - No Changes Required
**Rationale**: Feature enhances visibility of existing dual-agent architecture through HTML rendering. Does not modify DialogSession, UserAgent, or AIAgent implementations. Dialog turn recording already implemented in scenario_runner.py (lines 437-439). This feature makes the architecture observable via HTML reports.

### ✅ Principle II: Dialog Engine Modularity & Reusability
**Status**: COMPLIANT - No Changes Required
**Rationale**: HTML reporter is separate from dialog engine package. Changes isolated to presentation layer (html_reporter.py) and infrastructure layer (Dockerfile). No coupling introduced between dialog engine and MCPProxy-specific code. MCP config validation remains pluggable via mcp_servers.json.

### ✅ Principle III: Structured Dialog Logging for Trajectory Scoring
**Status**: COMPLIANT - Enhances Compliance
**Rationale**: Feature improves structured logging visibility by rendering all DialogTurn fields (timestamp, turn_type, actor, content, metadata) in HTML. No schema changes required - reads existing dialog_turns field populated by DialogSession.execute(). Adds human-readable presentation layer on top of machine-readable JSON logs.

### ✅ Principle IV: Similarity-Based Trajectory Evaluation
**Status**: COMPLIANT - No Changes Required
**Rationale**: Feature displays existing similarity scores in HTML reports via per_invocation_results. Does not modify evaluation algorithms in evaluator.py or similarity.py. Existing MCP-only filtering preserved in HTML rendering through tool-mcp CSS class.

### ✅ Principle V: Deterministic Evaluation Runs
**Status**: COMPLIANT - No Changes Required
**Rationale**: HTML rendering is presentation-only, does not affect scenario execution determinism. Temperature=0.0 setting unchanged. Docker container reset procedure maintained. Feature adds visibility without impacting reproducibility.

### ✅ Principle VI: Docker Isolation for Reproducibility
**Status**: COMPLIANT - Enhances Compliance
**Rationale**: Feature strengthens Docker isolation by adding bash package for complete shell compatibility. Container reset protocol preserved. Health check validation added to ensure clean state before execution. Port isolation (8081) maintained. No changes to state reset workflow.

### ✅ Principle VII: Path-Independent Configuration
**Status**: COMPLIANT - No Changes Required
**Rationale**: All MCP configuration remains environment-variable driven (MCPPROXY_SOURCE_PATH, TEST_SESSION, TEST_PORT). No hardcoded paths introduced. Config validation reads from configurable mcp_servers.json path. Docker context uses relative paths.

### ✅ Principle VIII: Clean Git Commit Hygiene
**Status**: COMPLIANT - Required for Implementation
**Rationale**: Per CLAUDE.md global guidelines, all commits must exclude AI attribution markers. Implementation commits will follow clean message format: "Fix HTML report dialog turn rendering" not "Add feature 🤖 Generated with Claude Code".

### Constitution Compliance Summary

**Overall Status**: ✅ FULLY COMPLIANT
**Violations**: None
**Enhancements**: Principles III (structured logging visibility) and VI (Docker isolation robustness)
**Required Reviews**: None - no constitutional amendments needed

## Project Structure

### Documentation (this feature)

```text
specs/003-fix-html-mcp-reports/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created yet)
```

### Source Code (repository root)

```text
src/mcp_eval/
├── html_reporter.py       # ✏️ MODIFY: Add dialog_turns rendering
│                          #   - New: _render_dialog_turns_section()
│                          #   - Modify: _generate_conversation_html()
│                          #   - Modify: _generate_comparison_conversation_html()
│                          #   - Add: _generate_dialog_turn_diff_html()
│                          #   - Add CSS: .turn-added, .turn-removed, .turn-modified
├── dialog_models.py       # ✅ READ-ONLY: DialogTurn structure reference
├── dialog_session.py      # ✅ READ-ONLY: Session execution flow
├── agents.py              # ✏️ MODIFY: Update AIAgent system prompt
│                          #   - Modify: system_prompt to prioritize MCPProxy tools
│                          #   - Add explicit instructions for mcp__mcpproxy__* tools
│                          #   - Ensure agent uses MCPProxy for tool discovery/server management
├── scenario_runner.py     # ✏️ MODIFY: Add MCP validation
│                          #   - New: _validate_mcp_config()
│                          #   - New: _check_container_health()
│                          #   - Modify: execute_scenario() add pre-flight checks
└── evaluator.py           # ✅ READ-ONLY: Similarity scoring reference

testing/docker/
├── Dockerfile             # ✏️ MODIFY: Add bash package
│                          #   Line 4: Add 'bash' to apk add command
├── docker-compose.yml     # ✅ READ-ONLY: Port mapping reference
├── entrypoint.sh          # ✅ READ-ONLY: Startup script (uses /bin/sh)
└── config-template.json   # ✅ READ-ONLY: MCPProxy config example

tests/
├── test_html_reporter.py  # ✏️ NEW: Unit tests for dialog turn rendering
├── test_dialog_models.py  # ✅ READ-ONLY: DialogTurn serialization tests
└── integration/
    └── test_scenario_execution.py  # ✏️ NEW: End-to-end dialog turn flow

mcp_servers.json           # ✅ VERIFY: Must point to port 8081
claude_settings.json       # ✅ VERIFY: temperature=0.0 present
```

**Structure Decision**: Single project structure maintained. Changes isolated to two modules (html_reporter.py, scenario_runner.py) and one infrastructure file (Dockerfile). No new packages or directories required. Testing follows existing pytest structure with unit tests alongside source files.

## Complexity Tracking

> **No violations identified** - Table not required per template guidelines

**Justification**: Feature adds straightforward HTML rendering logic and Docker package installation. No architectural complexity introduced. Uses existing data structures (DialogTurn), existing styling patterns (CSS classes for turn types), and existing container management (docker compose). Backward compatibility maintained through fallback to legacy messages format.

---

## Phase 0: Research

**Status**: ✅ COMPLETED
**Output**: research.md created with technical decisions
**Duration**: Completed before plan creation

### Research Artifacts Created

1. **research.md** - Documents four key decisions:
   - Dialog turn HTML rendering approach (chronological with type-based styling)
   - MCPProxy bash dependency solution (add to Alpine packages)
   - Diff visualization strategy (side-by-side with color coding)
   - MCP tool access validation (pre-flight health checks)

### Key Research Findings

1. **Dialog Turns Already Populated**: scenario_runner.py line 439 sets `execution_data["dialog_turns"]` from DialogSession.execute() - no data collection changes needed

2. **Alpine Linux Shell Gap**: MCPProxy Dockerfile uses alpine:3.19 with /bin/sh, but upstream server processes may expect /bin/bash

3. **HTML Reporter Extension Point**: Existing `_generate_conversation_html()` method at line 405-496 provides clear insertion point for dialog_turns rendering

4. **MCP Config Critical**: AI agent initialization requires mcp_servers.json pointing to correct port (8081), verified at agents.py lines 136-146

### Research Questions Answered

- **Q1**: How to render dialog turns? → Extract from detailed_log.json, render chronologically with turn-type styling
- **Q2**: Why bash missing? → Alpine Linux default shell is ash (/bin/sh)
- **Q3**: How to visualize diffs? → Side-by-side with color-coded turn alignment
- **Q4**: How to ensure MCP access? → Validate config and container health pre-execution

**Research Dependencies**: None - research complete and documented

---

## Phase 1: Design

**Status**: ✅ COMPLETED
**Output**: data-model.md, quickstart.md created
**Duration**: Completed before plan creation

### Design Artifacts Created

1. **data-model.md** - Comprehensive data model documentation:
   - DialogTurn schema with all turn types and metadata fields
   - HTMLReportData structure for baseline and comparison reports
   - Tool invocation data flow from dialog_turns to HTML
   - Per-invocation result schema for similarity display
   - Edge case handling (empty turns, orphaned results, long content)

2. **quickstart.md** - Developer testing guide:
   - MCPProxy Docker reset procedure with verification steps
   - MCP configuration validation checklist
   - Test scenario execution workflow
   - HTML report verification steps
   - Debugging tips for common issues

### Design Decisions

**1. Dialog Turn Rendering**:
```
Priority: Check dialog_turns field first
Fallback: Legacy messages format if empty
Render: Chronological order by turn_id
Styling: Turn-type specific (USER=blue, AGENT=green, TOOL=orange)
Nesting: TOOL_RESULT under TOOL_CALL (matched by tool_id)
```

**2. Diff Visualization**:
```
Algorithm: Position-based turn matching
Color Coding: Green=ADDED, Red=REMOVED, Yellow=MODIFIED
Layout: Side-by-side columns (current | baseline)
Filtering: Checkbox controls for tool type visibility
```

**3. Container Validation**:
```
Health Check: curl http://localhost:8081/health
Port Verify: docker port mcpproxy-test-test777-dind
Config Check: grep "8081" mcp_servers.json
Timing: Run before DialogSession.execute()
```

**4. Error Handling**:
```
Empty dialog_turns → Fall back to messages
Orphaned TOOL_RESULT → Render standalone with warning
Missing metadata → Use "unknown" placeholders
Long content → Truncate at 10,000 chars with "show more"
```

### Design Contracts

**Contract 1: DialogTurn → HTML**
- **Input**: List[Dict] from detailed_log.json["dialog_turns"]
- **Output**: HTML string with styled message cards
- **Contract**: Turn sequence preserved, all metadata visible on demand
- **Location**: html_reporter.py `_render_dialog_turns_section()`

**Contract 2: MCP Config Validation**
- **Input**: mcp_servers.json path, container name
- **Output**: Boolean (valid/invalid) + error messages
- **Contract**: Non-blocking for non-critical failures, hard fail for missing config
- **Location**: scenario_runner.py `_validate_mcp_config()`

**Contract 3: Diff Alignment**
- **Input**: current_turns: List[DialogTurn], baseline_turns: List[DialogTurn]
- **Output**: aligned_pairs: List[Tuple[Optional[DialogTurn], Optional[DialogTurn], DiffType]]
- **Contract**: All turns from both sides represented, no duplicates
- **Location**: html_reporter.py `_align_dialog_turns_for_diff()`

### Architecture Diagrams

**Data Flow** (from data-model.md):
```
DialogSession.execute()
  → dialog_turns populated
  → scenario_runner saves detailed_log.json
  → html_reporter reads dialog_turns
  → renders chronological HTML
```

**Rendering Decision Tree**:
```
Read detailed_log.json
  ├─ Has dialog_turns? YES
  │   ├─ Length > 0? YES → Render dialog turns
  │   └─ Length = 0? → Fall back to messages
  └─ Has dialog_turns? NO → Fall back to messages
```

**Phase 1 Dependencies**: Phase 0 research complete (✅)

---

## Phase 2: Task Generation

**Status**: ⏸️ PENDING
**Trigger**: Run `/speckit.tasks` command after plan approval
**Output**: tasks.md with dependency-ordered implementation tasks

### Task Generation Scope

**Tasks will cover**:
1. Dockerfile modification (bash package)
2. HTML reporter dialog_turns rendering
3. Diff visualization for comparison reports
4. MCP configuration validation
5. Unit tests for new rendering logic
6. Integration tests for end-to-end flow
7. Documentation updates (CLAUDE.md examples)

**Task Dependencies**:
- Dockerfile changes independent (can run in parallel)
- HTML rendering depends on data model understanding
- Diff visualization depends on basic rendering complete
- Tests depend on implementation complete

**Not included in tasks** (per spec Out of Scope):
- UI/UX redesign of HTML layout
- Real-time streaming of dialog turns
- Interactive filtering within reports
- Export to non-HTML formats
- Performance optimization for >200 turns

---

## Phase 3: Implementation

**Status**: ⏸️ NOT STARTED
**Trigger**: Run `/speckit.implement` after tasks.md created
**Process**: Execute tasks sequentially with validation gates

### Implementation Checklist

Pre-implementation validation:
- [ ] Plan.md approved by maintainers
- [ ] Constitution check passed (✅ already verified)
- [ ] Tasks.md generated with clear acceptance criteria
- [ ] Development environment set up (Docker, Python 3.11, uv)
- [ ] MCPProxy source available at MCPPROXY_SOURCE_PATH

Implementation sequence (from tasks.md - to be generated):
- [ ] Task 1: Docker bash package installation
- [ ] Task 2: HTML reporter dialog_turns rendering
- [ ] Task 3: Side-by-side diff visualization
- [ ] Task 4: MCP config validation
- [ ] Task 5: Unit test coverage
- [ ] Task 6: Integration test scenarios
- [ ] Task 7: Documentation updates

Post-implementation validation:
- [ ] All tests passing (pytest coverage ≥80%)
- [ ] HTML reports display dialog turns correctly
- [ ] Comparison reports show similarity scores
- [ ] MCP tools accessible from AI agent
- [ ] Docker container builds and runs successfully
- [ ] Backward compatibility verified (legacy messages still render)

---

## Success Metrics (from spec.md)

**SC-001**: HTML reports display complete dialog turn history for 100% of executed scenarios
**Verification**: Run 10 diverse scenarios, check each HTML report shows all dialog turns from detailed_log.json

**SC-002**: Users can identify all MCP tool invocations in HTML reports within 30 seconds
**Verification**: User study with 3 evaluators, measure time to locate MCP tools in 5 reports

**SC-003**: AI agent successfully invokes MCP tools in 95% of scenarios without container errors
**Verification**: Run 20 scenarios, count successful TOOL_RESULT entries with is_error=false

**SC-004**: MCPProxy container starts without shell-related errors in 100% of deployments
**Verification**: 10 fresh container builds, grep logs for "bash" errors, expect 0 occurrences

**SC-005**: Evaluation engineers can compare dialog trajectories and identify behavioral differences within 2 minutes
**Verification**: User study with 3 engineers, measure time to spot 3 inserted turn differences in comparison reports

**SC-006**: HTML reports load and render completely for sessions with up to 200 dialog turns without performance issues
**Verification**: Generate HTML for 200-turn session, measure load time <2 seconds, verify all turns visible

---

## Risks and Mitigations

### Risk 1: Backward Compatibility Break
**Likelihood**: Low
**Impact**: High (breaks existing baselines)
**Mitigation**: Implement fallback to legacy messages format if dialog_turns empty. Test with 10 existing baselines before release.

### Risk 2: Docker Image Size Increase
**Likelihood**: High (bash package ~1-2MB)
**Impact**: Low (acceptable per constraints)
**Mitigation**: Measure image size before/after, verify increase <5MB. Document in CHANGELOG.

### Risk 3: HTML Rendering Performance Degradation
**Likelihood**: Medium (complex rendering logic)
**Impact**: Medium (slow report generation)
**Mitigation**: Profile rendering with 200-turn sessions. Cache compiled regex patterns. Limit rendered metadata to essentials.

### Risk 4: MCP Container Health Check False Negatives
**Likelihood**: Medium (timing-sensitive)
**Impact**: High (blocks scenario execution)
**Mitigation**: Implement retry logic with exponential backoff. Log detailed error messages. Allow manual override via --skip-validation flag.

---

## Open Questions

### Q1: Should tool result content be truncated in HTML?
**Context**: TOOL_RESULT content can be very long (e.g., 100KB JSON responses)
**Options**: A) Show first 500 chars + expand button, B) Always show full content, C) Show preview + download link
**Recommendation**: Option A - matches existing tool result preview pattern (line 543-553 in html_reporter.py)
**Decision Needed By**: Task generation phase

### Q2: How to handle missing dialog_turns in comparison reports?
**Context**: Baseline may have dialog_turns but current execution does not (or vice versa)
**Options**: A) Fail comparison, B) Compare only legacy tool_calls_summary, C) Show warning and compare what's available
**Recommendation**: Option C - graceful degradation with clear warning badge
**Decision Needed By**: Task generation phase

### Q3: Should container validation be required or optional?
**Context**: Pre-flight health checks may slow down rapid development iterations
**Options**: A) Always required, B) Optional via --skip-validation flag, C) Required only for baseline recording
**Recommendation**: Option C - strict for baselines, lenient for development
**Decision Needed By**: Implementation phase

---

## References

- Feature Spec: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/spec.md`
- Constitution: `/Users/user/repos/mcp-eval/.specify/memory/constitution.md`
- Research: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/research.md`
- Data Model: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/data-model.md`
- Quickstart: `/Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/quickstart.md`
- CLAUDE.md: `/Users/user/repos/mcp-eval/CLAUDE.md` (Docker container requirements, git commit standards)
- Existing HTML Reporter: `/Users/user/repos/mcp-eval/src/mcp_eval/html_reporter.py`
- Dialog Models: `/Users/user/repos/mcp-eval/src/mcp_eval/dialog_models.py`
- Scenario Runner: `/Users/user/repos/mcp-eval/src/mcp_eval/scenario_runner.py`

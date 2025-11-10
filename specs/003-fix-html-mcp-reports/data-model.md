# Data Model: HTML Reports and Dialog Turn Rendering

**Feature**: 003-fix-html-mcp-reports
**Date**: 2025-11-10

## Overview

This document specifies the data structures and flow for rendering dialog turns in HTML reports. The system must support both new dialog_turns format (from DialogSession) and legacy messages format (for backward compatibility).

## Core Data Structures

### DialogTurn (Source: dialog_models.py)

**Purpose**: Represents a single interaction step in the conversation between User and AI Agent.

**Schema**:
```python
@dataclass
class DialogTurn:
    turn_id: int                    # Sequential turn counter (1-based)
    timestamp: datetime             # ISO-8601 with microsecond precision
    turn_type: TurnType             # Enum: USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, etc.
    actor: Actor                    # Enum: User, AI_Agent, System
    content: str                    # Full message text or tool invocation description
    metadata: Dict[str, Any]        # Turn-specific metadata
```

**JSON Serialization** (via to_dict()):
```json
{
  "turn_id": 1,
  "timestamp": "2025-11-10T14:32:15.123456",
  "turn_type": "USER_MESSAGE",
  "actor": "User",
  "content": "I need to find tools for managing GitHub repositories",
  "metadata": {
    "scenario_intent": "I need to find tools for managing GitHub repositories",
    "is_clarification_response": false
  }
}
```

**Turn Types**:
- `USER_MESSAGE`: User issues request or provides input
- `AGENT_MESSAGE`: AI agent responds with text (thinking/explanation)
- `TOOL_CALL`: AI agent invokes MCP or framework tool
- `TOOL_RESULT`: System returns tool execution result
- `CLARIFICATION_REQUEST`: AI agent asks user for more information
- `CLARIFICATION_RESPONSE`: User provides clarification

**Actors**:
- `User`: UserAgent (roleplays human)
- `AI_Agent`: AIAgent (has MCP tool access)
- `System`: Tool execution environment

**Metadata Fields by Turn Type**:

**USER_MESSAGE**:
```python
{
    "scenario_intent": str,           # Original user intent from scenario
    "is_clarification_response": bool # Whether this is answering a question
}
```

**AGENT_MESSAGE**:
```python
{
    "message_index": int,             # Sequential message counter
    "thinking_visible": bool          # Whether internal thinking shown
}
```

**TOOL_CALL**:
```python
{
    "tool_name": str,                 # e.g., "mcp__mcpproxy__retrieve_tools"
    "tool_id": str,                   # Unique identifier (e.g., "toolu_abc123")
    "tool_input": Dict[str, Any],     # Tool arguments
    "is_mcp_tool": bool              # True if tool_name starts with "mcp__"
}
```

**TOOL_RESULT**:
```python
{
    "tool_use_id": str,               # Matches tool_id from TOOL_CALL
    "is_error": bool,                 # Whether tool execution failed
    "result_size_bytes": int,         # Size of result payload
    "execution_time_ms": int          # Tool execution duration
}
```

**CLARIFICATION_REQUEST**:
```python
{
    "clarification_question": str,    # Question text
    "options": List[str],             # Possible answers
    "question_id": str                # Unique question identifier
}
```

**CLARIFICATION_RESPONSE**:
```python
{
    "question_id": str,               # References CLARIFICATION_REQUEST
    "selected_option": str,           # Chosen answer
    "is_clarification_response": bool # Always true
}
```

---

### HTMLReportData (Conceptual - not a Python class)

**Purpose**: Aggregated data structure passed to HTML report generator.

**Structure**:
```python
{
    # Scenario metadata
    "scenario": str,                          # Scenario name
    "execution_time": str,                    # ISO-8601 timestamp
    "user_intent": str,                       # Original user request
    "execution_status": str,                  # SUCCESS, FAILED, BLOCKED, etc.

    # Git version tracking
    "mcpproxy_git_info": {
        "git_hash": str,                      # Full commit hash
        "git_hash_short": str,                # 8-character short hash
        "commit_message": str,                # Commit subject line
        "commit_date": str,                   # ISO-8601 commit date
        "branch": str                         # Git branch name
    },

    # Dialog session data (NEW - Constitution Principle III)
    "dialog_turns": List[Dict[str, Any]],     # DialogTurn.to_dict() array
    "session_id": str,                        # Session identifier
    "dialog_session_status": str,             # Dialog session outcome
    "dialog_execution_time": float,           # Duration in seconds

    # Legacy backward-compatible fields
    "messages": List[Dict[str, Any]],         # Old message format
    "tool_calls_summary": List[Dict[str, Any]], # Extracted tool calls

    # Failure analysis
    "failure_analysis": {
        "total_tools": int,                   # Number of tools invoked
        "failed_tools": int,                  # Number of failures
        "failures": List[Dict],               # Failure details
        "success_rate": float                 # 0.0 to 1.0
    },

    # Termination info
    "early_stopped": bool,                    # Whether execution blocked early
    "available_tools": {                      # Tool discovery metadata
        "discovery_method": str,
        "tools": List[Dict],
        "discovered_at": str
    }
}
```

**Usage**:
- `baseline_data`: HTMLReportData from baseline execution
- `current_data`: HTMLReportData from evaluation run
- `comparison_result`: Similarity scores and diff analysis

---

### Tool Invocation Summary (Legacy Format)

**Purpose**: Backward-compatible tool call representation extracted from dialog_turns.

**Schema**:
```python
{
    "tool_name": str,                  # Tool identifier
    "tool_id": str,                    # Unique call ID
    "tool_input": Dict[str, Any],      # Arguments
    "timestamp": str,                  # ISO-8601 timestamp
    "response": {                      # Tool result
        "content": [                   # Result blocks
            {
                "type": "text",
                "text": str            # Result text
            }
        ],
        "is_error": bool              # Success/failure flag
    },
    "error": Optional[str]            # Error message if failed
}
```

**Extraction Logic** (scenario_runner.py `_extract_tool_calls_from_turns`):
1. Iterate through dialog_turns
2. For each TOOL_CALL turn, create pending entry with tool_name, tool_id, tool_input
3. For each TOOL_RESULT turn, match by tool_use_id and populate response
4. Add error field if is_error=True in metadata

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Scenario Execution (scenario_runner.py)                        │
│                                                                 │
│  DialogSession.execute()                                        │
│    ├─ UserAgent.issue_intent() → DialogTurn(USER_MESSAGE)     │
│    ├─ AIAgent.process_intent() → List[DialogTurn]             │
│    │    ├─ AGENT_MESSAGE (thinking/explanation)               │
│    │    ├─ TOOL_CALL (tool invocation)                        │
│    │    └─ TOOL_RESULT (tool response)                        │
│    └─ Returns: session_result with "turns" field              │
│                                                                 │
│  execution_data["dialog_turns"] = session_result["turns"]      │
│  execution_data["tool_calls_summary"] =                        │
│      _extract_tool_calls_from_turns(dialog_turns)              │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                           ↓ save_execution_results()
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Persistent Storage                                              │
│                                                                 │
│  baselines/scenario_name/detailed_log.json                      │
│  {                                                              │
│    "scenario": "...",                                           │
│    "execution_time": "...",                                     │
│    "dialog_turns": [                                            │
│      {                                                          │
│        "turn_id": 1,                                            │
│        "timestamp": "2025-11-10T14:32:15.123456",              │
│        "turn_type": "USER_MESSAGE",                             │
│        "actor": "User",                                         │
│        "content": "...",                                        │
│        "metadata": {...}                                        │
│      },                                                         │
│      ...                                                        │
│    ],                                                           │
│    "tool_calls_summary": [...],  // Backward compatibility      │
│    "messages": [...],             // Legacy format              │
│    ...                                                          │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                           ↓ load baseline/current data
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ HTML Report Generation (html_reporter.py)                       │
│                                                                 │
│  generate_baseline_report(baseline_data, scenario_name)         │
│    ├─ _generate_conversation_html(messages, tool_calls,        │
│    │                              dialog_turns)                │
│    │    ├─ Check if dialog_turns exists and non-empty          │
│    │    ├─ If YES: Render dialog turns chronologically         │
│    │    │    ├─ USER_MESSAGE → Blue card with user icon        │
│    │    │    ├─ AGENT_MESSAGE → Green card with agent icon     │
│    │    │    ├─ TOOL_CALL → Orange expandable card             │
│    │    │    └─ TOOL_RESULT → Nested under TOOL_CALL           │
│    │    └─ If NO: Fall back to legacy messages rendering       │
│    ├─ _generate_baseline_stats_html(baseline_data)             │
│    └─ _generate_available_tools_html(available_tools)          │
│                                                                 │
│  generate_comparison_report(current, baseline, comparison)      │
│    ├─ _generate_comparison_conversation_html()                 │
│    │    ├─ Side-by-side layout (current | baseline)            │
│    │    ├─ Render dialog_turns for both sides                  │
│    │    ├─ Highlight differences (added/removed/modified)       │
│    │    └─ Show similarity scores from comparison_result       │
│    └─ _generate_invocation_results_html(per_invocation)        │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ HTML Output                                                     │
│                                                                 │
│  reports/scenario_name_baseline_20251110_143215.html            │
│  ├─ Header: Scenario info, git hash, status badge              │
│  ├─ Statistics: Tool count, message count, success rate         │
│  ├─ Conversation Timeline:                                      │
│  │   ├─ Turn 1: USER_MESSAGE (blue card)                       │
│  │   ├─ Turn 2: AGENT_MESSAGE (green card)                     │
│  │   ├─ Turn 3: TOOL_CALL (orange expandable)                  │
│  │   │   └─ Tool input/output details                          │
│  │   └─ Turn 4: TOOL_RESULT (nested success/error)             │
│  └─ Footer: Generation timestamp                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## HTML Rendering Specifications

### Dialog Turn Card Structure

**USER_MESSAGE**:
```html
<div class="message user-message">
  <div class="message-header">
    <span class="message-type">👤 User</span>
    <span class="timestamp">2025-11-10T14:32:15</span>
  </div>
  <div class="message-content">
    I need to find tools for managing GitHub repositories
  </div>
</div>
```

**AGENT_MESSAGE**:
```html
<div class="message assistant-message">
  <div class="message-header">
    <span class="message-type">🤖 Assistant</span>
    <span class="timestamp">2025-11-10T14:32:16</span>
  </div>
  <div class="message-content">
    I'll search for GitHub-related tools in the MCP proxy.
  </div>
</div>
```

**TOOL_CALL + TOOL_RESULT** (combined expandable):
```html
<div class="message tool-message tool-mcp">
  <div class="tool-header" onclick="toggleToolCall('toolu_abc123')">
    <span class="tool-icon">🔧</span>
    <span class="tool-name">mcp__mcpproxy__retrieve_tools</span>
    <span class="tool-params">(query="GitHub repository management")</span>
    <span class="similarity-badge score-good">Sim: 0.950</span>
    <span class="expand-icon" id="icon-toolu_abc123">▶</span>
  </div>
  <div class="tool-details" id="details-toolu_abc123" style="display: none;">
    <div class="tool-section">
      <h4>📤 Tool Input:</h4>
      <pre class="json-code"><code>{ "query": "GitHub repository management" }</code></pre>
    </div>
    <div class="tool-section">
      <h4>📥 Tool Response:</h4>
      <div class="text-content">Found 10 GitHub tools: fork_repository, create_repository...</div>
    </div>
  </div>
</div>
```

### CSS Classes for Turn Types

```css
/* Turn type styling */
.user-message { border-left: 4px solid #3182ce; }        /* Blue */
.assistant-message { border-left: 4px solid #38a169; }   /* Green */
.tool-message { border-left: 4px solid #d69e2e; }        /* Orange */

/* Tool category filtering */
.tool-mcp { }                                             /* MCP tools - always visible */
.tool-non-mcp { display: none; }                         /* Framework tools - hidden by default */
.tool-todowrite { display: none; }                       /* TodoWrite - hidden by default */

/* Show when filter enabled */
.show-non-mcp .tool-non-mcp { display: block; }
.show-todowrite .tool-todowrite { display: block; }

/* Diff highlighting for comparison reports */
.turn-added { background: #c6f6d5; border-left-color: #38a169; }    /* Green */
.turn-removed { background: #fed7d7; border-left-color: #e53e3e; }  /* Red */
.turn-modified { background: #fef5e7; border-left-color: #d69e2e; } /* Yellow */
```

---

## Comparison Report Data Model

### Per-Invocation Result

**Purpose**: Track similarity scores for each tool invocation in trajectory comparison.

**Schema**:
```python
{
    "invocation": int,                    # Invocation sequence number (0-based)
    "score": float,                       # Similarity score (0.0 to 1.0)
    "details": str,                       # Human-readable description
    "actual_tools": [                     # Current execution tools
        {
            "name": str,                  # Tool name
            "similarity": float,          # Similarity to expected
            "input": Dict[str, Any]      # Tool arguments
        }
    ],
    "expected_tools": [                   # Baseline/expected tools
        {
            "name": str,
            "input": Dict[str, Any]
        }
    ]
}
```

**Example**:
```json
{
  "invocation": 0,
  "score": 0.950,
  "details": "Tool name match, high argument similarity",
  "actual_tools": [
    {
      "name": "mcp__mcpproxy__retrieve_tools",
      "similarity": 0.950,
      "input": {"query": "GitHub tools"}
    }
  ],
  "expected_tools": [
    {
      "name": "mcp__mcpproxy__retrieve_tools",
      "input": {"query": "GitHub repository management"}
    }
  ]
}
```

---

## Validation Rules

### Dialog Turn Validation

1. **turn_id**: Must be positive integer, sequential (no gaps)
2. **timestamp**: Must be valid ISO-8601 string, chronologically ordered
3. **turn_type**: Must be valid TurnType enum value
4. **actor**: Must be valid Actor enum value
5. **content**: Non-empty string (allow empty for TOOL_CALL if metadata complete)
6. **metadata**: Valid JSON object

### Tool Call Validation

1. **TOOL_CALL** must have metadata with: tool_name, tool_id, tool_input
2. **TOOL_RESULT** must reference existing TOOL_CALL via tool_use_id
3. **is_mcp_tool**: Must be True if tool_name starts with "mcp__"
4. Tool input must be valid JSON serializable dictionary

### HTML Report Validation

1. All dialog turns rendered in chronological order (sorted by turn_id)
2. TOOL_RESULT nested under corresponding TOOL_CALL (matched by tool_id)
3. Expandable sections start collapsed (display: none)
4. Color coding consistent with turn type and diff status
5. Similarity badges only shown for MCP tools in comparison reports

---

## Edge Cases

### Empty Dialog Turns

**Scenario**: `dialog_turns` field is empty list or missing
**Handling**: Fall back to legacy `messages` rendering
**Code**: Check `if not baseline_data.get("dialog_turns")` before rendering

### Orphaned Tool Results

**Scenario**: TOOL_RESULT with no matching TOOL_CALL
**Handling**: Render as standalone turn with warning indicator
**Display**: Show tool_use_id and result, mark with ⚠️ icon

### Very Long Content

**Scenario**: Turn content exceeds 10,000 characters
**Handling**: Truncate with "... (show more)" link
**Code**: `content[:10000] + ("..." if len(content) > 10000 else "")`

### Missing Metadata

**Scenario**: Required metadata fields missing (e.g., tool_name in TOOL_CALL)
**Handling**: Use fallback values: "unknown_tool", "unknown_id"
**Display**: Show with warning badge "⚠️ Incomplete metadata"

### Timestamp Parsing Errors

**Scenario**: Invalid ISO-8601 timestamp string
**Handling**: Display raw timestamp string, log warning
**Fallback**: Use "Invalid timestamp" placeholder

---

## Performance Considerations

### Large Dialog Sessions (>200 turns)

**Constitution Constraint**: Performance optimization out of scope for >200 turns
**Implementation**: No pagination/virtual scrolling required for MVP
**Warning**: Display notice if turn count exceeds 200

### Memory Usage

**Dialog turns in memory**: ~1KB per turn average
**200 turns**: ~200KB (acceptable)
**HTML file size**: ~500KB for 200 turns (acceptable)

### Rendering Speed

**Target**: <2 seconds to generate HTML for 200 turns
**Bottlenecks**: JSON syntax highlighting, CSS rendering
**Optimization**: Pre-compile regex patterns, minimize DOM traversal

---

## References

- Constitution Principle III: Structured Dialog Logging for Trajectory Scoring
- DialogTurn schema: /Users/user/repos/mcp-eval/src/mcp_eval/dialog_models.py
- HTML reporter: /Users/user/repos/mcp-eval/src/mcp_eval/html_reporter.py
- Scenario runner: /Users/user/repos/mcp-eval/src/mcp_eval/scenario_runner.py
- Feature spec: /Users/user/repos/mcp-eval/specs/003-fix-html-mcp-reports/spec.md

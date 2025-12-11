# Data Model: MCPProxy Control Server

**Feature**: 007-mcpproxy-control-server
**Date**: 2025-12-10

## Entities

### 1. TurnType (Extended Enum)

Extends existing `TurnType` enum in `dialog_models.py`:

| Value | Description | Actor |
|-------|-------------|-------|
| USER_MESSAGE | User sends message | USER |
| AGENT_MESSAGE | AI agent responds | AI_AGENT |
| TOOL_CALL | Agent invokes MCP tool | AI_AGENT |
| TOOL_RESULT | MCP tool returns result | SYSTEM |
| CLARIFICATION_REQUEST | Agent asks for clarification | AI_AGENT |
| CLARIFICATION_RESPONSE | User provides clarification | USER |
| **CONTROL_TOOL_CALL** | User Role invokes control MCP tool | USER |
| **CONTROL_TOOL_RESULT** | Control MCP tool returns result | SYSTEM |

### 2. UserControlAction

New entity for enhanced scenario format:

```python
@dataclass
class UserControlAction:
    """A control action executed by User Role during scenario."""
    trigger: str              # When to execute: "after_quarantine", "after_tool_N", "on_error"
    action: str               # Action name for trajectory matching
    tool: str                 # MCP tool name: "mcpproxy_control__unquarantine"
    args: Dict[str, Any]      # Tool arguments
    expected_result: Optional[Dict[str, Any]] = None  # Expected outcome for validation
```

**Trigger Types**:
- `after_tool_N` - After Nth agent tool call
- `after_quarantine` - When server enters quarantine state
- `on_error` - When agent tool call fails
- `before_completion` - Before final evaluation
- `manual` - Triggered by explicit instruction in user_intent

### 3. EnhancedScenario

Extended scenario model supporting user control actions:

```python
@dataclass
class EnhancedScenario:
    """Scenario with optional user control actions."""
    name: str
    description: str
    user_intent: str
    expected_trajectory: List[Dict[str, Any]]
    success_criteria: List[str]
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    config_file: Optional[str] = None
    # NEW fields
    user_control_actions: List[UserControlAction] = field(default_factory=list)
```

### 4. ControlToolCall (Log Entry)

Entry in detailed_log.json for control server calls:

```python
@dataclass
class ControlToolCall:
    """Log entry for control MCP server call."""
    timestamp: str            # ISO 8601
    type: str                 # "CONTROL_TOOL_CALL"
    tool_name: str            # e.g., "mcpproxy_control__unquarantine"
    tool_input: Dict[str, Any]
    tool_id: str              # Unique identifier
```

### 5. ControlToolResult (Log Entry)

Entry in detailed_log.json for control server results:

```python
@dataclass
class ControlToolResult:
    """Log entry for control MCP server result."""
    timestamp: str            # ISO 8601
    type: str                 # "CONTROL_TOOL_RESULT"
    tool_use_id: str          # Links to ControlToolCall
    success: bool
    response: Any             # Full response data
    error: Optional[str] = None
```

### 6. CompactSummary

Token-efficient report format:

```python
@dataclass
class CompactSummary:
    """Compact summary for AI agent consumption."""
    scenario_name: str
    status: str               # "PASSED", "FAILED", "ERROR"
    similarity_score: float   # 0.0 - 1.0
    agent_tools: List[ToolSummary]   # [AGENT] prefixed
    control_tools: List[ToolSummary] # [CTRL] prefixed
    errors: List[str]

@dataclass
class ToolSummary:
    """Minimal tool call summary."""
    name: str                 # Tool name without full prefix
    status: str               # "OK", "ERROR", "TIMEOUT"
```

## Relationships

```
EnhancedScenario
    └── user_control_actions: List[UserControlAction]

DialogSession
    └── turns: List[DialogTurn]
           ├── TurnType.TOOL_CALL (Agent)
           ├── TurnType.TOOL_RESULT (Agent)
           ├── TurnType.CONTROL_TOOL_CALL (User Role) [NEW]
           └── TurnType.CONTROL_TOOL_RESULT (User Role) [NEW]

detailed_log.json
    └── messages: List[LogEntry]
           ├── type: "TOOL_CALL"
           ├── type: "TOOL_RESULT"
           ├── type: "CONTROL_TOOL_CALL" [NEW]
           └── type: "CONTROL_TOOL_RESULT" [NEW]
```

## Validation Rules

### UserControlAction
- `trigger` must be one of: "after_tool_N", "after_quarantine", "on_error", "before_completion", "manual"
- `tool` must start with "mcpproxy_control__"
- `args` must match tool schema from control MCP server

### EnhancedScenario
- If `user_control_actions` is empty, scenario behaves identically to existing format
- `expected_trajectory` continues to only contain agent MCP tools (mcp__mcpproxy__*)
- `user_control_actions` must only reference control MCP tools (mcpproxy_control__*)

### CompactSummary
- Total output must be under 500 tokens
- Tool names truncated to 40 characters
- Error messages truncated to 100 characters

## State Transitions

### Scenario Execution Flow

```
[Start]
    ↓
User Agent issues intent
    ↓
AI Agent processes → TOOL_CALL → TOOL_RESULT
    ↓
Check triggers → if match → CONTROL_TOOL_CALL → CONTROL_TOOL_RESULT
    ↓
Continue or Complete
    ↓
Generate reports (HTML, JSON, compact summary)
    ↓
[End]
```

### Server Quarantine Flow (Example)

```
[Server Added]
    ↓
MCPProxy auto-quarantines (security check)
    ↓
trigger: "after_quarantine" fires
    ↓
User Role calls mcpproxy_control__unquarantine
    ↓
Server becomes active
    ↓
Agent can now use server's tools
```

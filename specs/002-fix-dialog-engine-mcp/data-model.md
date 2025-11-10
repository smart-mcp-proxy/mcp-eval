# Data Model: Dialog Engine Constitution Compliance

**Feature**: Dialog Engine Constitution Compliance & MCP Integration Fix
**Branch**: 002-fix-dialog-engine-mcp
**Date**: 2025-11-10

## Overview

This document defines the data models required to implement constitution-compliant dual-agent architecture and structured dialog logging for the MCP evaluation system.

---

## New Entities

### DialogTurn

**Purpose**: Represents a single turn in the dialog conversation with complete structured metadata per Constitution Principle III.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| turn_id | int | Yes | Sequential identifier within dialog session (1-indexed) |
| timestamp | datetime | Yes | ISO-8601 format with microsecond precision (e.g., "2025-11-10T14:30:52.123456") |
| turn_type | TurnType (enum) | Yes | Type of dialog turn: USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE |
| actor | Actor (enum) | Yes | Entity that generated this turn: User, AI_Agent, System |
| content | str | Yes | Full message text, tool invocation details, or result payload |
| metadata | dict[str, Any] | Yes | Turn-specific metadata (tool names, IDs, arguments, error flags, git hashes) |

**Enumerations**:

```python
class TurnType(str, Enum):
    USER_MESSAGE = "USER_MESSAGE"
    AGENT_MESSAGE = "AGENT_MESSAGE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"

class Actor(str, Enum):
    USER = "User"
    AI_AGENT = "AI_Agent"
    SYSTEM = "System"
```

**Metadata Structure by Turn Type**:

**USER_MESSAGE**:
```json
{
  "scenario_intent": "original user intent from YAML",
  "is_clarification_response": false
}
```

**AGENT_MESSAGE**:
```json
{
  "message_index": 0,
  "thinking_visible": false
}
```

**TOOL_CALL**:
```json
{
  "tool_name": "mcp__mcpproxy__upstream_servers",
  "tool_id": "toolu_abc123def456",
  "tool_input": {"query": "GitHub"},
  "is_mcp_tool": true
}
```

**TOOL_RESULT**:
```json
{
  "tool_use_id": "toolu_abc123def456",
  "is_error": false,
  "result_size_bytes": 4521,
  "execution_time_ms": 234
}
```

**CLARIFICATION_REQUEST**:
```json
{
  "clarification_question": "Which GitHub organization?",
  "options": ["anthropics", "modelcontextprotocol", "other"]
}
```

**CLARIFICATION_RESPONSE**:
```json
{
  "question_id": "clarif_001",
  "selected_option": "anthropics"
}
```

**Relationships**:
- Part of DialogSession (one session contains many turns)
- TOOL_RESULT turns reference TOOL_CALL turns via tool_use_id
- CLARIFICATION_RESPONSE turns reference CLARIFICATION_REQUEST turns via question_id

**Validation Rules**:
1. timestamp must be ISO-8601 with microsecond precision
2. turn_type and actor must be valid enum values
3. turn_id must be sequential (1, 2, 3, ...)
4. TOOL_RESULT must have matching TOOL_CALL with same tool_use_id
5. metadata structure must match turn_type requirements

**JSON Serialization Example**:
```json
{
  "turn_id": 3,
  "timestamp": "2025-11-10T14:30:52.123456",
  "turn_type": "TOOL_CALL",
  "actor": "AI_Agent",
  "content": "Calling mcp__mcpproxy__upstream_servers to list servers",
  "metadata": {
    "tool_name": "mcp__mcpproxy__upstream_servers",
    "tool_id": "toolu_abc123def456",
    "tool_input": {},
    "is_mcp_tool": true
  }
}
```

---

### UserAgent

**Purpose**: Roleplays human user in dual-agent architecture per Constitution Principle I. Issues scenario intents, responds to clarification requests, and evaluates goal achievement.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| scenario | ScenarioConfig | Yes | Loaded YAML scenario configuration |
| current_turn | int | Yes | Current turn number in dialog (0-indexed) |
| clarification_responses | list[dict] | No | Predefined responses to clarification requests from scenario YAML |
| conversation_history | list[DialogTurn] | Yes | Full dialog history for context |
| max_turns | int | Yes | Maximum allowed turns before timeout (default: 50) |

**Responsibilities**:
- Issues user intents from scenario.user_intent field
- Responds to CLARIFICATION_REQUEST turns from AI Agent
- Evaluates whether AI Agent achieved scenario success_criteria
- Does NOT directly invoke MCP tools (human-only behavior)

**Methods**:

```python
def issue_intent() -> DialogTurn:
    """Create USER_MESSAGE turn with scenario intent."""

def handle_clarification_request(request: DialogTurn) -> DialogTurn:
    """Respond to CLARIFICATION_REQUEST with predefined or default answer."""

def evaluate_result(final_turns: list[DialogTurn]) -> bool:
    """Check if success_criteria met based on dialog history."""

def get_next_action() -> Optional[DialogTurn]:
    """Determine next user action (intent, clarification, or done)."""
```

**State Transitions**:
1. INITIAL → issue_intent() → WAITING_FOR_AGENT
2. WAITING_FOR_AGENT → (receive AGENT_MESSAGE or TOOL_CALL) → PROCESSING
3. PROCESSING → (receive CLARIFICATION_REQUEST) → CLARIFICATION_NEEDED
4. CLARIFICATION_NEEDED → handle_clarification_request() → WAITING_FOR_AGENT
5. WAITING_FOR_AGENT → (max_turns exceeded) → TIMEOUT
6. WAITING_FOR_AGENT → evaluate_result() → SUCCESS or FAILURE

**Example Usage**:
```python
user_agent = UserAgent(
    scenario=scenario_config,
    current_turn=0,
    clarification_responses=[],
    conversation_history=[],
    max_turns=50
)

# Issue initial intent
initial_turn = user_agent.issue_intent()
# → DialogTurn(turn_type=USER_MESSAGE, actor=User, content="List all MCP servers")

# Handle clarification
if next_turn.turn_type == TurnType.CLARIFICATION_REQUEST:
    response_turn = user_agent.handle_clarification_request(next_turn)
    # → DialogTurn(turn_type=CLARIFICATION_RESPONSE, actor=User)
```

---

### AIAgent

**Purpose**: Roleplays AI assistant (like Claude Code, Cursor.ai) in dual-agent architecture per Constitution Principle I. Executes user requests by selecting and invoking MCP tools, asks clarifications when needed.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| claude_client | ClaudeSDKClient | Yes | Underlying Claude SDK client with MCP access |
| mcp_config | str | Yes | Path to mcp_servers.json configuration file |
| temperature | float | Yes | LLM temperature (MUST be 0.0 per Principle V) |
| system_prompt | str | Yes | System prompt defining agent behavior |
| conversation_history | list[DialogTurn] | Yes | Full dialog history for context |
| tools_discovered | bool | No | Whether initial MCP tool discovery completed |

**Responsibilities**:
- Has access to MCP servers under test (via mcp_config)
- Executes user requests by selecting and invoking appropriate MCP tools
- MAY ask User agent for clarification when scenario is underspecified
- MUST NOT know it's in a test scenario (authentic assistant behavior)

**Methods**:

```python
async def process_intent(user_turn: DialogTurn) -> list[DialogTurn]:
    """Process user intent and generate response turns (messages + tool calls)."""

async def invoke_tool(tool_name: str, tool_input: dict) -> DialogTurn:
    """Invoke MCP tool and return TOOL_RESULT turn."""

async def request_clarification(question: str, options: list[str]) -> DialogTurn:
    """Ask User agent for clarification (creates CLARIFICATION_REQUEST turn)."""

def get_available_tools() -> list[dict]:
    """Retrieve list of available MCP tools from servers."""
```

**Configuration**:

```python
ai_agent = AIAgent(
    claude_client=ClaudeSDKClient(
        options=ClaudeAgentOptions(
            system_prompt="You are a helpful agent that can use MCP tools",
            max_turns=100,
            mcp_servers="mcp_servers.json",
            permission_mode="bypassPermissions",
            model="claude-sonnet-4-5-20250929",
            settings="claude_settings.json"  # Contains {"temperature": 0.0}
        )
    ),
    mcp_config="mcp_servers.json",
    temperature=0.0,
    system_prompt="...",
    conversation_history=[],
    tools_discovered=False
)
```

**State Management**:
- Wraps ClaudeSDKClient to track DialogTurn objects
- Converts SDK Message objects to DialogTurn format
- Maintains conversation history for trajectory comparison
- Filters MCP tools (mcp__*) vs framework tools (TodoWrite, Bash)

**Example Usage**:
```python
# Process user intent
user_turn = DialogTurn(
    turn_id=1,
    turn_type=TurnType.USER_MESSAGE,
    actor=Actor.USER,
    content="List all MCP servers"
)

response_turns = await ai_agent.process_intent(user_turn)
# → [
#   DialogTurn(turn_type=AGENT_MESSAGE, content="I'll list the servers"),
#   DialogTurn(turn_type=TOOL_CALL, metadata={"tool_name": "mcp__mcpproxy__upstream_servers"}),
#   DialogTurn(turn_type=TOOL_RESULT, metadata={"is_error": false, "result_size_bytes": 1234})
# ]
```

---

### DialogSession

**Purpose**: Orchestrates interaction between UserAgent and AIAgent for a single scenario execution.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | str | Yes | Unique identifier (scenario name + timestamp) |
| scenario | ScenarioConfig | Yes | YAML scenario configuration |
| user_agent | UserAgent | Yes | User roleplay agent |
| ai_agent | AIAgent | Yes | AI assistant agent with MCP access |
| turns | list[DialogTurn] | Yes | Complete ordered dialog history |
| start_time | datetime | Yes | Session start timestamp |
| end_time | Optional[datetime] | No | Session end timestamp |
| status | SessionStatus (enum) | Yes | SUCCESS, FAILURE, TIMEOUT, ERROR |
| mcpproxy_git_hash | str | Yes | MCPProxy version for baseline tracking |

**Session Status Enum**:
```python
class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
```

**Methods**:
```python
async def execute() -> ScenarioResult:
    """Run dialog session until completion or timeout."""

def add_turn(turn: DialogTurn) -> None:
    """Append turn to history and update both agents."""

def export_to_json() -> dict:
    """Export session as structured log JSON."""
```

---

## Updated Entities

### ToolCallRecord (DEPRECATED)

**Status**: Replaced by DialogTurn with turn_type=TOOL_CALL

**Migration Path**:
```python
# Old ToolCallRecord
tool_record = ToolCallRecord(
    tool_name="mcp__mcpproxy__upstream_servers",
    tool_id="toolu_123",
    tool_input={},
    timestamp=datetime.now()
)

# New DialogTurn equivalent
tool_turn = DialogTurn(
    turn_id=5,
    timestamp=datetime.now(),
    turn_type=TurnType.TOOL_CALL,
    actor=Actor.AI_AGENT,
    content="Calling mcp__mcpproxy__upstream_servers",
    metadata={
        "tool_name": "mcp__mcpproxy__upstream_servers",
        "tool_id": "toolu_123",
        "tool_input": {},
        "is_mcp_tool": True
    }
)
```

### ScenarioResult

**New Field Added**: `dialog_turns: list[DialogTurn]`

**Updated Structure**:
```python
@dataclass
class ScenarioResult:
    scenario_name: str
    success: bool
    execution_time: float
    detailed_log: dict[str, Any]  # Contains {"turns": [DialogTurn.to_dict(), ...]}
    dialog_trajectory: str  # Human-readable text representation
    tool_calls: list[ToolCallRecord]  # DEPRECATED - kept for backward compatibility
    dialog_turns: list[DialogTurn]  # NEW - constitution-compliant structured log
    error: Optional[str] = None
    session_status: SessionStatus = SessionStatus.SUCCESS
    mcpproxy_git_hash: str = "unknown"
```

---

## Existing Entities (No Changes)

### ScenarioConfig

**Source**: Loaded from YAML scenario files

**Structure**:
```python
@dataclass
class ScenarioConfig:
    name: str
    description: str
    user_intent: str
    expected_trajectory: list[dict]
    success_criteria: list[str]
    tags: list[str]
    enabled: bool = True
    config_file: Optional[str] = None
```

**No changes required** - existing YAML schema supports dual-agent architecture.

### ConversationInterceptor

**Source**: Imported from main.py

**Purpose**: Context manager for ClaudeSDKClient conversations

**No changes required** - existing interceptor works with AIAgent wrapper.

---

## Data Flow Diagram

```
ScenarioConfig (YAML)
    ↓
DialogSession.execute()
    ↓
UserAgent.issue_intent() → DialogTurn (USER_MESSAGE)
    ↓
AIAgent.process_intent(user_turn) → list[DialogTurn] (AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT)
    ↓
UserAgent.evaluate_result(turns) → bool (success/failure)
    ↓
ScenarioResult (with dialog_turns: list[DialogTurn])
    ↓
detailed_log.json (structured JSON per Principle III)
    ↓
Evaluator (trajectory comparison, MCP-only filtering)
    ↓
HTML Report (visual diff, similarity scores)
```

---

## JSON Schema Examples

### Complete Scenario Execution Log

```json
{
  "session_id": "list_all_servers_20251110_143052",
  "scenario_name": "list_all_servers",
  "execution_time": 5.234,
  "start_time": "2025-11-10T14:30:52.000000",
  "end_time": "2025-11-10T14:30:57.234000",
  "status": "SUCCESS",
  "mcpproxy_git_hash": "a1b2c3d4",
  "turns": [
    {
      "turn_id": 1,
      "timestamp": "2025-11-10T14:30:52.123456",
      "turn_type": "USER_MESSAGE",
      "actor": "User",
      "content": "List all available MCP servers",
      "metadata": {
        "scenario_intent": "List all available MCP servers",
        "is_clarification_response": false
      }
    },
    {
      "turn_id": 2,
      "timestamp": "2025-11-10T14:30:53.456789",
      "turn_type": "AGENT_MESSAGE",
      "actor": "AI_Agent",
      "content": "I'll list all MCP servers using the upstream_servers tool.",
      "metadata": {
        "message_index": 0,
        "thinking_visible": false
      }
    },
    {
      "turn_id": 3,
      "timestamp": "2025-11-10T14:30:54.789012",
      "turn_type": "TOOL_CALL",
      "actor": "AI_Agent",
      "content": "Calling mcp__mcpproxy__upstream_servers({})",
      "metadata": {
        "tool_name": "mcp__mcpproxy__upstream_servers",
        "tool_id": "toolu_abc123def456",
        "tool_input": {},
        "is_mcp_tool": true
      }
    },
    {
      "turn_id": 4,
      "timestamp": "2025-11-10T14:30:56.012345",
      "turn_type": "TOOL_RESULT",
      "actor": "System",
      "content": "{\"servers\": [{\"name\": \"github\", \"status\": \"active\"}]}",
      "metadata": {
        "tool_use_id": "toolu_abc123def456",
        "is_error": false,
        "result_size_bytes": 1234,
        "execution_time_ms": 1223
      }
    },
    {
      "turn_id": 5,
      "timestamp": "2025-11-10T14:30:57.234567",
      "turn_type": "AGENT_MESSAGE",
      "actor": "AI_Agent",
      "content": "There is 1 active MCP server: github",
      "metadata": {
        "message_index": 1,
        "thinking_visible": false
      }
    }
  ]
}
```

---

## Migration Strategy

**Phase 1**: Implement new entities alongside existing code
- Create DialogTurn, UserAgent, AIAgent, DialogSession classes
- Keep ToolCallRecord for backward compatibility

**Phase 2**: Update scenario_runner.py to use DialogSession
- Instantiate UserAgent and AIAgent
- Run dual-agent dialog loop
- Export DialogTurn list to detailed_log.json

**Phase 3**: Update evaluator.py to use DialogTurn
- Filter turns by turn_type=TOOL_CALL and metadata.is_mcp_tool=true
- Extract tool_name and tool_input from DialogTurn.metadata
- Compare DialogTurn sequences instead of ToolCallRecord sequences

**Phase 4**: Update html_reporter.py to render DialogTurn
- Display full conversation with all turn types
- Highlight MCP tool calls vs framework tools
- Show actor labels (User vs AI_Agent vs System)

**Phase 5**: Deprecate ToolCallRecord
- Remove ToolCallRecord from new code paths
- Keep for backward compatibility with old baselines
- Document migration in CHANGELOG

---

## Constitution Compliance Mapping

| Principle | Entity | Field/Method | Compliance |
|-----------|--------|--------------|------------|
| I. Dual-Agent Architecture | UserAgent, AIAgent | Separate classes with distinct responsibilities | ✅ |
| I. Dual-Agent Architecture | DialogSession | Orchestrates user-agent interaction | ✅ |
| III. Structured Logging | DialogTurn | All required fields (timestamp, turn_type, actor, content, metadata) | ✅ |
| III. Structured Logging | DialogTurn.timestamp | ISO-8601 with microsecond precision | ✅ |
| III. Structured Logging | TurnType enum | USER_MESSAGE, AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT, CLARIFICATION_REQUEST, CLARIFICATION_RESPONSE | ✅ |
| III. Structured Logging | Actor enum | User, AI_Agent, System | ✅ |
| III. Structured Logging | DialogTurn.metadata | Tool names, IDs, arguments, error flags, git hashes | ✅ |
| V. Deterministic Evaluation | AIAgent.temperature | Must be 0.0 | ✅ |
| V. Deterministic Evaluation | AIAgent configuration | Enforced via ClaudeAgentOptions.settings | ✅ |

---

## Notes

- All timestamps use ISO-8601 format with microsecond precision for trajectory sorting
- DialogTurn is the single source of truth for all conversation events
- UserAgent does NOT have MCP access - only AIAgent can invoke tools
- Metadata structure varies by turn_type but all contain required tracking fields
- JSON serialization preserves all metadata for trajectory comparison
- Backward compatibility maintained via deprecated ToolCallRecord in ScenarioResult

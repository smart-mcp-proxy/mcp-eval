"""Dialog models for constitution-compliant structured logging.

Implements Principle III: Structured Dialog Logging for Trajectory Scoring
with complete metadata schema including turn types, actors, and timestamps.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class TurnType(str, Enum):
    """Dialog turn types per Constitution Principle III."""
    USER_MESSAGE = "USER_MESSAGE"
    AGENT_MESSAGE = "AGENT_MESSAGE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"
    # Control server turn types (User Role invokes control MCP tools)
    CONTROL_TOOL_CALL = "CONTROL_TOOL_CALL"
    CONTROL_TOOL_RESULT = "CONTROL_TOOL_RESULT"


class Actor(str, Enum):
    """Entity that generated the dialog turn."""
    USER = "User"
    AI_AGENT = "AI_Agent"
    SYSTEM = "System"


class SessionStatus(str, Enum):
    """Dialog session execution status."""
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class DialogTurn:
    """Represents a single turn in the dialog conversation.

    Implements Constitution Principle III requirements:
    - Timestamp: ISO-8601 format with microsecond precision
    - Turn Type: Enum specifying dialog turn category
    - Actor: Entity that generated the turn
    - Content: Full message text or tool invocation details
    - Metadata: Turn-specific metadata (tool names, IDs, arguments, error flags)
    """
    turn_id: int
    timestamp: datetime
    turn_type: TurnType
    actor: Actor
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DialogTurn to JSON-compatible dictionary.

        Returns:
            Dictionary with all fields, timestamp in ISO-8601 format,
            enums as string values for JSON serialization.
        """
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "turn_type": self.turn_type.value if isinstance(self.turn_type, TurnType) else self.turn_type,
            "actor": self.actor.value if isinstance(self.actor, Actor) else self.actor,
            "content": self.content,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogTurn':
        """Deserialize DialogTurn from dictionary.

        Args:
            data: Dictionary with turn_id, timestamp, turn_type, actor, content, metadata

        Returns:
            DialogTurn instance with parsed enums and datetime
        """
        # Parse timestamp from ISO-8601 string
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Parse enums from string values
        turn_type = data["turn_type"]
        if isinstance(turn_type, str):
            turn_type = TurnType(turn_type)

        actor = data["actor"]
        if isinstance(actor, str):
            actor = Actor(actor)

        return cls(
            turn_id=data["turn_id"],
            timestamp=timestamp,
            turn_type=turn_type,
            actor=actor,
            content=data["content"],
            metadata=data.get("metadata", {})
        )


# Valid trigger types for UserControlAction
VALID_TRIGGERS = frozenset([
    "after_tool_N",      # After Nth agent tool call (e.g., "after_tool_1", "after_tool_2")
    "after_quarantine",  # When server enters quarantine state
    "on_error",          # When agent tool call fails
    "before_completion", # Before final evaluation
    "manual",            # Triggered by explicit instruction in user_intent
])


@dataclass
class UserControlAction:
    """A control action executed by User Role during scenario.

    User control actions allow the simulated "user" to control mcpproxy
    state (e.g., unquarantine servers, read config) during scenario execution.

    Attributes:
        trigger: When to execute - one of: "after_tool_N", "after_quarantine",
                 "on_error", "before_completion", "manual"
        action: Action name for trajectory matching
        tool: MCP tool name (auto-generated from OpenAPI, e.g., "api_v1_servers_id_unquarantine")
        args: Tool arguments
        expected_result: Optional expected outcome for validation
    """
    trigger: str
    action: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate trigger type."""
        # Handle after_tool_N pattern
        trigger_base = self.trigger.rsplit("_", 1)[0] if self.trigger.startswith("after_tool_") else self.trigger
        if trigger_base not in VALID_TRIGGERS and not self.trigger.startswith("after_tool_"):
            valid = ", ".join(sorted(VALID_TRIGGERS))
            raise ValueError(f"Invalid trigger '{self.trigger}'. Must be one of: {valid} (or after_tool_N pattern)")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        result = {
            "trigger": self.trigger,
            "action": self.action,
            "tool": self.tool,
            "args": self.args,
        }
        if self.expected_result is not None:
            result["expected_result"] = self.expected_result
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserControlAction':
        """Deserialize from dictionary."""
        return cls(
            trigger=data["trigger"],
            action=data["action"],
            tool=data["tool"],
            args=data.get("args", {}),
            expected_result=data.get("expected_result"),
        )


@dataclass
class ControlToolCall:
    """Log entry for control MCP server call in detailed_log.json.

    Represents a call to the control MCP server from User Role.
    Distinguished from agent TOOL_CALL by type="CONTROL_TOOL_CALL".
    """
    timestamp: str  # ISO 8601
    type: str = "CONTROL_TOOL_CALL"
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_id": self.tool_id,
        }


@dataclass
class ControlToolResult:
    """Log entry for control MCP server result in detailed_log.json.

    Represents a result from the control MCP server.
    Distinguished from agent TOOL_RESULT by type="CONTROL_TOOL_RESULT".
    """
    timestamp: str  # ISO 8601
    type: str = "CONTROL_TOOL_RESULT"
    tool_use_id: str = ""  # Links to ControlToolCall
    success: bool = True
    response: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        result = {
            "timestamp": self.timestamp,
            "type": self.type,
            "tool_use_id": self.tool_use_id,
            "success": self.success,
            "response": self.response,
        }
        if self.error is not None:
            result["error"] = self.error
        return result


# Valid control MCP tool name prefixes/patterns (FR-012)
VALID_CONTROL_TOOL_PREFIXES = frozenset([
    "api_v1_config",
    "api_v1_servers",
    "api_v1_status",
    "healthz",
])


def is_valid_control_tool(tool_name: str) -> bool:
    """Check if tool name is a valid control MCP tool (FR-012).

    Args:
        tool_name: The tool name to validate

    Returns:
        True if valid control tool, False otherwise
    """
    # Check exact matches
    if tool_name in VALID_CONTROL_TOOL_PREFIXES:
        return True

    # Check prefix matches (api_v1_servers_id_unquarantine, etc.)
    for prefix in VALID_CONTROL_TOOL_PREFIXES:
        if tool_name.startswith(prefix):
            return True

    return False


def parse_user_control_actions(
    scenario_data: Dict[str, Any],
    validate_tools: bool = True
) -> List[UserControlAction]:
    """Parse user_control_actions from scenario YAML data.

    This function extracts and validates user control actions from
    scenario data, providing backward compatibility for scenarios
    without control actions.

    Args:
        scenario_data: Scenario dictionary from YAML load
        validate_tools: Whether to validate tool names (FR-012)

    Returns:
        List of UserControlAction instances (empty if not specified)

    Raises:
        ValueError: If any control action is invalid or references invalid tool
    """
    raw_actions = scenario_data.get("user_control_actions", [])
    if not raw_actions:
        return []

    actions = []
    for i, action_data in enumerate(raw_actions):
        try:
            action = UserControlAction.from_dict(action_data)

            # Validate tool name references valid control MCP tool (FR-012)
            if validate_tools and not is_valid_control_tool(action.tool):
                raise ValueError(
                    f"Tool '{action.tool}' is not a valid control MCP tool. "
                    f"Valid prefixes: {', '.join(sorted(VALID_CONTROL_TOOL_PREFIXES))}"
                )

            actions.append(action)
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"Invalid user_control_action at index {i}: {e}"
            ) from e

    return actions

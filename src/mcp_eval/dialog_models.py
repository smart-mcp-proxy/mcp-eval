"""Dialog models for constitution-compliant structured logging.

Implements Principle III: Structured Dialog Logging for Trajectory Scoring
with complete metadata schema including turn types, actors, and timestamps.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class TurnType(str, Enum):
    """Dialog turn types per Constitution Principle III."""
    USER_MESSAGE = "USER_MESSAGE"
    AGENT_MESSAGE = "AGENT_MESSAGE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"


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

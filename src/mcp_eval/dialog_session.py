"""Dialog session orchestrator for dual-agent architecture.

Implements Constitution Principle I: Dual-Agent Dialog Engine Architecture
with orchestration of User Agent and AI Agent interaction.
"""

import asyncio
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .dialog_models import DialogTurn, TurnType, Actor, SessionStatus
from .agents import UserAgent, AIAgent


@dataclass
class DialogSession:
    """Orchestrates interaction between UserAgent and AIAgent for scenario execution.

    Implements the dialog loop:
    1. UserAgent issues intent
    2. AIAgent processes intent and invokes MCP tools
    3. Loop continues until max turns or completion
    4. UserAgent evaluates final result
    """
    session_id: str
    scenario: Dict[str, Any]
    user_agent: UserAgent
    ai_agent: AIAgent
    turns: List[DialogTurn] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.RUNNING
    mcpproxy_git_hash: str = "unknown"

    def __post_init__(self):
        """Initialize session with git hash capture."""
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.mcpproxy_git_hash == "unknown":
            self.mcpproxy_git_hash = self._get_mcpproxy_git_hash()

    def _get_mcpproxy_git_hash(self) -> str:
        """Capture MCPProxy git hash for baseline tracking."""
        import os
        mcpproxy_source = os.getenv("MCPPROXY_SOURCE_PATH", "../mcpproxy-go")
        mcpproxy_path = Path(mcpproxy_source).expanduser().resolve()

        if not mcpproxy_path.exists():
            return "unknown"

        try:
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=mcpproxy_path,
                text=True
            ).strip()[:8]  # Short hash
            return git_hash
        except subprocess.CalledProcessError:
            return "unknown"

    async def execute(self) -> Dict[str, Any]:
        """Run dialog session until completion or timeout.

        Returns:
            Dictionary with session_id, turns, status, execution_time
        """
        self.status = SessionStatus.RUNNING

        try:
            # Step 1: User issues intent
            user_turn = self.user_agent.issue_intent()
            self.add_turn(user_turn)

            # Step 2: AI processes intent and generates response
            ai_turns = await self.ai_agent.process_intent(user_turn, len(self.turns))
            for turn in ai_turns:
                self.add_turn(turn)

            # Step 3: Check if max turns exceeded
            if len(self.turns) >= self.user_agent.max_turns:
                self.status = SessionStatus.TIMEOUT
            else:
                # Step 4: User evaluates result
                success = self.user_agent.evaluate_result(self.turns)
                self.status = SessionStatus.SUCCESS if success else SessionStatus.FAILURE

        except Exception as e:
            self.status = SessionStatus.ERROR
            # Add error turn for visibility
            error_turn = DialogTurn(
                turn_id=len(self.turns) + 1,
                timestamp=datetime.now(),
                turn_type=TurnType.AGENT_MESSAGE,
                actor=Actor.SYSTEM,
                content=f"Error: {str(e)}",
                metadata={"error": str(e), "error_type": type(e).__name__}
            )
            self.add_turn(error_turn)

        finally:
            self.end_time = datetime.now()

        return {
            "session_id": self.session_id,
            "scenario_name": self.scenario.get("name", "unknown"),
            "turns": [turn.to_dict() for turn in self.turns],
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "mcpproxy_git_hash": self.mcpproxy_git_hash
        }

    def add_turn(self, turn: DialogTurn) -> None:
        """Append turn to history and update both agents.

        Args:
            turn: DialogTurn to add to session
        """
        self.turns.append(turn)
        # Update agent conversation histories
        if turn not in self.user_agent.conversation_history:
            self.user_agent.conversation_history.append(turn)
        if turn not in self.ai_agent.conversation_history:
            self.ai_agent.conversation_history.append(turn)

    def export_to_json(self) -> Dict[str, Any]:
        """Export session as structured log JSON per Constitution Principle III.

        Returns:
            Dictionary with complete session data in constitution-compliant format
        """
        return {
            "session_id": self.session_id,
            "scenario": {
                "name": self.scenario.get("name", "unknown"),
                "description": self.scenario.get("description", ""),
                "user_intent": self.scenario.get("user_intent", "")
            },
            "execution_time": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "mcpproxy_git_hash": self.mcpproxy_git_hash,
            "turns": [turn.to_dict() for turn in self.turns]
        }

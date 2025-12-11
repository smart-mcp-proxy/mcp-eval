"""Dialog session orchestrator for dual-agent architecture.

Implements Constitution Principle I: Dual-Agent Dialog Engine Architecture
with orchestration of User Agent and AI Agent interaction.

FR-008: Session records control tool calls with distinct types
FR-021: Control server calls logged for reporting
"""

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

from .dialog_models import (
    DialogTurn, TurnType, Actor, SessionStatus,
    UserControlAction, ControlToolCall, ControlToolResult,
)
from .agents import UserAgent, AIAgent


@dataclass
class DialogSession:
    """Orchestrates interaction between UserAgent and AIAgent for scenario execution.

    Implements the dialog loop:
    1. UserAgent issues intent
    2. AIAgent processes intent and invokes MCP tools
    3. Check triggers and execute control actions (FR-008)
    4. Loop continues until max turns or completion
    5. UserAgent evaluates final result

    Control Server Integration (FR-008, FR-021):
    - Control actions defined in scenario's user_control_actions field
    - Executed via REST API calls to mcpproxy (not via MCP)
    - Recorded as CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT turns
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
    # Control server configuration
    control_server_base_url: str = ""
    control_server_api_key: str = ""
    _http_client: Optional[httpx.AsyncClient] = None

    def __post_init__(self):
        """Initialize session with git hash capture and control server config."""
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.mcpproxy_git_hash == "unknown":
            self.mcpproxy_git_hash = self._get_mcpproxy_git_hash()
        # Initialize control server config from environment
        if not self.control_server_base_url:
            self.control_server_base_url = os.getenv("MCPPROXY_BASE_URL", "http://localhost:8081")
        if not self.control_server_api_key:
            self.control_server_api_key = os.getenv("MCPPROXY_API_KEY", "")

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

        Implements control action integration (FR-008, FR-014):
        - After each agent tool result, check for triggered control actions
        - Execute control actions via REST API
        - Record control actions as CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT turns

        Returns:
            Dictionary with session_id, turns, status, execution_time, control_calls
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

                # Track agent tool calls for after_tool_N triggers
                if turn.turn_type == TurnType.TOOL_CALL:
                    self.user_agent.increment_tool_count()

                # Step 3: Check for triggered control actions after each tool result
                if turn.turn_type == TurnType.TOOL_RESULT:
                    event_data = {
                        "content": turn.content,
                        "is_error": turn.metadata.get("is_error", False),
                    }
                    triggered = self.user_agent.check_triggers("tool_result", event_data)
                    for action in triggered:
                        await self._execute_control_action(action)

            # Check before_completion triggers
            completion_actions = self.user_agent.check_triggers("completion")
            for action in completion_actions:
                await self._execute_control_action(action)

            # Step 4: Check if max turns exceeded
            if len(self.turns) >= self.user_agent.max_turns:
                self.status = SessionStatus.TIMEOUT
            else:
                # Step 5: User evaluates result
                success = self.user_agent.evaluate_result(self.turns)
                self.status = SessionStatus.SUCCESS if success else SessionStatus.FAILURE

        except Exception as e:
            self.status = SessionStatus.ERROR
            # Check on_error triggers
            error_actions = self.user_agent.check_triggers("error", {"error": str(e)})
            for action in error_actions:
                try:
                    await self._execute_control_action(action)
                except Exception:
                    pass  # Don't let control action errors mask original error

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
            # Close HTTP client if open
            if self._http_client is not None:
                await self._http_client.aclose()
                self._http_client = None

        return {
            "session_id": self.session_id,
            "scenario_name": self.scenario.get("name", "unknown"),
            "turns": [turn.to_dict() for turn in self.turns],
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "mcpproxy_git_hash": self.mcpproxy_git_hash,
            # Include control action logs (FR-021)
            "control_tool_calls": [c.to_dict() for c in self.user_agent.control_tool_calls],
            "control_tool_results": [r.to_dict() for r in self.user_agent.control_tool_results],
        }

    async def _execute_control_action(self, action: UserControlAction) -> None:
        """Execute a control action via REST API and record the results.

        Args:
            action: The control action to execute

        FR-008: Records CONTROL_TOOL_CALL/CONTROL_TOOL_RESULT turns
        FR-021: Logs control server calls for reporting
        """
        # Record the control call
        tool_call = self.user_agent.record_control_call(action)

        # Add CONTROL_TOOL_CALL turn
        call_turn = DialogTurn(
            turn_id=len(self.turns) + 1,
            timestamp=datetime.now(),
            turn_type=TurnType.CONTROL_TOOL_CALL,
            actor=Actor.USER,
            content=f"[CTRL] {action.tool}({action.args})",
            metadata={
                "tool_name": action.tool,
                "tool_id": tool_call.tool_id,
                "tool_input": action.args,
                "trigger": action.trigger,
                "action_name": action.action,
            }
        )
        self.add_turn(call_turn)

        # Execute the REST API call
        try:
            response_data = await self._call_control_api(action)
            success = True
            error = None
        except Exception as e:
            response_data = {"error": str(e)}
            success = False
            error = str(e)

        # Record the result
        tool_result = self.user_agent.record_control_result(
            tool_call, success, response_data, error
        )

        # Add CONTROL_TOOL_RESULT turn
        result_turn = DialogTurn(
            turn_id=len(self.turns) + 1,
            timestamp=datetime.now(),
            turn_type=TurnType.CONTROL_TOOL_RESULT,
            actor=Actor.SYSTEM,
            content=str(response_data)[:500] if success else f"Error: {error}",
            metadata={
                "tool_use_id": tool_call.tool_id,
                "is_error": not success,
                "success": success,
                "trigger": action.trigger,
            }
        )
        self.add_turn(result_turn)

    async def _call_control_api(self, action: UserControlAction) -> Dict[str, Any]:
        """Call mcpproxy REST API for control action.

        Args:
            action: The control action with tool name and args

        Returns:
            API response data

        The tool name follows pattern: api_v1_path_param
        Maps to endpoint: /api/v1/path/{param}
        """
        # Initialize HTTP client if needed
        if self._http_client is None:
            params = {}
            if self.control_server_api_key:
                params["apikey"] = self.control_server_api_key
            self._http_client = httpx.AsyncClient(
                base_url=self.control_server_base_url,
                timeout=30.0,
                params=params,
            )

        # Convert tool name to API path
        # api_v1_servers_id_unquarantine -> /api/v1/servers/{id}/unquarantine
        tool_parts = action.tool.split("_")
        path_parts = []
        i = 0
        while i < len(tool_parts):
            part = tool_parts[i]
            if part == "id" and i + 1 < len(tool_parts):
                # {id} parameter - get from args
                server_id = action.args.get("id", action.args.get("server_id", ""))
                path_parts.append(server_id)
            else:
                path_parts.append(part)
            i += 1

        endpoint = "/" + "/".join(path_parts)

        # Determine HTTP method based on endpoint
        if any(verb in endpoint for verb in ["/restart", "/quarantine", "/unquarantine", "/enable", "/disable"]):
            method = "POST"
        else:
            method = "GET"

        # Make the request
        if method == "POST":
            # Filter out path params from body
            body = {k: v for k, v in action.args.items() if k not in ("id", "server_id")}
            response = await self._http_client.post(endpoint, json=body if body else None)
        else:
            # Query params for GET
            params = {k: v for k, v in action.args.items() if k not in ("id", "server_id")}
            response = await self._http_client.get(endpoint, params=params if params else None)

        # Parse response - allow non-2xx responses to still return data
        # Some mcpproxy endpoints return 500 but still apply state changes
        result = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            result = response.json()
        else:
            result = {"text": response.text}

        # Add HTTP status info
        result["_http_status"] = response.status_code
        result["_http_ok"] = response.is_success

        # Raise only for real failures (not state-applied-but-persist-failed)
        if response.status_code >= 400 and response.status_code != 500:
            response.raise_for_status()

        return result

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
            Dictionary with complete session data in constitution-compliant format.
            Includes control_tool_calls and control_tool_results (FR-022).
        """
        result = {
            "session_id": self.session_id,
            "scenario": {
                "name": self.scenario.get("name", "unknown"),
                "description": self.scenario.get("description", ""),
                "user_intent": self.scenario.get("user_intent", ""),
                "has_control_actions": len(self.user_agent.control_actions) > 0,
            },
            "execution_time": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "mcpproxy_git_hash": self.mcpproxy_git_hash,
            "turns": [turn.to_dict() for turn in self.turns],
        }

        # Include control action logs if any (FR-022)
        if self.user_agent.control_tool_calls:
            result["control_tool_calls"] = [c.to_dict() for c in self.user_agent.control_tool_calls]
        if self.user_agent.control_tool_results:
            result["control_tool_results"] = [r.to_dict() for r in self.user_agent.control_tool_results]

        return result

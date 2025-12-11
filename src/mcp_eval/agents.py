"""Dual-agent architecture for MCP evaluation system.

Implements Constitution Principle I: Dual-Agent Dialog Engine Architecture
with separate User Agent and AI Agent roles.

FR-006: User Role has access to control MCP server
FR-007: Agent Role does NOT have access to control MCP server
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from .dialog_models import (
    DialogTurn, TurnType, Actor,
    UserControlAction, ControlToolCall, ControlToolResult,
    parse_user_control_actions,
)


@dataclass
class UserAgent:
    """Roleplays human user in dual-agent architecture.

    Responsibilities per Constitution Principle I:
    - Issues requests to trigger MCP tool usage based on scenario intent
    - Responds to clarification questions from the AI agent
    - Does NOT directly invoke MCP tools (human-only behavior)
    - Evaluates whether the AI agent achieved goals and used tools correctly

    FR-006: User Role has access to control MCP server for test environment manipulation.
    Control actions are defined in scenario's user_control_actions field.
    """
    scenario: Dict[str, Any]
    current_turn: int = 0
    clarification_responses: List[Dict[str, str]] = field(default_factory=list)
    conversation_history: List[DialogTurn] = field(default_factory=list)
    max_turns: int = 50
    # Control server support (FR-006)
    control_actions: List[UserControlAction] = field(default_factory=list)
    executed_control_actions: List[str] = field(default_factory=list)  # Track executed triggers
    control_tool_calls: List[ControlToolCall] = field(default_factory=list)
    control_tool_results: List[ControlToolResult] = field(default_factory=list)
    agent_tool_call_count: int = 0  # Track agent tool calls for after_tool_N triggers

    def __post_init__(self):
        """Parse control actions from scenario."""
        if not self.control_actions:
            self.control_actions = parse_user_control_actions(self.scenario)

    def issue_intent(self) -> DialogTurn:
        """Create USER_MESSAGE DialogTurn from scenario.user_intent.

        Returns:
            DialogTurn with turn_type=USER_MESSAGE containing user intent
        """
        self.current_turn += 1
        user_intent = self.scenario.get("user_intent", "")

        turn = DialogTurn(
            turn_id=self.current_turn,
            timestamp=datetime.now(),
            turn_type=TurnType.USER_MESSAGE,
            actor=Actor.USER,
            content=user_intent,
            metadata={
                "scenario_intent": user_intent,
                "is_clarification_response": False
            }
        )
        self.conversation_history.append(turn)
        return turn

    def handle_clarification_request(self, request: DialogTurn) -> DialogTurn:
        """Respond to CLARIFICATION_REQUEST with predefined or default answer.

        Args:
            request: DialogTurn with turn_type=CLARIFICATION_REQUEST

        Returns:
            DialogTurn with turn_type=CLARIFICATION_RESPONSE
        """
        self.current_turn += 1

        # Extract clarification question from metadata
        question = request.metadata.get("clarification_question", "")
        options = request.metadata.get("options", [])

        # For now, use first option as default (future: look up in scenario)
        selected_option = options[0] if options else "proceed"

        turn = DialogTurn(
            turn_id=self.current_turn,
            timestamp=datetime.now(),
            turn_type=TurnType.CLARIFICATION_RESPONSE,
            actor=Actor.USER,
            content=f"Selected: {selected_option}",
            metadata={
                "question_id": request.metadata.get("question_id", f"clarif_{request.turn_id}"),
                "selected_option": selected_option,
                "is_clarification_response": True
            }
        )
        self.conversation_history.append(turn)
        return turn

    def evaluate_result(self, dialog_turns: List[DialogTurn]) -> bool:
        """Check if success_criteria met based on dialog history.

        Args:
            dialog_turns: Complete list of dialog turns from session

        Returns:
            True if success criteria met, False otherwise
        """
        success_criteria = self.scenario.get("success_criteria", [])
        if not success_criteria:
            # No criteria defined, consider success if no errors
            error_turns = [t for t in dialog_turns if t.turn_type == TurnType.TOOL_RESULT and t.metadata.get("is_error")]
            return len(error_turns) == 0

        # Check if all criteria phrases appear in conversation content
        conversation_text = " ".join([turn.content for turn in dialog_turns])

        met_criteria = []
        for criterion in success_criteria:
            # Simple substring match (can be enhanced with more sophisticated matching)
            if criterion.lower() in conversation_text.lower():
                met_criteria.append(criterion)

        # Success if majority of criteria met
        return len(met_criteria) >= len(success_criteria) * 0.5

    def check_triggers(self, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> List[UserControlAction]:
        """Check if any control actions should be triggered.

        Args:
            event_type: Type of event - "tool_call", "tool_result", "quarantine", "error", "completion"
            event_data: Optional event-specific data (tool name, error message, etc.)

        Returns:
            List of control actions that should be executed
        """
        triggered_actions = []

        for action in self.control_actions:
            # Skip already executed actions
            trigger_key = f"{action.trigger}:{action.tool}"
            if trigger_key in self.executed_control_actions:
                continue

            # Check trigger conditions
            should_trigger = False

            if action.trigger.startswith("after_tool_"):
                # after_tool_N trigger
                try:
                    n = int(action.trigger.split("_")[-1])
                    if event_type == "tool_result" and self.agent_tool_call_count >= n:
                        should_trigger = True
                except ValueError:
                    pass

            elif action.trigger == "after_quarantine":
                if event_type == "quarantine":
                    should_trigger = True
                # Also check if tool result indicates quarantine
                if event_type == "tool_result" and event_data:
                    content = str(event_data.get("content", "")).lower()
                    if "quarantine" in content or "quarantined" in content:
                        should_trigger = True

            elif action.trigger == "on_error":
                if event_type == "error":
                    should_trigger = True
                if event_type == "tool_result" and event_data and event_data.get("is_error"):
                    should_trigger = True

            elif action.trigger == "before_completion":
                if event_type == "completion":
                    should_trigger = True

            elif action.trigger == "manual":
                # Manual triggers are handled separately
                pass

            if should_trigger:
                triggered_actions.append(action)
                self.executed_control_actions.append(trigger_key)

        return triggered_actions

    def record_control_call(self, action: UserControlAction) -> ControlToolCall:
        """Record a control tool call for logging.

        Args:
            action: The control action being executed

        Returns:
            ControlToolCall log entry
        """
        tool_call = ControlToolCall(
            timestamp=datetime.now().isoformat(),
            type="CONTROL_TOOL_CALL",
            tool_name=action.tool,
            tool_input=action.args,
            tool_id=str(uuid.uuid4())[:8],
        )
        self.control_tool_calls.append(tool_call)
        return tool_call

    def record_control_result(
        self,
        tool_call: ControlToolCall,
        success: bool,
        response: Any,
        error: Optional[str] = None
    ) -> ControlToolResult:
        """Record a control tool result for logging.

        Args:
            tool_call: The corresponding tool call
            success: Whether the call succeeded
            response: The response data
            error: Optional error message

        Returns:
            ControlToolResult log entry
        """
        result = ControlToolResult(
            timestamp=datetime.now().isoformat(),
            type="CONTROL_TOOL_RESULT",
            tool_use_id=tool_call.tool_id,
            success=success,
            response=response,
            error=error,
        )
        self.control_tool_results.append(result)
        return result

    def increment_tool_count(self):
        """Increment the agent tool call counter."""
        self.agent_tool_call_count += 1


@dataclass
class AIAgent:
    """Roleplays AI assistant (like Claude Code, Cursor.ai) in dual-agent architecture.

    Responsibilities per Constitution Principle I:
    - Has access to MCP servers under test
    - Executes user requests by selecting and invoking appropriate MCP tools
    - MAY ask User agent for clarification when scenario is underspecified
    - MUST NOT know it's in a test scenario (authentic assistant behavior)

    FR-007: Agent Role does NOT have access to control MCP server.
    The control server is only available to User Role (see UserAgent).
    AIAgent only accesses mcpproxy via its native MCP interface.
    """
    mcp_config: str
    temperature: float = 0.0
    # FR-007a: System prompt MUST explicitly prioritize MCPProxy tools for MCP operations
    # This ensures AI agent uses mcp__mcpproxy__* tools instead of generic tools (WebSearch, Glob, etc.)
    system_prompt: str = """You are an MCP evaluation agent testing MCPProxy server functionality.

🎯 PRIMARY DIRECTIVE: Use MCPProxy tools for all MCP-related operations.

CRITICAL TOOL USAGE RULES:
1. Tool Discovery: ALWAYS use mcp__mcpproxy__retrieve_tools (NEVER WebSearch, Grep, Glob)
2. Server Management: ALWAYS use mcp__mcpproxy__upstream_servers (NEVER Read, Bash, file tools)
3. Security: ALWAYS use mcp__mcpproxy__quarantine_security for quarantine operations
4. Server Search: ALWAYS use mcp__mcpproxy__search_servers and mcp__mcpproxy__list_registries
5. Tool Execution: Use mcp__mcpproxy__call_tool after discovering tools

WORKFLOW EXAMPLES:
- "Find tools for X" → Call mcp__mcpproxy__retrieve_tools(query="X")
- "List MCP servers" → Call mcp__mcpproxy__upstream_servers(operation="list")
- "Add MCP server" → Call mcp__mcpproxy__upstream_servers(operation="add", ...)

Your goal is to test MCPProxy. Only use generic tools (WebSearch, Bash) when NO MCPProxy alternative exists."""
    conversation_history: List[DialogTurn] = field(default_factory=list)
    tools_discovered: bool = False
    _client: Optional[ClaudeSDKClient] = None

    async def initialize_client(self):
        """Initialize ClaudeSDKClient with MCP configuration."""
        if self._client is None:
            # Load MCP servers config as dict (SDK requires dict, not file path)
            import json
            from pathlib import Path

            mcp_config_dict = {}
            if self.mcp_config:
                config_path = Path(self.mcp_config)
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                        # Extract mcpServers dict from config file
                        mcp_config_dict = config_data.get('mcpServers', {})

            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                max_turns=100,
                mcp_servers=mcp_config_dict,  # Pass dict directly, not file path
                permission_mode="bypassPermissions",
                model="claude-sonnet-4-5-20250929",
                settings="claude_settings.json",  # Contains {"temperature": 0.0}
                # CRITICAL: SDK aborts connection if allowed_tools is empty/omitted
                # List MCPProxy built-in tools to enable connection
                allowed_tools=[
                    "mcp__mcpproxy__retrieve_tools",
                    "mcp__mcpproxy__call_tool",
                    "mcp__mcpproxy__read_cache",
                    "mcp__mcpproxy__upstream_servers",
                    "mcp__mcpproxy__quarantine_security",
                    "mcp__mcpproxy__search_servers",
                    "mcp__mcpproxy__list_registries"
                ]
            )
            self._client = ClaudeSDKClient(options=options)

    async def process_intent(self, user_turn: DialogTurn, current_turn_id: int) -> List[DialogTurn]:
        """Process user intent and generate response turns.

        Args:
            user_turn: DialogTurn with turn_type=USER_MESSAGE
            current_turn_id: Current turn counter

        Returns:
            List of DialogTurn objects (AGENT_MESSAGE, TOOL_CALL, TOOL_RESULT)
        """
        await self.initialize_client()

        turns = []
        turn_counter = current_turn_id

        # Send user query to Claude SDK
        async with self._client as client:
            await client.query(user_turn.content)

            # Collect all messages and tool calls
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        turn_counter += 1

                        if hasattr(block, 'text') and block.text:
                            # Agent message
                            turn = DialogTurn(
                                turn_id=turn_counter,
                                timestamp=datetime.now(),
                                turn_type=TurnType.AGENT_MESSAGE,
                                actor=Actor.AI_AGENT,
                                content=block.text,
                                metadata={
                                    "message_index": len([t for t in turns if t.turn_type == TurnType.AGENT_MESSAGE]),
                                    "thinking_visible": False
                                }
                            )
                            turns.append(turn)
                            self.conversation_history.append(turn)

                        elif hasattr(block, 'name') and hasattr(block, 'id'):
                            # Tool use block
                            tool_name = block.name
                            tool_id = block.id
                            tool_input = getattr(block, 'input', {})

                            turn = DialogTurn(
                                turn_id=turn_counter,
                                timestamp=datetime.now(),
                                turn_type=TurnType.TOOL_CALL,
                                actor=Actor.AI_AGENT,
                                content=f"Calling {tool_name}({tool_input})",
                                metadata={
                                    "tool_name": tool_name,
                                    "tool_id": tool_id,
                                    "tool_input": tool_input,
                                    "is_mcp_tool": tool_name.startswith("mcp__")
                                }
                            )
                            turns.append(turn)
                            self.conversation_history.append(turn)

                        elif hasattr(block, 'tool_use_id') and hasattr(block, 'content'):
                            # Tool result block
                            turn = DialogTurn(
                                turn_id=turn_counter,
                                timestamp=datetime.now(),
                                turn_type=TurnType.TOOL_RESULT,
                                actor=Actor.SYSTEM,
                                content=str(block.content)[:500],  # Truncate for readability
                                metadata={
                                    "tool_use_id": block.tool_use_id,
                                    "is_error": getattr(block, 'is_error', False),
                                    "result_size_bytes": len(str(block.content)),
                                    "execution_time_ms": 0  # Placeholder
                                }
                            )
                            turns.append(turn)
                            self.conversation_history.append(turn)

        return turns

    async def invoke_tool(self, tool_name: str, tool_input: Dict[str, Any], turn_id: int) -> DialogTurn:
        """Invoke MCP tool and return TOOL_RESULT DialogTurn.

        Note: Tool invocation is handled by ClaudeSDKClient automatically.
        This method is for direct tool calls if needed in future.

        Args:
            tool_name: Name of MCP tool
            tool_input: Tool arguments
            turn_id: Turn identifier

        Returns:
            DialogTurn with turn_type=TOOL_RESULT
        """
        # Placeholder implementation - actual tool calls go through Claude SDK
        turn = DialogTurn(
            turn_id=turn_id,
            timestamp=datetime.now(),
            turn_type=TurnType.TOOL_RESULT,
            actor=Actor.SYSTEM,
            content=f"Result from {tool_name}",
            metadata={
                "tool_use_id": f"direct_{turn_id}",
                "is_error": False,
                "result_size_bytes": 0,
                "execution_time_ms": 0
            }
        )
        self.conversation_history.append(turn)
        return turn

    async def request_clarification(self, question: str, options: List[str], turn_id: int) -> DialogTurn:
        """Ask User agent for clarification.

        Args:
            question: Clarification question
            options: List of possible answers
            turn_id: Turn identifier

        Returns:
            DialogTurn with turn_type=CLARIFICATION_REQUEST
        """
        turn = DialogTurn(
            turn_id=turn_id,
            timestamp=datetime.now(),
            turn_type=TurnType.CLARIFICATION_REQUEST,
            actor=Actor.AI_AGENT,
            content=question,
            metadata={
                "clarification_question": question,
                "options": options,
                "question_id": f"clarif_{turn_id}"
            }
        )
        self.conversation_history.append(turn)
        return turn

"""Dual-agent architecture for MCP evaluation system.

Implements Constitution Principle I: Dual-Agent Dialog Engine Architecture
with separate User Agent and AI Agent roles.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import yaml

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from .dialog_models import DialogTurn, TurnType, Actor


@dataclass
class UserAgent:
    """Roleplays human user in dual-agent architecture.

    Responsibilities per Constitution Principle I:
    - Issues requests to trigger MCP tool usage based on scenario intent
    - Responds to clarification questions from the AI agent
    - Does NOT directly invoke MCP tools (human-only behavior)
    - Evaluates whether the AI agent achieved goals and used tools correctly
    """
    scenario: Dict[str, Any]
    current_turn: int = 0
    clarification_responses: List[Dict[str, str]] = field(default_factory=list)
    conversation_history: List[DialogTurn] = field(default_factory=list)
    max_turns: int = 50

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


@dataclass
class AIAgent:
    """Roleplays AI assistant (like Claude Code, Cursor.ai) in dual-agent architecture.

    Responsibilities per Constitution Principle I:
    - Has access to MCP servers under test
    - Executes user requests by selecting and invoking appropriate MCP tools
    - MAY ask User agent for clarification when scenario is underspecified
    - MUST NOT know it's in a test scenario (authentic assistant behavior)
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
            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                max_turns=100,
                mcp_servers=self.mcp_config,
                permission_mode="bypassPermissions",
                model="claude-sonnet-4-5-20250929",
                settings="claude_settings.json"  # Contains {"temperature": 0.0}
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

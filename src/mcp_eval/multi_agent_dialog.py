"""Multi-agent dialog engine for simulating user-agent conversations."""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from rich.console import Console

console = Console()

class MultiAgentDialogEngine:
    """Engine for orchestrating dialog between MCP executor agent and user simulator agent."""
    
    def __init__(self, scenario_data: Dict[str, Any], mcp_config: str, output_dir: Path):
        self.scenario_data = scenario_data
        self.mcp_config = mcp_config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Dialog tracking
        self.conversation_log = []
        self.current_turn = 0
        self.max_turns = scenario_data.get('max_turns', 10)
        
        # Agent clients (will be initialized in async context)
        self.agent1_client = None  # MCP executor
        self.agent2_client = None  # User simulator
        
        # Extract dialog flow from scenario
        self.expected_dialog_flow = scenario_data.get('expected_dialog_flow', [])
        self.initial_user_intent = scenario_data.get('initial_user_intent', '')
        
    async def __aenter__(self):
        """Async context manager entry - initialize both agents."""
        console.print("🔧 [blue]Initializing multi-agent dialog system...[/blue]")
        
        # Initialize Agent 1 (MCP Executor)
        self.agent1_client = ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="""You are a helpful MCP tool executor agent. You can use MCP tools to access upstream servers and help users with their requests. 

When a user asks questions or requests help:
1. Use appropriate MCP tools to investigate and solve their problems
2. Ask follow-up questions if you need more information
3. Explain what you're doing and what you found
4. Be conversational and helpful

Available MCP tools include:
- mcp__mcpproxy__upstream_servers: List/manage upstream servers
- mcp__mcpproxy__server_logs: Get server logs
- mcp__mcpproxy__retrieve_tools: Search for available tools
- And other MCP tools for server management

Execute tasks step by step and provide clear explanations.""",
                max_turns=50,
                mcp_servers=self.mcp_config,
                permission_mode="bypassPermissions",
                model="claude-3-5-sonnet-20241022",
                settings="claude_settings.json"  # Temperature=0.0 for deterministic behavior
            )
        )
        
        # Initialize Agent 2 (User Simulator)
        self.agent2_client = ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=f"""You are an experienced AI developer/DevOps engineer working with MCP tools and server management. You are practical, direct, and knowledgeable about system administration.

Expected Dialog Flow: {json.dumps(self.expected_dialog_flow, indent=2)}

Your personality and response style:
- Professional and technically literate
- Ask specific, actionable questions 
- Provide context about your environment when relevant
- Use technical terminology appropriately
- Be concise but informative
- Focus on practical solutions and next steps
- Don't use overly enthusiastic phrases like "Perfect!" or "Great!"

Example responses:
- "Show me the logs for the last 50 lines"
- "I need to check the quarantine status" 
- "What's the connection error exactly?"
- "Let me unquarantine that server"
- "The config looks correct on my end"

Available tools for config changes:
- Read: Read configuration files
- Write: Update configuration files  
- Edit: Make specific edits to files
- Sleep: Wait for operations to complete""",
                max_turns=50,
                permission_mode="bypassPermissions",
                model="claude-3-5-sonnet-20241022"
            )
        )
        
        await self.agent1_client.__aenter__()
        await self.agent2_client.__aenter__()
        
        console.print("✅ [green]Multi-agent dialog system initialized[/green]")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup both agents."""
        try:
            if self.agent1_client:
                await self.agent1_client.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            console.print(f"⚠️ [yellow]Agent 1 cleanup warning: {e}[/yellow]")
        
        try:
            if self.agent2_client:
                await self.agent2_client.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            console.print(f"⚠️ [yellow]Agent 2 cleanup warning: {e}[/yellow]")
        
        console.print("🔄 [yellow]Multi-agent dialog system cleaned up[/yellow]")
    
    def _log_turn(self, turn_number: int, speaker: str, message: str, tool_calls: List[Dict] = None):
        """Log a dialog turn."""
        turn_data = {
            "turn": turn_number,
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message,
            "tool_calls": tool_calls or []
        }
        self.conversation_log.append(turn_data)
        
        # Pretty print to console
        color = "cyan" if speaker == "Agent" else "magenta"
        console.print(f"[bold {color}]{speaker} (Turn {turn_number}):[/bold {color}] {message}")
        
        if tool_calls:
            for tool_call in tool_calls:
                console.print(f"  🔧 [green]{tool_call.get('tool_name', 'unknown')}[/green]")
    
    async def _collect_agent_response(self, client: ClaudeSDKClient, query: str, speaker_name: str) -> Tuple[str, List[Dict]]:
        """Send query to agent and collect full response with tool calls."""
        console.print(f"📤 [dim]Sending query to {speaker_name}...[/dim]")
        await client.query(query)
        
        response_text_parts = []
        tool_calls = []
        message_count = 0
        
        console.print(f"📥 [dim]Collecting response from {speaker_name}...[/dim]")
        try:
            # Add timeout wrapper
            async with asyncio.timeout(60):  # 60 second timeout
                async for message in client.receive_response():
                    message_count += 1
                    console.print(f"📨 [dim]Message {message_count} from {speaker_name}[/dim]")
                    
                    if hasattr(message, 'content'):
                        for block in message.content:
                            # Text content
                            if hasattr(block, 'text'):
                                response_text_parts.append(block.text)
                                console.print(f"💬 [dim]Text: {block.text[:100]}...[/dim]")
                            
                            # Tool use
                            elif hasattr(block, 'name') and hasattr(block, 'id'):
                                tool_calls.append({
                                    "tool_name": block.name,
                                    "tool_id": block.id,
                                    "tool_input": getattr(block, 'input', {}),
                                    "timestamp": datetime.now().isoformat()
                                })
                                console.print(f"🔧 [dim]Tool call: {block.name}[/dim]")
                            
                            # Tool result
                            elif hasattr(block, 'tool_use_id') and hasattr(block, 'content'):
                                # Find corresponding tool call and add result
                                for tool_call in tool_calls:
                                    if tool_call.get("tool_id") == block.tool_use_id:
                                        tool_call["result"] = block.content
                                        tool_call["is_error"] = getattr(block, 'is_error', False)
                                        console.print(f"✅ [dim]Tool result for {tool_call['tool_name']}[/dim]")
                                        break
        except asyncio.TimeoutError:
            console.print(f"⏰ [yellow]Timeout waiting for {speaker_name} response[/yellow]")
            if not response_text_parts:
                response_text_parts.append(f"[Response timed out after 60 seconds]")
        
        full_response = "\n".join(response_text_parts).strip()
        console.print(f"📋 [dim]Final response from {speaker_name}: {len(full_response)} chars, {len(tool_calls)} tools[/dim]")
        return full_response, tool_calls
    
    async def execute_multi_turn_dialog(self) -> Dict[str, Any]:
        """Execute the multi-turn dialog between agents."""
        console.print(f"🎭 [bold blue]Starting multi-turn dialog: {self.scenario_data.get('name', 'Unknown')}[/bold blue]")
        
        # Start with initial user intent
        current_message = self.initial_user_intent
        self._log_turn(0, "User", current_message)
        
        for turn in range(1, self.max_turns + 1):
            self.current_turn = turn
            
            # Agent 1 (MCP Executor) responds to user
            console.print(f"🤖 [blue]Agent processing turn {turn}...[/blue]")
            agent_response, agent_tool_calls = await self._collect_agent_response(
                self.agent1_client, current_message, "Agent"
            )
            
            if not agent_response.strip():
                console.print("⚠️ [yellow]Agent response empty, ending dialog[/yellow]")
                break
                
            self._log_turn(turn, "Agent", agent_response, agent_tool_calls)
            
            # Check if dialog should end (agent indicates completion)
            if self._is_dialog_complete(agent_response, turn):
                console.print("✅ [green]Dialog completed naturally[/green]")
                break
            
            # User Simulator responds
            console.print(f"👤 [magenta]User simulator processing turn {turn}...[/magenta]")
            
            # Build context for user simulator
            conversation_context = self._build_conversation_context()
            user_prompt = f"""The agent just said: "{agent_response}"

Previous conversation context:
{conversation_context}

Current turn: {turn} of expected {len(self.expected_dialog_flow)} turns

Please respond as a user would. Be natural and follow the expected dialog flow."""
            
            user_response, user_tool_calls = await self._collect_agent_response(
                self.agent2_client, user_prompt, "User"
            )
            
            if not user_response.strip():
                console.print("⚠️ [yellow]User response empty, ending dialog[/yellow]")
                break
                
            self._log_turn(turn, "User", user_response, user_tool_calls)
            
            # User response becomes next message for agent
            current_message = user_response
            
            # Check if we've completed expected turns
            if turn >= len(self.expected_dialog_flow):
                console.print("✅ [green]Completed expected dialog flow[/green]")
                break
        
        # Save results
        results = await self._save_dialog_results()
        console.print(f"📊 [green]Dialog completed with {len(self.conversation_log)} turns[/green]")
        return results
    
    def _is_dialog_complete(self, agent_response: str, turn: int) -> bool:
        """Check if dialog should end based on agent response."""
        completion_indicators = [
            "you're all set", "that's everything", "problem solved", 
            "working now", "completed successfully", "all done"
        ]
        
        return any(indicator in agent_response.lower() for indicator in completion_indicators)
    
    def _build_conversation_context(self) -> str:
        """Build conversation context for user simulator."""
        context_parts = []
        for turn_data in self.conversation_log[-4:]:  # Last 4 turns for context
            speaker = turn_data["speaker"]
            message = turn_data["message"]
            context_parts.append(f"{speaker}: {message}")
        
        return "\n".join(context_parts)
    
    async def _save_dialog_results(self) -> Dict[str, Any]:
        """Save dialog results to files."""
        # Detailed log
        detailed_log_path = self.output_dir / "multi_agent_detailed_log.json"
        detailed_log = {
            "scenario": self.scenario_data.get('name', 'Unknown'),
            "execution_time": datetime.now().isoformat(),
            "total_turns": len(self.conversation_log),
            "conversation_log": self.conversation_log,
            "scenario_data": self.scenario_data
        }
        
        with open(detailed_log_path, 'w') as f:
            json.dump(detailed_log, f, indent=2)
        
        # Human-readable dialog transcript
        transcript_path = self.output_dir / "dialog_transcript.txt"
        with open(transcript_path, 'w') as f:
            f.write(f"Multi-Agent Dialog: {self.scenario_data.get('name', 'Unknown')}\n")
            f.write(f"Executed: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            
            for turn_data in self.conversation_log:
                f.write(f"{turn_data['speaker']} (Turn {turn_data['turn']}):\n")
                f.write(f"{turn_data['message']}\n")
                
                if turn_data.get('tool_calls'):
                    f.write(f"Tool calls:\n")
                    for tool_call in turn_data['tool_calls']:
                        f.write(f"  - {tool_call.get('tool_name', 'unknown')}\n")
                f.write("\n")
        
        # Generate HTML report
        try:
            from .multi_agent_reporter import MultiAgentHTMLReporter
            reporter = MultiAgentHTMLReporter()
            scenario_name = self.scenario_data.get('name', 'Unknown').replace(' ', '_').lower()
            html_report_path = reporter.generate_dialog_report(detailed_log, scenario_name)
            console.print(f"📊 [blue]HTML report generated: {html_report_path}[/blue]")
        except Exception as e:
            console.print(f"⚠️ [yellow]Failed to generate HTML report: {e}[/yellow]")
            html_report_path = None
        
        console.print(f"📄 [green]Results saved to {self.output_dir}[/green]")
        
        return {
            "success": True,
            "total_turns": len(self.conversation_log),
            "detailed_log_path": str(detailed_log_path),
            "transcript_path": str(transcript_path),
            "html_report_path": html_report_path,
            "conversation_log": self.conversation_log
        }
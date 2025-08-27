"""Scenario execution engine for MCP evaluation."""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from contextlib import asynccontextmanager

import sys
from pathlib import Path

# Import our existing interceptor from the root directory
sys.path.append(str(Path(__file__).parent.parent.parent))
from main import ConversationInterceptor


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""
    tool_name: str
    tool_id: str
    tool_input: Dict[str, Any]
    timestamp: datetime
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ScenarioResult:
    """Result of scenario execution."""
    scenario_name: str
    success: bool
    execution_time: float
    detailed_log: Dict[str, Any]
    dialog_trajectory: str
    tool_calls: List[ToolCallRecord]
    error: Optional[str] = None


class ScenarioEngine:
    """Executes user scenarios and records detailed interaction logs."""
    
    def __init__(self, mcp_config: str = "mcp_servers.json", verbose: bool = False):
        self.mcp_config = mcp_config
        self.verbose = verbose
        self.interceptor = ConversationInterceptor(log_file="scenario_debug.jsonl")
    
    def execute_scenario(self, scenario_data: Dict[str, Any]) -> ScenarioResult:
        """
        Execute a scenario and return detailed results.
        
        Args:
            scenario_data: Scenario configuration from YAML
            
        Returns:
            ScenarioResult with logs and trajectory
        """
        scenario_name = scenario_data.get("name", "unknown")
        user_intent = scenario_data.get("user_intent", "")
        
        if self.verbose:
            print(f"Executing scenario: {scenario_name}")
            print(f"User intent: {user_intent}")
        
        start_time = time.time()
        
        try:
            # Execute the scenario asynchronously
            result = asyncio.run(self._execute_scenario_async(scenario_data))
            execution_time = time.time() - start_time
            
            return ScenarioResult(
                scenario_name=scenario_name,
                success=True,
                execution_time=execution_time,
                detailed_log=result["detailed_log"],
                dialog_trajectory=result["dialog_trajectory"], 
                tool_calls=result["tool_calls"]
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            if self.verbose:
                print(f"Scenario failed: {error_msg}")
            
            return ScenarioResult(
                scenario_name=scenario_name,
                success=False,
                execution_time=execution_time,
                detailed_log={"error": error_msg, "timestamp": datetime.now().isoformat()},
                dialog_trajectory=f"ERROR: {error_msg}",
                tool_calls=[],
                error=error_msg
            )
    
    async def _execute_scenario_async(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scenario using Claude SDK with MCP integration."""
        user_intent = scenario_data.get("user_intent", "")
        
        async with self.interceptor.intercept_conversation(
            system_prompt="You are a helpful agent that can use MCP tools to access upstream servers",
            max_turns=10,
            mcp_servers=self.mcp_config,
            permission_mode="bypassPermissions"
        ) as client:
            # Send user query
            await client.query(user_intent)
            
            # Collect all messages and tool calls
            tool_calls = []
            dialog_parts = [f"USER: {user_intent}\n"]
            
            async for message in client.receive_response():
                # Process message and extract tool calls
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text') and block.text:
                            dialog_parts.append(f"AGENT: {block.text}\n")
                        elif hasattr(block, 'name') and hasattr(block, 'id'):  # Tool use block
                            tool_record = ToolCallRecord(
                                tool_name=block.name,
                                tool_id=block.id,
                                tool_input=getattr(block, 'input', {}),
                                timestamp=datetime.now()
                            )
                            tool_calls.append(tool_record)
                            dialog_parts.append(f"TOOL_CALL: {block.name}({tool_record.tool_input})\n")
                        elif hasattr(block, 'tool_use_id') and hasattr(block, 'content'):  # Tool result
                            # Find matching tool call and add response
                            for tc in tool_calls:
                                if tc.tool_id == block.tool_use_id:
                                    tc.response = {
                                        "content": block.content,
                                        "is_error": getattr(block, 'is_error', None)
                                    }
                                    
                                    # Add to dialog
                                    if getattr(block, 'is_error', False):
                                        dialog_parts.append(f"TOOL_ERROR: {block.content}\n")
                                    else:
                                        content_preview = str(block.content)[:200]
                                        dialog_parts.append(f"TOOL_RESULT: {content_preview}...\n")
                                    break
        
        # Extract detailed log from interceptor
        detailed_log = {
            "scenario": scenario_data.get("name", "unknown"),
            "execution_time": datetime.now().isoformat(),
            "user_intent": user_intent,
            "messages": self.interceptor.events,
            "tool_calls_summary": [asdict(tc) for tc in tool_calls]
        }
        
        # Create dialog trajectory
        dialog_trajectory = "".join(dialog_parts)
        
        # Add evaluation status
        success_criteria = scenario_data.get("success_criteria", [])
        evaluation_status = self._evaluate_success(dialog_trajectory, tool_calls, success_criteria)
        dialog_trajectory += f"\nEVALUATION: {evaluation_status}\n"
        
        return {
            "detailed_log": detailed_log,
            "dialog_trajectory": dialog_trajectory,
            "tool_calls": tool_calls
        }
    
    def _evaluate_success(
        self, 
        dialog_trajectory: str, 
        tool_calls: List[ToolCallRecord], 
        success_criteria: List[str]
    ) -> str:
        """Evaluate if scenario met success criteria."""
        if not success_criteria:
            return "✅ SUCCESS - No specific criteria defined"
        
        met_criteria = []
        for criterion in success_criteria:
            # Simple string matching for now - could be enhanced with semantic matching
            if any(criterion.lower() in str(tc.response).lower() for tc in tool_calls if tc.response):
                met_criteria.append(criterion)
            elif criterion.lower() in dialog_trajectory.lower():
                met_criteria.append(criterion)
        
        if len(met_criteria) == len(success_criteria):
            return f"✅ SUCCESS - All {len(success_criteria)} criteria met"
        else:
            return f"❌ PARTIAL - {len(met_criteria)}/{len(success_criteria)} criteria met"
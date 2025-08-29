"""Enhanced scenario execution engine with failure-aware recording and human validation."""

import asyncio
import json
import yaml
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import traceback

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

console = Console()

class FailureAwareScenarioRunner:
    """Scenario runner with enhanced failure detection and human validation reporting."""
    
    def __init__(self, output_dir: Path, mcp_config: str = "mcp_servers.json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_config = mcp_config
        self.current_config_file = None
        
        # Critical operations that can block further execution
        self.critical_operations = {
            "add", "create", "initialize", "connect", "setup", "install"
        }
        
        # Capture mcpproxy-go git hash for baseline tracking
        self.mcpproxy_git_info = self._get_mcpproxy_git_info()
    
    def _get_mcpproxy_git_info(self) -> Dict[str, Any]:
        """Get git hash and commit info for mcpproxy-go project."""
        import os
        mcpproxy_source = os.getenv("MCPPROXY_SOURCE_PATH", "../mcpproxy-go")
        mcpproxy_path = Path(mcpproxy_source).expanduser().resolve()
        
        if not mcpproxy_path.exists():
            return {
                "git_hash": "unknown",
                "git_hash_short": "unknown",
                "commit_message": "mcpproxy-go directory not found",
                "commit_date": None,
                "branch": "unknown"
            }
        
        try:
            # Get git hash
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=mcpproxy_path,
                text=True
            ).strip()
            
            # Get short hash
            git_hash_short = git_hash[:8]
            
            # Get commit message
            commit_message = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=mcpproxy_path,
                text=True
            ).strip()
            
            # Get commit date
            commit_date = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%ci"],
                cwd=mcpproxy_path,
                text=True
            ).strip()
            
            # Get branch name
            try:
                branch = subprocess.check_output(
                    ["git", "branch", "--show-current"],
                    cwd=mcpproxy_path,
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                branch = "detached"
            
            return {
                "git_hash": git_hash,
                "git_hash_short": git_hash_short,
                "commit_message": commit_message,
                "commit_date": commit_date,
                "branch": branch
            }
            
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Could not get mcpproxy git info: {e}[/yellow]")
            return {
                "git_hash": "error",
                "git_hash_short": "error", 
                "commit_message": f"Git command failed: {str(e)}",
                "commit_date": None,
                "branch": "error"
            }
    
    def _restart_mcpproxy_docker(self, config_file: str) -> bool:
        """Restart MCPProxy Docker container with specified config."""
        try:
            console.print(f"🔄 [yellow]Restarting MCPProxy with config: {config_file}[/yellow]")
            
            # Change to Docker directory (relative to project root)
            project_root = Path(__file__).parent.parent.parent  # Go up from src/mcp_eval/ to project root
            docker_dir = project_root / "testing" / "docker"
            if not docker_dir.exists():
                console.print(f"❌ [red]Docker directory not found: {docker_dir}[/red]")
                return False
            
            # Copy the config file to the Docker directory as config-template.json
            config_source = Path(config_file)
            if not config_source.exists():
                console.print(f"❌ [red]Config file not found: {config_file}[/red]")
                return False
            
            import shutil
            config_dest = docker_dir / "config-template.json"
            shutil.copy2(config_source, config_dest)
            console.print(f"📋 [green]Config copied to {config_dest}[/green]")
            
            # Set environment variables for Docker compose
            env = {
                **subprocess.os.environ,
                "TEST_SESSION": "test777-dind"
            }
            
            # Stop existing container
            console.print("🛑 Stopping existing MCPProxy container...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=docker_dir,
                env=env,
                check=False,
                capture_output=True
            )
            
            # Start container with new config
            console.print("🚀 Starting MCPProxy with new config...")
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=docker_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                console.print(f"❌ [red]Failed to start MCPProxy: {result.stderr}[/red]")
                return False
            
            # Wait a moment for container to be ready
            console.print("⏳ Waiting for MCPProxy to be ready...")
            import time
            time.sleep(5)
            
            # Verify container is running and healthy
            verify_result = subprocess.run(
                ["docker", "ps", "--filter", "name=mcpproxy-test-test777-dind", "--format", "table {{.Names}}\\t{{.Status}}"],
                capture_output=True,
                text=True
            )
            
            if "mcpproxy-test-test777-dind" in verify_result.stdout and "Up" in verify_result.stdout:
                console.print("✅ [green]MCPProxy container restarted successfully[/green]")
                return True
            else:
                console.print("❌ [red]MCPProxy container not healthy after restart[/red]")
                console.print(f"Docker ps output: {verify_result.stdout}")
                return False
                
        except subprocess.CalledProcessError as e:
            console.print(f"❌ [red]Docker restart failed: {e}[/red]")
            if hasattr(e, 'stdout') and e.stdout:
                console.print(f"stdout: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                console.print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            console.print(f"❌ [red]Unexpected error during Docker restart: {e}[/red]")
            return False
    
    async def _discover_tools(self) -> Dict[str, Any]:
        """Discover available tools from MCP servers."""
        try:
            from claude_code_sdk import ClaudeSDKClient
            import asyncio
            
            # Wait a bit longer after Docker restart to ensure MCPProxy is fully ready
            console.print("⏳ [yellow]Waiting for MCPProxy to be fully ready for tool discovery...[/yellow]")
            await asyncio.sleep(3)
            
            # Create a temporary SDK client to discover tools
            client = ClaudeSDKClient(
                options=ClaudeCodeOptions(
                    mcp_servers=self.mcp_config,
                    permission_mode="bypassPermissions",
                    model="claude-3-5-sonnet-20241022",
                    settings="claude_settings.json"  # Settings file with temperature=0.0
                )
            )
            
            # Make a list_tools call to discover available tools with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Send a simple query to trigger tool discovery
                    console.print(f"🛠️  [yellow]Querying available tools (attempt {attempt + 1}/{max_retries})...[/yellow]")
                    response = await client.query(
                        "List all available MCP tools and their descriptions"
                    )
                    
                    # Parse the response to extract tool information
                    tools_info = {
                        "discovery_method": "claude_query",
                        "query_response": str(response)[:1000],  # Truncate response for storage
                        "discovered_at": datetime.now().isoformat(),
                        "tools": []
                    }
                    
                    # Try to extract structured tool information from messages
                    for message in response.messages:
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'name') and hasattr(block, 'id'):  # Tool use block
                                    tool_info = {
                                        "name": block.name,
                                        "id": block.id,
                                        "input": getattr(block, 'input', {}),
                                        "discovered_via": "tool_call"
                                    }
                                    tools_info["tools"].append(tool_info)
                    
                    console.print(f"✅ [green]Discovered {len(tools_info['tools'])} tools via queries[/green]")
                    return tools_info
                    
                except Exception as query_error:
                    console.print(f"⚠️  [yellow]Tool query attempt {attempt + 1} failed: {query_error}[/yellow]")
                    if attempt == max_retries - 1:  # Last attempt
                        # Return a graceful degradation - don't fail the whole scenario
                        return {
                            "discovery_method": "failed_with_retry",
                            "error": str(query_error),
                            "discovered_at": datetime.now().isoformat(),
                            "tools": [],
                            "note": "Tool discovery failed but scenario execution can continue"
                        }
                    else:
                        # Wait before retry
                        await asyncio.sleep(2)
                
        except Exception as e:
            console.print(f"❌ [red]Tool discovery failed: {e}[/red]")
            # Return a graceful degradation - don't fail the whole scenario
            return {
                "discovery_method": "error_graceful",
                "error": str(e),
                "discovered_at": datetime.now().isoformat(),
                "tools": [],
                "note": "Tool discovery failed but scenario execution can continue"
            }
        
    async def execute_scenario(
        self, 
        scenario_file: Path, 
        mode: str = "baseline"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a scenario with enhanced failure detection and reporting.
        
        Args:
            scenario_file: Path to scenario YAML file
            mode: "baseline" or "evaluation"
            
        Returns:
            Tuple of (success, execution_data)
        """
        console.print(f"🚀 [bold blue]Executing scenario: {scenario_file.name}[/bold blue]")
        
        # Load scenario
        try:
            with open(scenario_file, 'r') as f:
                scenario_data = yaml.safe_load(f)
        except Exception as e:
            console.print(f"❌ [red]Failed to load scenario: {e}[/red]")
            return False, {"error": f"Scenario load failed: {e}"}
        
        # Check if scenario is enabled
        if not scenario_data.get('enabled', True):
            console.print(f"⏭️  [yellow]Scenario disabled, skipping[/yellow]")
            return True, {"skipped": True, "reason": "disabled"}
        
        scenario_name = scenario_data.get('name', 'Unknown Scenario')
        user_intent = scenario_data.get('user_intent', '')
        expected_trajectory = scenario_data.get('expected_trajectory', [])
        success_criteria = scenario_data.get('success_criteria', [])
        config_file = scenario_data.get('config_file', None)
        
        # Handle scenario-specific config
        if config_file:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                # Resolve relative path from scenario file directory
                config_path = scenario_file.parent.parent / config_file
            
            if config_path.exists():
                console.print(f"🔧 [cyan]Using scenario-specific config: {config_path}[/cyan]")
                
                # Restart MCPProxy with new config if it's different from current
                if str(config_path) != self.current_config_file:
                    if not self._restart_mcpproxy_docker(str(config_path)):
                        console.print(f"❌ [red]Failed to restart MCPProxy with config: {config_path}[/red]")
                        return False, {"error": f"MCPProxy restart failed with config: {config_path}"}
                    
                    # Update current_config_file but keep using the same mcp_servers.json for Claude SDK
                    self.current_config_file = str(config_path)
                else:
                    console.print(f"📋 [green]MCPProxy already using correct config[/green]")
            else:
                console.print(f"❌ [red]Config file not found: {config_path}[/red]")
                return False, {"error": f"Config file not found: {config_path}"}
        
        console.print(f"📋 [bold]{scenario_name}[/bold]")
        console.print(f"🎯 Intent: {user_intent}")
        console.print(f"📊 Expected tools: {len(expected_trajectory)}")
        
        # Skip tool discovery for now due to connection issues - it's only for metadata
        available_tools = {
            "discovery_method": "skipped",
            "note": "Tool discovery disabled to avoid connection issues",
            "discovered_at": datetime.now().isoformat(),
            "tools": []
        }
        
        # Execute with enhanced tracking
        execution_data = {
            "scenario": scenario_name,
            "execution_time": datetime.now().isoformat(),
            "user_intent": user_intent,
            "expected_trajectory": expected_trajectory,
            "success_criteria": success_criteria,
            "mode": mode,
            "available_tools": available_tools,
            "messages": [],
            "tool_calls_summary": [],
            "execution_status": "UNKNOWN",
            "failure_analysis": {},
            "early_stopped": False,
            "mcpproxy_git_info": self.mcpproxy_git_info
        }
        
        try:
            # Execute scenario with Claude SDK
            success = await self._execute_with_claude(user_intent, execution_data)
            
            # Analyze execution results
            self._analyze_execution_results(execution_data)
            
            # Generate human validation report
            if mode == "baseline":
                self._generate_validation_report(execution_data, scenario_file)
            
            return success, execution_data
            
        except Exception as e:
            console.print(f"❌ [red]Execution failed: {e}[/red]")
            execution_data["execution_status"] = "ERROR"
            execution_data["error"] = str(e)
            execution_data["traceback"] = traceback.format_exc()
            return False, execution_data
    
    async def _execute_with_claude(self, user_intent: str, execution_data: Dict[str, Any]) -> bool:
        """Execute scenario with Claude SDK and track all interactions."""
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="You are a helpful agent that can use MCP tools to access upstream servers. Execute tasks step by step and provide clear explanations.",
                max_turns=100,
                mcp_servers=self.mcp_config,
                permission_mode="bypassPermissions",
                model="claude-3-5-sonnet-20241022",
                settings="claude_settings.json"  # Settings file with temperature=0.0
            )
        ) as client:
            
            # Send user query
            console.print(f"💬 [cyan]Sending query: {user_intent}[/cyan]")
            await client.query(user_intent)
            
            message_count = 0
            current_tool_call = None
            
            async for message in client.receive_response():
                message_count += 1
                
                # Log full message
                execution_data["messages"].append({
                    "timestamp": datetime.now().isoformat(),
                    "message_number": message_count,
                    "type": type(message).__name__,
                    "content": self._serialize_message(message)
                })
                
                # Process message content
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'name') and hasattr(block, 'id'):  # Tool use block
                            current_tool_call = {
                                "tool_name": block.name,
                                "tool_id": block.id,
                                "tool_input": getattr(block, 'input', {}),
                                "timestamp": datetime.now().isoformat(),
                                "response": None,
                                "error": None
                            }
                            
                            console.print(f"🔧 [green]Tool Call: {block.name}[/green]")
                            
                        elif hasattr(block, 'tool_use_id') and hasattr(block, 'content'):  # Tool result block
                            if current_tool_call and current_tool_call["tool_id"] == block.tool_use_id:
                                # Parse tool result
                                try:
                                    parsed_content = json.loads(block.content)
                                except (json.JSONDecodeError, TypeError):
                                    parsed_content = block.content
                                
                                current_tool_call["response"] = {
                                    "content": [{
                                        "type": "text",
                                        "text": block.content
                                    }],
                                    "is_error": getattr(block, 'is_error', None)
                                }
                                
                                # Check for errors
                                if getattr(block, 'is_error', None) or self._detect_error_in_response(parsed_content):
                                    current_tool_call["error"] = self._extract_error_message(parsed_content, block)
                                    console.print(f"❌ [red]Tool Error: {current_tool_call['error']}[/red]")
                                else:
                                    console.print(f"✅ [green]Tool Success[/green]")
                                
                                # Add to summary and check for early stopping
                                execution_data["tool_calls_summary"].append(current_tool_call.copy())
                                
                                # Check if this is a critical failure that should stop execution
                                if self._is_critical_failure(current_tool_call):
                                    console.print(f"🚫 [bold red]Critical failure detected - stopping execution[/bold red]")
                                    execution_data["early_stopped"] = True
                                    execution_data["execution_status"] = "BLOCKED"
                                    return False
                                
                                current_tool_call = None
                        
                        elif hasattr(block, 'text'):  # Text response
                            console.print(f"💭 [white]{block.text[:100]}...[/white]")
            
            return True
    
    def _serialize_message(self, message) -> Dict[str, Any]:
        """Serialize message object for JSON storage."""
        try:
            if hasattr(message, '__dict__'):
                return {
                    '_type': type(message).__name__,
                    **{k: self._serialize_object(v) for k, v in message.__dict__.items()}
                }
            else:
                return {"_type": type(message).__name__, "_str": str(message)}
        except Exception as e:
            return {"_type": type(message).__name__, "_error": str(e)}
    
    def _serialize_object(self, obj) -> Any:
        """Recursively serialize objects."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize_object(v) for k, v in obj.items()}
        elif hasattr(obj, '__dict__'):
            return {k: self._serialize_object(v) for k, v in obj.__dict__.items()}
        else:
            return str(obj)
    
    def _detect_error_in_response(self, parsed_content: Any) -> bool:
        """Detect errors in tool response content."""
        if isinstance(parsed_content, dict):
            # Check for common error indicators
            return any(key in parsed_content for key in ['error', 'Error', 'ERROR', 'failed', 'Failed'])
        elif isinstance(parsed_content, str):
            error_keywords = ['error', 'failed', 'not found', 'invalid', 'unable to']
            return any(keyword in parsed_content.lower() for keyword in error_keywords)
        return False
    
    def _extract_error_message(self, parsed_content: Any, block) -> str:
        """Extract error message from response."""
        if hasattr(block, 'is_error') and block.is_error:
            return "Tool returned error response"
        
        if isinstance(parsed_content, dict):
            for key in ['error', 'Error', 'ERROR', 'message']:
                if key in parsed_content:
                    return str(parsed_content[key])
        
        if isinstance(parsed_content, str) and len(parsed_content) < 200:
            return parsed_content
        
        return "Tool execution failed"
    
    def _is_critical_failure(self, tool_call: Dict[str, Any]) -> bool:
        """Check if this is a critical failure that blocks further execution."""
        if not tool_call.get("error"):
            return False
        
        # Check if this involves a critical operation
        tool_input = tool_call.get("tool_input", {})
        operation = tool_input.get("operation", "").lower()
        
        return any(critical_op in operation for critical_op in self.critical_operations)
    
    def _analyze_execution_results(self, execution_data: Dict[str, Any]):
        """Analyze execution results and set status."""
        tool_calls = execution_data.get("tool_calls_summary", [])
        
        if execution_data.get("early_stopped"):
            execution_data["execution_status"] = "BLOCKED"
            return
        
        # Count failures
        failures = []
        for tool_call in tool_calls:
            if tool_call.get("error"):
                failures.append({
                    "tool": tool_call.get("tool_name"),
                    "operation": tool_call.get("tool_input", {}).get("operation", ""),
                    "error": tool_call.get("error")
                })
        
        execution_data["failure_analysis"] = {
            "total_tools": len(tool_calls),
            "failed_tools": len(failures),
            "failures": failures,
            "success_rate": (len(tool_calls) - len(failures)) / max(1, len(tool_calls))
        }
        
        # Set overall status
        if len(failures) == 0:
            execution_data["execution_status"] = "SUCCESS"
        elif len(failures) == len(tool_calls):
            execution_data["execution_status"] = "FAILED"
        else:
            execution_data["execution_status"] = "PARTIAL"
    
    def _generate_validation_report(self, execution_data: Dict[str, Any], scenario_file: Path):
        """Generate human validation report for baseline review."""
        console.print("\n" + "="*80)
        console.print("🧑‍⚖️ [bold yellow]BASELINE VALIDATION REPORT[/bold yellow]")
        console.print("="*80)
        
        # Scenario overview
        scenario_panel = Panel(
            f"[bold]Scenario:[/bold] {execution_data['scenario']}\n"
            f"[bold]Intent:[/bold] {execution_data['user_intent']}\n"
            f"[bold]Status:[/bold] {execution_data['execution_status']}\n"
            f"[bold]Tools Executed:[/bold] {len(execution_data['tool_calls_summary'])}",
            title="📋 Scenario Summary",
            border_style="blue"
        )
        console.print(scenario_panel)
        
        # Tool execution summary
        tool_table = Table(
            title="🔧 Tool Execution Summary",
            box=box.ROUNDED
        )
        tool_table.add_column("#", style="dim", width=3)
        tool_table.add_column("Tool Name", style="cyan")
        tool_table.add_column("Operation", style="green")
        tool_table.add_column("Parameters", style="white")
        tool_table.add_column("Status", justify="center")
        tool_table.add_column("Result/Error", style="yellow")
        
        for i, tool_call in enumerate(execution_data['tool_calls_summary'], 1):
            tool_name = tool_call.get('tool_name', 'Unknown')
            operation = tool_call.get('tool_input', {}).get('operation', 'N/A')
            
            # Format parameters (show first few)
            params = tool_call.get('tool_input', {})
            if params:
                # Convert complex values to strings and truncate
                param_items = []
                for k, v in list(params.items())[:2]:
                    v_str = str(v)
                    if len(v_str) > 30:
                        v_str = v_str[:30] + "..."
                    param_items.append(f"{k}: {v_str}")
                param_str = ", ".join(param_items)
                if len(params) > 2:
                    param_str += f" +{len(params)-2} more"
            else:
                param_str = "(no params)"
            
            # Status and result
            if tool_call.get('error'):
                status = "❌ ERROR"
                result = str(tool_call.get('error', 'Unknown error'))[:50] + "..."
            else:
                status = "✅ SUCCESS"
                response = tool_call.get('response', {})
                if response:
                    content = response.get('content', [{}])
                    # Handle nested content structure
                    if isinstance(content, list) and len(content) > 0:
                        first_item = content[0]
                        if isinstance(first_item, dict):
                            text_data = first_item.get('text', '')
                            # Handle case where text is still a list (nested structure)
                            if isinstance(text_data, list) and len(text_data) > 0:
                                text = text_data[0].get('text', '') if isinstance(text_data[0], dict) else str(text_data[0])
                            else:
                                text = str(text_data)
                        else:
                            text = str(first_item)
                    else:
                        text = str(content)
                    result = text[:50] + ("..." if len(text) > 50 else "")
                else:
                    result = "No response data"
            
            tool_table.add_row(
                str(i),
                tool_name,
                operation,
                param_str,
                status,
                result
            )
        
        console.print(tool_table)
        
        # Validation questions
        validation_panel = Panel(
            "[bold yellow]HUMAN VALIDATION REQUIRED[/bold yellow]\n\n"
            "Please review the execution above and verify:\n"
            "✓ Are the tool calls appropriate for the user intent?\n"
            "✓ Do the parameters make sense?\n"
            "✓ Are the results as expected?\n"
            "✓ Does this represent a good baseline trajectory?\n\n"
            "[bold]If this execution is NOT acceptable:[/bold]\n"
            f"Run: uv run python mcp-eval baseline {scenario_file.stem} --retry\n\n"
            "[bold]If this execution is acceptable:[/bold]\n"
            "The baseline has been automatically saved.",
            title="👨‍💻 Next Steps",
            border_style="yellow"
        )
        console.print(validation_panel)
        console.print("\n")
    
    def save_execution_results(self, execution_data: Dict[str, Any], scenario_name: str, mode: str):
        """Save execution results to output directory."""
        # Use the output_dir directly without adding extra subdirectories
        # The CLI already creates the appropriate directory structure
        output_dir = self.output_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed log
        detailed_log_path = output_dir / "detailed_log.json"
        with open(detailed_log_path, 'w') as f:
            json.dump(execution_data, f, indent=2)
        
        # Generate human-readable trajectory
        trajectory_path = output_dir / "trajectory.txt"
        self._generate_trajectory_file(execution_data, trajectory_path)
        
        console.print(f"💾 [green]Results saved to {output_dir}[/green]")
    
    def _generate_trajectory_file(self, execution_data: Dict[str, Any], output_path: Path):
        """Generate human-readable trajectory file."""
        with open(output_path, 'w') as f:
            f.write(f"USER: {execution_data['user_intent']}\n")
            f.write("AGENT: I'll help you with this task.\n")
            
            for i, tool_call in enumerate(execution_data['tool_calls_summary'], 1):
                # Tool call
                tool_name = tool_call.get('tool_name', 'unknown')
                tool_input = tool_call.get('tool_input', {})
                f.write(f"TOOL_CALL: {tool_name}({tool_input})\n")
                
                # Tool result
                if tool_call.get('error'):
                    f.write(f"TOOL_RESULT: ERROR - {tool_call['error']}\n")
                else:
                    response = tool_call.get('response', {})
                    if response:
                        content = response.get('content', [{}])[0].get('text', 'No response')
                        f.write(f"TOOL_RESULT: {content}\n")
                    else:
                        f.write("TOOL_RESULT: Success (no response data)\n")
                
                f.write("AGENT: Tool executed successfully.\n")
            
            # Evaluation
            status = execution_data.get('execution_status', 'UNKNOWN')
            if status == "SUCCESS":
                f.write("\nEVALUATION: ✅ SUCCESS - All tools executed successfully\n")
            elif status == "BLOCKED":
                f.write("\nEVALUATION: 🚫 BLOCKED - Critical failure prevented completion\n")
            elif status == "FAILED":
                f.write("\nEVALUATION: ❌ FAILED - Multiple tool failures\n")
            else:
                f.write(f"\nEVALUATION: ⚠️  PARTIAL - Status: {status}\n")
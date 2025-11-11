"""
HTML Report Generator for MCP Evaluation System

Generates rich, interactive HTML reports for:
1. Baseline data quality analysis
2. Baseline vs evaluation comparison with diff visualization
"""

import json
import html
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()

class HTMLReporter:
    """Generate interactive HTML reports for MCP evaluation results."""
    
    def __init__(self, output_dir: Path = Path("reports")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_baseline_report(self, 
                                baseline_data: Dict[str, Any], 
                                scenario_name: str,
                                output_filename: Optional[str] = None) -> Path:
        """Generate HTML report for baseline data quality analysis."""
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{scenario_name}_baseline_{timestamp}.html"
            
        output_path = self.output_dir / output_filename
        
        html_content = self._generate_baseline_html(baseline_data, scenario_name)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        console.print(f"📊 [green]Baseline report generated:[/green] {output_path}")
        return output_path
        
    def generate_comparison_report(self,
                                 current_data: Dict[str, Any],
                                 baseline_data: Dict[str, Any], 
                                 comparison_result: Dict[str, Any],
                                 scenario_name: str,
                                 output_filename: Optional[str] = None) -> Path:
        """Generate HTML report comparing baseline vs current execution."""
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{scenario_name}_comparison_{timestamp}.html"
            
        output_path = self.output_dir / output_filename
        
        html_content = self._generate_comparison_html(
            current_data, baseline_data, comparison_result, scenario_name
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        console.print(f"📊 [green]Comparison report generated:[/green] {output_path}")
        return output_path
    
    def _generate_available_tools_html(self, available_tools: Dict[str, Any]) -> str:
        """Generate HTML section for available tools information."""
        if not available_tools or not available_tools.get("tools"):
            # Check if this is a graceful degradation vs hard failure
            discovery_method = available_tools.get("discovery_method", "unknown") if available_tools else "unknown"
            error_msg = available_tools.get("error", "Unknown error") if available_tools else "No data available"
            note_msg = available_tools.get("note", "") if available_tools else ""
            
            if discovery_method in ["failed_with_retry", "error_graceful"]:
                # Graceful degradation - show informational message
                return f"""
        <section class="stats-container">
            <h3>🛠️ Available Tools</h3>
            <div class="empty-conversation">
                <p><strong>ℹ️ Tool Discovery Status:</strong> Tool discovery was not successful during baseline recording</p>
                <p class="error">Reason: {html.escape(str(error_msg))}</p>
                {f'<p class="info"><em>{html.escape(note_msg)}</em></p>' if note_msg else ''}
                <p><small>Note: This does not affect scenario execution or validation. The MCP tools are still functional during the actual conversation.</small></p>
            </div>
        </section>"""
            else:
                # Hard failure - show error message
                return f"""
        <section class="stats-container">
            <h3>🛠️ Available Tools</h3>
            <div class="empty-conversation">
                <p>No tools discovered or tool discovery failed</p>
                {f'<p class="error">Error: {html.escape(str(error_msg))}</p>' if available_tools and available_tools.get("error") else ''}
            </div>
        </section>"""
        
        discovery_method = available_tools.get("discovery_method", "unknown")
        discovered_at = available_tools.get("discovered_at", "unknown")
        tools_list = available_tools.get("tools", [])
        
        tools_grid_html = ""
        if tools_list:
            tools_grid_html = '<div class="stats-grid">'
            for i, tool in enumerate(tools_list):
                tool_name = html.escape(str(tool.get("name", f"tool_{i}")))
                tool_id = html.escape(str(tool.get("id", "unknown")))
                tool_input = tool.get("input", {})
                input_preview = html.escape(str(tool_input)[:50]) + ("..." if len(str(tool_input)) > 50 else "")
                
                tools_grid_html += f"""
                <div class="stat-item">
                    <div class="stat-value" style="font-size: 1.2em;">{tool_name}</div>
                    <div class="stat-label">ID: {tool_id}</div>
                    {f'<div class="stat-label" style="margin-top: 4px; font-family: monospace; font-size: 0.7em;">{input_preview}</div>' if input_preview.strip() != '{}' else ''}
                </div>"""
            tools_grid_html += '</div>'
        else:
            tools_grid_html = '<p class="empty-conversation">No tools found in discovery response</p>'
        
        return f"""
        <section class="stats-container">
            <h3>🛠️ Available Tools Discovery</h3>
            <div class="mcpproxy-info" style="margin-bottom: 10px;">
                <strong>Discovery Method:</strong> {html.escape(discovery_method)} 
                <span class="commit-date">at {discovered_at}</span>
            </div>
            <div class="termination-info">
                <div class="termination-details">
                    <span><strong>Total Tools:</strong> {len(tools_list)}</span>
                    <span><strong>Status:</strong> {"SUCCESS" if tools_list else "FAILED" if available_tools.get("error") else "NO_TOOLS"}</span>
                </div>
            </div>
            {tools_grid_html}
        </section>"""
        
    def _evaluate_actual_status(self, baseline_data: Dict[str, Any]) -> str:
        """Evaluate actual execution status based on failure analysis and tool success."""
        failure_analysis = baseline_data.get("failure_analysis", {})
        
        # If we have failure analysis data, use it
        if failure_analysis:
            success_rate = failure_analysis.get("success_rate", 0.0)
            failed_tools = failure_analysis.get("failed_tools", 0)
            
            if success_rate == 1.0 and failed_tools == 0:
                return "SUCCESS"
            elif success_rate > 0.5:
                return "PARTIAL"
            else:
                return "FAILED"
        
        # Fallback to original status if no failure analysis
        return baseline_data.get("execution_status", "Unknown")
    
    def _analyze_termination_info(self, baseline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how the conversation terminated."""
        messages = baseline_data.get("messages", [])
        if not messages:
            return {"type": "unknown", "reason": "No messages found"}
        
        last_message = messages[-1]
        msg_type = last_message.get("type", "")
        
        if msg_type == "ResultMessage":
            content = last_message.get("content", {})
            subtype = content.get("subtype", "")
            duration_ms = content.get("duration_ms", 0)
            num_turns = content.get("num_turns", 0)
            
            if subtype == "error_max_turns":
                return {
                    "type": "max_turns_reached",
                    "reason": f"Maximum turns limit reached ({num_turns} turns)",
                    "duration_ms": duration_ms,
                    "num_turns": num_turns
                }
            elif subtype == "success":
                return {
                    "type": "normal_completion", 
                    "reason": "Conversation completed normally",
                    "duration_ms": duration_ms,
                    "num_turns": num_turns
                }
            elif "timeout" in subtype or "error" in subtype:
                return {
                    "type": "error_termination",
                    "reason": f"Terminated due to: {subtype}",
                    "duration_ms": duration_ms,
                    "num_turns": num_turns
                }
        elif msg_type == "AssistantMessage":
            return {
                "type": "incomplete",
                "reason": "Conversation ended with assistant response (may be incomplete)"
            }
        elif msg_type == "UserMessage":  
            return {
                "type": "incomplete",
                "reason": "Conversation ended with user message (response pending)"
            }
        
        return {
            "type": "unknown",
            "reason": f"Conversation ended with {msg_type}"
        }

    def _generate_baseline_html(self, baseline_data: Dict[str, Any], scenario_name: str) -> str:
        """Generate HTML content for baseline report."""
        
        # Extract key information
        scenario = baseline_data.get("scenario", scenario_name)
        execution_time = baseline_data.get("execution_time", "Unknown")
        user_intent = baseline_data.get("user_intent", "")
        status = self._evaluate_actual_status(baseline_data)
        messages = baseline_data.get("messages", [])
        tool_calls_summary = baseline_data.get("tool_calls_summary", [])
        termination_info = self._analyze_termination_info(baseline_data)
        mcpproxy_git_info = baseline_data.get("mcpproxy_git_info", {})
        
        # T022: Generate conversation HTML - try dialog_turns first, fallback to legacy messages
        conversation_html = self._render_dialog_turns_section(baseline_data)
        if not conversation_html:
            # Fallback to legacy message rendering if dialog_turns unavailable
            conversation_html = self._generate_conversation_html(messages, tool_calls_summary, termination_info, user_intent=user_intent)
        
        # Generate summary statistics  
        stats_html = self._generate_baseline_stats_html(baseline_data)
        
        # Generate termination info
        termination_html = self._generate_termination_info_html(termination_info)
        
        # Generate available tools info
        tools_html = self._generate_available_tools_html(baseline_data.get("available_tools", {}))

        # T034: Generate MCP tools section (separate from conversation flow)
        mcp_tools_html = self._render_mcp_tools_section(baseline_data)

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Baseline Report: {html.escape(scenario)}</title>
    {self._get_embedded_styles()}
    {self._get_embedded_scripts()}
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>🎯 MCP Baseline Report</h1>
            <div class="scenario-info">
                <h2>{html.escape(scenario)}</h2>
                <p class="execution-time">Recorded: {execution_time}</p>
                <p class="user-intent"><strong>User Intent:</strong> {html.escape(user_intent)}</p>
                <div class="mcpproxy-info">
                    <strong>MCPProxy Version:</strong> 
                    <code title="Full hash: {mcpproxy_git_info.get('git_hash', 'unknown')}">{mcpproxy_git_info.get('git_hash_short', 'unknown')}</code>
                    ({html.escape(mcpproxy_git_info.get('commit_message', 'unknown'))[:50]}{'...' if len(mcpproxy_git_info.get('commit_message', '')) > 50 else ''})
                    <span class="commit-date">{mcpproxy_git_info.get('commit_date', 'unknown')}</span>
                </div>
                <div class="status-badge status-{status.lower()}">{status}</div>
            </div>
        </header>
        
        {stats_html}

        {termination_html}

        {tools_html}

        {mcp_tools_html}

        <main class="conversation-container">
            <h3>📋 Conversation Log</h3>
            {conversation_html}
        </main>
        
        <footer class="report-footer">
            <p>Generated by MCP Evaluation System at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </footer>
    </div>
</body>
</html>"""

    def _align_dialog_turns_for_diff(
        self,
        current_data: Dict[str, Any],
        baseline_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """T052-T054: Align dialog turns from current and baseline for diff display.

        Uses position-based alignment to match turns and detect differences.

        Args:
            current_data: Current execution data with dialog_turns
            baseline_data: Baseline execution data with dialog_turns

        Returns:
            List of alignment dicts with keys:
            - position: int
            - current_turn: DialogTurn dict or None
            - baseline_turn: DialogTurn dict or None
            - diff_type: "ADDED" | "REMOVED" | "MODIFIED" | "UNCHANGED"
        """
        current_turns = current_data.get("dialog_turns", [])
        baseline_turns = baseline_data.get("dialog_turns", [])

        alignments = []
        max_len = max(len(current_turns), len(baseline_turns))

        for i in range(max_len):
            current_turn = current_turns[i] if i < len(current_turns) else None
            baseline_turn = baseline_turns[i] if i < len(baseline_turns) else None

            # T054: Determine diff type
            if current_turn and baseline_turn:
                # Both present - check if modified
                current_content = current_turn.get("content", "")
                baseline_content = baseline_turn.get("content", "")
                current_type = current_turn.get("turn_type", "")
                baseline_type = baseline_turn.get("turn_type", "")

                if current_content == baseline_content and current_type == baseline_type:
                    diff_type = "UNCHANGED"
                else:
                    diff_type = "MODIFIED"
            elif current_turn and not baseline_turn:
                # Only in current - added
                diff_type = "ADDED"
            elif baseline_turn and not current_turn:
                # Only in baseline - removed
                diff_type = "REMOVED"
            else:
                # Should not happen
                continue

            alignments.append({
                "position": i,
                "current_turn": current_turn,
                "baseline_turn": baseline_turn,
                "diff_type": diff_type
            })

        return alignments

    def _generate_dialog_turn_diff_html(
        self,
        current_data: Dict[str, Any],
        baseline_data: Dict[str, Any]
    ) -> str:
        """T055-T060: Generate side-by-side dialog turn comparison with diff highlighting.

        Args:
            current_data: Current execution data
            baseline_data: Baseline execution data

        Returns:
            HTML string with side-by-side turn comparison
        """
        alignments = self._align_dialog_turns_for_diff(current_data, baseline_data)

        if not alignments:
            return '<p class="empty-conversation">No dialog turns to compare</p>'

        # T059: Calculate diff summary stats
        added_count = sum(1 for a in alignments if a["diff_type"] == "ADDED")
        removed_count = sum(1 for a in alignments if a["diff_type"] == "REMOVED")
        modified_count = sum(1 for a in alignments if a["diff_type"] == "MODIFIED")
        unchanged_count = sum(1 for a in alignments if a["diff_type"] == "UNCHANGED")

        # T060: Filter controls
        filter_controls = f'''
        <div class="diff-filter-controls">
            <label><input type="checkbox" id="show-added" checked onclick="toggleDiffFilter('added')">
                <span class="diff-badge diff-added">{added_count} Added</span></label>
            <label><input type="checkbox" id="show-removed" checked onclick="toggleDiffFilter('removed')">
                <span class="diff-badge diff-removed">{removed_count} Removed</span></label>
            <label><input type="checkbox" id="show-modified" checked onclick="toggleDiffFilter('modified')">
                <span class="diff-badge diff-modified">{modified_count} Modified</span></label>
            <label><input type="checkbox" id="show-unchanged" checked onclick="toggleDiffFilter('unchanged')">
                <span class="diff-badge diff-unchanged">{unchanged_count} Unchanged</span></label>
        </div>'''

        # T056: Side-by-side layout
        html_parts = []
        html_parts.append('<div class="diff-side-by-side">')

        for alignment in alignments:
            diff_type = alignment["diff_type"]
            current_turn = alignment["current_turn"]
            baseline_turn = alignment["baseline_turn"]

            # CSS class for filtering
            filter_class = f"turn-{diff_type.lower()}"

            html_parts.append(f'<div class="diff-row {filter_class}">')

            # Left column - Current
            html_parts.append('<div class="diff-column diff-current">')
            if current_turn:
                turn_html = self._render_single_turn_for_diff(current_turn, diff_type, is_current=True, other_turn=baseline_turn)
                html_parts.append(turn_html)
            else:
                html_parts.append('<div class="turn-placeholder">Turn removed</div>')
            html_parts.append('</div>')

            # Right column - Baseline
            html_parts.append('<div class="diff-column diff-baseline">')
            if baseline_turn:
                turn_html = self._render_single_turn_for_diff(baseline_turn, diff_type, is_current=False, other_turn=current_turn)
                html_parts.append(turn_html)
            else:
                html_parts.append('<div class="turn-placeholder">Turn added</div>')
            html_parts.append('</div>')

            html_parts.append('</div>')  # Close diff-row

        html_parts.append('</div>')  # Close diff-side-by-side

        return filter_controls + "\n".join(html_parts)

    def _render_single_turn_for_diff(
        self,
        turn: Dict[str, Any],
        diff_type: str,
        is_current: bool,
        other_turn: Optional[Dict[str, Any]] = None
    ) -> str:
        """Helper to render a single turn in diff view with highlighting.

        Args:
            turn: The dialog turn to render
            diff_type: ADDED, REMOVED, MODIFIED, UNCHANGED
            is_current: True if this is current execution, False if baseline
            other_turn: The corresponding turn from other side (for MODIFIED diffs)

        Returns:
            HTML string for the turn
        """
        turn_type = turn.get("turn_type", "UNKNOWN")
        content = turn.get("content", "")
        timestamp = turn.get("timestamp", "")
        actor = turn.get("actor", "Unknown")

        # Determine styling based on turn type
        if turn_type == "USER_MESSAGE":
            message_class = "user-message"
            icon = "👤"
            label = "User"
        elif turn_type == "AGENT_MESSAGE":
            message_class = "assistant-message"
            icon = "🤖"
            label = "Assistant"
        elif turn_type == "TOOL_CALL":
            message_class = "tool-message"
            icon = "🔧"
            tool_name = turn.get("metadata", {}).get("tool_name", "unknown")
            label = f"Tool: {tool_name}"
        elif turn_type == "TOOL_RESULT":
            message_class = "tool-message"
            icon = "📊"
            label = "Result"
        else:
            message_class = "message"
            icon = "📝"
            label = turn_type

        # T057: Color-coded diff highlighting
        diff_class = ""
        if diff_type == "ADDED":
            diff_class = "turn-added"
        elif diff_type == "REMOVED":
            diff_class = "turn-removed"
        elif diff_type == "MODIFIED":
            diff_class = "turn-modified"
        else:
            diff_class = "turn-unchanged"

        # T058: Character-level diff for MODIFIED turns
        content_html = html.escape(content)
        if diff_type == "MODIFIED" and other_turn:
            other_content = other_turn.get("content", "")
            content_html = self._highlight_content_diff(content, other_content, is_current)

        # Format timestamp
        timestamp_str = timestamp
        if timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                timestamp_str = dt.strftime("%H:%M:%S")
            except:
                timestamp_str = str(timestamp)[:8]

        return f'''
        <div class="message {message_class} {diff_class}">
            <div class="message-header">
                <span class="message-type">{icon} {html.escape(label)}</span>
                <span class="timestamp">{html.escape(timestamp_str)}</span>
            </div>
            <div class="message-content">{content_html}</div>
        </div>'''

    def _highlight_content_diff(self, current: str, baseline: str, is_current: bool) -> str:
        """T058: Highlight character-level differences using difflib.

        Args:
            current: Current content
            baseline: Baseline content
            is_current: True if rendering current side, False if baseline

        Returns:
            HTML with diff highlighting
        """
        import difflib

        if current == baseline:
            return html.escape(current)

        # Use difflib to find differences
        matcher = difflib.SequenceMatcher(None, baseline, current)
        result = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Unchanged text
                text = current[j1:j2] if is_current else baseline[i1:i2]
                result.append(html.escape(text))
            elif tag == 'replace':
                # Modified text
                text = current[j1:j2] if is_current else baseline[i1:i2]
                result.append(f'<span class="diff-highlight">{html.escape(text)}</span>')
            elif tag == 'insert':
                # Added text (only in current)
                if is_current:
                    result.append(f'<span class="diff-highlight">{html.escape(current[j1:j2])}</span>')
            elif tag == 'delete':
                # Removed text (only in baseline)
                if not is_current:
                    result.append(f'<span class="diff-highlight">{html.escape(baseline[i1:i2])}</span>')

        return ''.join(result)

    def _generate_comparison_html(self, 
                                current_data: Dict[str, Any], 
                                baseline_data: Dict[str, Any],
                                comparison_result: Dict[str, Any], 
                                scenario_name: str) -> str:
        """Generate HTML content for comparison report."""
        
        # Extract key information
        scenario = current_data.get("scenario", scenario_name)
        current_status = self._evaluate_actual_status(current_data)
        baseline_status = self._evaluate_actual_status(baseline_data)
        
        # Extract git info from both current and baseline
        current_git_info = current_data.get("mcpproxy_git_info", {})
        baseline_git_info = baseline_data.get("mcpproxy_git_info", {})
        
        # Get user intents
        current_user_intent = current_data.get("user_intent", "")
        baseline_user_intent = baseline_data.get("user_intent", "")
        
        # Generate side-by-side conversation HTML
        comparison_html = self._generate_comparison_conversation_html(
            current_data, baseline_data, comparison_result
        )
        
        # Generate comparison summary
        summary_html = self._generate_comparison_summary_html(comparison_result)
        
        # Generate per-invocation results if available
        invocation_results_html = self._generate_invocation_results_html(comparison_result)

        # T061: Generate dialog turn comparison
        dialog_turn_diff_html = self._generate_dialog_turn_diff_html(current_data, baseline_data)

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Comparison Report: {html.escape(scenario)}</title>
    {self._get_embedded_styles()}
    {self._get_embedded_scripts()}
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>⚖️ MCP Comparison Report</h1>
            <div class="scenario-info">
                <h2>{html.escape(scenario)}</h2>
                <p class="user-intent"><strong>User Intent:</strong> {html.escape(current_user_intent)}</p>
                <div class="git-info-comparison">
                    <div class="current-version">
                        <strong>Current MCPProxy:</strong> 
                        <code title="Full hash: {current_git_info.get('git_hash', 'unknown')}">{current_git_info.get('git_hash_short', 'unknown')}</code>
                        ({html.escape(current_git_info.get('commit_message', 'unknown'))[:40]}{'...' if len(current_git_info.get('commit_message', '')) > 40 else ''})
                        <span class="commit-date">{current_git_info.get('commit_date', 'unknown')}</span>
                    </div>
                    <div class="baseline-version">
                        <strong>Baseline MCPProxy:</strong> 
                        <code title="Full hash: {baseline_git_info.get('git_hash', 'unknown')}">{baseline_git_info.get('git_hash_short', 'unknown')}</code>
                        ({html.escape(baseline_git_info.get('commit_message', 'unknown'))[:40]}{'...' if len(baseline_git_info.get('commit_message', '')) > 40 else ''})
                        <span class="commit-date">{baseline_git_info.get('commit_date', 'unknown')}</span>
                    </div>
                </div>
                <div class="comparison-badges">
                    <span class="status-badge status-{current_status.lower()}">Current: {current_status}</span>
                    <span class="status-badge status-{baseline_status.lower()}">Baseline: {baseline_status}</span>
                </div>
            </div>
        </header>
        
        {summary_html}

        {invocation_results_html}

        <section class="dialog-turn-comparison">
            <h3>🔄 Dialog Turn Comparison</h3>
            {dialog_turn_diff_html}
        </section>

        <main class="comparison-container">
            <h3>📊 Execution Comparison</h3>
            {comparison_html}
        </main>
        
        <footer class="report-footer">
            <p>Generated by MCP Evaluation System at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </footer>
    </div>
</body>
</html>"""

    def _generate_termination_info_html(self, termination_info: Dict[str, Any]) -> str:
        """Generate HTML for termination information."""
        termination_type = termination_info.get("type", "unknown")
        reason = termination_info.get("reason", "Unknown")
        duration_ms = termination_info.get("duration_ms", 0)
        num_turns = termination_info.get("num_turns", 0)
        
        # Determine the styling based on termination type
        if termination_type == "normal_completion":
            badge_class = "success"
            icon = "✅"
        elif termination_type == "max_turns_reached":
            badge_class = "warning" 
            icon = "⚠️"
        elif termination_type == "error_termination":
            badge_class = "error"
            icon = "❌"
        else:
            badge_class = "unknown"
            icon = "❓"
        
        duration_str = f"{duration_ms/1000:.1f}s" if duration_ms > 0 else "Unknown"
        
        return f"""
        <section class="stats-container">
            <h3>🏁 Conversation Termination</h3>
            <div class="termination-info">
                <div class="termination-badge status-{badge_class}">
                    {icon} {reason}
                </div>
                <div class="termination-details">
                    <span><strong>Duration:</strong> {duration_str}</span>
                    {f'<span><strong>Turns:</strong> {num_turns}</span>' if num_turns > 0 else ''}
                </div>
            </div>
        </section>
        """

    def _extract_mcp_tools_from_turns(self, baseline_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract MCP tool invocations from dialog_turns.

        Filters dialog_turns to find TOOL_CALL turns where the tool name starts with 'mcp__'.
        Pairs each tool call with its corresponding tool result for display.

        Args:
            baseline_data: Dictionary containing detailed_log.json data with dialog_turns field

        Returns:
            List of dicts with {'call': tool_call_turn, 'result': tool_result_turn} for each MCP tool
        """
        dialog_turns = baseline_data.get("dialog_turns", [])
        if not dialog_turns:
            return []

        mcp_tools = []
        tool_call_map = {}  # Map tool_use_id to tool_call_turn

        # First pass: collect all MCP tool calls
        for turn in dialog_turns:
            if turn.get("turn_type") == "TOOL_CALL":
                metadata = turn.get("metadata", {})
                tool_name = metadata.get("tool_name", "")

                # Check if this is an MCP tool (starts with mcp__)
                if tool_name.startswith("mcp__"):
                    tool_use_id = metadata.get("tool_use_id", "")
                    tool_call_map[tool_use_id] = turn

        # Second pass: match tool results with their calls
        for turn in dialog_turns:
            if turn.get("turn_type") == "TOOL_RESULT":
                metadata = turn.get("metadata", {})
                tool_use_id = metadata.get("tool_use_id", "")

                # If this result corresponds to an MCP tool call, pair them
                if tool_use_id in tool_call_map:
                    mcp_tools.append({
                        'call': tool_call_map[tool_use_id],
                        'result': turn
                    })
                    # Remove from map so we don't match it again
                    del tool_call_map[tool_use_id]

        # Handle tool calls without results (still pending or failed)
        for tool_use_id, call_turn in tool_call_map.items():
            mcp_tools.append({
                'call': call_turn,
                'result': None  # No result available
            })

        return mcp_tools

    def _render_mcp_tools_section(self, baseline_data: Dict[str, Any]) -> str:
        """Render MCP tools in a dedicated section separate from dialog turns.

        Displays all MCP tool invocations with tool name, input parameters (formatted JSON),
        result preview, and success/failure indicators.

        Args:
            baseline_data: Dictionary containing detailed_log.json data

        Returns:
            HTML string with rendered MCP tools section, or empty string if no MCP tools
        """
        mcp_tools = self._extract_mcp_tools_from_turns(baseline_data)

        # T069: Edge case - dialog_turns present but no MCP tools found
        dialog_turns = baseline_data.get("dialog_turns", [])
        tool_calls_summary = baseline_data.get("tool_calls_summary", [])

        if not mcp_tools:
            # Check if this is anomalous (dialog present but no tools)
            if dialog_turns:
                return '''
        <section class="mcp-tools-section">
            <h3>🔧 MCP Tools Invoked</h3>
            <div class="status-badge status-warning" style="display: block; margin: 10px 0;">
                ⚠️ Warning: Conversation recorded but no MCP tool invocations found
            </div>
            <p class="empty-conversation">
                This may indicate that the agent didn't use any MCP tools during the conversation,
                or tool call logging failed.
            </p>
        </section>'''
            else:
                return ""  # No dialog turns and no MCP tools - normal empty state

        # T033: Calculate summary statistics
        total_count = len(mcp_tools)
        successful_count = sum(1 for tool in mcp_tools
                             if tool['result'] and not tool['result'].get('metadata', {}).get('is_error', False))
        failed_count = sum(1 for tool in mcp_tools
                         if tool['result'] and tool['result'].get('metadata', {}).get('is_error', False))

        html_parts = []
        html_parts.append(f'''
        <section class="mcp-tools-section">
            <h3>🔧 MCP Tools Invoked: {total_count} total, {successful_count} successful, {failed_count} failed</h3>
            <div class="mcp-tools-grid">''')

        for idx, tool in enumerate(mcp_tools):
            call_turn = tool['call']
            result_turn = tool['result']

            # Extract tool information from metadata
            call_metadata = call_turn.get('metadata', {})
            tool_name = call_metadata.get('tool_name', 'unknown_tool')
            tool_input = call_metadata.get('tool_input', {})
            tool_use_id = call_metadata.get('tool_use_id', f'tool_{idx}')

            # T031: Determine success/failure indicator
            is_error = False
            if result_turn:
                result_metadata = result_turn.get('metadata', {})
                is_error = result_metadata.get('is_error', False)

            success_icon = "❌" if is_error else "✅"
            status_class = "tool-failed" if is_error else "tool-success"

            # T030: Format input parameters with JSON syntax highlighting
            formatted_input = self._format_json_with_syntax_highlighting(tool_input)

            # T032: Result preview (first 500 chars)
            result_preview_html = ""
            if result_turn:
                result_content = result_turn.get('content', '')
                result_str = str(result_content)

                if len(result_str) > 500:
                    preview = html.escape(result_str[:500])
                    full = html.escape(result_str)
                    result_preview_html = f'''
                    <div class="tool-result-preview">
                        <h5>📥 Result:</h5>
                        <div class="result-content">
                            <span id="result_{tool_use_id}_preview">{preview}...</span>
                            <span id="result_{tool_use_id}_full" style="display: none;">{full}</span>
                            <button class="expand-btn" onclick="toggleContent('result_{tool_use_id}')">Expand</button>
                        </div>
                    </div>'''
                else:
                    result_preview_html = f'''
                    <div class="tool-result-preview">
                        <h5>📥 Result:</h5>
                        <div class="result-content">{html.escape(result_str)}</div>
                    </div>'''
            else:
                result_preview_html = '<div class="tool-result-preview"><h5>📥 Result:</h5><p><em>No result available</em></p></div>'

            # T029: MCP tool badge with dark blue color
            html_parts.append(f'''
            <div class="mcp-tool-card {status_class}">
                <div class="tool-card-header">
                    <span class="tool-badge mcp-badge">MCP</span>
                    <span class="tool-name-display">{html.escape(tool_name)}</span>
                    <span class="status-indicator">{success_icon}</span>
                </div>
                <div class="tool-input-params">
                    <h5>📤 Input Parameters:</h5>
                    <pre class="json-code"><code class="language-json">{formatted_input}</code></pre>
                </div>
                {result_preview_html}
            </div>''')

        html_parts.append('''
            </div>
        </section>''')

        return "\n".join(html_parts)

    def _render_dialog_turns_section(self, baseline_data: Dict[str, Any]) -> str:
        """Render dialog turns from structured dialog logging.

        This method extracts dialog_turns from the detailed_log.json and prepares
        them for HTML rendering. Handles edge cases:
        - No dialog_turns field: Returns empty string for legacy fallback
        - Empty dialog_turns array: Displays "No dialog turns recorded" message

        Args:
            baseline_data: Dictionary containing detailed_log.json data with dialog_turns field

        Returns:
            HTML string with rendered dialog turns, or empty string if unavailable
        """
        # T068: Edge case - distinguish between missing field and empty array
        if "dialog_turns" not in baseline_data:
            # No field at all - return empty for backward compatibility (legacy fallback)
            return ""

        dialog_turns = baseline_data.get("dialog_turns", [])

        # T068: Edge case - dialog_turns exists but is empty
        if not dialog_turns:
            return '''
        <section class="stats-container">
            <h3>💬 Conversation Dialog</h3>
            <p class="empty-conversation">⚠️ No dialog turns recorded in this session</p>
        </section>'''

        # T015: Sort dialog turns chronologically by turn_id
        sorted_turns = sorted(dialog_turns, key=lambda t: t.get("turn_id", 0))

        # Build HTML for all dialog turns
        html_parts = []
        html_parts.append('<div class="conversation">')

        for turn in sorted_turns:
            turn_id = turn.get("turn_id", 0)
            timestamp = turn.get("timestamp", "")
            turn_type = turn.get("turn_type", "UNKNOWN")
            actor = turn.get("actor", "Unknown")
            content = turn.get("content", "")
            metadata = turn.get("metadata", {})

            # T016: Turn-type-specific HTML rendering with color coding
            if turn_type == "USER_MESSAGE":
                # Blue border for user messages
                message_class = "user-message"
                icon = "👤"
                label = "User"
            elif turn_type == "AGENT_MESSAGE":
                # Green border for agent messages
                message_class = "assistant-message"
                icon = "🤖"
                label = "Assistant"
            elif turn_type == "TOOL_CALL":
                # Orange border for tool calls
                message_class = "tool-message"
                icon = "🔧"
                tool_name = metadata.get("tool_name", "unknown_tool")
                label = f"Tool Call: {tool_name}"
            elif turn_type == "TOOL_RESULT":
                # Orange border for tool results
                message_class = "tool-message"
                icon = "📊"
                tool_id = metadata.get("tool_use_id", "unknown")
                label = f"Tool Result: {tool_id[:12]}..."
            elif turn_type == "CLARIFICATION_REQUEST":
                # User-style for clarification requests
                message_class = "user-message"
                icon = "❓"
                label = "Clarification Request"
            elif turn_type == "CLARIFICATION_RESPONSE":
                # Agent-style for clarification responses
                message_class = "assistant-message"
                icon = "💡"
                label = "Clarification Response"
            else:
                # Generic styling for unknown turn types
                message_class = "message"
                icon = "📝"
                label = turn_type

            # T017: Format timestamp for human readability
            timestamp_str = timestamp
            if timestamp:
                try:
                    from datetime import datetime
                    # Handle ISO-8601 format with 'Z' or '+00:00' timezone
                    dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                    timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    # If parsing fails, use raw timestamp
                    timestamp_str = str(timestamp)[:19]  # Truncate to reasonable length
            else:
                timestamp_str = "No timestamp"

            # T019: Implement content truncation for long messages
            content_str = str(content)
            truncate_threshold = 1000

            # T020: Prepare metadata display (collapsed by default)
            metadata_html = ""
            if metadata:
                metadata_id = f"metadata_{turn_id}"
                metadata_json = self._format_json_with_syntax_highlighting(metadata)
                metadata_html = f'''
                <div class="metadata-section">
                    <button class="metadata-toggle" onclick="toggleMetadata('{metadata_id}')">
                        <span id="icon-{metadata_id}">▶</span> Metadata
                    </button>
                    <div id="details-{metadata_id}" class="metadata-content" style="display: none;">
                        <pre>{metadata_json}</pre>
                    </div>
                </div>'''

            if len(content_str) > truncate_threshold:
                # Content needs truncation with "show more" functionality
                content_id = f"content_{turn_id}"
                preview = html.escape(content_str[:truncate_threshold])
                full = html.escape(content_str)

                html_parts.append(f'''
            <div class="message {message_class}">
                <div class="message-header">
                    <span class="message-type">{icon} {html.escape(label)}</span>
                    <span class="timestamp">{html.escape(timestamp_str)}</span>
                </div>
                <div class="message-content">
                    <span id="{content_id}_preview">{preview}...</span>
                    <span id="{content_id}_full" style="display: none;">{full}</span>
                    <button class="show-more-btn" onclick="toggleContent('{content_id}')">Show more</button>
                </div>
                {metadata_html}
            </div>''')
            else:
                # Content is short enough, no truncation needed
                html_parts.append(f'''
            <div class="message {message_class}">
                <div class="message-header">
                    <span class="message-type">{icon} {html.escape(label)}</span>
                    <span class="timestamp">{html.escape(timestamp_str)}</span>
                </div>
                <div class="message-content">{html.escape(content_str)}</div>
                {metadata_html}
            </div>''')

        html_parts.append('</div>')
        return "\n".join(html_parts)

    def _generate_conversation_html(self, messages: List[Dict], tool_calls_summary: List[Dict], termination_info: Optional[Dict] = None, similarity_scores: Optional[Dict] = None, mcp_similarity_scores: Optional[Dict] = None, user_intent: Optional[str] = None) -> str:
        """Generate HTML for conversation messages with expandable tool calls."""
        
        html_parts = []
        
        # Add the initial user message from user_intent if provided
        if user_intent:
            html_parts.append(f"""
            <div class="message user-message">
                <div class="message-header">
                    <span class="message-type">👤 User</span>
                    <span class="timestamp">Initial Request</span>
                </div>
                <div class="message-content">
                    {self._format_text_content(user_intent)}
                </div>
            </div>
            """)
        
        tool_call_index = 0
        mcp_tool_index = 0  # Separate counter for MCP tools only
        
        for message in messages:
            msg_type = message.get("type", "Unknown")
            content = message.get("content", {})
            timestamp = message.get("timestamp", "")
            
            if msg_type == "UserMessage":
                # Check if this is actually a tool result (misclassified)
                if isinstance(content, dict) and content.get("_type") == "UserMessage":
                    user_content = content.get("content", [])
                    if isinstance(user_content, list) and len(user_content) > 0:
                        first_item = user_content[0]
                        if isinstance(first_item, dict) and "tool_use_id" in first_item:
                            # This is a tool result, not a user message
                            if tool_call_index > 0:  # Make sure we have a tool call to attach this to
                                # Skip this - it should be handled by the tool call display
                                continue
                
                # Regular user message
                user_text = self._extract_text_from_content(content)
                html_parts.append(f"""
                <div class="message user-message">
                    <div class="message-header">
                        <span class="message-type">👤 User</span>
                        <span class="timestamp">{timestamp}</span>
                    </div>
                    <div class="message-content">
                        {self._format_text_content(user_text)}
                    </div>
                </div>
                """)
                
            elif msg_type == "AssistantMessage":
                # Assistant message - check for tool calls
                assistant_content = content.get("content", [])
                
                for content_item in assistant_content:
                    if isinstance(content_item, dict):
                        if "text" in content_item:
                            # Text response
                            html_parts.append(f"""
                            <div class="message assistant-message">
                                <div class="message-header">
                                    <span class="message-type">🤖 Assistant</span>
                                    <span class="timestamp">{timestamp}</span>
                                </div>
                                <div class="message-content">
                                    {self._format_text_content(content_item["text"])}
                                </div>
                            </div>
                            """)
                            
                        elif "name" in content_item and "input" in content_item:
                            # Tool call - find the corresponding result
                            tool_result = None
                            if tool_call_index < len(tool_calls_summary):
                                tool_result = tool_calls_summary[tool_call_index]
                            
                            # Look ahead for the tool result in the next UserMessage
                            tool_result_content = self._find_tool_result(messages, content_item.get("id"), tool_call_index)
                            
                            # Get similarity score for this tool call if available (only for MCP tools)
                            similarity_score = None
                            tool_name = content_item.get("name", "")
                            if tool_name.startswith("mcp__") and mcp_similarity_scores and mcp_tool_index in mcp_similarity_scores:
                                similarity_score = mcp_similarity_scores[mcp_tool_index]
                                mcp_tool_index += 1  # Only increment for MCP tools
                            
                            html_parts.append(self._generate_tool_call_html(content_item, tool_result, tool_result_content, similarity_score))
                            tool_call_index += 1
        
        return "\n".join(html_parts)
        
    def _find_tool_result(self, messages: List[Dict], tool_id: str, message_index: int) -> Optional[str]:
        """Find the tool result content for a given tool call."""
        # Look in subsequent messages for tool result
        for i in range(message_index, len(messages)):
            message = messages[i]
            if message.get("type") == "UserMessage":
                content = message.get("content", {})
                if isinstance(content, dict) and content.get("_type") == "UserMessage":
                    user_content = content.get("content", [])
                    if isinstance(user_content, list):
                        for item in user_content:
                            if isinstance(item, dict) and item.get("tool_use_id") == tool_id:
                                return item.get("content", [])
        return None
        
    def _format_text_content(self, text: str) -> str:
        """Format text content by handling newlines and escaping HTML."""
        if not text:
            return ""
        
        # Replace literal \n with actual line breaks, escape HTML, then convert to <br>
        formatted_text = html.escape(str(text))
        formatted_text = formatted_text.replace('\\n', '\n')  # Convert literal \n to newlines
        formatted_text = formatted_text.replace('\n', '<br>')  # Convert newlines to HTML breaks
        
        return formatted_text
        
    def _generate_tool_call_html(self, tool_call: Dict, tool_summary: Optional[Dict], tool_result_content: Optional[List] = None, similarity_score: Optional[float] = None) -> str:
        """Generate expandable HTML for tool call."""
        
        tool_name = tool_call.get("name", "unknown_tool")
        tool_input = tool_call.get("input", {})
        tool_id = tool_call.get("id", "unknown_id")
        
        # Create preview of parameters
        param_preview = self._create_param_preview(tool_input)
        
        # Create similarity badge if score is provided
        similarity_badge = ""
        if similarity_score is not None:
            similarity_class = self._get_score_class(similarity_score)
            similarity_badge = f'<span class="similarity-badge score-{similarity_class}">Sim: {similarity_score:.3f}</span>'
        
        # Process tool result content
        result_html = ""
        if tool_result_content:
            result_html = self._format_tool_result_content(tool_result_content)
        elif tool_summary:
            # Fallback to summary if available
            result_preview = tool_summary.get("result_preview", "")
            full_result = self._format_json_with_syntax_highlighting(tool_summary.get("result", {}))
            result_html = f"""
                <div class="result-preview">{html.escape(result_preview)}</div>
                <pre class="json-code"><code class="language-json">{full_result}</code></pre>
            """
        
        # Determine tool category for filtering
        tool_class = ""
        if tool_name == "TodoWrite":
            tool_class = "tool-todowrite"
        elif not tool_name.startswith("mcp__"):
            tool_class = "tool-non-mcp"
        else:
            tool_class = "tool-mcp"
        
        return f"""
        <div class="message tool-message {tool_class}">
            <div class="tool-header" onclick="toggleToolCall('{tool_id}')">
                <span class="tool-icon">🔧</span>
                <span class="tool-name">{html.escape(tool_name)}</span>
                <span class="tool-params">({param_preview})</span>
                {similarity_badge}
                <span class="expand-icon" id="icon-{tool_id}">▶</span>
            </div>
            <div class="tool-details" id="details-{tool_id}" style="display: none;">
                <div class="tool-section">
                    <h4>📤 Tool Input:</h4>
                    <pre class="json-code"><code class="language-json">{self._format_json_with_syntax_highlighting(tool_input)}</code></pre>
                </div>
                {f'''
                <div class="tool-section">
                    <h4>📥 Tool Response:</h4>
                    {result_html}
                </div>
                ''' if result_html else ''}
            </div>
        </div>
        """
        
    def _create_param_preview(self, params: Dict) -> str:
        """Create a short preview of tool parameters."""
        if not params:
            return ""
            
        preview_parts = []
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 30:
                preview_parts.append(f'{key}="{value[:27]}..."')
            elif isinstance(value, (list, dict)):
                preview_parts.append(f'{key}=<{type(value).__name__}>')
            else:
                preview_parts.append(f'{key}={repr(value)}')
                
        return ", ".join(preview_parts[:3])  # Show max 3 params in preview
        
    def _format_json_with_syntax_highlighting(self, data: Any) -> str:
        """Format JSON with basic syntax highlighting using HTML."""
        if data is None:
            return ""
            
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Apply basic syntax highlighting
        json_str = html.escape(json_str)
        
        # Color strings (green)
        json_str = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)"(\s*:)', 
                         r'<span class="json-key">"\1"</span>\3', json_str)
        json_str = re.sub(r':\s*"([^"\\]*(\\.[^"\\]*)*)"', 
                         r': <span class="json-string">"\1"</span>', json_str)
        
        # Color numbers (blue)
        json_str = re.sub(r'\b(\d+\.?\d*)\b', 
                         r'<span class="json-number">\1</span>', json_str)
        
        # Color booleans and null (purple)
        json_str = re.sub(r'\b(true|false|null)\b', 
                         r'<span class="json-boolean">\1</span>', json_str)
        
        # Color brackets (gray)
        json_str = re.sub(r'([{}[\]])', 
                         r'<span class="json-bracket">\1</span>', json_str)
        
        return json_str
        
    def _format_tool_result_content(self, content: List) -> str:
        """Format tool result content for display."""
        if not content:
            return ""
            
        result_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_content = item.get("text", "")
                    # Try to parse as JSON for better formatting
                    try:
                        parsed_json = json.loads(text_content)
                        formatted_json = self._format_json_with_syntax_highlighting(parsed_json)
                        result_parts.append(f'<pre class="json-code"><code class="language-json">{formatted_json}</code></pre>')
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, display as text
                        result_parts.append(f'<div class="text-content">{self._format_text_content(text_content)}</div>')
                else:
                    # Other types, display as JSON
                    formatted_item = self._format_json_with_syntax_highlighting(item)
                    result_parts.append(f'<pre class="json-code"><code class="language-json">{formatted_item}</code></pre>')
            else:
                # Non-dict items
                result_parts.append(f'<div class="text-content">{self._format_text_content(str(item))}</div>')
                
        return "\n".join(result_parts)
        
    def _generate_baseline_stats_html(self, baseline_data: Dict[str, Any]) -> str:
        """Generate statistics summary for baseline data."""
        
        tool_calls_count = len(baseline_data.get("tool_calls_summary", []))
        messages_count = len(baseline_data.get("messages", []))
        status = baseline_data.get("execution_status", "Unknown")
        
        return f"""
        <section class="stats-container">
            <h3>📈 Execution Statistics</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{tool_calls_count}</div>
                    <div class="stat-label">Tool Calls</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{messages_count}</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{status}</div>
                    <div class="stat-label">Status</div>
                </div>
            </div>
        </section>
        """
        
    def _generate_comparison_summary_html(self, comparison_result: Dict[str, Any]) -> str:
        """Generate comparison summary with scores and metrics."""
        
        # Extract scores from evaluation_metrics if available
        eval_metrics = comparison_result.get("evaluation_metrics", {})
        overall_score = eval_metrics.get("overall_score", comparison_result.get("overall_score", 0.0))
        trajectory_score = eval_metrics.get("tool_trajectory_score", comparison_result.get("trajectory_score", 0.0))
        
        status = comparison_result.get("status", "Unknown")
        
        # Get tool counts from current and baseline execution sections
        current_exec = comparison_result.get("current_execution", {})
        baseline_exec = comparison_result.get("baseline_execution", {})
        current_tools = current_exec.get("tool_calls_count", 0)
        baseline_tools = baseline_exec.get("tool_calls_count", 0)
        
        status_color = "red" if status == "BROKEN" else "yellow" if status == "WARNING" else "green"
        
        return f"""
        <section class="comparison-summary">
            <h3>📊 Comparison Results</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value score-{self._get_score_class(overall_score)}">{overall_score:.3f}</div>
                    <div class="summary-label">Overall Score</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value score-{self._get_score_class(trajectory_score)}">{trajectory_score:.3f}</div>
                    <div class="summary-label">Trajectory Score</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value status-{status_color}">{status}</div>
                    <div class="summary-label">Status</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{current_tools} / {baseline_tools}</div>
                    <div class="summary-label">Tools (Current/Baseline)</div>
                </div>
            </div>
        </section>
        """
        
    def _generate_invocation_results_html(self, comparison_result: Dict[str, Any]) -> str:
        """Generate HTML for per-invocation results with similarity scores."""
        
        per_invocation_results = comparison_result.get("per_invocation_results", [])
        if not per_invocation_results:
            return ""
        
        results_html = ""
        for result in per_invocation_results:
            invocation = result.get("invocation", 0)
            score = result.get("score", 0.0)
            details = result.get("details", "")
            actual_tools = result.get("actual_tools", [])
            expected_tools = result.get("expected_tools", [])
            
            score_class = self._get_score_class(score)
            
            # Generate tool comparison
            tool_comparison_html = ""
            if actual_tools and expected_tools:
                actual_tool = actual_tools[0]
                expected_tool = expected_tools[0]
                
                actual_name = actual_tool.get("name", "unknown")
                expected_name = expected_tool.get("name", "unknown")
                similarity = actual_tool.get("similarity", score)
                
                tool_comparison_html = f"""
                <div class="tool-comparison">
                    <div class="tool-match">
                        <span class="tool-name">Current: {html.escape(actual_name)}</span>
                        <span class="similarity-badge score-{self._get_score_class(similarity)}">Similarity: {similarity:.3f}</span>
                    </div>
                    <div class="tool-match">
                        <span class="tool-name">Expected: {html.escape(expected_name)}</span>
                    </div>
                </div>
                """
            elif actual_tools:
                actual_tool = actual_tools[0]
                actual_name = actual_tool.get("name", "unknown")
                tool_comparison_html = f"""
                <div class="tool-comparison">
                    <div class="tool-match extra">
                        <span class="tool-name">Extra: {html.escape(actual_name)}</span>
                        <span class="status-badge status-warning">EXTRA CALL</span>
                    </div>
                </div>
                """
            elif expected_tools:
                expected_tool = expected_tools[0]
                expected_name = expected_tool.get("name", "unknown")
                tool_comparison_html = f"""
                <div class="tool-comparison">
                    <div class="tool-match missing">
                        <span class="tool-name">Missing: {html.escape(expected_name)}</span>
                        <span class="status-badge status-error">MISSING CALL</span>
                    </div>
                </div>
                """
            
            results_html += f"""
            <div class="invocation-result">
                <div class="invocation-header">
                    <span class="invocation-number">Invocation {invocation}</span>
                    <span class="invocation-score score-{score_class}">{score:.3f}</span>
                </div>
                <div class="invocation-details">
                    <p class="invocation-description">{html.escape(details)}</p>
                    {tool_comparison_html}
                </div>
            </div>
            """
        
        return f"""
        <section class="comparison-summary">
            <h3>🔍 Per-Invocation Analysis</h3>
            <div class="invocation-results">
                {results_html}
            </div>
        </section>
        """
        
    def _get_score_class(self, score: float) -> str:
        """Get CSS class for score coloring."""
        if score >= 0.8:
            return "good"
        elif score >= 0.5:
            return "warning"
        else:
            return "bad"
            
    def _generate_comparison_conversation_html(self, current_data: Dict, baseline_data: Dict, comparison_result: Optional[Dict] = None) -> str:
        """Generate side-by-side comparison of conversations."""
        
        current_messages = current_data.get("messages", [])
        baseline_messages = baseline_data.get("messages", [])
        
        # Get user intents for both executions
        current_user_intent = current_data.get("user_intent", "")
        baseline_user_intent = baseline_data.get("user_intent", "")
        
        # Create MCP tool similarity mapping
        mcp_similarity_scores = {}
        if comparison_result and "per_invocation_results" in comparison_result:
            for i, result in enumerate(comparison_result["per_invocation_results"]):
                # Extract similarity from actual_tools if available
                if result.get("actual_tools") and len(result["actual_tools"]) > 0:
                    actual_tool = result["actual_tools"][0]
                    if "similarity" in actual_tool:
                        mcp_similarity_scores[i] = actual_tool["similarity"]
        
        # Generate conversations for both sides with user intents
        current_html = self._generate_conversation_html(current_messages, current_data.get("tool_calls_summary", []), mcp_similarity_scores=mcp_similarity_scores, user_intent=current_user_intent)
        baseline_html = self._generate_conversation_html(baseline_messages, baseline_data.get("tool_calls_summary", []), user_intent=baseline_user_intent)
        
        # Handle empty cases
        if not current_html.strip():
            current_html = '<div class="empty-conversation">No conversation data available</div>'
        if not baseline_html.strip():
            baseline_html = '<div class="empty-conversation">No conversation data available</div>'
        
        return f"""
        <div class="tool-filter-controls">
            <h4>🔧 Tool Display Filters</h4>
            <label class="filter-checkbox">
                <input type="checkbox" id="show-todowrite" onchange="toggleToolFilter('todowrite')"> 
                Show TodoWrite calls
            </label>
            <label class="filter-checkbox">
                <input type="checkbox" id="show-non-mcp" onchange="toggleToolFilter('non-mcp')"> 
                Show non-MCP tools (Bash, Read, Write, etc.)
            </label>
        </div>
        <div class="side-by-side">
            <div class="side current-side">
                <h4>📊 Current Execution</h4>
                {current_html}
            </div>
            <div class="side baseline-side">
                <h4>📋 Baseline</h4>
                {baseline_html}
            </div>
        </div>
        """
        
    def _extract_text_from_content(self, content: Any) -> str:
        """Extract readable text from various content formats."""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            if "content" in content:
                return self._extract_text_from_content(content["content"])
            elif "text" in content:
                return content["text"]
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "content" in item:
                    text_parts.append(str(item["content"]))
                elif isinstance(item, str):
                    text_parts.append(item)
            return " ".join(text_parts)
        return str(content)
        
    def _get_embedded_styles(self) -> str:
        """Return embedded CSS styles."""
        return """
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f7fa;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 8px;
}

.report-header {
    background: white;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.report-header h1 {
    color: #2d3748;
    margin-bottom: 8px;
    font-size: 1.8em;
}

.scenario-info h2 {
    color: #4a5568;
    margin-bottom: 6px;
    font-size: 1.4em;
}

.execution-time {
    color: #718096;
    margin-bottom: 6px;
    font-size: 0.9em;
}

.user-intent {
    background: #f7fafc;
    padding: 8px;
    border-left: 3px solid #3182ce;
    margin: 8px 0;
    border-radius: 3px;
    font-size: 0.95em;
}

.mcpproxy-info {
    background: #f0fff4;
    padding: 6px 8px;
    border-left: 3px solid #38a169;
    margin: 6px 0;
    border-radius: 3px;
    font-size: 0.85em;
    color: #2d5a3d;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.mcpproxy-info code {
    background: #e6fffa;
    padding: 2px 4px;
    border-radius: 2px;
    font-weight: 600;
    color: #1a202c;
    cursor: help;
}

.mcpproxy-info .commit-date {
    color: #68d391;
    font-size: 0.8em;
    margin-left: 8px;
}

.status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75em;
    margin: 3px;
}

.status-success { background: #c6f6d5; color: #22543d; }
.status-error { background: #fed7d7; color: #742a2a; }
.status-warning { background: #fef5e7; color: #975a16; }
.status-unknown { background: #e2e8f0; color: #4a5568; }

.termination-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 8px;
}

.termination-badge {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9em;
    flex-grow: 1;
}

.termination-details {
    display: flex;
    gap: 16px;
    font-size: 0.9em;
    color: #4a5568;
}

.stats-container, .comparison-summary {
    background: white;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.stats-grid, .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-top: 8px;
}

.stat-item, .summary-item {
    text-align: center;
    padding: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    transition: all 0.2s;
}

.stat-item:hover, .summary-item:hover {
    border-color: #3182ce;
    transform: translateY(-2px);
}

.stat-value, .summary-value {
    font-size: 1.6em;
    font-weight: bold;
    margin-bottom: 3px;
}

.stat-label, .summary-label {
    color: #718096;
    font-size: 0.8em;
}

.score-good { color: #38a169; }
.score-warning { color: #d69e2e; }
.score-bad { color: #e53e3e; }

.conversation-container, .comparison-container {
    background: white;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.message {
    margin-bottom: 8px;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

.user-message {
    border-left: 4px solid #3182ce;
}

.assistant-message {
    border-left: 4px solid #38a169;
}

.tool-message {
    border-left: 4px solid #d69e2e;
}

.message-header {
    background: #f7fafc;
    padding: 6px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.message-type {
    font-weight: 600;
    color: #2d3748;
    font-size: 0.9em;
}

.timestamp {
    color: #718096;
    font-size: 0.7em;
}

.message-content {
    padding: 10px;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.9em;
    line-height: 1.4;
}

/* T023: Styles for dialog turn cards */
.show-more-btn {
    background: #3182ce;
    color: white;
    border: none;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8em;
    margin-top: 8px;
    transition: background 0.2s;
}

.show-more-btn:hover {
    background: #2c5aa0;
}

.metadata-section {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #e2e8f0;
}

.metadata-toggle {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8em;
    color: #4a5568;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 4px;
}

.metadata-toggle:hover {
    background: #edf2f7;
    border-color: #cbd5e0;
}

.metadata-content {
    margin-top: 8px;
    padding: 8px;
    background: #f7fafc;
    border-radius: 4px;
    font-size: 0.8em;
}

.metadata-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}

/* T035: Styles for MCP tools section */
.mcp-tools-section {
    background: white;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.mcp-tools-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 12px;
    margin-top: 12px;
}

.mcp-tool-card {
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px;
    background: #f7fafc;
    transition: all 0.2s;
}

.mcp-tool-card:hover {
    border-color: #3182ce;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.mcp-tool-card.tool-success {
    border-left: 4px solid #38a169;
}

.mcp-tool-card.tool-failed {
    border-left: 4px solid #e53e3e;
}

.tool-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
}

.tool-badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.7em;
    font-weight: 600;
    text-transform: uppercase;
}

.mcp-badge {
    background: #2c5282;
    color: white;
}

.tool-framework-badge {
    background: #a0aec0;
    color: white;
}

.tool-name-display {
    font-weight: 600;
    color: #2d3748;
    flex-grow: 1;
    font-size: 0.95em;
}

.status-indicator {
    font-size: 1.2em;
}

.tool-input-params {
    margin-bottom: 10px;
}

.tool-input-params h5 {
    margin: 0 0 6px 0;
    font-size: 0.85em;
    color: #4a5568;
}

.tool-result-preview {
    margin-top: 10px;
}

.tool-result-preview h5 {
    margin: 0 0 6px 0;
    font-size: 0.85em;
    color: #4a5568;
}

.result-content {
    background: white;
    padding: 8px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.85em;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 300px;
    overflow-y: auto;
}

.expand-btn {
    background: #3182ce;
    color: white;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8em;
    margin-top: 6px;
    transition: background 0.2s;
}

.expand-btn:hover {
    background: #2c5aa0;
}

.tool-header {
    background: #fef5e7;
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background-color 0.2s;
}

.tool-header:hover {
    background: #fed7aa;
}

.tool-icon {
    font-size: 1.2em;
}

.tool-name {
    font-weight: 600;
    color: #975a16;
}

.tool-params {
    color: #718096;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
    flex-grow: 1;
}

.similarity-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.7em;
    margin-left: 8px;
    border: 1px solid;
}

.similarity-badge.score-good {
    background: #c6f6d5;
    color: #22543d;
    border-color: #38a169;
}

.similarity-badge.score-warning {
    background: #fef5e7;
    color: #975a16;
    border-color: #d69e2e;
}

.similarity-badge.score-bad {
    background: #fed7d7;
    color: #742a2a;
    border-color: #e53e3e;
}

.expand-icon {
    transition: transform 0.2s;
    font-weight: bold;
    color: #975a16;
}

.expand-icon.expanded {
    transform: rotate(90deg);
}

.tool-details {
    border-top: 1px solid #e2e8f0;
}

.tool-section {
    padding: 10px;
    border-bottom: 1px solid #f1f5f9;
}

.tool-section:last-child {
    border-bottom: none;
}

.tool-section h4 {
    margin-bottom: 6px;
    color: #2d3748;
    font-size: 0.9em;
}

.json-code {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 8px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.8em;
    line-height: 1.3;
    max-width: 100%;
}

.json-code code {
    background: none;
    color: #2d3748;
}

/* JSON Syntax Highlighting */
.json-key {
    color: #d73a49;
    font-weight: 600;
}

.json-string {
    color: #032f62;
}

.json-number {
    color: #005cc5;
}

.json-boolean {
    color: #6f42c1;
    font-weight: 600;
}

.json-bracket {
    color: #6a737d;
    font-weight: bold;
}

.text-content {
    background: #f8f9fa;
    border: 1px solid #e1e4e8;
    border-radius: 4px;
    padding: 8px;
    margin-bottom: 6px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.8em;
    line-height: 1.3;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-width: 100%;
}

.result-preview {
    background: #f0fff4;
    border: 1px solid #9ae6b4;
    border-radius: 4px;
    padding: 6px;
    margin-bottom: 6px;
    color: #22543d;
    font-size: 0.85em;
}

.side-by-side {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
}

.side {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px;
}

.current-side {
    border-left: 3px solid #3182ce;
}

.baseline-side {
    border-left: 3px solid #805ad5;
}

.side h4 {
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 1.1em;
}

.comparison-badges {
    margin-top: 8px;
}

.report-footer {
    text-align: center;
    color: #718096;
    padding: 12px;
    border-top: 1px solid #e2e8f0;
    margin-top: 20px;
    font-size: 0.8em;
}

.empty-conversation {
    color: #a0aec0;
    font-style: italic;
    text-align: center;
    padding: 20px;
    background: #f7fafc;
    border-radius: 4px;
    border: 1px dashed #cbd5e0;
}

.invocation-results {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 8px;
}

.invocation-result {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    overflow: hidden;
}

.invocation-header {
    background: #f7fafc;
    padding: 8px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
}

.invocation-number {
    font-weight: 600;
    color: #2d3748;
    font-size: 0.9em;
}

.invocation-score {
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8em;
}

.invocation-score.score-good {
    background: #c6f6d5;
    color: #22543d;
}

.invocation-score.score-warning {
    background: #fef5e7;
    color: #975a16;
}

.invocation-score.score-bad {
    background: #fed7d7;
    color: #742a2a;
}

.invocation-details {
    padding: 10px 12px;
}

.invocation-description {
    color: #4a5568;
    font-size: 0.85em;
    margin-bottom: 8px;
}

.tool-comparison {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.tool-match {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    background: #f8f9fa;
    border-radius: 4px;
    font-size: 0.8em;
}

.tool-match.extra {
    background: #fef5e7;
    border-left: 3px solid #d69e2e;
}

.tool-match.missing {
    background: #fed7d7;
    border-left: 3px solid #e53e3e;
}

.tool-match .tool-name {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    color: #2d3748;
}

.tool-filter-controls {
    background: white;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.tool-filter-controls h4 {
    margin: 0 0 8px 0;
    color: #2d3748;
    font-size: 1em;
}

.filter-checkbox {
    display: inline-block;
    margin-right: 20px;
    cursor: pointer;
    font-size: 0.9em;
    color: #4a5568;
}

.filter-checkbox input {
    margin-right: 6px;
}

/* Hide TodoWrite and non-MCP tools by default */
.tool-todowrite {
    display: none;
}

.tool-non-mcp {
    display: none;
}

/* Show only when filter is active */
.show-todowrite .tool-todowrite {
    display: block;
}

.show-non-mcp .tool-non-mcp {
    display: block;
}

@media (max-width: 768px) {
    .side-by-side {
        grid-template-columns: 1fr;
    }
    
    .stats-grid, .summary-grid {
        grid-template-columns: 1fr;
    }
    
    .container {
        padding: 10px;
    }
}

/* Git info comparison styles */
.git-info-comparison {
    background: #f8f9fa;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.current-version, .baseline-version {
    font-size: 0.85em;
    color: #2d3748;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.current-version {
    border-right: 1px solid #cbd5e0;
    padding-right: 16px;
}

.current-version code, .baseline-version code {
    background: #e6fffa;
    padding: 2px 4px;
    border-radius: 2px;
    font-weight: 600;
    color: #1a202c;
    cursor: help;
}

.current-version .commit-date, .baseline-version .commit-date {
    color: #68d391;
    font-size: 0.8em;
    margin-left: 8px;
    display: block;
    margin-top: 4px;
}

/* Dialog Turn Comparison styles - T062 */
.dialog-turn-comparison {
    background: white;
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.dialog-turn-comparison h3 {
    color: #2d3748;
    margin-bottom: 12px;
    font-size: 1.3em;
}

.diff-filter-controls {
    background: #f7fafc;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 16px;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    align-items: center;
}

.diff-filter-controls label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 0.9em;
}

.diff-filter-controls input[type="checkbox"] {
    cursor: pointer;
}

.diff-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 0.85em;
}

.diff-badge.diff-added {
    background: #c6f6d5;
    color: #22543d;
}

.diff-badge.diff-removed {
    background: #fed7d7;
    color: #742a2a;
}

.diff-badge.diff-modified {
    background: #fef5e7;
    color: #975a16;
}

.diff-badge.diff-unchanged {
    background: #e2e8f0;
    color: #4a5568;
}

.diff-side-by-side {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.diff-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    border-radius: 4px;
    overflow: hidden;
}

.diff-row.turn-added {
    background: #f0fff4;
    border: 1px solid #c6f6d5;
}

.diff-row.turn-removed {
    background: #fff5f5;
    border: 1px solid #fed7d7;
}

.diff-row.turn-modified {
    background: #fffaf0;
    border: 1px solid #fef5e7;
}

.diff-row.turn-unchanged {
    background: #f8f9fa;
    border: 1px solid #e2e8f0;
}

.diff-column {
    padding: 12px;
    display: flex;
    flex-direction: column;
}

.diff-column.diff-current {
    border-right: 2px solid #cbd5e0;
}

.diff-column .turn-header {
    font-weight: 600;
    font-size: 0.85em;
    color: #4a5568;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #e2e8f0;
}

.diff-column.diff-current .turn-header {
    color: #2b6cb0;
}

.diff-column.diff-baseline .turn-header {
    color: #805ad5;
}

.diff-column .turn-metadata {
    font-size: 0.75em;
    color: #718096;
    margin-bottom: 6px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

.diff-column .turn-type {
    background: #edf2f7;
    padding: 2px 6px;
    border-radius: 2px;
    font-weight: 600;
}

.diff-column .turn-actor {
    color: #4a5568;
}

.diff-column .turn-content {
    font-size: 0.9em;
    line-height: 1.5;
    color: #2d3748;
    white-space: pre-wrap;
    word-break: break-word;
}

.diff-highlight {
    background: #fef5e7;
    padding: 2px 4px;
    border-radius: 2px;
    font-weight: 600;
}

.turn-added .diff-highlight {
    background: #c6f6d5;
}

.turn-removed .diff-highlight {
    background: #fed7d7;
}

.turn-modified .diff-highlight {
    background: #ffd700;
}

.turn-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    color: #a0aec0;
    font-style: italic;
    font-size: 0.9em;
    background: #f7fafc;
    border-radius: 4px;
}

/* Hide filtered diff rows */
.diff-row.turn-added.filtered-out,
.diff-row.turn-removed.filtered-out,
.diff-row.turn-modified.filtered-out,
.diff-row.turn-unchanged.filtered-out {
    display: none;
}

</style>
        """
        
    def _get_embedded_scripts(self) -> str:
        """Return embedded JavaScript for interactive features."""
        return """
<script>
function toggleToolCall(toolId) {
    const details = document.getElementById('details-' + toolId);
    const icon = document.getElementById('icon-' + toolId);
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        icon.textContent = '▼';
        icon.classList.add('expanded');
    } else {
        details.style.display = 'none';
        icon.textContent = '▶';
        icon.classList.remove('expanded');
    }
}

// Toggle tool filter display
function toggleToolFilter(filterType) {
    const container = document.querySelector('.container');
    const checkbox = document.getElementById(`show-${filterType}`);

    if (checkbox.checked) {
        container.classList.add(`show-${filterType}`);
    } else {
        container.classList.remove(`show-${filterType}`);
    }
}

// Toggle content truncation (show more/show less)
function toggleContent(contentId) {
    const preview = document.getElementById(contentId + '_preview');
    const full = document.getElementById(contentId + '_full');
    const btn = event.target;

    if (full.style.display === 'none') {
        preview.style.display = 'none';
        full.style.display = 'inline';
        btn.textContent = 'Show less';
    } else {
        preview.style.display = 'inline';
        full.style.display = 'none';
        btn.textContent = 'Show more';
    }
}

// Toggle metadata display (collapsed by default)
function toggleMetadata(metadataId) {
    const details = document.getElementById('details-' + metadataId);
    const icon = document.getElementById('icon-' + metadataId);

    if (details.style.display === 'none') {
        details.style.display = 'block';
        icon.textContent = '▼';
    } else {
        details.style.display = 'none';
        icon.textContent = '▶';
    }
}

// Ensure all tool calls start collapsed (default state)
document.addEventListener('DOMContentLoaded', function() {
    const allToolDetails = document.querySelectorAll('[id^="details-"]');
    allToolDetails.forEach(function(details) {
        details.style.display = 'none';
    });

    const allExpandIcons = document.querySelectorAll('[id^="icon-"]');
    allExpandIcons.forEach(function(icon) {
        icon.textContent = '▶';
        icon.classList.remove('expanded');
    });
});

// T062: Toggle diff filter for dialog turn comparison
function toggleDiffFilter(filterType) {
    const checkbox = document.getElementById(`show-${filterType}`);
    const rows = document.querySelectorAll(`.diff-row.turn-${filterType}`);

    rows.forEach(function(row) {
        if (checkbox.checked) {
            row.classList.remove('filtered-out');
        } else {
            row.classList.add('filtered-out');
        }
    });
}
</script>
        """

# ============================================================================
# Summary Report Generation Functions
# ============================================================================

def _get_status_color(status: 'ScenarioStatus') -> str:
    """Get Bootstrap color hex value for status badge.
    
    Args:
        status: ScenarioStatus enum value
        
    Returns:
        Hex color string (e.g., "#28a745")
    """
    from mcp_eval.summary_models import ScenarioStatus
    
    colors = {
        ScenarioStatus.PASSED: "#28a745",   # Green
        ScenarioStatus.FAILED: "#dc3545",   # Red
        ScenarioStatus.RECORDED: "#007bff", # Blue
        ScenarioStatus.ERROR: "#ffc107"     # Yellow
    }
    return colors[status]


def _truncate_intent(intent: str, max_length: int = 60) -> tuple[str, str]:
    """Truncate intent string for display with tooltip.
    
    Args:
        intent: Full intent text
        max_length: Maximum length before truncation (default 60)
        
    Returns:
        Tuple of (display_text, full_text) where display_text is truncated
        with "..." if needed, and full_text is the original
    """
    if len(intent) <= max_length:
        return (intent, intent)
    return (intent[:max_length] + "...", intent)


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to display string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "12.3s"
    """
    return f"{seconds:.1f}s"


def _format_similarity(score: Optional[float]) -> str:
    """Format similarity score for display.
    
    Args:
        score: Similarity score between 0.0 and 1.0, or None
        
    Returns:
        Formatted string like "0.92" or "N/A" if score is None
    """
    if score is None:
        return "N/A"
    return f"{score:.2f}"


def generate_summary_report(test_run: 'TestRunSummary') -> str:
    """Generate aggregated HTML summary report for multi-scenario test run.
    
    Args:
        test_run: TestRunSummary containing all scenario execution metadata
        
    Returns:
        Complete HTML document as string
    """
    from mcp_eval.summary_models import TestRunSummary, ScenarioStatus
    
    # Format timestamp for title
    timestamp_str = test_run.test_run_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Build HTML document
    html_parts = []
    
    # DOCTYPE and HTML head
    html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Evaluation Test Summary - {timestamp_str}</title>
    <style>
        /* Color Palette */
        :root {{
            --color-passed: #28a745;
            --color-failed: #dc3545;
            --color-recorded: #007bff;
            --color-error: #ffc107;
            --color-bg: #ffffff;
            --color-text: #212529;
            --color-border: #dee2e6;
        }}
        
        /* General Styles */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--color-bg);
            color: var(--color-text);
        }}
        
        header {{
            margin-bottom: 30px;
        }}
        
        h1 {{
            margin: 0 0 15px 0;
            color: var(--color-text);
        }}
        
        .summary-stats {{
            margin: 15px 0;
            font-size: 1.1rem;
        }}
        
        .summary-stats .stat {{
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        
        .summary-stats .stat.passed {{
            color: var(--color-passed);
            font-weight: 600;
        }}
        
        .summary-stats .stat.failed {{
            color: var(--color-failed);
            font-weight: 600;
        }}
        
        .summary-stats .stat.recorded {{
            color: var(--color-recorded);
            font-weight: 600;
        }}
        
        .summary-stats .stat.error {{
            color: var(--color-error);
            font-weight: 600;
        }}
        
        .metadata {{
            margin: 10px 0;
            font-size: 0.9rem;
            color: #6c757d;
        }}
        
        .metadata span {{
            margin-right: 20px;
        }}
        
        /* Table Styles */
        main {{
            overflow-x: auto;
        }}
        
        .scenarios-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .scenarios-table thead {{
            background-color: #f8f9fa;
            border-bottom: 2px solid var(--color-border);
        }}
        
        .scenarios-table th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: var(--color-text);
        }}
        
        .scenarios-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--color-border);
        }}
        
        .scenarios-table tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        /* Status Badge Styles */
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 600;
            color: white;
            text-align: center;
        }}
        
        .status-passed {{
            background-color: var(--color-passed);
        }}
        
        .status-failed {{
            background-color: var(--color-failed);
        }}
        
        .status-recorded {{
            background-color: var(--color-recorded);
        }}
        
        .status-error {{
            background-color: var(--color-error);
            color: #212529; /* Dark text on yellow for contrast */
        }}
        
        /* Column-specific Styles */
        .scenario-name a {{
            color: #007bff;
            text-decoration: none;
        }}
        
        .scenario-name a:hover {{
            text-decoration: underline;
        }}
        
        .intent {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .tool-count,
        .duration,
        .similarity-score {{
            text-align: center;
        }}
        
        /* Footer */
        footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 0.9rem;
            color: #6c757d;
        }}
    </style>
</head>
<body>""")
    
    # Header section
    html_parts.append(f"""
    <header>
        <h1>MCP Evaluation Test Summary</h1>
        <div class="summary-stats">
            <span class="stat">Total: {test_run.total_scenarios}</span>
            <span class="stat passed">{test_run.passed_count} passed</span>
            <span class="stat failed">{test_run.failed_count} failed</span>
            <span class="stat recorded">{test_run.recorded_count} recorded</span>""")
    
    # Only show error stat if there are errors
    if test_run.error_count > 0:
        html_parts.append(f"""
            <span class="stat error">{test_run.error_count} errors</span>""")
    
    html_parts.append("""
        </div>
        <div class="metadata">""")
    
    # Metadata line
    html_parts.append(f"""
            <span>Test Run: {test_run.test_run_timestamp.isoformat()}</span>""")
    
    if test_run.git_hash:
        html_parts.append(f"""
            <span>Git: {test_run.git_hash}</span>""")
    
    if test_run.mcp_config_path:
        html_parts.append(f"""
            <span>Config: {test_run.mcp_config_path}</span>""")
    
    html_parts.append("""
        </div>
    </header>""")
    
    # Main table section
    html_parts.append("""
    <main>
        <table class="scenarios-table">
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Intent</th>
                    <th>Status</th>
                    <th>Tools</th>
                    <th>Duration</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>""")
    
    # Table rows - one per scenario
    for summary in test_run.scenario_summaries:
        status_class = summary.status.value.lower()
        status_color = _get_status_color(summary.status)
        display_intent, full_intent = _truncate_intent(summary.user_intent)
        duration_str = _format_duration(summary.duration_seconds)
        similarity_str = _format_similarity(summary.similarity_score)
        
        html_parts.append(f"""
                <tr class="scenario-row status-{status_class}">
                    <td class="scenario-name">
                        <a href="{summary.detailed_report_path}">{html.escape(summary.scenario_name)}</a>
                    </td>
                    <td class="intent" title="{html.escape(full_intent)}">
                        {html.escape(display_intent)}
                    </td>
                    <td class="status">
                        <span class="badge status-{status_class}">{summary.status.value}</span>
                    </td>
                    <td class="tool-count">{summary.tool_count}</td>
                    <td class="duration">{duration_str}</td>
                    <td class="similarity-score">{similarity_str}</td>
                </tr>""")
    
    # Close table and main
    html_parts.append("""
            </tbody>
        </table>
    </main>""")
    
    # Footer
    from mcp_eval import __version__
    html_parts.append(f"""
    <footer>
        <p>Generated by mcp-eval v{__version__}</p>
    </footer>
</body>
</html>""")
    
    return "".join(html_parts)

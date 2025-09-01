"""Enhanced HTML reporting for multi-agent dialogs."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple


class MultiAgentHTMLReporter:
    """Generate HTML reports for multi-agent dialog sessions."""
    
    def __init__(self):
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
    
    def _format_json_with_colors(self, obj: Any) -> str:
        """Format JSON with syntax highlighting."""
        if not obj:
            return '<span class="json-null">null</span>'
        
        json_str = json.dumps(obj, indent=2)
        
        # Apply syntax highlighting
        json_str = json_str.replace('"', '&quot;')
        
        # Color keys
        import re
        json_str = re.sub(r'&quot;([^&]+)&quot;:', r'<span class="json-key">&quot;\1&quot;</span>:', json_str)
        
        # Color string values  
        json_str = re.sub(r': &quot;([^&]*)&quot;', r': <span class="json-string">&quot;\1&quot;</span>', json_str)
        
        # Color numbers
        json_str = re.sub(r': (\d+)', r': <span class="json-number">\1</span>', json_str)
        
        # Color booleans
        json_str = re.sub(r': (true|false)', r': <span class="json-boolean">\1</span>', json_str)
        
        # Color null
        json_str = re.sub(r': null', r': <span class="json-null">null</span>', json_str)
        
        return json_str
    
    def generate_dialog_report(self, detailed_log: Dict[str, Any], scenario_name: str) -> str:
        """Generate an HTML report for a multi-agent dialog session."""
        
        conversation_log = detailed_log.get("conversation_log", [])
        scenario_data = detailed_log.get("scenario_data", {})
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.report_dir / f"{scenario_name}_dialog_{timestamp}.html"
        
        html_content = self._generate_dialog_html(
            conversation_log, scenario_data, detailed_log
        )
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def generate_comparison_report(self, current_log: Dict[str, Any], baseline_log: Dict[str, Any], 
                                 comparison_result: Dict[str, Any], scenario_name: str) -> str:
        """Generate an HTML comparison report between current and baseline dialogs."""
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.report_dir / f"{scenario_name}_comparison_{timestamp}.html"
        
        current_conversation = current_log.get("conversation_log", [])
        baseline_conversation = baseline_log.get("conversation_log", [])
        
        html_content = self._generate_comparison_html(
            current_conversation, baseline_conversation, comparison_result, current_log.get("scenario_data", {})
        )
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def _extract_tool_calls_with_details(self, conversation_log: List[Dict]) -> List[Dict]:
        """Extract MCP tool calls with full details including results."""
        tool_calls = []
        
        for turn in conversation_log:
            if turn['speaker'] == 'Agent':  # Only agent makes MCP tool calls
                turn_tool_calls = turn.get('tool_calls', [])
                for tool_call in turn_tool_calls:
                    tool_name = tool_call.get('tool_name', '')
                    if tool_name.startswith('mcp__'):  # Only MCP tools
                        tool_calls.append({
                            'turn': turn['turn'],
                            'tool_name': tool_name,
                            'tool_input': tool_call.get('tool_input', {}),
                            'tool_result': tool_call.get('result', 'No result'),
                            'is_error': tool_call.get('is_error', False),
                            'timestamp': tool_call.get('timestamp', '')
                        })
        
        return tool_calls
    
    def _calculate_tool_call_similarity(self, current_call: Dict, baseline_call: Dict) -> Dict[str, Any]:
        """Calculate detailed similarity between two tool calls."""
        from .similarity import calculate_args_similarity
        
        # Tool name similarity (exact match)
        name_similarity = 1.0 if current_call['tool_name'] == baseline_call['tool_name'] else 0.0
        
        # Arguments similarity
        args_similarity = calculate_args_similarity(
            current_call['tool_input'], 
            baseline_call['tool_input']
        )
        
        # Overall similarity (weighted: name 40%, args 60%)
        overall_similarity = (name_similarity * 0.4) + (args_similarity * 0.6)
        
        return {
            'overall_similarity': overall_similarity,
            'name_similarity': name_similarity,
            'args_similarity': args_similarity,
            'name_match': current_call['tool_name'] == baseline_call['tool_name']
        }

    def _generate_comparison_html(self, current_conversation: List[Dict], baseline_conversation: List[Dict], 
                                comparison_result: Dict[str, Any], scenario_data: Dict) -> str:
        """Generate HTML content for comparison report."""
        
        scenario_name = scenario_data.get('name', 'Unknown Scenario')
        overall_score = comparison_result.get('overall_similarity', 0.0)
        
        # Score colors
        score_color = "#28a745" if overall_score >= 0.8 else "#ffc107" if overall_score >= 0.6 else "#dc3545"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Agent Dialog Comparison: {scenario_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
        .comparison-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .score-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .score-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid {score_color};
        }}
        .score-value {{
            font-size: 2em;
            font-weight: bold;
            color: {score_color};
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        .dialog-column {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .column-header {{
            padding: 15px 20px;
            border-radius: 10px 10px 0 0;
            font-weight: bold;
            text-align: center;
        }}
        .current-header {{
            background: #28a745;
            color: white;
        }}
        .baseline-header {{
            background: #6c757d;
            color: white;
        }}
        .dialog-content {{
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }}
        .turn {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #dee2e6;
        }}
        .turn.agent {{
            border-left-color: #28a745;
            background: #f8fff9;
        }}
        .turn.user {{
            border-left-color: #dc3545;
            background: #fff8f8;
        }}
        .turn-header {{
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }}
        .message {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            white-space: pre-wrap;
            font-size: 0.9em;
        }}
        .analysis-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .tool-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        .tool-stats {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }}
        .tool-calls-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .tool-calls-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        .tool-calls-column {{
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
        }}
        .tool-calls-header {{
            background: #f8f9fa;
            padding: 15px;
            font-weight: bold;
            border-bottom: 1px solid #dee2e6;
        }}
        .tool-calls-content {{
            padding: 15px;
            max-height: 500px;
            overflow-y: auto;
        }}
        .tool-call-item {{
            margin-bottom: 15px;
            border: 1px solid #e3f2fd;
            border-radius: 6px;
            background: #fafafa;
        }}
        .tool-call-header {{
            background: #e3f2fd;
            padding: 10px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
        }}
        .tool-call-header:hover {{
            background: #bbdefb;
        }}
        .tool-call-name {{
            font-weight: bold;
            color: #1976d2;
        }}
        .tool-call-details {{
            padding: 15px;
            display: none;
            border-top: 1px solid #bbdefb;
        }}
        .tool-call-details.expanded {{
            display: block;
        }}
        .tool-section {{
            margin-bottom: 15px;
        }}
        .tool-section-title {{
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }}
        .tool-json-content {{
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 0.85em;
            line-height: 1.4;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }}
        .similarity-metrics {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .similarity-score {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 10px;
        }}
        .score-high {{ background: #d4edda; color: #155724; }}
        .score-medium {{ background: #fff3cd; color: #856404; }}
        .score-low {{ background: #f8d7da; color: #721c24; }}
        .alignment-indicator {{
            text-align: center;
            padding: 5px;
            background: #e9ecef;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 0.8em;
            color: #6c757d;
        }}
    </style>
    <script>
        function toggleToolCall(toolId) {{
            const content = document.getElementById('tool-details-' + toolId);
            const toggle = document.getElementById('tool-toggle-' + toolId);
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                toggle.textContent = '▶ Expand';
            }} else {{
                content.classList.add('expanded');
                toggle.textContent = '▼ Collapse';
            }}
        }}
        
        function getScoreClass(score) {{
            if (score >= 0.8) return 'score-high';
            if (score >= 0.6) return 'score-medium';
            return 'score-low';
        }}
    </script>
</head>
<body>
    <div class="comparison-container">
        <div class="header">
            <h1>🔍 Multi-Agent Dialog Comparison</h1>
            <h2>{scenario_name}</h2>
            <p>Generated: {datetime.now().isoformat()}</p>
        </div>
        
        <div class="score-section">
            <h3>📊 Similarity Scores</h3>
            <div class="score-grid">
                <div class="score-card">
                    <div class="score-value">{overall_score:.3f}</div>
                    <div>Overall Similarity</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{comparison_result.get('trajectory_similarity', 0.0):.3f}</div>
                    <div>Tool Trajectory</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{comparison_result.get('dialog_flow_similarity', 0.0):.3f}</div>
                    <div>Dialog Flow</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{comparison_result.get('turn_similarity', 0.0):.3f}</div>
                    <div>Turn Sequence</div>
                </div>
            </div>
        </div>
        
        <div class="comparison-grid">
            <div class="dialog-column">
                <div class="column-header current-header">
                    Current Dialog ({len(current_conversation)} turns)
                </div>
                <div class="dialog-content">
"""

        # Add current conversation
        for turn in current_conversation:
            speaker = turn['speaker'].lower()
            speaker_class = 'agent' if speaker == 'agent' else 'user'
            tool_count = len(turn.get('tool_calls', []))
            
            html += f"""
                    <div class="turn {speaker_class}">
                        <div class="turn-header">
                            <span>{'🤖' if speaker == 'agent' else '👤'} {turn['speaker']} (Turn {turn['turn']})</span>
                            <span>{tool_count} tools</span>
                        </div>
                        <div class="message">{turn.get('message', 'No message')[:200]}{'...' if len(turn.get('message', '')) > 200 else ''}</div>"""
            
            # Add tool call details for agent turns
            if speaker == 'agent' and tool_count > 0:
                for tool_call in turn.get('tool_calls', []):
                    tool_name = tool_call.get('tool_name', 'Unknown')
                    tool_input = tool_call.get('tool_input', {})
                    tool_result = tool_call.get('result', [])
                    
                    # Format tool input
                    input_str = str(tool_input)[:100] + ('...' if len(str(tool_input)) > 100 else '')
                    
                    # Format tool output
                    if tool_result and isinstance(tool_result, list) and len(tool_result) > 0:
                        first_result = tool_result[0]
                        if isinstance(first_result, dict) and 'text' in first_result:
                            output_str = first_result['text'][:100] + ('...' if len(first_result['text']) > 100 else '')
                        else:
                            output_str = str(first_result)[:100] + ('...' if len(str(first_result)) > 100 else '')
                    else:
                        output_str = 'No output'
                    
                    html += f"""
                        <div class="tool-call-summary" style="margin: 10px 0; padding: 8px; background: #e8f5e8; border-left: 3px solid #28a745; border-radius: 4px;">
                            <div style="font-weight: bold; color: #155724;">🔧 {tool_name}</div>
                            <div style="font-size: 0.85em; color: #6c757d; margin: 4px 0;">
                                <strong>Args:</strong> {input_str}
                            </div>
                            <div style="font-size: 0.85em; color: #6c757d;">
                                <strong>Output:</strong> {output_str}
                            </div>
                        </div>"""
            
            html += """
                    </div>"""

        html += """
                </div>
            </div>
            
            <div class="dialog-column">
                <div class="column-header baseline-header">
                    Baseline Dialog (""" + str(len(baseline_conversation)) + """ turns)
                </div>
                <div class="dialog-content">
"""

        # Add baseline conversation
        for turn in baseline_conversation:
            speaker = turn['speaker'].lower()
            speaker_class = 'agent' if speaker == 'agent' else 'user'
            tool_count = len(turn.get('tool_calls', []))
            
            html += f"""
                    <div class="turn {speaker_class}">
                        <div class="turn-header">
                            <span>{'🤖' if speaker == 'agent' else '👤'} {turn['speaker']} (Turn {turn['turn']})</span>
                            <span>{tool_count} tools</span>
                        </div>
                        <div class="message">{turn.get('message', 'No message')[:200]}{'...' if len(turn.get('message', '')) > 200 else ''}</div>"""
            
            # Add tool call details for agent turns
            if speaker == 'agent' and tool_count > 0:
                for tool_call in turn.get('tool_calls', []):
                    tool_name = tool_call.get('tool_name', 'Unknown')
                    tool_input = tool_call.get('tool_input', {})
                    tool_result = tool_call.get('result', [])
                    
                    # Format tool input
                    input_str = str(tool_input)[:100] + ('...' if len(str(tool_input)) > 100 else '')
                    
                    # Format tool output
                    if tool_result and isinstance(tool_result, list) and len(tool_result) > 0:
                        first_result = tool_result[0]
                        if isinstance(first_result, dict) and 'text' in first_result:
                            output_str = first_result['text'][:100] + ('...' if len(first_result['text']) > 100 else '')
                        else:
                            output_str = str(first_result)[:100] + ('...' if len(str(first_result)) > 100 else '')
                    else:
                        output_str = 'No output'
                    
                    html += f"""
                        <div class="tool-call-summary" style="margin: 10px 0; padding: 8px; background: #e8f5e8; border-left: 3px solid #28a745; border-radius: 4px;">
                            <div style="font-weight: bold; color: #155724;">🔧 {tool_name}</div>
                            <div style="font-size: 0.85em; color: #6c757d; margin: 4px 0;">
                                <strong>Args:</strong> {input_str}
                            </div>
                            <div style="font-size: 0.85em; color: #6c757d;">
                                <strong>Output:</strong> {output_str}
                            </div>
                        </div>"""
            
            html += """
                    </div>"""

        # Add tool usage comparison
        tool_comparison = comparison_result.get('tool_usage_comparison', {})
        
        html += f"""
                </div>
            </div>
        </div>
        
        <div class="tool-calls-section">
            <h3>🔧 Detailed Tool Calls Comparison</h3>
            <div class="similarity-metrics">
                <strong>Tool Trajectory Similarity Breakdown:</strong><br>
                Overall Tool Similarity: <span class="similarity-score {self._get_score_class(comparison_result.get('trajectory_similarity', 0.0))}">{comparison_result.get('trajectory_similarity', 0.0):.3f}</span>
            </div>
            
            {self._generate_tool_calls_comparison(current_conversation, baseline_conversation, comparison_result)}
        </div>
        
        <div class="analysis-section">
            <h3>📊 Tool Usage Summary</h3>
            <div class="tool-comparison">
                <div class="tool-stats">
                    <h4>Current Dialog</h4>
                    <p><strong>Total tool calls:</strong> {tool_comparison.get('current_tool_count', 0)}</p>
                    <p><strong>Unique tools:</strong> {len(set(tool_comparison.get('common_tools', []) + tool_comparison.get('current_only_tools', [])))}</p>
                    <p><strong>Current-only tools:</strong> {', '.join(tool_comparison.get('current_only_tools', [])) or 'None'}</p>
                </div>
                <div class="tool-stats">
                    <h4>Baseline Dialog</h4>
                    <p><strong>Total tool calls:</strong> {tool_comparison.get('baseline_tool_count', 0)}</p>
                    <p><strong>Unique tools:</strong> {len(set(tool_comparison.get('common_tools', []) + tool_comparison.get('baseline_only_tools', [])))}</p>
                    <p><strong>Baseline-only tools:</strong> {', '.join(tool_comparison.get('baseline_only_tools', [])) or 'None'}</p>
                </div>
            </div>
            <p><strong>Common tools:</strong> {', '.join(tool_comparison.get('common_tools', [])) or 'None'}</p>
            <p><strong>Tool overlap ratio:</strong> {tool_comparison.get('tool_overlap_ratio', 0.0):.3f}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_dialog_html(self, conversation_log: List[Dict], scenario_data: Dict, detailed_log: Dict) -> str:
        """Generate the HTML content for the dialog report."""
        
        scenario_name = scenario_data.get('name', 'Unknown Scenario')
        total_turns = len(conversation_log)
        execution_time = detailed_log.get('execution_time', 'Unknown')
        
        # Count tool calls by agent
        agent_tool_calls = []
        user_tool_calls = []
        
        for turn in conversation_log:
            tool_calls = turn.get('tool_calls', [])
            if turn['speaker'] == 'Agent':
                agent_tool_calls.extend(tool_calls)
            else:
                user_tool_calls.extend(tool_calls)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Agent Dialog Report: {scenario_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .dialog-container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .turn {{
            margin-bottom: 25px;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .turn.agent {{
            border-left: 4px solid #28a745;
        }}
        .turn.user {{
            border-left: 4px solid #dc3545;
        }}
        .turn-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }}
        .speaker {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        .speaker.agent {{
            color: #28a745;
        }}
        .speaker.user {{
            color: #dc3545;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .message {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            white-space: pre-wrap;
        }}
        .tool-calls {{
            margin-top: 15px;
        }}
        .tool-call {{
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 6px;
            margin: 5px 0;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .tool-header {{
            background: #1976d2;
            color: white;
            padding: 8px 12px;
            border-radius: 6px 6px 0 0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
        }}
        .tool-header:hover {{
            background: #1565c0;
        }}
        .tool-toggle {{
            font-size: 0.8em;
            opacity: 0.8;
        }}
        .tool-content {{
            padding: 10px;
            display: none;
            border-top: 1px solid #90caf9;
        }}
        .tool-content.expanded {{
            display: block;
        }}
        .tool-json {{
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            white-space: pre-wrap;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 0.85em;
            line-height: 1.4;
            max-height: 300px;
            overflow-y: auto;
        }}
        .json-key {{
            color: #0066cc;
            font-weight: bold;
        }}
        .json-string {{
            color: #009900;
        }}
        .json-number {{
            color: #cc6600;
        }}
        .json-boolean {{
            color: #cc0066;
        }}
        .json-null {{
            color: #999;
        }}
        .scenario-info {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .expected-flow {{
            background: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 6px;
            padding: 15px;
            margin-top: 15px;
        }}
        .flow-item {{
            margin: 10px 0;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
    </style>
    <script>
        function toggleTool(toolId) {{
            const content = document.getElementById('tool-content-' + toolId);
            const toggle = document.getElementById('tool-toggle-' + toolId);
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                toggle.textContent = '▶ Expand';
            }} else {{
                content.classList.add('expanded');
                toggle.textContent = '▼ Collapse';
            }}
        }}
        
        function formatJSON(obj) {{
            const json = JSON.stringify(obj, null, 2);
            return json
                .replace(/"([^"]+)":/g, '<span class="json-key">"$1":</span>')
                .replace(/: "([^"]+)"/g, ': <span class="json-string">"$1"</span>')
                .replace(/: (\d+)/g, ': <span class="json-number">$1</span>')
                .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
                .replace(/: null/g, ': <span class="json-null">null</span>');
        }}
    </script>
</head>
<body>
    <div class="dialog-container">
        <div class="header">
            <h1>🎭 Multi-Agent Dialog Report</h1>
            <h2>{scenario_name}</h2>
            <p>Generated: {execution_time}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_turns}</div>
                <div>Total Turns</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(agent_tool_calls)}</div>
                <div>Agent Tool Calls</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(user_tool_calls)}</div>
                <div>User Tool Calls</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(scenario_data.get('expected_dialog_flow', []))}</div>
                <div>Expected Turns</div>
            </div>
        </div>
        
        <div class="scenario-info">
            <h3>📋 Scenario Information</h3>
            <p><strong>Description:</strong> {scenario_data.get('description', 'No description provided')}</p>
            <p><strong>Initial Intent:</strong> {scenario_data.get('initial_user_intent', 'Not specified')}</p>
            
            <div class="expected-flow">
                <h4>Expected Dialog Flow</h4>
"""

        # Add expected dialog flow
        for i, flow_item in enumerate(scenario_data.get('expected_dialog_flow', []), 1):
            html += f"""
                <div class="flow-item">
                    <strong>Turn {flow_item.get('turn', i)}:</strong> {flow_item.get('agent_action', 'Unknown action')}<br>
                    <em>Expected tools:</em> {', '.join(flow_item.get('expected_tools', []))}<br>
                    <em>User response pattern:</em> {flow_item.get('user_response_pattern', 'Not specified')}
                </div>"""

        html += """
            </div>
        </div>
        
        <div class="dialog-transcript">
            <h3>💬 Dialog Transcript</h3>
"""

        # Add conversation turns
        for turn in conversation_log:
            speaker = turn['speaker'].lower()
            speaker_class = 'agent' if speaker == 'agent' else 'user'
            timestamp = turn.get('timestamp', 'Unknown time')
            message = turn.get('message', 'No message content')
            tool_calls = turn.get('tool_calls', [])
            
            html += f"""
            <div class="turn {speaker_class}">
                <div class="turn-header">
                    <span class="speaker {speaker_class}">
                        {'🤖' if speaker == 'agent' else '👤'} {turn['speaker']} (Turn {turn['turn']})
                    </span>
                    <span class="timestamp">{timestamp}</span>
                </div>
                <div class="message">{message}</div>
"""
            
            if tool_calls:
                html += '<div class="tool-calls">'
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.get('tool_name', 'unknown')
                    tool_input = tool_call.get('tool_input', {})
                    tool_result = tool_call.get('result', 'No result available')
                    is_error = tool_call.get('is_error', False)
                    
                    tool_id = f"{turn['turn']}-{i}"
                    
                    # Parse result if it's JSON string
                    try:
                        if isinstance(tool_result, str):
                            result_obj = json.loads(tool_result)
                        else:
                            result_obj = tool_result
                    except (json.JSONDecodeError, TypeError):
                        result_obj = tool_result
                    
                    html += f"""
                    <div class="tool-call">
                        <div class="tool-header" onclick="toggleTool('{tool_id}')">
                            <span>🔧 {tool_name}</span>
                            <span class="tool-toggle" id="tool-toggle-{tool_id}">▶ Expand</span>
                        </div>
                        <div class="tool-content" id="tool-content-{tool_id}">
                            <div><strong>Input:</strong></div>
                            <div class="tool-json">{self._format_json_with_colors(tool_input)}</div>
                            
                            <div style="margin-top: 10px;"><strong>Output:</strong></div>
                            <div class="tool-json{'error' if is_error else ''}">{self._format_json_with_colors(result_obj)}</div>
                        </div>
                    </div>"""
                html += '</div>'
            
            html += '</div>'

        html += """
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _get_score_class(self, score: float) -> str:
        """Get CSS class for similarity score."""
        if score >= 0.8:
            return 'score-high'
        elif score >= 0.6:
            return 'score-medium'
        else:
            return 'score-low'
    
    def _generate_tool_calls_comparison(self, current_conversation: List[Dict], baseline_conversation: List[Dict], comparison_result: Dict) -> str:
        """Generate HTML for detailed tool calls comparison."""
        # Extract tool calls with full details
        current_tools = self._extract_tool_calls_with_details(current_conversation)
        baseline_tools = self._extract_tool_calls_with_details(baseline_conversation)
        
        # Align tool calls for comparison
        aligned_calls = self._align_tool_calls(current_tools, baseline_tools)
        
        html = """
            <div class="tool-calls-grid">
                <div class="tool-calls-column">
                    <div class="tool-calls-header">Current Tool Calls</div>
                    <div class="tool-calls-content">
        """
        
        for i, (current_call, baseline_call, similarity) in enumerate(aligned_calls):
            if current_call:
                html += self._generate_tool_call_html(current_call, f"current-{i}", similarity)
            else:
                html += f'<div class="alignment-indicator">⚪ No corresponding call</div>'
        
        html += """
                    </div>
                </div>
                <div class="tool-calls-column">
                    <div class="tool-calls-header">Baseline Tool Calls</div>
                    <div class="tool-calls-content">
        """
        
        for i, (current_call, baseline_call, similarity) in enumerate(aligned_calls):
            if baseline_call:
                html += self._generate_tool_call_html(baseline_call, f"baseline-{i}", similarity)
            else:
                html += f'<div class="alignment-indicator">⚪ No corresponding call</div>'
        
        html += """
                    </div>
                </div>
            </div>
        """
        
        return html
    
    def _align_tool_calls(self, current_tools: List[Dict], baseline_tools: List[Dict]) -> List[Tuple]:
        """Align tool calls for side-by-side comparison."""
        aligned = []
        max_len = max(len(current_tools), len(baseline_tools))
        
        for i in range(max_len):
            current_call = current_tools[i] if i < len(current_tools) else None
            baseline_call = baseline_tools[i] if i < len(baseline_tools) else None
            
            # Calculate similarity if both calls exist
            similarity = None
            if current_call and baseline_call:
                similarity = self._calculate_tool_call_similarity(current_call, baseline_call)
            
            aligned.append((current_call, baseline_call, similarity))
        
        return aligned
    
    def _generate_tool_call_html(self, tool_call: Dict, call_id: str, similarity: Dict = None) -> str:
        """Generate HTML for a single tool call."""
        tool_name = tool_call['tool_name']
        turn_num = tool_call['turn']
        
        # Similarity badge
        similarity_badge = ""
        if similarity:
            score = similarity['overall_similarity']
            score_class = self._get_score_class(score)
            similarity_badge = f'<span class="similarity-score {score_class}">{score:.3f}</span>'
        
        html = f"""
            <div class="tool-call-item">
                <div class="tool-call-header" onclick="toggleToolCall('{call_id}')">
                    <div>
                        <span class="tool-call-name">🔧 {tool_name}</span>
                        <small style="color: #666;"> (Turn {turn_num})</small>
                    </div>
                    <div>
                        {similarity_badge}
                        <span class="tool-toggle" id="tool-toggle-{call_id}">▶ Expand</span>
                    </div>
                </div>
                <div class="tool-call-details" id="tool-details-{call_id}">
                    <div class="tool-section">
                        <div class="tool-section-title">📥 Input Arguments:</div>
                        <div class="tool-json-content">{self._format_json_with_colors(tool_call['tool_input'])}</div>
                    </div>
                    
                    <div class="tool-section">
                        <div class="tool-section-title">📤 Output Result:</div>
                        <div class="tool-json-content">{self._format_json_with_colors(self._parse_tool_result(tool_call['tool_result']))}</div>
                    </div>
        """
        
        if similarity:
            html += f"""
                    <div class="tool-section">
                        <div class="tool-section-title">📊 Similarity Metrics:</div>
                        <div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">
                            <strong>Overall:</strong> <span class="similarity-score {self._get_score_class(similarity['overall_similarity'])}">{similarity['overall_similarity']:.3f}</span><br>
                            <strong>Name Match:</strong> <span class="similarity-score {'score-high' if similarity['name_match'] else 'score-low'}">{'✅' if similarity['name_match'] else '❌'}</span><br>
                            <strong>Args Similarity:</strong> <span class="similarity-score {self._get_score_class(similarity['args_similarity'])}">{similarity['args_similarity']:.3f}</span>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
        
        return html
    
    def _parse_tool_result(self, result: Any) -> Any:
        """Parse tool result, handling JSON strings."""
        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return result
        return result
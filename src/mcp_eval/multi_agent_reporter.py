"""Enhanced HTML reporting for multi-agent dialogs."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


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
    </style>
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
                        <div class="message">{turn.get('message', 'No message')[:200]}{'...' if len(turn.get('message', '')) > 200 else ''}</div>
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
                        <div class="message">{turn.get('message', 'No message')[:200]}{'...' if len(turn.get('message', '')) > 200 else ''}</div>
                    </div>"""

        # Add tool usage comparison
        tool_comparison = comparison_result.get('tool_usage_comparison', {})
        
        html += f"""
                </div>
            </div>
        </div>
        
        <div class="analysis-section">
            <h3>🔧 Tool Usage Analysis</h3>
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
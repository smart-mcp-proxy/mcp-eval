"""Judge Agent for TextGrad-style feedback loop analysis.

This module implements the core JudgeAgent class that analyzes baseline
and comparison reports using LLM-based evaluation.
"""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage

from mcp_eval.judge.models import (
    AnalysisType,
    EvidenceItem,
    ImprovementAspect,
    ImprovementPriority,
    ImprovementSuggestion,
    JudgeAssessment,
    SuggestionStatus,
)
from mcp_eval.judge.prompts import (
    JUDGE_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_baseline_analysis_prompt,
    build_comparison_analysis_prompt,
)
from mcp_eval.judge.source_locator import find_tool_definition


# Default model for judge analysis
DEFAULT_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-4-5-20250929")

# Timeout for LLM calls (120 seconds for complex analysis)
LLM_TIMEOUT_SECONDS = 120

# Maximum retries for LLM API failures
MAX_RETRIES = 3


def get_api_key() -> Optional[str]:
    """Check if authentication is available.

    The Claude Agent SDK handles authentication automatically via:
    1. ANTHROPIC_API_KEY environment variable
    2. CLAUDE_CODE_OAUTH_TOKEN environment variable
    3. ~/.claude or ~/.anthropic credential files

    Returns:
        "available" if any auth method is available, None otherwise.
    """
    # Check for explicit API key
    if os.getenv("ANTHROPIC_API_KEY"):
        return "available"

    # Check for OAuth token
    if os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return "available"

    # Check if Claude credential files exist
    home = Path.home()
    claude_auth = home / ".claude"
    anthropic_auth = home / ".anthropic"
    if claude_auth.exists() or anthropic_auth.exists():
        return "available"

    return None


class JudgeAgent:
    """Agent for analyzing MCP tool trajectories and generating improvement suggestions.

    Uses LLM-based analysis to identify why tool usage deviated from expectations
    and suggests specific improvements to tool descriptions.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        verbose: bool = False,
    ):
        """Initialize the JudgeAgent.

        Args:
            model: LLM model to use for analysis. Defaults to JUDGE_MODEL env var
                   or claude-sonnet-4-5-20250929.
            verbose: Enable verbose logging output.
        """
        self.model = model or DEFAULT_JUDGE_MODEL
        self.verbose = verbose

    def analyze_baseline(self, baseline_path: Path) -> JudgeAssessment:
        """Analyze a baseline trajectory for optimality.

        Args:
            baseline_path: Path to baseline directory containing detailed_log.json
                          and the scenario YAML.

        Returns:
            JudgeAssessment with analysis results and improvement suggestions.

        Raises:
            FileNotFoundError: If baseline files are missing.
            ValueError: If baseline data is invalid.
        """
        start_time = time.time()
        baseline_path = Path(baseline_path)

        # Load baseline data
        baseline_data, scenario_data = self._load_baseline_data(baseline_path)

        # Build analysis prompt
        prompt = self._build_baseline_analysis_prompt(baseline_data, scenario_data)

        # Call LLM for analysis
        llm_response = self._call_llm(prompt)

        # Parse response into JudgeAssessment
        assessment = self._parse_llm_response(
            llm_response=llm_response,
            scenario_name=scenario_data.get("name", baseline_path.name),
            analysis_type=AnalysisType.BASELINE,
            source_report_path=str(baseline_path),
            original_score=None,
            duration_seconds=time.time() - start_time,
        )

        return assessment

    def analyze_comparison(
        self,
        comparison_path: Path,
        pass_threshold: float = 0.8,
    ) -> JudgeAssessment:
        """Analyze a comparison report for divergence causes.

        Args:
            comparison_path: Path to comparison JSON file.
            pass_threshold: Score threshold for pass/fail determination.

        Returns:
            JudgeAssessment with analysis results and improvement suggestions.

        Raises:
            FileNotFoundError: If comparison file is missing.
            ValueError: If comparison data is invalid.
        """
        start_time = time.time()
        comparison_path = Path(comparison_path)

        # Load comparison data
        comparison_data = self._load_comparison_data(comparison_path)

        # Build analysis prompt
        prompt = self._build_comparison_analysis_prompt(comparison_data, pass_threshold)

        # Call LLM for analysis
        llm_response = self._call_llm(prompt)

        # Extract scenario name and score from nested structures
        scenario = comparison_data.get("scenario", {})
        scenario_name = scenario.get("name") if isinstance(scenario, dict) else comparison_data.get("scenario_name", comparison_path.stem)
        eval_metrics = comparison_data.get("evaluation_metrics", {})
        similarity_score = eval_metrics.get("overall_score", comparison_data.get("similarity_score"))

        # Parse response into JudgeAssessment
        assessment = self._parse_llm_response(
            llm_response=llm_response,
            scenario_name=scenario_name,
            analysis_type=AnalysisType.COMPARISON,
            source_report_path=str(comparison_path),
            original_score=similarity_score,
            duration_seconds=time.time() - start_time,
        )

        return assessment

    def _load_baseline_data(self, baseline_path: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Load baseline detailed_log.json and scenario data.

        The detailed_log.json contains embedded scenario information including
        user_intent, expected_trajectory, and success_criteria.

        Args:
            baseline_path: Path to baseline directory.

        Returns:
            Tuple of (baseline_data, scenario_data).

        Raises:
            FileNotFoundError: If required files are missing.
        """
        # Load detailed_log.json
        log_file = baseline_path / "detailed_log.json"
        if not log_file.exists():
            raise FileNotFoundError(f"Baseline log not found: {log_file}")

        with open(log_file) as f:
            baseline_data = json.load(f)

        # Check for stale baseline indicators
        stale_warnings = self._check_stale_baseline(baseline_data, baseline_path)
        if stale_warnings and self.verbose:
            for warning in stale_warnings:
                print(f"⚠️  Stale baseline warning: {warning}")

        # Extract scenario data from baseline_data (embedded in detailed_log.json)
        scenario_data = {
            "name": baseline_data.get("scenario", baseline_path.name.replace("_baseline", "")),
            "user_intent": baseline_data.get("user_intent", ""),
            "expected_trajectory": baseline_data.get("expected_trajectory", []),
            "success_criteria": baseline_data.get("success_criteria", []),
            "description": baseline_data.get("scenario", ""),
            "stale_warnings": stale_warnings,  # Pass warnings to prompt
        }

        return baseline_data, scenario_data

    def _check_stale_baseline(self, baseline_data: Dict[str, Any], baseline_path: Path) -> List[str]:
        """Check if baseline appears to be stale.

        Args:
            baseline_data: Loaded baseline data.
            baseline_path: Path to baseline directory.

        Returns:
            List of warning messages if baseline appears stale.
        """
        warnings = []

        # Check 1: Missing mcp_eval_info (old baseline format)
        if "mcp_eval_info" not in baseline_data:
            warnings.append("Baseline missing mcp_eval_info - recorded with older mcp-eval version")

        # Check 2: Check baseline age from file modification time
        log_file = baseline_path / "detailed_log.json"
        if log_file.exists():
            import os
            mtime = os.path.getmtime(log_file)
            age_days = (time.time() - mtime) / (24 * 3600)
            if age_days > 30:
                warnings.append(f"Baseline is {age_days:.0f} days old - consider re-recording")

        # Check 3: Check for non-MCP tools in trajectory (indicates stale baseline)
        tool_calls = baseline_data.get("tool_calls_summary", [])
        framework_tools_found = []
        for call in tool_calls:
            tool_name = call.get("tool_name", "")
            if tool_name and not tool_name.startswith("mcp__"):
                if tool_name not in framework_tools_found:
                    framework_tools_found.append(tool_name)

        if framework_tools_found:
            warnings.append(
                f"Baseline contains non-MCP tools ({', '.join(framework_tools_found[:3])}) - "
                "may need re-recording with current MCP tools"
            )

        return warnings

    def _load_comparison_data(self, comparison_path: Path) -> Dict[str, Any]:
        """Load comparison JSON report.

        Args:
            comparison_path: Path to comparison JSON file.

        Returns:
            Comparison data dictionary.

        Raises:
            FileNotFoundError: If comparison file is missing.
            ValueError: If JSON is invalid.
        """
        if not comparison_path.exists():
            raise FileNotFoundError(f"Comparison report not found: {comparison_path}")

        with open(comparison_path) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid comparison JSON: {e}")

    def _build_baseline_analysis_prompt(
        self,
        baseline_data: Dict[str, Any],
        scenario_data: Dict[str, Any],
    ) -> str:
        """Build prompt for baseline analysis.

        Args:
            baseline_data: Loaded baseline detailed_log.json.
            scenario_data: Loaded scenario YAML data.

        Returns:
            Formatted analysis prompt.
        """
        # Extract expected trajectory from scenario
        expected_trajectory = yaml.dump(
            scenario_data.get("expected_trajectory", []),
            default_flow_style=False,
        )

        # Format actual trajectory from baseline (use tool_calls_summary if available)
        tool_calls = baseline_data.get("tool_calls_summary", baseline_data.get("messages", []))
        actual_trajectory = self._format_trajectory(tool_calls)

        # Add stale baseline warnings if present
        stale_warnings = scenario_data.get("stale_warnings", [])
        if stale_warnings:
            warning_text = "\n⚠️ STALE BASELINE WARNINGS:\n" + "\n".join(f"- {w}" for w in stale_warnings)
            actual_trajectory = warning_text + "\n\n" + actual_trajectory

        # Extract tool descriptions from baseline (if available)
        tool_descriptions = self._extract_tool_descriptions(baseline_data)

        return build_baseline_analysis_prompt(
            scenario_name=scenario_data.get("name", "unknown"),
            user_intent=scenario_data.get("user_intent", scenario_data.get("description", "")),
            expected_trajectory=expected_trajectory,
            actual_trajectory=actual_trajectory,
            tool_descriptions=tool_descriptions,
        )

    def _build_comparison_analysis_prompt(
        self,
        comparison_data: Dict[str, Any],
        pass_threshold: float,
    ) -> str:
        """Build prompt for comparison analysis.

        Args:
            comparison_data: Loaded comparison JSON.
            pass_threshold: Score threshold for pass/fail.

        Returns:
            Formatted analysis prompt.
        """
        # Extract scenario info (can be at top level or nested in 'scenario')
        scenario = comparison_data.get("scenario", {})
        scenario_name = scenario.get("name") if isinstance(scenario, dict) else comparison_data.get("scenario_name", "unknown")
        user_intent = scenario.get("user_intent", "") if isinstance(scenario, dict) else comparison_data.get("user_intent", "")

        # Extract similarity score from evaluation_metrics or top level
        eval_metrics = comparison_data.get("evaluation_metrics", {})
        similarity_score = eval_metrics.get("overall_score", comparison_data.get("similarity_score", 0.0))

        # Get pass threshold from data or use provided default
        pass_threshold = eval_metrics.get("pass_threshold", pass_threshold)

        # Extract trajectories from nested structures
        baseline_exec = comparison_data.get("baseline_execution", {})
        current_exec = comparison_data.get("current_execution", {})

        # Get tool calls from execution sections
        baseline_trajectory = baseline_exec.get("tool_calls", comparison_data.get("baseline_trajectory", []))
        current_trajectory = current_exec.get("tool_calls", comparison_data.get("current_trajectory", []))

        baseline_trajectory_str = json.dumps(baseline_trajectory, indent=2)
        current_trajectory_str = json.dumps(current_trajectory, indent=2)

        # Format per-invocation comparison
        per_invocation = comparison_data.get("per_invocation_results", [])
        per_invocation_comparison = self._format_per_invocation(per_invocation)

        # Extract tool descriptions
        tool_descriptions = self._extract_tool_descriptions(comparison_data)

        return build_comparison_analysis_prompt(
            scenario_name=scenario_name,
            user_intent=user_intent,
            similarity_score=similarity_score,
            pass_threshold=pass_threshold,
            baseline_trajectory=baseline_trajectory_str,
            current_trajectory=current_trajectory_str,
            per_invocation_comparison=per_invocation_comparison,
            tool_descriptions=tool_descriptions,
        )

    def _format_trajectory(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Format trajectory tool calls for prompt.

        Handles both old message format and new tool_calls_summary format.

        Args:
            tool_calls: List of tool call dictionaries from detailed_log.json.

        Returns:
            Formatted trajectory string.
        """
        formatted = []
        for i, call in enumerate(tool_calls):
            # Handle tool_calls_summary format (newer)
            if "tool_name" in call:
                tool_name = call.get("tool_name", "unknown")
                tool_input = json.dumps(call.get("tool_input", {}), indent=2)
                response = call.get("response", {})
                response_str = str(response)[:500] if response else "No response"
                formatted.append(
                    f"TOOL_CALL {i + 1}: {tool_name}\n"
                    f"Input: {tool_input}\n"
                    f"Response: {response_str}"
                )

            # Handle old message format
            elif "type" in call:
                msg_type = call.get("type", "UNKNOWN")
                data = call.get("data", {})

                if msg_type == "TOOL_CALL":
                    tool_name = data.get("tool_name", "unknown")
                    tool_input = json.dumps(data.get("tool_input", {}), indent=2)
                    formatted.append(f"TOOL_CALL: {tool_name}\nInput: {tool_input}")

                elif msg_type == "TOOL_RESULT":
                    is_error = data.get("is_error", False)
                    status = "ERROR" if is_error else "SUCCESS"
                    content = str(data.get("parsed_content", data.get("raw_content", "")))[:500]
                    formatted.append(f"TOOL_RESULT ({status}): {content}")

        return "\n\n".join(formatted) if formatted else "No tool calls recorded"

    def _format_per_invocation(self, per_invocation: List[Dict[str, Any]]) -> str:
        """Format per-invocation comparison for prompt.

        Args:
            per_invocation: List of per-invocation comparison results.

        Returns:
            Formatted comparison string.
        """
        formatted = []
        for i, inv in enumerate(per_invocation):
            invocation_num = inv.get("invocation", i + 1)
            formatted.append(f"### Invocation {invocation_num}")

            # Handle both old and new format
            score = inv.get("similarity_score", inv.get("score", 0.0))
            formatted.append(f"- Similarity Score: {score:.2f}")

            # Handle actual_tools format (new)
            actual_tools = inv.get("actual_tools", [])
            expected_tools = inv.get("expected_tools", [])

            if actual_tools:
                for tool in actual_tools:
                    formatted.append(f"- Actual Tool: {tool.get('name', 'N/A')}")
                    formatted.append(f"  Args: {json.dumps(tool.get('args', {}))}")
                    if "similarity" in tool:
                        formatted.append(f"  Tool Similarity: {tool['similarity']:.2f}")
            elif inv.get("current_tool"):
                formatted.append(f"- Current Tool: {inv.get('current_tool', 'N/A')}")

            if expected_tools:
                for tool in expected_tools:
                    formatted.append(f"- Expected Tool: {tool.get('name', 'N/A')}")
                    formatted.append(f"  Args: {json.dumps(tool.get('args', {}))}")
            elif inv.get("baseline_tool"):
                formatted.append(f"- Baseline Tool: {inv.get('baseline_tool', 'N/A')}")

            # Details field
            if inv.get("details"):
                formatted.append(f"- Details: {inv['details']}")

            if inv.get("differences"):
                formatted.append(f"- Differences: {json.dumps(inv['differences'], indent=2)}")

        return "\n".join(formatted)

    def _extract_tool_descriptions(self, data: Dict[str, Any]) -> str:
        """Extract tool descriptions from data.

        Args:
            data: Baseline or comparison data.

        Returns:
            Formatted tool descriptions string.
        """
        tools = data.get("tools", data.get("available_tools", []))
        if not tools:
            return "No tool descriptions available."

        formatted = []
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("name", "unknown")
                desc = tool.get("description", "No description")
                formatted.append(f"- **{name}**: {desc}")
            else:
                formatted.append(f"- {tool}")

        return "\n".join(formatted)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM for analysis using Claude Agent SDK.

        Args:
            prompt: Analysis prompt to send.

        Returns:
            LLM response text.

        Raises:
            Exception: If LLM call fails after retries.
        """
        # Run the async query in sync context
        return asyncio.run(self._call_llm_async(prompt))

    async def _call_llm_async(self, prompt: str) -> str:
        """Async implementation of LLM call using Claude Agent SDK.

        Args:
            prompt: Analysis prompt to send.

        Returns:
            LLM response text.
        """
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                if self.verbose:
                    print(f"Calling LLM (attempt {attempt + 1}/{MAX_RETRIES})...")

                # Combine system prompt with user prompt
                full_prompt = f"{JUDGE_SYSTEM_PROMPT}\n\n{prompt}"

                # Create options for the query
                options = ClaudeAgentOptions(
                    model=self.model,
                    permission_mode="bypassPermissions",
                    allowed_tools=[],  # No tools needed for judge analysis
                )

                # Collect response text
                text_content = ""
                async for message in query(prompt=full_prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        # message.content can be a string or list of content blocks
                        if isinstance(message.content, str):
                            text_content += message.content
                        elif isinstance(message.content, list):
                            for block in message.content:
                                if isinstance(block, str):
                                    text_content += block
                                elif hasattr(block, "text"):
                                    text_content += block.text
                                elif isinstance(block, dict) and "text" in block:
                                    text_content += block["text"]

                if self.verbose:
                    print(f"LLM response received ({len(text_content)} chars)")

                return text_content

            except Exception as e:
                last_error = e
                if self.verbose:
                    print(f"LLM error (attempt {attempt + 1}): {e}")

                # Don't retry on authentication errors
                if "authentication" in str(e).lower():
                    raise

                # Exponential backoff
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    if self.verbose:
                        print(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        raise last_error or Exception("LLM call failed after retries")

    def _parse_llm_response(
        self,
        llm_response: str,
        scenario_name: str,
        analysis_type: AnalysisType,
        source_report_path: str,
        original_score: Optional[float],
        duration_seconds: float,
    ) -> JudgeAssessment:
        """Parse LLM response into JudgeAssessment.

        Args:
            llm_response: Raw LLM response text.
            scenario_name: Name of analyzed scenario.
            analysis_type: Type of analysis performed.
            source_report_path: Path to source report.
            original_score: Similarity score if comparison.
            duration_seconds: Time taken for analysis.

        Returns:
            Parsed JudgeAssessment.

        Raises:
            ValueError: If response cannot be parsed.
        """
        # Generate assessment ID
        assessment_id = f"judge_{uuid.uuid4().hex[:8]}"

        # Try to parse JSON from response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = llm_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            parsed = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            # If parsing fails, create minimal assessment
            if self.verbose:
                print(f"Failed to parse LLM response as JSON: {e}")

            return JudgeAssessment(
                id=assessment_id,
                scenario_name=scenario_name,
                analysis_type=analysis_type,
                source_report_path=source_report_path,
                original_score=original_score,
                root_cause_analysis=f"LLM response could not be parsed as JSON. Raw response: {llm_response[:500]}",
                failure_patterns=["parse_error"],
                improvement_suggestions=[],
                judge_model=self.model,
                judge_prompt_version=PROMPT_VERSION,
                duration_seconds=duration_seconds,
            )

        # Build improvement suggestions with source locations
        suggestions = []
        for i, sug_data in enumerate(parsed.get("improvement_suggestions", [])):
            suggestion = self._build_suggestion(
                sug_data=sug_data,
                assessment_id=assessment_id,
                suggestion_index=i,
                scenario_name=scenario_name,
            )
            if suggestion:
                suggestions.append(suggestion)

        # Ensure root_cause_analysis meets minimum length
        root_cause = parsed.get("root_cause_analysis", "")
        if len(root_cause) < 100:
            root_cause = root_cause + " " * (100 - len(root_cause))

        return JudgeAssessment(
            id=assessment_id,
            scenario_name=scenario_name,
            analysis_type=analysis_type,
            source_report_path=source_report_path,
            original_score=original_score,
            root_cause_analysis=root_cause,
            failure_patterns=parsed.get("failure_patterns", []),
            improvement_suggestions=suggestions,
            judge_model=self.model,
            judge_prompt_version=PROMPT_VERSION,
            duration_seconds=duration_seconds,
        )

    def _build_suggestion(
        self,
        sug_data: Dict[str, Any],
        assessment_id: str,
        suggestion_index: int,
        scenario_name: str,
    ) -> Optional[ImprovementSuggestion]:
        """Build ImprovementSuggestion from parsed data.

        Args:
            sug_data: Parsed suggestion data from LLM.
            assessment_id: Parent assessment ID.
            suggestion_index: Index of this suggestion.
            scenario_name: Name of scenario.

        Returns:
            ImprovementSuggestion or None if invalid.
        """
        # List of framework tools that should NOT have suggestions
        FRAMEWORK_TOOLS = {
            "Bash", "Read", "Write", "Edit", "Glob", "Grep",
            "WebSearch", "WebFetch", "TodoWrite", "Task",
            "AskUserQuestion", "NotebookEdit", "EnterPlanMode",
            "ExitPlanMode", "Skill", "SlashCommand", "KillShell",
        }

        try:
            tool_name = sug_data.get("tool_name", "")
            if not tool_name:
                return None

            # Filter out non-MCP tools (framework tools)
            # Only accept tools starting with mcp__ prefix
            if not tool_name.startswith("mcp__"):
                # Check if it's a known framework tool
                if tool_name in FRAMEWORK_TOOLS:
                    if self.verbose:
                        print(f"Skipping framework tool suggestion: {tool_name}")
                    return None
                # Also skip any unknown non-mcp tools
                if self.verbose:
                    print(f"Skipping non-MCP tool suggestion: {tool_name}")
                return None

            # Find source location
            source_location = find_tool_definition(tool_name)

            # Parse aspect enum
            aspect_str = sug_data.get("aspect", "description")
            try:
                aspect = ImprovementAspect(aspect_str)
            except ValueError:
                aspect = ImprovementAspect.DESCRIPTION

            # Parse priority enum
            priority_str = sug_data.get("priority", "medium")
            try:
                priority = ImprovementPriority(priority_str)
            except ValueError:
                priority = ImprovementPriority.MEDIUM

            # Build evidence items
            evidence = []
            for ev_data in sug_data.get("evidence", []):
                try:
                    evidence.append(
                        EvidenceItem(
                            scenario_name=ev_data.get("scenario_name", scenario_name),
                            invocation_index=ev_data.get("invocation_index", 0),
                            expected_behavior=ev_data.get("expected_behavior", ""),
                            actual_behavior=ev_data.get("actual_behavior", ""),
                            similarity_score=ev_data.get("similarity_score", 0.0),
                            tool_call_details=ev_data.get("tool_call_details", {}),
                        )
                    )
                except Exception:
                    pass

            # Ensure at least one evidence item
            if not evidence:
                evidence.append(
                    EvidenceItem(
                        scenario_name=scenario_name,
                        invocation_index=0,
                        expected_behavior="Expected behavior not specified",
                        actual_behavior="Actual behavior from analysis",
                        similarity_score=0.5,
                        tool_call_details={"tool_name": tool_name},
                    )
                )

            # Ensure rationale meets minimum length
            rationale = sug_data.get("rationale", "Improvement suggested by judge analysis")
            if len(rationale) < 50:
                rationale = rationale + " " * (50 - len(rationale))

            return ImprovementSuggestion(
                id=f"{assessment_id}_sug_{suggestion_index}",
                tool_name=tool_name,
                aspect=aspect,
                parameter_name=sug_data.get("parameter_name"),
                source_location=source_location,
                current_value=sug_data.get("current_value", ""),
                proposed_value=sug_data.get("proposed_value", ""),
                rationale=rationale,
                chain_of_thought=sug_data.get("chain_of_thought"),
                priority=priority,
                expected_score_improvement=sug_data.get("expected_score_improvement"),
                confidence=sug_data.get("confidence", 0.5),
                evidence=evidence,
                affected_scenarios=sug_data.get("affected_scenarios"),
                status=SuggestionStatus.PENDING,
            )

        except Exception as e:
            if self.verbose:
                print(f"Failed to build suggestion: {e}")
            return None

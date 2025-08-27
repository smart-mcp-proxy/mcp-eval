"""Trajectory evaluation and comparison engine."""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .similarity import calculate_trajectory_similarity, calculate_tool_call_similarity

# Define required classes locally since trajectory_evaluator.py was removed
@dataclass
class ToolCall:
    """Represents a single tool call."""
    name: str
    args: Dict[str, Any]

@dataclass
class Invocation:
    """Represents a single invocation with one or more tool calls."""
    tool_calls: List[ToolCall]

@dataclass
class InvocationResult:
    """Result of comparing a single invocation."""
    invocation: int
    score: float
    details: str
    actual_tools: List[Dict[str, Any]]
    expected_tools: List[Dict[str, Any]]

@dataclass
class EvaluationResult:
    """Result of trajectory evaluation."""
    overall_score: float
    per_invocation_results: List[InvocationResult]

class BaseTrajectoryEvaluator:
    """Basic trajectory evaluator for comparing tool invocations."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def evaluate_invocations(
        self, 
        current_invocations: List[Invocation], 
        baseline_invocations: List[Invocation]
    ) -> EvaluationResult:
        """Compare current invocations against baseline."""
        per_invocation_results = []
        
        # Simple comparison - match by index
        max_len = max(len(current_invocations), len(baseline_invocations))
        
        for i in range(max_len):
            current_inv = current_invocations[i] if i < len(current_invocations) else None
            baseline_inv = baseline_invocations[i] if i < len(baseline_invocations) else None
            
            if current_inv and baseline_inv:
                # Compare tool calls
                score = self._compare_invocations(current_inv, baseline_inv)
                details = "MATCH" if score == 1.0 else "MISMATCH"
                
                actual_tools = [{"name": tc.name, "args": tc.args} for tc in current_inv.tool_calls]
                expected_tools = [{"name": tc.name, "args": tc.args} for tc in baseline_inv.tool_calls]
                
            elif current_inv and not baseline_inv:
                score = 0.0
                details = "EXTRA INVOCATION"
                actual_tools = [{"name": tc.name, "args": tc.args} for tc in current_inv.tool_calls]
                expected_tools = []
                
            elif not current_inv and baseline_inv:
                score = 0.0
                details = "MISSING INVOCATION"
                actual_tools = []
                expected_tools = [{"name": tc.name, "args": tc.args} for tc in baseline_inv.tool_calls]
            else:
                continue
            
            per_invocation_results.append(InvocationResult(
                invocation=i + 1,
                score=score,
                details=f"Invocation {i + 1}: {details}",
                actual_tools=actual_tools,
                expected_tools=expected_tools
            ))
        
        # Calculate overall score as average of individual invocation scores
        overall_score = sum(r.score for r in per_invocation_results) / len(per_invocation_results) if per_invocation_results else 0.0
        
        return EvaluationResult(
            overall_score=overall_score,
            per_invocation_results=per_invocation_results
        )
    
    def _compare_invocations(self, current: Invocation, baseline: Invocation) -> float:
        """Compare two invocations and return similarity score."""
        if len(current.tool_calls) != len(baseline.tool_calls):
            return 0.0
        
        # Simple exact match for now
        for curr_tc, base_tc in zip(current.tool_calls, baseline.tool_calls):
            if curr_tc.name != base_tc.name or curr_tc.args != base_tc.args:
                return 0.0
        
        return 1.0


@dataclass 
class ComparisonResult:
    """Result of comparing two scenario executions."""
    overall_score: float
    tool_trajectory_score: float
    per_invocation_results: List[InvocationResult]
    execution_time_diff: float
    tool_count_diff: int
    success_status_match: bool
    detailed_comparison: Dict[str, Any]
    # New failure-aware fields
    execution_status: str  # "SUCCESS", "BLOCKED", "FAILED", "DEGRADED"
    failure_analysis: Dict[str, Any]
    early_stopped: bool
    blocking_failure_step: Optional[int]


class TrajectoryEvaluator:
    """Enhanced trajectory evaluator for MCP scenario comparison with failure-aware logic."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.base_evaluator = BaseTrajectoryEvaluator(threshold)
        # Critical tool operations that block subsequent execution
        self.critical_operations = {
            "add", "create", "initialize", "connect", "setup"
        }
    
    def compare_executions(
        self, 
        current_log: Dict[str, Any], 
        baseline_log: Dict[str, Any]
    ) -> ComparisonResult:
        """
        Compare current execution against baseline with failure-aware analysis.
        
        Args:
            current_log: Detailed log from current execution
            baseline_log: Detailed log from baseline execution
            
        Returns:
            ComparisonResult with detailed comparison metrics and failure analysis
        """
        # Extract tool calls and analyze failures
        current_tools = current_log.get("tool_calls_summary", [])
        baseline_tools = baseline_log.get("tool_calls_summary", [])
        
        # Analyze execution status and failure patterns
        current_analysis = self._analyze_execution_status(current_tools)
        baseline_analysis = self._analyze_execution_status(baseline_tools)
        
        # Determine if comparison is valid or if early stopping should occur
        if current_analysis["status"] == "BLOCKED" and baseline_analysis["status"] == "SUCCESS":
            # Current execution blocked, baseline succeeded - major regression
            return self._create_blocked_comparison_result(
                current_log, baseline_log, current_analysis, baseline_analysis
            )
        
        # Use new similarity-based trajectory comparison (MCP tools only)
        similarity_score = calculate_trajectory_similarity(current_tools, baseline_tools)
        
        # Create detailed per-invocation results for compatibility
        per_invocation_results = self._create_per_invocation_results(current_tools, baseline_tools)
        
        execution_time_diff = self._calculate_time_diff(current_log, baseline_log)
        tool_count_diff = len(current_tools) - len(baseline_tools)
        
        # Compare success status
        success_status_match = current_analysis["status"] == baseline_analysis["status"]
        
        # Enhanced failure analysis
        failure_analysis = {
            "current_failures": current_analysis["failures"],
            "baseline_failures": baseline_analysis["failures"],
            "new_failures": current_analysis["failures"] - baseline_analysis["failures"],
            "resolved_failures": baseline_analysis["failures"] - current_analysis["failures"],
            "failure_cascade": self._detect_failure_cascade(current_tools),
            "critical_operations_affected": self._analyze_critical_operations(current_tools, baseline_tools)
        }
        
        # Detailed comparison
        detailed_comparison = {
            "trajectory_matches": similarity_score,
            "current_tool_count": len(current_tools),
            "baseline_tool_count": len(baseline_tools),
            "tool_differences": self._analyze_tool_differences(current_tools, baseline_tools),
            "execution_status_comparison": {
                "current": current_analysis["status"],
                "baseline": baseline_analysis["status"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate overall score with failure awareness
        overall_score = self._calculate_failure_aware_score(
            similarity_score,
            current_analysis,
            baseline_analysis,
            tool_count_diff,
            success_status_match
        )
        
        return ComparisonResult(
            overall_score=overall_score,
            tool_trajectory_score=similarity_score,
            per_invocation_results=per_invocation_results,
            execution_time_diff=execution_time_diff,
            tool_count_diff=tool_count_diff,
            success_status_match=success_status_match,
            detailed_comparison=detailed_comparison,
            execution_status=current_analysis["status"],
            failure_analysis=failure_analysis,
            early_stopped=current_analysis["early_stopped"],
            blocking_failure_step=current_analysis["blocking_step"]
        )
    
    def _create_per_invocation_results(
        self, 
        current_tools: List[Dict[str, Any]], 
        baseline_tools: List[Dict[str, Any]]
    ) -> List[InvocationResult]:
        """Create detailed per-invocation results using similarity calculations."""
        # Filter to only MCP tool calls
        current_mcp = [call for call in current_tools if call.get('tool_name', '').startswith('mcp__')]
        baseline_mcp = [call for call in baseline_tools if call.get('tool_name', '').startswith('mcp__')]
        
        max_len = max(len(current_mcp), len(baseline_mcp))
        results = []
        
        for i in range(max_len):
            current_call = current_mcp[i] if i < len(current_mcp) else None
            baseline_call = baseline_mcp[i] if i < len(baseline_mcp) else None
            
            if current_call and baseline_call:
                # Both calls exist - calculate similarity
                similarity = calculate_tool_call_similarity(current_call, baseline_call)
                if similarity == 1.0:
                    details = "EXACT MATCH"
                elif similarity >= 0.8:
                    details = f"SIMILAR (similarity: {similarity:.3f})"
                elif similarity > 0.0:
                    details = f"PARTIAL MATCH (similarity: {similarity:.3f})"
                else:
                    details = "MISMATCH"
                
                actual_tools = [{
                    "name": current_call.get("tool_name", ""),
                    "args": current_call.get("tool_input", {}),
                    "similarity": similarity
                }]
                expected_tools = [{
                    "name": baseline_call.get("tool_name", ""),
                    "args": baseline_call.get("tool_input", {})
                }]
                
            elif current_call and not baseline_call:
                # Extra call in current
                similarity = 0.0
                details = "EXTRA CALL"
                actual_tools = [{
                    "name": current_call.get("tool_name", ""),
                    "args": current_call.get("tool_input", {}),
                    "similarity": similarity
                }]
                expected_tools = []
                
            elif not current_call and baseline_call:
                # Missing call in current
                similarity = 0.0
                details = "MISSING CALL"
                actual_tools = []
                expected_tools = [{
                    "name": baseline_call.get("tool_name", ""),
                    "args": baseline_call.get("tool_input", {})
                }]
            else:
                continue
            
            results.append(InvocationResult(
                invocation=i + 1,
                score=similarity,
                details=f"Invocation {i + 1}: {details}",
                actual_tools=actual_tools,
                expected_tools=expected_tools
            ))
        
        return results

    def _extract_invocations(self, execution_log: Dict[str, Any]) -> List[Invocation]:
        """Extract tool invocations from execution log."""
        invocations = []
        
        # Get tool calls from summary
        tool_calls_summary = execution_log.get("tool_calls_summary", [])
        
        for tool_call_data in tool_calls_summary:
            tool_call = ToolCall(
                name=tool_call_data.get("tool_name", ""),
                args=tool_call_data.get("tool_input", {})
            )
            
            # Create invocation with single tool call
            # In future, could group related tool calls into single invocations
            invocation = Invocation(tool_calls=[tool_call])
            invocations.append(invocation)
        
        return invocations
    
    def _calculate_time_diff(self, current_log: Dict[str, Any], baseline_log: Dict[str, Any]) -> float:
        """Calculate execution time difference."""
        # This would need access to execution times from logs
        # For now, return 0 as placeholder
        return 0.0
    
    def _compare_success_status(self, current_log: Dict[str, Any], baseline_log: Dict[str, Any]) -> bool:
        """Compare success status between executions."""
        # Extract success status from logs if available
        # For now, return True as placeholder
        return True
    
    def _analyze_tool_differences(
        self, 
        current_tools: List[Dict[str, Any]], 
        baseline_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze differences in tool usage."""
        current_tool_names = set(tool.get("tool_name", "") for tool in current_tools)
        baseline_tool_names = set(tool.get("tool_name", "") for tool in baseline_tools)
        
        return {
            "tools_added": list(current_tool_names - baseline_tool_names),
            "tools_removed": list(baseline_tool_names - current_tool_names),
            "tools_common": list(current_tool_names & baseline_tool_names),
            "parameter_differences": self._compare_tool_parameters(current_tools, baseline_tools)
        }
    
    def _compare_tool_parameters(
        self, 
        current_tools: List[Dict[str, Any]], 
        baseline_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compare parameters for common tools."""
        differences = []
        
        # Create lookup for baseline tools
        baseline_by_name = {
            tool.get("tool_name", ""): tool for tool in baseline_tools
        }
        
        for current_tool in current_tools:
            tool_name = current_tool.get("tool_name", "")
            baseline_tool = baseline_by_name.get(tool_name)
            
            if baseline_tool:
                current_params = current_tool.get("tool_input", {})
                baseline_params = baseline_tool.get("tool_input", {})
                
                if current_params != baseline_params:
                    differences.append({
                        "tool_name": tool_name,
                        "current_params": current_params,
                        "baseline_params": baseline_params
                    })
        
        return differences
    
    def _analyze_execution_status(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze execution status and detect failures."""
        failures = set()
        blocking_step = None
        early_stopped = False
        
        for i, tool_call in enumerate(tool_calls):
            # Check for explicit errors
            if tool_call.get("error") or (tool_call.get("response", {}).get("is_error")):
                operation = tool_call.get("tool_input", {}).get("operation", "")
                tool_name = tool_call.get("tool_name", "")
                
                failure_type = f"{tool_name}:{operation}" if operation else tool_name
                failures.add(failure_type)
                
                # Check if this is a critical operation that blocks subsequent execution
                if any(critical_op in operation.lower() for critical_op in self.critical_operations):
                    blocking_step = i
                    early_stopped = True
                    break
        
        # Determine overall execution status
        if early_stopped and blocking_step is not None:
            status = "BLOCKED"
        elif failures:
            status = "FAILED"
        elif len(tool_calls) == 0:
            status = "EMPTY"
        else:
            status = "SUCCESS"
        
        return {
            "status": status,
            "failures": failures,
            "blocking_step": blocking_step,
            "early_stopped": early_stopped,
            "total_tools": len(tool_calls)
        }
    
    def _create_blocked_comparison_result(
        self, 
        current_log: Dict[str, Any], 
        baseline_log: Dict[str, Any],
        current_analysis: Dict[str, Any],
        baseline_analysis: Dict[str, Any]
    ) -> ComparisonResult:
        """Create comparison result for blocked execution."""
        current_tools = current_log.get("tool_calls_summary", [])
        baseline_tools = baseline_log.get("tool_calls_summary", [])
        
        failure_analysis = {
            "execution_blocked": True,
            "blocking_failure": list(current_analysis["failures"])[0] if current_analysis["failures"] else "unknown",
            "baseline_succeeded": baseline_analysis["status"] == "SUCCESS",
            "tools_executed_before_failure": current_analysis["blocking_step"] or 0,
            "expected_remaining_tools": len(baseline_tools) - (current_analysis["blocking_step"] or 0),
            "regression_severity": "CRITICAL"  # Baseline worked, current blocked
        }
        
        detailed_comparison = {
            "trajectory_matches": 0.0,  # Cannot compare blocked vs success
            "current_tool_count": len(current_tools),
            "baseline_tool_count": len(baseline_tools),
            "execution_status_comparison": {
                "current": "BLOCKED",
                "baseline": "SUCCESS",
                "regression": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return ComparisonResult(
            overall_score=0.0,  # Blocked execution = complete failure
            tool_trajectory_score=0.0,
            per_invocation_results=[],
            execution_time_diff=0.0,
            tool_count_diff=len(current_tools) - len(baseline_tools),
            success_status_match=False,
            detailed_comparison=detailed_comparison,
            execution_status="BLOCKED",
            failure_analysis=failure_analysis,
            early_stopped=True,
            blocking_failure_step=current_analysis["blocking_step"]
        )
    
    def _detect_failure_cascade(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect if failures cascaded from earlier critical failures."""
        cascade = []
        critical_failure_found = False
        
        for i, tool_call in enumerate(tool_calls):
            if tool_call.get("error") or (tool_call.get("response", {}).get("is_error")):
                operation = tool_call.get("tool_input", {}).get("operation", "")
                
                # Check if this is a critical operation failure
                is_critical = any(critical_op in operation.lower() for critical_op in self.critical_operations)
                
                cascade.append({
                    "step": i,
                    "tool": tool_call.get("tool_name", ""),
                    "operation": operation,
                    "error": tool_call.get("error", "Tool returned error"),
                    "is_critical": is_critical,
                    "caused_by_earlier_failure": critical_failure_found and not is_critical
                })
                
                if is_critical:
                    critical_failure_found = True
        
        return cascade
    
    def _analyze_critical_operations(self, current_tools: List[Dict[str, Any]], baseline_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze impact on critical operations."""
        def extract_critical_ops(tools):
            critical_ops = []
            for tool in tools:
                operation = tool.get("tool_input", {}).get("operation", "")
                if any(critical_op in operation.lower() for critical_op in self.critical_operations):
                    critical_ops.append({
                        "operation": operation,
                        "tool": tool.get("tool_name", ""),
                        "success": not (tool.get("error") or tool.get("response", {}).get("is_error"))
                    })
            return critical_ops
        
        current_critical = extract_critical_ops(current_tools)
        baseline_critical = extract_critical_ops(baseline_tools)
        
        return {
            "current_critical_operations": current_critical,
            "baseline_critical_operations": baseline_critical,
            "critical_operations_regressed": [
                op for op in current_critical 
                if not op["success"] and any(b_op["operation"] == op["operation"] and b_op["success"] for b_op in baseline_critical)
            ]
        }
    
    def _calculate_failure_aware_score(
        self,
        trajectory_score: float,
        current_analysis: Dict[str, Any],
        baseline_analysis: Dict[str, Any],
        tool_count_diff: int,
        success_match: bool
    ) -> float:
        """Calculate overall score with failure awareness."""
        current_status = current_analysis["status"]
        baseline_status = baseline_analysis["status"]
        
        # Handle different status combinations
        if current_status == "BLOCKED":
            if baseline_status == "SUCCESS":
                return 0.0  # Critical regression - total failure
            elif baseline_status == "BLOCKED":
                return 0.3  # Both blocked, some partial credit for consistency
            else:
                return 0.1  # Current worse than baseline
        
        elif current_status == "FAILED":
            if baseline_status == "SUCCESS":
                return max(0.0, trajectory_score * 0.5)  # Significant regression
            elif baseline_status == "FAILED":
                return trajectory_score * 0.7  # Both failed, compare trajectories
            else:
                return trajectory_score * 0.6
        
        elif current_status == "SUCCESS":
            if baseline_status == "SUCCESS":
                # Both successful - use trajectory score with bonuses
                score = trajectory_score * 0.8
                score += 0.2 if success_match else 0.0
                score -= 0.1 if abs(tool_count_diff) > 2 else 0.0
                return max(0.0, min(1.0, score))
            else:
                # Current success, baseline failed - improvement!
                return min(1.0, trajectory_score + 0.2)
        
        # Fallback to basic trajectory score
        return max(0.0, min(1.0, trajectory_score))
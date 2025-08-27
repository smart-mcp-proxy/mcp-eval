"""Report generation for MCP evaluations."""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict, dataclass
from .evaluator import ComparisonResult

# Define ScenarioResult locally since it's needed for compatibility
@dataclass
class ScenarioResult:
    """Result of scenario execution."""
    scenario_name: str
    success: bool
    execution_time: float
    detailed_log: Dict[str, Any]
    dialog_trajectory: str
    tool_calls: List[Any]  # List of tool call records
    error: Optional[str] = None


class ReportGenerator:
    """Generates evaluation reports in various formats."""
    
    def generate_comparison_report(
        self,
        scenario_data: Dict[str, Any],
        current_result: ScenarioResult,
        baseline_log: Dict[str, Any],
        comparison_result: ComparisonResult
    ) -> Dict[str, Any]:
        """Generate detailed comparison report."""
        
        return {
            "report_type": "trajectory_comparison",
            "generated_at": datetime.now().isoformat(),
            "scenario": {
                "name": scenario_data.get("name", "unknown"),
                "description": scenario_data.get("description", ""),
                "user_intent": scenario_data.get("user_intent", ""),
                "expected_trajectory": scenario_data.get("expected_trajectory", [])
            },
            "evaluation_metrics": {
                "overall_score": comparison_result.overall_score,
                "tool_trajectory_score": comparison_result.tool_trajectory_score,
                "success_status_match": comparison_result.success_status_match,
                "execution_time_diff_seconds": comparison_result.execution_time_diff,
                "tool_count_difference": comparison_result.tool_count_diff,
                "pass_threshold": 0.8,
                "result": "PASS" if comparison_result.overall_score >= 0.8 else "FAIL"
            },
            "current_execution": {
                "success": current_result.success,
                "execution_time": current_result.execution_time,
                "tool_calls_count": len(current_result.tool_calls),
                "tool_calls": current_result.tool_calls,  # Already in dict format
                "error": current_result.error
            },
            "baseline_execution": {
                "scenario": baseline_log.get("scenario", ""),
                "execution_time": baseline_log.get("execution_time", ""),
                "tool_calls_count": len(baseline_log.get("tool_calls_summary", [])),
                "tool_calls": baseline_log.get("tool_calls_summary", [])
            },
            "detailed_comparison": comparison_result.detailed_comparison,
            "per_invocation_results": [
                {
                    "invocation": i + 1,
                    "score": result.score,
                    "details": result.details,
                    "actual_tools": result.actual_tools,
                    "expected_tools": result.expected_tools
                }
                for i, result in enumerate(comparison_result.per_invocation_results)
            ],
            "recommendations": self._generate_recommendations(comparison_result)
        }
    
    def generate_batch_report(self, batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary report for batch execution."""
        
        total_scenarios = len(batch_results)
        successful_scenarios = [r for r in batch_results if r["status"] == "SUCCESS"]
        failed_scenarios = [r for r in batch_results if r["status"] == "FAILED"]
        
        # Calculate statistics
        total_execution_time = sum(
            r.get("execution_time", 0) for r in successful_scenarios
        )
        
        total_tool_calls = sum(
            r.get("tool_calls", 0) for r in successful_scenarios
        )
        
        return {
            "report_type": "batch_execution",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_scenarios": total_scenarios,
                "successful_scenarios": len(successful_scenarios),
                "failed_scenarios": len(failed_scenarios),
                "success_rate": len(successful_scenarios) / total_scenarios * 100,
                "total_execution_time": total_execution_time,
                "average_execution_time": total_execution_time / len(successful_scenarios) if successful_scenarios else 0,
                "total_tool_calls": total_tool_calls,
                "average_tool_calls_per_scenario": total_tool_calls / len(successful_scenarios) if successful_scenarios else 0
            },
            "scenario_results": batch_results,
            "failed_scenarios_details": [
                {
                    "scenario": r["scenario"],
                    "error": r.get("error", "Unknown error")
                }
                for r in failed_scenarios
            ],
            "performance_metrics": {
                "fastest_scenario": min(successful_scenarios, key=lambda x: x.get("execution_time", float('inf')), default={}).get("scenario"),
                "slowest_scenario": max(successful_scenarios, key=lambda x: x.get("execution_time", 0), default={}).get("scenario"),
                "most_tool_calls": max(successful_scenarios, key=lambda x: x.get("tool_calls", 0), default={}).get("scenario"),
                "least_tool_calls": min(successful_scenarios, key=lambda x: x.get("tool_calls", float('inf')), default={}).get("scenario")
            },
            "recommendations": self._generate_batch_recommendations(batch_results)
        }
    
    def generate_human_readable_summary(self, report: Dict[str, Any]) -> str:
        """Generate human-readable summary from report."""
        
        if report["report_type"] == "trajectory_comparison":
            return self._format_comparison_summary(report)
        elif report["report_type"] == "batch_execution":
            return self._format_batch_summary(report)
        else:
            return "Unknown report type"
    
    def _format_comparison_summary(self, report: Dict[str, Any]) -> str:
        """Format trajectory comparison as readable text."""
        
        metrics = report["evaluation_metrics"]
        scenario = report["scenario"]
        
        summary = f"""
# MCP Evaluation Report: {scenario['name']}

## Scenario Details
- **Description**: {scenario['description']}  
- **User Intent**: {scenario['user_intent']}

## Evaluation Results
- **Overall Score**: {metrics['overall_score']:.2f}/1.00
- **Tool Trajectory Score**: {metrics['tool_trajectory_score']:.2f}/1.00
- **Result**: {metrics['result']}
- **Success Status Match**: {'✅' if metrics['success_status_match'] else '❌'}

## Execution Comparison
- **Current Execution Time**: {report['current_execution']['execution_time']:.2f}s
- **Tool Calls**: {report['current_execution']['tool_calls_count']} (Δ{metrics['tool_count_difference']:+d})

## Tool Usage Analysis
"""
        
        # Add per-invocation details
        for inv_result in report["per_invocation_results"]:
            summary += f"- **Invocation {inv_result['invocation']}**: {inv_result['details']}\n"
        
        # Add recommendations
        if report["recommendations"]:
            summary += "\n## Recommendations\n"
            for rec in report["recommendations"]:
                summary += f"- {rec}\n"
        
        return summary
    
    def _format_batch_summary(self, report: Dict[str, Any]) -> str:
        """Format batch execution as readable text."""
        
        summary_data = report["summary"]
        
        summary = f"""
# MCP Batch Evaluation Report

## Overview
- **Total Scenarios**: {summary_data['total_scenarios']}
- **Success Rate**: {summary_data['success_rate']:.1f}% ({summary_data['successful_scenarios']}/{summary_data['total_scenarios']})
- **Total Execution Time**: {summary_data['total_execution_time']:.2f}s
- **Average Time per Scenario**: {summary_data['average_execution_time']:.2f}s

## Performance Metrics
- **Fastest Scenario**: {report['performance_metrics']['fastest_scenario']}
- **Slowest Scenario**: {report['performance_metrics']['slowest_scenario']}
- **Most Tool Calls**: {report['performance_metrics']['most_tool_calls']}

## Failed Scenarios
"""
        
        for failed in report["failed_scenarios_details"]:
            summary += f"- **{failed['scenario']}**: {failed['error']}\n"
        
        return summary
    
    def _generate_recommendations(self, comparison_result: ComparisonResult) -> List[str]:
        """Generate actionable recommendations based on comparison."""
        
        recommendations = []
        
        if comparison_result.tool_trajectory_score < 0.8:
            recommendations.append(
                "Tool trajectory mismatch detected. Review expected vs actual tool calls."
            )
        
        if abs(comparison_result.tool_count_diff) > 2:
            recommendations.append(
                f"Significant difference in tool usage count ({comparison_result.tool_count_diff:+d}). "
                "Consider updating baseline or investigating efficiency."
            )
        
        if not comparison_result.success_status_match:
            recommendations.append(
                "Success status mismatch between current and baseline execution."
            )
        
        if comparison_result.overall_score >= 0.9:
            recommendations.append(
                "Excellent trajectory match! Consider this execution as a new baseline."
            )
        
        return recommendations
    
    def _generate_batch_recommendations(self, batch_results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for batch execution."""
        
        recommendations = []
        
        failed_count = len([r for r in batch_results if r["status"] == "FAILED"])
        success_rate = (len(batch_results) - failed_count) / len(batch_results) * 100
        
        if success_rate < 80:
            recommendations.append(
                f"Low success rate ({success_rate:.1f}%). Review failed scenarios and MCP server configuration."
            )
        
        if failed_count > 0:
            recommendations.append(
                f"{failed_count} scenario(s) failed. Check error details and retry with fixes."
            )
        
        # Analyze execution times
        successful_results = [r for r in batch_results if r["status"] == "SUCCESS" and "execution_time" in r]
        if successful_results:
            avg_time = sum(r["execution_time"] for r in successful_results) / len(successful_results)
            if avg_time > 30:
                recommendations.append(
                    f"High average execution time ({avg_time:.1f}s). Consider optimizing scenarios or MCP configuration."
                )
        
        return recommendations
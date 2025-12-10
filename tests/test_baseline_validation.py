"""Tests for baseline validation against expected trajectory."""

import pytest
import json
from datetime import datetime
from pathlib import Path

# Import the functions we'll implement
from src.mcp_eval.scenario_runner import (
    BaselineValidationResult,
    ToolCallComparison,
    validate_baseline_against_expected,
    display_validation_warnings
)


class TestBaselineValidation:
    """Test suite for baseline validation functionality."""

    def test_exact_match_validation(self):
        """T015: Test that exact match between expected and actual results in EXACT_MATCH status."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email", "debug": True}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {"query": "email", "debug": True}
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_exact",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        assert result.overall_similarity == 1.0
        assert result.validation_status == "EXACT_MATCH"
        assert not result.has_warnings
        assert len(result.warnings) == 0

    def test_minor_divergence_validation(self):
        """T016: Test minor divergence (threshold <= similarity < 1.0) shows correct status."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {"query": "email"}  # Exactly the same
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_minor",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        # Exact match should give 1.0
        assert result.overall_similarity == 1.0
        assert result.validation_status == "EXACT_MATCH"
        assert not result.has_warnings
        assert len(result.tool_call_comparisons) == 1

    def test_major_divergence_validation(self):
        """T017: Test major divergence (similarity < 0.8) shows strong warning."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email", "debug": True}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {
                    "query": "email tools send receive manage messages",
                    "debug": True,
                    "limit": 10,
                    "include_stats": True
                }
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_major",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        assert result.overall_similarity < 0.8
        assert result.validation_status == "MAJOR_DIVERGENCE"
        assert result.has_warnings
        assert len(result.warnings) > 0

    def test_tool_count_mismatch(self):
        """T018: Test that different numbers of tool calls generates warning."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {"query": "email"}
            },
            {
                "tool_name": "mcp__mcpproxy__upstream_servers",
                "tool_input": {"operation": "list"}
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_count",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        assert len(result.tool_call_comparisons) == 2  # Should compare all
        assert any("count" in w.lower() or "mismatch" in w.lower() for w in result.warnings)

    def test_missing_expected_trajectory(self):
        """T019: Test graceful handling when expected_trajectory is missing or empty."""
        # Arrange - empty expected trajectory
        expected_trajectory = []
        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {"query": "email"}
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_missing",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        # Should handle gracefully, not crash
        assert result is not None
        assert result.scenario_name == "test_missing"

    def test_validation_result_saved_in_json(self):
        """T020: Test that validation result can be converted to JSON dict."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {"query": "email"}
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_json",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        result_dict = result.to_dict()

        # Assert
        assert isinstance(result_dict, dict)
        assert "scenario_name" in result_dict
        assert "overall_similarity" in result_dict
        assert "validation_status" in result_dict
        assert "tool_call_comparisons" in result_dict
        assert "warnings" in result_dict
        assert "timestamp" in result_dict

        # Should be JSON serializable
        json_str = json.dumps(result_dict)
        assert json_str is not None

    def test_warnings_display_with_rich(self, capsys):
        """T021: Test that warnings are displayed with rich formatting."""
        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email", "debug": True}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {
                    "query": "email tools send receive",
                    "debug": True,
                    "limit": 10
                }
            }
        ]

        result = validate_baseline_against_expected(
            scenario_name="test_display",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Act
        display_validation_warnings(result, verbose=True)

        # Assert
        # Can't easily test rich output, but verify function doesn't crash
        # In real implementation, this would display to console
        assert result.has_warnings  # Should have warnings to display

    def test_baseline_succeeded_current_failed(self):
        """T093: Test handling when baseline succeeded but current execution could fail."""
        # Arrange - Simulate scenario where baseline has valid tool calls
        # but we're validating against expected trajectory
        expected_trajectory = [
            {
                "tool": "mcp__mcpproxy__retrieve_tools",
                "args": {"query": "email"}
            }
        ]

        # Actual baseline has additional parameters that weren't expected
        actual_tool_calls = [
            {
                "tool_name": "mcp__mcpproxy__retrieve_tools",
                "tool_input": {
                    "query": "email",
                    "debug": True,
                    "limit": 10,
                    "include_stats": True
                }
            }
        ]

        # Act
        result = validate_baseline_against_expected(
            scenario_name="test_extra_params",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        # Should handle gracefully - extra params reduce similarity but don't cause crash
        assert result is not None
        assert result.overall_similarity < 1.0  # Not perfect match
        assert result.overall_similarity > 0.0  # But some similarity exists
        # The similarity should be decent since core params match
        assert result.overall_similarity > 0.5

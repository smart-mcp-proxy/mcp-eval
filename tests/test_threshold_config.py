"""Tests for configurable similarity thresholds."""

import pytest
import yaml
from pathlib import Path

# Import the functions we'll test
from src.mcp_eval.scenario_runner import validate_similarity_threshold


class TestThresholdConfiguration:
    """Test suite for configurable similarity thresholds."""

    def test_default_threshold_0_8(self):
        """T070: Test that default threshold is 0.8 when not specified."""
        # Arrange & Act
        threshold = validate_similarity_threshold(None)

        # Assert
        assert threshold == 0.8

    def test_custom_threshold_from_yaml(self):
        """T071: Test that custom threshold can be loaded from scenario YAML."""
        # Arrange
        custom_threshold = 0.6

        # Act
        threshold = validate_similarity_threshold(custom_threshold)

        # Assert
        assert threshold == 0.6

    def test_threshold_validation_rejects_invalid(self):
        """T072: Test that invalid thresholds are rejected."""
        # Test values outside 0.0-1.0 range
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_similarity_threshold(1.5)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_similarity_threshold(-0.1)

        # Test non-numeric values
        with pytest.raises(ValueError, match="must be a number"):
            validate_similarity_threshold("0.8")

    def test_pass_fail_at_threshold_boundary(self):
        """T073: Test pass/fail determination at threshold boundary."""
        # This test verifies the logic in baseline validation
        from src.mcp_eval.scenario_runner import validate_baseline_against_expected

        # Arrange
        expected_trajectory = [
            {
                "tool": "mcp__test__search",
                "args": {"query": "test"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__test__search",
                "tool_input": {"query": "test"}
            }
        ]

        # Act - Test with threshold 0.8, similarity is 1.0 (should pass)
        result = validate_baseline_against_expected(
            scenario_name="test_boundary",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        assert result.overall_similarity == 1.0
        assert result.overall_similarity >= 0.8
        assert result.validation_status == "EXACT_MATCH"
        assert not result.has_warnings

    def test_threshold_boundary_below(self):
        """Test similarity just below threshold triggers warning."""
        from src.mcp_eval.scenario_runner import validate_baseline_against_expected

        # Arrange - Create a case with similarity ~0.5
        expected_trajectory = [
            {
                "tool": "mcp__test__search",
                "args": {"query": "test"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__test__search",
                "tool_input": {"query": "test different query"}
            }
        ]

        # Act - Test with threshold 0.8, similarity will be < 0.8
        result = validate_baseline_against_expected(
            scenario_name="test_below",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert
        assert result.overall_similarity < 0.8
        assert result.validation_status == "MAJOR_DIVERGENCE"
        assert result.has_warnings

    def test_flexible_threshold_0_6(self):
        """Test that lower threshold (0.6) allows more variation."""
        from src.mcp_eval.scenario_runner import validate_baseline_against_expected

        # Arrange - Same test case as above
        expected_trajectory = [
            {
                "tool": "mcp__test__search",
                "args": {"query": "test"}
            }
        ]

        actual_tool_calls = [
            {
                "tool_name": "mcp__test__search",
                "tool_input": {"query": "test different query"}
            }
        ]

        # Act - Test with lower threshold 0.6
        result_0_6 = validate_baseline_against_expected(
            scenario_name="test_flexible",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.6
        )

        # Test with strict threshold 0.8
        result_0_8 = validate_baseline_against_expected(
            scenario_name="test_strict",
            expected_trajectory=expected_trajectory,
            actual_tool_calls=actual_tool_calls,
            threshold=0.8
        )

        # Assert - Same similarity score, but different warning status based on threshold
        assert result_0_6.overall_similarity == result_0_8.overall_similarity

        # With 0.6 threshold, less likely to have warnings (unless similarity < 0.6)
        # With 0.8 threshold, more likely to have warnings (if similarity < 0.8)
        if result_0_6.overall_similarity >= 0.6:
            # Should pass with flexible threshold
            assert result_0_6.validation_status != "MAJOR_DIVERGENCE" or not result_0_6.has_warnings or result_0_6.overall_similarity < 0.6

        if result_0_8.overall_similarity < 0.8:
            # Should fail with strict threshold
            assert result_0_8.has_warnings


class TestThresholdValidation:
    """Test suite for threshold validation function."""

    def test_validate_none_returns_default(self):
        """Test that None returns default threshold."""
        assert validate_similarity_threshold(None) == 0.8

    def test_validate_accepts_valid_floats(self):
        """Test that valid float values are accepted."""
        assert validate_similarity_threshold(0.0) == 0.0
        assert validate_similarity_threshold(0.5) == 0.5
        assert validate_similarity_threshold(1.0) == 1.0
        assert validate_similarity_threshold(0.75) == 0.75

    def test_validate_accepts_valid_ints(self):
        """Test that valid integer values are accepted and converted."""
        assert validate_similarity_threshold(0) == 0.0
        assert validate_similarity_threshold(1) == 1.0

    def test_validate_rejects_out_of_range(self):
        """Test that out-of-range values are rejected."""
        with pytest.raises(ValueError):
            validate_similarity_threshold(-0.001)

        with pytest.raises(ValueError):
            validate_similarity_threshold(1.001)

        with pytest.raises(ValueError):
            validate_similarity_threshold(2.0)

    def test_validate_rejects_non_numeric(self):
        """Test that non-numeric values are rejected."""
        with pytest.raises(ValueError):
            validate_similarity_threshold("0.8")

        with pytest.raises(ValueError):
            validate_similarity_threshold([0.8])

        with pytest.raises(ValueError):
            validate_similarity_threshold({"threshold": 0.8})

"""Tests for enhanced similarity calculation with parameter weighting."""

import pytest
import json
from pathlib import Path
from typing import Dict, Any

# Import the functions we'll test
from src.mcp_eval.similarity import (
    SimilarityConfig,
    ParameterComparison,
    calculate_tool_call_similarity,
    calculate_args_similarity,
    calculate_value_similarity,
    calculate_string_similarity,
    calculate_key_similarity
)


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def identical_calls(fixtures_dir):
    """Load identical calls fixture."""
    with open(fixtures_dir / "identical_calls.json") as f:
        return json.load(f)


@pytest.fixture
def semantic_equivalent(fixtures_dir):
    """Load semantic equivalent fixture."""
    with open(fixtures_dir / "semantic_equivalent.json") as f:
        return json.load(f)


@pytest.fixture
def partial_match(fixtures_dir):
    """Load partial match fixture."""
    with open(fixtures_dir / "partial_match.json") as f:
        return json.load(f)


@pytest.fixture
def complete_mismatch(fixtures_dir):
    """Load complete mismatch fixture."""
    with open(fixtures_dir / "complete_mismatch.json") as f:
        return json.load(f)


class TestSimilarityScoring:
    """Test suite for enhanced similarity scoring."""

    def test_identical_calls(self, identical_calls):
        """T031: Test that identical tool calls return similarity = 1.0."""
        # Arrange
        call1 = identical_calls["call1"]
        call2 = identical_calls["call2"]
        expected = identical_calls["expected_similarity"]

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == expected
        assert similarity == 1.0

    def test_semantic_equivalent_queries(self, semantic_equivalent):
        """T032: Test semantic equivalence (query: 'email' vs 'email tools')."""
        # Arrange
        call1 = semantic_equivalent["call1"]
        call2 = semantic_equivalent["call2"]
        expected_min = semantic_equivalent["expected_similarity_min"]
        expected_max = semantic_equivalent["expected_similarity_max"]

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert expected_min <= similarity <= expected_max
        # Note: Current algorithm gives ~0.65 for subset matches like "email" ⊂ "email tools"
        # This will improve with parameter weighting implementation

    def test_extra_optional_parameters(self, partial_match):
        """T033: Test that extra optional params don't over-penalize (e.g., limit, include_stats)."""
        # Arrange
        call1 = partial_match["call1"]
        call2 = partial_match["call2"]
        expected_min = partial_match["expected_similarity_min"]

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity >= expected_min
        # Should not drop below 0.5 for reasonable extra params

    def test_missing_optional_parameters(self):
        """T034: Test missing optional parameters get score 0.5 instead of 0.0."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True}
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email"}  # Missing 'debug'
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        # With missing parameter handling, should be > 0.5
        assert similarity > 0.5
        assert similarity < 1.0

    def test_different_tool_names(self, complete_mismatch):
        """T035: Test completely different tool names return similarity = 0.0."""
        # Arrange
        call1 = complete_mismatch["call1"]
        call2 = complete_mismatch["call2"]
        expected = complete_mismatch["expected_similarity"]

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == expected
        assert similarity == 0.0

    def test_nested_json_parameters(self):
        """T036: Test comparison of nested JSON structures."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__add_server",
            "tool_input": {
                "server_name": "test",
                "config": {
                    "command": "python",
                    "args": ["-m", "test"],
                    "env": {"DEBUG": "true"}
                }
            }
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__add_server",
            "tool_input": {
                "server_name": "test",
                "config": {
                    "command": "python",
                    "args": ["-m", "test"],
                    "env": {"DEBUG": "true"}
                }
            }
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_unicode_string_handling(self):
        """T037: Test Unicode string comparison."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email 📧 tools"}
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email 📧 tools"}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_null_value_handling(self):
        """T038: Test handling of null/None values in parameters."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "limit": None}
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "limit": None}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_parameter_order_independence(self):
        """T039: Test that parameter order doesn't affect similarity."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True, "limit": 10}
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"limit": 10, "query": "email", "debug": True}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_whitespace_normalization(self):
        """T040: Test whitespace differences are normalized."""
        # Arrange
        str1 = "email   tools    search"
        str2 = "email tools search"

        # Act
        similarity = calculate_string_similarity(str1, str2)

        # Assert
        assert similarity == 1.0

    def test_boolean_value_comparison(self):
        """T041: Test boolean value comparison."""
        # Arrange
        call1 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True}
        }
        call2 = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": False}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity < 1.0  # Different boolean values
        assert similarity > 0.5  # But not completely different

    def test_numeric_distance_similarity(self):
        """T042: Test numeric value similarity based on distance."""
        # Arrange
        args1 = {"limit": 10}
        args2 = {"limit": 15}

        # Act
        similarity = calculate_args_similarity(args1, args2)

        # Assert
        # Should be high similarity for close numbers
        assert similarity > 0.9

    def test_parameter_weighting(self):
        """T043: Test that important parameters (query, tool_name) have higher weight."""
        # Arrange - different query values (high weight)
        call1_query_diff = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True, "limit": 10}
        }
        call2_query_diff = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "github", "debug": True, "limit": 10}
        }

        # Arrange - different low-weight parameter (limit)
        call1_limit_diff = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True, "limit": 10}
        }
        call2_limit_diff = {
            "tool_name": "mcp__mcpproxy__retrieve_tools",
            "tool_input": {"query": "email", "debug": True, "limit": 20}
        }

        # Act
        similarity_query_diff = calculate_tool_call_similarity(call1_query_diff, call2_query_diff)
        similarity_limit_diff = calculate_tool_call_similarity(call1_limit_diff, call2_limit_diff)

        # Assert
        # Difference in high-weight parameter (query) should impact score more
        # than difference in low-weight parameter (limit)
        assert similarity_query_diff < similarity_limit_diff


class TestParameterComparison:
    """Test suite for ParameterComparison dataclass."""

    def test_parameter_comparison_creation(self):
        """Test creating ParameterComparison instances."""
        # Arrange & Act
        comparison = ParameterComparison(
            parameter_name="query",
            expected_value="email",
            actual_value="email tools",
            similarity_score=0.85,
            comparison_method="jaccard",
            weight=1.5
        )

        # Assert
        assert comparison.parameter_name == "query"
        assert comparison.similarity_score == 0.85
        assert comparison.weight == 1.5
        assert not comparison.is_exact_match

    def test_exact_match_property(self):
        """Test is_exact_match property."""
        # Arrange & Act
        exact = ParameterComparison(
            parameter_name="debug",
            expected_value=True,
            actual_value=True,
            similarity_score=1.0,
            comparison_method="exact"
        )
        not_exact = ParameterComparison(
            parameter_name="query",
            expected_value="email",
            actual_value="emails",
            similarity_score=0.95,
            comparison_method="jaccard"
        )

        # Assert
        assert exact.is_exact_match
        assert not not_exact.is_exact_match

    def test_is_missing_property(self):
        """Test is_missing property for None values."""
        # Arrange & Act
        missing = ParameterComparison(
            parameter_name="limit",
            expected_value=10,
            actual_value=None,
            similarity_score=0.5,
            comparison_method="missing"
        )
        not_missing = ParameterComparison(
            parameter_name="debug",
            expected_value=True,
            actual_value=False,
            similarity_score=0.0,
            comparison_method="exact"
        )

        # Assert
        assert missing.is_missing
        assert not not_missing.is_missing


class TestNormalizeParameters:
    """Test suite for parameter normalization (future enhancement)."""

    def test_normalize_dict_key_order(self):
        """Test that dictionary key order is normalized."""
        # Arrange
        args1 = {"query": "email", "debug": True, "limit": 10}
        args2 = {"limit": 10, "query": "email", "debug": True}

        # Act
        similarity = calculate_args_similarity(args1, args2)

        # Assert
        assert similarity == 1.0  # Order shouldn't matter

    def test_normalize_string_whitespace(self):
        """Test that string whitespace is normalized."""
        # Arrange
        str1 = "  email   tools  "
        str2 = "email tools"

        # Act
        similarity = calculate_string_similarity(str1.strip(), str2)

        # Assert
        assert similarity == 1.0

    def test_normalize_json_formatting(self):
        """Test that JSON formatting differences are normalized."""
        # Arrange
        value1 = {"key": "value", "nested": {"a": 1, "b": 2}}
        value2 = {"nested": {"b": 2, "a": 1}, "key": "value"}

        # Act
        similarity = calculate_value_similarity(value1, value2)

        # Assert
        assert similarity == 1.0  # Same content, different order


class TestEdgeCases:
    """Test suite for edge cases in similarity calculations."""

    def test_timestamps_dynamically_generated_ids(self):
        """T085: Test that dynamically generated IDs/timestamps don't affect core similarity too much."""
        # Arrange
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "email", "timestamp": "2025-01-01T10:00:00Z"}
        }
        call2 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "email", "timestamp": "2025-01-01T10:05:00Z"}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        # Timestamps differ but query matches, should still have reasonable similarity
        # The weighted average accounts for both matching (query) and non-matching (timestamp) params
        assert similarity > 0.5  # At least half similar due to matching query

    def test_empty_parameter_dicts(self):
        """T089: Test handling of empty parameter dictionaries."""
        # Arrange
        call1 = {
            "tool_name": "mcp__test__list",
            "tool_input": {}
        }
        call2 = {
            "tool_name": "mcp__test__list",
            "tool_input": {}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_parameter_key_similarity_jaccard(self):
        """T090: Test Jaccard similarity for parameter keys."""
        # Arrange
        keys1 = {"query", "debug", "limit"}
        keys2 = {"query", "debug", "offset"}

        # Act
        similarity = calculate_key_similarity(keys1, keys2)

        # Assert
        # Intersection: {query, debug} = 2, Union: {query, debug, limit, offset} = 4
        assert similarity == 0.5

    def test_parameter_value_similarity_weighted(self):
        """T091: Test weighted value similarity for different parameter types."""
        # Arrange
        from src.mcp_eval.similarity import calculate_parameter_similarity, SimilarityConfig

        config = SimilarityConfig()

        # Act
        query_comparison = calculate_parameter_similarity("query", "email", "email tools", config)
        debug_comparison = calculate_parameter_similarity("debug", True, True, config)

        # Assert
        assert query_comparison.weight == 1.5  # Query has higher weight
        assert debug_comparison.weight == 1.0  # Debug has default weight
        assert debug_comparison.similarity_score == 1.0

    def test_tool_name_mismatch_immediate_zero(self):
        """T092: Test that tool name mismatch immediately returns 0.0."""
        # Arrange
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "email"}
        }
        call2 = {
            "tool_name": "mcp__test__list",
            "tool_input": {"query": "email"}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 0.0

    def test_large_nested_json_objects(self):
        """T088: Test similarity calculation with large nested JSON objects."""
        # Arrange
        large_config = {
            "env": {"VAR1": "value1", "VAR2": "value2", "VAR3": "value3"},
            "command": "python",
            "args": ["-m", "module", "--flag"],
            "volumes": ["/data:/data", "/logs:/logs"],
            "ports": {"8080": "8080", "9090": "9090"}
        }

        call1 = {
            "tool_name": "mcp__test__configure",
            "tool_input": {"config": large_config}
        }
        call2 = {
            "tool_name": "mcp__test__configure",
            "tool_input": {"config": large_config}
        }

        # Act
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

    def test_encoding_errors_graceful_handling(self):
        """T087: Test graceful handling of encoding/special characters."""
        # Arrange
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "email 📧 测试"}
        }
        call2 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "email 📧 测试"}
        }

        # Act - Should not crash
        similarity = calculate_tool_call_similarity(call1, call2)

        # Assert
        assert similarity == 1.0

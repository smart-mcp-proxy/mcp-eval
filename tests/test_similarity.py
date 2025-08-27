"""Unit tests for similarity calculation module."""

import unittest
from src.mcp_eval.similarity import (
    calculate_key_similarity,
    calculate_string_similarity, 
    calculate_number_similarity,
    calculate_json_similarity,
    calculate_value_similarity,
    calculate_args_similarity,
    calculate_tool_call_similarity,
    calculate_trajectory_similarity
)


class TestKeySimilarity(unittest.TestCase):
    
    def test_identical_keys(self):
        keys1 = {"a", "b", "c"}
        keys2 = {"a", "b", "c"}
        self.assertEqual(calculate_key_similarity(keys1, keys2), 1.0)
    
    def test_no_common_keys(self):
        keys1 = {"a", "b", "c"}
        keys2 = {"x", "y", "z"}
        self.assertEqual(calculate_key_similarity(keys1, keys2), 0.0)
    
    def test_partial_overlap(self):
        keys1 = {"a", "b", "c"}
        keys2 = {"b", "c", "d"}
        # Intersection: {b, c} = 2, Union: {a, b, c, d} = 4
        self.assertEqual(calculate_key_similarity(keys1, keys2), 0.5)
    
    def test_empty_sets(self):
        keys1 = set()
        keys2 = set()
        self.assertEqual(calculate_key_similarity(keys1, keys2), 1.0)
    
    def test_one_empty_set(self):
        keys1 = {"a", "b"}
        keys2 = set()
        self.assertEqual(calculate_key_similarity(keys1, keys2), 0.0)


class TestStringSimilarity(unittest.TestCase):
    
    def test_identical_strings(self):
        self.assertEqual(calculate_string_similarity("hello world", "hello world"), 1.0)
    
    def test_completely_different(self):
        self.assertEqual(calculate_string_similarity("hello", "goodbye"), 0.0)
    
    def test_partial_overlap(self):
        # "hello world" vs "world peace"
        # words1: {hello, world}, words2: {world, peace}
        # intersection: {world} = 1, union: {hello, world, peace} = 3
        result = calculate_string_similarity("hello world", "world peace")
        self.assertAlmostEqual(result, 1/3, places=3)
    
    def test_case_insensitive(self):
        result = calculate_string_similarity("Hello World", "HELLO WORLD")
        self.assertEqual(result, 1.0)
    
    def test_empty_strings(self):
        self.assertEqual(calculate_string_similarity("", ""), 1.0)
    
    def test_one_empty_string(self):
        self.assertEqual(calculate_string_similarity("hello", ""), 0.0)


class TestNumberSimilarity(unittest.TestCase):
    
    def test_identical_numbers(self):
        self.assertEqual(calculate_number_similarity(5.0, 5.0), 1.0)
    
    def test_small_difference(self):
        # Default max_diff is 1000, so diff of 10 should give similarity of 0.99
        result = calculate_number_similarity(100.0, 110.0)
        self.assertAlmostEqual(result, 0.99, places=3)
    
    def test_large_difference(self):
        # Difference of 1000 with max_diff 1000 should give 0
        result = calculate_number_similarity(0.0, 1000.0)
        self.assertEqual(result, 0.0)
    
    def test_custom_max_diff(self):
        # With max_diff of 100, difference of 50 should give 0.5
        result = calculate_number_similarity(0.0, 50.0, max_diff=100.0)
        self.assertEqual(result, 0.5)


class TestJsonSimilarity(unittest.TestCase):
    
    def test_identical_objects(self):
        obj1 = {"a": 1, "b": [2, 3]}
        obj2 = {"a": 1, "b": [2, 3]}
        self.assertEqual(calculate_json_similarity(obj1, obj2), 1.0)
    
    def test_different_objects(self):
        obj1 = {"a": 1}
        obj2 = {"b": 2}
        result = calculate_json_similarity(obj1, obj2)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
    
    def test_similar_objects(self):
        obj1 = {"a": 1, "b": 2}
        obj2 = {"a": 1, "c": 3}
        result = calculate_json_similarity(obj1, obj2)
        # Should have some similarity due to shared structure
        self.assertGreater(result, 0.0)
        self.assertLess(result, 1.0)


class TestValueSimilarity(unittest.TestCase):
    
    def test_identical_values(self):
        self.assertEqual(calculate_value_similarity("hello", "hello"), 1.0)
        self.assertEqual(calculate_value_similarity(42, 42), 1.0)
    
    def test_none_values(self):
        self.assertEqual(calculate_value_similarity(None, None), 1.0)
        self.assertEqual(calculate_value_similarity(None, "hello"), 0.0)
    
    def test_string_values(self):
        result = calculate_value_similarity("hello world", "hello there")
        self.assertGreater(result, 0.0)  # Should have some similarity
        self.assertLess(result, 1.0)
    
    def test_number_values(self):
        result = calculate_value_similarity(10, 15)
        self.assertGreater(result, 0.9)  # Should be high similarity
    
    def test_mixed_types(self):
        # Should convert to strings for comparison
        result = calculate_value_similarity(42, "42")
        self.assertGreater(result, 0.0)


class TestArgsSimilarity(unittest.TestCase):
    
    def test_identical_args(self):
        args1 = {"query": "hello", "limit": 10}
        args2 = {"query": "hello", "limit": 10}
        self.assertEqual(calculate_args_similarity(args1, args2), 1.0)
    
    def test_empty_args(self):
        self.assertEqual(calculate_args_similarity({}, {}), 1.0)
    
    def test_different_keys(self):
        args1 = {"query": "hello"}
        args2 = {"search": "hello"}
        result = calculate_args_similarity(args1, args2)
        # Should be low similarity due to no common keys
        self.assertLess(result, 0.5)
    
    def test_same_keys_different_values(self):
        args1 = {"query": "hello world"}
        args2 = {"query": "hello there"}
        result = calculate_args_similarity(args1, args2)
        # Should have decent similarity
        self.assertGreater(result, 0.3)
        self.assertLess(result, 1.0)
    
    def test_partial_key_overlap(self):
        args1 = {"query": "hello", "limit": 10}
        args2 = {"query": "hello", "offset": 0}
        result = calculate_args_similarity(args1, args2)
        # Should have good similarity due to matching query
        self.assertGreater(result, 0.5)


class TestToolCallSimilarity(unittest.TestCase):
    
    def test_identical_calls(self):
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "hello", "limit": 10}
        }
        call2 = {
            "tool_name": "mcp__test__search", 
            "tool_input": {"query": "hello", "limit": 10}
        }
        self.assertEqual(calculate_tool_call_similarity(call1, call2), 1.0)
    
    def test_different_tool_names(self):
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "hello"}
        }
        call2 = {
            "tool_name": "mcp__test__list",
            "tool_input": {"query": "hello"}
        }
        self.assertEqual(calculate_tool_call_similarity(call1, call2), 0.0)
    
    def test_same_tool_different_args(self):
        call1 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "hello world"}
        }
        call2 = {
            "tool_name": "mcp__test__search",
            "tool_input": {"query": "hello there"}
        }
        result = calculate_tool_call_similarity(call1, call2)
        self.assertGreater(result, 0.0)
        self.assertLess(result, 1.0)


class TestTrajectorySimilarity(unittest.TestCase):
    
    def test_identical_trajectories(self):
        calls1 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}},
            {"tool_name": "mcp__test__list", "tool_input": {"limit": 10}}
        ]
        calls2 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}},
            {"tool_name": "mcp__test__list", "tool_input": {"limit": 10}}
        ]
        self.assertEqual(calculate_trajectory_similarity(calls1, calls2), 1.0)
    
    def test_filters_non_mcp_calls(self):
        calls1 = [
            {"tool_name": "TodoWrite", "tool_input": {"todos": []}},
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}}
        ]
        calls2 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}}
        ]
        # Should ignore TodoWrite and only compare mcp__ calls
        self.assertEqual(calculate_trajectory_similarity(calls1, calls2), 1.0)
    
    def test_empty_trajectories(self):
        self.assertEqual(calculate_trajectory_similarity([], []), 1.0)
    
    def test_no_mcp_calls(self):
        calls1 = [{"tool_name": "TodoWrite", "tool_input": {}}]
        calls2 = [{"tool_name": "Bash", "tool_input": {}}]
        # Both have no MCP calls, so similarity should be 1.0
        self.assertEqual(calculate_trajectory_similarity(calls1, calls2), 1.0)
    
    def test_one_empty_mcp_trajectory(self):
        calls1 = [{"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}}]
        calls2 = [{"tool_name": "TodoWrite", "tool_input": {}}]  # No MCP calls
        self.assertEqual(calculate_trajectory_similarity(calls1, calls2), 0.0)
    
    def test_different_length_trajectories(self):
        calls1 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}},
            {"tool_name": "mcp__test__list", "tool_input": {"limit": 10}}
        ]
        calls2 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}}
        ]
        # Should get 0.5 (first call matches 1.0, second call missing gets 0.0)
        result = calculate_trajectory_similarity(calls1, calls2)
        self.assertEqual(result, 0.5)
    
    def test_reordered_calls(self):
        calls1 = [
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}},
            {"tool_name": "mcp__test__list", "tool_input": {"limit": 10}}
        ]
        calls2 = [
            {"tool_name": "mcp__test__list", "tool_input": {"limit": 10}},
            {"tool_name": "mcp__test__search", "tool_input": {"query": "hello"}}
        ]
        # Order matters, so this should not be 1.0
        result = calculate_trajectory_similarity(calls1, calls2)
        self.assertEqual(result, 0.0)  # Different tools at each position


if __name__ == '__main__':
    unittest.main()
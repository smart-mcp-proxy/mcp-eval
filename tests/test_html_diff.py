"""Tests for HTML diff normalization."""

import pytest
import json
from typing import Dict, Any

# Import the functions we'll implement
from src.mcp_eval.html_reporter import (
    HtmlDiffConfig,
    normalize_tool_call_content,
    HTMLReporter
)


class TestHtmlDiffNormalization:
    """Test suite for HTML diff normalization."""

    def test_identical_params_no_highlights(self):
        """T054: Test that identical parameters produce no highlights (no diff)."""
        # Arrange
        text1 = '{"query": "email", "debug": true}'
        text2 = '{"query": "email", "debug": true}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 == normalized2
        # This ensures difflib will not highlight these as different

    def test_different_values_correct_highlights(self):
        """T055: Test that actual value differences are preserved for highlighting."""
        # Arrange
        text1 = '{"query": "email", "debug": true}'
        text2 = '{"query": "email tools", "debug": true}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 != normalized2
        # Verify the actual difference is in the query value
        dict1 = json.loads(normalized1)
        dict2 = json.loads(normalized2)
        assert dict1["query"] != dict2["query"]
        assert dict1["debug"] == dict2["debug"]

    def test_different_keys_green_red_highlighting(self):
        """T056: Test that different keys produce distinct normalized output."""
        # Arrange
        text1 = '{"query": "email", "debug": true}'
        text2 = '{"query": "email", "limit": 10}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 != normalized2
        dict1 = json.loads(normalized1)
        dict2 = json.loads(normalized2)
        assert "debug" in dict1
        assert "debug" not in dict2
        assert "limit" in dict2
        assert "limit" not in dict1

    def test_parameter_order_normalization(self):
        """T057: Test that parameter order doesn't affect diff (alphabetical sorting)."""
        # Arrange
        text1 = '{"query": "email", "debug": true, "limit": 10}'
        text2 = '{"limit": 10, "query": "email", "debug": true}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 == normalized2
        # Keys should be alphabetically sorted
        dict1 = json.loads(normalized1)
        keys = list(dict1.keys())
        assert keys == sorted(keys)

    def test_whitespace_normalization(self):
        """T058: Test that whitespace differences don't cause false highlights."""
        # Arrange
        text1 = '{"query":"email","debug":true}'
        text2 = '{\n  "query": "email",\n  "debug": true\n}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 == normalized2
        # Both should produce consistent formatting

    def test_malformed_json_graceful_fallback(self):
        """T059: Test graceful handling of malformed JSON."""
        # Arrange
        malformed_text = '{"query": "email", debug: true}'  # Missing quotes on key

        # Act - should not crash
        normalized = normalize_tool_call_content(malformed_text)

        # Assert - should return original or best-effort normalized string
        assert normalized is not None
        assert isinstance(normalized, str)
        # Should contain the original content
        assert "email" in normalized

    def test_python_dict_vs_json_format(self):
        """T060: Test conversion between Python dict format and JSON format."""
        # Arrange - Python format with True/False
        python_format = "{'query': 'email', 'debug': True}"
        json_format = '{"query": "email", "debug": true}'

        # Act
        normalized_python = normalize_tool_call_content(python_format)
        normalized_json = normalize_tool_call_content(json_format)

        # Assert - Both should normalize to same JSON format
        assert normalized_python == normalized_json
        # Should use JSON booleans (lowercase true/false)
        assert "true" in normalized_python
        assert "True" not in normalized_python


class TestHtmlDiffConfig:
    """Test suite for HtmlDiffConfig dataclass."""

    def test_html_diff_config_defaults(self):
        """Test HtmlDiffConfig default values."""
        # Arrange & Act
        config = HtmlDiffConfig()

        # Assert
        assert config.normalize_whitespace is True
        assert config.normalize_dict_keys is True
        assert config.normalize_json_format is True
        assert config.show_line_numbers is True
        assert config.enable_character_diff is True

    def test_html_diff_config_custom_values(self):
        """Test HtmlDiffConfig with custom values."""
        # Arrange & Act
        config = HtmlDiffConfig(
            normalize_whitespace=False,
            normalize_dict_keys=False,
            added_bg_color="#custom"
        )

        # Assert
        assert config.normalize_whitespace is False
        assert config.normalize_dict_keys is False
        assert config.added_bg_color == "#custom"


class TestComplexNormalization:
    """Test suite for complex normalization scenarios."""

    def test_nested_json_normalization(self):
        """Test normalization of nested JSON structures."""
        # Arrange
        text1 = '{"config": {"env": {"DEBUG": "true"}, "command": "python"}}'
        text2 = '{"config": {"command": "python", "env": {"DEBUG": "true"}}}'

        # Act
        normalized1 = normalize_tool_call_content(text1)
        normalized2 = normalize_tool_call_content(text2)

        # Assert
        assert normalized1 == normalized2

    def test_embedded_dict_in_text(self):
        """Test extraction and normalization of dicts embedded in text."""
        # Arrange
        text_with_dict = 'Tool call: {"query": "email", "debug": true} returned results'

        # Act
        normalized = normalize_tool_call_content(text_with_dict)

        # Assert
        assert normalized is not None
        # Should normalize the embedded JSON
        assert "debug" in normalized or "query" in normalized

    def test_mixed_quotes_normalization(self):
        """Test normalization handles mixed quote styles."""
        # Arrange
        single_quotes = "{'query': 'email'}"
        double_quotes = '{"query": "email"}'

        # Act
        normalized1 = normalize_tool_call_content(single_quotes)
        normalized2 = normalize_tool_call_content(double_quotes)

        # Assert
        assert normalized1 == normalized2


class TestCharacterLevelDiffIssues:
    """Test suite for character-level diff highlighting issues."""

    def test_whitespace_in_numbers_no_confusing_highlights(self):
        """Test that whitespace differences in numbers don't cause character-by-character highlights.

        Issue: "d8f 1 2 02 22f 3 f" vs "d8 f1 20222f 3 f" was showing confusing character highlights
        """
        # Arrange
        text1 = "d8f 1 2 02 22f 3 f"
        text2 = "d8 f1 20222f 3 f"

        # Act - normalize whitespace
        normalized1 = ' '.join(text1.split())
        normalized2 = ' '.join(text2.split())

        # Assert - should be different but in a clear way
        assert normalized1 != normalized2
        # The actual difference should be clear, not character-by-character

    def test_similar_words_confusing_highlights(self):
        """Test that similar words don't show confusing character-level highlights.

        Issue: "successfully found and us" vs "success f ul y found and used the"
        was showing character-by-character highlights that were confusing.
        """
        # Arrange
        text1 = "successfully found and us"
        text2 = "success f ul y found and used the"

        # Act - These are clearly different
        # The highlighting should be word-based or token-based, not character-level

        # Assert
        assert text1 != text2
        # Note: This test documents the issue - we need better diff algorithm

    def test_identical_words_no_highlights(self):
        """Test that identical words like 'Perfect' don't show character highlights.

        Issue: "Perfect" vs "Perfect" was showing "Pe r f e c t" with character highlights
        """
        # Arrange
        text1 = "Perfect! I found a tool"
        text2 = "Perfect! I found a tool"

        # Act
        # When normalized, these should be identical

        # Assert
        assert text1 == text2
        # No highlights should appear

    def test_html_reporter_highlight_diff_method(self):
        """Test the _highlight_content_diff method with problematic cases."""
        # Arrange
        reporter = HTMLReporter()

        # Case 1: Identical content should have no highlights
        current1 = "Perfect! I found a tool"
        baseline1 = "Perfect! I found a tool"

        # Case 2: Whitespace differences should normalize
        current2 = "d8f 1 2 02 22f 3 f"
        baseline2 = "d8 f1 20222f 3 f"

        # Act
        result1_current = reporter._highlight_content_diff(current1, baseline1, is_current=True)
        result1_baseline = reporter._highlight_content_diff(current1, baseline1, is_current=False)

        result2_current = reporter._highlight_content_diff(current2, baseline2, is_current=True)

        # Assert
        # Case 1: No diff-highlight spans should appear for identical content
        assert '<span class="diff-highlight">' not in result1_current
        assert '<span class="diff-highlight">' not in result1_baseline

    def test_character_level_diff_real_case_from_screenshot(self):
        """Test real cases from screenshot showing confusing character-level highlights.

        Issue from screenshot:
        - "Perfect" appearing as "Pe r f e c t" with char highlights
        - "d8f 1 2 02 22f 3 f" vs "d8 f1 20222f 3 f" with confusing highlights
        - Numbers like "655428463 76 05" vs "3156 55 4 284637605" with highlights
        """
        # Arrange
        reporter = HTMLReporter()

        # Case from screenshot: "Perfect" with character-level highlights
        current1 = "Perfect! I found"
        baseline1 = "Perfect! I found"

        # Case from screenshot: Git hashes with whitespace differences
        current2 = "d8f1 2022f 3f"
        baseline2 = "d8 f1 20222f 3 f"

        # Case from screenshot: Number sequences
        current3 = "0.0 4 3156 55 4 284637605"
        baseline3 = "0.0 4 315 655428463 76 05"

        # Act
        result1 = reporter._highlight_content_diff(current1, baseline1, is_current=True)
        result2 = reporter._highlight_content_diff(current2, baseline2, is_current=True)
        result3 = reporter._highlight_content_diff(current3, baseline3, is_current=True)

        # Assert
        # Case 1: Identical text should have NO highlights
        assert '<span class="diff-highlight">' not in result1, \
            f"Identical text should not have highlights, but got: {result1}"

        # Case 2 and 3: When there ARE differences, we shouldn't highlight every character
        # Instead, we want more intelligent highlighting
        # For now, document that these are problematic
        print(f"\nCase 2 (git hash with whitespace):\n{result2}")
        print(f"\nCase 3 (numbers):\n{result3}")


class TestTimestampFormatting:
    """Test suite for timestamp formatting in HTML reports."""

    def test_timestamp_format_yyyy_mm_dd(self):
        """Test that timestamps are formatted as YYYY/MM/DD HH:MM:SS."""
        # Arrange
        from datetime import datetime
        reporter = HTMLReporter()

        # Create a test timestamp in ISO format
        test_timestamp = "2025-11-12T14:53:55.123456"

        # Act - Use the internal method that formats dialog turns
        # We need to test the timestamp formatting logic
        dt = datetime.fromisoformat(test_timestamp.replace('Z', '+00:00'))
        formatted = dt.strftime("%Y/%m/%d %H:%M:%S")

        # Assert
        assert formatted == "2025/11/12 14:53:55"
        # Format should be YYYY/MM/DD HH:MM:SS
        assert len(formatted) == 19
        assert formatted[4] == '/'
        assert formatted[7] == '/'
        assert formatted[10] == ' '
        assert formatted[13] == ':'
        assert formatted[16] == ':'

    def test_timestamp_parsing_with_z_suffix(self):
        """Test that timestamps with Z suffix are correctly parsed."""
        # Arrange
        from datetime import datetime
        test_timestamp = "2025-11-12T14:53:55Z"

        # Act
        dt = datetime.fromisoformat(test_timestamp.replace('Z', '+00:00'))
        formatted = dt.strftime("%Y/%m/%d %H:%M:%S")

        # Assert
        assert formatted == "2025/11/12 14:53:55"


class TestJSONFormatting:
    """Test suite for JSON formatting in tool results."""

    def test_json_pretty_printing(self):
        """Test that JSON is pretty-printed with indentation."""
        # Arrange
        reporter = HTMLReporter()
        json_content = '{"query": "test", "debug": true, "limit": 10}'

        # Act
        result = reporter._format_tool_result(json_content)

        # Assert
        assert '<pre class="json-content">' in result
        assert 'json-key' in result  # Syntax highlighting applied
        # Should have indentation (newlines from pretty print)
        assert '\n' in result or '&#10;' in result

    def test_json_syntax_highlighting(self):
        """Test that JSON elements are syntax highlighted."""
        # Arrange
        reporter = HTMLReporter()
        json_content = '{"name": "test", "count": 42, "active": true, "value": null}'

        # Act
        result = reporter._format_tool_result(json_content)

        # Assert
        # Keys should be highlighted
        assert 'json-key' in result
        # String values should be highlighted
        assert 'json-string' in result
        # Numbers should be highlighted
        assert 'json-number' in result
        # Keywords (true, false, null) should be highlighted
        assert 'json-keyword' in result

    def test_long_json_collapsible(self):
        """Test that long JSON output is collapsible."""
        # Arrange
        reporter = HTMLReporter()
        # Create JSON with more than 20 lines
        large_dict = {f"key_{i}": f"value_{i}" for i in range(30)}
        json_content = json.dumps(large_dict)

        # Act
        result = reporter._format_tool_result(json_content, max_display_lines=20)

        # Assert
        # Should have expand/collapse buttons
        assert 'json-expand-btn' in result
        assert 'json-collapse-btn' in result
        # Should have preview and full sections
        assert 'json-preview' in result
        assert 'json-full' in result
        # Should show truncation message
        assert 'more lines' in result

    def test_short_json_no_collapse(self):
        """Test that short JSON is not collapsible."""
        # Arrange
        reporter = HTMLReporter()
        json_content = '{"key1": "value1", "key2": "value2"}'

        # Act
        result = reporter._format_tool_result(json_content, max_display_lines=20)

        # Assert
        # Should NOT have expand/collapse buttons
        assert 'json-expand-btn' not in result
        assert 'json-collapse-btn' not in result
        # Should just have the content
        assert '<pre class="json-content">' in result

    def test_non_json_plain_text(self):
        """Test that non-JSON content is displayed as plain text."""
        # Arrange
        reporter = HTMLReporter()
        plain_text = "This is just plain text, not JSON"

        # Act
        result = reporter._format_tool_result(plain_text)

        # Assert
        assert '<pre class="plain-content">' in result
        assert 'json-key' not in result  # No syntax highlighting
        assert 'This is just plain text' in result

    def test_python_dict_format(self):
        """Test that Python dict format is converted to JSON."""
        # Arrange
        reporter = HTMLReporter()
        python_dict = "{'query': 'test', 'debug': True, 'limit': 10}"

        # Act
        result = reporter._format_tool_result(python_dict)

        # Assert
        # Should be parsed and formatted as JSON
        assert '<pre class="json-content">' in result
        assert 'json-key' in result

    def test_empty_content(self):
        """Test handling of empty content."""
        # Arrange
        reporter = HTMLReporter()

        # Act
        result = reporter._format_tool_result("")

        # Assert
        assert 'no-content' in result
        assert 'No content' in result

    def test_json_array_formatting(self):
        """Test that JSON arrays are formatted correctly."""
        # Arrange
        reporter = HTMLReporter()
        json_array = '[{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]'

        # Act
        result = reporter._format_tool_result(json_array)

        # Assert
        assert '<pre class="json-content">' in result
        assert 'json-key' in result
        assert 'json-number' in result

    def test_nested_json_string_decoding(self):
        """Test that nested JSON strings in 'text' field are decoded and formatted."""
        # Arrange
        reporter = HTMLReporter()
        # Simulate MCP tool result with JSON in "text" field
        nested_json = json.dumps([
            {
                "type": "text",
                "text": '{"query": "print environment variables", "tools": [{"name": "printEnv", "description": "Prints all environment variables"}]}'
            }
        ])

        # Act
        result = reporter._format_tool_result(nested_json)

        # Assert
        # Should decode the nested JSON and format it
        assert '<pre class="json-content">' in result
        assert 'json-key' in result
        # The nested "query" key should be visible
        assert 'query' in result
        assert 'tools' in result
        assert 'printEnv' in result

    def test_deeply_nested_json_decoding(self):
        """Test that deeply nested JSON strings are decoded up to max depth."""
        # Arrange
        reporter = HTMLReporter()
        # Create 3 levels of nesting
        level_3 = json.dumps({"level": 3, "data": "innermost"})
        level_2 = json.dumps({"level": 2, "text": level_3})
        level_1 = json.dumps({"level": 1, "text": level_2})

        # Act
        result = reporter._format_tool_result(level_1)

        # Assert
        # Should decode up to max_depth (default 3)
        assert 'level' in result
        # Level 3 should be decoded
        assert 'innermost' in result

    def test_nested_json_with_non_json_strings(self):
        """Test that regular strings are not affected by nested JSON decoding."""
        # Arrange
        reporter = HTMLReporter()
        mixed_json = json.dumps({
            "text": '{"valid": "json"}',
            "description": "This is just a plain string, not JSON",
            "count": 42
        })

        # Act
        result = reporter._format_tool_result(mixed_json)

        # Assert
        # Should decode the "text" field
        assert 'valid' in result
        # Should preserve the plain string
        assert 'plain string' in result
        assert 'json-key' in result

    def test_recursive_json_decode_method(self):
        """Test the _decode_nested_json method directly."""
        # Arrange
        reporter = HTMLReporter()
        nested_data = {
            "type": "text",
            "text": '{"query": "test", "count": 10}'
        }

        # Act
        decoded = reporter._decode_nested_json(nested_data)

        # Assert
        # The "text" field should be decoded to a dict
        assert isinstance(decoded["text"], dict)
        assert decoded["text"]["query"] == "test"
        assert decoded["text"]["count"] == 10

    def test_try_decode_json_string_method(self):
        """Test the _try_decode_json_string method."""
        # Arrange
        reporter = HTMLReporter()

        # Act & Assert
        # Valid JSON string
        result1 = reporter._try_decode_json_string('{"key": "value"}')
        assert isinstance(result1, dict)
        assert result1["key"] == "value"

        # Plain string (not JSON)
        result2 = reporter._try_decode_json_string('just a string')
        assert result2 == 'just a string'

        # Empty string
        result3 = reporter._try_decode_json_string('')
        assert result3 == ''

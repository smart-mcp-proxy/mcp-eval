"""Unit tests for reporter module including trajectory text generation."""

import pytest
from src.mcp_eval.reporter import ReportGenerator


class TestGenerateTrajectoryText:
    """Tests for generate_trajectory_text method (FR-023)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = ReportGenerator()

    def test_empty_session(self):
        """Test generating trajectory for empty session."""
        session_data = {
            "scenario": {"name": "test", "user_intent": "test intent"},
            "turns": [],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "# Scenario: test" in result
        assert "# User Intent: test intent" in result
        assert "# Status: SUCCESS" in result

    def test_user_message_turn(self):
        """Test USER_MESSAGE turn formatting."""
        session_data = {
            "scenario": {"name": "test", "user_intent": "do something"},
            "turns": [
                {"turn_type": "USER_MESSAGE", "content": "Hello world", "metadata": {}}
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "USER: Hello world" in result

    def test_agent_message_turn(self):
        """Test AGENT_MESSAGE turn formatting."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {"turn_type": "AGENT_MESSAGE", "content": "I can help", "metadata": {}}
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "AGENT: I can help" in result

    def test_tool_call_turn(self):
        """Test TOOL_CALL turn formatting with [AGENT] prefix."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "TOOL_CALL",
                    "content": "Calling tool",
                    "metadata": {
                        "tool_name": "mcp__mcpproxy__list_tools",
                        "tool_input": {"query": "test"},
                    },
                }
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[AGENT] TOOL_CALL: mcp__mcpproxy__list_tools" in result

    def test_tool_result_turn(self):
        """Test TOOL_RESULT turn formatting with [AGENT] prefix."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "TOOL_RESULT",
                    "content": "Success response",
                    "metadata": {"is_error": False},
                }
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[AGENT] TOOL_RESULT: Success response" in result

    def test_tool_error_turn(self):
        """Test TOOL_RESULT with error."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "TOOL_RESULT",
                    "content": "Error message",
                    "metadata": {"is_error": True},
                }
            ],
            "status": "FAILURE",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[AGENT] TOOL_ERROR: Error message" in result

    def test_control_tool_call_turn(self):
        """Test CONTROL_TOOL_CALL turn formatting with [CTRL] prefix."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "CONTROL_TOOL_CALL",
                    "content": "Control call",
                    "metadata": {
                        "tool_name": "api_v1_servers_id_unquarantine",
                        "tool_input": {"id": "server1"},
                        "trigger": "after_quarantine",
                    },
                }
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[CTRL] TOOL_CALL: api_v1_servers_id_unquarantine" in result
        assert "Trigger: after_quarantine" in result

    def test_control_tool_result_turn(self):
        """Test CONTROL_TOOL_RESULT turn formatting with [CTRL] prefix."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "CONTROL_TOOL_RESULT",
                    "content": "Unquarantine successful",
                    "metadata": {"is_error": False, "success": True},
                }
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[CTRL] TOOL_RESULT: Unquarantine successful" in result

    def test_control_tool_error_turn(self):
        """Test CONTROL_TOOL_RESULT with error."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "CONTROL_TOOL_RESULT",
                    "content": "Server not found",
                    "metadata": {"is_error": True},
                }
            ],
            "status": "FAILURE",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "[CTRL] TOOL_ERROR: Server not found" in result

    def test_control_actions_summary(self):
        """Test control actions count in footer."""
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [],
            "status": "SUCCESS",
            "control_tool_calls": [
                {"tool_name": "api_v1_servers_id_unquarantine"},
                {"tool_name": "api_v1_config"},
            ],
        }
        result = self.reporter.generate_trajectory_text(session_data)
        assert "# Control Actions: 2 executed" in result

    def test_content_truncation(self):
        """Test that long content is truncated."""
        long_content = "x" * 300  # More than 200 chars
        session_data = {
            "scenario": {"name": "test", "user_intent": ""},
            "turns": [
                {
                    "turn_type": "TOOL_RESULT",
                    "content": long_content,
                    "metadata": {"is_error": False},
                }
            ],
            "status": "SUCCESS",
        }
        result = self.reporter.generate_trajectory_text(session_data)
        # Should be truncated with ...
        assert "xxx..." in result
        # Full content should not be present (300 x's)
        assert long_content not in result

    def test_full_conversation_flow(self):
        """Test a complete conversation with all turn types."""
        session_data = {
            "scenario": {"name": "unquarantine_flow", "user_intent": "Add server and unquarantine"},
            "turns": [
                {"turn_type": "USER_MESSAGE", "content": "Add server", "metadata": {}},
                {"turn_type": "AGENT_MESSAGE", "content": "I'll add it", "metadata": {}},
                {"turn_type": "TOOL_CALL", "content": "", "metadata": {"tool_name": "mcp__mcpproxy__add_server", "tool_input": {"name": "test"}}},
                {"turn_type": "TOOL_RESULT", "content": "Server added, quarantined", "metadata": {"is_error": False}},
                {"turn_type": "CONTROL_TOOL_CALL", "content": "", "metadata": {"tool_name": "api_v1_servers_id_unquarantine", "tool_input": {"id": "test"}, "trigger": "after_quarantine"}},
                {"turn_type": "CONTROL_TOOL_RESULT", "content": "Unquarantined", "metadata": {"is_error": False}},
                {"turn_type": "AGENT_MESSAGE", "content": "Done!", "metadata": {}},
            ],
            "status": "SUCCESS",
            "control_tool_calls": [{"tool_name": "api_v1_servers_id_unquarantine"}],
        }
        result = self.reporter.generate_trajectory_text(session_data)

        # Verify ordering and all elements present
        lines = result.split("\n")
        assert any("USER: Add server" in line for line in lines)
        assert any("AGENT: I'll add it" in line for line in lines)
        assert any("[AGENT] TOOL_CALL: mcp__mcpproxy__add_server" in line for line in lines)
        assert any("[CTRL] TOOL_CALL: api_v1_servers_id_unquarantine" in line for line in lines)
        assert any("# Control Actions: 1 executed" in line for line in lines)

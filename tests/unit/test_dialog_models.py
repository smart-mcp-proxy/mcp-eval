"""Unit tests for dialog models including UserControlAction."""

import pytest
from datetime import datetime

from src.mcp_eval.dialog_models import (
    UserControlAction,
    ControlToolCall,
    ControlToolResult,
    parse_user_control_actions,
    is_valid_control_tool,
    VALID_TRIGGERS,
    VALID_CONTROL_TOOL_PREFIXES,
)


class TestUserControlAction:
    """Tests for UserControlAction dataclass."""

    def test_create_valid_action(self):
        """Test creating a valid control action."""
        action = UserControlAction(
            trigger="after_tool_1",
            action="unquarantine_server",
            tool="api_v1_servers_id_unquarantine",
            args={"id": "test-server"},
        )
        assert action.trigger == "after_tool_1"
        assert action.action == "unquarantine_server"
        assert action.tool == "api_v1_servers_id_unquarantine"
        assert action.args == {"id": "test-server"}

    def test_valid_triggers(self):
        """Test all valid trigger types."""
        valid_triggers = ["after_tool_1", "after_tool_5", "after_quarantine", "on_error", "before_completion", "manual"]
        for trigger in valid_triggers:
            action = UserControlAction(
                trigger=trigger,
                action="test",
                tool="api_v1_config",
            )
            assert action.trigger == trigger

    def test_invalid_trigger_raises_error(self):
        """Test that invalid trigger raises ValueError."""
        with pytest.raises(ValueError, match="Invalid trigger"):
            UserControlAction(
                trigger="invalid_trigger",
                action="test",
                tool="api_v1_config",
            )

    def test_to_dict(self):
        """Test serialization to dictionary."""
        action = UserControlAction(
            trigger="after_tool_2",
            action="read_config",
            tool="api_v1_config",
            args={"format": "json"},
            expected_result={"success": True},
        )
        result = action.to_dict()
        assert result["trigger"] == "after_tool_2"
        assert result["action"] == "read_config"
        assert result["tool"] == "api_v1_config"
        assert result["args"] == {"format": "json"}
        assert result["expected_result"] == {"success": True}

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "trigger": "on_error",
            "action": "restart_server",
            "tool": "api_v1_servers_id_restart",
            "args": {"id": "my-server"},
        }
        action = UserControlAction.from_dict(data)
        assert action.trigger == "on_error"
        assert action.tool == "api_v1_servers_id_restart"


class TestControlToolCall:
    """Tests for ControlToolCall dataclass."""

    def test_create_tool_call(self):
        """Test creating a control tool call."""
        call = ControlToolCall(
            timestamp="2025-01-15T10:00:00",
            tool_name="api_v1_servers_id_unquarantine",
            tool_input={"id": "test"},
            tool_id="abc123",
        )
        assert call.type == "CONTROL_TOOL_CALL"
        assert call.tool_name == "api_v1_servers_id_unquarantine"

    def test_to_dict(self):
        """Test serialization."""
        call = ControlToolCall(
            timestamp="2025-01-15T10:00:00",
            tool_name="api_v1_config",
            tool_input={},
            tool_id="xyz",
        )
        result = call.to_dict()
        assert result["type"] == "CONTROL_TOOL_CALL"
        assert result["tool_name"] == "api_v1_config"


class TestControlToolResult:
    """Tests for ControlToolResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = ControlToolResult(
            timestamp="2025-01-15T10:00:01",
            tool_use_id="abc123",
            success=True,
            response={"status": "ok"},
        )
        assert result.type == "CONTROL_TOOL_RESULT"
        assert result.success is True
        assert result.error is None

    def test_create_error_result(self):
        """Test creating an error result."""
        result = ControlToolResult(
            timestamp="2025-01-15T10:00:01",
            tool_use_id="abc123",
            success=False,
            response=None,
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"


class TestParseUserControlActions:
    """Tests for parse_user_control_actions function."""

    def test_empty_scenario(self):
        """Test parsing scenario without control actions."""
        scenario = {"name": "test", "user_intent": "do something"}
        actions = parse_user_control_actions(scenario)
        assert actions == []

    def test_parse_single_action(self):
        """Test parsing scenario with one control action."""
        scenario = {
            "name": "test",
            "user_control_actions": [
                {
                    "trigger": "after_quarantine",
                    "action": "unquarantine",
                    "tool": "api_v1_servers_id_unquarantine",
                    "args": {"id": "server1"},
                }
            ],
        }
        actions = parse_user_control_actions(scenario)
        assert len(actions) == 1
        assert actions[0].trigger == "after_quarantine"

    def test_parse_multiple_actions(self):
        """Test parsing scenario with multiple control actions."""
        scenario = {
            "name": "test",
            "user_control_actions": [
                {"trigger": "after_tool_1", "action": "read_config", "tool": "api_v1_config"},
                {"trigger": "before_completion", "action": "list_servers", "tool": "api_v1_servers"},
            ],
        }
        actions = parse_user_control_actions(scenario)
        assert len(actions) == 2

    def test_invalid_tool_name_raises_error(self):
        """Test that invalid tool name raises error with validation enabled."""
        scenario = {
            "name": "test",
            "user_control_actions": [
                {"trigger": "after_tool_1", "action": "test", "tool": "invalid_tool_name"},
            ],
        }
        with pytest.raises(ValueError, match="not a valid control MCP tool"):
            parse_user_control_actions(scenario, validate_tools=True)

    def test_validation_disabled(self):
        """Test that validation can be disabled."""
        scenario = {
            "name": "test",
            "user_control_actions": [
                {"trigger": "after_tool_1", "action": "test", "tool": "any_tool_name"},
            ],
        }
        actions = parse_user_control_actions(scenario, validate_tools=False)
        assert len(actions) == 1


class TestIsValidControlTool:
    """Tests for is_valid_control_tool function."""

    def test_valid_prefixes(self):
        """Test valid control tool prefixes."""
        assert is_valid_control_tool("api_v1_config") is True
        assert is_valid_control_tool("api_v1_servers") is True
        assert is_valid_control_tool("api_v1_status") is True
        assert is_valid_control_tool("healthz") is True

    def test_valid_derived_names(self):
        """Test valid derived tool names."""
        assert is_valid_control_tool("api_v1_servers_id_unquarantine") is True
        assert is_valid_control_tool("api_v1_servers_id_restart") is True
        assert is_valid_control_tool("api_v1_servers_id_logs") is True

    def test_invalid_names(self):
        """Test invalid tool names."""
        assert is_valid_control_tool("mcp__mcpproxy__list_tools") is False
        assert is_valid_control_tool("TodoWrite") is False
        assert is_valid_control_tool("random_tool") is False

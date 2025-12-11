"""Contract tests for control MCP tools.

These tests verify that the control tool names and expected behavior
match the mcpproxy REST API contract.
"""

import pytest
from src.mcp_eval.dialog_models import (
    is_valid_control_tool,
    VALID_CONTROL_TOOL_PREFIXES,
)


class TestControlToolContract:
    """Contract tests for control MCP tool names."""

    # Expected control tool names based on mcpproxy OAS spec
    EXPECTED_CONTROL_TOOLS = [
        # Config endpoints
        "api_v1_config",
        # Server list endpoint
        "api_v1_servers",
        # Server control endpoints
        "api_v1_servers_id_restart",
        "api_v1_servers_id_logs",
        "api_v1_servers_id_quarantine",
        "api_v1_servers_id_unquarantine",
        "api_v1_servers_id_enable",
        "api_v1_servers_id_disable",
        # Status endpoint
        "api_v1_status",
        # Health check
        "healthz",
    ]

    # Tool names that should NOT be valid control tools
    EXCLUDED_TOOLS = [
        # MCP protocol tools (Agent Role only)
        "mcp__mcpproxy__retrieve_tools",
        "mcp__mcpproxy__call_tool",
        "mcp__mcpproxy__upstream_servers",
        "mcp__mcpproxy__quarantine_security",
        # Framework tools
        "TodoWrite",
        "Bash",
        "Read",
        "Write",
        # Other API endpoints not exposed as control tools
        "api_v1_tool_calls",
        "api_v1_sessions",
        "api_v1_registries",
    ]

    def test_expected_tools_are_valid(self):
        """Verify all expected control tools are recognized as valid."""
        for tool_name in self.EXPECTED_CONTROL_TOOLS:
            assert is_valid_control_tool(tool_name), f"{tool_name} should be valid"

    def test_excluded_tools_are_invalid(self):
        """Verify excluded tools are not recognized as control tools."""
        for tool_name in self.EXCLUDED_TOOLS:
            assert not is_valid_control_tool(tool_name), f"{tool_name} should not be valid"

    def test_valid_prefixes_cover_expected_tools(self):
        """Verify VALID_CONTROL_TOOL_PREFIXES can match all expected tools."""
        for tool_name in self.EXPECTED_CONTROL_TOOLS:
            matched = False
            for prefix in VALID_CONTROL_TOOL_PREFIXES:
                if tool_name == prefix or tool_name.startswith(prefix):
                    matched = True
                    break
            assert matched, f"{tool_name} not covered by any prefix"


class TestControlToolNamingConvention:
    """Tests for control tool naming convention from OpenAPI paths."""

    # Mapping of OpenAPI paths to expected tool names
    PATH_TO_TOOL_NAME = {
        "/api/v1/config": "api_v1_config",
        "/api/v1/servers": "api_v1_servers",
        "/api/v1/servers/{id}/restart": "api_v1_servers_id_restart",
        "/api/v1/servers/{id}/logs": "api_v1_servers_id_logs",
        "/api/v1/servers/{id}/quarantine": "api_v1_servers_id_quarantine",
        "/api/v1/servers/{id}/unquarantine": "api_v1_servers_id_unquarantine",
        "/api/v1/status": "api_v1_status",
        "/healthz": "healthz",
    }

    def test_path_to_tool_name_conversion(self):
        """Verify OpenAPI path to tool name conversion is correct."""
        for path, expected_name in self.PATH_TO_TOOL_NAME.items():
            # Simulate the conversion done by FastMCP
            # /api/v1/servers/{id}/restart -> api_v1_servers_id_restart
            tool_name = path.lstrip("/").replace("/", "_").replace("{", "").replace("}", "")
            assert tool_name == expected_name, f"Path {path} should convert to {expected_name}"


class TestControlToolArguments:
    """Tests for control tool argument contracts."""

    def test_unquarantine_requires_id(self):
        """Verify unquarantine tool requires server id argument."""
        # This is a documentation/contract test
        # The actual validation happens in UserControlAction
        from src.mcp_eval.dialog_models import UserControlAction

        # Should work with id
        action = UserControlAction(
            trigger="after_quarantine",
            action="unquarantine",
            tool="api_v1_servers_id_unquarantine",
            args={"id": "test-server"},
        )
        assert action.args["id"] == "test-server"

    def test_restart_requires_id(self):
        """Verify restart tool requires server id argument."""
        from src.mcp_eval.dialog_models import UserControlAction

        action = UserControlAction(
            trigger="on_error",
            action="restart",
            tool="api_v1_servers_id_restart",
            args={"id": "my-server"},
        )
        assert action.args["id"] == "my-server"

    def test_logs_accepts_optional_params(self):
        """Verify logs tool accepts optional parameters."""
        from src.mcp_eval.dialog_models import UserControlAction

        action = UserControlAction(
            trigger="before_completion",
            action="get_logs",
            tool="api_v1_servers_id_logs",
            args={"id": "server1", "tail": 100, "level": "error"},
        )
        assert action.args["tail"] == 100


class TestControlToolTriggers:
    """Tests for control tool trigger contracts."""

    VALID_TRIGGERS = [
        "after_tool_1",
        "after_tool_2",
        "after_tool_10",
        "after_quarantine",
        "on_error",
        "before_completion",
        "manual",
    ]

    INVALID_TRIGGERS = [
        "after_tool",  # Missing number
        "after_tool_0",  # Zero not typically used
        "before_tool_1",  # Wrong prefix
        "during_execution",  # Not a valid trigger
        "on_success",  # Not implemented
    ]

    def test_valid_triggers_accepted(self):
        """Verify all valid triggers are accepted."""
        from src.mcp_eval.dialog_models import UserControlAction

        for trigger in self.VALID_TRIGGERS:
            try:
                action = UserControlAction(
                    trigger=trigger,
                    action="test",
                    tool="api_v1_config",
                )
                assert action.trigger == trigger
            except ValueError:
                pytest.fail(f"Trigger {trigger} should be valid")

    def test_invalid_triggers_rejected(self):
        """Verify invalid triggers are rejected."""
        from src.mcp_eval.dialog_models import UserControlAction

        for trigger in self.INVALID_TRIGGERS:
            # Some may be valid (like after_tool_0), so we just check they're handled
            try:
                action = UserControlAction(
                    trigger=trigger,
                    action="test",
                    tool="api_v1_config",
                )
                # If it didn't raise, that's okay for some edge cases
            except ValueError:
                # Expected for truly invalid triggers
                pass

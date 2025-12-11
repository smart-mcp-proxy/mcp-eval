"""Integration tests for dialog session with control actions.

These tests verify the full flow of executing scenarios with
user_control_actions through the DialogSession.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.mcp_eval.dialog_session import DialogSession
from src.mcp_eval.agents import UserAgent, AIAgent
from src.mcp_eval.dialog_models import TurnType, DialogTurn, Actor


class TestDialogSessionWithControlActions:
    """Integration tests for DialogSession with control actions."""

    def create_scenario_with_control(self):
        """Create a test scenario with control actions."""
        return {
            "name": "test_with_control",
            "description": "Test scenario with control actions",
            "user_intent": "Add a server and verify it works",
            "user_control_actions": [
                {
                    "trigger": "after_tool_1",
                    "action": "unquarantine_server",
                    "tool": "api_v1_servers_id_unquarantine",
                    "args": {"id": "test-server"},
                }
            ],
            "success_criteria": ["server added"],
        }

    def create_scenario_without_control(self):
        """Create a test scenario without control actions."""
        return {
            "name": "test_without_control",
            "description": "Test scenario without control actions",
            "user_intent": "List all servers",
            "success_criteria": ["servers listed"],
        }

    def test_user_agent_parses_control_actions(self):
        """Test that UserAgent correctly parses control actions from scenario."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)

        assert len(user_agent.control_actions) == 1
        assert user_agent.control_actions[0].trigger == "after_tool_1"
        assert user_agent.control_actions[0].tool == "api_v1_servers_id_unquarantine"

    def test_user_agent_handles_empty_control_actions(self):
        """Test that UserAgent handles scenarios without control actions."""
        scenario = self.create_scenario_without_control()
        user_agent = UserAgent(scenario=scenario)

        assert len(user_agent.control_actions) == 0

    def test_user_agent_checks_after_tool_trigger(self):
        """Test that UserAgent correctly checks after_tool_N triggers."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)

        # Before any tool calls, should not trigger
        user_agent.agent_tool_call_count = 0
        triggered = user_agent.check_triggers("tool_result", {})
        assert len(triggered) == 0

        # After first tool call, should trigger
        user_agent.agent_tool_call_count = 1
        triggered = user_agent.check_triggers("tool_result", {})
        assert len(triggered) == 1
        assert triggered[0].action == "unquarantine_server"

    def test_user_agent_does_not_retrigger(self):
        """Test that control actions only trigger once."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)
        user_agent.agent_tool_call_count = 1

        # First check should trigger
        triggered1 = user_agent.check_triggers("tool_result", {})
        assert len(triggered1) == 1

        # Second check should not trigger (already executed)
        triggered2 = user_agent.check_triggers("tool_result", {})
        assert len(triggered2) == 0

    def test_user_agent_checks_quarantine_trigger(self):
        """Test that UserAgent detects quarantine in tool results."""
        scenario = {
            "name": "test",
            "user_intent": "test",
            "user_control_actions": [
                {
                    "trigger": "after_quarantine",
                    "action": "unquarantine",
                    "tool": "api_v1_servers_id_unquarantine",
                    "args": {"id": "server1"},
                }
            ],
        }
        user_agent = UserAgent(scenario=scenario)

        # Should trigger when quarantine detected in result
        triggered = user_agent.check_triggers(
            "tool_result",
            {"content": "Server added but quarantined for security review"}
        )
        assert len(triggered) == 1

    def test_user_agent_records_control_call(self):
        """Test that UserAgent correctly records control tool calls."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)

        action = user_agent.control_actions[0]
        call = user_agent.record_control_call(action)

        assert call.type == "CONTROL_TOOL_CALL"
        assert call.tool_name == "api_v1_servers_id_unquarantine"
        assert call.tool_input == {"id": "test-server"}
        assert len(user_agent.control_tool_calls) == 1

    def test_user_agent_records_control_result(self):
        """Test that UserAgent correctly records control tool results."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)

        action = user_agent.control_actions[0]
        call = user_agent.record_control_call(action)
        result = user_agent.record_control_result(
            call,
            success=True,
            response={"status": "unquarantined"},
            error=None
        )

        assert result.type == "CONTROL_TOOL_RESULT"
        assert result.success is True
        assert result.tool_use_id == call.tool_id
        assert len(user_agent.control_tool_results) == 1

    def test_dialog_session_includes_control_data_in_export(self):
        """Test that DialogSession exports include control action data."""
        scenario = self.create_scenario_with_control()
        user_agent = UserAgent(scenario=scenario)
        ai_agent = AIAgent(mcp_config="mcp_servers.json")

        session = DialogSession(
            session_id="test-session",
            scenario=scenario,
            user_agent=user_agent,
            ai_agent=ai_agent,
        )

        # Simulate a control call being recorded
        action = user_agent.control_actions[0]
        call = user_agent.record_control_call(action)
        user_agent.record_control_result(call, True, {"status": "ok"})

        # Export should include control data
        export = session.export_to_json()
        assert export["scenario"]["has_control_actions"] is True
        assert "control_tool_calls" in export
        assert "control_tool_results" in export
        assert len(export["control_tool_calls"]) == 1

    def test_dialog_session_backward_compatible(self):
        """Test that DialogSession works with scenarios without control actions."""
        scenario = self.create_scenario_without_control()
        user_agent = UserAgent(scenario=scenario)
        ai_agent = AIAgent(mcp_config="mcp_servers.json")

        session = DialogSession(
            session_id="test-session",
            scenario=scenario,
            user_agent=user_agent,
            ai_agent=ai_agent,
        )

        export = session.export_to_json()
        assert export["scenario"]["has_control_actions"] is False
        # Should not have control keys if no actions
        assert "control_tool_calls" not in export or len(export.get("control_tool_calls", [])) == 0

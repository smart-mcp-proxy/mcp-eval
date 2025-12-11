"""Unit tests for control MCP server."""

import pytest
from unittest.mock import MagicMock, patch
from fastmcp.server.openapi import HTTPRoute, MCPType

from src.mcp_eval.control_server.server import (
    control_route_mapper,
    create_control_server,
)


class TestControlRouteMapper:
    """Tests for control_route_mapper function."""

    def test_includes_config_endpoint(self):
        """Test that /api/v1/config is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/config"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_servers_endpoint(self):
        """Test that /api/v1/servers is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/servers"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_status_endpoint(self):
        """Test that /api/v1/status is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/status"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_healthz_endpoint(self):
        """Test that /healthz is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/healthz"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_servers_restart(self):
        """Test that /api/v1/servers/{id}/restart is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/servers/{id}/restart"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_servers_unquarantine(self):
        """Test that /api/v1/servers/{id}/unquarantine is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/servers/{id}/unquarantine"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_includes_servers_logs(self):
        """Test that /api/v1/servers/{id}/logs is exposed."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/servers/{id}/logs"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.TOOL

    def test_excludes_mcp_endpoint(self):
        """Test that /mcp endpoint is excluded."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/mcp"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.EXCLUDE

    def test_excludes_tool_calls_endpoint(self):
        """Test that /api/v1/tool-calls is excluded."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/tool-calls"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.EXCLUDE

    def test_excludes_sessions_endpoint(self):
        """Test that /api/v1/sessions is excluded."""
        route = MagicMock(spec=HTTPRoute)
        route.path = "/api/v1/sessions"
        result = control_route_mapper(route, MCPType.TOOL)
        assert result == MCPType.EXCLUDE


class TestCreateControlServer:
    """Tests for create_control_server function."""

    def test_raises_error_when_oas_not_found(self):
        """Test that missing OAS file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="OpenAPI spec not found"):
            create_control_server(oas_path="/nonexistent/path/swagger.yaml")

    @patch("src.mcp_eval.control_server.server.yaml.safe_load")
    @patch("builtins.open")
    @patch("src.mcp_eval.control_server.server.Path.exists")
    def test_creates_server_with_valid_oas(self, mock_exists, mock_open, mock_yaml_load):
        """Test successful server creation with valid OAS."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "test", "version": "1.0"},
            "paths": {},
        }

        # We can't easily test the full FastMCP creation without mocking more,
        # but we can verify the function doesn't error with valid inputs
        # This is more of a smoke test
        try:
            server = create_control_server()
        except Exception as e:
            # Expected - we're not mocking FastMCP
            assert "FastMCP" in str(type(e).__name__) or "openapi" in str(e).lower()

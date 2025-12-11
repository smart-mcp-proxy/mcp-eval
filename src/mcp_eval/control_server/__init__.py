"""Control MCP Server package for User Role mcpproxy control.

This package provides an MCP server that wraps mcpproxy's REST API,
enabling User Role to execute control actions (unquarantine, read config,
restart, view logs) during scenario execution.

The server is auto-generated from mcpproxy's OpenAPI specification using FastMCP v2.
"""

from .server import create_control_server, control_route_mapper

__all__ = ["create_control_server", "control_route_mapper"]

"""Control MCP Server for User Role mcpproxy control.

This module creates an MCP server that wraps mcpproxy's REST API,
enabling User Role to execute control actions during scenario execution.

The server is auto-generated from mcpproxy's OpenAPI specification using FastMCP v2.
Only control-relevant endpoints are exposed as MCP tools.
"""

import os
from pathlib import Path
from typing import Optional

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.openapi import HTTPRoute, MCPType


# Default paths - can be overridden via environment variables
DEFAULT_OAS_PATH = "../mcpproxy-go/oas/swagger.yaml"
DEFAULT_BASE_URL = "http://localhost:8081"


def control_route_mapper(route: HTTPRoute, default_type: MCPType) -> MCPType | None:
    """Filter OpenAPI endpoints to expose only control-relevant operations.

    This function determines which endpoints from mcpproxy's OpenAPI spec
    should be exposed as MCP tools for the User Role.

    Args:
        route: The HTTP route from the OpenAPI spec
        default_type: The default MCP type that would be assigned

    Returns:
        MCPType.TOOL for control endpoints, MCPType.EXCLUDE for others
    """
    # Exact paths to expose as tools
    control_paths = {
        "/api/v1/config",
        "/api/v1/servers",
        "/api/v1/status",
        "/healthz",
    }

    # Path patterns (with {id} parameter) to expose
    control_patterns = [
        "/api/v1/servers/{id}/restart",
        "/api/v1/servers/{id}/logs",
        "/api/v1/servers/{id}/quarantine",
        "/api/v1/servers/{id}/unquarantine",
        "/api/v1/servers/{id}/enable",
        "/api/v1/servers/{id}/disable",
    ]

    # Check exact matches
    if route.path in control_paths:
        return MCPType.TOOL

    # Check pattern matches
    for pattern in control_patterns:
        # Convert pattern to a simple check
        # /api/v1/servers/{id}/restart -> /api/v1/servers/*/restart
        pattern_prefix = pattern.split("{id}")[0]  # /api/v1/servers/
        pattern_suffix = pattern.split("{id}")[1] if "{id}" in pattern else ""  # /restart

        if route.path.startswith(pattern_prefix):
            # Check if path has the right structure
            remaining = route.path[len(pattern_prefix):]
            if pattern_suffix:
                if remaining.endswith(pattern_suffix) or pattern_suffix.lstrip("/") in remaining:
                    return MCPType.TOOL
            else:
                # No suffix means just checking prefix
                return MCPType.TOOL

    # Exclude all other endpoints
    return MCPType.EXCLUDE


def create_control_server(
    oas_path: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> FastMCP:
    """Create the control MCP server from mcpproxy's OpenAPI spec.

    Args:
        oas_path: Path to mcpproxy's OpenAPI spec (swagger.yaml)
        base_url: Base URL for mcpproxy REST API
        api_key: API key for mcpproxy authentication

    Returns:
        FastMCP server instance ready to run

    Raises:
        FileNotFoundError: If OAS file not found
        ValueError: If OAS file is invalid
    """
    # Resolve paths and configuration
    oas_path = oas_path or os.getenv("MCPPROXY_OAS_PATH", DEFAULT_OAS_PATH)
    base_url = base_url or os.getenv("MCPPROXY_BASE_URL", DEFAULT_BASE_URL)
    api_key = api_key or os.getenv("MCPPROXY_API_KEY", "")

    # Resolve relative path from mcp-eval root
    oas_file = Path(oas_path)
    if not oas_file.is_absolute():
        # Try relative to current working directory
        if not oas_file.exists():
            # Try relative to mcp-eval package root
            package_root = Path(__file__).parent.parent.parent.parent
            oas_file = package_root / oas_path

    if not oas_file.exists():
        raise FileNotFoundError(
            f"MCPProxy OpenAPI spec not found at: {oas_file}\n"
            f"Set MCPPROXY_OAS_PATH environment variable to the correct path."
        )

    # Load OpenAPI spec
    with open(oas_file, "r") as f:
        openapi_spec = yaml.safe_load(f)

    # Create HTTP client for mcpproxy REST API
    client_params = {}
    if api_key:
        client_params["params"] = {"apikey": api_key}

    client = httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
        **client_params,
    )

    # Create MCP server from OpenAPI spec with route filtering
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="mcpproxy-control",
        route_map_fn=control_route_mapper,
    )

    return mcp


# Module-level server for stdio transport
_server: Optional[FastMCP] = None


def get_server() -> FastMCP:
    """Get or create the control MCP server singleton."""
    global _server
    if _server is None:
        _server = create_control_server()
    return _server


def main():
    """Run the control MCP server (stdio transport)."""
    server = get_server()
    server.run()


if __name__ == "__main__":
    main()
